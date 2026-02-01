-- =====================================================
-- PHASE 2: TASK FRAMEWORK (SURVEYS)
-- Adds tasks JSONB to studies and task_submissions table
-- =====================================================

-- =====================================================
-- 1. ADD TASKS FIELD TO STUDIES
-- =====================================================

-- Tasks stored as JSONB array on studies
-- Structure: [{ id, type, title, pages: [{ id, title, blocks: [...] }] }]
ALTER TABLE public.studies
ADD COLUMN tasks JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.studies.tasks IS 'Array of task definitions. Each task has id, type (survey), title, and pages with blocks.';

-- =====================================================
-- 2. CREATE TASK_SUBMISSIONS TABLE
-- =====================================================

CREATE TABLE public.task_submissions (
  id BIGSERIAL PRIMARY KEY,
  study_id BIGINT NOT NULL REFERENCES public.studies(id) ON DELETE CASCADE,
  task_id TEXT NOT NULL,  -- Matches task.id in studies.tasks JSONB
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  responses JSONB NOT NULL DEFAULT '{}'::jsonb,  -- Keyed by block ID
  submitted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

  -- Single submission per user per task for MVP
  UNIQUE(study_id, task_id, user_id)
);

-- Indexes
CREATE INDEX idx_task_submissions_study_id ON public.task_submissions (study_id);
CREATE INDEX idx_task_submissions_user_id ON public.task_submissions (user_id);
CREATE INDEX idx_task_submissions_task_id ON public.task_submissions (task_id);

COMMENT ON TABLE public.task_submissions IS 'Participant survey responses for study tasks';
COMMENT ON COLUMN public.task_submissions.task_id IS 'Matches task.id in studies.tasks JSONB';
COMMENT ON COLUMN public.task_submissions.responses IS 'Survey responses keyed by block ID';

-- =====================================================
-- 3. RLS POLICIES FOR TASK_SUBMISSIONS
-- =====================================================

ALTER TABLE public.task_submissions ENABLE ROW LEVEL SECURITY;

-- Participants can view their own submissions
CREATE POLICY "Users can view own task submissions"
  ON public.task_submissions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Participants can insert submissions (must be approved + consented)
CREATE POLICY "Approved participants can submit tasks"
  ON public.task_submissions FOR INSERT
  TO authenticated
  WITH CHECK (
    auth.uid() = user_id
    AND EXISTS (
      SELECT 1 FROM public.participation_requests pr
      WHERE pr.study_id = task_submissions.study_id
      AND pr.user_id = auth.uid()
      AND pr.status = 'approved'
      AND pr.consent_acknowledged_at IS NOT NULL
    )
  );

-- Study owners can view all submissions for their studies
CREATE POLICY "Study owners can view task submissions"
  ON public.task_submissions FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.studies
      WHERE studies.id = task_submissions.study_id
      AND studies.created_by = auth.uid()
    )
  );
