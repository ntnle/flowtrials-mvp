# Flow Trials - Handoff Document

## Current Status

**Phase 1: Participation Management** - COMPLETED
**Phase 2: Task Framework (Surveys)** - COMPLETED
**Phase 3: Audio Recording Blocks** - COMPLETED
**Phase 4: Task Media Blocks** - COMPLETED

---

## Phase 4: Task Media Blocks

### What's New

1. **Storage Migration** (`supabase/migrations/20260201000003_add_task_media_storage.sql`)
   - Created `task-media` private bucket (10MB limit, images + PDFs)
   - RLS policies for study owners to upload/view/update/delete task media
   - RLS policies for approved participants with consent to view task media
   - Path format: `{study_id}/{task_id}/{timestamp}_{filename}`

2. **Supabase Client Helpers** (`frontend-sv/src/lib/supabase.js`)
   - `uploadTaskMedia(studyId, taskId, file)` - Upload image/PDF with metadata
   - `getTaskMediaUrl(path)` - Get signed URL (1 hour expiry)
   - `deleteTaskMedia(path)` - Delete media file

3. **Task Editor** (`frontend-sv/src/routes/profile/+page.svelte`)
   - Added "Media" block type to task editor
   - Upload interface for images (JPEG, PNG, WebP, GIF, SVG) and PDFs
   - Media items list with delete functionality
   - Optional captions for each media item

4. **Survey Renderer** (`frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte`)
   - Media block display with image preview
   - PDF items shown with download link
   - Captions displayed when provided
   - Gated by approval + consent (RLS enforced)

### Media Block Structure

Media blocks store items (not responses):
```json
{
  "type": "media",
  "items": [
    {
      "path": "123/task-456/1738425600000_image.jpg",
      "kind": "image",
      "mimeType": "image/jpeg",
      "size": 234567,
      "caption": "Optional caption"
    }
  ]
}
```

---

## Phase 3: Audio Recording Blocks

### What's New

1. **Storage Migration** (`supabase/migrations/20260201000002_add_audio_storage.sql`)
   - Created `study-recordings` private bucket (50MB limit, audio MIME types)
   - RLS policies for participants to upload/view/delete their own recordings
   - RLS policies for study owners to view/delete all recordings for their studies
   - Path format: `{study_id}/{participation_request_id}/{timestamp}.webm`

2. **Supabase Client Helpers** (`frontend-sv/src/lib/supabase.js`)
   - `uploadAudioRecording(studyId, participationRequestId, audioBlob)` - Upload audio with metadata
   - `getAudioRecordingUrl(path)` - Get signed URL (1 hour expiry)
   - `deleteAudioRecording(path)` - Delete audio file

3. **Survey Renderer** (`frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte`)
   - Audio recording UI with microphone access
   - Start/Stop recording with timer display
   - Automatic upload on stop
   - Re-record functionality
   - Required field validation for audio blocks

4. **Task Editor** (`frontend-sv/src/routes/profile/+page.svelte`)
   - Added "Audio Recording" block type to task editor
   - Audio blocks have `label` and `required` fields

### Audio Response Storage

Audio recordings are stored in two places:
1. **File storage**: `study-recordings` bucket (actual audio file)
2. **Response metadata**: Stored in `task_submissions.responses` JSONB

Example response object:
```json
{
  "block-id-123": {
    "path": "456/789/1738425600000.webm",
    "size": 45678,
    "mimeType": "audio/webm",
    "uploadedAt": "2026-02-01T12:00:00.000Z"
  }
}
```

---

## Phase 2: Task Framework (Surveys)

### What's New

1. **Database Migration** (`supabase/migrations/20260201000001_add_task_framework.sql`)
   - Added `tasks` JSONB column to `studies` table
   - Created `task_submissions` table for storing survey responses
   - RLS policies for participants to submit and view own submissions
   - RLS policies for study owners to view all submissions

