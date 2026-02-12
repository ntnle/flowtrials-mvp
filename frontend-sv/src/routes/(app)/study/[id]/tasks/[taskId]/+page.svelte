<script>
  import { onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getStudyByIdSupabase, getMyParticipationForStudy, getMyTaskSubmissions, submitTaskResponse, uploadAudioRecording, deleteAudioRecording, getTaskMediaUrl } from '$lib/supabase.js';
  import { getStudyById } from '$lib/api.js';
  import { user, loading as authLoading } from '$lib/authStore.js';
  import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card/index.js';

  let studyId = null;
  let taskId = null;
  $: studyId = $page.params.id;
  $: taskId = $page.params.taskId;

  let study = null;
  let task = null;
  let loading = true;
  let error = null;
  let myParticipation = null;
  let alreadySubmitted = false;

  // Survey state
  let currentPageIndex = 0;
  let responses = {}; // keyed by block id
  let showConfirmModal = false;
  let submitting = false;
  let submitError = '';
  let showValidationHint = false;

  // Audio recording state
  const MAX_RECORDING_SECONDS = 30;

  /** @type {Record<string, string|null>} */
  let audioPreviewUrlByBlockId = {};
  /** @type {Record<string, 'idle'|'recording'|'uploading'|'saved'|'error'>} */
  let audioStatusByBlockId = {};
  /** @type {Record<string, string|null>} */
  let audioErrorByBlockId = {};
  /** @type {Record<string, Blob|null>} */
  let audioBlobByBlockId = {};

  /** @type {Record<string, string|null>} */
  let pendingDeletePathByBlockId = {};

  let activeRecordingBlockId = null;
  let activeUploadingBlockId = null;

  let mediaRecorder = null;
  let activeStream = null;
  let audioChunks = [];
  let recordingTimer = 0;
  let recordingInterval = null;
  let stopInProgress = false;

  let loadedKey = null;
  $: {
    const key = `${studyId}-${taskId}`;
    if (key !== loadedKey && studyId && taskId) {
      loadedKey = key;
      loadData(studyId, taskId);
    }
  }

  async function loadData(studyId, taskId) {
    loading = true;
    error = null;

    // Must be logged in (but don't redirect until auth initialization completes)
    if ($authLoading) {
      const unsubscribe = authLoading.subscribe((isLoading) => {
        if (isLoading) return;
        unsubscribe();
        loadData(studyId, taskId);
      });
      return;
    }

    if (!$user) {
      goto(`/login?redirect=${encodeURIComponent($page.url.pathname)}`);
      return;
    }

    try {
      // Load participation status
      myParticipation = await getMyParticipationForStudy(studyId);

      // Check access: must be approved + consent acknowledged
      if (!myParticipation || myParticipation.status !== 'approved' || !myParticipation.consent_acknowledged_at) {
        error = 'You must be approved and have acknowledged consent to access study tasks.';
        loading = false;
        return;
      }

      // Load study
      try {
        study = await getStudyById(studyId);
      } catch {
        study = await getStudyByIdSupabase(studyId);
      }

      // Find the task
      task = study.tasks?.find(t => t.id === taskId);
      if (!task) {
        error = 'Task not found.';
        loading = false;
        return;
      }

      // Check if already submitted
      const submissions = await getMyTaskSubmissions(studyId);
      alreadySubmitted = submissions.some(s => s.task_id === taskId);

      if (alreadySubmitted) {
        error = 'You have already completed this task.';
      }

    } catch (err) {
      console.error('Error loading task:', err);
      error = 'Failed to load task.';
    } finally {
      loading = false;
    }
  }

  // Current page
  $: currentPage = task?.pages?.[currentPageIndex] || null;
  $: totalPages = task?.pages?.length || 0;
  $: isLastPage = currentPageIndex === totalPages - 1;
  $: isFirstPage = currentPageIndex === 0;

  // Validation
  function validateCurrentPage() {
    if (!currentPage) return true;

    for (const block of currentPage.blocks) {
      if (block.required && block.type === 'checkbox' && (!responses[block.id] || responses[block.id].length === 0)) {
        return false;
      }
      if (block.required && block.type === 'audio_recording') {
        const status = audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle');
        if (!responses[block.id]?.path) return false;
        if (status === 'recording' || status === 'uploading') return false;
        continue;
      }
      if (block.required && !responses[block.id]) return false;
    }
    return true;
  }

  $: currentPageValid = validateCurrentPage();

  $: isAudioBusyOnCurrentPage = Boolean(
    currentPage?.blocks?.some(
      (b) => b.type === 'audio_recording' && (audioStatusByBlockId[b.id] === 'recording' || audioStatusByBlockId[b.id] === 'uploading')
    )
  );

  function nextPage() {
    if (!currentPageValid) {
      showValidationHint = true;
      return;
    }
    if (currentPageIndex < totalPages - 1) {
      currentPageIndex++;
    }
  }

  function prevPage() {
    if (currentPageIndex > 0) {
      currentPageIndex--;
    }
  }

  function handleShowConfirm() {
    if (!currentPageValid) {
      showValidationHint = true;
      return;
    }
    showConfirmModal = true;
  }

  async function handleSubmit() {
    submitting = true;
    submitError = '';

    try {
      await submitTaskResponse(parseInt(studyId), taskId, responses);
      goto(`/study/${studyId}/tasks?submitted=true`);
    } catch (err) {
      console.error('Submit error:', err);
      submitError = err.message || 'Failed to submit. Please try again.';
    } finally {
      submitting = false;
    }
  }

  function handleCheckboxChange(blockId, option, checked) {
    const current = responses[blockId] || [];
    if (checked) {
      responses[blockId] = [...current, option];
    } else {
      responses[blockId] = current.filter(o => o !== option);
    }
    responses = responses; // trigger reactivity
  }

  function revokePreviewUrl(blockId) {
    const url = audioPreviewUrlByBlockId[blockId];
    if (url) URL.revokeObjectURL(url);
    audioPreviewUrlByBlockId = { ...audioPreviewUrlByBlockId, [blockId]: null };
  }

  function setAudioStatus(blockId, status) {
    audioStatusByBlockId = { ...audioStatusByBlockId, [blockId]: status };
  }

  function setAudioError(blockId, message) {
    audioErrorByBlockId = { ...audioErrorByBlockId, [blockId]: message };
  }

  async function uploadBlobForBlock(blockId, audioBlob) {
    activeUploadingBlockId = blockId;
    setAudioStatus(blockId, 'uploading');
    setAudioError(blockId, null);

    try {
      const metadata = await uploadAudioRecording(parseInt(studyId), myParticipation.id, audioBlob);

      const priorPathToDelete = pendingDeletePathByBlockId[blockId];
      responses[blockId] = metadata;
      responses = responses; // trigger reactivity
      setAudioStatus(blockId, 'saved');

      if (priorPathToDelete && priorPathToDelete !== metadata.path) {
        try {
          await deleteAudioRecording(priorPathToDelete);
        } catch (err) {
          // Best-effort delete; ignore failures.
          console.warn('Failed to delete prior recording:', err);
        }
      }

      pendingDeletePathByBlockId = { ...pendingDeletePathByBlockId, [blockId]: null };
    } catch (err) {
      console.error('Upload error:', err);

      // Safer re-record behavior: if a previous recording exists, keep it as the valid saved response.
      if (responses?.[blockId]) {
        setAudioStatus(blockId, 'saved');
        setAudioError(blockId, err?.message || 'Upload failed. Your previous recording is still saved.');
      } else {
        setAudioStatus(blockId, 'error');
        setAudioError(blockId, err?.message || 'Failed to upload. You can retry or re-record.');
      }
    } finally {
      activeUploadingBlockId = null;
    }
  }

  // Audio recording functions
  async function startRecording(blockId) {
    try {
      if (activeRecordingBlockId || activeUploadingBlockId) return;

      showValidationHint = false;
      setAudioError(blockId, null);
      setAudioStatus(blockId, 'recording');

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      activeStream = stream;
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunks = [];
      activeRecordingBlockId = blockId;
      recordingTimer = 0;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        audioBlobByBlockId = { ...audioBlobByBlockId, [blockId]: audioBlob };

        const existingPreview = audioPreviewUrlByBlockId[blockId];
        if (existingPreview) URL.revokeObjectURL(existingPreview);
        const previewUrl = URL.createObjectURL(audioBlob);
        audioPreviewUrlByBlockId = { ...audioPreviewUrlByBlockId, [blockId]: previewUrl };

        activeRecordingBlockId = null;

        if (recordingInterval) {
          clearInterval(recordingInterval);
          recordingInterval = null;
        }

        await uploadBlobForBlock(blockId, audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
        activeStream = null;
        mediaRecorder = null;
        stopInProgress = false;
      };

      mediaRecorder.start();

      // Update timer every second
      recordingInterval = setInterval(() => {
        recordingTimer = Math.min(recordingTimer + 1, MAX_RECORDING_SECONDS);
        if (recordingTimer >= MAX_RECORDING_SECONDS) {
          stopRecording();
        }
      }, 1000);

    } catch (err) {
      console.error('Microphone access error:', err);
      setAudioStatus(blockId, 'error');
      setAudioError(blockId, 'Could not access your microphone. Check browser permissions and try again.');
      activeRecordingBlockId = null;
    }
  }

  function stopRecording() {
    if (stopInProgress) return;
    if (!mediaRecorder) return;
    if (mediaRecorder.state === 'inactive') return;

    stopInProgress = true;
    try {
      if (recordingInterval) {
        clearInterval(recordingInterval);
        recordingInterval = null;
      }
      mediaRecorder.stop();
    } catch (err) {
      console.error('Stop recording error:', err);
      stopInProgress = false;
    }
  }

  async function handleRerecord(blockId) {
    showValidationHint = false;

    const existingPath = responses?.[blockId]?.path;
    if (existingPath) {
      pendingDeletePathByBlockId = { ...pendingDeletePathByBlockId, [blockId]: existingPath };
    }

    // Clear local preview + blob for the new attempt; keep the previous uploaded response until the new upload succeeds.
    if (audioPreviewUrlByBlockId[blockId]) revokePreviewUrl(blockId);
    audioBlobByBlockId = { ...audioBlobByBlockId, [blockId]: null };
    setAudioError(blockId, null);

    await startRecording(blockId);
  }

  async function handleRetryUpload(blockId) {
    const audioBlob = audioBlobByBlockId[blockId];
    if (!audioBlob) {
      setAudioStatus(blockId, 'error');
      setAudioError(blockId, 'Nothing to upload yet. Please record again.');
      return;
    }

    await uploadBlobForBlock(blockId, audioBlob);
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  onDestroy(() => {
    try {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    } catch {
      // ignore
    }

    if (recordingInterval) {
      clearInterval(recordingInterval);
      recordingInterval = null;
    }

    if (activeStream) {
      try {
        activeStream.getTracks().forEach((t) => t.stop());
      } catch {
        // ignore
      }
      activeStream = null;
    }

    for (const url of Object.values(audioPreviewUrlByBlockId)) {
      if (url) URL.revokeObjectURL(url);
    }
  });
</script>

<main class="min-h-screen bg-background p-6">
  <div class="mx-auto max-w-2xl">
    <!-- Back button -->
    <button
      on:click={() => goto(`/study/${studyId}/tasks`)}
      class="mb-6 text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
    >
      ← Back to Tasks
    </button>

    {#if loading}
      <Card>
        <CardContent class="p-8 text-center">
          <p class="text-muted-foreground">Loading task...</p>
        </CardContent>
      </Card>
    {:else if error}
      <Card class="border-destructive">
        <CardHeader>
          <CardTitle class="text-destructive">Cannot Access Task</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="text-muted-foreground mb-4">{error}</p>
          <button
            on:click={() => goto(`/study/${studyId}/tasks`)}
            class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
          >
            Return to Tasks
          </button>
        </CardContent>
      </Card>
    {:else if task && currentPage}
      <!-- Task header -->
      <Card class="mb-4">
        <CardContent class="p-4">
          <div class="flex justify-between items-center">
            <h1 class="font-semibold">{task.title}</h1>
            <span class="text-sm text-muted-foreground">
              Page {currentPageIndex + 1} of {totalPages}
            </span>
          </div>
          <!-- Progress bar -->
          <div class="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div
              class="h-full bg-primary transition-all"
              style="width: {((currentPageIndex + 1) / totalPages) * 100}%"
            ></div>
          </div>
        </CardContent>
      </Card>

      <!-- Current page -->
      <Card class="mb-4">
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
                    bind:value={responses[block.id]}
                    class="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    placeholder="Your answer..."
                  />
                </label>
              {:else if block.type === 'long_text'}
                <label class="block">
                  <span class="text-sm font-medium">
                    {block.label}
                    {#if block.required}<span class="text-destructive">*</span>{/if}
                  </span>
                  <textarea
                    bind:value={responses[block.id]}
                    rows="4"
                    class="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm resize-none"
                    placeholder="Your answer..."
                  ></textarea>
                </label>
              {:else if block.type === 'number'}
                <label class="block">
                  <span class="text-sm font-medium">
                    {block.label}
                    {#if block.required}<span class="text-destructive">*</span>{/if}
                  </span>
                  <input
                    type="number"
                    bind:value={responses[block.id]}
                    class="mt-1 w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    placeholder="Enter a number..."
                  />
                </label>
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
                          bind:group={responses[block.id]}
                          class="accent-primary"
                        />
                        <span class="text-sm">{option}</span>
                      </label>
                    {/each}
                  </div>
                </fieldset>
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
              {:else if block.type === 'audio_recording'}
                <div>
                  <span class="text-sm font-medium block mb-2">
                    {block.label}
                    {#if block.required}<span class="text-destructive">*</span>{/if}
                  </span>

                  {#if showValidationHint && block.required && !responses[block.id]?.path}
                    <p class="text-xs text-destructive">This is required.</p>
                  {/if}

                  {#if (audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle')) === 'recording' && activeRecordingBlockId === block.id}
                    <!-- Recording -->
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
                    <!-- Uploading -->
                    <div class="p-4 border border-border rounded-md bg-muted/30">
                      <div class="flex items-center justify-between">
                        <span class="text-sm font-medium">Uploading…</span>
                        <span class="text-xs text-muted-foreground">Please don’t navigate away</span>
                      </div>
                    </div>
                  {:else if (audioStatusByBlockId[block.id] || (responses[block.id] ? 'saved' : 'idle')) === 'saved' && responses[block.id]}
                    <!-- Saved -->
                    <div class="p-4 border border-border rounded-md bg-muted/30 space-y-3">
                      <div class="flex items-center justify-between">
                        <span class="text-sm font-medium">Saved</span>
                        <span class="text-xs text-muted-foreground">
                          Uploaded {new Date(responses[block.id].uploadedAt).toLocaleString()}
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
                    <!-- Error -->
                    <div class="p-4 border border-destructive rounded-md bg-destructive/5 space-y-3">
                      <div class="text-sm font-medium text-destructive">Error</div>
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
                    <!-- Idle -->
                    <div class="p-4 border border-dashed border-input rounded-md">
                      <p class="text-sm text-muted-foreground mb-3">
                        Record a single high-quality clip. You can listen back and re-record before submitting.
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
                <!-- Media block (images and PDFs) -->
                <div class="space-y-3">
                  {#if block.items && block.items.length > 0}
                    {#each block.items as item}
                      <div class="border border-border rounded-md overflow-hidden">
                        {#if item.kind === 'image'}
                          {#await getTaskMediaUrl(item.path)}
                            <div class="p-4 text-sm text-muted-foreground">Loading image...</div>
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
                              <span class="text-xs text-muted-foreground">Loading...</span>
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
          disabled={isFirstPage || isAudioBusyOnCurrentPage}
          class="px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ← Previous
        </button>

        <div class="flex gap-1">
          {#each Array(totalPages) as _, i}
            <button
              disabled={isAudioBusyOnCurrentPage}
              on:click={() => {
                if (isAudioBusyOnCurrentPage) return;
                if (i < currentPageIndex || currentPageValid) currentPageIndex = i;
                else showValidationHint = true;
              }}
              class="w-2 h-2 rounded-full {i === currentPageIndex ? 'bg-primary' : i < currentPageIndex ? 'bg-primary/50' : 'bg-muted'} disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={`Go to page ${i + 1}`}
            ></button>
          {/each}
        </div>

        {#if showValidationHint && !currentPageValid}
          <p class="text-xs text-destructive">Complete required fields to continue.</p>
        {/if}

        {#if isLastPage}
          <button
            on:click={handleShowConfirm}
            disabled={!currentPageValid || isAudioBusyOnCurrentPage}
            class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Submit
          </button>
        {:else}
          <button
            on:click={nextPage}
            disabled={!currentPageValid || isAudioBusyOnCurrentPage}
            class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        {/if}
      </div>
    {/if}
  </div>
</main>

<!-- Confirm Submit Modal -->
{#if showConfirmModal}
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    role="button"
    tabindex="0"
    aria-label="Close modal"
    on:click={() => showConfirmModal = false}
    on:keydown={(e) => { if (e.key === 'Escape') showConfirmModal = false; }}
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
          <CardTitle>{study?.join_flow_key === 'slp-2026' ? 'Submit final recordings?' : 'Submit responses?'}</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <p class="text-sm text-muted-foreground">
            You're about to submit your responses. This action cannot be undone.
          </p>
          <p class="text-sm text-muted-foreground">
            {study?.join_flow_key === 'slp-2026'
              ? 'Make sure you are satisfied with each recording before submitting.'
              : 'Please review your answers before submitting.'}
          </p>

          {#if submitError}
            <div class="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
              {submitError}
            </div>
          {/if}

          <div class="flex gap-3 pt-2">
            <button
              on:click={() => showConfirmModal = false}
              disabled={submitting}
              class="flex-1 px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              Review Answers
            </button>
            <button
              on:click={handleSubmit}
              disabled={submitting}
              class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Confirm Submit'}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
{/if}
