<script>
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fly } from 'svelte/transition';
	import {
		getStudyByIdSupabase,
		getMyParticipationForStudy,
		getMyTaskSubmissions,
		submitTaskResponse,
		uploadAudioRecording,
		deleteAudioRecording,
		getTaskMediaUrl
	} from '$lib/supabase.js';
	import { getStudyById } from '$lib/api.js';
	import { user, loading as authLoading } from '$lib/authStore';
	import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card/index.js';

	// Route params
	let studyId = null;
	let taskId = null;

	// State
	let loading = true;
	let error = null;
	let study = null;
	let task = null;
	let participation = null;
	let alreadySubmitted = {};

	// Task navigation
	let taskNumber = 1;
	let totalTasks = 1;

	// Page navigation
	let currentPageIndex = 0;
	let responses = {};
	let showValidationHint = false;

	// Audio recording
	const MAX_RECORDING_SECONDS = 30;
	let activeRecordingBlockId = null;
	let mediaRecorder = null;
	let activeStream = null;
	let recordingTimer = 0;
	let recordingInterval = null;
	let stopInProgress = false;

	// Per-block audio state maps
	let audioStatusByBlockId = {};      // 'idle' | 'recording' | 'uploading' | 'saved' | 'error'
	let audioErrorByBlockId = {};       // error message per block
	let audioPreviewUrlByBlockId = {};  // object URL for playback
	let lastBlobByBlockId = {};         // blob for retry upload
	let pendingDeletePathByBlockId = {}; // path to delete after successful re-record

	// Submit modal
	let showConfirmModal = false;
	let submitting = false;
	let submitError = null;

	// Derived values
	$: pages = task?.pages || [];
	$: totalPages = pages.length;
	$: currentPage = pages[currentPageIndex] || null;
	$: isFirstPage = currentPageIndex === 0;
	$: isLastPage = currentPageIndex === totalPages - 1;

	// FIX: Pass pages and responses as explicit dependencies so Svelte re-runs validation
	// when these objects change (e.g., after audio upload completes)
	$: currentPageValid = validatePage(currentPageIndex, pages, responses);
	$: allPagesValid = validateAllPages(pages, responses);

	// Audio busy states - also pass audioStatusByBlockId as explicit dependency
	$: isAudioBusyOnCurrentPage = checkAudioBusyOnCurrentPage(currentPage, audioStatusByBlockId);
	$: anyAudioBusy = Object.values(audioStatusByBlockId).some(
		(s) => s === 'recording' || s === 'uploading'
	);

	function setResponse(blockId, value) {
		responses = { ...responses, [blockId]: value };
	}

	function setAudioStatus(blockId, status) {
		audioStatusByBlockId = { ...audioStatusByBlockId, [blockId]: status };
	}

	function setAudioError(blockId, message) {
		audioErrorByBlockId = { ...audioErrorByBlockId, [blockId]: message };
	}

	function setAudioPreviewUrl(blockId, url) {
		audioPreviewUrlByBlockId = { ...audioPreviewUrlByBlockId, [blockId]: url };
	}

	function setLastBlob(blockId, blob) {
		lastBlobByBlockId = { ...lastBlobByBlockId, [blockId]: blob };
	}

	function setPendingDeletePath(blockId, path) {
		pendingDeletePathByBlockId = { ...pendingDeletePathByBlockId, [blockId]: path };
	}

	function clearPendingDeletePath(blockId) {
		if (!pendingDeletePathByBlockId[blockId]) return;
		const next = { ...pendingDeletePathByBlockId };
		delete next[blockId];
		pendingDeletePathByBlockId = next;
	}

	function clearLastBlob(blockId) {
		if (!lastBlobByBlockId[blockId]) return;
		const next = { ...lastBlobByBlockId };
		delete next[blockId];
		lastBlobByBlockId = next;
	}

	// FIX: Accept currentPage and audioStatusByBlockId as parameters for proper reactivity
	function checkAudioBusyOnCurrentPage(pg, statusMap) {
		if (!pg) return false;
		for (const block of pg.blocks || []) {
			if (block.type === 'audio_recording') {
				const status = statusMap[block.id];
				if (status === 'recording' || status === 'uploading') return true;
			}
		}
		return false;
	}

	// FIX: Accept pages and responses as parameters for proper reactivity
	function validatePage(pageIndex, pagesArr, responsesObj) {
		const pg = pagesArr[pageIndex];
		if (!pg) return false;
		for (const block of pg.blocks || []) {
			if (!block.required) continue;
			// Skip display-only blocks that don't require user input
			if (block.type === 'text' || block.type === 'media') continue;
			if (block.type === 'audio_recording') {
				// Audio is valid if we have saved metadata with a path
				const hasValidRecording = Boolean(responsesObj[block.id]?.path);
				if (!hasValidRecording) return false;
			} else if (block.type === 'checkbox') {
				if (!responsesObj[block.id] || responsesObj[block.id].length === 0) return false;
			} else {
				// For text/number inputs, check if response exists and is not just whitespace
				const response = responsesObj[block.id];
				if (response === undefined || response === null || (typeof response === 'string' && response.trim() === '')) {
					return false;
				}
			}
		}
		return true;
	}

	// FIX: Accept pages and responses as parameters for proper reactivity
	function validateAllPages(pagesArr, responsesObj) {
		for (let i = 0; i < pagesArr.length; i++) {
			if (!validatePage(i, pagesArr, responsesObj)) return false;
		}
		return true;
	}

	// Navigation
	function nextPage() {
		if (!currentPageValid || anyAudioBusy) {
			showValidationHint = true;
			return;
		}
		if (currentPageIndex < totalPages - 1) {
			currentPageIndex++;
			showValidationHint = false;
		}
	}

	function prevPage() {
		if (currentPageIndex > 0 && !anyAudioBusy) {
			currentPageIndex--;
			showValidationHint = false;
		}
	}

	// Checkbox handler
	function handleCheckboxChange(blockId, option, checked) {
		const current = responses[blockId] || [];
		if (checked) {
			setResponse(blockId, [...current, option]);
		} else {
			setResponse(blockId, current.filter((o) => o !== option));
		}
	}

	// Audio recording functions
	function formatTime(seconds) {
		const m = Math.floor(seconds / 60);
		const s = seconds % 60;
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	async function startRecording(blockId) {
		if (anyAudioBusy || activeRecordingBlockId) return;

		try {
			stopInProgress = false;
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			activeStream = stream;
			activeRecordingBlockId = blockId;
			setAudioStatus(blockId, 'recording');
			setAudioError(blockId, null);

			const chunks = [];
			mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

			mediaRecorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunks.push(e.data);
			};

			mediaRecorder.onstop = async () => {
				const blob = new Blob(chunks, { type: 'audio/webm' });
				setLastBlob(blockId, blob);

				// Recording has ended; release locks and stop the stream now.
				activeRecordingBlockId = null;
				if (activeStream) {
					activeStream.getTracks().forEach((t) => t.stop());
					activeStream = null;
				}

				// Create preview URL
				if (audioPreviewUrlByBlockId[blockId]) {
					URL.revokeObjectURL(audioPreviewUrlByBlockId[blockId]);
				}
				setAudioPreviewUrl(blockId, URL.createObjectURL(blob));

				// Upload
				await uploadBlob(blockId, blob);
				stopInProgress = false;
			};

			mediaRecorder.start();
			recordingTimer = 0;

			recordingInterval = setInterval(() => {
				recordingTimer++;
				if (recordingTimer >= MAX_RECORDING_SECONDS) {
					stopRecording();
				}
			}, 1000);
		} catch (err) {
			console.error('Failed to start recording:', err);
			setAudioStatus(blockId, 'error');
			setAudioError(blockId, 'Could not access microphone. Please check permissions.');
			activeRecordingBlockId = null;
			stopInProgress = false;
		}
	}

	function stopRecording() {
		if (stopInProgress) return;
		if (!mediaRecorder) return;
		if (mediaRecorder.state === 'inactive') return;

		stopInProgress = true;
		if (recordingInterval) {
			clearInterval(recordingInterval);
			recordingInterval = null;
		}
		try {
			mediaRecorder.stop();
		} catch (err) {
			console.error('Failed to stop recording:', err);
			stopInProgress = false;
		}
	}

	async function uploadBlob(blockId, blob) {
		setAudioStatus(blockId, 'uploading');
		setAudioError(blockId, null);

		try {
			const result = await uploadAudioRecording(studyId, participation.id, blob);

			// uploadAudioRecording throws on error; no result.error expected.

			// If there was a pending delete from re-record, delete it now
			if (pendingDeletePathByBlockId[blockId]) {
				try {
					await deleteAudioRecording(pendingDeletePathByBlockId[blockId]);
				} catch {
					// Ignore delete errors
				}
				clearPendingDeletePath(blockId);
			}

			setResponse(blockId, {
				path: result.path,
				size: blob.size,
				mimeType: blob.type,
				uploadedAt: result.uploadedAt || new Date().toISOString()
			});

			setAudioStatus(blockId, 'saved');
		} catch (err) {
			console.error('Upload failed:', err);

			// Safer re-record behavior: if a previous recording exists, keep it as saved.
			if (responses[blockId]?.path) {
				setAudioStatus(blockId, 'saved');
				setAudioError(blockId, err?.message || 'Upload failed. Your previous recording is still saved.');
			} else {
				setAudioStatus(blockId, 'error');
				setAudioError(blockId, err?.message || 'Upload failed. Please retry.');
			}
		}
	}

	async function handleRetryUpload(blockId) {
		const blob = lastBlobByBlockId[blockId];
		if (blob) {
			await uploadBlob(blockId, blob);
		}
	}

	async function handleRerecord(blockId) {
		// Store current path for deletion after successful new upload
		if (responses[blockId]?.path) {
			setPendingDeletePath(blockId, responses[blockId].path);
		}

		// Reset local attempt state, but keep prior saved response until a new upload succeeds.
		setAudioStatus(blockId, 'idle');
		setAudioError(blockId, null);

		if (audioPreviewUrlByBlockId[blockId]) {
			URL.revokeObjectURL(audioPreviewUrlByBlockId[blockId]);
			const next = { ...audioPreviewUrlByBlockId };
			delete next[blockId];
			audioPreviewUrlByBlockId = next;
		}

		clearLastBlob(blockId);
	}

	// Submit functions
	function handleShowConfirm() {
		if (!allPagesValid || anyAudioBusy) {
			showValidationHint = true;
			return;
		}
		submitError = null;
		showConfirmModal = true;
	}

	async function handleSubmit() {
		if (submitting) return;
		submitting = true;
		submitError = null;

		try {
			const { error: submitErr } = await submitTaskResponse(studyId, taskId, responses);

			if (submitErr) {
				throw new Error(submitErr);
			}

			// Find next task
			const tasks = study.tasks || [];
			const currentIndex = tasks.findIndex((t) => t.id === taskId);
			const nextTask = tasks[currentIndex + 1];

			if (nextTask) {
				goto(`/join/${studyId}/koreng/task/${nextTask.id}`);
			} else {
				goto(`/join/${studyId}/koreng/complete`);
			}
		} catch (err) {
			console.error('Submit failed:', err);
			submitError = err.message || 'Failed to submit. Please try again.';
			submitting = false;
		}
	}

	// Load data
	async function loadData() {
		loading = true;
		error = null;

		studyId = $page.params.studyId;
		taskId = $page.params.taskId;

		// Wait for auth to finish loading
		if ($authLoading) {
			// Auth still initializing, wait a bit and check again
			const unsubscribe = authLoading.subscribe((isLoading) => {
				if (!isLoading) {
					unsubscribe();
					loadData();
				}
			});
			return;
		}

		// Check auth
		if (!$user) {
			const redirectPath = encodeURIComponent(`/join/${studyId}/koreng/task/${taskId}`);
			goto(`/login?redirect=${redirectPath}`);
			return;
		}

		try {
			// Load study (try FastAPI first, fallback to Supabase)
			let studyData = await getStudyById(studyId);
			if (!studyData) {
				studyData = await getStudyByIdSupabase(studyId);
			}

			if (!studyData) {
				error = 'Study not found.';
				loading = false;
				return;
			}

			study = studyData;

			// Validate koreng flow
			if (study.join_flow_key !== 'koreng_phoneme') {
				error = 'This study does not use the koreng flow.';
				loading = false;
				return;
			}

			// Check participation
			const participationData = await getMyParticipationForStudy(studyId);

			if (!participationData) {
				error = 'You must join this study to access tasks.';
				loading = false;
				return;
			}

			if (participationData.status !== 'approved') {
				error = 'Your participation has not been approved yet.';
				loading = false;
				return;
			}

			if (!participationData.consent_acknowledged_at) {
				error = 'You must acknowledge consent before accessing tasks.';
				loading = false;
				return;
			}

			participation = participationData;

			// Find task
			const tasks = study.tasks || [];
			totalTasks = tasks.length;
			const currentTaskIndex = tasks.findIndex((t) => t.id === taskId);

			if (currentTaskIndex === -1) {
				error = 'Task not found.';
				loading = false;
				return;
			}

			task = tasks[currentTaskIndex];
			taskNumber = currentTaskIndex + 1;

			// Check already submitted
			const { data: submissions } = await getMyTaskSubmissions(studyId);
			if (submissions) {
				for (const sub of submissions) {
					alreadySubmitted[sub.task_id] = true;
				}
			}

			// If current task already submitted, advance
			if (alreadySubmitted[taskId]) {
				const nextTask = tasks[currentTaskIndex + 1];
				if (nextTask && !alreadySubmitted[nextTask.id]) {
					goto(`/join/${studyId}/koreng/task/${nextTask.id}`);
				} else {
					goto(`/join/${studyId}/koreng/complete`);
				}
				return;
			}

			// Initialize responses and audio status for existing saved audio
			currentPageIndex = 0;
			responses = {};
			let nextAudioStatusByBlockId = {};

			for (const pg of task.pages || []) {
				for (const block of pg.blocks || []) {
					if (block.type === 'audio_recording') {
						nextAudioStatusByBlockId[block.id] = 'idle';
					}
				}
			}
			audioStatusByBlockId = nextAudioStatusByBlockId;

			loading = false;
		} catch (err) {
			console.error('Error loading task:', err);
			error = 'Failed to load task. Please try again.';
			loading = false;
		}
	}

	onMount(() => {
		loadData();
	});

	// Reload on param changes
	$: if ($page.params.taskId && $page.params.taskId !== taskId) {
		loadData();
	}

	onDestroy(() => {
		// Cleanup recording
		if (recordingInterval) {
			clearInterval(recordingInterval);
		}

		if (mediaRecorder && mediaRecorder.state !== 'inactive') {
			try {
				mediaRecorder.stop();
			} catch {
				// ignore
			}
		}

		if (activeStream) {
			try {
				activeStream.getTracks().forEach((t) => t.stop());
			} catch {
				// ignore
			}
			activeStream = null;
		}

		// Revoke object URLs
		for (const url of Object.values(audioPreviewUrlByBlockId)) {
			if (url) URL.revokeObjectURL(url);
		}
	});
