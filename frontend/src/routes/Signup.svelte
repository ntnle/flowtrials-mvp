<script>
  import { Input } from "$lib/components/ui/input/index.js";
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card/index.js";
  import { push } from "svelte-spa-router";
  import { signUp } from "$lib/supabase";

  let email = '';
  let password = '';
  let confirmPassword = '';
  let consent = false;
  let loading = false;
  let error = '';
  let info = '';

  async function handleSignup() {
    console.log('=== handleSignup called ===');
    error = '';
    info = '';

    if (!consent) {
      error = 'Please agree to the terms and conditions';
      console.log('Error: No consent');
      return;
    }

    if (password !== confirmPassword) {
      error = 'Passwords do not match';
      console.log('Error: Passwords do not match');
      return;
    }

    if (password.length < 6) {
      error = 'Password must be at least 6 characters';
      console.log('Error: Password too short');
      return;
    }

    loading = true;
    console.log('Starting signup for email:', email);

    try {
      console.log('Calling signUp...');
      const result = await signUp(email, password);
      console.log('signUp returned:', result);

      const { user, session } = result || {};

      if (!user) {
        throw new Error('Signup failed - no user returned');
      }

      if (!session) {
        info = 'Check your email to confirm your account, then log in.';
        return;
      }

      console.log('User created successfully:', user.id);

      // Check if there's a redirect URL from query params
      const urlParams = new URLSearchParams(window.location.search);
      const redirect = urlParams.get('redirect');

      if (redirect) {
        // Redirect back to the study page with a flag to show confirmation modal
        console.log('Redirecting to:', redirect);
        push(`${redirect}?fromSignup=true`);
      } else {
        // Navigate to profile
        console.log('Navigating to /profile');
        push('/profile');
      }
    } catch (err) {
      console.error('Signup error:', err);
      error = err.message || 'Signup failed. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<main class="min-h-screen bg-background flex items-center justify-center p-6">
  <div class="w-full max-w-md">
    <Card>
      <CardHeader>
        <CardTitle>Create Your Profile</CardTitle>
      </CardHeader>
      <CardContent>
        <form on:submit|preventDefault={handleSignup} class="space-y-4">
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
              placeholder="At least 6 characters"
              required
              disabled={loading}
            />
          </div>

          <div class="space-y-2">
            <label for="confirmPassword" class="text-sm font-medium">Confirm Password</label>
            <Input
              id="confirmPassword"
              type="password"
              bind:value={confirmPassword}
              placeholder="Re-enter password"
              required
              disabled={loading}
            />
          </div>

          <div class="space-y-2">
            <label class="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                bind:checked={consent}
                disabled={loading}
                class="mt-0.5"
              />
              <span>
                I agree to receive communications about clinical trial opportunities and understand my data will be stored securely.
              </span>
            </label>
          </div>

          {#if error}
            <p class="text-sm text-destructive">{error}</p>
          {/if}
          {#if info}
            <p class="text-sm text-primary">{info}</p>
          {/if}

          <button
            type="submit"
            disabled={loading || !consent}
            class="w-full h-12 px-6 bg-primary text-primary-foreground rounded-md font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? 'Creating account...' : 'Create Profile & Continue'}
          </button>

          <p class="text-sm text-center text-muted-foreground">
            Already have an account?
            <button
              type="button"
              on:click={() => {
                const urlParams = new URLSearchParams(window.location.search);
                const redirect = urlParams.get('redirect');
                if (redirect) {
                  push(`/login?redirect=${encodeURIComponent(redirect)}`);
                } else {
                  push('/login');
                }
              }}
              class="text-primary hover:underline"
            >
              Log in
            </button>
          </p>
        </form>
      </CardContent>
    </Card>
  </div>
</main>
