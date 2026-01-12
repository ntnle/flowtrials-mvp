# Flow Trials - AI Features & Caching Implementation Handoff

## Overview

This document details the AI-powered accessibility features and caching system added to Flow Trials. These features help users understand complex medical terminology through plain-language translations and interactive tools.

## What Was Implemented

### 1. AI-Powered Study Assistance Features

Three AI features to make clinical trial information more accessible:

#### A. Plain Title Generation
- **Purpose**: Rewrites complex medical study titles into plain language
- **Format**: Follows `[intervention] for [condition] on [population]` when possible
- **Example**: "A Phase III Randomized Study of..." → "New diabetes medication for adults with type 2 diabetes"
- **Location**: Study page header section

#### B. Plain Summary Generation
- **Purpose**: Converts technical study descriptions into 2-3 paragraph plain-language summaries
- **Features**: No medical jargon, accessible to general public, medically accurate
- **Location**: Study page summary section

#### C. Eligibility Quiz
- **Purpose**: Generates 5-10 yes/no questions to help users self-assess eligibility
- **Features**:
  - Interactive yes/no/unsure buttons
  - Optional explanations for each question
  - Disclaimers about official eligibility confirmation
- **Location**: Study page eligibility criteria section

### 2. Database-Backed Caching System

All AI-generated content is cached in the database to reduce costs and improve performance.

#### Cache Architecture
- **Storage**: Persistent fields in `studies` table
- **Version Control**: `ai_cache_version` field tracks prompt/model changes
- **Invalidation**: Increment version constant to invalidate all caches
- **Cache Keys**: `study_id + ai_cache_version`

#### Cache Behavior
- **Cache Hit**: Instant response from database, no AI API call
- **Cache Miss**: Generate via Anthropic API, save to database for future use
- **Rate Limiting**: Applied only on cache misses (100 requests/60 seconds globally)

## File Changes

### Backend Changes

#### 1. Database Migration
**File**: `supabase/migrations/20260112000000_add_ai_cache.sql`
```sql
ALTER TABLE public.studies
  ADD COLUMN ai_plain_title TEXT,
  ADD COLUMN ai_plain_summary TEXT,
  ADD COLUMN ai_eligibility_quiz JSONB,
  ADD COLUMN ai_cache_version TEXT DEFAULT 'v1',
  ADD COLUMN ai_cached_at TIMESTAMPTZ;
```

#### 2. Backend API (`backend/main.py`)

**New Constants**:
- `AI_CACHE_VERSION = "v1-sonnet-4.5"` - Increment to invalidate all caches

**New Pydantic Models**:
- `EligibilityQuizQuestion` - Question + optional explanation
- Request/Response models for all 3 AI endpoints (with `study_id` and `cached` flag)

**Cache Helper Functions**:
- `save_ai_plain_title(study_id, plain_title)`
- `save_ai_plain_summary(study_id, plain_summary)`
- `save_ai_eligibility_quiz(study_id, quiz_questions)`

**New API Endpoints**:
1. `POST /ai/eligibility-quiz`
   - Input: `study_id`, `eligibility_criteria`
   - Output: Array of quiz questions + `cached` flag

2. `POST /ai/study-summary`
   - Input: `study_id`, title, summary, interventions, conditions
   - Output: Plain-language summary text + `cached` flag

3. `POST /ai/plain-title`
   - Input: `study_id`, title, interventions, conditions
   - Output: Simplified title + `cached` flag

**Cache Logic** (in all endpoints):
```python
# 1. Check cache first
study = get_study_by_id(request.study_id)
if study.ai_field and study.ai_cache_version == AI_CACHE_VERSION:
    return Response(data=study.ai_field, cached=True)

# 2. Generate on cache miss
ai_rate_limiter.check_rate_limit()
result = anthropic_api_call(...)

# 3. Save to cache
save_ai_field(study_id, result)

return Response(data=result, cached=False)
```

