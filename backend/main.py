import json
import os
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager
from collections import deque
from time import time

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from anthropic import Anthropic


# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger("uvicorn.error")


# =============================================================================
# === CONFIG ===
# =============================================================================

DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-admin-token-12345")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# AI Cache version - increment when prompts or model changes
AI_CACHE_VERSION = "v2-sonnet-4.5"


# =============================================================================
# === CONTRACTS ===
# =============================================================================

class Intervention(BaseModel):
    """Intervention detail"""
    intervention_type: Optional[str] = None
    intervention_name: str
    description: Optional[str] = None


class Location(BaseModel):
    """Study location"""
    facility_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class Contact(BaseModel):
    """Study contact"""
    name: str
    role: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class EligibilityQuizQuestion(BaseModel):
    """Single quiz question"""
    question: str
    explanation: Optional[str] = None


class StudyCreate(BaseModel):
    """Input for admin create study"""
    title: str = Field(min_length=1)
    description: Optional[str] = None
    brief_summary: Optional[str] = None
    detailed_description: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    recruiting_status: Optional[str] = None
    study_type: Optional[str] = None
    interventions: List[Intervention] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    locations: List[Location] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)
    site_zips: List[str] = Field(default_factory=list)
    source: str = "internal"
    source_id: Optional[str] = None
    raw_json: Optional[str] = None


class Study(BaseModel):
    """Stored and returned study"""
    id: int
    source: str
    source_id: Optional[str] = None
    title: str
    brief_summary: Optional[str] = None
    detailed_description: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    recruiting_status: Optional[str] = None
    study_type: Optional[str] = None
    interventions: List[Intervention]
    conditions: List[str]
    locations: List[Location]
    contacts: List[Contact]
    site_zips: List[str]
    raw_json: Optional[str] = None
    last_synced_at: Optional[str] = None
    created_at: str
    updated_at: str
    description: Optional[str] = None
    ai_plain_title: Optional[str] = None
    ai_plain_summary: Optional[str] = None
    ai_eligibility_quiz: Optional[List[EligibilityQuizQuestion]] = None
    ai_cache_version: Optional[str] = None
    ai_cached_at: Optional[str] = None


class SearchRequest(BaseModel):
    """Search request parameters"""
    zip: Optional[str] = None
    conditions_include: List[str] = Field(default_factory=list)
    conditions_exclude: List[str] = Field(default_factory=list)
    query_text: Optional[str] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)


class SearchResultItem(BaseModel):
    """Single search result with scoring details"""
    study_id: int
    title: str
    plain_title: Optional[str] = None
    snippet: str
    score: float
    reasons: List[str]
    recruiting_status: Optional[str] = None
    study_type: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    locations_summary: Optional[str] = None


class SearchResponse(BaseModel):
    """Search results container"""
    items: List[SearchResultItem]
    total: int


class EligibilityQuizRequest(BaseModel):
    """Request for eligibility quiz generation"""
    study_id: int
    eligibility_criteria: str


class EligibilityQuizResponse(BaseModel):
    """Response with generated quiz"""
    questions: List[EligibilityQuizQuestion]
    cached: bool = False


class StudySummaryRequest(BaseModel):
    """Request for study summary generation"""
    study_id: int
    title: str
    brief_summary: Optional[str] = None
    detailed_description: Optional[str] = None
    interventions: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)


class StudySummaryResponse(BaseModel):
    """Response with plain-language summary"""
    summary: str
    cached: bool = False


class PlainTitleRequest(BaseModel):
    """Request for plain title generation"""
    study_id: int
    title: str
    brief_summary: Optional[str] = None
    interventions: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)


class PlainTitleResponse(BaseModel):
    """Response with simplified title"""
    plain_title: str
    cached: bool = False


