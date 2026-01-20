import { createClient } from '@supabase/supabase-js';

// Get Supabase credentials from environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'http://localhost:54321';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0';

// Create Supabase client
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
});

/**
 * Auth helpers
 */

export async function signUp(email, password) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: window.location.origin
    }
  });

  if (error) throw error;

  // Return both user and session for immediate access
  return {
    user: data.user,
    session: data.session
  };
}

export async function signIn(email, password) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password
  });

  if (error) throw error;

  // Return both user and session for consistency
  return {
    user: data.user,
    session: data.session
  };
}

export async function signOut() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

export async function getCurrentUser() {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  return user;
}

export async function getSession() {
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error) throw error;
  return session;
}

/**
 * User Profile helpers
 */

export async function getUserProfile(userId) {
  const { data, error } = await supabase
    .from('user_profiles')
    .select('*')
    .eq('id', userId)
    .single();

  if (error) throw error;
  return data;
}

export async function updateUserProfile(userId, profileData) {
  const { data, error } = await supabase
    .from('user_profiles')
    .update(profileData)
    .eq('id', userId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Participation Request helpers
 */

export async function createParticipationRequest(studyId, notes = '', contactPreference = 'email') {
  const user = await getCurrentUser();
  if (!user) throw new Error('Must be logged in to create participation request');

  console.log('Creating participation request with:', {
    user_id: user.id,
    study_id: studyId,
    notes,
    contact_preference: contactPreference,
    status: 'pending'
  });

  const { data, error } = await supabase
    .from('participation_requests')
    .insert({
      user_id: user.id,
      study_id: studyId,
      notes,
      contact_preference: contactPreference,
      status: 'pending'
    })
    .select()
    .single();

  if (error) {
    console.error('Supabase insert error:', error);
    // Handle unique constraint violation (user already requested this study)
    if (error.code === '23505') {
      throw new Error('You have already requested to participate in this study');
    }
    throw error;
  }

  console.log('Participation request created:', data);
  return data;
}

export async function getUserParticipationRequests() {
  const user = await getCurrentUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from('participation_requests')
    .select(`
      *,
      studies (
        id,
        title,
        brief_summary,
        recruiting_status
      )
    `)
    .eq('user_id', user.id)
    .order('created_at', { ascending: false });

  if (error) throw error;
  return data;
}

export async function withdrawParticipationRequest(requestId) {
  const { data, error } = await supabase
    .from('participation_requests')
    .update({ status: 'withdrawn' })
    .eq('id', requestId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Researcher helpers
 */

export async function isResearcher() {
  try {
    const { data, error } = await supabase.rpc('is_researcher');
    if (error) throw error;
    return data || false;
  } catch (err) {
    console.error('Error checking researcher status:', err);
    return false;
  }
}

export async function getUserStudies() {
  const user = await getCurrentUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from('studies')
    .select('*')
    .eq('created_by', user.id)
    .order('created_at', { ascending: false });

  if (error) throw error;
  return data;
}

export async function createDraftStudy(studyData) {
  const user = await getCurrentUser();
  if (!user) throw new Error('Must be logged in to create study');

  const { data, error } = await supabase
    .from('studies')
    .insert({
      ...studyData,
      created_by: user.id,
      is_published: false
    })
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function updateStudy(studyId, studyData) {
  const { data, error } = await supabase
    .from('studies')
    .update(studyData)
    .eq('id', studyId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function deleteStudy(studyId) {
  const { error } = await supabase
    .from('studies')
    .delete()
    .eq('id', studyId);

  if (error) throw error;
}

export async function getStudyByIdSupabase(studyId) {
  const { data, error } = await supabase
    .from('studies')
    .select('*')
    .eq('id', studyId)
    .single();

  if (error) throw error;
  return data;
}

/**
 * Auth state listener
 */

export function onAuthStateChange(callback) {
  const { data: { subscription } } = supabase.auth.onAuthStateChange(
    (event, session) => {
      callback(event, session);
    }
  );

  return subscription;
}
