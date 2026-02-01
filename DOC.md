# Flow Trials - Architecture Documentation

## What We're Building

Clinical trial discovery and participation platform where users search studies, request participation, and researchers manage their own trials with participant data collection.

---

## MVP Feature Set (Current)

### Participant
- Study search with keyword + semantic scoring
- Browse/filter studies (conditions, location, recruiting status)
- Study detail pages with full information
- User authentication (Supabase Auth)
- Participant profiles (10-section demographic form)
- Participation request workflow (pending → approved/rejected/withdrawn)

### Researcher
- Researcher detection (.edu emails + manual allowlist)
- Draft study creation (unpublished until ready)
- Study editing and publishing workflow
- Media upload (images/PDFs, max 5MB, 10 files per study)
- Compensation field (JSONB for flexible formats)

### AI
- Plain title generation (cached in Postgres)
- Plain summary generation (cached)
- Eligibility quiz generation (cached)

---

## WIP Features (Next Up)

### Phase 1: Participation Management (Researcher-Facing) ✓ COMPLETED
- ✓ Consent acknowledgment tracking (`consent_acknowledged_at` column on `participation_requests`)
- ✓ Researcher UI to approve/reject participation (Profile → My Studies → Requests button)
- ✓ RLS policies for study owners to SELECT/UPDATE participation requests for their studies
- ✓ Participant gating: must be approved AND consent-acknowledged to access tasks
- ✓ Researcher can reset consent if consent documents change

### Phase 2: Task Framework (Surveys First) ✓ COMPLETED
- ✓ Tasks stored on `studies.tasks` JSONB (pages + blocks)
- ✓ Survey tasks with text and question blocks (no branching)
- ✓ Final submit confirmation per task (no auto-submit)
- ✓ Task submissions stored in `task_submissions` table
- ✓ Researcher task editor (Profile → Edit Study → Tasks section)
- ✓ Participant task list and survey runner (/study/:id/tasks)

### Phase 3: Audio Tasks (Later)
- Audio recording task type with attempts and review status
- Private `study-recordings` storage bucket with RLS

---

## Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     VERCEL (Frontend)                       │
│                  Svelte SPA - Static Deploy                 │
│                                                             │
│  • Routes: /, /browse, /study/:id, /profile, /signup, /login, /bio │
│  • Monolithic pages (state + handlers + UI in one file)    │
│  • Direct Supabase client (auth, CRUD, storage, RLS)       │
│  • Calls FastAPI for search/AI features only               │
└─────────────────────────────────────────────────────────────┘
                              ↓ ↑
                    ┌─────────┴─┴─────────┐
                    │   Supabase Client   │
                    │   (browser SDK)     │
                    └─────────┬─┬─────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│                  SUPABASE (Data Layer)                      │
│                     PostgreSQL + Auth                       │
│                                                             │
│  • Auth: User accounts (auth.users)                        │
│  • Tables: studies, user_profiles, participation_requests  │
│  • RLS: Row-level security policies                        │
│  • Storage: study-media, study-recordings (with RLS)       │
│  • Functions: is_researcher(), handle_updated_at()         │
└─────────────────────────────────────────────────────────────┘
                              ↑ ↓
