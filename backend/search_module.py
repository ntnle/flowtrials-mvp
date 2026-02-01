"""
SEARCH MODULE
Owns study search, scoring, and retrieval logic.

Boundaries:
- Search: Keyword matching, semantic search, custom scoring
- Ingestion: CT.gov data fetch and normalization (helpers only; scripts live in scripts/)
- Study data: CRUD operations for studies table
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional, List

from psycopg.types.json import Jsonb
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

from platform_module import get_db, ADMIN_TOKEN

# Configure logger
logger = logging.getLogger("uvicorn.error")


# ======================================================================
# CONFIG
# ======================================================================

# Feature flag for semantic search
USE_SEMANTIC_SEARCH = os.getenv("USE_SEMANTIC_SEARCH", "false").lower() == "true"

# CT.gov API configuration
CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2"

# OpenAI embeddings configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


# ======================================================================
# TYPES
# ======================================================================

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
    media: List[dict] = Field(default_factory=list)
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
    media: List[dict] = Field(default_factory=list)
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
    tasks: List[dict] = Field(default_factory=list)


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


# ======================================================================
# DEPENDENCIES
# ======================================================================

# --- CT.gov API Client ---

def fetch_studies_from_ctgov(
    query_cond: Optional[str] = None,
    page_size: int = 100,
    page_token: Optional[str] = None,
    recruiting_status: Optional[str] = None
) -> dict:
    """Fetch studies from ClinicalTrials.gov API v2"""
    import requests

    url = f"{CTGOV_API_BASE}/studies"
    params = {
        "format": "json",
        "pageSize": min(page_size, 1000)
    }

    if query_cond:
        params["query.cond"] = query_cond
    if recruiting_status:
        params["filter.overallStatus"] = recruiting_status
    if page_token:
        params["pageToken"] = page_token

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    return {
        "studies": data.get("studies", []),
        "nextPageToken": data.get("nextPageToken")
    }


def fetch_all_pages_from_ctgov(
    query_cond: Optional[str] = None,
    max_pages: int = 5,
    page_size: int = 100,
    recruiting_status: Optional[str] = None
) -> List[dict]:
    """Fetch multiple pages of studies from CT.gov"""
    all_studies = []
    page_token = None
    pages_fetched = 0

    while pages_fetched < max_pages:
        result = fetch_studies_from_ctgov(
            query_cond=query_cond,
            page_size=page_size,
            page_token=page_token,
            recruiting_status=recruiting_status
        )

        studies = result.get("studies", [])
        all_studies.extend(studies)

        pages_fetched += 1
        page_token = result.get("nextPageToken")

        if not page_token:
            break

    return all_studies


# --- CT.gov Data Normalization ---

def safe_get(data: dict, *keys, default=None):
    """Safely navigate nested dict"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, {})
        else:
            return default
    return data if data != {} else default


