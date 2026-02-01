# Study Task Framework (Voice Recording + Surveys) - Implementation Spec

## Goal
Enable researchers to define study tasks (surveys now, audio later) and collect participant responses with explicit consent, while keeping security and data ownership enforced by Supabase RLS.

## Design Principles (Match Current Codebase)
- **Supabase-first mutations**: All task/consent/submission writes go through Supabase SDK so RLS is the source of truth.
- **FastAPI read-only**: Avoid new write endpoints unless FastAPI gains JWT verification and mirrors RLS checks.
- **Monolithic pages**: Each new route is a single Svelte file containing state + handlers + UI.
- **Minimal abstractions**: Prefer clear, local code over shared helpers unless a page becomes unwieldy.

---

## Part 1: Participation Management for Researchers

### Consent Model (Simplest Possible)
- **One consent per study**.
- Consent is stored as a **media item** tagged with `kind: "consent"` in `studies.media`.
- Participant acknowledgment is stored on `participation_requests` as a timestamp.
- Researchers do **not** approve consent separately. They only approve participation.

### Required Schema Changes
**`participation_requests`** (add fields)
- `consent_acknowledged_at` TIMESTAMPTZ

### Researcher UI/Actions
- View participation requests for their studies.
- Approve/reject participation (existing manual flow, UI planned).
- See consent status: `consent_acknowledged_at` present or not.

### Frontend Gating
- Participant must be `approved` **and** have `consent_acknowledged_at` to access tasks.

---

## Part 2: Task Creation Framework (Tasks Stored on Study)

### Studies Table Additions
**`studies`** (add field)
- `tasks` JSONB DEFAULT '[]'::jsonb

### Task JSON Schema (Stored in `studies.tasks`)
Tasks are a **superset**: surveys, audio, future games, etc.

```json
[
  {
    "id": "task_survey_1",
    "type": "survey",
    "title": "Baseline Survey",
    "order_index": 1,
    "is_required": true,
    "is_active": true,
    "pages": [
      {
        "id": "page_intro",
        "title": "Welcome",
        "blocks": [
          {"id": "blk_welcome", "type": "text", "text": "Thanks for participating."}
        ]
      },
      {
        "id": "page_q1",
        "title": "Background",
        "blocks": [
          {"id": "q_age", "type": "short_text", "label": "How old are you?", "required": true},
          {"id": "q_gender", "type": "single_choice", "label": "Gender?", "options": ["Female", "Male", "Non-binary", "Prefer not to say"], "required": true},
          {"id": "q_stress", "type": "scale", "label": "Stress today?", "min": 1, "max": 5, "min_label": "Low", "max_label": "High"}
        ]
      }
    ]
  },
  {
    "id": "task_audio_1",
    "type": "audio",
    "title": "Voice Reflection",
    "order_index": 2,
    "is_required": false,
    "is_active": true,
    "max_duration_seconds": 180,
    "max_attempts": 3,
    "prompt": "Describe your experience in your own words."
  }
]
```

### Survey Block Types (MVP)
- `text`
- `short_text`
- `long_text`
- `single_choice`
- `multi_choice`
- `scale`

### Task Authoring Rules
- `id` is **stable** and string-based (not an array index).
- `order_index` controls display order.
- Keep tasks and blocks small and JSON-friendly.

### Researcher UI/Actions
- Add/edit/reorder tasks within the study edit form.
- For survey tasks: add pages and blocks.
- For audio tasks: set prompt and max duration/attempts.

---

## Part 3: Submit Task Responses (Survey + Audio)

### New Table: `study_task_responses`
Store participant task submissions and review status.

**Fields**
- `id` BIGSERIAL PK
- `participation_request_id` BIGINT FK → `participation_requests.id`
- `study_id` BIGINT FK → `studies.id`
- `user_id` UUID FK → `auth.users.id`
- `task_id` TEXT NOT NULL  -- matches tasks[].id
- `attempt_number` INTEGER DEFAULT 1
- `response_json` JSONB  -- for survey task answers
- `recording_path` TEXT  -- for audio tasks
- `recording_mime` TEXT
- `recording_size_bytes` INTEGER
- `duration_seconds` INTEGER
- `status` TEXT DEFAULT 'submitted'  -- submitted | accepted | needs_retry | rejected
- `reviewer_id` UUID FK → `auth.users.id` (nullable)
- `reviewer_notes` TEXT
- `submitted_at` TIMESTAMPTZ DEFAULT now()
- `reviewed_at` TIMESTAMPTZ

**Constraints**
- UNIQUE `(participation_request_id, task_id, attempt_number)`

**Indexes**
- `(study_id)`
- `(participation_request_id)`
- `(user_id)`

### Storage Bucket: `study-recordings`
**Configuration**
- Public: `false`
- Size limit: 50MB
- Allowed MIME: `audio/webm`, `audio/mp4`, `audio/mpeg`, `audio/wav`, `audio/ogg`
- Path: `{study_id}/{participation_request_id}/{response_id}.webm`

### RLS Policies (Required)
**`study_task_responses`**
- **SELECT**: user owns row OR study owner.
- **INSERT**: user owns row AND
  - participation request approved
  - consent_acknowledged_at is NOT NULL
  - participation_request_id belongs to auth.uid()
- **UPDATE**:
  - participant can update own row only if you allow editing (MVP: no edits)
  - study owner can set `status`, `reviewer_notes`, `reviewed_at`, `reviewer_id`
- **DELETE**: optional; only before review (`status IN ('submitted','needs_retry')`).

**Storage (`study-recordings`)**
- **SELECT**: study owner OR participant who owns the participation_request.
- **INSERT**: uploader owns participation_request AND participation approved AND consent acknowledged.
- **DELETE**: uploader OR study owner (optional).

### Submission Flow
**Survey task**
1) Participant completes pages.
2) Final confirmation screen appears.
3) On confirm, create `study_task_responses` row with `response_json` and `status = submitted`.

**Audio task**
1) Create response row with `attempt_number` and status `submitted`.
2) Upload audio to `study-recordings/{study_id}/{participation_request_id}/{response_id}.webm`.
3) Update response row with `recording_path`, metadata, and `duration_seconds`.
4) Researcher reviews and sets status: `accepted`, `needs_retry`, or `rejected`.

---

## Frontend Routes (Monolithic Pages)
- `frontend-sv/src/routes/study/[id]/consent/+page.svelte`
- `frontend-sv/src/routes/study/[id]/tasks/+page.svelte`
- `frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte`

---

## Supabase Client Functions (Suggested Additions)
In `frontend-sv/src/lib/supabase.js`:
- `getParticipationRequestForStudy(studyId)`
- `acknowledgeConsent(participationRequestId, userAgent)`
- `listTaskResponses(participationRequestId)`
- `createTaskResponse(responseData)`
- `updateTaskResponse(id, updates)`
- `uploadStudyRecording(studyId, participationRequestId, responseId, file)`

---

## Open Decisions
- Allow participants to edit submissions before review, or only add new attempts? (MVP: only new attempts)
- Should rejected submissions allow a retry, or only `needs_retry`?
MVP recommendation

Make rejected final and use needs_retry for “try again.”
This keeps meanings clean and gives researchers a deliberate “retry” action.