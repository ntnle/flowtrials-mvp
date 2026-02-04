Goal
- Add a minimal “task media” block type for surveys that supports images and PDFs, with private storage and participant‑gated access.

Non-Goals
- Audio/video playback or recording.
- Task branching, randomization, or advanced validation.
- FastAPI endpoints.

Acceptance Criteria
- Task schema supports `type: "media"` blocks with `items[]` (path, kind, caption).
- Researchers can upload task media from the task editor UI.
- Participants can view task media only after approval + consent.
- Media is stored in a private `task-media` bucket with RLS.

Atomic TODOs (Doer Checklist)
1) Create a new migration in `supabase/migrations/` to add a private `task-media` bucket (images + PDFs only).
2) Add RLS policies for `task-media` so study owners can upload/manage, and participants can read only when approved + consent acknowledged.
3) Update `STUDY_TASK_FRAMEWORK.md` to define the `media` block schema and allowed MIME types.
4) Extend task editor UI in `frontend-sv/src/routes/profile/+page.svelte` to add a `media` block and upload files into it.
5) Extend task renderer in `frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte` to display media blocks (image preview + PDF link).
6) Add Supabase helpers in `frontend-sv/src/lib/supabase.js` for uploading/reading `task-media`.
7) Update `DOC.md` / `HANDOFF.md` to mention task media blocks (MVP).

Open Questions / Blockers
- Confirm storage path format for task media (recommended: `{study_id}/{task_id}/{filename}`).
