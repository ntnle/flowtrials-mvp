-- =====================================================
-- AI CACHE MIGRATION
-- Add fields to cache AI-generated content
-- =====================================================

-- Add AI cache fields to studies table
ALTER TABLE public.studies
  ADD COLUMN ai_plain_title TEXT,
  ADD COLUMN ai_plain_summary TEXT,
  ADD COLUMN ai_eligibility_quiz JSONB,
  ADD COLUMN ai_cache_version TEXT DEFAULT 'v1',
  ADD COLUMN ai_cached_at TIMESTAMPTZ;

-- Index for cache lookups
CREATE INDEX idx_studies_ai_cache_version ON public.studies (ai_cache_version);

-- Comments for documentation
COMMENT ON COLUMN public.studies.ai_plain_title IS 'AI-generated plain language title';
COMMENT ON COLUMN public.studies.ai_plain_summary IS 'AI-generated plain language summary';
COMMENT ON COLUMN public.studies.ai_eligibility_quiz IS 'AI-generated eligibility quiz questions';
COMMENT ON COLUMN public.studies.ai_cache_version IS 'Version of AI prompts/model used for caching';
COMMENT ON COLUMN public.studies.ai_cached_at IS 'Timestamp when AI content was last generated';
