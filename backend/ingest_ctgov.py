"""
Ingestion script for ClinicalTrials.gov studies
Fetches studies by condition and stores them in the database
"""
import sys
from datetime import datetime
from ctgov_client import fetch_all_pages
from ctgov_normalizer import normalize_ctgov_study
from main import insert_study, get_db


DEFAULT_CONDITIONS = [
    "Diabetes",
    "Asthma",
    "Depression",
    "Heart Disease",
    "Arthritis",
    "Cancer",
    "Hypertension",
    "Anxiety"
]


def upsert_ctgov_study(study_create):
    """
    Insert or update a CT.gov study in the database
    Uses source_id (NCT ID) to check for existing study
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM studies WHERE source = 'ctgov' AND source_id = %s",
            (study_create.source_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing study
            study_id = existing["id"]
            now = datetime.utcnow().isoformat()

            import json
            from psycopg2.extras import Json

            # Prepare data for JSONB columns (use Json adapter)
            interventions_json = Json([i.model_dump() for i in study_create.interventions])
            locations_json = Json([loc.model_dump() for loc in study_create.locations])
            contacts_json = Json([c.model_dump() for c in study_create.contacts])

            # Prepare raw_json - convert to Json adapter if it's a string
            raw_json_data = study_create.raw_json
            if isinstance(raw_json_data, str):
                raw_json_data = Json(json.loads(raw_json_data))
            elif raw_json_data is not None:
                raw_json_data = Json(raw_json_data)

            # Prepare arrays
            normalized_conditions = [c.strip().lower() for c in study_create.conditions]
            normalized_zips = [z.strip() for z in study_create.site_zips]

            cursor.execute("""
                UPDATE studies
                SET title = %s,
                    brief_summary = %s,
                    detailed_description = %s,
                    eligibility_criteria = %s,
                    recruiting_status = %s,
                    study_type = %s,
                    interventions = %s,
                    conditions = %s,
                    locations = %s,
                    contacts = %s,
                    site_zips = %s,
                    raw_json = %s,
                    last_synced_at = %s,
                    updated_at = %s
                WHERE id = %s
            """, (
                study_create.title,
                study_create.brief_summary,
                study_create.detailed_description,
                study_create.eligibility_criteria,
                study_create.recruiting_status,
                study_create.study_type,
                interventions_json,
                normalized_conditions,
                locations_json,
                contacts_json,
                normalized_zips,
                raw_json_data,
                now,
                now,
                study_id
            ))
            print(f"  Updated: {study_create.source_id} - {study_create.title[:60]}")
        else:
            # Insert new study
            insert_study(study_create)
            print(f"  Inserted: {study_create.source_id} - {study_create.title[:60]}")


def ingest_condition(condition: str, max_pages: int = 3, recruiting_only: bool = True):
    """
    Ingest studies for a specific condition

    Args:
        condition: Condition search term
        max_pages: Maximum number of pages to fetch (100 studies per page)
        recruiting_only: If True, only fetch RECRUITING studies
    """
    print(f"\nFetching studies for condition: {condition}")
    print(f"Max pages: {max_pages} (up to {max_pages * 100} studies)")
    if recruiting_only:
        print("Filter: RECRUITING studies only")

    try:
        studies = fetch_all_pages(
            query_cond=condition,
            max_pages=max_pages,
            recruiting_status="RECRUITING" if recruiting_only else None
        )
        print(f"Fetched {len(studies)} studies from CT.gov")

        for idx, raw_study in enumerate(studies, 1):
            try:
                study_create = normalize_ctgov_study(raw_study)
                upsert_ctgov_study(study_create)
            except Exception as e:
                import traceback
                print(f"  Error processing study {idx}: {e}")
                print(f"  Study ID: {raw_study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'Unknown')}")
                traceback.print_exc()
                continue

        print(f"Completed ingestion for: {condition}")

    except Exception as e:
        print(f"Error fetching studies for {condition}: {e}")


def main():
    """Main ingestion runner"""
    print("=" * 60)
    print("ClinicalTrials.gov Ingestion Script")
    print("=" * 60)

    conditions_to_ingest = DEFAULT_CONDITIONS
    max_pages = 3

    if len(sys.argv) > 1:
        conditions_to_ingest = sys.argv[1:]

    print(f"\nConditions to ingest: {', '.join(conditions_to_ingest)}")
    print(f"Pages per condition: {max_pages}\n")

    for condition in conditions_to_ingest:
        ingest_condition(condition, max_pages=max_pages)

    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
