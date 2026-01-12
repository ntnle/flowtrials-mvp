<script>
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { onMount } from 'svelte';
  import { push, querystring } from "svelte-spa-router";
  import { searchStudies, generatePlainTitle, getStudyById } from "$lib/api.js";

  let searchQuery = '';
  let zipCode = '';
  let studies = [];
  let loading = true;
  let currentPage = 1;
  let totalStudies = 0;
  const pageSize = 10;

  // Track AI generation state per study
  let aiTitleGenerating = {};

  async function fetchStudies(query, page = 1) {
    try {
      loading = true;
      const zip = zipCode.trim() || null;
      const response = await searchStudies(query || "", page, pageSize, zip);
      studies = response.items.map(item => ({
        id: item.study_id,
        title: item.title,
        plainTitle: item.plain_title,
        snippet: item.snippet,
        score: item.score,
        reasons: item.reasons,
        recruitingStatus: item.recruiting_status,
        studyType: item.study_type,
        conditions: item.conditions || [],
        locationsSummary: item.locations_summary
      }));
      totalStudies = response.total;
      currentPage = page;
      loading = false;

      // Trigger AI generation for studies without plainTitle
      studies.forEach(study => {
        if (!study.plainTitle) {
          generateAITitle(study.id);
        }
      });
    } catch (error) {
      console.error("Error fetching studies:", error);
      studies = [];
      totalStudies = 0;
      loading = false;
    }
  }

  async function generateAITitle(studyId) {
    if (aiTitleGenerating[studyId]) return; // Already generating

    aiTitleGenerating[studyId] = true;
    aiTitleGenerating = aiTitleGenerating; // Trigger reactivity

    try {
      // Fetch full study data
      const fullStudy = await getStudyById(studyId);

      // Generate plain title
      const response = await generatePlainTitle(fullStudy);

      // Update the study in the list
      studies = studies.map(s =>
        s.id === studyId
          ? { ...s, plainTitle: response.plain_title }
          : s
      );
    } catch (error) {
      console.error(`Failed to generate AI title for study ${studyId}:`, error);
    } finally {
      aiTitleGenerating[studyId] = false;
      aiTitleGenerating = aiTitleGenerating; // Trigger reactivity
    }
  }

  onMount(() => {
    const params = new URLSearchParams($querystring);
    searchQuery = params.get('q') || '';
    fetchStudies(searchQuery, 1);
  });

  function handleSearch() {
    push(`/browse?q=${encodeURIComponent(searchQuery)}`);
    fetchStudies(searchQuery, 1);
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }

  function handleNextPage() {
    if (currentPage * pageSize < totalStudies) {
      fetchStudies(searchQuery, currentPage + 1);
    }
  }

  function handlePrevPage() {
    if (currentPage > 1) {
      fetchStudies(searchQuery, currentPage - 1);
    }
  }

  $: startIdx = (currentPage - 1) * pageSize + 1;
  $: endIdx = Math.min(currentPage * pageSize, totalStudies);
  $: totalPages = Math.ceil(totalStudies / pageSize);
</script>

