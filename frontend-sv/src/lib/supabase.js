import { createClient } from '@supabase/supabase-js';

// Get Supabase credentials from environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'http://localhost:54321';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0';

if (import.meta.env.DEV) {
  // eslint-disable-next-line no-console
  console.log('[supabase] init', {
    url: supabaseUrl,
    usingEnvUrl: Boolean(import.meta.env.VITE_SUPABASE_URL),
    usingEnvAnonKey: Boolean(import.meta.env.VITE_SUPABASE_ANON_KEY)
  });
}

const SUPABASE_SINGLETON_KEY = '__flowtrials_supabase__';

function getSupabaseSingleton() {
  const existing = globalThis[SUPABASE_SINGLETON_KEY];
  if (existing) return existing;

  const client = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: true
    }
  });

  globalThis[SUPABASE_SINGLETON_KEY] = client;
  return client;
}

// Create Supabase client (singleton to avoid multiple GoTrueClient instances)
export const supabase = getSupabaseSingleton();

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
 * Researcher participation request helpers
 */

export async function getStudyParticipationRequests(studyId) {
  // Fetch participation requests
  const { data: requests, error: reqError } = await supabase
    .from('participation_requests')
    .select('*')
    .eq('study_id', studyId)
    .order('created_at', { ascending: false });

  if (reqError) throw reqError;
  if (!requests || requests.length === 0) return [];

  // Fetch user profiles for these participants
  const userIds = requests.map(r => r.user_id);
  const { data: profiles, error: profError } = await supabase
    .from('user_profiles')
    .select('id, age, gender, conditions, zip_code')
    .in('id', userIds);

  if (profError) throw profError;

  // Merge profiles into requests
  const profileMap = new Map((profiles || []).map(p => [p.id, p]));
  return requests.map(r => ({
    ...r,
    user_profiles: profileMap.get(r.user_id) || null
  }));
}

export async function updateParticipationRequestStatus(requestId, status) {
  const { data, error } = await supabase
    .from('participation_requests')
    .update({ status })
    .eq('id', requestId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function resetParticipationConsent(requestId) {
  const { data, error } = await supabase
    .from('participation_requests')
    .update({ consent_acknowledged_at: null })
    .eq('id', requestId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Participant consent helpers
 */

export async function acknowledgeConsent(requestId) {
  const { data, error } = await supabase
    .from('participation_requests')
    .update({ consent_acknowledged_at: new Date().toISOString() })
    .eq('id', requestId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function getMyParticipationForStudy(studyId) {
  const user = await getCurrentUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from('participation_requests')
    .select('*')
    .eq('study_id', studyId)
    .eq('user_id', user.id)
    .single();

  if (error && error.code !== 'PGRST116') throw error; // PGRST116 = no rows
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
 * Storage helpers for study media
 */

export async function uploadStudyMedia(studyId, file) {
  const user = await getCurrentUser();
  if (!user) throw new Error('Must be logged in to upload media');

  // Generate unique filename
  const timestamp = Date.now();
  const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
  const filename = `${timestamp}_${sanitizedName}`;
  const path = `${studyId}/${filename}`;

  // Upload to storage
  const { data, error } = await supabase.storage
    .from('study-media')
    .upload(path, file, {
      cacheControl: '3600',
      upsert: false
    });

  if (error) throw error;
  return data.path;
}

export async function deleteStudyMedia(path) {
  const { error } = await supabase.storage
    .from('study-media')
    .remove([path]);

  if (error) throw error;
}

export function getPublicMediaUrl(path) {
  const { data } = supabase.storage
    .from('study-media')
    .getPublicUrl(path);

  return data.publicUrl;
}

/**
 * Audio Recording helpers
 */

export async function uploadAudioRecording(studyId, participationRequestId, audioBlob) {
  const user = await getCurrentUser();
  if (!user) throw new Error('Must be logged in to upload audio');

  // Generate unique filename with timestamp
  const timestamp = Date.now();
  const filename = `${timestamp}.webm`;
  const path = `${studyId}/${participationRequestId}/${filename}`;

  // Upload to storage
  const { data, error } = await supabase.storage
    .from('study-recordings')
    .upload(path, audioBlob, {
      contentType: 'audio/webm',
      cacheControl: '3600',
      upsert: false
    });

  if (error) throw error;

  // Return metadata about the recording
  return {
    path: data.path,
    size: audioBlob.size,
    mimeType: audioBlob.type,
    uploadedAt: new Date().toISOString()
  };
}

export async function getAudioRecordingUrl(path) {
  const { data, error } = await supabase.storage
    .from('study-recordings')
    .createSignedUrl(path, 3600); // 1 hour expiry

  if (error) throw error;
  return data.signedUrl;
}

export async function deleteAudioRecording(path) {
  const { error } = await supabase.storage
    .from('study-recordings')
    .remove([path]);

  if (error) throw error;
}

/**
 * Task Media helpers
 */

export async function uploadTaskMedia(studyId, taskId, file) {
  const user = await getCurrentUser();
  if (!user) throw new Error('Must be logged in to upload task media');

  // Generate unique filename
  const timestamp = Date.now();
  const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
  const filename = `${timestamp}_${sanitizedName}`;
  const path = `${studyId}/${taskId}/${filename}`;

  // Upload to storage
  const { data, error } = await supabase.storage
    .from('task-media')
    .upload(path, file, {
      cacheControl: '3600',
      upsert: false
    });

  if (error) throw error;

  // Return metadata
  return {
    path: data.path,
    kind: file.type.startsWith('image/') ? 'image' : 'pdf',
    mimeType: file.type,
    size: file.size
  };
}

export async function getTaskMediaUrl(path) {
  const { data, error } = await supabase.storage
    .from('task-media')
    .createSignedUrl(path, 3600); // 1 hour expiry

  if (error) throw error;
  return data.signedUrl;
}

export async function deleteTaskMedia(path) {
  const { error } = await supabase.storage
    .from('task-media')
    .remove([path]);

  if (error) throw error;
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

/**
 * Task submission helpers
 */

export async function submitTaskResponse(studyId, taskId, responses) {
  const user = await getCurrentUser();
  if (!user) throw new Error('Must be logged in to submit task');

  const { data, error } = await supabase
    .from('task_submissions')
    .insert({
      study_id: studyId,
      task_id: taskId,
      user_id: user.id,
      responses
    })
    .select()
    .single();

  if (error) {
    if (error.code === '23505') {
      throw new Error('You have already submitted this task');
    }
    throw error;
  }
  return data;
}

export async function getMyTaskSubmissions(studyId) {
  const user = await getCurrentUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from('task_submissions')
    .select('*')
    .eq('study_id', studyId)
    .eq('user_id', user.id);

  if (error) throw error;
  return data || [];
}

export async function getTaskSubmissionsForStudy(studyId) {
  const { data, error } = await supabase
    .from('task_submissions')
    .select('*')
    .eq('study_id', studyId)
    .order('submitted_at', { ascending: false });

  if (error) throw error;
  return data || [];
}
