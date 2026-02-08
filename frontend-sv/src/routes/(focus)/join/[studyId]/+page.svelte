<script>
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { getStudyById } from '$lib/api.js';
	import { user, loading as authLoading } from '$lib/authStore.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card/index.js';
	import { supabase, signUp, getUserProfile, updateUserProfile, acknowledgeConsent } from '$lib/supabase.js';

	let loading = true;
	let notAvailable = false;
	let study = null;
	let errorMessage = '';

	let email = '';
	let password = '';
	let confirmPassword = '';
	let signupLoading = false;

	let profileLoading = false;
	let profileSaving = false;
	let profile = null;
	let profileAge = '';
	let profileGender = '';
	let profileZip = '';
	let profileConditions = '';

	let participationLoading = false;
	let participation = null;
	let consentSaving = false;

	let initializedAfterAuth = false;

	$: joinRedirectPath = page?.url?.pathname || `/join/${page.params.studyId}`;
	$: loginHref = `/login?redirect=${encodeURIComponent(joinRedirectPath)}`;
	$: currentStep = (() => {
		// Map existing UI states to Step 1–4 without changing any gating.
		if ($authLoading) return 1;
		if (!$user) return 1;

		// While we refresh state, infer the most likely active step.
		if (profileLoading || participationLoading) {
			if (!isProfileComplete(profile)) return 2;
			if (participation && participation.status !== 'approved') return 3;
			return 4;
		}

		if (!isProfileComplete(profile)) return 2;
		if (participation && participation.status !== 'approved') return 3;
		return 4;
	})();

	function isProfileComplete(p) {
		if (!p) return false;
		return Boolean(p.age) && Boolean(p.gender) && Boolean(p.zip_code);
	}

	async function loadProfile() {
		profileLoading = true;
		try {
			profile = await getUserProfile($user.id);
			profileAge = profile?.age ?? '';
			profileGender = profile?.gender ?? '';
			profileZip = profile?.zip_code ?? '';
			profileConditions = Array.isArray(profile?.conditions) ? profile.conditions.join(', ') : '';
		} finally {
			profileLoading = false;
		}
	}

	async function loadParticipation() {
		participationLoading = true;
		try {
			const { data, error } = await supabase
				.from('participation_requests')
				.select('*')
				.eq('study_id', Number(page.params.studyId))
				.eq('user_id', $user.id)
				.maybeSingle();

			if (error) throw error;
			participation = data;
		} finally {
			participationLoading = false;
		}
	}

	async function ensureParticipationRequest() {
		await loadParticipation();
		if (participation) return;

		participationLoading = true;
		try {
			// Attempt auto-approve insert first; RLS will reject for non-auto-approve studies.
			let { data, error } = await supabase
				.from('participation_requests')
				.insert({
					user_id: $user.id,
					study_id: Number(page.params.studyId),
					status: 'approved'
				})
				.select()
				.single();

			if (error) {
				// Fall back to a standard pending request for non-auto-approve studies.
				({ data, error } = await supabase
					.from('participation_requests')
					.insert({
						user_id: $user.id,
						study_id: Number(page.params.studyId),
						status: 'pending'
					})
					.select()
					.single());
			}

			if (error) throw error;
			participation = data;
		} finally {
			participationLoading = false;
		}
	}

	async function tryAutoApprovePending() {
		if (!participation) return;
		if (participation.status !== 'pending') return;
		if (!study?.auto_approve_participation) return;

		participationLoading = true;
		try {
			const { data, error } = await supabase
				.from('participation_requests')
				.update({ status: 'approved' })
				.eq('id', participation.id)
				.select()
				.single();

			if (error) throw error;
			participation = data;
		} finally {
			participationLoading = false;
		}
	}

	async function refreshJoinState() {
		errorMessage = '';
		if (!$user) return;

		await loadProfile();
		await ensureParticipationRequest();
		await tryAutoApprovePending();
		await loadParticipation();
	}

	async function handleSignup() {
		errorMessage = '';
		if (!email.trim()) {
			errorMessage = 'Email is required.';
			return;
		}
		if (!password) {
			errorMessage = 'Password is required.';
			return;
		}
		if (password !== confirmPassword) {
			errorMessage = 'Passwords do not match.';
			return;
		}
		if (password.length < 6) {
			errorMessage = 'Password must be at least 6 characters.';
			return;
		}

		signupLoading = true;
		try {
			const result = await signUp(email.trim(), password);
			if (!result?.session) {
				errorMessage = 'Signup succeeded, but no session was returned.';
				return;
			}
			initializedAfterAuth = false;
		} catch (err) {
			errorMessage = err?.message || 'Signup failed.';
		} finally {
			signupLoading = false;
		}
	}

	async function handleSaveProfile() {
		errorMessage = '';
		if (!$user) return;

		profileSaving = true;
		try {
			const conditions = profileConditions
				.split(',')
				.map((c) => c.trim())
				.filter(Boolean)
				.map((c) => c.toLowerCase());

			await updateUserProfile($user.id, {
				age: profileAge ? Number(profileAge) : null,
				gender: profileGender || null,
				zip_code: profileZip || null,
				conditions
			});
			initializedAfterAuth = false;
		} catch (err) {
			errorMessage = err?.message || 'Failed to save profile.';
		} finally {
			profileSaving = false;
		}
	}

	async function handleAcknowledgeConsent() {
		errorMessage = '';
		if (!participation?.id) return;

		consentSaving = true;
		try {
			participation = await acknowledgeConsent(participation.id);
		} catch (err) {
			errorMessage = err?.message || 'Failed to acknowledge consent.';
		} finally {
			consentSaving = false;
		}
	}

	onMount(async () => {
		loading = true;
		notAvailable = false;
		study = null;
		errorMessage = '';
		profile = null;
		participation = null;
		initializedAfterAuth = false;

		try {
			study = await getStudyById(page.params.studyId);
			// Join route is only enabled for explicitly joinable studies.
			if (!study?.join_flow_key) {
				notAvailable = true;
				study = null;
			}
		} catch {
			notAvailable = true;
		} finally {
			loading = false;
		}
	});

	$: if (!loading && !notAvailable && study && !$authLoading && !initializedAfterAuth) {
		initializedAfterAuth = true;
		refreshJoinState().catch((err) => {
			errorMessage = err?.message || 'Something went wrong.';
		});
	}
