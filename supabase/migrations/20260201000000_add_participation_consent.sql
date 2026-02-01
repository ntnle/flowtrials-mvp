-- =====================================================
-- PHASE 1: PARTICIPATION MANAGEMENT & CONSENT
-- Adds consent tracking and researcher visibility
-- =====================================================

-- =====================================================
-- 1. ADD CONSENT FIELDS TO PARTICIPATION_REQUESTS
-- =====================================================

-- Track when participant acknowledged consent for study
ALTER TABLE public.participation_requests
ADD COLUMN consent_acknowledged_at TIMESTAMPTZ NULL;

-- Index for filtering by consent status
CREATE INDEX idx_participation_requests_consent ON public.participation_requests (consent_acknowledged_at);

COMMENT ON COLUMN public.participation_requests.consent_acknowledged_at IS 'Timestamp when participant acknowledged study consent. NULL means not yet acknowledged.';

-- =====================================================
-- 2. ADD RLS POLICY FOR STUDY OWNERS TO VIEW REQUESTS
-- =====================================================

-- Study owners can SELECT participation requests for their studies
CREATE POLICY "Study owners can view participation requests"
  ON public.participation_requests FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.studies
      WHERE studies.id = participation_requests.study_id
      AND studies.created_by = auth.uid()
    )
  );

-- Study owners can UPDATE participation requests for their studies (approve/reject)
CREATE POLICY "Study owners can update participation requests"
  ON public.participation_requests FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.studies
      WHERE studies.id = participation_requests.study_id
      AND studies.created_by = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.studies
      WHERE studies.id = participation_requests.study_id
      AND studies.created_by = auth.uid()
    )
  );

-- =====================================================
-- 3. ALLOW STUDY OWNERS TO VIEW PARTICIPANT PROFILES
-- =====================================================

-- Study owners can view profiles of users who requested to participate in their studies
CREATE POLICY "Study owners can view participant profiles"
  ON public.user_profiles FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.participation_requests pr
      JOIN public.studies s ON s.id = pr.study_id
      WHERE pr.user_id = user_profiles.id
      AND s.created_by = auth.uid()
    )
  );
