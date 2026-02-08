# Flow Trials — Product

## At A Glance
Flow Trials is a clinical trial discovery and participation platform.

Primary user roles:
- **Participants**: search studies, request participation, complete approved/consented tasks.
- **Researchers**: create/publish studies, manage participation requests, author tasks, review submissions.

Key product invariants (agents should preserve):
- Task access is gated by participation status: must be **approved** and have **consent acknowledged** (`consent_acknowledged_at`).
- Participation requests are per-user/per-study (enforced by a uniqueness constraint).
- Tasks live on the study as JSON (`studies.tasks`); submissions live in `task_submissions` (RLS-controlled).
- AI outputs are **cache-backed** and should be treated as idempotent.

Canonical architecture context: [ARCHITECTURE.md](ARCHITECTURE.md).

## Main User Flows

### Participant
1) Discover studies: browse/search and open study detail.
2) Auth + profile: Supabase Auth; profile stored in `user_profiles`.
3) Request participation: create a `participation_requests` row.
4) Consent gating: on approval, participant acknowledges consent (`consent_acknowledged_at`).
5) Complete tasks:
   - Survey tasks
   - Audio recording blocks (audio stored privately; metadata stored in submissions)
   - Media blocks (images/PDFs embedded via private storage)

Primary routes:
- `/browse`, `/study/:id`
- `/signup`, `/login`, `/profile`
- `/study/:id/tasks`, `/study/:id/tasks/:taskId`

### Researcher
1) Researcher access: `.edu` email and/or allowlist.
2) Create draft studies; edit; publish/unpublish.
3) Manage participation requests: approve/reject; reset consent when docs change.
4) Author tasks in the study editor (writes go through Supabase; RLS enforces permissions).

## AI Functionality
FastAPI provides search + AI endpoints (read-only for frontend writes). AI features:
- Plain-language title
- Plain-language summary
- Eligibility quiz

## Explicit Non-Goals
- Backend-driven write APIs for core mutations (Supabase-first).
- Complex survey branching/randomization.
- Heavy back-office dashboard beyond basic study + task management.
