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
			<p class="text-sm text-muted-foreground">Loading…</p>
		</div>
	{:else if notAvailable}
		<div class="text-center">
			<h1 class="text-2xl font-semibold">Study not available</h1>
		</div>
	{:else}
		<div class="w-full max-w-xl">
			<div class="text-center mb-6">
				{#if study?.join_flow_key === 'slp-2026'}
					<h1 class="text-3xl font-bold tracking-tight">SLP 2026 — Join</h1>
				{:else}
					<h1 class="text-3xl font-bold tracking-tight">Join this study</h1>
				{/if}
				<p class="text-sm text-muted-foreground mt-2">Study ID: {page.params.studyId}</p>
			</div>

			{#if errorMessage}
				<p class="text-sm text-destructive mb-4 text-center">{errorMessage}</p>
			{/if}

			{#if $authLoading}
				<div class="text-center">
					<p class="text-sm text-muted-foreground">Loading account…</p>
				</div>
			{:else if !$user}
				<Card>
					<CardHeader>
						<CardTitle>Create your account</CardTitle>
					</CardHeader>
					<CardContent>
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
								{signupLoading ? 'Creating…' : 'Create account'}
							</button>
						</form>
					</CardContent>
				</Card>
			{:else if profileLoading || participationLoading}
				<div class="text-center">
					<p class="text-sm text-muted-foreground">Preparing your join…</p>
				</div>
			{:else if !isProfileComplete(profile)}
				<Card>
					<CardHeader>
						<CardTitle>Complete your profile</CardTitle>
					</CardHeader>
					<CardContent>
						<form on:submit|preventDefault={handleSaveProfile} class="space-y-4">
							<div class="space-y-2">
								<label for="age" class="text-sm font-medium">Age</label>
								<Input id="age" type="number" min="0" bind:value={profileAge} disabled={profileSaving} />
							</div>
							<div class="space-y-2">
								<label for="gender" class="text-sm font-medium">Gender</label>
								<Input id="gender" type="text" bind:value={profileGender} disabled={profileSaving} />
							</div>
							<div class="space-y-2">
								<label for="zip" class="text-sm font-medium">ZIP code</label>
								<Input id="zip" type="text" maxlength="10" bind:value={profileZip} disabled={profileSaving} />
							</div>
							<div class="space-y-2">
								<label for="conditions" class="text-sm font-medium">Conditions (comma-separated)</label>
								<Input id="conditions" type="text" bind:value={profileConditions} disabled={profileSaving} />
							</div>
							<button
								type="submit"
								disabled={profileSaving}
								class="w-full h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
							>
								{profileSaving ? 'Saving…' : 'Save profile'}
							</button>
						</form>
					</CardContent>
				</Card>
			{:else if participation && participation.status !== 'approved'}
				<Card>
					<CardHeader>
						<CardTitle>Request submitted</CardTitle>
					</CardHeader>
					<CardContent>
						<p class="text-sm text-muted-foreground">
							Your participation request is {participation.status}. You’ll be able to start tasks once you’re approved and have acknowledged consent.
						</p>
					</CardContent>
				</Card>
			{:else if participation && !participation.consent_acknowledged_at}
				<Card>
					<CardHeader>
						<CardTitle>Consent</CardTitle>
					</CardHeader>
					<CardContent class="space-y-4">
						<p class="text-sm text-muted-foreground">
							By continuing, you acknowledge the study consent information.
						</p>
						<button
							type="button"
							disabled={consentSaving}
							on:click={handleAcknowledgeConsent}
							class="w-full h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
						>
							{consentSaving ? 'Saving…' : 'I agree'}
						</button>
					</CardContent>
				</Card>
			{:else}
				<Card>
					<CardHeader>
						<CardTitle>Ready</CardTitle>
					</CardHeader>
					<CardContent class="space-y-4">
						<p class="text-sm text-muted-foreground">
							You’re approved and consented. You can start tasks.
						</p>
						<a
							href={`/study/${page.params.studyId}/tasks`}
							class="w-full inline-flex items-center justify-center h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
						>
							Start task
						</a>
					</CardContent>
				</Card>
			{/if}
		</div>
	{/if}
</main>
