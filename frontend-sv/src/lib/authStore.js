import { writable } from 'svelte/store';
import { supabase, onAuthStateChange } from '$lib/supabase.js';

const AUTH_STORE_SINGLETON_KEY = '__flowtrials_auth_store__';

const authState = globalThis[AUTH_STORE_SINGLETON_KEY] || {
  user: writable(null),
  session: writable(null),
  loading: writable(true),
  initPromise: null,
  hasHydrated: false
};

if (!globalThis[AUTH_STORE_SINGLETON_KEY]) {
  globalThis[AUTH_STORE_SINGLETON_KEY] = authState;
} else if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
  console.log('[authStore] reusing singleton');
}

export const user = authState.user;
export const session = authState.session;
export const loading = authState.loading;

// Initialize auth state
export async function initAuth() {
  if (authState.initPromise) return authState.initPromise;

  authState.initPromise = (async () => {
    authState.loading.set(true);
    authState.hasHydrated = false;
    let receivedInitialSessionEvent = false;

    let subscription;
    try {
      // Subscribe first so we reliably receive INITIAL_SESSION.
      subscription = onAuthStateChange((event, newSession) => {
        if (import.meta.env.DEV) {
          // eslint-disable-next-line no-console
          console.log('[auth]', event, {
            hasSession: Boolean(newSession),
            userId: newSession?.user?.id ?? null,
            expiresAt: newSession?.expires_at ?? null
          });
        }

        // Guard against a late INITIAL_SESSION overwriting a newer session.
        if (event === 'INITIAL_SESSION') {
          if (authState.hasHydrated) return;
          receivedInitialSessionEvent = true;
          authState.hasHydrated = true;
        }

        authState.session.set(newSession);
        authState.user.set(newSession?.user ?? null);
        if (event === 'INITIAL_SESSION') authState.loading.set(false);
      });

      const { data, error } = await supabase.auth.getSession();
      if (error) throw error;

      // Fallback: only apply getSession if we didn't already hydrate from INITIAL_SESSION.
      if (!receivedInitialSessionEvent) {
        authState.session.set(data.session);
        authState.user.set(data.session?.user ?? null);
        authState.hasHydrated = true;
        authState.loading.set(false);
      } else if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.log('[auth] getSession skipped (INITIAL_SESSION already received)', {
          hasSession: Boolean(data.session)
        });
      }
    } catch (err) {
      console.error('initAuth failed:', err);
      authState.session.set(null);
      authState.user.set(null);
      authState.hasHydrated = true;
      authState.loading.set(false);
    }

    return subscription;
  })();

  return authState.initPromise;
}
