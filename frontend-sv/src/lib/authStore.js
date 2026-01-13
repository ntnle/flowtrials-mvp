import { writable } from 'svelte/store';
import { supabase, onAuthStateChange } from './supabase';

export const user = writable(null);
export const session = writable(null);
export const loading = writable(true);

// Initialize auth state
export async function initAuth() {
  const { data: { session: currentSession } } = await supabase.auth.getSession();
  session.set(currentSession);
  user.set(currentSession?.user ?? null);
  loading.set(false);

  // Listen for auth changes
  onAuthStateChange((event, newSession) => {
    session.set(newSession);
    user.set(newSession?.user ?? null);
  });
}
