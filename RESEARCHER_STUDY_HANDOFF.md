# Researcher Study Seed + Ownership Handoff

This doc covers:
1) Adding the `compensation` field to `public.studies`
2) Seeding **two** copies of the Bridge2AI study
3) Assigning ownership (`created_by`) to:
   - `le.nathan.trung@gmail.com`
   - `jennyk@mit.edu`
4) Sending Kaley (`voice_study@mit.edu`) an email “recover account / set password” link

---

## 0) Prerequisite: apply the `compensation` migration

Migration file:
- `supabase/migrations/20260115000000_add_compensation_to_studies.sql`

Apply locally:

```bash
supabase db reset
```

---

## 1) Seed the duplicated study (2 rows)

Run this SQL (Supabase SQL editor or `psql`). It inserts two rows with different `source_id` values so they can coexist.

```sql
INSERT INTO public.studies (
  source,
  source_id,
  title,
  description,
  eligibility_criteria,
  recruiting_status,
  study_type,
  conditions,
  locations,
  contacts,
  compensation,
  created_by,
  is_published,
  last_synced_at,
  raw_json
) VALUES
(
  'researcher',
  'BRIDGE2AI',
  'Bridge2AI Voice Mood Disorder Study',
  'The human voice is unique to each individual and contains audio features that have been linked to diseases such as Parkinson’s, dementia, mood disorders, and certain cancers. Given the advances in artificial intelligence, there is increased interest in using voice in the diagnosis of disease. Although early results are promising, many limitations remain including the limited size of databases available, and their questionable quality and diversity. The main purpose of this study is to build a large open science database of human voices, speech and respiratory sounds, other health data, and associated metadata. This database will respect applicable best ethical practices and ensure representation of a diverse population to fuel artificial intelligence research related to voice. Some of the information collected will further be shared with the general public in full open access, in a de-identified or aggregated form.\n\nWe are looking for participants to participate in a large research study on diagnosing mental health disorders from voice recordings at MIT, and are welcome to participate onsite or remotely. Enroll by accessing the QR code on the flyer attached.',
  'Inclusion Criteria:\n- Official diagnosis of major depressive disorder, anxiety disorder or bipolar disorder (I or II) from a clinician/psychiatrist.\n- Age: 18 years or older.',
  'recruiting',
  'observational',
  ARRAY[
    'major depression',
    'major depressive disorder',
    'anxiety disorders',
    'mood disorders',
    'bipolar i',
    'bipolar ii'
  ]::text[],
  '[{"lat":42.360091,"lon":-71.09416,"city":"Cambridge","state":"Massachusetts","country":"United States","facility_name":"Massachusetts Institute of Technology"}]'::jsonb,
  '[{"name":"Kaley Jenney","email":"voice_study@mit.edu","phone_number":""}]'::jsonb,
  '{"type":"Gift Card","amount":"Participants will only receive compensation after completion of the study.","details":""}'::jsonb,
  NULL,
  TRUE,
  NOW(),
  '{
    "legacy_study_uuid":"df44d203-0b88-473a-86df-ba313ecf8d94",
    "study_id":"BRIDGE2AI",
    "note":"seeded copy #1",
    "intended_owner_email":"jennyk@mit.edu"
  }'::jsonb
),
(
  'researcher',
  'BRIDGE2AI_DUP',
  'Bridge2AI Voice Mood Disorder Study',
  'The human voice is unique to each individual and contains audio features that have been linked to diseases such as Parkinson’s, dementia, mood disorders, and certain cancers. Given the advances in artificial intelligence, there is increased interest in using voice in the diagnosis of disease. Although early results are promising, many limitations remain including the limited size of databases available, and their questionable quality and diversity. The main purpose of this study is to build a large open science database of human voices, speech and respiratory sounds, other health data, and associated metadata. This database will respect applicable best ethical practices and ensure representation of a diverse population to fuel artificial intelligence research related to voice. Some of the information collected will further be shared with the general public in full open access, in a de-identified or aggregated form.\n\nWe are looking for participants to participate in a large research study on diagnosing mental health disorders from voice recordings at MIT, and are welcome to participate onsite or remotely. Enroll by accessing the QR code on the flyer attached.',
  'Inclusion Criteria:\n- Official diagnosis of major depressive disorder, anxiety disorder or bipolar disorder (I or II) from a clinician/psychiatrist.\n- Age: 18 years or older.',
  'recruiting',
  'observational',
  ARRAY[
    'major depression',
    'major depressive disorder',
    'anxiety disorders',
    'mood disorders',
    'bipolar i',
    'bipolar ii'
  ]::text[],
  '[{"lat":42.360091,"lon":-71.09416,"city":"Cambridge","state":"Massachusetts","country":"United States","facility_name":"Massachusetts Institute of Technology"}]'::jsonb,
  '[{"name":"Kaley Jenney","email":"voice_study@mit.edu","phone_number":""}]'::jsonb,
  '{"type":"Gift Card","amount":"Participants will only receive compensation after completion of the study.","details":""}'::jsonb,
  NULL,
  TRUE,
  NOW(),
  '{
    "legacy_study_uuid":"df44d203-0b88-473a-86df-ba313ecf8d94",
    "study_id":"BRIDGE2AI",
    "note":"seeded copy #2 (duplicate)",
    "intended_owner_email":"le.nathan.trung@gmail.com"
  }'::jsonb
);

-- Verify
SELECT id, source, source_id, title, created_by, created_at
FROM public.studies
WHERE source = 'researcher'
  AND source_id IN ('BRIDGE2AI', 'BRIDGE2AI_DUP')
ORDER BY id;
```