┌─────────────────────────────────────────────────────────────┐
│                 RENDER (Backend API)                        │
│              FastAPI - Python Service                       │
│                                                             │
│  • Search: POST /search (keyword + semantic scoring)       │
│  • Study CRUD: GET /studies/:id (read-only for frontend)   │
│  • AI Features: /ai/plain-title, /ai/study-summary, /ai/eligibility-quiz │
│  • Ingestion: Scripts sync CT.gov → Supabase               │
│  • Direct DB connection (pooler with SSL)                  │
└─────────────────────────────────────────────────────────────┘
```

### Responsibility Boundaries

| Layer | Owns | Does NOT Own |
|-------|------|--------------|
| **Supabase** | Auth, user data, participation requests, researcher studies, file storage | Search logic, AI features, CT.gov ingestion |
| **FastAPI (Render)** | Search/scoring, AI generation (titles/summaries/quizzes), CT.gov sync, published study reads | Auth, user profiles, participation CRUD, researcher study mutations |
| **Svelte (Vercel)** | UI/UX, auth flows, profile management, participation requests | Search scoring, AI generation |

### Communication Patterns

**Frontend → Supabase (via `@supabase/supabase-js`):**
- ✅ **Auth**: signUp, signIn, signOut, session management
- ✅ **User profiles**: Read/write to `user_profiles` table
- ✅ **Participation requests**: CRUD on `participation_requests` table
- ✅ **Researcher operations**: Create/edit/delete draft studies, publish/unpublish
- ✅ **Storage**: Upload/delete files to `study-media` bucket
- ✅ **RLS enforcement**: All operations subject to Row-Level Security policies

**Frontend → FastAPI (via `fetch()`):**
- ✅ **Search**: `POST /search` - keyword + semantic scoring
- ✅ **Study retrieval**: `GET /studies/:id` - read published studies (primary method)
- ✅ **AI features**:
  - `POST /ai/plain-title` - Generate simplified titles
  - `POST /ai/study-summary` - Generate plain summaries
  - `POST /ai/eligibility-quiz` - Generate eligibility quizzes
- ❌ **No write operations** - FastAPI is read-only for frontend

**Mixed usage patterns:**
- **Study detail page**: Tries FastAPI `GET /studies/:id` first (published studies), falls back to Supabase direct query if authenticated (for draft studies)
- **Browse page**: FastAPI search returns studies, then calls AI endpoints to backfill missing plain titles

**Key Principle:** Frontend uses Supabase SDK for ALL mutations (create/update/delete). FastAPI is for search, AI generation, and reading published studies only.

### Frontend Operation Reference Table

Quick reference for where each operation goes:

| Operation | Method | Destination | File | Notes |
|-----------|--------|-------------|------|-------|
| **Auth** | | | | |
| Sign up | Supabase SDK | Supabase Auth | `supabase.js` | Creates auth.users + user_profiles |
| Sign in | Supabase SDK | Supabase Auth | `supabase.js` | Returns session token |
| Sign out | Supabase SDK | Supabase Auth | `supabase.js` | Clears session |
| Get current user | Supabase SDK | Supabase Auth | `supabase.js` | From session |
| **Search & Browse** | | | | |
| Search studies | `fetch()` | FastAPI `/search` | `api.js` | Keyword + semantic scoring |
| Get study by ID | `fetch()` | FastAPI `/studies/:id` | `api.js` | Published studies only |
| Get draft study | Supabase SDK | PostgreSQL `studies` | `supabase.js` | Fallback for unpublished |
| **AI Features** | | | | |
| Generate plain title | `fetch()` | FastAPI `/ai/plain-title` | `api.js` | Cached in DB |
| Generate summary | `fetch()` | FastAPI `/ai/study-summary` | `api.js` | Cached in DB |
| Generate quiz | `fetch()` | FastAPI `/ai/eligibility-quiz` | `api.js` | Cached in DB |
| **User Profiles** | | | | |
| Get profile | Supabase SDK | PostgreSQL `user_profiles` | `supabase.js` | RLS: own profile only |
| Update profile | Supabase SDK | PostgreSQL `user_profiles` | `supabase.js` | RLS: own profile only |
| **Participation** | | | | |
| Create request | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: authenticated |
| Get my requests | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: own requests |
| Withdraw request | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: own requests |
| Get my participation for study | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: own requests |
| Acknowledge consent | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | Sets consent_acknowledged_at |
| **Researcher Participation Mgmt** | | | | |
| Get study requests | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: study owner |
| Approve/reject request | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: study owner |
| Reset consent | Supabase SDK | PostgreSQL `participation_requests` | `supabase.js` | RLS: study owner |
| **Researcher** | | | | |
| Check if researcher | Supabase RPC | PostgreSQL function | `supabase.js` | Checks .edu or allowlist |
| Get my studies | Supabase SDK | PostgreSQL `studies` | `supabase.js` | RLS: created_by = me |
| Create draft study | Supabase SDK | PostgreSQL `studies` | `supabase.js` | RLS: is_researcher() |
| Update study | Supabase SDK | PostgreSQL `studies` | `supabase.js` | RLS: created_by = me |
| Delete study | Supabase SDK | PostgreSQL `studies` | `supabase.js` | RLS: created_by = me |
| Publish study | Supabase SDK | PostgreSQL `studies` | `supabase.js` | UPDATE is_published |
| **Storage** | | | | |
| Upload media | Supabase SDK | Storage `study-media` | `supabase.js` | RLS: researchers only |
| Delete media | Supabase SDK | Storage `study-media` | `supabase.js` | RLS: study owners only |
| Get public URL | Supabase SDK | Storage `study-media` | `supabase.js` | Public bucket |

### Data Flow Examples

**Example 1: User searches for studies**
```
User enters "diabetes" → searchStudies() in api.js
  → POST http://localhost:8000/search
    → FastAPI search_module.py
      → PostgreSQL query (studies table)
        → Returns ranked results
  → Frontend displays study cards
