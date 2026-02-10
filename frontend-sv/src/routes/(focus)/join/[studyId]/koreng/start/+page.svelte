<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { getStudyById } from '$lib/api.js';
	import { getStudyByIdSupabase } from '$lib/supabase.js';

	let loading = true;
	let error = null;

	onMount(async () => {
		const studyId = page.params.studyId;
		
		try {
			// Load study (try FastAPI first, fallback to Supabase)
			let study;
			try {
				study = await getStudyById(studyId);
			} catch {
				study = await getStudyByIdSupabase(studyId);
			}

			// Validate koreng flow key
			if (study?.join_flow_key !== 'koreng_phoneme') {
				error = 'This study is not configured for this recording session.';
				loading = false;
				return;
			}

			// Validate tasks exist
			if (!study.tasks || study.tasks.length === 0) {
				error = 'No tasks configured for this study.';
				loading = false;
				return;
			}

			// Get first task
			const firstTaskId = study.tasks[0].id;
			
			// Navigate to first task
			goto(`/join/${studyId}/koreng/task/${firstTaskId}`);
		} catch (err) {
			console.error('Error loading koreng session:', err);
			error = 'Failed to start session.';
			loading = false;
		}
	});
</script>

<main class="min-h-screen bg-background flex items-center justify-center p-6">
	{#if loading}
		<div class="text-center">
			<p class="text-sm text-muted-foreground">Starting your session…</p>
		</div>
	{:else if error}
		<div class="text-center max-w-md">
			<h1 class="text-2xl font-semibold mb-2">Cannot start session</h1>
			<p class="text-sm text-muted-foreground mb-4">{error}</p>
			<a
				href={`/join/${page.params.studyId}`}
				class="inline-flex items-center justify-center px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
			>
				Return to join
			</a>
		</div>
	{/if}
</main>
