-- =====================================================
-- RESEARCHER-OWNED DRAFT STUDIES MIGRATION
-- Phase 1: Database + Backend Enforcement
-- =====================================================

-- =====================================================
-- 1. ADD COLUMNS TO STUDIES TABLE
-- =====================================================

-- Add created_by column (nullable for existing CT.gov rows)
ALTER TABLE public.studies
ADD COLUMN created_by UUID NULL REFERENCES auth.users(id) ON DELETE SET NULL;

-- Add is_published column (default TRUE for existing CT.gov rows)
ALTER TABLE public.studies
ADD COLUMN is_published BOOLEAN NOT NULL DEFAULT TRUE;

-- Index for efficient filtering by published status and owner
CREATE INDEX idx_studies_is_published ON public.studies (is_published);
CREATE INDEX idx_studies_created_by ON public.studies (created_by);

-- =====================================================
-- 2. CREATE RESEARCHER ALLOWLIST TABLE
-- =====================================================

-- Manual DB admin-only table for non-.edu email allowlisting
CREATE TABLE public.researcher_allowlist_emails (
  email TEXT PRIMARY KEY
);

-- Enable RLS with no policies (only service role / DB admin can manage)
ALTER TABLE public.researcher_allowlist_emails ENABLE ROW LEVEL SECURITY;

-- No policies = only service role can SELECT/INSERT/UPDATE/DELETE

COMMENT ON TABLE public.researcher_allowlist_emails IS 'Manually managed allowlist of researcher emails (beyond .edu). Only DB admin/service role can modify.';

-- =====================================================
-- 3. CREATE RESEARCHER DETECTION FUNCTION
-- =====================================================

-- Function to check if current user is a researcher
-- Returns true if authenticated email ends with .edu OR is in allowlist
CREATE OR REPLACE FUNCTION public.is_researcher()
RETURNS BOOLEAN AS $$
DECLARE
  user_email TEXT;
BEGIN
  -- Get current user's email
  SELECT email INTO user_email
  FROM auth.users
  WHERE id = auth.uid();

  -- Return false if no user or no email
  IF user_email IS NULL THEN
    RETURN FALSE;
  END IF;

  -- Check if .edu email (case-insensitive)
  IF lower(user_email) LIKE '%.edu' THEN
    RETURN TRUE;
  END IF;

  -- Check if in allowlist (case-insensitive match)
  IF EXISTS (
    SELECT 1
    FROM public.researcher_allowlist_emails
    WHERE lower(email) = lower(user_email)
  ) THEN
    RETURN TRUE;
  END IF;

  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.is_researcher() IS 'Returns true if authenticated user has .edu email or is in researcher allowlist';

-- =====================================================
-- 4. REPLACE STUDIES SELECT POLICY
-- =====================================================

-- Drop existing public SELECT policy
DROP POLICY IF EXISTS "Studies are viewable by everyone" ON public.studies;

-- New SELECT policy: public can see published, owners can see their drafts
CREATE POLICY "Studies are viewable by public or owner"
  ON public.studies FOR SELECT
  TO authenticated, anon
  USING (
    is_published = TRUE
    OR (auth.uid() IS NOT NULL AND created_by = auth.uid())
  );

-- =====================================================
-- 5. ADD STUDIES INSERT POLICY (DRAFT-ON-CREATE)
-- =====================================================

-- Researchers can insert drafts only
-- Must set: created_by = auth.uid(), is_published = false, source != 'ctgov'
CREATE POLICY "Researchers can insert draft studies"
  ON public.studies FOR INSERT
  TO authenticated
  WITH CHECK (
    public.is_researcher()
    AND created_by = auth.uid()
    AND is_published = FALSE
    AND source IS NOT NULL
    AND btrim(source) <> ''
    AND lower(source) <> 'ctgov'
  );

-- =====================================================
-- 6. ADD STUDIES UPDATE POLICY (OWNER-MANAGED)
-- =====================================================

-- Owners can update their own studies
-- Continue to forbid spoofing CT.gov source
CREATE POLICY "Owners can update own studies"
  ON public.studies FOR UPDATE
  TO authenticated
  USING (created_by = auth.uid())
  WITH CHECK (
    created_by = auth.uid()
    AND lower(source) <> 'ctgov'
  );

-- =====================================================
-- 7. ADD STUDIES DELETE POLICY (OWNER-MANAGED)
-- =====================================================

-- Owners can delete their own studies
CREATE POLICY "Owners can delete own studies"
  ON public.studies FOR DELETE
  TO authenticated
  USING (created_by = auth.uid());

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON COLUMN public.studies.created_by IS 'User who created this study (NULL for CT.gov imports)';
COMMENT ON COLUMN public.studies.is_published IS 'Whether study is published (visible in public search). Defaults to TRUE for CT.gov imports.';