```

**Example 2: User requests to participate**
```
User clicks "Participate" → createParticipationRequest() in supabase.js
  → Supabase SDK .from('participation_requests').insert()
    → PostgreSQL INSERT
      → RLS policy checks: auth.uid() exists
        → Creates row with status='pending'
  → Frontend redirects to /profile
```

**Example 3: Researcher creates draft study**
```
Researcher fills form → createDraftStudy() in supabase.js
  → Supabase SDK .from('studies').insert({created_by: auth.uid(), is_published: false})
    → PostgreSQL INSERT
      → RLS policy checks: is_researcher() AND created_by = auth.uid()
        → Creates draft study
  → Frontend shows in "My Studies" tab
```

**Example 4: Study page loads published study**
```
User visits /study/123 → getStudyById(123) in api.js
  → GET http://localhost:8000/studies/123
    → FastAPI search_module.py
      → PostgreSQL SELECT WHERE id=123 AND is_published=true
        → Returns full study object
  → Frontend displays study details
```

**Example 5: Study page loads draft study (fallback)**
```
Researcher visits /study/123 → getStudyById(123) fails (unpublished)
  → Fallback: getStudyByIdSupabase(123) in supabase.js
    → Supabase SDK .from('studies').select().eq('id', 123)
      → PostgreSQL SELECT
        → RLS policy allows: created_by = auth.uid() OR is_published = true
          → Returns draft study
  → Frontend displays with "DRAFT" badge
```

---

## Local Development Setup

### 1. Supabase (Required First)

```bash
# Start Supabase locally
supabase start

# Apply all migrations
supabase db reset

# Get connection info
supabase status
# Note: ANON_KEY, API_URL, DB_URL (pooler)
```

### 2. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure .env (copy from .env.example)
# Required:
#   DATABASE_URL=<from supabase status, pooler URL>?sslmode=require
#   ANTHROPIC_API_KEY=<your key>
#   FRONTEND_ORIGINS=http://localhost:5173,http://localhost:3000

uvicorn main:app --reload --port 8000
# Health check: http://localhost:8000/health
```

### 3. Frontend (Svelte)

```bash
cd frontend-sv
pnpm install

# Configure .env (copy from .env.example)
# Required:
#   VITE_SUPABASE_URL=<from supabase status>
#   VITE_SUPABASE_ANON_KEY=<from supabase status>
#   VITE_API_BASE=http://localhost:8000

pnpm dev
# Opens: http://localhost:5173
```

---

## Data Model Essentials

### Core Tables (Supabase)

#### `studies`
Clinical trial records (from CT.gov ingestion + researcher-created).

