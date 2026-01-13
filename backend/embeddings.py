"""
Embeddings client for semantic search
Uses OpenAI text-embedding-3-small (1536 dimensions)
"""
import os
import re
from typing import List
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


def get_openai_client() -> OpenAI:
    """Get OpenAI client instance"""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured in environment")
    return OpenAI(api_key=OPENAI_API_KEY)


def normalize_for_embedding(title: str, brief_summary: str) -> str:
    """
    Normalize text for embedding generation
    Matches SQL function: generate_search_text()

    Format: "{title} | {brief_summary}"
    - Lowercase
    - Collapse multiple whitespace to single space
    - Trim leading/trailing whitespace
    - Preserve medical terminology and acronyms

    Args:
        title: Study title
        brief_summary: Brief summary text

    Returns:
        Normalized text ready for embedding
    """
    text = f"{title or ''} | {brief_summary or ''}"
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    return text.lower().strip()


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using OpenAI

    Args:
        text: Input text (should be normalized via normalize_for_embedding)

    Returns:
        List of 1536 floats (embedding vector)

    Raises:
        RuntimeError: If OPENAI_API_KEY not configured
        Exception: If OpenAI API call fails
    """
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
    """
    Generate embeddings for multiple texts in batches

    OpenAI allows up to 2048 texts per request, but we use conservative
    batch size of 100 to avoid rate limits and timeouts.

    Args:
        texts: List of normalized texts
        batch_size: Number of texts per API call (default 100)

    Returns:
        List of embeddings (same order as input, zero vectors for empty texts)

    Raises:
        RuntimeError: If OPENAI_API_KEY not configured
        Exception: If OpenAI API call fails
    """
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
