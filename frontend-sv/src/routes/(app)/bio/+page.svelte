<script>
  const baseUrl = import.meta.env.BASE_URL;
  const founders = [
    {
      name: 'Malhaar Agrawal',
      title: 'MD Candidate, Co-Founder & CEO',
      image: `${baseUrl}malhaar.jpeg`,
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
      image: `${baseUrl}nathanle.jpeg`,
      description:
        'Nathan is a senior at Swarthmore College who brings engineering focus to build a user-friendly platform. He is dedicated to reducing disparities in health research and making it easier for people to engage with clinical studies.',
      socials: {
        linkedin: 'https://www.linkedin.com/in/nathan-le-b31a7a212/',
        email: 'mailto:nathan@flowtrials.com'
      }
    }
  ];
</script>

<main class="min-h-screen bg-background text-foreground">
  <div class="relative isolate">
    <div class="absolute inset-0 -z-10">
      <div class="absolute inset-0 bg-gradient-to-b from-blue-50/60 via-white to-white"></div>
      <div class="absolute inset-0 bg-[radial-gradient(65%_50%_at_50%_-10%,rgba(21,93,252,0.08),transparent)]"></div>
    </div>

    <div class="relative mx-auto max-w-6xl px-4 md:px-8 2xl:px-0 py-16 pb-24">
      <section class="mb-12">
        <div class="text-center max-w-3xl mx-auto">
          <h1 class="text-4xl md:text-5xl font-bold tracking-tight mb-4">Meet our founders</h1>
          <p class="text-lg text-muted-foreground">
            The team bringing clinical research closer to the people it serves.
          </p>
        </div>
      </section>

      <section class="space-y-16">
        {#each founders as founder}
          <div class="grid gap-8 lg:grid-cols-2 items-start">
            <div class="rounded-2xl overflow-hidden shadow-lg max-w-[70%] mx-auto lg:mx-0">
              <img
                src={founder.image}
                alt={founder.name}
                class="w-full h-auto"
                loading="lazy"
              />
            </div>

            <div class="space-y-6 flex flex-col justify-center">
              <div>
                <h2 class="text-3xl font-bold tracking-tight mb-2">{founder.name}</h2>
                <p class="text-lg font-medium text-blue-700">{founder.title}</p>
              </div>
              <p class="text-muted-foreground text-lg leading-relaxed">{founder.description}</p>
              <div class="flex flex-wrap gap-3 pt-2">
                <a
                  class="inline-flex items-center gap-2 rounded-full border border-border bg-background px-5 py-2.5 text-sm font-medium text-blue-700 hover:bg-accent transition-colors"
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
                  class="inline-flex items-center gap-2 rounded-full border border-border bg-background px-5 py-2.5 text-sm font-medium hover:bg-accent transition-colors"
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
        {/each}
      </section>
    </div>
  </div>
</main>