**Key Fields:**
- `id` (bigserial): Primary key
- `source` (text): 'ctgov' or 'researcher'
- `source_id` (text): NCT number or custom ID
- `title`, `description`, `eligibility_criteria` (text)
- `recruiting_status` (text): 'recruiting', 'not_yet_recruiting', 'completed', 'suspended'
- `conditions` (text[]): Searchable condition tags (lowercase)
- `locations` (jsonb): Study sites with lat/lon
- `contacts` (jsonb): Researcher contact info
- `media` (jsonb): `[{"path": "...", "caption": "..."}]` - supplemental files
- `tasks` (jsonb): `[{"id", "type", "title", "pages": [{"id", "title", "blocks": [...]}]}]` - survey tasks
- `created_by` (uuid): FK to auth.users (NULL for CT.gov studies)
- `is_published` (boolean): Draft vs public (default TRUE for CT.gov, FALSE for researcher)
- `ai_plain_title`, `ai_plain_summary`, `ai_eligibility_quiz` (text/jsonb): Cached AI outputs

**RLS:**
- Public can SELECT published studies (`is_published = TRUE`)
- Researchers can INSERT draft studies (`created_by = auth.uid()`, `is_published = FALSE`)
- Study owners can UPDATE/DELETE their own studies

#### `user_profiles`
Extended participant information (auto-created on signup).

**Key Fields:**
- `id` (uuid): PK, FK to auth.users
- `age`, `gender`, `race`, `ethnicity`
- `conditions` (text[]): Health conditions
- `medications`, `allergies`, `previous_trials`
- `zip_code`, `travel_radius`
- `weekday_availability`, `weekend_availability`, `preferred_time_of_day`
- `in_person_willing`, `remote_willing`
- `compensation_importance` (int 1-5)

**RLS:**
- Users can SELECT/UPDATE own profile

#### `participation_requests`
Participant interest in studies.

**Key Fields:**
- `id` (bigserial): PK
- `user_id` (uuid): FK to auth.users
- `study_id` (bigint): FK to studies
- `status` (text): 'pending', 'contacted', 'approved', 'rejected', 'withdrawn'
- `notes` (text): Participant message
- `contact_preference` (text): 'email', 'phone', 'portal'
- `consent_acknowledged_at` (timestamptz): When participant acknowledged consent (NULL = not yet)
- `UNIQUE(user_id, study_id)`: One request per user per study

**RLS:**
- Users can SELECT/INSERT/UPDATE own requests
- Study owners can SELECT/UPDATE requests for their studies (approve/reject, reset consent)

#### `researcher_allowlist_emails`
Manual researcher access (supplements .edu auto-detection).

**Key Fields:**
- `email` (text): PK

**Usage:**
- `is_researcher()` function checks `.edu` domain OR allowlist membership

#### `task_submissions`
Participant survey responses for study tasks.

**Key Fields:**
- `id` (bigserial): PK
- `study_id` (bigint): FK to studies
- `task_id` (text): Matches task.id in studies.tasks JSONB
- `user_id` (uuid): FK to auth.users
- `responses` (jsonb): Survey responses keyed by block ID
- `submitted_at` (timestamptz): When submitted
- `UNIQUE(study_id, task_id, user_id)`: Single submission per user per task

**RLS:**
- Users can SELECT/INSERT own submissions
- Study owners can SELECT all submissions for their studies

### Storage Buckets

#### `study-media`
Researcher-uploaded recruitment materials.

**Configuration:**
- Public: `true` (public read)
- Size limit: 5MB per file
- Formats: JPEG, PNG, WebP, GIF, SVG, PDF
- Path: `{study_id}/{timestamp}_{filename}`
- Max: 10 files per study

**RLS:**
- Public can SELECT (download)
- Researchers can INSERT (upload)
- Study owners can DELETE (from their study folders)

#### `study-recordings` (Planned)
Participant voice recording submissions.

**Configuration:**
- Public: `false` (RLS-controlled)
- Size limit: 50MB per file
- Formats: audio/webm, audio/mp4, audio/mpeg, audio/wav, audio/ogg
- Path: `{study_id}/{user_id}/{submission_id}.webm`

