<script>
  import { onMount } from 'svelte';
  import Router from 'svelte-spa-router';
  import { push, link } from 'svelte-spa-router';
  import { initAuth, user } from './lib/authStore';
  import { signOut } from './lib/supabase';

  // Routes
  import Home from './routes/Home.svelte';
  import Browse from './routes/Browse.svelte';
  import StudyPage from './routes/StudyPage.svelte';
  import Signup from './routes/Signup.svelte';
  import Login from './routes/Login.svelte';
  import Profile from './routes/Profile.svelte';

  const routes = {
    '/': Home,
    '/browse': Browse,
    '/study/:id': StudyPage,
    '/signup': Signup,
    '/login': Login,
    '/profile': Profile,
  };

  onMount(() => {
    initAuth();
  });

  async function handleSignOut() {
    await signOut();
    push('/');
  }
</script>

<!-- Navigation Bar -->
<nav class="border-b bg-background">
  <div class="flex items-center justify-between max-w-7xl mx-auto px-6 py-4">
    <a href="/" use:link class="text-xl font-bold text-primary">Flow Trials</a>

    <div class="flex items-center gap-6">
      <a href="/browse" use:link class="text-sm font-medium hover:text-primary transition-colors">Browse</a>

      {#if $user}
        <a href="/profile" use:link class="text-sm font-medium hover:text-primary transition-colors">Profile</a>
        <button
          on:click={handleSignOut}
          class="text-sm font-medium hover:text-primary transition-colors"
        >
          Sign Out
        </button>
      {:else}
        <a href="/login" use:link class="text-sm font-medium hover:text-primary transition-colors">Login</a>
        <a
          href="/signup"
          use:link
          class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Sign Up
        </a>
      {/if}
    </div>
  </div>
</nav>

<Router {routes} />
