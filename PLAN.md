Goal
- Add a first-pass audio recording block type to the survey/task framework, with storage, RLS, and UI to record + submit audio.

Non-Goals
- Transcription, waveform rendering, or analytics.
- Advanced retry workflows or branching logic.
- FastAPI endpoints for audio.

Acceptance Criteria
- Task schema supports `type: "audio_recording"` blocks.
- Participants can record and upload audio for those blocks in the survey UI.
- Audio files are stored in a private `study-recordings` bucket with RLS.
- Audio responses are stored in `study_task_responses.response_json`.

Atomic TODOs (Doer Checklist)
1) Add a storage migration to create `study-recordings` bucket (private, 50MB, audio MIME types).
2) Add storage RLS policies for upload/select/delete based on study ownership and participation approval.
3) Update task schema docs in `STUDY_TASK_FRAMEWORK.md` to include `audio_recording` block shape and response shape.
4) Extend the survey renderer in `frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte` to support `audio_recording` blocks.
5) Add recording/upload helpers in `frontend-sv/src/lib/supabase.js` (upload audio and return path + metadata).
6) Update response saving to store audio response object inside `response_json` for that block.
7) Update `DOC.md` and `HANDOFF.md` to mention audio block support (MVP).

Open Questions / Blockers
- Confirm storage path format for recordings (recommended: `{study_id}/{participation_request_id}/{response_id}.webm`).
