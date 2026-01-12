"""
ClinicalTrials.gov API v2 Client
"""
import requests
from typing import Optional, List, Dict, Any


CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2"


def fetch_studies(
    query_cond: Optional[str] = None,
    page_size: int = 100,
    page_token: Optional[str] = None,
    recruiting_status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch studies from ClinicalTrials.gov API v2

    Args:
        query_cond: Condition search term
        page_size: Number of results per page (max 1000)
        page_token: Token for pagination
        recruiting_status: Filter by recruiting status (e.g., "RECRUITING")

    Returns:
        Dict with 'studies' list and 'nextPageToken' if available
    """
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


def fetch_all_pages(
    query_cond: Optional[str] = None,
    max_pages: int = 5,
    page_size: int = 100,
    recruiting_status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch multiple pages of studies

    Args:
        query_cond: Condition search term
        max_pages: Maximum number of pages to fetch
        page_size: Results per page
        recruiting_status: Filter by recruiting status (e.g., "RECRUITING")

    Returns:
        List of all study objects
    """
    all_studies = []
    page_token = None
    pages_fetched = 0

    while pages_fetched < max_pages:
        result = fetch_studies(
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
