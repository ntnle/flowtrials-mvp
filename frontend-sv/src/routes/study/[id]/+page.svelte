<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getStudyById, generateEligibilityQuiz, generateStudySummary, generatePlainTitle } from '$lib/api.js';
  import { createParticipationRequest, getStudyByIdSupabase } from '$lib/supabase.js';
  import { user } from '$lib/authStore';
  import { Card, CardHeader, CardTitle, CardContent } from '$lib/components/ui/card/index.js';

  let studyId = null;
  $: studyId = $page.params.id;

  let study = null;
  let loading = true;
  let error = null;
  let showConfirmModal = false;
  let participationNote = '';
  let submitting = false;
  let submitError = '';
  let isDraft = false;

  // AI feature state
  let aiQuiz = null;
  let aiQuizLoading = false;
  let aiQuizError = '';
  let aiQuizExpanded = false;
  let quizAnswers = {};

  let aiSummary = null;
  let aiSummaryLoading = false;
  let aiSummaryError = '';
  let aiSummaryExpanded = false;

  let aiTitle = null;
  let aiTitleLoading = false;
  let aiTitleError = '';
  let aiTitleExpanded = false;

  let loadedStudyId = null;
  $: if (studyId && studyId !== loadedStudyId) {
    loadedStudyId = studyId;
    loadStudy(studyId);
  }

  // Watch for user state changes and check if we should show modal
  let handledFromSignup = false;
  $: if (!handledFromSignup && $user && $page.url.searchParams.get('fromSignup') === 'true') {
    handledFromSignup = true;
    showConfirmModal = true;
    goto($page.url.pathname, { replaceState: true, keepfocus: true, noScroll: true });
  }

  async function loadStudy(studyId) {
    loading = true;
    error = null;
    study = null;
    isDraft = false;

    try {
      // Try loading from FastAPI first (published studies)
      study = await getStudyById(studyId);

      // Load cached AI content if available
      if (study.ai_plain_title) {
        aiTitle = study.ai_plain_title;
        aiTitleExpanded = true;
      }
      if (study.ai_plain_summary) {
        aiSummary = study.ai_plain_summary;
        aiSummaryExpanded = true;
      }
      if (study.ai_eligibility_quiz) {
        aiQuiz = study.ai_eligibility_quiz;
        aiQuizExpanded = true;
      }

      loading = false;
    } catch (err) {
      console.error("Error loading study from FastAPI:", err);

      // If user is authenticated and FastAPI failed, try Supabase (might be a draft)
      if ($user) {
        try {
          console.log("Attempting to load draft study from Supabase...");
          study = await getStudyByIdSupabase(studyId);
          isDraft = !study.is_published;
          loading = false;
        } catch (supabaseErr) {
          console.error("Error loading study from Supabase:", supabaseErr);
          error = "Failed to load study details";
          loading = false;
        }
      } else {
        error = "Failed to load study details";
        loading = false;
      }
    }
  }

  function handleRequestParticipate() {
    // Check if user is logged in
    if (!$user) {
      // Store the current study ID and redirect to signup
      goto(`/signup?redirect=${encodeURIComponent($page.url.pathname)}`);
      return;
    }

    // User is logged in, show confirmation modal
    showConfirmModal = true;
  }

  async function handleConfirmParticipation() {
    submitting = true;
    submitError = '';

    try {
      console.log('Submitting participation request:', {
        studyId: parseInt(studyId),
        note: participationNote,
        contactPreference: 'email'
      });

      // Create participation request with the study ID as an integer
      await createParticipationRequest(
        parseInt(studyId), // Convert string to integer
        participationNote,
        'email'
      );

      console.log('Participation request successful');
      // Success! Redirect to profile
      goto('/profile?participationSuccess=true');
    } catch (err) {
      console.error('Participation request error:', err);
      console.error('Error details:', err.message, err.code, err.details);
      if (err.message && err.message.includes('already requested')) {
        submitError = 'You have already submitted a request for this study.';
      } else {
        submitError = err.message || 'Unable to submit request. Please try again.';
      }
      submitting = false;
    }
  }

  function handleCancelModal() {
    showConfirmModal = false;
    participationNote = '';
    submitError = '';
  }

  function handleBackToBrowse() {
    goto('/browse');
  }

  // AI Feature Handlers
  async function handleGenerateQuiz() {
    if (!study?.eligibility_criteria) return;

    aiQuizLoading = true;
    aiQuizError = '';
    aiQuizExpanded = true;
    quizAnswers = {};

    try {
      const response = await generateEligibilityQuiz(study.id, study.eligibility_criteria);
      aiQuiz = response.questions;
    } catch (err) {
      console.error('Quiz generation error:', err);
      aiQuizError = err.message || 'Failed to generate quiz. Please try again.';
    } finally {
      aiQuizLoading = false;
    }
  }

  async function handleGenerateSummary() {
    if (!study) return;

    aiSummaryLoading = true;
    aiSummaryError = '';
    aiSummaryExpanded = true;

    try {
      const response = await generateStudySummary(study);
      aiSummary = response.summary;
    } catch (err) {
      console.error('Summary generation error:', err);
      aiSummaryError = err.message || 'Failed to generate summary. Please try again.';
    } finally {
      aiSummaryLoading = false;
    }
  }

  async function handleGenerateTitle() {
    if (!study) return;

    aiTitleLoading = true;
    aiTitleError = '';
    aiTitleExpanded = true;

    try {
      const response = await generatePlainTitle(study);
      aiTitle = response.plain_title;
    } catch (err) {
      console.error('Title generation error:', err);
      aiTitleError = err.message || 'Failed to generate title. Please try again.';
    } finally {
      aiTitleLoading = false;
    }
  }

  function toggleQuiz() {
    aiQuizExpanded = !aiQuizExpanded;
  }

  function toggleSummary() {
    aiSummaryExpanded = !aiSummaryExpanded;
  }

  function toggleTitle() {
    aiTitleExpanded = !aiTitleExpanded;
  }

  // Side navigation scroll handling
  function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // Intervention expand state
  let expandedInterventions = {};

  function toggleIntervention(index) {
    expandedInterventions[index] = !expandedInterventions[index];
    expandedInterventions = expandedInterventions; // Trigger reactivity
  }

  // Read more state for long text sections
  let summaryExpanded = false;
  let eligibilityExpanded = false;
  let descriptionExpanded = false;
  const SUMMARY_PREVIEW_LENGTH = 300;
  const ELIGIBILITY_PREVIEW_LENGTH = 400;
  const DESCRIPTION_PREVIEW_LENGTH = 400;

  function splitEligibilityText(text) {
    if (!text) return { inclusion: [], exclusion: [], other: [] };

    const raw = String(text);
    const lower = raw.toLowerCase();
    const inclusionIdx = lower.indexOf('inclusion criteria');
    const exclusionIdx = lower.indexOf('exclusion criteria');

    let inclusionText = '';
    let exclusionText = '';
    let otherText = '';

    if (inclusionIdx !== -1 && exclusionIdx !== -1) {
      if (inclusionIdx < exclusionIdx) {
        inclusionText = raw.slice(inclusionIdx, exclusionIdx);
        exclusionText = raw.slice(exclusionIdx);
      } else {
        exclusionText = raw.slice(exclusionIdx, inclusionIdx);
        inclusionText = raw.slice(inclusionIdx);
      }
      otherText = raw.slice(0, Math.min(inclusionIdx, exclusionIdx));
    } else if (inclusionIdx !== -1) {
      inclusionText = raw.slice(inclusionIdx);
      otherText = raw.slice(0, inclusionIdx);
    } else if (exclusionIdx !== -1) {
      exclusionText = raw.slice(exclusionIdx);
      otherText = raw.slice(0, exclusionIdx);
    } else {
      otherText = raw;
    }

    const toBullets = (section) => {
      const lines = String(section)
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean)
        .filter((l) => !/^(inclusion|exclusion)\s*criteria:?$/i.test(l));

      const bullets = lines
        .filter((l) => /^([•\-*]|\d+[\).])\s+/.test(l))
        .map((l) => l.replace(/^([•\-*]|\d+[\).])\s+/, '').trim())
        .filter(Boolean);

      if (bullets.length >= 2) return bullets;
      return lines;
    };

    return {
      inclusion: toBullets(inclusionText),
      exclusion: toBullets(exclusionText),
      other: toBullets(otherText)
    };
  }

  $: eligibilityParsed = splitEligibilityText(study?.eligibility_criteria);

  // Quiz pagination state
  let currentQuizQuestion = 0;
  let quizCompleted = false;

  function nextQuestion() {
    if (aiQuiz && currentQuizQuestion < aiQuiz.length - 1) {
      currentQuizQuestion++;
    }
  }

  function previousQuestion() {
    if (currentQuizQuestion > 0) {
      currentQuizQuestion--;
      quizCompleted = false;
    }
  }

  function resetQuiz() {
    currentQuizQuestion = 0;
    quizAnswers = {};
    quizCompleted = false;
  }

  function handleQuizAnswer(answer) {
    quizAnswers[currentQuizQuestion] = answer;
    quizAnswers = quizAnswers; // Trigger reactivity

    // Auto-advance to next question after a brief delay
    setTimeout(() => {
      if (currentQuizQuestion < aiQuiz.length - 1) {
        nextQuestion();
      } else {
        // Mark quiz as completed
        quizCompleted = true;
      }
    }, 300);
  }

  // Calculate eligibility based on quiz answers
  $: eligibilitySummary = (() => {
    if (!quizCompleted || !aiQuiz) return null;

    const answeredCount = Object.keys(quizAnswers).length;
    const yesCount = Object.values(quizAnswers).filter(a => a === 'yes').length;
    const noCount = Object.values(quizAnswers).filter(a => a === 'no').length;
    const unsureCount = Object.values(quizAnswers).filter(a => a === 'unsure').length;

    // Simple heuristic: if more than half are "yes" and no "no" answers, likely eligible
    const likelyEligible = yesCount > aiQuiz.length / 2 && noCount === 0;

    return {
      likelyEligible,
      yesCount,
      noCount,
      unsureCount,
      totalQuestions: aiQuiz.length
    };
  })();
