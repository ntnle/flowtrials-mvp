<script>
  import { Input } from "$lib/components/ui/input/index.js";
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card/index.js";
  import { push, link } from "svelte-spa-router";
  import { signIn } from "$lib/supabase";

  let email = '';
  let password = '';
  let loading = false;
  let error = '';

  async function handleLogin() {
    loading = true;
    error = '';

    try {
      await signIn(email, password);

      // Check if there's a redirect URL from query params
      const urlParams = new URLSearchParams(window.location.search);
      const redirect = urlParams.get('redirect');

      if (redirect) {
        // Redirect back to the study page with a flag to show confirmation modal
        push(`${redirect}?fromSignup=true`);
      } else {
        // Default redirect to browse
        push('/browse');
      }
    } catch (err) {
      error = err.message || 'Invalid credentials. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<main class="min-h-screen bg-background flex items-center justify-center p-6">
  <div class="w-full max-w-md">
    <Card>
      <CardHeader>
        <CardTitle>Log In</CardTitle>
      </CardHeader>
      <CardContent>
        <form on:submit|preventDefault={handleLogin} class="space-y-4">
          <div class="space-y-2">
            <label for="email" class="text-sm font-medium">Email</label>
            <Input
              id="email"
              type="email"
              bind:value={email}
              placeholder="you@example.com"
              required
              disabled={loading}
            />
          </div>

          <div class="space-y-2">
            <label for="password" class="text-sm font-medium">Password</label>
            <Input
              id="password"
              type="password"
              bind:value={password}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          {#if error}
            <p class="text-sm text-destructive">{error}</p>
          {/if}

          <button
            type="submit"
            disabled={loading}
            class="w-full h-10 px-4 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
          >
            {loading ? 'Logging in...' : 'Log In'}
          </button>

          <p class="text-sm text-center text-muted-foreground">
            Don't have an account?
            <button
              type="button"
              on:click={() => {
                const urlParams = new URLSearchParams(window.location.search);
                const redirect = urlParams.get('redirect');
                if (redirect) {
                  push(`/signup?redirect=${encodeURIComponent(redirect)}`);
                } else {
                  push('/signup');
                }
              }}
              class="text-primary hover:underline"
            >
              Sign up
            </button>
          </p>
        </form>
      </CardContent>
    </Card>
  </div>
</main>