**RLS (Planned):**
- Study owners can SELECT all recordings for their studies
- Participants can SELECT/INSERT/DELETE own recordings

---

## Backend Architecture (FastAPI)

### Module Structure

Monolithic modules with inline dependencies (no scattered helpers).

**`backend/main.py`** - Entrypoint (28 lines)
- Wires together platform, search, and AI modules
- Mounts routes at root (no `/api` prefix)

**`backend/platform_module.py`** - Infrastructure
- Database connection (`get_db()` context manager)
- CORS middleware
- Health check endpoint (`/health`)
- Startup event (test DB connection)

**`backend/search_module.py`** - Study operations
- Study CRUD (GET /studies/:id)
- Search endpoint (POST /search) with custom scoring
- CT.gov ingestion helpers (inline)
- Embeddings generation (inline, uses OpenAI)

**`backend/ai_module.py`** - AI features
- Plain title generation (`POST /ai/plain-title`)
- Plain summary generation (`POST /ai/study-summary`)
- Eligibility quiz generation (`POST /ai/eligibility-quiz`)
- Anthropic client wrapper
- Rate limiting (100 req/min, in-memory)
- PostgreSQL caching

**`scripts/`** - Runnable workflows
- `scripts/ingest_ctgov.py` - Import studies from CT.gov API
- `scripts/backfill_embeddings.py` - Generate embeddings for existing studies

### Database Connection

FastAPI uses **direct PostgreSQL connection** (not Supabase client).

**Connection String Format:**
```
postgresql://postgres.[ref]:[password]@aws-0-us-west-2.pooler.supabase.com:6543/postgres?sslmode=require
```

**Must use:**
- Pooler host (not direct `db.[ref].supabase.co`)
- `?sslmode=require` (avoids IPv6 issues on Render)
- Transaction pooler mode

**Context Manager Pattern:**
```python
with get_db() as conn:
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM studies WHERE id = %s", (study_id,))
    row = cursor.fetchone()
```

---

## Frontend Architecture (Svelte)

### Monolithic Page Philosophy

Keep UI logic, data loading, and event handlers in **one file per route**. Avoid splitting features across many components.

**Benefits:**
- Feature logic in one place (no file jumping)
- Clear traceability (search for a feature = one file)
- Accept duplication over premature abstraction

**When to extract components:**
- Only when page becomes unwieldy (>1000 lines)
- Only when explicitly directed
- Use shared UI primitives only (`frontend-sv/src/lib/components/ui/`)

### Route Pages

**`frontend-sv/src/routes/`** - Each route is a monolithic `.svelte` file:

- **`home/+page.svelte`** - Landing page with search and condition suggestions
- **`browse/+page.svelte`** - Study cards with filters (conditions, location, recruiting status)
- **`study/[id]/+page.svelte`** - Full study details, participation request form, media display
- **`profile/+page.svelte`** - User profile editor, participation request list, **researcher study management**
- **`signup/+page.svelte`** - Account creation with redirect handling
- **`login/+page.svelte`** - Login form
- **`bio/+page.svelte`** - 10-section demographic profile form

### Frontend Helper Libraries

#### Supabase Client (`frontend-sv/src/lib/supabase.js`)

All operations using `@supabase/supabase-js` SDK - direct database access with RLS.

**Auth:**
- `getCurrentUser()` - Get current session user
- `signUp(email, password)` - Create account
- `signIn(email, password)` - Login
- `signOut()` - Logout
- `getSession()` - Get current session
- `onAuthStateChange(callback)` - Listen to auth events

**User Profiles (direct table access):**
- `getUserProfile(userId)` - SELECT from `user_profiles`
- `updateUserProfile(userId, updates)` - UPDATE `user_profiles`

**Participation Requests (direct table access):**
- `createParticipationRequest(studyId, notes, contactPreference)` - INSERT into `participation_requests`
- `getUserParticipationRequests()` - SELECT with joined `studies` data
- `withdrawParticipationRequest(requestId)` - UPDATE status to 'withdrawn'

