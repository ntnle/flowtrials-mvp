-- =====================================================
-- ADD MEDIA TO STUDIES
-- Researchers can add supplemental materials (posters, images) via URLs
-- =====================================================

ALTER TABLE public.studies
ADD COLUMN IF NOT EXISTS media JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.studies.media IS 'Array of media items: [{"url": "https://...", "caption": "..."}]';
