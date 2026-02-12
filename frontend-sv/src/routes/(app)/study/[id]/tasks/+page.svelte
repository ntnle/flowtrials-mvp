<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getStudyByIdSupabase, getMyParticipationForStudy, getMyTaskSubmissions } from '$lib/supabase.js';
  import { getStudyById } from '$lib/api.js';
  import { user, loading as authLoading } from '$lib/authStore.js';
  import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card/index.js';

  let studyId = null;
  $: studyId = $page.params.id;

  let study = null;
  let loading = true;
  let error = null;
  let myParticipation = null;
  let mySubmissions = [];

  let loadedStudyId = null;
  $: if (studyId && studyId !== loadedStudyId) {
    loadedStudyId = studyId;
    loadData(studyId);
  }

  async function loadData(studyId) {
    loading = true;
    error = null;

    // Must be logged in (but don't redirect until auth initialization completes)
    if ($authLoading) {
      const unsubscribe = authLoading.subscribe((isLoading) => {
        if (isLoading) return;
        unsubscribe();
        loadData(studyId);
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

      // Load study (try FastAPI first, fallback to Supabase)
      try {
        study = await getStudyById(studyId);
      } catch {
        study = await getStudyByIdSupabase(studyId);
      }

      // Load my submissions
      mySubmissions = await getMyTaskSubmissions(studyId);

    } catch (err) {
      console.error('Error loading tasks:', err);
      error = 'Failed to load study tasks.';
    } finally {
      loading = false;
    }
  }

  function isTaskCompleted(taskId) {
    return mySubmissions.some(s => s.task_id === taskId);
  }

  function getSubmissionDate(taskId) {
    const submission = mySubmissions.find(s => s.task_id === taskId);
    return submission ? new Date(submission.submitted_at).toLocaleDateString() : null;
  }
</script>

<main class="min-h-screen bg-background p-6">
  <div class="mx-auto max-w-3xl">
    <!-- Back button -->
    <button
      on:click={() => goto(`/study/${studyId}`)}
      class="mb-6 text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
    >
      ← Back to Study
    </button>

    {#if loading}
      <Card>
        <CardContent class="p-8 text-center">
          <p class="text-muted-foreground">Loading tasks...</p>
        </CardContent>
      </Card>
    {:else if error}
      <Card class="border-destructive">
        <CardHeader>
          <CardTitle class="text-destructive">Access Denied</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="text-muted-foreground mb-4">{error}</p>
          <button
            on:click={() => goto(`/study/${studyId}`)}
            class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
          >
            Return to Study
          </button>
        </CardContent>
      </Card>
    {:else if study}
      <Card class="mb-6">
        <CardHeader>
          <CardTitle>Study Tasks</CardTitle>
          <p class="text-sm text-muted-foreground">{study.title}</p>
        </CardHeader>
      </Card>

      {#if !study.tasks || study.tasks.length === 0}
        <Card>
          <CardContent class="p-8 text-center">
            <p class="text-muted-foreground">No tasks available for this study yet.</p>
            <p class="text-sm text-muted-foreground mt-2">Check back later for surveys and activities.</p>
          </CardContent>
        </Card>
      {:else}
        <div class="space-y-3">
          {#each study.tasks as task, index}
            {@const completed = isTaskCompleted(task.id)}
            {@const submissionDate = getSubmissionDate(task.id)}
            <Card class="{completed ? 'border-green-200 dark:border-green-900' : ''}">
              <CardContent class="p-4">
                <div class="flex justify-between items-center">
                  <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="font-medium">{task.title}</span>
                      {#if completed}
                        <span class="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                          Completed
                        </span>
                      {:else}
                        <span class="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                          Pending
                        </span>
                      {/if}
                    </div>
                    <p class="text-xs text-muted-foreground">
                      {task.pages?.length || 0} page(s)
                      {#if submissionDate}
                        · Submitted {submissionDate}
                      {/if}
                    </p>
                  </div>
                  <div>
                    {#if completed}
                      <span class="text-sm text-muted-foreground">Done</span>
                    {:else}
                      <button
                        on:click={() => goto(`/study/${studyId}/tasks/${task.id}`)}
                        class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
                      >
                        Start
                      </button>
                    {/if}
                  </div>
                </div>
              </CardContent>
            </Card>
          {/each}
        </div>

        <!-- Progress summary -->
        <Card class="mt-6">
          <CardContent class="p-4">
            <div class="flex justify-between items-center text-sm">
              <span class="text-muted-foreground">Progress</span>
              <span class="font-medium">
                {mySubmissions.length} / {study.tasks.length} tasks completed
              </span>
            </div>
            <div class="mt-2 h-2 bg-muted rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all"
                style="width: {study.tasks.length > 0 ? (mySubmissions.length / study.tasks.length * 100) : 0}%"
              ></div>
            </div>
          </CardContent>
        </Card>
      {/if}
    {/if}
  </div>
</main>
