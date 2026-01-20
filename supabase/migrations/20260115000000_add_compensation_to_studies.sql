-- =====================================================
-- ADD COMPENSATION TO STUDIES
-- Researcher-created studies may include compensation details
-- =====================================================

ALTER TABLE public.studies
ADD COLUMN IF NOT EXISTS compensation JSONB;

COMMENT ON COLUMN public.studies.compensation IS 'Compensation details for this study (researcher-provided); free-form JSON';