**Updated Study Model**:
```python
class Study(BaseModel):
    # ... existing fields ...
    ai_plain_title: Optional[str] = None
    ai_plain_summary: Optional[str] = None
    ai_eligibility_quiz: Optional[List[EligibilityQuizQuestion]] = None
    ai_cache_version: Optional[str] = None
    ai_cached_at: Optional[str] = None
```

#### 3. Dependencies
**File**: `backend/requirements.txt`
```
anthropic==0.39.0  # Added
```

**File**: `backend/.env.example`
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Added
```

### Frontend Changes

#### 1. API Client (`frontend/src/lib/api.js`)

**New Functions**:
```javascript
// All functions now pass study_id for caching
generateEligibilityQuiz(studyId, eligibilityCriteria)
generateStudySummary(study)  // Includes study.id
generatePlainTitle(study)     // Includes study.id
```

#### 2. Study Page (`frontend/src/routes/StudyPage.svelte`)

**New State Variables**:
```javascript
// For each AI feature (quiz/summary/title)
let aiQuiz = null;
let aiQuizLoading = false;
let aiQuizError = '';
let aiQuizExpanded = false;
let quizAnswers = {};  // For quiz only
```

**Cache Loading on Page Load**:
```javascript
async function loadStudy(studyId) {
  study = await getStudyById(studyId);

  // Load cached AI content if available
  if (study.ai_plain_title) {
    aiTitle = study.ai_plain_title;
    aiTitleExpanded = true;
  }
  // ... same for summary and quiz
}
```

**UI Components Added**:
1. **AI Title Button** - Header section (line ~164)
2. **AI Summary Button** - Summary section (line ~194)
3. **AI Quiz Button** - Eligibility section (line ~218)

**Visual Styling**:
- ✨ sparkle icon indicates AI content
- Muted background (`bg-muted/50`)
- Left accent border (`border-l-4 border-accent`)
- Italic text for AI-generated content
- Collapsible sections with ▶/▼ toggle

**Quiz Interactive UI**:
```svelte
<button on:click={() => quizAnswers[idx] = 'yes'}>Yes</button>
<button on:click={() => quizAnswers[idx] = 'no'}>No</button>
<button on:click={() => quizAnswers[idx] = 'unsure'}>Unsure</button>
```

## AI Model & Prompts

**Model**: `claude-sonnet-4-5` (Anthropic)

**Prompt Guidelines**:
- Emphasize medical accuracy
- Avoid medical jargon
- Write for general public (no medical background assumed)
- Keep responses concise (quiz: 5-10 questions, summary: 2-3 paragraphs, title: <15 words)

## How to Use

### For Developers

**Apply Database Migration**:
```bash
cd supabase
supabase db reset  # Applies all migrations including AI cache
```

**Install Backend Dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

**Configure Environment**:
```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Run Services**:
```bash
# Terminal 1: Supabase
cd supabase
supabase start

# Terminal 2: Backend
cd backend
source .venv/bin/activate
uvicorn main:app --reload

# Terminal 3: Frontend
cd frontend
pnpm dev
```

### Cache Invalidation

When prompts or model changes, increment the version:

```python
# backend/main.py
AI_CACHE_VERSION = "v2-sonnet-4.5"  # Changed from v1
```

All existing cached content becomes stale. Next requests will regenerate and re-cache.

### Rate Limiting

- **Global limit**: 100 AI requests per 60 seconds
- **Scope**: Applies only to cache misses
- **Implementation**: In-memory deque (can upgrade to Redis for production)
- **Error**: Returns HTTP 429 when exceeded

## Cost Optimization

### Cache Efficiency
- **First request**: Hits Anthropic API (~$0.003-0.015 per study depending on token count)
- **Subsequent requests**: Free (database lookup)
- **Typical savings**: 95%+ cost reduction after first 100 studies cached

### Token Usage (Estimated per study)
- Plain Title: ~500 tokens
- Plain Summary: ~1500 tokens
- Eligibility Quiz: ~2000 tokens
- **Total per study**: ~4000 tokens = ~$0.012 (Claude Sonnet 4.5 rates)

## Future Enhancements

### Planned (from TODO list)

