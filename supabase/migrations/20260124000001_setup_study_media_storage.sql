-- =====================================================
-- SETUP STUDY MEDIA STORAGE BUCKET
-- =====================================================

-- Create storage bucket for study media (images, PDFs)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'study-media',
  'study-media',
  true, -- Public read access
  5242880, -- 5MB in bytes
  ARRAY[
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
    'image/svg+xml',
    'application/pdf'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- STORAGE RLS POLICIES
-- =====================================================

-- Allow public to view/download files
CREATE POLICY "Public can view study media"
  ON storage.objects FOR SELECT
  TO public
  USING (bucket_id = 'study-media');

-- Allow authenticated researchers to upload files
CREATE POLICY "Researchers can upload study media"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'study-media'
    AND public.is_researcher()
  );

-- Allow study owners to delete their study's media files
-- Files must be in their study folder: {study_id}/*
CREATE POLICY "Study owners can delete their media"
  ON storage.objects FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'study-media'
    AND (
      -- Extract study_id from path (format: {study_id}/{filename})
      -- Check if user owns the study
      EXISTS (
        SELECT 1 FROM public.studies
        WHERE id = (split_part(name, '/', 1))::bigint
          AND created_by = auth.uid()
      )
    )
  );
