-- =====================================================
-- SEED DATA FOR LOCAL DEVELOPMENT
-- =====================================================

-- Insert demo studies (migrated from FastAPI seed data)
INSERT INTO public.studies (
  source,
  source_id,
  title,
  brief_summary,
  detailed_description,
  eligibility_criteria,
  recruiting_status,
  study_type,
  interventions,
  conditions,
  locations,
  contacts,
  site_zips,
  description
) VALUES
(
  'internal',
  NULL,
  'Remote Survey on Social Media Ads for Clinical Trial Recruitment',
  'Online survey examining how social media advertising influences awareness and willingness to join clinical trials.',
  'Participants complete a 15-20 minute remote survey about exposure to research ads on platforms like Facebook, Instagram, and TikTok. The study measures perceived credibility, clarity of information, and likelihood of contacting a study team.',
  'Adults 18+ who use social media at least weekly, located in the United States, able to complete an online survey in English',
  'Recruiting',
  'Observational',
  '[]'::jsonb,
  ARRAY['clinical-trial-recruitment', 'social-media', 'online-advertising'],
  '[{"facility_name": "Remote (Online Survey)", "city": "Remote", "country": "USA"}]'::jsonb,
  '[]'::jsonb,
  ARRAY[]::TEXT[],
  'Online survey examining how social media advertising influences awareness and willingness to join clinical trials.'
),
(
  'internal',
  NULL,
  'Remote Survey Comparing Patient Portal vs Email Outreach',
  'Survey study comparing which online outreach channel is more effective for motivating clinical trial inquiries.',
  'Participants review brief, de-identified examples of trial invitations delivered via patient portal messages and email. The survey measures trust, comprehension, and intent to respond across channels.',
  'Adults 18+ with prior experience using a patient portal or receiving healthcare emails, located in the United States, access to a computer or smartphone',
  'Recruiting',
  'Observational',
  '[]'::jsonb,
  ARRAY['clinical-trial-recruitment', 'patient-portals', 'email-outreach'],
  '[{"facility_name": "Remote (Online Survey)", "city": "Remote", "country": "USA"}]'::jsonb,
  '[]'::jsonb,
  ARRAY[]::TEXT[],
  'Survey study comparing which online outreach channel is more effective for motivating clinical trial inquiries.'
),
(
  'internal',
  NULL,
  'Remote Survey on Telehealth Platform Messaging',
  'Online survey assessing how in-app messaging within telehealth platforms affects interest in clinical trial participation.',
  'Participants review short, de-identified message examples delivered through telehealth apps and rate trust, clarity, and likelihood of responding. The study evaluates which message styles improve recruitment intent.',
  'Adults 18+ who have used telehealth in the past 12 months, located in the United States, able to complete a remote survey',
  'Recruiting',
  'Observational',
  '[]'::jsonb,
  ARRAY['clinical-trial-recruitment', 'telehealth', 'in-app-messaging'],
  '[{"facility_name": "Remote (Online Survey)", "city": "Remote", "country": "USA"}]'::jsonb,
  '[]'::jsonb,
  ARRAY[]::TEXT[],
  'Online survey assessing how in-app messaging within telehealth platforms affects interest in clinical trial participation.'
);

-- Note: User profiles, saved studies, and participation requests will be created
-- through the application as users sign up and interact with the system
