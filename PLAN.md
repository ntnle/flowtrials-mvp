Goal
- Define and implement the MVP task framework for studies (surveys only), stored on the study object, with participant task flow and final submit confirmation.

Non-Goals
- Implement audio recording tasks or storage.
- Add branching/skip logic, randomization, or advanced survey features.
- Add new FastAPI endpoints or backend modules.

Acceptance Criteria
- `studies` has a `tasks` JSONB field used as the source of truth for survey tasks.
- Researchers can create/edit/reorder survey tasks (pages + blocks) in the study editor UI.
- Participants can view a task list and complete a survey task with a final submit confirmation.
- Survey responses are stored per task submission (single JSON blob keyed by block IDs).
- Docs reflect the task framework and MVP scope.

Atomic TODOs (Doer Checklist)
1) Add a new migration in `supabase/migrations/` to add `tasks` JSONB to `studies` (default empty array).
2) Update `frontend-sv/src/lib/supabase.js` study helpers to read/write the `tasks` field.
3) Extend the researcher study editor in `frontend-sv/src/routes/profile/+page.svelte` to add/edit/reorder tasks, pages, and blocks for `type: "survey"`.
4) Add participant task list view in `frontend-sv/src/routes/study/[id]/tasks/+page.svelte` (only show when approved + consent acknowledged).
5) Add survey task runner in `frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte` with page navigation, required validation, and final submit confirmation.
6) Store survey responses in the task responses table as JSON keyed by block IDs (no analytics or derived fields).
7) Update `DOC.md`, `HANDOFF.md`, and `STUDY_TASK_FRAMEWORK.md` to reflect the survey task framework and MVP limits.

Open Questions / Blockers
- Confirm whether survey responses should allow multiple attempts immediately or be single-submit for MVP.