# =============================================================================
# === RATE LIMITER ===
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter for AI endpoints"""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def check_rate_limit(self):
        """Check if request is within rate limit"""
        now = time()
        # Remove old requests outside the window
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

        if len(self.requests) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds."
            )

        self.requests.append(now)


# Global rate limiter: 100 requests per 60 seconds
ai_rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


# =============================================================================
# === AI CLIENT ===
# =============================================================================

def get_anthropic_client() -> Anthropic:
    """Get Anthropic client instance"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured"
        )
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def save_ai_plain_title(study_id: int, plain_title: str):
    """Save AI-generated plain title to database"""
    now = datetime.utcnow()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE studies
            SET ai_plain_title = %s,
                ai_cache_version = %s,
                ai_cached_at = %s
            WHERE id = %s
        """, (plain_title, AI_CACHE_VERSION, now, study_id))


def save_ai_plain_summary(study_id: int, plain_summary: str):
    """Save AI-generated plain summary to database"""
    now = datetime.utcnow()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE studies
            SET ai_plain_summary = %s,
                ai_cache_version = %s,
                ai_cached_at = %s
            WHERE id = %s
        """, (plain_summary, AI_CACHE_VERSION, now, study_id))


def save_ai_eligibility_quiz(study_id: int, quiz_questions: List[EligibilityQuizQuestion]):
    """Save AI-generated eligibility quiz to database"""
    now = datetime.utcnow()
    quiz_data = Jsonb([q.model_dump() for q in quiz_questions])

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE studies
            SET ai_eligibility_quiz = %s,
                ai_cache_version = %s,
                ai_cached_at = %s
            WHERE id = %s
        """, (quiz_data, AI_CACHE_VERSION, now, study_id))


# =============================================================================
# === DB ===
# =============================================================================

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_study(study_data: StudyCreate) -> Study:
    """Insert a new study into the database"""
    now = datetime.utcnow().isoformat()

    # Normalize conditions and zips to lowercase trimmed
    normalized_conditions = [c.strip().lower() for c in study_data.conditions]
    normalized_zips = [z.strip() for z in study_data.site_zips]

    # Prepare JSONB fields using Json adapter
    interventions_json = Jsonb([i.model_dump() for i in study_data.interventions])
    locations_json = Jsonb([loc.model_dump() for loc in study_data.locations])
    contacts_json = Jsonb([c.model_dump() for c in study_data.contacts])

    # Prepare raw_json - convert to Json adapter if it's a string
    raw_json_data = study_data.raw_json
    if isinstance(raw_json_data, str):
        raw_json_data = Jsonb(json.loads(raw_json_data))
    elif raw_json_data is not None:
        raw_json_data = Jsonb(raw_json_data)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO studies
            (source, source_id, title, brief_summary, detailed_description,
             eligibility_criteria, recruiting_status, study_type, interventions,
             conditions, locations, contacts, site_zips, raw_json,
             last_synced_at, created_at, updated_at, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            study_data.source,
            study_data.source_id,
            study_data.title,
            study_data.brief_summary,
            study_data.detailed_description,
            study_data.eligibility_criteria,
            study_data.recruiting_status,
            study_data.study_type,
            interventions_json,
            normalized_conditions,
            locations_json,
            contacts_json,
            normalized_zips,
            raw_json_data,
            now if study_data.source == "ctgov" else None,
            now,
            now,
            study_data.description
        ))
        study_id = cursor.fetchone()['id']

    return get_study_by_id(study_id)


def get_study_by_id(study_id: int) -> Study:
    """Retrieve a study by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies WHERE id = %s", (study_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Study not found")
        return _row_to_study(dict(row))


def list_all_studies() -> List[Study]:
    """Retrieve all studies"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies ORDER BY id")
        rows = cursor.fetchall()
        return [_row_to_study(dict(row)) for row in rows]


def count_studies() -> int:
    """Count total studies in database"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM studies")
        return cursor.fetchone()['count']


