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

  const valueProps = [
    {
      title: 'Patient-first search',
      copy: 'Plain-language filters and AI-assisted summaries help you decide quickly if a study fits.'
    },
    {
      title: 'Streamlined outreach',
      copy: 'Submit interest directly to study teams—no endless forms or confusing email threads.'
    },
    {
      title: 'Built with clinicians',
      copy: 'We partner with researchers to keep details accurate and up to date.'
    }
  ];

  const founders = [
    {
      name: 'Malhaar Agrawal',
      title: 'MD Candidate, Co-Founder & CEO',
      initials: 'MA',
      description:
        "Malhaar is a medical student at UPenn's Perelman School of Medicine, an MIT alumnus, and a Truman Scholar with six years of clinical research experience. He co-founded Flow Trials to modernize recruitment and make participation in cutting-edge medical research more accessible.",
      socials: {
        linkedin: 'https://www.linkedin.com/in/malhaar-agrawal-b805771a9/',
        email: 'mailto:malhaar@flowtrials.com'
      }
    },
    {
      name: 'Nathan Le',
      title: 'Co-Founder',
      initials: 'NL',
      description:
        'Nathan is a senior at Swarthmore College who brings engineering focus to build a user-friendly platform. He is dedicated to reducing disparities in health research and making it easier for people to engage with clinical studies.',
      socials: {
        linkedin: 'https://www.linkedin.com/in/nathan-le-b31a7a212/',
        email: 'mailto:nathan@flowtrials.com'
      }
    }
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

<main class="min-h-screen bg-background text-foreground">
  <div class="relative isolate">
    <div class="absolute inset-0 -z-10">
      <div class="absolute inset-0 bg-gradient-to-b from-blue-50/60 via-white to-white" />
      <div class="absolute inset-0 bg-[radial-gradient(65%_50%_at_50%_-10%,rgba(21,93,252,0.08),transparent)]" />
    </div>

    <div class="relative mx-auto max-w-6xl px-4 md:px-8 2xl:px-0 pb-24">
      <section class="pt-16 pb-10 md:pt-20 md:pb-14">
        <div class="flex flex-col items-center text-center max-w-4xl mx-auto">
          <!-- Hero -->
          <h1 class="mb-8 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-7xl">
            Find Clinical Trials
            <div class="mb-2 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-7xl">
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
          <div class="mb-8 space-y-3 w-full">
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
          <div class="flex flex-col space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0 justify-center mb-10">
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
          <div class="mb-4 space-y-2 text-sm text-muted-foreground border-t border-border pt-6">
            <p>Participation is opt-in—you choose which studies to request.</p>
            <p>Study teams review your request and contact you if you're eligible.</p>
            <p>You can withdraw a participation request at any time.</p>
          </div>
        </div>
      </section>

      <section class="py-12 md:py-16">
        <div class="text-center max-w-3xl mx-auto mb-10">
          <h2 class="text-3xl md:text-4xl font-bold tracking-tight">Why Flow Trials</h2>
          <p class="mt-4 text-lg text-muted-foreground">
            Built to make finding and joining clinical research simple, transparent, and respectful of your time.
          </p>
        </div>
        <div class="grid gap-6 md:grid-cols-3">
          {#each valueProps as item}
            <div class="h-full rounded-2xl border border-border bg-card/50 p-6 shadow-sm">
              <h3 class="text-xl font-semibold mb-3">{item.title}</h3>
              <p class="text-muted-foreground leading-relaxed">{item.copy}</p>
            </div>
          {/each}
        </div>
      </section>

      <section class="py-12 md:py-16">
        <div class="text-center max-w-3xl mx-auto mb-10">
          <h2 class="text-3xl md:text-4xl font-bold tracking-tight">Meet our founders</h2>
          <p class="mt-4 text-lg text-muted-foreground">
            The team bringing clinical research closer to the people it serves.
          </p>
        </div>

        <div class="space-y-8">
          {#each founders as founder}
            <div class="rounded-3xl border border-border bg-card/60 backdrop-blur-sm p-6 md:p-8 shadow-sm">
              <div class="grid gap-6 md:grid-cols-[auto,1fr] items-center">
                <div class="flex items-center gap-4">
                  <div class="h-20 w-20 md:h-24 md:w-24 rounded-2xl bg-gradient-to-br from-blue-100 via-white to-blue-200 border border-border text-2xl font-semibold text-blue-900 flex items-center justify-center">
                    {founder.initials}
                  </div>
                </div>

                <div class="space-y-4">
                  <div>
                    <h3 class="text-2xl font-bold tracking-tight">{founder.name}</h3>
                    <p class="mt-1 text-base font-medium text-blue-700">{founder.title}</p>
                  </div>
                  <p class="text-muted-foreground leading-relaxed">{founder.description}</p>
                  <div class="flex flex-wrap gap-3">
                    <a
                      class="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium text-blue-700 hover:bg-accent transition-colors"
                      href={founder.socials.linkedin}
                      target="_blank"
                      rel="noreferrer"
                    >
                      LinkedIn
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                        <path d="M8 4v8m-3-5h6m3-3v8a2 2 0 0 1-2 2H6l-4 3V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2Z" />
                      </svg>
                    </a>
                    <a
                      class="inline-flex items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
                      href={founder.socials.email}
                    >
                      Email
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                        <path d="m3 5 5 4 5-4" />
                        <rect x="2" y="4" width="12" height="9" rx="2" ry="2" />
                      </svg>
                    </a>
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </section>

      <!-- MVP Disclaimer -->
      <div class="text-xs text-muted-foreground pt-8 border-t border-border">
        Flow Trials does not provide medical advice. Eligibility is determined by study teams.
      </div>
    </div>
  </div>
</main>