def normalize_ctgov_study(raw_study: dict) -> StudyCreate:
    """Normalize a single CT.gov study to our StudyCreate model"""
    protocol = raw_study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    description_mod = protocol.get("descriptionModule", {})
    eligibility_mod = protocol.get("eligibilityModule", {})
    status_mod = protocol.get("statusModule", {})
    design_mod = protocol.get("designModule", {})
    conditions_mod = protocol.get("conditionsModule", {})
    arms_interventions_mod = protocol.get("armsInterventionsModule", {})
    contacts_locations_mod = protocol.get("contactsLocationsModule", {})

    # NCT ID
    nct_id = identification.get("nctId", "")

    # Title
    title = identification.get("officialTitle") or identification.get("briefTitle", "Untitled Study")

    # Descriptions
    brief_summary = safe_get(description_mod, "briefSummary", default="")
    detailed_description = safe_get(description_mod, "detailedDescription", default="")

    # Eligibility
    eligibility_criteria = safe_get(eligibility_mod, "eligibilityCriteria", default="")

    # Status
    recruiting_status = safe_get(status_mod, "overallStatus", default="Unknown")

    # Study type
    study_type = safe_get(design_mod, "studyType", default="")

    # Conditions
    conditions = conditions_mod.get("conditions", [])
    conditions_normalized = [c.lower().replace(" ", "-") for c in conditions]

    # Interventions
    interventions_raw = arms_interventions_mod.get("interventions", [])
    interventions = []
    for intv in interventions_raw:
        interventions.append(Intervention(
            intervention_type=intv.get("type"),
            intervention_name=intv.get("name", "Unknown"),
            description=intv.get("description")
        ))

    # Locations
    locations_raw = contacts_locations_mod.get("locations", [])
    locations = []
    for loc in locations_raw:
        facility = loc.get("facility", "")
        city = loc.get("city", "")
        state = loc.get("state", "")
        country = loc.get("country", "")
        geo = loc.get("geoPoint", {})

        locations.append(Location(
            facility_name=facility,
            city=city,
            state=state,
            country=country,
            lat=geo.get("lat") if geo else None,
            lon=geo.get("lon") if geo else None
        ))

    # Contacts
    central_contacts_raw = contacts_locations_mod.get("centralContacts", [])
    contacts = []
    for contact in central_contacts_raw:
        contacts.append(Contact(
            name=contact.get("name", "Unknown"),
            role=contact.get("role"),
            phone=contact.get("phone"),
            email=contact.get("email")
        ))

    # Site zips (we don't have this in CT.gov, so empty for now)
    site_zips = []

    # Raw JSON
    raw_json = json.dumps(raw_study)

    return StudyCreate(
        source="ctgov",
        source_id=nct_id,
        title=title,
        brief_summary=brief_summary,
        detailed_description=detailed_description,
        eligibility_criteria=eligibility_criteria,
        recruiting_status=recruiting_status,
        study_type=study_type,
        interventions=interventions,
        conditions=conditions_normalized,
        locations=locations,
        contacts=contacts,
        site_zips=site_zips,
        raw_json=raw_json
    )


# --- OpenAI Embeddings ---

def get_openai_client():
    """Get OpenAI client instance"""
    from openai import OpenAI

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured in environment")
    return OpenAI(api_key=OPENAI_API_KEY)


