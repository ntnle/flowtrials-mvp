<script>
	import './layout.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { locales, localizeHref } from '$lib/paraglide/runtime';
	import favicon from '$lib/assets/favicon.svg';
	import { initAuth, user } from '$lib/authStore.js';
	import { signOut } from '$lib/supabase.js';

	let { children } = $props();

	onMount(() => {
		initAuth();
	});

	async function handleSignOut() {
		await signOut();
		goto('/');
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
<!-- Navigation Bar -->
<nav class="border-b bg-background">
	<div class="flex items-center justify-between max-w-7xl mx-auto px-6 py-4">
		<a href="/" class="text-xl font-bold text-primary">Flow Trials</a>

		<div class="flex items-center gap-6">
			<a href="/browse" class="text-sm font-medium hover:text-primary transition-colors">Browse</a>
			<a href="/bio" class="text-sm font-medium hover:text-primary transition-colors">Bio</a>

			{#if $user}
				<a href="/profile" class="text-sm font-medium hover:text-primary transition-colors">Profile</a>
				<button
					onclick={handleSignOut}
					class="text-sm font-medium hover:text-primary transition-colors"
				>
					Sign Out
				</button>
			{:else}
				<a href="/login" class="text-sm font-medium hover:text-primary transition-colors">Login</a>
				<a
					href="/signup"
					class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
				>
					Sign Up
				</a>
			{/if}
		</div>
	</div>
</nav>
{@render children()}
<div style="display:none">
	{#each locales as locale}
		<a
			href={localizeHref(page.url.pathname, { locale })}
		>
			{locale}
		</a>
	{/each}
</div>