2. **Supabase Client Helpers** (`frontend-sv/src/lib/supabase.js`)
   - `submitTaskResponse(studyId, taskId, responses)` - Submit survey responses
   - `getMyTaskSubmissions(studyId)` - Get user's submissions for a study
   - `getTaskSubmissionsForStudy(studyId)` - Researcher gets all submissions

3. **Researcher Task Editor** (`frontend-sv/src/routes/profile/+page.svelte`)
   - Task management section in study editor (Edit → Tasks)
   - Add/remove survey tasks
   - Add/remove pages within tasks
   - Add/remove question blocks (text, short_text, long_text, multiple_choice, checkbox, number, audio_recording, media)
   - Edit block labels, required flag, and options
   - Upload media items (images/PDFs) for media blocks

4. **Participant Task Flow**
   - Task list page (`/study/:id/tasks`) - Shows all tasks with completion status
   - Survey runner (`/study/:id/tasks/:taskId`) - Multi-page survey with validation
   - Final submit confirmation modal
   - Single submission per task (no re-submission)

### Task Data Structure

```json
{
  "id": "uuid",
  "type": "survey",
  "title": "Pre-Study Questionnaire",
  "pages": [
    {
      "id": "uuid",
      "title": "Page 1",
      "blocks": [
        { "id": "uuid", "type": "text", "content": "Instructions..." },
        { "id": "uuid", "type": "short_text", "label": "Name?", "required": true },
        { "id": "uuid", "type": "multiple_choice", "label": "Frequency?", "options": ["Daily", "Weekly"], "required": true }
      ]
    }
  ]
}
```

### Block Types

| Type | Description | Fields |
|------|-------------|--------|
| `text` | Static text/instructions | `content` |
| `short_text` | Single-line input | `label`, `required` |
| `long_text` | Multi-line textarea | `label`, `required` |
| `number` | Numeric input | `label`, `required` |
| `multiple_choice` | Radio buttons (single select) | `label`, `required`, `options[]` |
| `checkbox` | Checkboxes (multi-select) | `label`, `required`, `options[]` |
| `audio_recording` | Audio recording capture | `label`, `required` |
| `media` | Images and PDFs display | `items[]` (path, kind, caption) |

**Audio Recording Block Response Format:**
```json
{
  "path": "123/456/1738425600000.webm",
  "size": 45678,
  "mimeType": "audio/webm",
  "uploadedAt": "2026-02-01T12:00:00.000Z"
}
```

**Media Block Structure (not a response):**
```json
{
  "items": [
    {
      "path": "123/task-456/1738425600000_image.jpg",
      "kind": "image",
      "mimeType": "image/jpeg",
      "size": 234567,
      "caption": "Optional caption"
    }
  ]
}
```

---

## Phase 1: Participation Management (Previous)

1. **Database Migration** (`supabase/migrations/20260201000000_add_participation_consent.sql`)
   - Added `consent_acknowledged_at` column to `participation_requests`
   - RLS policies for study owners to SELECT/UPDATE participation requests

2. **Researcher UI** - Approve/reject requests, reset consent

3. **Participant Consent Flow** - Status banner, consent modal, task access gating

---

## To Apply Migrations

```bash
cd /Users/nathanle/Desktop/flowtrials
supabase db reset  # Resets and applies all migrations
```

## Next Steps (Phase 3)

Phase 3: Audio Tasks
- Audio recording task type
- Private `study-recordings` storage bucket
- Recording attempts and review status

## Files Changed (Phase 2)

| File | Change |
|------|--------|
| `supabase/migrations/20260201000001_add_task_framework.sql` | New migration |
| `frontend-sv/src/lib/supabase.js` | Added task submission helpers |
| `frontend-sv/src/routes/profile/+page.svelte` | Task editor UI |
| `frontend-sv/src/routes/study/[id]/+page.svelte` | View Tasks button |
| `frontend-sv/src/routes/study/[id]/tasks/+page.svelte` | New: Task list page |
| `frontend-sv/src/routes/study/[id]/tasks/[taskId]/+page.svelte` | New: Survey runner |
| `DOC.md` | Updated Phase 2 status, data model |