def normalize_for_embedding(title: str, brief_summary: str) -> str:
    """Normalize text for embedding generation (matches SQL function)"""
    import re

    text = f"{title or ''} | {brief_summary or ''}"
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    return text.lower().strip()


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text using OpenAI"""
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * EMBEDDING_DIMENSION

    client = get_openai_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding


def generate_embeddings_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """Generate embeddings for multiple texts in batches"""
    if not texts:
        return []

    # Filter out empty texts and track indices
    non_empty_indices = [i for i, t in enumerate(texts) if t and t.strip()]
    non_empty_texts = [texts[i] for i in non_empty_indices]

    if not non_empty_texts:
        # All texts are empty, return zero vectors
        return [[0.0] * EMBEDDING_DIMENSION] * len(texts)

    client = get_openai_client()
    all_embeddings = []

    # Process in batches
    for i in range(0, len(non_empty_texts), batch_size):
        batch = non_empty_texts[i:i + batch_size]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            encoding_format="float"
        )
        all_embeddings.extend([item.embedding for item in response.data])

    # Reconstruct full list with zero vectors for empty texts
    embeddings = [[0.0] * EMBEDDING_DIMENSION] * len(texts)
    for idx, orig_idx in enumerate(non_empty_indices):
        embeddings[orig_idx] = all_embeddings[idx]

    return embeddings


# ======================================================================
# REPO
# ======================================================================

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
    media_json = Jsonb(study_data.media if study_data.media else [])

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
             conditions, locations, contacts, site_zips, media, raw_json,
             last_synced_at, created_at, updated_at, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            media_json,
            raw_json_data,
            now if study_data.source == "ctgov" else None,
            now,
            now,
            study_data.description
        ))
        study_id = cursor.fetchone()['id']

    return get_study_by_id(study_id)


def get_study_by_id(study_id: int) -> Study:
    """Retrieve a study by ID (published only)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM studies WHERE id = %s AND is_published = TRUE",
            (study_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Study not found")
        return _row_to_study(dict(row))


def list_all_studies() -> List[Study]:
    """Retrieve all studies (published only)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies WHERE is_published = TRUE ORDER BY id")
        rows = cursor.fetchall()
        return [_row_to_study(dict(row)) for row in rows]


def _row_to_study(row: dict) -> Study:
    """Convert database row to Study model"""
    # JSONB columns are returned as Python dicts/lists, not JSON strings
    interventions_data = row["interventions"] if row["interventions"] else []
    locations_data = row["locations"] if row["locations"] else []
    contacts_data = row["contacts"] if row["contacts"] else []
    media_data = row.get("media") if row.get("media") else []

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
        media=media_data,
        raw_json=raw_json_value,
        last_synced_at=row["last_synced_at"].isoformat() if row["last_synced_at"] else None,
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
        updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        description=row["description"],
        ai_plain_title=row.get("ai_plain_title"),
        ai_plain_summary=row.get("ai_plain_summary"),
        ai_eligibility_quiz=ai_quiz,
        ai_cache_version=row.get("ai_cache_version"),
        ai_cached_at=row.get("ai_cached_at").isoformat() if row.get("ai_cached_at") else None,
        tasks=row.get("tasks") or []
    )


# ======================================================================
# SERVICE
# ======================================================================

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


def generate_snippet(study: Study) -> str:
    """Extract snippet from study description (sentence-aware truncation)"""
    snippet_source = study.brief_summary or study.detailed_description or study.description or "No description available"
    if len(snippet_source) <= 180:
        return snippet_source

    truncated = snippet_source[:180]
    last_period = truncated.rfind('. ')
    last_question = truncated.rfind('? ')
    last_exclaim = truncated.rfind('! ')
    sentence_end = max(last_period, last_question, last_exclaim)

    if sentence_end >= 140:
        return snippet_source[:sentence_end + 1].strip()
    else:
        return truncated.rstrip() + "..."


def generate_locations_summary(study: Study) -> Optional[str]:
    """Generate locations summary from study locations"""
    if not study.locations:
        return None
    unique_cities = list(set([loc.city for loc in study.locations if loc.city]))
    if not unique_cities:
        return None
    locations_summary = ", ".join(unique_cities[:3])
    if len(unique_cities) > 3:
        locations_summary += f" +{len(unique_cities) - 3} more"
    return locations_summary


def search_studies_semantic(request: SearchRequest) -> SearchResponse:
    """
    Execute semantic search with vector similarity + keyword fallback
    Hybrid approach: Union vector candidates with keyword candidates
    """
    # Normalize request parameters
    include_tags = [normalize_text(c) for c in request.conditions_include]
    exclude_tags = [normalize_text(c) for c in request.conditions_exclude]
    request_zip = request.zip.strip() if request.zip else None

    # If no query text, fall back to condition-only filtering
    if not request.query_text or not request.query_text.strip():
        return search_studies(request)

    # Generate query embedding
    try:
        query_embedding = generate_embedding(request.query_text.lower().strip())
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        # Fall back to keyword-only search
        return search_studies(request)

    # Fetch candidates via hybrid approach
    candidate_map = {}

    with get_db() as conn:
        cursor = conn.cursor()

        # Fetch vector similarity candidates (top 150, published only)
        cursor.execute("""
            SELECT id, source, source_id, title, brief_summary, detailed_description,
                   description, eligibility_criteria, recruiting_status, study_type,
                   interventions, conditions, locations, contacts, site_zips,
                   created_at, updated_at, ai_plain_title,
                   (embedding <=> %s::vector) as similarity_distance
            FROM studies
            WHERE embedding IS NOT NULL AND is_published = TRUE
            ORDER BY similarity_distance
            LIMIT 150
        """, (query_embedding,))
        vector_candidates = cursor.fetchall()

        for row in vector_candidates:
            candidate_map[row["id"]] = (row, row.get("similarity_distance", 1.0))

        # Fetch keyword/trigram candidates (top 50, published only)
        cursor.execute("""
            SELECT id, source, source_id, title, brief_summary, detailed_description,
                   description, eligibility_criteria, recruiting_status, study_type,
                   interventions, conditions, locations, contacts, site_zips,
                   created_at, updated_at, ai_plain_title
            FROM studies
            WHERE search_text %% %s AND is_published = TRUE
            ORDER BY similarity(search_text, %s) DESC
            LIMIT 50
        """, (request.query_text.lower(), request.query_text.lower()))
        keyword_candidates = cursor.fetchall()

        for row in keyword_candidates:
            if row["id"] not in candidate_map:
                candidate_map[row["id"]] = (row, 0.5)  # Neutral similarity for keyword-only

    # Convert to Study objects and apply filters + scoring
    results = []
    for study_id, (row, similarity_distance) in candidate_map.items():
        # Parse locations
        locations = []
        if row.get("locations"):
            for loc_data in row["locations"]:
                locations.append(Location(
                    facility_name=loc_data.get("facility_name"),
                    city=loc_data.get("city"),
                    state=loc_data.get("state"),
                    country=loc_data.get("country")
                ))

        # Parse interventions
        interventions = []
        if row.get("interventions"):
            for int_data in row["interventions"]:
                interventions.append(Intervention(
                    intervention_type=int_data.get("intervention_type"),
                    intervention_name=int_data.get("intervention_name"),
                    description=int_data.get("description")
                ))

        # Parse contacts
        contacts = []
        if row.get("contacts"):
            for contact_data in row["contacts"]:
                contacts.append(Contact(
                    name=contact_data.get("name"),
                    role=contact_data.get("role"),
                    phone=contact_data.get("phone"),
                    email=contact_data.get("email")
                ))

        # Create Study object
        study = Study(
            id=row["id"],
            source=row["source"],
            source_id=row.get("source_id"),
            title=row["title"],
            brief_summary=row.get("brief_summary"),
            detailed_description=row.get("detailed_description"),
            eligibility_criteria=row.get("eligibility_criteria"),
            description=row.get("description"),
            recruiting_status=row.get("recruiting_status"),
            study_type=row.get("study_type"),
            interventions=interventions,
            conditions=row.get("conditions", []),
            locations=locations,
            contacts=contacts,
            site_zips=row.get("site_zips", []),
            created_at=row["created_at"].isoformat() if row.get("created_at") else "",
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
            ai_plain_title=row.get("ai_plain_title")
        )

        study_conditions = [normalize_text(c) for c in study.conditions]

        # FILTERING RULES
        # Apply exclude filter
        if any(excluded in study_conditions for excluded in exclude_tags):
            continue

        # Apply include filter
        if include_tags and not any(included in study_conditions for included in include_tags):
            continue

        # SCORING RULES
        score = 0
        reasons = []

        # Vector similarity score (convert distance to similarity: closer to 0 = better)
        # Scale: distance ∈ [0, 2] → similarity_score ∈ [100, 0]
        vector_score = int((1.0 - min(similarity_distance, 1.0)) * 100)
        score += vector_score
        if vector_score > 50:
            reasons.append(f"Semantic match ({vector_score})")

        # +10 for each included condition matched
        matched_includes = [tag for tag in include_tags if tag in study_conditions]
        if matched_includes:
            score += len(matched_includes) * 10
            reasons.append(f"Conditions: {', '.join(matched_includes)}")

        # Keyword bonus (check if query terms appear in text)
        kw_score, has_kw_match = keyword_score(request.query_text, study)
        if has_kw_match:
            score += kw_score
            reasons.append("Keyword match")

        # ZIP boost
        if request_zip and request_zip in study.site_zips:
            score += 5
            reasons.append("ZIP match")

        # Generate snippet and locations summary
        snippet = generate_snippet(study)
        locations_summary = generate_locations_summary(study)

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

    # Apply pagination
    total = len(results)
    start_idx = (request.page - 1) * request.limit
    end_idx = start_idx + request.limit
    paginated_results = results[start_idx:end_idx]

    return SearchResponse(items=paginated_results, total=total)


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


# ======================================================================
# ROUTES
# ======================================================================

def register_search_routes(app: FastAPI):
    """Register search and study endpoints"""

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
        if USE_SEMANTIC_SEARCH:
            return search_studies_semantic(request)
        else:
            return search_studies(request)

    @app.get("/studies/{study_id}", response_model=Study)
    def get_study(study_id: int):
        """Get a specific study by ID"""
        return get_study_by_id(study_id)
