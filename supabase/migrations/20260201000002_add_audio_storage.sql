-- Migration: Add study-recordings storage bucket for audio task responses
-- Description: Creates a private bucket for audio recordings with RLS policies

-- Create the storage bucket for audio recordings
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'study-recordings',
  'study-recordings',
  false,  -- Private bucket
  52428800,  -- 50MB limit
  ARRAY['audio/webm', 'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/mp4', 'audio/m4a']
)
ON CONFLICT (id) DO NOTHING;

-- RLS Policies for study-recordings bucket

-- Policy 1: Participants can upload recordings to their own participation request folder
-- Path format: {study_id}/{participation_request_id}/{filename}
CREATE POLICY "Participants can upload their own recordings"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'study-recordings'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT study_id
    FROM public.participation_requests
    WHERE user_id = auth.uid()
    AND status = 'approved'
  )
  AND (storage.foldername(name))[2]::bigint IN (
    SELECT id
    FROM public.participation_requests
    WHERE user_id = auth.uid()
    AND status = 'approved'
  )
);

-- Policy 2: Study owners can view all recordings for their studies
CREATE POLICY "Study owners can view recordings"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'study-recordings'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT id
    FROM public.studies
    WHERE created_by = auth.uid()
  )
);

-- Policy 3: Participants can view their own recordings
CREATE POLICY "Participants can view their own recordings"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'study-recordings'
  AND (storage.foldername(name))[2]::bigint IN (
    SELECT id
    FROM public.participation_requests
    WHERE user_id = auth.uid()
  )
);

-- Policy 4: Study owners can delete recordings from their studies
CREATE POLICY "Study owners can delete recordings"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'study-recordings'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT id
    FROM public.studies
    WHERE created_by = auth.uid()
  )
);

-- Policy 5: Participants can delete their own recordings
CREATE POLICY "Participants can delete their own recordings"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'study-recordings'
  AND (storage.foldername(name))[2]::bigint IN (
    SELECT id
    FROM public.participation_requests
    WHERE user_id = auth.uid()
  )
);
