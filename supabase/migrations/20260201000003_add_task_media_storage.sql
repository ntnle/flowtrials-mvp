-- Migration: Add task-media storage bucket for task images and PDFs
-- Description: Creates a private bucket for task media with RLS policies

-- Create the storage bucket for task media
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'task-media',
  'task-media',
  false,  -- Private bucket
  10485760,  -- 10MB limit
  ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/svg+xml', 'application/pdf']
)
ON CONFLICT (id) DO NOTHING;

-- RLS Policies for task-media bucket

-- Policy 1: Study owners can upload media to their studies
-- Path format: {study_id}/{task_id}/{filename}
CREATE POLICY "Study owners can upload task media"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'task-media'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT id
    FROM public.studies
    WHERE created_by = auth.uid()
  )
);

-- Policy 2: Study owners can view their task media
CREATE POLICY "Study owners can view task media"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'task-media'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT id
    FROM public.studies
    WHERE created_by = auth.uid()
  )
);

-- Policy 3: Approved participants with consent can view task media
CREATE POLICY "Approved participants can view task media"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'task-media'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT study_id
    FROM public.participation_requests
    WHERE user_id = auth.uid()
    AND status = 'approved'
    AND consent_acknowledged_at IS NOT NULL
  )
);

-- Policy 4: Study owners can delete their task media
CREATE POLICY "Study owners can delete task media"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'task-media'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT id
    FROM public.studies
    WHERE created_by = auth.uid()
  )
);

-- Policy 5: Study owners can update their task media
CREATE POLICY "Study owners can update task media"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'task-media'
  AND (storage.foldername(name))[1]::bigint IN (
    SELECT id
    FROM public.studies
    WHERE created_by = auth.uid()
  )
);