def _row_to_study(row: dict) -> Study:
    """Convert database row to Study model"""
    # JSONB columns are returned as Python dicts/lists, not JSON strings
    interventions_data = row["interventions"] if row["interventions"] else []
    locations_data = row["locations"] if row["locations"] else []
    contacts_data = row["contacts"] if row["contacts"] else []

    # Convert raw_json to JSON string if it's a dict (for API response)
    raw_json_value = row["raw_json"]
    if isinstance(raw_json_value, dict):
        raw_json_value = json.dumps(raw_json_value)

    # Parse AI eligibility quiz from JSONB
    ai_quiz_data = row.get("ai_eligibility_quiz")
    ai_quiz = None
    if ai_quiz_data:
        ai_quiz = [EligibilityQuizQuestion(**q) for q in ai_quiz_data]

    return Study(
        id=row["id"],
        source=row["source"],
        source_id=row["source_id"],
        title=row["title"],
        brief_summary=row["brief_summary"],
        detailed_description=row["detailed_description"],
        eligibility_criteria=row["eligibility_criteria"],
        recruiting_status=row["recruiting_status"],
        study_type=row["study_type"],
        interventions=[Intervention(**i) for i in interventions_data],
        conditions=row["conditions"],
        locations=[Location(**loc) for loc in locations_data],
        contacts=[Contact(**c) for c in contacts_data],
        site_zips=row["site_zips"],
        raw_json=raw_json_value,
        last_synced_at=row["last_synced_at"].isoformat() if row["last_synced_at"] else None,
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        description=row["description"],
        ai_plain_title=row.get("ai_plain_title"),
        ai_plain_summary=row.get("ai_plain_summary"),
        ai_eligibility_quiz=ai_quiz,
        ai_cache_version=row.get("ai_cache_version"),
        ai_cached_at=row.get("ai_cached_at").isoformat() if row.get("ai_cached_at") else None
    )


# =============================================================================
# === SEARCH ===
# =============================================================================

def normalize_text(text: Optional[str]) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""
    return text.lower().strip()


def keyword_score(query_text: str, study: Study) -> tuple[int, bool]:
    """Calculate keyword match score and whether match exists"""
    if not query_text:
        return 0, False

    query_lower = normalize_text(query_text)
    search_corpus = " ".join([
        study.title,
        study.brief_summary or "",
        study.detailed_description or "",
        study.eligibility_criteria or "",
        study.description or ""
    ]).lower()

    # Simple substring matching - count occurrences
    keywords = query_lower.split()
    total_score = 0
    has_match = False

    for keyword in keywords:
        if keyword in search_corpus:
            # Count occurrences of this keyword
            count = search_corpus.count(keyword)
            total_score += count * 2  # 2 points per occurrence
            has_match = True

    return total_score, has_match


def search_studies(request: SearchRequest) -> SearchResponse:
    """Execute search with filtering and scoring"""
    all_studies = list_all_studies()
    results = []

    # Normalize request parameters
    include_tags = [normalize_text(c) for c in request.conditions_include]
    exclude_tags = [normalize_text(c) for c in request.conditions_exclude]
    request_zip = request.zip.strip() if request.zip else None

    for study in all_studies:
        study_conditions = [normalize_text(c) for c in study.conditions]

        # FILTERING RULES

        # Apply exclude filter - if study has any excluded tag, skip it
        if any(excluded in study_conditions for excluded in exclude_tags):
            continue

        # Apply include filter - if include list is non-empty, study must match at least one
        if include_tags and not any(included in study_conditions for included in include_tags):
            continue

        # SCORING RULES

        score = 0
        reasons = []

        # +10 for each included condition matched
        matched_includes = [tag for tag in include_tags if tag in study_conditions]
        if matched_includes:
            score += len(matched_includes) * 10
            reasons.append(f"Matched conditions: {', '.join(matched_includes)}")

        # Keyword scoring
        if request.query_text:
            kw_score, has_kw_match = keyword_score(request.query_text, study)
            score += kw_score
            if has_kw_match:
                reasons.append(f"Keyword match in study content")

        # ZIP boost
        if request_zip and request_zip in study.site_zips:
            score += 5
            reasons.append("ZIP match boost")

        # Create snippet from description (140-180 chars, sentence-aware)
        snippet_source = study.brief_summary or study.detailed_description or study.description or "No description available"
        if len(snippet_source) <= 180:
            snippet = snippet_source
        else:
            # Try to cut at sentence boundary within 140-180 range
            truncated = snippet_source[:180]
            last_period = truncated.rfind('. ')
            last_question = truncated.rfind('? ')
            last_exclaim = truncated.rfind('! ')
            sentence_end = max(last_period, last_question, last_exclaim)

            if sentence_end >= 140:
                # Found sentence boundary in acceptable range
                snippet = snippet_source[:sentence_end + 1].strip()
            else:
                # No good sentence boundary, hard cut at 180
                snippet = truncated.rstrip() + "..."

        # Create locations summary
        locations_summary = None
        if study.locations:
            unique_cities = list(set([loc.city for loc in study.locations if loc.city]))
            if unique_cities:
                locations_summary = ", ".join(unique_cities[:3])
                if len(unique_cities) > 3:
                    locations_summary += f" +{len(unique_cities) - 3} more"

        results.append(SearchResultItem(
            study_id=study.id,
            title=study.title,
            plain_title=study.ai_plain_title,
            snippet=snippet,
            score=score,
            reasons=reasons if reasons else ["General match"],
            recruiting_status=study.recruiting_status,
            study_type=study.study_type,
            conditions=study.conditions,
            locations_summary=locations_summary
        ))

    # Sort by score descending
    results.sort(key=lambda x: x.score, reverse=True)

    # Get total count
    total = len(results)

    # Apply pagination
    start_idx = (request.page - 1) * request.limit
    end_idx = start_idx + request.limit
    paginated_results = results[start_idx:end_idx]

    return SearchResponse(items=paginated_results, total=total)