**Researcher Operations (direct table access):**
- `isResearcher()` - RPC call to `is_researcher()` function
- `getUserStudies()` - SELECT from `studies` WHERE `created_by = auth.uid()`
- `createDraftStudy(studyData)` - INSERT into `studies` with `is_published = false`
- `updateStudy(studyId, updates)` - UPDATE `studies`
- `deleteStudy(studyId)` - DELETE from `studies`
- `getStudyByIdSupabase(studyId)` - SELECT single study (used as fallback for drafts)

**Storage Operations:**
- `uploadStudyMedia(studyId, file)` - Upload to `study-media` bucket
- `deleteStudyMedia(path)` - Remove from `study-media` bucket
- `getPublicMediaUrl(path)` - Get public URL for file

#### FastAPI Client (`frontend-sv/src/lib/api.js`)

All operations calling FastAPI endpoints - search and AI features (read-only for frontend).

**Search:**
- `searchStudies(query, page, limit, zip)` - POST to `/search`
- Returns: `{ items: [...], total: number }`

**Study Retrieval:**
- `getStudyById(studyId)` - GET from `/studies/:id`
- Returns full study object (published studies only)

**AI Features (all cached in database):**
- `generatePlainTitle(study)` - POST to `/ai/plain-title`
  - Cached in `studies.ai_plain_title`
- `generateStudySummary(study)` - POST to `/ai/study-summary`
  - Cached in `studies.ai_plain_summary`
- `generateEligibilityQuiz(studyId, eligibilityCriteria)` - POST to `/ai/eligibility-quiz`
  - Cached in `studies.ai_eligibility_quiz`

**Example usage:**
```javascript
import { searchStudies, getStudyById, generatePlainTitle } from '$lib/api.js';

// Search (calls FastAPI)
const { items, total } = await searchStudies('diabetes', 1, 10, '02139');

// Get study (calls FastAPI for published studies)
const study = await getStudyById(studyId);

// Generate AI content if not cached (calls FastAPI → Anthropic)
const { plain_title } = await generatePlainTitle(study);
```

---

## Participation Flow (End-to-End)

### 1. Browse/Search
**Data flow:** Frontend → FastAPI `/search` → PostgreSQL → Frontend

User enters query → `searchStudies()` in `api.js` → FastAPI search endpoint → returns study list.

### 2. View Study Details
**Data flow:** Frontend → FastAPI `/studies/:id` (or Supabase for drafts) → Frontend

- **Published studies**: `getStudyById()` calls FastAPI → returns cached study data
- **Draft studies** (authenticated users): Falls back to `getStudyByIdSupabase()` → direct Supabase query with RLS

### 3. Request Participation
**Data flow:** Frontend → Supabase Auth check → UI decision

- Click "Participate" → checks `$user` store (Supabase session)
- If logged out → redirect to `/signup?redirect=/study/:id`
- If logged in → show confirmation modal

### 4. Signup (if needed)
**Data flow:** Frontend → Supabase Auth → PostgreSQL trigger → Frontend

- `signUp(email, password)` → Supabase creates `auth.users` row
- Database trigger auto-creates `user_profiles` row
- Redirect back to study page with `fromSignup=true`

### 5. Confirm Participation Request
**Data flow:** Frontend → Supabase → PostgreSQL (with RLS) → Frontend

- Modal with optional notes field
- `createParticipationRequest(studyId, notes, 'email')` → Supabase SDK
- INSERT into `participation_requests` table with `status = 'pending'`
- RLS policy validates: user is authenticated, UNIQUE constraint enforced
- Redirect to `/profile` (shows request list)

### 6. Researcher Approval (Manual)
**Data flow:** Supabase Dashboard → PostgreSQL → (future: Frontend notification)

- Via Supabase Dashboard: UPDATE `participation_requests` SET `status = 'approved'`
- Future: UI in Profile page for researchers to approve/reject

### 7. Task Completion (Planned)
**Data flow:** Frontend → Supabase (consent + submissions) → Storage