</script>

<main class="min-h-screen bg-background">
	{#if loading}
		<div class="flex items-center justify-center min-h-screen">
			<p class="text-sm text-muted-foreground">Loading…</p>
		</div>
	{:else if error}
		<div class="flex items-center justify-center min-h-screen p-6">
			<Card class="border-destructive max-w-md">
				<CardHeader>
					<CardTitle class="text-destructive">Cannot access task</CardTitle>
				</CardHeader>
				<CardContent>
					<p class="text-sm text-muted-foreground mb-4">{error}</p>
					<a
						href={`/join/${studyId}`}
						class="inline-flex items-center justify-center px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
					>
						Return to join
					</a>
				</CardContent>
			</Card>
		</div>
	{:else if task && currentPage}
		<!-- Persistent header -->
		<div class="bg-card border-b border-border">
			<div class="mx-auto max-w-2xl p-4">
				<div class="flex items-center justify-between mb-2">
					<h1 class="text-lg font-semibold truncate">{study?.title || 'Study'}</h1>
				</div>
				<div class="flex items-center justify-between">
					<h2 class="text-sm text-muted-foreground">{task.title}</h2>
					<span class="text-xs text-muted-foreground whitespace-nowrap ml-4">
						Task {taskNumber} of {totalTasks} • Page {currentPageIndex + 1} of {totalPages}
					</span>
				</div>
				<!-- Progress bar -->
				<div class="mt-2 h-1 bg-muted rounded-full overflow-hidden">
					<div
						class="h-full bg-primary transition-all"
						style="width: {((currentPageIndex + 1) / totalPages) * 100}%"
					></div>
				</div>
			</div>
		</div>

		<!-- Current page -->
		<div class="mx-auto max-w-2xl p-6">
			{#key `${taskId}-${currentPageIndex}`}
				<div in:fly={{ x: 16, duration: 180, opacity: 0 }} out:fly={{ x: -16, duration: 120, opacity: 0 }}>
					<Card class="mb-6">
						<CardHeader>
							<CardTitle class="text-lg">{currentPage.title || `Page ${currentPageIndex + 1}`}</CardTitle>
						</CardHeader>
						<CardContent class="space-y-6">
							{#each currentPage.blocks as block}
								<div class="space-y-2">
									{#if block.type === 'text'}
										<p class="text-sm text-foreground whitespace-pre-wrap">{block.content}</p>

									{:else if block.type === 'short_text'}
										<label class="block">
											<span class="text-sm font-medium">
												{block.label}
												{#if block.required}<span class="text-destructive">*</span>{/if}
											</span>
											<input
												type="text"
												value={responses[block.id] ?? ''}
												on:input={(e) => setResponse(block.id, e.target.value)}
												class="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
												placeholder="Your answer…"
											/>
										</label>
										{#if showValidationHint && block.required && (!responses[block.id] || (typeof responses[block.id] === 'string' && responses[block.id].trim() === ''))}
											<p class="text-xs text-destructive">This is required.</p>
										{/if}

									{:else if block.type === 'long_text'}
										<label class="block">
											<span class="text-sm font-medium">
												{block.label}
												{#if block.required}<span class="text-destructive">*</span>{/if}
											</span>
											<textarea
												value={responses[block.id] ?? ''}
												on:input={(e) => setResponse(block.id, e.target.value)}
												rows="4"
												class="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm resize-none"
												placeholder="Your answer…"
											></textarea>
										</label>
										{#if showValidationHint && block.required && (!responses[block.id] || (typeof responses[block.id] === 'string' && responses[block.id].trim() === ''))}
											<p class="text-xs text-destructive">This is required.</p>
										{/if}

									{:else if block.type === 'number'}
										<label class="block">
											<span class="text-sm font-medium">
												{block.label}
												{#if block.required}<span class="text-destructive">*</span>{/if}
											</span>
											<input
												type="number"
												value={responses[block.id] ?? ''}
												on:input={(e) => setResponse(block.id, e.target.value)}
												class="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
												placeholder="Enter a number…"
											/>
										</label>
										{#if showValidationHint && block.required && (!responses[block.id] || (typeof responses[block.id] === 'string' && responses[block.id].trim() === ''))}
											<p class="text-xs text-destructive">This is required.</p>
										{/if}

									{:else if block.type === 'multiple_choice'}
										<fieldset>
											<legend class="text-sm font-medium mb-2">
												{block.label}
												{#if block.required}<span class="text-destructive">*</span>{/if}
											</legend>
											<div class="space-y-2">
												{#each block.options || [] as option}
													<label class="flex items-center gap-2 p-2 border border-input rounded-md cursor-pointer hover:bg-accent {responses[block.id] === option ? 'border-primary bg-primary/5' : ''}">
														<input
															type="radio"
															name={block.id}
															value={option}
															checked={responses[block.id] === option}
															on:change={() => setResponse(block.id, option)}
															class="accent-primary"
														/>
														<span class="text-sm">{option}</span>
													</label>
												{/each}
											</div>
										</fieldset>
										{#if showValidationHint && block.required && !responses[block.id]}
											<p class="text-xs text-destructive">This is required.</p>
										{/if}

									{:else if block.type === 'checkbox'}
										<fieldset>
											<legend class="text-sm font-medium mb-2">
												{block.label}
												{#if block.required}<span class="text-destructive">*</span>{/if}
												<span class="text-xs text-muted-foreground ml-1">(select all that apply)</span>
											</legend>
											<div class="space-y-2">
												{#each block.options || [] as option}
													<label class="flex items-center gap-2 p-2 border border-input rounded-md cursor-pointer hover:bg-accent {(responses[block.id] || []).includes(option) ? 'border-primary bg-primary/5' : ''}">
														<input
															type="checkbox"
															checked={(responses[block.id] || []).includes(option)}
															on:change={(e) => handleCheckboxChange(block.id, option, e.target.checked)}
															class="accent-primary"
														/>
														<span class="text-sm">{option}</span>
													</label>
												{/each}
											</div>
										</fieldset>
										{#if showValidationHint && block.required && (!responses[block.id] || responses[block.id].length === 0)}
											<p class="text-xs text-destructive">This is required.</p>
										{/if}

									{:else if block.type === 'audio_recording'}
										<div>
											<span class="text-sm font-medium block mb-2">
												{block.label}
												{#if block.required}<span class="text-destructive">*</span>{/if}
											</span>

											{#if showValidationHint && block.required && !responses[block.id]?.path}
												<p class="text-xs text-destructive mb-2">This is required.</p>
											{/if}

											{#if (audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle')) === 'recording' && activeRecordingBlockId === block.id}
												<!-- Recording state -->
												<div class="p-4 border-2 border-destructive rounded-md bg-destructive/5">
													<div class="flex items-center justify-between mb-3">
														<div class="flex items-center gap-2">
															<div class="w-3 h-3 bg-destructive rounded-full animate-pulse"></div>
															<span class="text-sm font-medium">Recording</span>
														</div>
														<span class="text-sm font-mono">{formatTime(recordingTimer)} / 0:30</span>
													</div>
													<p class="text-xs text-muted-foreground mb-3">Max 30 seconds. Recording will stop automatically.</p>
													<button
														on:click={stopRecording}
														class="w-full px-4 py-2 bg-destructive text-destructive-foreground rounded-md text-sm font-medium hover:opacity-90"
													>
														Stop recording
													</button>
												</div>

											{:else if (audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle')) === 'uploading'}
												<!-- Uploading state -->
												<div class="p-4 border border-border rounded-md bg-muted/30">
													<div class="flex items-center justify-between">
														<span class="text-sm font-medium">Uploading…</span>
														<span class="text-xs text-muted-foreground">Please don't navigate away</span>
													</div>
												</div>

											{:else if (audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle')) === 'saved' && responses[block.id]}
												<!-- Saved state -->
												<div class="p-4 border border-border rounded-md bg-muted/30 space-y-3">
													<div class="flex items-center justify-between">
														<span class="text-sm font-medium text-green-600">✓ Saved</span>
														<span class="text-xs text-muted-foreground">
															{new Date(responses[block.id].uploadedAt).toLocaleTimeString()}
														</span>
													</div>

													{#if audioErrorByBlockId[block.id]}
														<p class="text-sm text-destructive">{audioErrorByBlockId[block.id]}</p>
													{/if}

													{#if audioPreviewUrlByBlockId[block.id]}
														<audio controls src={audioPreviewUrlByBlockId[block.id]} class="w-full"></audio>
													{/if}

													<button
														on:click={() => handleRerecord(block.id)}
														disabled={isAudioBusyOnCurrentPage}
														class="px-4 py-2 border border-input rounded-md text-sm hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
													>
														Re-record
													</button>
												</div>

											{:else if (audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle')) === 'error'}
												<!-- Error state -->
												<div class="p-4 border border-destructive rounded-md bg-destructive/5 space-y-3">
													<div class="text-sm font-medium text-destructive">Upload failed</div>
													{#if audioErrorByBlockId[block.id]}
														<p class="text-sm text-destructive">{audioErrorByBlockId[block.id]}</p>
													{/if}

													{#if audioPreviewUrlByBlockId[block.id]}
														<audio controls src={audioPreviewUrlByBlockId[block.id]} class="w-full"></audio>
													{/if}

													<div class="flex gap-2">
														<button
															on:click={() => handleRetryUpload(block.id)}
															disabled={isAudioBusyOnCurrentPage}
															class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
														>
															Retry upload
														</button>
														<button
															on:click={() => handleRerecord(block.id)}
															disabled={isAudioBusyOnCurrentPage}
															class="px-4 py-2 border border-input rounded-md text-sm hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
														>
															Re-record
														</button>
													</div>
												</div>

											{:else}
												<!-- Idle state -->
												<div class="p-4 border border-dashed border-input rounded-md">
													<p class="text-sm text-muted-foreground mb-3">
														Record your response. You can listen back and re-record before moving on.
													</p>
													<button
														on:click={() => startRecording(block.id)}
														disabled={isAudioBusyOnCurrentPage}
														class="w-full px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
													>
														<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
															<path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
															<path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
														</svg>
														Start recording
													</button>
												</div>
											{/if}
										</div>

									{:else if block.type === 'media'}
										<!-- Media block -->
										<div class="space-y-3">
											{#if block.items && block.items.length > 0}
												{#each block.items as item}
													<div class="border border-border rounded-md overflow-hidden">
														{#if item.kind === 'image'}
															{#await getTaskMediaUrl(item.path)}
																<div class="p-4 text-sm text-muted-foreground">Loading image…</div>
															{:then imageUrl}
																{#if imageUrl}
																	<img
																		src={imageUrl}
																		alt={item.caption || 'Task media'}
																		class="w-full h-auto"
																	/>
																	{#if item.caption}
																		<div class="p-2 bg-muted/30 text-sm text-muted-foreground">
																			{item.caption}
																		</div>
																	{/if}
																{:else}
																	<div class="p-4 text-sm text-destructive">Failed to load image</div>
																{/if}
															{/await}
														{:else if item.kind === 'pdf'}
															<div class="p-4 flex items-center gap-3">
																<svg class="w-8 h-8 text-muted-foreground" fill="currentColor" viewBox="0 0 24 24">
																	<path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
																</svg>
																<div class="flex-1">
																	<p class="text-sm font-medium">{item.path.split('/').pop()}</p>
																	{#if item.caption}
																		<p class="text-xs text-muted-foreground">{item.caption}</p>
																	{/if}
																</div>
																{#await getTaskMediaUrl(item.path)}
																	<span class="text-xs text-muted-foreground">Loading…</span>
																{:then pdfUrl}
																	{#if pdfUrl}
																		<a
																			href={pdfUrl}
																			target="_blank"
																			rel="noopener noreferrer"
																			class="px-3 py-1 bg-primary text-primary-foreground rounded text-xs font-medium hover:opacity-90"
																		>
																			View PDF
																		</a>
																	{:else}
																		<span class="text-xs text-destructive">Failed to load</span>
																	{/if}
																{/await}
															</div>
														{/if}
													</div>
												{/each}
											{:else}
												<p class="text-sm text-muted-foreground">No media items</p>
											{/if}
										</div>
									{/if}
								</div>
							{/each}
						</CardContent>
					</Card>

					<!-- Navigation -->
					<div class="flex justify-between items-center">
						<button
							on:click={prevPage}
							disabled={isFirstPage || anyAudioBusy}
							class="px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
						>
							← Previous
						</button>

						<div class="flex gap-1">
							{#each Array(totalPages) as _, i}
								<button
									disabled={anyAudioBusy}
									on:click={() => {
										if (anyAudioBusy) return;
										if (i < currentPageIndex || currentPageValid) {
											currentPageIndex = i;
											showValidationHint = false;
										} else {
											showValidationHint = true;
										}
									}}
									class="w-2 h-2 rounded-full {i === currentPageIndex ? 'bg-primary' : i < currentPageIndex ? 'bg-primary/50' : 'bg-muted'} disabled:opacity-50 disabled:cursor-not-allowed"
									aria-label={`Go to page ${i + 1}`}
								></button>
							{/each}
						</div>

						{#if isLastPage}
							<button
								on:click={handleShowConfirm}
								disabled={!allPagesValid || anyAudioBusy}
								class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								Submit
							</button>
						{:else}
							<button
								on:click={nextPage}
								disabled={!currentPageValid || anyAudioBusy}
								class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								Next →
							</button>
						{/if}
					</div>

					{#if showValidationHint && (!allPagesValid || !currentPageValid)}
						<p class="text-sm text-center text-destructive mt-4">Complete required fields to continue.</p>
					{/if}
				</div>
			{/key}
		</div>
	{/if}
</main>

<!-- Confirm Submit Modal -->
{#if showConfirmModal}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		role="button"
		tabindex="0"
		aria-label="Close modal"
		on:click={() => (showConfirmModal = false)}
		on:keydown={(e) => {
			if (e.key === 'Escape') showConfirmModal = false;
		}}
	>
		<div
			role="dialog"
			aria-modal="true"
			tabindex="-1"
			on:click|stopPropagation
			on:keydown|stopPropagation={() => {}}
		>
			<Card class="max-w-md w-full bg-card text-card-foreground border border-border shadow-2xl">
				<CardHeader>
					<CardTitle>Submit your responses?</CardTitle>
				</CardHeader>
				<CardContent class="space-y-4">
					<p class="text-sm text-muted-foreground">
						You're about to submit your responses. This action cannot be undone.
					</p>
					<p class="text-sm text-muted-foreground">
						Make sure you are satisfied with each recording before submitting.
					</p>

					{#if submitError}
						<div class="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
							{submitError}
						</div>
					{/if}

					<div class="flex gap-3 pt-2">
						<button
							on:click={() => (showConfirmModal = false)}
							disabled={submitting}
							class="flex-1 px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
						>
							Review
						</button>
						<button
							on:click={handleSubmit}
							disabled={submitting}
							class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
						>
							{submitting ? 'Submitting…' : 'Confirm'}
						</button>
					</div>
				</CardContent>
			</Card>
		</div>
	</div>
{/if}