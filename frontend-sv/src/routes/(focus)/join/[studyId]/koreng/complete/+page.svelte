<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { getStudyById } from '$lib/api.js';
	import { getStudyByIdSupabase } from '$lib/supabase.js';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card/index.js';

	let loading = true;
	let studyTitle = '';

	onMount(async () => {
		const studyId = page.params.studyId;
		
		try {
			// Load study title for friendly thank-you message
			let study;
			try {
				study = await getStudyById(studyId);
			} catch {
				study = await getStudyByIdSupabase(studyId);
			}

			studyTitle = study?.title || 'this study';
		} catch (err) {
			console.error('Error loading study:', err);
			studyTitle = 'this study';
		} finally {
			loading = false;
		}
	});

	function handleContinue() {
		goto(`/profile?studyId=${page.params.studyId}&highlight=participation`);
	}
</script>

<main class="min-h-screen bg-background flex items-center justify-center p-6">
	{#if loading}
		<div class="text-center">
			<p class="text-sm text-muted-foreground">Finalizing…</p>
		</div>
	{:else}
		<Card class="max-w-md w-full">
			<CardHeader>
				<CardTitle class="text-center">Thank you!</CardTitle>
			</CardHeader>
			<CardContent class="space-y-4 text-center">
				<p class="text-sm text-muted-foreground">
					You've completed all tasks for <span class="font-medium text-foreground">{studyTitle}</span>.
				</p>
				<p class="text-sm text-muted-foreground">
					Your recordings have been securely saved and the research team will review them soon.
				</p>
				<button
					on:click={handleContinue}
					class="w-full px-6 py-3 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90"
				>
					View my participation
				</button>
			</CardContent>
		</Card>
	{/if}
</main>