#### Search Page Pagination & AI Titles
**Acceptance Criteria**:
- "Found X studies" shows total matches
- Results paginated at 10 per page
- Cards show AI plain title (fallback to original)
- Search remains fast (no AI calls block search)

**Implementation**:
1. Update `/search` endpoint to return `total` count and accept pagination params
2. Include `ai_plain_title` in search result items
3. Add pagination controls to Browse.svelte
4. Render cards with AI title fallback: `{study.ai_plain_title || study.title}`

### Additional Considerations

**Background Cache Warming**:
- Create admin job to pre-generate AI content for all studies
- Run nightly or after ingestion
- Ensures all users get instant cached responses

**Per-Study Analytics**:
- Track AI feature usage per study
- Identify most valuable features
- Optimize caching strategy

**Multi-Language Support**:
- Add language parameter to AI requests
- Cache per study + language combination
- Extend `ai_cache_version` to include language code

## Architecture Decisions

### Why Database Caching vs Redis?
- **Pros**: Simpler deployment, persistence across restarts, easier queries
- **Cons**: Slightly slower than Redis (negligible for this use case)
- **Decision**: PostgreSQL sufficient for MVP, can migrate to Redis if needed

### Why Global Rate Limiting?
- **Pros**: Simple implementation, protects budget
- **Cons**: Single user can exhaust quota
- **Decision**: Global sufficient for MVP, can add per-user limits later

### Why Lazy Generation vs Pre-Generation?
- **Pros**: No upfront cost, only generate for viewed studies
- **Cons**: First user per study experiences delay
- **Decision**: Lazy generation for MVP, add background jobs later

## Testing

### Manual Testing Checklist
- [ ] Click "Simplify Title" button on study page
- [ ] Verify title displays with ✨ icon and distinct styling
- [ ] Reload page - verify cached title loads instantly
- [ ] Click "Get Plain Summary" button
- [ ] Verify summary appears with proper formatting
- [ ] Click "Check Your Eligibility" button
- [ ] Verify quiz renders with yes/no/unsure buttons
- [ ] Click quiz answers and verify visual feedback
- [ ] Test all features on study without cached content
- [ ] Test all features on study with cached content
- [ ] Verify rate limiting at 100 requests (requires load testing)

### Database Testing
```sql
-- Verify cache fields exist
SELECT ai_plain_title, ai_plain_summary, ai_cache_version, ai_cached_at
FROM studies
WHERE id = 1;

-- Check cache coverage
SELECT
  COUNT(*) as total_studies,
  COUNT(ai_plain_title) as cached_titles,
  COUNT(ai_plain_summary) as cached_summaries,
  COUNT(ai_eligibility_quiz) as cached_quizzes
FROM studies;

-- Find stale caches
SELECT id, title, ai_cache_version
FROM studies
WHERE ai_cache_version IS NOT NULL
  AND ai_cache_version != 'v1-sonnet-4.5';
```

## Troubleshooting

### AI Generation Fails
**Symptoms**: Error message on frontend
**Causes**:
- Missing `ANTHROPIC_API_KEY`
- Rate limit exceeded
- Invalid API key
- Network issues

**Solutions**:
1. Check backend logs for detailed error
2. Verify `.env` file has valid API key
3. Wait 60 seconds if rate limited
4. Check Anthropic API status page

### Cached Content Not Loading
**Symptoms**: AI buttons visible but no cached content on page load
**Causes**:
- Migration not applied
- Cache version mismatch
- Database connection issue

**Solutions**:
1. Run `supabase db reset`
2. Check `ai_cache_version` matches constant
3. Verify Supabase is running

### Study Page Crashes
**Symptoms**: White screen or error on study page
**Causes**:
- Missing AI fields in Study model
- Type mismatch in quiz data

**Solutions**:
1. Check browser console for errors
2. Verify backend logs for serialization issues
3. Clear browser cache and reload

## Contact & Support

For questions about this implementation:
- Review [DOC.md](DOC.md) for overall architecture
- Check Anthropic API docs for model details
- See Supabase docs for database migrations