# =============================================================================
# === API ROUTES ===
# =============================================================================

app = FastAPI(title="Clinical Trials Search API")

# CORS configuration for local development and deployed frontend

def get_allowed_origins() -> list[str]:
    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ]
    extra_origins = os.getenv("FRONTEND_ORIGINS")
    if extra_origins:
        origins.extend([origin.strip() for origin in extra_origins.split(",") if origin.strip()])
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/admin/studies", response_model=Study)
def create_study(
    study: StudyCreate,
    x_admin_token: Optional[str] = Header(None)
):
    """Admin endpoint to create a new study"""
    # Simple token authentication
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")

    return insert_study(study)


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """Search studies with filtering and ranking"""
    return search_studies(request)


@app.get("/studies/{study_id}", response_model=Study)
def get_study(study_id: int):
    """Get a specific study by ID"""
    return get_study_by_id(study_id)


@app.post("/ai/eligibility-quiz", response_model=EligibilityQuizResponse)
def generate_eligibility_quiz(request: EligibilityQuizRequest):
    """Generate an eligibility quiz from criteria text"""
    # Check cache first
    try:
        study = get_study_by_id(request.study_id)
        if (study.ai_eligibility_quiz and
            study.ai_cache_version == AI_CACHE_VERSION):
            return EligibilityQuizResponse(
                questions=study.ai_eligibility_quiz,
                cached=True
            )
    except HTTPException:
        pass  # Study not found, continue to generate

    ai_rate_limiter.check_rate_limit()

    client = get_anthropic_client()

    prompt = f"""You are a medical AI assistant helping people understand clinical trial eligibility criteria.

Given the following eligibility criteria, create 5-10 simple yes/no questions that help a person determine if they might be eligible for this study.

Keep questions:
- Simple and clear (no medical jargon)
- Answerable with yes/no
- Focused on the most important criteria
- Medically accurate

Eligibility Criteria:
{request.eligibility_criteria}

Return ONLY a JSON array of objects with this structure:
[
  {{"question": "Are you between 18 and 65 years old?", "explanation": "This study is only for adults in this age range"}},
  ...
]

Do not include any other text, just the JSON array."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Remove markdown code fences if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            # Remove first line (```json or ```) and last line (```)
            if len(lines) > 2:
                response_text = '\n'.join(lines[1:-1]).strip()

        # Try to extract JSON array using regex
        import re
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)

        questions_data = json.loads(response_text)

        questions = [EligibilityQuizQuestion(**q) for q in questions_data]

        # Save to cache
        save_ai_eligibility_quiz(request.study_id, questions)

        return EligibilityQuizResponse(questions=questions, cached=False)

    except json.JSONDecodeError as e:
        logger.exception("Failed to parse AI response for eligibility quiz", extra={"study_id": request.study_id})
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        logger.exception("AI generation failed for eligibility quiz", extra={"study_id": request.study_id})
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@app.post("/ai/study-summary", response_model=StudySummaryResponse)
def generate_study_summary(request: StudySummaryRequest):
    """Generate a plain-language summary of a study"""
    # Check cache first
    try:
        study = get_study_by_id(request.study_id)
        if (study.ai_plain_summary and
            study.ai_cache_version == AI_CACHE_VERSION):
            return StudySummaryResponse(
                summary=study.ai_plain_summary,
                cached=True
            )
    except HTTPException:
        pass  # Study not found, continue to generate

    ai_rate_limiter.check_rate_limit()

    client = get_anthropic_client()

    interventions_text = ", ".join(request.interventions) if request.interventions else "Not specified"
    conditions_text = ", ".join(request.conditions) if request.conditions else "Not specified"

    prompt = f"""You are a medical AI assistant that rewrites study information into plain, accessible language.

