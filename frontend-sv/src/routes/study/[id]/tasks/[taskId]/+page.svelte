<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getStudyByIdSupabase, getMyParticipationForStudy, getMyTaskSubmissions, submitTaskResponse } from '$lib/supabase.js';
  import { getStudyById } from '$lib/api.js';
  import { user } from '$lib/authStore';
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

    // Must be logged in
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
      if (block.required && !responses[block.id]) {
        return false;
      }
      if (block.required && block.type === 'checkbox' && (!responses[block.id] || responses[block.id].length === 0)) {
        return false;
      }
    }
    return true;
  }

  $: currentPageValid = validateCurrentPage();

  function nextPage() {
    if (!currentPageValid) {
      alert('Please complete all required fields before continuing.');
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
      alert('Please complete all required fields before submitting.');
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
              {/if}
            </div>
          {/each}
        </CardContent>
      </Card>

      <!-- Navigation -->
      <div class="flex justify-between items-center">
        <button
          on:click={prevPage}
          disabled={isFirstPage}
          class="px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ← Previous
        </button>

        <div class="flex gap-1">
          {#each Array(totalPages) as _, i}
            <button
              on:click={() => { if (i < currentPageIndex || currentPageValid) currentPageIndex = i; }}
              class="w-2 h-2 rounded-full {i === currentPageIndex ? 'bg-primary' : i < currentPageIndex ? 'bg-primary/50' : 'bg-muted'}"
              aria-label={`Go to page ${i + 1}`}
            ></button>
          {/each}
        </div>

        {#if isLastPage}
          <button
            on:click={handleShowConfirm}
            disabled={!currentPageValid}
            class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Submit
          </button>
        {:else}
          <button
            on:click={nextPage}
            disabled={!currentPageValid}
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
          <CardTitle>Submit Survey?</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <p class="text-sm text-muted-foreground">
            You're about to submit your responses. This action cannot be undone.
          </p>
          <p class="text-sm text-muted-foreground">
            Please review your answers before submitting.
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
