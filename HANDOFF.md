# Handoff Notes

This file captures near-term implementation notes that are too tactical for PRODUCT/ARCHITECTURE.

## Profile UX (requested changes)

### Goal

Make it obvious in the profile which studies a participant is actively in, and give researchers fast access to study management, without mixing the two experiences in a confusing way.

### Current state (today)

- The profile page is a single mixed UI at [frontend-sv/src/routes/(app)/profile/+page.svelte](frontend-sv/src/routes/(app)/profile/+page.svelte) that includes:
  - Participant participation request list and profile fields
  - Researcher study management (draft/publish, task authoring)
  - Researcher participation request management
  - Researcher task submission review (including signed audio URLs)
- Focused join flows exist under `(focus)` routes (navbar-free) as documented in [ARCHITECTURE.md](ARCHITECTURE.md).

### Desired UX behavior

1) Focused-study presence in profile

- For studies that are configured for a focused join funnel (i.e. `studies.join_flow_key` is set for a published study):
  - Show a clear “Focused study session” section for each active participation (or approved+consented participation).
  - Include a shareable entry link to the focused join route: `/join/:studyId`.
  - If a study has an additional focused flow entry (e.g. a study-specific start step), include the direct link as well.

2) Share links

- Links should be copyable and unambiguous.
- Treat them as pointers into existing focused routes; do not invent new endpoints.

3) Menu / information architecture cleanup

- Participant view should prioritize:
  - “My studies” (status + next action)
  - “My profile” (demographics/health data)
- Researcher view should prioritize:
  - “My studies” (create/edit/publish)
  - “Participation requests” (per-study)
  - “Submissions” (per-study)
- Avoid putting researcher tools behind participant-centric navigation labels (and vice versa).

4) Partition participant vs researcher UIs

- Preferred: separate routes or explicit view segmentation rather than a single mixed page.
- Keep the existing capability checks (`isResearcher()`) and Supabase-first mutation model.

### Implementation notes / file pointers

- Participant profile + participation UI currently lives in:
  - [frontend-sv/src/routes/(app)/profile/+page.svelte](frontend-sv/src/routes/(app)/profile/+page.svelte)
- Focused join route (navbar-free):
  - [frontend-sv/src/routes/(focus)/join/[studyId]/+page.svelte](frontend-sv/src/routes/(focus)/join/[studyId]/+page.svelte)
- If creating study-specific focused “session start” entrypoints, keep them under `(focus)` and link from profile.

### Acceptance criteria

- A participant with active participations can find and copy the focused join link(s) from profile in under 10 seconds.
- A researcher can reach “My studies” management without seeing participant-only prompts.
- No writes are moved to FastAPI; all mutations remain Supabase-first.

## Notes on repo docs

- Root [README.md](README.md) currently references DOC.md and STUDY_TASK_FRAMEWORK.md, but these files are not present in the repository.
- If those docs are still desired, either add them or update README to avoid dead links.