</script>

{#if loading}
  <div class="min-h-screen bg-background">
    <div class="mx-auto max-w-4xl p-6">
      <!-- Loading skeleton -->
      <div class="mb-6">
        <div class="h-8 w-32 bg-muted animate-pulse rounded"></div>
      </div>
      <Card class="mb-6">
        <CardHeader>
          <div class="h-8 w-3/4 bg-muted animate-pulse rounded mb-4"></div>
          <div class="h-6 w-1/4 bg-muted animate-pulse rounded"></div>
        </CardHeader>
      </Card>
      <Card class="mb-6">
        <CardContent class="p-6">
          <div class="h-4 w-full bg-muted animate-pulse rounded mb-2"></div>
          <div class="h-4 w-full bg-muted animate-pulse rounded mb-2"></div>
          <div class="h-4 w-2/3 bg-muted animate-pulse rounded"></div>
        </CardContent>
      </Card>
    </div>
  </div>
{:else if error}
  <div class="min-h-screen bg-background">
    <div class="mx-auto max-w-4xl p-6">
      <Card class="border-destructive">
        <CardHeader>
          <CardTitle class="text-destructive">Error Loading Study</CardTitle>
        </CardHeader>
        <CardContent>
          <p class="text-muted-foreground mb-4">{error}</p>
          <button
            on:click={handleBackToBrowse}
            class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
          >
            Back to Browse
          </button>
        </CardContent>
      </Card>
    </div>
  </div>
{:else if study}
  <div class="min-h-screen bg-background">
    <div class="mx-auto max-w-7xl p-6 flex gap-8">
      <!-- Sticky Side Navigation -->
      <aside class="hidden lg:block w-48 flex-shrink-0">
        <nav class="sticky top-6 space-y-1">
          <button on:click={() => scrollToSection('summary')} class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
            Summary
          </button>
          {#if study.eligibility_criteria}
            <button on:click={() => scrollToSection('eligibility')} class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
              Eligibility
            </button>
          {/if}
          {#if study.interventions && study.interventions.length > 0}
            <button on:click={() => scrollToSection('interventions')} class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
              Interventions
            </button>
          {/if}
          {#if study.locations && study.locations.length > 0}
            <button on:click={() => scrollToSection('locations')} class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
              Locations
            </button>
          {/if}
          {#if study.contacts && study.contacts.length > 0}
            <button on:click={() => scrollToSection('contacts')} class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
              Contacts
            </button>
          {/if}
        </nav>
      </aside>

      <!-- Main Content -->
      <div class="flex-1 min-w-0">
        <!-- Back button -->
        <button
          on:click={handleBackToBrowse}
          class="mb-6 text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
        >
          ← Back to Browse
        </button>

        <!-- Header Section -->
      <Card class="mb-6">
        <CardHeader>
          <div class="flex items-start gap-3 mb-4">
            <CardTitle class="text-2xl flex-1">{study.title}</CardTitle>
            {#if isDraft}
              <span class="px-3 py-1 rounded text-sm font-medium bg-gray-100 text-gray-800 border border-gray-300">
                Draft / Unpublished
              </span>
            {/if}
          </div>

          <!-- AI Plain Title Button -->
          <button
            on:click={handleGenerateTitle}
            disabled={aiTitleLoading}
            class="mb-4 px-3 py-1.5 text-xs font-medium bg-muted hover:bg-muted/80 border border-border rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            <span class="inline-block w-4 h-4 text-center">✨</span>
            {aiTitleLoading ? 'Generating...' : 'Simplify Title (AI)'}
          </button>

          <!-- AI Plain Title Display -->
          {#if aiTitle}
            <div class="mb-4 p-4 bg-muted/50 border-l-4 border-accent rounded-md">
              <div class="flex items-start justify-between gap-2 mb-2">
                <span class="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  <span class="inline-block">✨</span> AI-Generated Plain Title
                </span>
                <button
                  on:click={toggleTitle}
                  class="text-xs text-muted-foreground hover:text-foreground"
                >
                  {aiTitleExpanded ? '▼' : '▶'}
                </button>
              </div>
              {#if aiTitleExpanded}
                <p class="text-base font-semibold text-foreground italic">{aiTitle}</p>
              {/if}
            </div>
          {/if}
          {#if aiTitleError}
            <div class="mb-4 p-3 bg-destructive/10 text-destructive text-sm rounded-md">
              {aiTitleError}
            </div>
          {/if}

          <div class="flex flex-wrap gap-2 items-center">
            {#if study.recruiting_status}
              <span class="px-3 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                {study.recruiting_status}
              </span>
            {/if}
            {#if study.conditions && study.conditions.length > 0}
              {#each study.conditions.slice(0, 5) as condition}
                <span class="px-3 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                  {condition}
                </span>
              {/each}
              {#if study.conditions.length > 5}
                <span class="text-xs text-muted-foreground">
                  +{study.conditions.length - 5} more
                </span>
              {/if}
            {/if}
          </div>
        </CardHeader>
      </Card>

      <!-- Summary Section -->
      {#if study.brief_summary}
        <Card class="mb-6" id="summary">
          <CardHeader>
            <div class="flex items-center justify-between">
              <CardTitle class="text-lg">Summary</CardTitle>
              <button
                on:click={handleGenerateSummary}
                disabled={aiSummaryLoading}
                class="px-3 py-1.5 text-xs font-medium bg-muted hover:bg-muted/80 border border-border rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <span class="inline-block w-4 h-4 text-center">✨</span>
                {aiSummaryLoading ? 'Generating...' : 'AI Summary'}
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <div class="prose prose-sm max-w-prose">
              {#if study.brief_summary.length > SUMMARY_PREVIEW_LENGTH}
                <p class="text-foreground leading-7">
                  {summaryExpanded ? study.brief_summary : study.brief_summary.substring(0, SUMMARY_PREVIEW_LENGTH) + '...'}
                </p>
                <button
                  on:click={() => summaryExpanded = !summaryExpanded}
                  class="mt-2 text-xs text-primary hover:underline"
                >
                  {summaryExpanded ? 'Read less' : 'Read more'}
                </button>
              {:else}
                <p class="text-foreground leading-7">{study.brief_summary}</p>
              {/if}
            </div>

            <!-- AI Study Summary Display -->
            {#if aiSummary}
              <div class="mt-4 p-4 bg-muted/50 border-l-4 border-accent rounded-md">
                <div class="flex items-start justify-between gap-2 mb-2">
                  <span class="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <span class="inline-block">✨</span> AI-Generated Plain Summary
                  </span>
                  <button
                    on:click={toggleSummary}
                    class="text-xs text-muted-foreground hover:text-foreground"
                  >
                    {aiSummaryExpanded ? '▼' : '▶'}
                  </button>
                </div>
                {#if aiSummaryExpanded}
                  <div class="prose prose-sm max-w-prose">
                    <p class="text-foreground leading-7 whitespace-pre-wrap italic">{aiSummary}</p>
                  </div>
                {/if}
              </div>
            {/if}
            {#if aiSummaryError}
              <div class="mt-4 p-3 bg-destructive/10 text-destructive text-sm rounded-md">
                {aiSummaryError}
              </div>
            {/if}
          </CardContent>
        </Card>
      {/if}

      <!-- Detailed Description Section -->
      {#if study.detailed_description}
        <Card class="mb-6">
          <CardHeader>
            <CardTitle class="text-lg">Description</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="prose prose-sm max-w-prose">
              {#if study.detailed_description.length > DESCRIPTION_PREVIEW_LENGTH}
                <p class="text-foreground leading-7 whitespace-pre-wrap">
                  {descriptionExpanded ? study.detailed_description : study.detailed_description.substring(0, DESCRIPTION_PREVIEW_LENGTH) + '...'}
                </p>
                <button
                  on:click={() => descriptionExpanded = !descriptionExpanded}
                  class="mt-2 text-xs text-primary hover:underline"
                >
                  {descriptionExpanded ? 'Read less' : 'Read more'}
                </button>
              {:else}
                <p class="text-foreground leading-7 whitespace-pre-wrap">{study.detailed_description}</p>
              {/if}
            </div>
          </CardContent>
        </Card>
      {/if}

      <!-- Eligibility Criteria Section -->
      {#if study.eligibility_criteria}
        <Card class="mb-6" id="eligibility">
          <CardHeader>
            <div class="flex items-center justify-between">
              <CardTitle class="text-lg">Eligibility Criteria</CardTitle>
              <button
                on:click={handleGenerateQuiz}
                disabled={aiQuizLoading}
                class="px-3 py-1.5 text-xs font-medium bg-muted hover:bg-muted/80 border border-border rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <span class="inline-block w-4 h-4 text-center">✨</span>
                {aiQuizLoading ? 'Generating...' : 'AI Screening'}
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <div class="space-y-4">
              {#if eligibilityParsed.other && eligibilityParsed.other.length > 0}
                <div class="text-sm text-muted-foreground">
                  {#each eligibilityParsed.other.slice(0, 3) as line}
                    <p class="leading-6">{line}</p>
                  {/each}
                </div>
              {/if}

              <div class="grid gap-4 md:grid-cols-2">
                <div class="rounded-md border border-border bg-muted/30 p-4">
                  <div class="flex items-center justify-between mb-3">
                    <div class="text-sm font-semibold text-foreground">Inclusion</div>
                    <span class="text-xs text-muted-foreground">Usually must be true</span>
                  </div>
                  {#if eligibilityParsed.inclusion && eligibilityParsed.inclusion.length > 0}
                    <ul class="space-y-2 text-sm text-foreground">
                      {#each eligibilityParsed.inclusion.slice(0, 12) as item}
                        <li class="flex gap-2">
                          <span class="text-muted-foreground">•</span>
                          <span class="leading-6">{item}</span>
                        </li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="text-sm text-muted-foreground">No inclusion criteria listed.</p>
                  {/if}
                </div>

                <div class="rounded-md border border-border bg-muted/30 p-4">
                  <div class="flex items-center justify-between mb-3">
                    <div class="text-sm font-semibold text-foreground">Exclusion</div>
                    <span class="text-xs text-muted-foreground">Usually means not eligible</span>
                  </div>
                  {#if eligibilityParsed.exclusion && eligibilityParsed.exclusion.length > 0}
                    <ul class="space-y-2 text-sm text-foreground">
                      {#each eligibilityParsed.exclusion.slice(0, 12) as item}
                        <li class="flex gap-2">
                          <span class="text-muted-foreground">•</span>
                          <span class="leading-6">{item}</span>
                        </li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="text-sm text-muted-foreground">No exclusion criteria listed.</p>
                  {/if}
                </div>
              </div>

              <div class="rounded-md border border-border bg-background p-3">
                <button
                  type="button"
                  on:click={() => eligibilityExpanded = !eligibilityExpanded}
                  class="text-xs font-medium text-primary hover:underline"
                >
                  {eligibilityExpanded ? 'Hide original eligibility text' : 'Show original eligibility text'}
                </button>

                {#if eligibilityExpanded}
                  <pre class="mt-3 text-xs text-foreground whitespace-pre-wrap font-sans leading-6">{study.eligibility_criteria}</pre>
                {/if}
              </div>

              <div class="text-xs text-muted-foreground">
                Always confirm with the study team—final eligibility is determined by investigators.
              </div>
            </div>

            <!-- AI Eligibility Quiz Display -->
            {#if aiQuiz}
              <div class="mt-4 p-4 bg-muted/50 border-l-4 border-accent rounded-md">
                <div class="flex items-start justify-between gap-2 mb-3">
                  <span class="text-xs font-medium text-muted-foreground flex items-center gap-1">
                    <span class="inline-block">✨</span> AI-Generated Eligibility Quiz
                  </span>
                  <button
                    on:click={toggleQuiz}
                    class="text-xs text-muted-foreground hover:text-foreground"
                  >
                    {aiQuizExpanded ? '▼' : '▶'}
                  </button>
                </div>
                {#if aiQuizExpanded}
                  <div class="space-y-4">
                    {#if !quizCompleted}
                      <div class="flex items-center justify-between mb-4">
                        <p class="text-xs text-muted-foreground italic">
                          Question {currentQuizQuestion + 1} of {aiQuiz.length}
                        </p>
                        <button
                          on:click={resetQuiz}
                          class="text-xs text-muted-foreground hover:text-foreground"
                        >
                          Reset
                        </button>
                      </div>

                      {#if aiQuiz[currentQuizQuestion]}
                        <div class="p-4 bg-background rounded-md border border-border">
                          <p class="text-sm font-medium text-foreground mb-2">
                            {currentQuizQuestion + 1}. {aiQuiz[currentQuizQuestion].question}
                          </p>
                          {#if aiQuiz[currentQuizQuestion].explanation}
                            <p class="text-xs text-muted-foreground mb-3 italic">
                              {aiQuiz[currentQuizQuestion].explanation}
                            </p>
                          {/if}
                          <div class="flex gap-2">
                            <button
                              on:click={() => handleQuizAnswer('yes')}
                              class="px-3 py-1 text-xs rounded border {quizAnswers[currentQuizQuestion] === 'yes' ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:bg-muted'} transition-colors"
                            >
                              Yes
                            </button>
                            <button
                              on:click={() => handleQuizAnswer('no')}
                              class="px-3 py-1 text-xs rounded border {quizAnswers[currentQuizQuestion] === 'no' ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:bg-muted'} transition-colors"
                            >
                              No
                            </button>
                            <button
                              on:click={() => handleQuizAnswer('unsure')}
                              class="px-3 py-1 text-xs rounded border {quizAnswers[currentQuizQuestion] === 'unsure' ? 'bg-primary text-primary-foreground border-primary' : 'bg-background border-border hover:bg-muted'} transition-colors"
                            >
                              Unsure
                            </button>
                          </div>
                        </div>
                      {/if}

                      <div class="flex justify-between items-center mt-4">
                        <button
                          on:click={previousQuestion}
                          disabled={currentQuizQuestion === 0}
                          class="px-3 py-1.5 text-xs border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted transition-colors"
                        >
                          ← Previous
                        </button>
                        <div class="flex gap-1">
                          {#each aiQuiz as _, idx}
                            <button
                              on:click={() => { currentQuizQuestion = idx; quizCompleted = false; }}
                              aria-label={`Go to question ${idx + 1}`}
                              class="w-2 h-2 rounded-full {idx === currentQuizQuestion ? 'bg-primary' : quizAnswers[idx] ? 'bg-primary/50' : 'bg-muted'} transition-colors"
                            ></button>
                          {/each}
                        </div>
                        <button
                          on:click={nextQuestion}
                          disabled={currentQuizQuestion === aiQuiz.length - 1 || !quizAnswers[currentQuizQuestion]}
                          class="px-3 py-1.5 text-xs border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted transition-colors"
                        >
                          Next →
                        </button>
                      </div>
                    {:else}
                      <!-- Quiz completed - show summary -->
                      <div class="p-4 bg-background rounded-md border border-border">
                        <div class="text-center mb-4">
                          <p class="text-sm font-semibold text-foreground mb-2">Quiz Complete!</p>
                          <div class="flex justify-center gap-4 text-xs text-muted-foreground mb-3">
                            <span>{eligibilitySummary.yesCount} Yes</span>
                            <span>{eligibilitySummary.noCount} No</span>
                            <span>{eligibilitySummary.unsureCount} Unsure</span>
                          </div>
                        </div>

                        {#if eligibilitySummary.likelyEligible}
                          <div class="p-3 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900 rounded-md mb-3">
                            <p class="text-sm text-green-800 dark:text-green-200">
                              <strong>You may be eligible!</strong> Based on your responses, you appear to meet the initial criteria for this study. We recommend contacting the study coordinator to confirm your eligibility and learn more about participation.
                            </p>
                          </div>
                        {:else}
                          <div class="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-md mb-3">
                            <p class="text-sm text-amber-800 dark:text-amber-200">
                              <strong>Eligibility unclear.</strong> Based on your responses, please reach out to the study coordinator to discuss your eligibility. They can provide personalized guidance based on the full eligibility criteria.
                            </p>
                          </div>
                        {/if}

                        <button
                          on:click={resetQuiz}
                          class="w-full px-3 py-2 text-xs border rounded hover:bg-muted transition-colors"
                        >
                          Retake Quiz
                        </button>
                      </div>
                    {/if}

                    <div class="mt-4 p-3 bg-accent/10 border border-accent rounded-md">
                      <p class="text-xs text-foreground">
                        <strong>Note:</strong> This quiz is AI-generated and provides general guidance only. Please review the full eligibility criteria above and contact the study team to confirm your eligibility.
                      </p>
                    </div>
                  </div>
                {/if}
              </div>
            {/if}
            {#if aiQuizError}
              <div class="mt-4 p-3 bg-destructive/10 text-destructive text-sm rounded-md">
                {aiQuizError}
              </div>
            {/if}
          </CardContent>
        </Card>
      {/if}

      <!-- Interventions Section -->
      {#if study.interventions && study.interventions.length > 0}
        <Card class="mb-6" id="interventions">
          <CardHeader>
            <CardTitle class="text-lg">Interventions</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="space-y-2">
              {#each study.interventions as intervention, idx}
                <div class="border border-border rounded-md p-3">
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1">
                      <div class="font-medium text-foreground text-sm">
                        {intervention.intervention_name}
                      </div>
                      {#if intervention.intervention_type}
                        <div class="text-xs text-muted-foreground mt-1">
                          {intervention.intervention_type}
                        </div>
                      {/if}
                      {#if intervention.description && !expandedInterventions[idx]}
                        <div class="text-xs text-muted-foreground mt-2">
                          {intervention.description.substring(0, 100)}{intervention.description.length > 100 ? '...' : ''}
                        </div>
                      {/if}
                    </div>
                    {#if intervention.description && intervention.description.length > 100}
                      <button
                        on:click={() => toggleIntervention(idx)}
                        class="text-xs text-muted-foreground hover:text-foreground px-2"
                      >
                        {expandedInterventions[idx] ? '▼' : '▶'}
                      </button>
                    {/if}
                  </div>
                  {#if intervention.description && expandedInterventions[idx]}
                    <div class="text-xs text-muted-foreground mt-3 pt-3 border-t border-border">
                      {intervention.description}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          </CardContent>
        </Card>
      {/if}

      <!-- Locations Section -->
      {#if study.locations && study.locations.length > 0}
        <Card class="mb-6" id="locations">
          <CardHeader>
            <CardTitle class="text-lg">Locations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul class="space-y-2">
              {#each study.locations as location}
                <li class="text-sm text-foreground">
                  {#if location.facility_name}
                    <span class="font-medium">{location.facility_name}</span>
                    {#if location.city || location.state || location.country}
                      <span class="text-muted-foreground"> - </span>
                    {/if}
                  {/if}
                  <span class="text-muted-foreground">
                    {[location.city, location.state, location.country].filter(Boolean).join(', ')}
                  </span>
                </li>
              {/each}
            </ul>
          </CardContent>
        </Card>
      {:else}
        <Card class="mb-6">
          <CardHeader>
            <CardTitle class="text-lg">Locations</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">No locations listed</p>
          </CardContent>
        </Card>
      {/if}

      <!-- Contacts Section -->
      {#if study.contacts && study.contacts.length > 0}
        <Card class="mb-6" id="contacts">
          <CardHeader>
            <CardTitle class="text-lg">Contacts</CardTitle>
          </CardHeader>
          <CardContent>
            <ul class="space-y-3">
              {#each study.contacts as contact}
                <li class="text-sm">
                  <div class="font-medium text-foreground">
                    {contact.name}
                    {#if contact.role}
                      <span class="text-muted-foreground font-normal">({contact.role})</span>
                    {/if}
                  </div>
                  <div class="text-muted-foreground mt-1 space-y-1">
                    {#if contact.phone}
                      <div>Phone: {contact.phone}</div>
                    {/if}
                    {#if contact.email}
                      <div>Email: {contact.email}</div>
                    {/if}
                  </div>
                </li>
              {/each}
            </ul>
          </CardContent>
        </Card>
      {/if}

      <!-- Action Buttons -->
      <Card class="mb-6">
        <CardContent class="p-6">
          <button
            on:click={handleRequestParticipate}
            class="w-full px-6 py-3 bg-primary text-primary-foreground rounded-md font-semibold hover:opacity-90 transition-opacity"
          >
            Participate
          </button>
        </CardContent>
      </Card>

        <!-- Metadata footer -->
        <div class="text-xs text-muted-foreground text-center pb-6">
          <div>Study ID: {study.id}</div>
          {#if study.source === 'ctgov' && study.source_id}
            <div class="mt-1">ClinicalTrials.gov ID: {study.source_id}</div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Confirmation Modal -->
{#if showConfirmModal}
  <div
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    role="button"
    tabindex="0"
    aria-label="Close participation modal"
    on:click={handleCancelModal}
    on:keydown={(e) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') handleCancelModal();
    }}
  >
    <div
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown|stopPropagation={() => {}}
    >
      <Card class="max-w-lg w-full bg-card text-card-foreground border border-border shadow-2xl">
        <CardHeader>
          <CardTitle>Confirm Participation</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
        <p class="text-sm text-muted-foreground">
          The study team will review your request and contact you if you're eligible.
        </p>

        <div class="space-y-2">
          <label for="note" class="text-sm font-medium">
            Optional Note for Researchers
          </label>
          <textarea
            id="note"
            bind:value={participationNote}
            placeholder="Add any relevant information (medications, availability, questions, etc.)"
            rows="4"
            disabled={submitting}
            class="w-full px-3 py-2 text-sm border border-input rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          ></textarea>
        </div>

        {#if submitError}
          <div class="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
            {submitError}
          </div>
        {/if}

        <div class="flex gap-3 pt-2">
          <button
            on:click={handleCancelModal}
            disabled={submitting}
            class="flex-1 px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            on:click={handleConfirmParticipation}
            disabled={submitting}
            class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Confirm Participation'}
          </button>
        </div>
        </CardContent>
      </Card>
    </div>
  </div>
{/if}
