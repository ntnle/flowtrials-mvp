# Flow Trials - Handoff Document

## Current Status

**Phase 1: Participation Management** - COMPLETED
**Phase 2: Task Framework (Surveys)** - COMPLETED

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
   - Add/remove question blocks (text, short_text, long_text, multiple_choice, checkbox, number)
   - Edit block labels, required flag, and options

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
