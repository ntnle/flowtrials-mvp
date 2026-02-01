# Flow Trials - Handoff Document

## Current Status

**Phase 1: Participation Management** - COMPLETED

All Phase 1 features have been implemented:

### What's New

1. **Database Migration** (`supabase/migrations/20260201000000_add_participation_consent.sql`)
   - Added `consent_acknowledged_at` column to `participation_requests`
   - Added RLS policy for study owners to SELECT participation requests
   - Added RLS policy for study owners to UPDATE participation requests (approve/reject)

2. **Supabase Client Helpers** (`frontend-sv/src/lib/supabase.js`)
   - `getStudyParticipationRequests(studyId)` - Researcher fetches requests for their study
   - `updateParticipationRequestStatus(requestId, status)` - Approve/reject requests
   - `resetParticipationConsent(requestId)` - Reset consent when documents change
   - `acknowledgeConsent(requestId)` - Participant acknowledges consent
   - `getMyParticipationForStudy(studyId)` - Check participant's status for a study

3. **Researcher UI** (`frontend-sv/src/routes/profile/+page.svelte`)
   - "Requests" button on each study card in My Studies tab
   - View all participation requests with participant info
   - Approve/Reject buttons for pending requests
   - Reset Consent button for approved participants
   - Consent status indicator

4. **Participant Consent Flow** (`frontend-sv/src/routes/study/[id]/+page.svelte`)
   - Shows participation status banner (pending/approved/rejected/withdrawn)
   - Consent acknowledgment modal for approved participants
   - Task access gating (requires approved + consent_acknowledged)
   - Placeholder for future task UI

## To Apply Migration

```bash
cd /Users/nathanle/Desktop/flowtrials
supabase db reset  # Resets and applies all migrations
# OR for production:
# supabase db push
```

## Next Steps (Phase 2)

Phase 2: Task Framework (Surveys)
- Store tasks on `studies.tasks` as JSON
- Survey task UI with pages and question blocks
- Task submission tracking

## Files Changed

| File | Change |
|------|--------|
| `supabase/migrations/20260201000000_add_participation_consent.sql` | New migration |
| `frontend-sv/src/lib/supabase.js` | Added 5 new helper functions |
| `frontend-sv/src/routes/profile/+page.svelte` | Researcher participation management UI |
| `frontend-sv/src/routes/study/[id]/+page.svelte` | Participant consent flow |
| `DOC.md` | Updated Phase 1 status, data model, operation reference |
