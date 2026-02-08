<script>
	import { goto } from '$app/navigation';
	import { Input } from "$lib/components/ui/input/index.js";

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
			title: 'Find studies that fit',
			bullets: [
				'AI-generated plain-language summaries translate complex protocols',
				'Eligibility highlights show key criteria at a glance',
				'Data sourced from ClinicalTrials.gov, updated through clinical partnerships'
			]
		},
		{
			title: 'Signal interest on your terms',
			bullets: [
				'You decide which studies to request—fully opt-in',
				'Share only your name and contact info with study teams',
				'Withdraw your request anytime, no questions asked',
				'Study teams review eligibility and reach out if you match'
			]
		},
		{
			title: 'Connect with prepared participants',
			bullets: [
				'Participants arrive informed—already reviewed summaries and criteria',
				'Receive essential contact signals from genuinely interested candidates',
				'Listings kept accurate and current through clinical partnerships'
			]
		}
	];

	function handleSearch() {
		if (searchQuery.trim()) {
			goto(`/browse?q=${encodeURIComponent(searchQuery)}`);
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
			<div class="absolute inset-0 bg-gradient-to-b from-blue-50/60 via-white to-white"></div>
			<div class="absolute inset-0 bg-[radial-gradient(65%_50%_at_50%_-10%,rgba(21,93,252,0.08),transparent)]"></div>
		</div>

		<div class="relative mx-auto max-w-6xl px-4 md:px-8 2xl:px-0 pb-24">
			<section class="pt-16 pb-10 md:pt-20 md:pb-14">
				<div class="flex flex-col items-center text-center max-w-4xl mx-auto">
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
						Making clinical trials more accessible, searchable, and understandable—plain-language summaries, eligibility clarity, and a guided way to reach study teams.
					</p>

					<div class="mb-8 space-y-3 w-full">
						<Input
							bind:value={searchQuery}
							on:keydown={handleKeydown}
							placeholder="Search by condition or keyword..."
							class="h-14 text-lg"
						/>
					</div>

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
							<h3 class="text-xl font-semibold mb-4">{item.title}</h3>
							<ul class="space-y-2">
								{#each item.bullets as bullet}
									<li class="text-sm text-muted-foreground leading-relaxed flex items-start gap-2">
										<span class="text-primary mt-1">•</span>
										<span>{bullet}</span>
									</li>
								{/each}
							</ul>
						</div>
					{/each}
				</div>

				<div class="mt-8 p-4 rounded-lg bg-muted/30 border border-border">
					<div class="grid gap-3 md:grid-cols-2 lg:grid-cols-4 text-xs text-muted-foreground">
						<div class="flex items-start gap-2">
							<span class="text-primary">✓</span>
							<span>No medical advice—eligibility determined by investigators</span>
						</div>
						<div class="flex items-start gap-2">
							<span class="text-primary">✓</span>
							<span>Minimal data collection, secure handling</span>
						</div>
						<div class="flex items-start gap-2">
							<span class="text-primary">✓</span>
							<span>Listings kept current via clinical partners</span>
						</div>
						<div class="flex items-start gap-2">
							<span class="text-primary">✓</span>
							<span>Withdraw participation requests anytime</span>
						</div>
					</div>
				</div>
			</section>

			<div class="text-xs text-muted-foreground pt-8 border-t border-border">
				Flow Trials does not provide medical advice. Eligibility is determined by study teams.
			</div>
		</div>
	</div>
</main>