Task: Write a concise summary of the study's research goals using ONLY the information provided below. Do not add facts, make assumptions, or infer details not stated. If a detail is missing, omit it or say "Not provided."

Focus on what the study is trying to learn or test. Describe what participation involves only if it is explicitly stated.

Style: neutral and factual (no marketing), 1-2 short paragraphs (3-6 sentences total), no bullet points or headings. Return only the summary text.

Study Information:
Title: {request.title}
Conditions: {conditions_text}
Interventions: {interventions_text}
Brief Summary: {request.brief_summary or "Not provided"}
Detailed Description: {request.detailed_description or "Not provided"}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )

        summary = message.content[0].text.strip()

        # Save to cache
        save_ai_plain_summary(request.study_id, summary)

        return StudySummaryResponse(summary=summary, cached=False)

    except Exception as e:
        logger.exception("AI generation failed for study summary", extra={"study_id": request.study_id})
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@app.post("/ai/plain-title", response_model=PlainTitleResponse)
def generate_plain_title(request: PlainTitleRequest):
    """Generate a plain-language title"""
    # Check cache first
    try:
        study = get_study_by_id(request.study_id)
        if (study.ai_plain_title and
            study.ai_cache_version == AI_CACHE_VERSION):
            return PlainTitleResponse(
                plain_title=study.ai_plain_title,
                cached=True
            )
    except HTTPException:
        pass  # Study not found, continue to generate

    ai_rate_limiter.check_rate_limit()

    client = get_anthropic_client()

    interventions_text = ", ".join(request.interventions) if request.interventions else "Not specified"
    conditions_text = ", ".join(request.conditions) if request.conditions else "Not specified"

    prompt = f"""You are a medical AI assistant helping people understand clinical trials.

Given the following clinical trial information, rewrite the title in plain language without medical jargon.

Try to follow the format: [intervention] for [condition] on [population]
For example: "New diabetes medication for adults with type 2 diabetes"

If the format doesn't fit naturally, use another clear structure.

Keep it:
- Simple and clear (no medical jargon)
- Under 15 words
- Medically accurate
- Informative

Study Information:
Original Title: {request.title}
Conditions: {conditions_text}
Interventions: {interventions_text}
Brief Summary: {request.brief_summary or "Not provided"}

Return ONLY the simplified title text, nothing else."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        plain_title = message.content[0].text.strip()

        # Save to cache
        save_ai_plain_title(request.study_id, plain_title)

        return PlainTitleResponse(plain_title=plain_title, cached=False)

    except Exception as e:
        logger.exception("AI generation failed for plain title", extra={"study_id": request.study_id})
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "total_studies": count_studies(), "database": "supabase-postgres"}


# =============================================================================
# === STARTUP ===
# =============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize application on startup"""
    print("Connecting to Supabase Postgres...")
    print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")

    # Test database connection
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM studies")
            count = cursor.fetchone()['count']
            print(f"Successfully connected! Found {count} studies in database.")
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        print("Make sure Supabase is running: supabase start")

    print("Application ready.")