<main class="min-h-screen bg-background">
  <!-- Header with search -->
  <div class="border-b bg-card sticky top-0 z-10">
    <div class="mx-auto max-w-5xl p-4">
      <div class="flex items-center gap-3">
        <button
          on:click={() => push('/')}
          class="text-2xl hover:opacity-70 transition-opacity"
        >
          ←
        </button>
        <div class="flex-1">
          <Input
            bind:value={searchQuery}
            on:keydown={handleKeydown}
            placeholder="Search by condition or keyword..."
            class="h-10"
          />
        </div>
        <div class="flex flex-col gap-1">
          <Input
            bind:value={zipCode}
            on:keydown={handleKeydown}
            placeholder="ZIP (optional)"
            class="h-10 w-32"
            maxlength="5"
          />
        </div>
        <button
          on:click={handleSearch}
          class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
        >
          Search
        </button>
      </div>
    </div>
  </div>

  <!-- Results -->
  <div class="mx-auto max-w-5xl p-6">
    {#if loading}
      <div class="text-center py-12">
        <p class="text-muted-foreground">Loading studies...</p>
      </div>
    {:else if studies.length === 0 && totalStudies === 0}
      <div class="text-center py-12 space-y-4">
        <div class="text-4xl">🔍</div>
        <div>
          <h3 class="text-lg font-semibold mb-2">No studies found</h3>
          <p class="text-sm text-muted-foreground">
            Try searching for a different condition or term.
          </p>
        </div>
        <button
          on:click={() => push('/')}
          class="px-4 py-2 border rounded-md text-sm font-medium hover:bg-accent"
        >
          Start Over
        </button>
      </div>
    {:else}
      <div class="mb-4 flex items-center justify-between">
        <p class="text-sm text-muted-foreground">
          {#if totalStudies > 0}
            Showing {startIdx}–{endIdx} of {totalStudies} {totalStudies === 1 ? 'study' : 'studies'}
            {#if searchQuery}
              for "{searchQuery}"
            {/if}
          {/if}
        </p>
      </div>

      <div class="grid gap-4">
        {#each studies as study}
          <button type="button" on:click={() => push(`/study/${study.id}`)} class="w-full text-left">
            <Card class="hover:shadow-md transition-shadow cursor-pointer">
              <CardHeader>
                <div class="flex items-start justify-between gap-4">
                  <div class="flex-1">
                    {#if study.plainTitle}
                      <!-- AI title as main, original as subheader -->
                      <div class="flex items-start gap-2 mb-1">
                        <div class="flex-1">
                          <div class="flex items-center gap-2 mb-1">
                            <CardTitle class="text-lg">{study.plainTitle}</CardTitle>
                            <span class="text-xs text-muted-foreground italic whitespace-nowrap">✨ AI</span>
                          </div>
                        </div>
                        {#if study.recruitingStatus}
                          <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium whitespace-nowrap">
                            {study.recruitingStatus}
                          </span>
                        {/if}
                      </div>
                      <div class="text-xs text-muted-foreground mb-2">
                        Original: {study.title}
                      </div>
                    {:else if aiTitleGenerating[study.id]}
                      <!-- Loading state -->
                      <div class="flex items-start gap-2 mb-1">
                        <CardTitle class="text-lg flex-1">{study.title}</CardTitle>
                        {#if study.recruitingStatus}
                          <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium whitespace-nowrap">
                            {study.recruitingStatus}
                          </span>
                        {/if}
                      </div>
                      <div class="text-xs text-muted-foreground mb-2">
                        <span class="animate-pulse">✨ Generating simplified title...</span>
                      </div>
                    {:else}
                      <!-- No AI title, show original only -->
                      <div class="flex items-start gap-2 mb-2">
                        <CardTitle class="text-lg flex-1">{study.title}</CardTitle>
                        {#if study.recruitingStatus}
                          <span class="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium whitespace-nowrap">
                            {study.recruitingStatus}
                          </span>
                        {/if}
                      </div>
                    {/if}
                    {#if study.studyType || study.locationsSummary}
                      <div class="text-xs text-muted-foreground">
                        {#if study.studyType}
                          <span>{study.studyType}</span>
                        {/if}
                        {#if study.studyType && study.locationsSummary}
                          <span class="mx-1">•</span>
                        {/if}
                        {#if study.locationsSummary}
                          <span>{study.locationsSummary}</span>
                        {:else if study.locations && study.locations.length > 1}
                          <span>Multiple locations</span>
                        {/if}
                      </div>
                    {/if}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p class="text-sm text-muted-foreground mb-3">{study.snippet}</p>
                {#if study.conditions && study.conditions.length > 0}
                  <div class="mb-3 flex flex-wrap gap-2">
                    {#each study.conditions.slice(0, 3) as condition}
                      <span class="px-2 py-1 bg-muted rounded text-xs text-muted-foreground">
                        {condition}
                      </span>
                    {/each}
                  </div>
                {/if}
                {#if study.reasons && study.reasons.length > 0}
                  <div class="flex flex-wrap gap-2">
                    {#each study.reasons as reason}
                      <span class="px-2 py-1 bg-primary/10 text-primary rounded text-xs">
                        {reason}
                      </span>
                    {/each}
                  </div>
                {/if}
              </CardContent>
            </Card>
          </button>
        {/each}
      </div>

      {#if totalPages > 1}
        <div class="mt-6 flex items-center justify-center gap-4">
          <button
            on:click={handlePrevPage}
            disabled={currentPage === 1}
            class="px-4 py-2 border rounded-md text-sm font-medium hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span class="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages}
          </span>
          <button
            on:click={handleNextPage}
            disabled={currentPage >= totalPages}
            class="px-4 py-2 border rounded-md text-sm font-medium hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      {/if}
    {/if}
  </div>
</main>