---

## 2) Assign ownership (`created_by`) to specific emails

Ownership assignment requires the target users to exist in `auth.users`.

### 2.1 Verify users exist

```sql
SELECT id, email, created_at
FROM auth.users
WHERE lower(email) IN (lower('le.nathan.trung@gmail.com'), lower('jennyk@mit.edu'));
```

### 2.2 Assign `BRIDGE2AI` to `jennyk@mit.edu`

```sql
UPDATE public.studies s
SET created_by = u.id
FROM auth.users u
WHERE s.source = 'researcher'
  AND s.source_id = 'BRIDGE2AI'
  AND lower(u.email) = lower('jennyk@mit.edu');
```

### 2.3 Assign `BRIDGE2AI_DUP` to `le.nathan.trung@gmail.com`

```sql
UPDATE public.studies s
SET created_by = u.id
FROM auth.users u
WHERE s.source = 'researcher'
  AND s.source_id = 'BRIDGE2AI_DUP'
  AND lower(u.email) = lower('le.nathan.trung@gmail.com');
```

### 2.4 Verify ownership

```sql
SELECT s.id, s.source_id, s.title, s.created_by, u.email
FROM public.studies s
LEFT JOIN auth.users u ON u.id = s.created_by
WHERE s.source = 'researcher'
  AND s.source_id IN ('BRIDGE2AI', 'BRIDGE2AI_DUP')
ORDER BY s.id;
```

---

## 3) Send Kaley a “recover account / set password” link

**Password” link**

If Kaley doesn’t exist in auth.users yet (common when migrating from another Supabase project), you need to create the user in the new project and then send a recovery link so she can set a password and log in.

You should not try to insert rows directly into auth.users via SQL.

### Option 1 (simplest): Supabase Dashboard (no code)

Open Supabase Dashboard → Authentication → Users

Click Add user (or Invite user if available)

Enter Kaley’s email (e.g. voice_study@mit.edu)

Use Send password recovery / Send invite link

Supabase emails her a link to set/reset her password

---

## Optional: hide the duplicate from public search

```sql
UPDATE public.studies
SET is_published = FALSE
WHERE source = 'researcher' AND source_id = 'BRIDGE2AI_DUP';
```