</script>

<main class="min-h-screen bg-background flex items-center justify-center p-6">
	{#if loading}
		<div class="text-center">
			<p class="text-sm text-muted-foreground">Preparing your study session…</p>
		</div>
	{:else if notAvailable}
		<div class="text-center">
			<h1 class="text-2xl font-semibold">Study not available</h1>
		</div>
	{:else}
		<div class="w-full max-w-xl">
			<div class="text-center mb-6">
				<h1 class="text-3xl font-bold tracking-tight">{study.title}</h1>
				<p class="text-sm text-muted-foreground mt-2">Step {currentStep} of 4</p>
			</div>

			{#if $authLoading}
				<div class="text-center">
					<p class="text-sm text-muted-foreground">Preparing your study session…</p>
					{#if errorMessage}
						<p class="text-sm text-destructive mt-2">{errorMessage}</p>
					{/if}
				</div>
			{:else if !$user}
				<Card>
					<CardHeader>
						<CardTitle>Create your account</CardTitle>
						<p class="text-sm text-muted-foreground">
							This creates a secure login so we can save your progress.
						</p>
					</CardHeader>
					<CardContent>
						{#if errorMessage}
							<p class="text-sm text-destructive mb-4">{errorMessage}</p>
						{/if}
						<form on:submit|preventDefault={handleSignup} class="space-y-4">
							<div class="space-y-2">
								<label for="email" class="text-sm font-medium">Email</label>
								<Input id="email" type="email" bind:value={email} required disabled={signupLoading} />
							</div>
							<div class="space-y-2">
								<label for="password" class="text-sm font-medium">Password</label>
								<Input id="password" type="password" bind:value={password} required disabled={signupLoading} />
							</div>
							<div class="space-y-2">
								<label for="confirmPassword" class="text-sm font-medium">Confirm password</label>
								<Input id="confirmPassword" type="password" bind:value={confirmPassword} required disabled={signupLoading} />
							</div>
							<button
								type="submit"
								disabled={signupLoading}
								class="w-full h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
							>
								{signupLoading ? 'Creating…' : 'Create account and continue'}
							</button>
						</form>
						<div class="mt-4 text-sm text-muted-foreground">
							Already have an account?
							<a href={loginHref} class="underline underline-offset-4 hover:opacity-90">Sign in</a>
						</div>
					</CardContent>
				</Card>
			{:else if profileLoading || participationLoading}
				<div class="text-center">
					<p class="text-sm text-muted-foreground">Preparing your study session…</p>
					{#if errorMessage}
						<p class="text-sm text-destructive mt-2">{errorMessage}</p>
					{/if}
				</div>
			{:else if !isProfileComplete(profile)}
				<Card>
					<CardHeader>
						<CardTitle>Complete your profile</CardTitle>
						<p class="text-sm text-muted-foreground">
							We use this to confirm basic eligibility and tailor instructions.
						</p>
					</CardHeader>
					<CardContent>
						{#if errorMessage}
							<p class="text-sm text-destructive mb-4">{errorMessage}</p>
						{/if}
						<form on:submit|preventDefault={handleSaveProfile} class="space-y-4">
							<div class="space-y-2">
								<label for="age" class="text-sm font-medium">Age (years)</label>
								<Input id="age" type="number" min="0" bind:value={profileAge} placeholder="e.g., 25" disabled={profileSaving} />
							</div>
							<div class="space-y-2">
								<label for="gender" class="text-sm font-medium">Gender</label>
								<Input
									id="gender"
									type="text"
									bind:value={profileGender}
									placeholder="e.g., woman, man, non-binary"
									disabled={profileSaving}
								/>
							</div>
							<div class="space-y-2">
								<label for="zip" class="text-sm font-medium">ZIP code</label>
								<Input
									id="zip"
									type="text"
									maxlength="10"
									bind:value={profileZip}
									placeholder="e.g., 02139"
									disabled={profileSaving}
								/>
							</div>
							<div class="space-y-2">
								<label for="conditions" class="text-sm font-medium">Conditions (optional, comma-separated)</label>
								<Input
									id="conditions"
									type="text"
									bind:value={profileConditions}
									placeholder="e.g., asthma, tinnitus"
									disabled={profileSaving}
								/>
							</div>
							<button
								type="submit"
								disabled={profileSaving}
								class="w-full h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
							>
								{profileSaving ? 'Saving…' : 'Save and continue'}
							</button>
						</form>
					</CardContent>
				</Card>
			{:else if participation && participation.status !== 'approved'}
				<Card>
					<CardHeader>
						<CardTitle>Participation request sent</CardTitle>
						<p class="text-sm text-muted-foreground">
							We need to approve your request before you can begin.
						</p>
					</CardHeader>
					<CardContent>
						{#if errorMessage}
							<p class="text-sm text-destructive mb-4">{errorMessage}</p>
						{/if}
						<p class="text-sm text-muted-foreground">
							Status: {participation.status}. Once approved, you’ll review a short consent summary and then start the recording session.
						</p>
					</CardContent>
				</Card>
			{:else if participation && !participation.consent_acknowledged_at}
				<Card>
					<CardHeader>
						<CardTitle>Consent</CardTitle>
						<p class="text-sm text-muted-foreground">
							This is required before we can collect any recordings.
						</p>
					</CardHeader>
					<CardContent class="space-y-4">
						{#if errorMessage}
							<p class="text-sm text-destructive">{errorMessage}</p>
						{/if}
						<div class="text-sm text-muted-foreground space-y-1">
							<p>You’ll complete a short speech recording session.</p>
							<p>Your submissions are stored securely and used for research.</p>
							<p>Participation is voluntary; you can stop at any time.</p>
						</div>
						<button
							type="button"
							disabled={consentSaving}
							on:click={handleAcknowledgeConsent}
							class="w-full h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
						>
							{consentSaving ? 'Saving…' : 'I consent and continue'}
						</button>
					</CardContent>
				</Card>
			{:else}
				<Card>
					<CardHeader>
						<CardTitle>Ready</CardTitle>
						<p class="text-sm text-muted-foreground">
							You’re approved and consented — you can begin now.
						</p>
					</CardHeader>
					<CardContent class="space-y-4">
						{#if errorMessage}
							<p class="text-sm text-destructive">{errorMessage}</p>
						{/if}
						<p class="text-sm text-muted-foreground">
							You’ll record ~30-second clips. You can re-record before submitting.
						</p>
						<a
							href={`/study/${page.params.studyId}/tasks`}
							class="w-full inline-flex items-center justify-center h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
						>
							Start recording session
						</a>
					</CardContent>
				</Card>
			{/if}
		</div>
	{/if}
</main>
