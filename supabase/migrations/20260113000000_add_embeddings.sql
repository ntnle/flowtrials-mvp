-- =====================================================
-- EMBEDDINGS MIGRATION
-- Add pgvector support for semantic search
-- =====================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add search_text column (normalized concatenation for embeddings)
-- Add embedding column (1536 dimensions for OpenAI text-embedding-3-small)
ALTER TABLE public.studies
  ADD COLUMN IF NOT EXISTS search_text TEXT,
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create function to generate search_text
-- Matches Python normalization logic: lowercase + whitespace collapse
CREATE OR REPLACE FUNCTION public.generate_search_text(
  p_title TEXT,
  p_brief_summary TEXT
) RETURNS TEXT AS $$
BEGIN
  RETURN LOWER(TRIM(REGEXP_REPLACE(
    COALESCE(p_title, '') || ' | ' || COALESCE(p_brief_summary, ''),
    '\s+', ' ', 'g'
  )));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Backfill search_text for existing studies
UPDATE public.studies
SET search_text = public.generate_search_text(title, brief_summary)
WHERE search_text IS NULL;

-- Create trigger to auto-update search_text on insert/update
CREATE OR REPLACE FUNCTION public.update_search_text()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_text := public.generate_search_text(NEW.title, NEW.brief_summary);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_search_text
  BEFORE INSERT OR UPDATE OF title, brief_summary ON public.studies
  FOR EACH ROW
  EXECUTE FUNCTION public.update_search_text();

-- Create trigram index for hybrid search (keyword fallback)
CREATE INDEX IF NOT EXISTS idx_studies_search_text_trgm ON public.studies
  USING GIN (search_text gin_trgm_ops);

-- Note: IVFFLAT index will be created by backfill script after embeddings are generated
-- This avoids index rebuilds during bulk inserts
-- Command to run manually after backfill:
--   CREATE INDEX idx_studies_embedding_ivfflat ON public.studies
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- Add column comments for documentation
COMMENT ON COLUMN public.studies.search_text IS 'Normalized text for embedding generation: "{title} | {brief_summary}" (lowercase, whitespace collapsed)';
COMMENT ON COLUMN public.studies.embedding IS 'OpenAI text-embedding-3-small (1536 dimensions) for semantic search via pgvector cosine similarity';