- Participant sees approved status → consent flow → task list → voice recording submission
- All operations via Supabase SDK with RLS enforcement

---

## Researcher Workflow

### 1. Researcher Detection
**Data flow:** Frontend → Supabase RPC → PostgreSQL function → Frontend

Function `is_researcher()` checks email domain or allowlist:
```sql
CREATE OR REPLACE FUNCTION public.is_researcher() RETURNS BOOLEAN AS $$
DECLARE user_email TEXT;
BEGIN
  SELECT email INTO user_email FROM auth.users WHERE id = auth.uid();

  -- Check .edu email
  IF lower(user_email) LIKE '%.edu' THEN RETURN TRUE; END IF;

  -- Check allowlist
  IF EXISTS (SELECT 1 FROM public.researcher_allowlist_emails
             WHERE lower(email) = lower(user_email)) THEN RETURN TRUE; END IF;

  RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

Frontend calls: `isResearcher()` → Supabase RPC → returns boolean.

### 2. Study Creation
**Data flow:** Frontend → Supabase → PostgreSQL (with RLS) → Frontend

Profile page (`/profile`) → "My Studies" tab:
- Form fields: title, source, description, eligibility, conditions, site_zips
- Click "Create Draft" → `createDraftStudy(studyData)`
- Supabase SDK: INSERT into `studies` with `created_by = auth.uid()`, `is_published = false`
- RLS policy validates: `is_researcher() = true`, `created_by = auth.uid()`
- Study only visible to creator (RLS: `created_by = auth.uid()` OR `is_published = true`)

### 3. Media Upload
**Data flow:** Frontend → Supabase Storage → PostgreSQL → Frontend

Edit study → "Media (Supplemental Materials)" section:
- Click "Upload File" → select image/PDF (max 5MB)
- `uploadStudyMedia(studyId, file)` → Supabase Storage SDK
- Upload to `study-media/{study_id}/{timestamp}_{filename}`
- RLS policy validates: researcher can upload, study owner can delete
- Add caption → `updateStudy(studyId, { media: [..., {path, caption}] })`
- Updates `studies.media` JSONB array

### 4. Publishing
**Data flow:** Frontend → Supabase → PostgreSQL (RLS) → Frontend

- Click "Publish" → `updateStudy(studyId, { is_published: true })`
- Supabase SDK: UPDATE `studies` SET `is_published = true`
- RLS policy validates: `created_by = auth.uid()`, `source != 'ctgov'`
- Study becomes visible in public search (FastAPI reads published studies)

### 5. Managing Requests (Current State)
**Data flow:** Frontend → Supabase → PostgreSQL (RLS) → Frontend

- `getUserParticipationRequests()` → Supabase SDK
- SELECT from `participation_requests` with joined `studies` data
- RLS policy currently allows users to see their own requests only; researcher visibility is WIP
- Display in Profile page with status (pending/approved/rejected/withdrawn)
- Approval currently manual via Supabase Dashboard (no UI yet)

---

## Researcher Operations Guide (Consolidated)

### Eligibility
- Automatic: `.edu` email domains qualify.
- Manual allowlist: add emails to `researcher_allowlist_emails`.

### Creating Studies
- Profile page → "My Studies" → "+ Create New Study".
- Required fields: **Title**, **Source** (cannot be `ctgov`).
- New studies are drafts (`is_published = false`) until published.

### Media Upload (Recruitment Materials)
- Formats: JPEG, PNG, WebP, GIF, SVG, PDF
- Size limit: 5MB per file
- Max 10 files per study
- Storage path: `study-media/{study_id}/{timestamp}_{filename}`
- Optional captions stored in `studies.media`

### Publishing
- Publish/Unpublish toggles `is_published`.
- Published studies appear in public search and detail pages.

### Admin / SQL Operations (when needed)
- Add allowlist email:
  - `INSERT INTO public.researcher_allowlist_emails (email) VALUES ('researcher@institution.org');`
- Assign ownership:
  - `UPDATE public.studies SET created_by = <user_id> WHERE id = <study_id>;`
- Add media item:
  - `UPDATE studies SET media = COALESCE(media, '[]'::jsonb) || '[{\"path\":\"123/file.pdf\",\"caption\":\"Recruitment\"}]'::jsonb WHERE id = 123;`

### Troubleshooting
- Upload fails with “Must save study first”: create the study to get an ID before uploading.
- Media not visible: check `studies.media`, storage bucket, and publish status.
- Permission errors: verify `.edu` or allowlist access.

## Key Conventions

### Code Style

**Backend (Python):**
- Module structure: CONFIG → TYPES → DEPENDENCIES → REPO → SERVICE → ROUTES
- Inline dependencies (no scattered helper files)
- Use `psycopg[binary]>=3.2` (not psycopg2)
- Context managers for DB connections

**Frontend (Svelte):**
- Monolithic pages (state + handlers + UI in one file)
- Use existing primitives: `frontend-sv/src/lib/components/ui/`
- Package manager: **pnpm** (never npm/yarn)
- Avoid extracting components unless necessary

### Database

**Migrations:**
- Location: `supabase/migrations/`
- Naming: `YYYYMMDDhhmmss_description.sql`
- Apply locally: `supabase db reset`

**RLS Policies:**
- Enable on all user-facing tables
- Use `auth.uid()` for user identity
- Use `EXISTS` subqueries for ownership checks

**Triggers:**
- `handle_updated_at()` - Auto-update `updated_at` column
- User profile creation - Auto-create on auth.users insert

### Deployment

**Backend (Render):**
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Environment variables: `DATABASE_URL` (pooler with SSL), `ANTHROPIC_API_KEY`, `FRONTEND_ORIGINS`

**Frontend (Vercel):**
- Framework preset: Vite
- Build command: `pnpm build`
- Output directory: `dist`
- Environment variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE`

