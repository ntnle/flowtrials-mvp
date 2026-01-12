-- =====================================================
-- INITIAL SCHEMA MIGRATION
-- Clinical Trials Search Platform
-- =====================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For text search performance

-- =====================================================
-- STUDIES TABLE
-- =====================================================

CREATE TABLE public.studies (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  source_id TEXT,
  title TEXT NOT NULL,
  brief_summary TEXT,
  detailed_description TEXT,
  eligibility_criteria TEXT,
  recruiting_status TEXT,
  study_type TEXT,
  interventions JSONB DEFAULT '[]'::jsonb,
  conditions TEXT[] NOT NULL DEFAULT '{}',
  locations JSONB DEFAULT '[]'::jsonb,
  contacts JSONB DEFAULT '[]'::jsonb,
  site_zips TEXT[] NOT NULL DEFAULT '{}',
  raw_json JSONB,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  description TEXT
);

-- Indexes for search performance
CREATE INDEX idx_studies_conditions ON public.studies USING GIN (conditions);
CREATE INDEX idx_studies_site_zips ON public.studies USING GIN (site_zips);
CREATE INDEX idx_studies_recruiting_status ON public.studies (recruiting_status);
CREATE INDEX idx_studies_source ON public.studies (source, source_id);
CREATE INDEX idx_studies_title_trgm ON public.studies USING GIN (title gin_trgm_ops);

-- =====================================================
-- USER PROFILES TABLE
-- =====================================================

CREATE TABLE public.user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Basic Demographics
  age INTEGER,
  gender TEXT,
  race TEXT,
  ethnicity TEXT,

  -- Medical Conditions
  conditions TEXT[] DEFAULT '{}',
  other_condition TEXT,

  -- Current Medications
  medications TEXT,
  allergies TEXT,

  -- Previous Trial Experience
  previous_trials TEXT,
  trial_experience TEXT,

  -- Location & Travel
  zip_code TEXT,
  travel_radius INTEGER DEFAULT 25,

  -- Availability
  weekday_availability BOOLEAN DEFAULT false,
  weekend_availability BOOLEAN DEFAULT false,
  preferred_time_of_day TEXT,

  -- Preferences
  in_person_willing BOOLEAN DEFAULT false,
  remote_willing BOOLEAN DEFAULT false,
  compensation_importance INTEGER DEFAULT 3,

  -- Lifestyle Factors
  smoker TEXT,
  alcohol_use TEXT,
  exercise_frequency TEXT,

  -- Health Insurance
  has_insurance TEXT,
  insurance_type TEXT,

  -- Additional Info
  additional_notes TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Index for profile lookups
CREATE INDEX idx_user_profiles_conditions ON public.user_profiles USING GIN (conditions);
CREATE INDEX idx_user_profiles_zip_code ON public.user_profiles (zip_code);

-- =====================================================
-- PARTICIPATION REQUESTS TABLE
-- =====================================================

CREATE TABLE public.participation_requests (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  study_id BIGINT NOT NULL REFERENCES public.studies(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'pending' NOT NULL,
  notes TEXT,
  contact_preference TEXT, -- email, phone, portal
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

  -- Ensure user can only request once per study
  UNIQUE(user_id, study_id)
);

-- Indexes for participation requests
CREATE INDEX idx_participation_requests_user_id ON public.participation_requests (user_id);
CREATE INDEX idx_participation_requests_study_id ON public.participation_requests (study_id);
CREATE INDEX idx_participation_requests_status ON public.participation_requests (status);

-- Status check constraint
ALTER TABLE public.participation_requests
  ADD CONSTRAINT participation_requests_status_check
  CHECK (status IN ('pending', 'contacted', 'approved', 'rejected', 'withdrawn'));

-- =====================================================
-- USER SAVED STUDIES TABLE
-- =====================================================

CREATE TABLE public.user_saved_studies (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  study_id BIGINT NOT NULL REFERENCES public.studies(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

  PRIMARY KEY (user_id, study_id)
);

-- Index for quick lookups
CREATE INDEX idx_user_saved_studies_user_id ON public.user_saved_studies (user_id);

-- =====================================================
-- USER MATCH ANSWERS TABLE
-- =====================================================

CREATE TABLE public.user_match_answers (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  answers JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all user-related tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participation_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_saved_studies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_match_answers ENABLE ROW LEVEL SECURITY;

-- Studies are public (read-only for users)
ALTER TABLE public.studies ENABLE ROW LEVEL SECURITY;

-- Studies: Anyone can read
CREATE POLICY "Studies are viewable by everyone"
  ON public.studies FOR SELECT
  TO authenticated, anon
  USING (true);

-- User Profiles: Users can only see and edit their own profile
CREATE POLICY "Users can view own profile"
  ON public.user_profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON public.user_profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON public.user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- Participation Requests: Users can only see and manage their own
CREATE POLICY "Users can view own participation requests"
  ON public.participation_requests FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own participation requests"
  ON public.participation_requests FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own participation requests"
  ON public.participation_requests FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id);

-- Saved Studies: Users can only see and manage their own
CREATE POLICY "Users can view own saved studies"
  ON public.user_saved_studies FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own saved studies"
  ON public.user_saved_studies FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own saved studies"
  ON public.user_saved_studies FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Match Answers: Users can only see and manage their own
CREATE POLICY "Users can view own match answers"
  ON public.user_match_answers FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own match answers"
  ON public.user_match_answers FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own match answers"
  ON public.user_match_answers FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id);

-- =====================================================
-- FUNCTIONS & TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER set_updated_at_studies
  BEFORE UPDATE ON public.studies
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_user_profiles
  BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_participation_requests
  BEFORE UPDATE ON public.participation_requests
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_updated_at_user_match_answers
  BEFORE UPDATE ON public.user_match_answers
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_updated_at();

-- Function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id)
  VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile when user signs up
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE public.studies IS 'Clinical trial studies from various sources (ClinicalTrials.gov, internal)';
COMMENT ON TABLE public.user_profiles IS 'Extended user profile data beyond auth.users';
COMMENT ON TABLE public.participation_requests IS 'User requests to participate in studies';
COMMENT ON TABLE public.user_saved_studies IS 'Studies saved/bookmarked by users';
COMMENT ON TABLE public.user_match_answers IS 'User responses to matching questionnaire';

COMMENT ON COLUMN public.participation_requests.status IS 'Request status: pending, contacted, approved, rejected, withdrawn';
