<script>
  import { Input } from "$lib/components/ui/input/index.js";
  import { push } from "svelte-spa-router";

  let searchQuery = '';

  const suggestedConditions = [
    'Diabetes',
    'Asthma',
    'Depression',
    'Heart Disease',
    'Arthritis',
    'Cancer',
    'Hypertension',
    'Anxiety'
  ];

  function handleSearch() {
    if (searchQuery.trim()) {
      push(`/browse?q=${encodeURIComponent(searchQuery)}`);
    }
  }

  function handleConditionClick(condition) {
    searchQuery = condition;
    handleSearch();
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }
</script>

<main class="min-h-screen bg-background flex items-center justify-center p-6">
  <div class="relative mx-auto max-w-5xl px-4 md:px-8 2xl:px-0">
    <div class="flex flex-col items-center text-center max-w-3xl mx-auto">
      <div class="w-full">
        <!-- Hero -->
        <h1 class="mb-8 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-7xl">
          Find Clinical Trials
          <div class="mb-8 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-7xl">
            <span>with just a</span>
            <span> </span>
            <span class="relative inline-block">
              <span class="relative z-10">Click</span>
              <span class="absolute bottom-2 left-0 right-0 h-1/4" style="background-color: rgba(21, 93, 252, 0.3);"></span>
            </span>
          </div>
        </h1>

        <p class="mb-10 max-w-2xl text-xl text-muted-foreground md:text-2xl mx-auto">
          Find clinical trials you may be eligible for and express your interest to study teams. For people considering participation in medical research.
        </p>

        <!-- Search Input -->
        <div class="mb-8 space-y-3">
          <Input
            bind:value={searchQuery}
            on:keydown={handleKeydown}
            placeholder="Search by condition or keyword..."
            class="h-14 text-lg"
          />
        </div>

        <!-- Suggested Conditions -->
        <div class="space-y-3 mb-8">
          <p class="text-sm text-muted-foreground">Or choose a common condition:</p>
          <div class="flex flex-wrap gap-2 justify-center">
            {#each suggestedConditions as condition}
              <button
                on:click={() => handleConditionClick(condition)}
                class="px-4 py-2 border border-border rounded-full text-sm hover:bg-accent transition-colors"
              >
                {condition}
              </button>
            {/each}
          </div>
        </div>

        <!-- CTA Button -->
        <div class="flex flex-col space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0 justify-center mb-12">
          <button
            on:click={handleSearch}
            disabled={!searchQuery.trim()}
            class="inline-flex items-center justify-center whitespace-nowrap font-medium focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 text-white shadow h-10 gap-2 rounded-full px-8 py-6 text-lg shadow-lg transition-all hover:shadow-xl"
            style="background-color: #155dfc;"
          >
            Find Studies
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
              <path d="M5 12h14"></path>
              <path d="m12 5 7 7-7 7"></path>
            </svg>
          </button>
        </div>

        <!-- Trust Microcopy -->
        <div class="mb-8 space-y-2 text-sm text-muted-foreground border-t border-border pt-6">
          <p>Participation is opt-in—you choose which studies to request.</p>
          <p>Study teams review your request and contact you if you're eligible.</p>
          <p>You can withdraw a participation request at any time.</p>
        </div>


        <!-- MVP Disclaimer -->
        <div class="text-xs text-muted-foreground pt-4">
          Flow Trials does not provide medical advice. Eligibility is determined by study teams.
        </div>
      </div>
    </div>
  </div>
</main>
