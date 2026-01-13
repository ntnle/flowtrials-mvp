"""
AI MODULE
Owns AI-assisted features (plain titles, summaries, eligibility quizzes).

Boundaries:
- AI generation: Anthropic API calls for title/summary/quiz generation
- Caching: AI response caching in database
- Rate limiting: AI API rate limiting and retry logic
"""
import json
import os
import logging
import re
from datetime import datetime
from collections import deque
from time import time
from typing import List, Optional

from psycopg.types.json import Jsonb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from anthropic import Anthropic

from platform_module import get_db
from search_module import EligibilityQuizQuestion, get_study_by_id

# Configure logger
logger = logging.getLogger("uvicorn.error")


# ======================================================================
# CONFIG
# ======================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# AI Cache version - increment when prompts or model changes
AI_CACHE_VERSION = "v2-sonnet-4.5"


# ======================================================================
# TYPES
# ======================================================================

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


# ======================================================================
# DEPENDENCIES
# ======================================================================

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


def get_anthropic_client() -> Anthropic:
    """Get Anthropic client instance"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured"
        )
    return Anthropic(api_key=ANTHROPIC_API_KEY)


# ======================================================================
# REPO
# ======================================================================

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


# ======================================================================
# SERVICE
# ======================================================================
# (No additional service logic needed; generation happens in routes)


# ======================================================================
# ROUTES
# ======================================================================

def register_ai_routes(app: FastAPI):
    """Register AI generation endpoints"""

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
