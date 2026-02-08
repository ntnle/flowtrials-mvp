-- Tighten study-recordings uploads to require approved + consented

DROP POLICY IF EXISTS "Participants can upload their own recordings" ON storage.objects;

-- Policy: Participants can upload recordings only when approved AND consent acknowledged
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
    AND consent_acknowledged_at IS NOT NULL
  )
  AND (storage.foldername(name))[2]::bigint IN (
    SELECT id
    FROM public.participation_requests
    WHERE user_id = auth.uid()
    AND status = 'approved'
    AND consent_acknowledged_at IS NOT NULL
  )
);
