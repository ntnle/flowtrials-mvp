Goal
- Provide a minimal, actionable plan to implement Phase 1 participation management (researcher-facing approvals + consent acknowledgment gating) so the participation flow is complete for MVP.

Non-Goals
- Implement survey/task framework or audio recording.
- Add new FastAPI endpoints or backend modules.
- Refactor existing UI or data models beyond what Phase 1 requires.

Acceptance Criteria
- Participation requests support consent acknowledgment tracking.
- Researchers can view and approve/reject requests for their studies in the UI.
- RLS allows study owners to SELECT participation requests for their studies.
- Participant access to tasks is gated by approved + consent acknowledged.
- Researchers can reset consent acknowledgment if consent changes.

Atomic TODOs (Doer Checklist)
1) Create a new migration in `supabase/migrations/` to add consent acknowledgment fields to `participation_requests`.
2) In the same migration, add an RLS policy allowing study owners to SELECT participation requests for their studies.
3) Update Supabase client helpers in `frontend-sv/src/lib/supabase.js` to fetch researcher-owned participation requests and to update consent acknowledgment.
4) Extend researcher UI in `frontend-sv/src/routes/profile/+page.svelte` to list participation requests for owned studies and allow approve/reject.
5) Add participant consent acknowledgment flow (load consent media tagged `kind: "consent"` and set `consent_acknowledged_at`) in `frontend-sv/src/routes/study/[id]/` flow.
6) Add researcher action to reset `consent_acknowledged_at` when consent changes in `frontend-sv/src/routes/profile/+page.svelte`.
7) Enforce gating for task access (approved + consent acknowledged) in the same study flow UI.
8) Update `DOC.md` and `HANDOFF.md` to reflect Phase 1 completion and new consent/participation behavior.

Open Questions / Blockers
- None.