**Database (Supabase):**
- Connection pooler mode: Transaction
- SSL mode: Required (`?sslmode=require`)

---

## Common Errors & Solutions

### CORS 503/Blocked
**Symptom:** API requests fail with CORS error or 503.
**Cause:** `FRONTEND_ORIGINS` typo (e.g., double `https://`).
**Fix:** Check `backend/.env` and redeploy.

### Database Connection Unreachable
**Symptom:** Backend can't connect to database.
**Cause:** Using direct host (`db.[ref].supabase.co`) without SSL.
**Fix:** Use pooler host with `?sslmode=require`.

### Health Checks Failing (Render)
**Symptom:** Render shows unhealthy service.
**Cause:** Health check probing `/` returns 404.
**Fix:** Set health check path to `/health`.

### Media Not Appearing
**Symptom:** Uploaded files don't show on study page.
**Cause:** Backend `Study` model missing `media` field.
**Fix:** Ensure `_row_to_study()` includes `media` in mapping.

### RLS Policy Blocks Insert
**Symptom:** "new row violates row-level security policy".
**Cause:** Missing permission check in RLS `WITH CHECK` clause.
**Fix:** Verify policy conditions match insert data (e.g., `created_by = auth.uid()`).

### a common pitfall is forgetting to update the fastapi after making database / ui schema changes

---

## Next Implementation: Voice Recording Framework

Implementation spec: `STUDY_TASK_FRAMEWORK.md` (preferred)
Plan file (internal): `/Users/nathanle/.claude/plans/parsed-booping-galaxy.md`

**Summary:**
- New tables: `study_tasks`, `consent_documents`, `consent_acknowledgments`, `task_submissions`
- New storage bucket: `study-recordings` (private, 50MB limit)
- New backend module: `backend/tasks_module.py`
- New frontend pages: consent flow, task list, voice recording UI
- RLS enforcement: Consent required before task submission

**Key architectural alignment:**
- Tasks stored in Supabase (user data)
- Voice recordings in Supabase Storage (with RLS)
- Backend module for task/consent API (follows monolithic pattern)
- Frontend pages follow monolithic philosophy (state + handlers + UI in one file)
