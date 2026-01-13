"""
Backfill embeddings for existing studies
Resumable: skips studies that already have embeddings
"""
import sys
from time import sleep
from pathlib import Path

# Add backend directory to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from search_module import generate_embeddings_batch, normalize_for_embedding
from platform_module import get_db

BATCH_SIZE = 100  # OpenAI allows up to 2048, but 100 is safer for rate limits
RATE_LIMIT_DELAY = 1.0  # Seconds between batches


def backfill_embeddings(dry_run: bool = False):
    """
    Backfill embeddings for studies missing them

    Args:
        dry_run: If True, only print what would be done without making changes
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Count studies needing embeddings
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM studies
            WHERE embedding IS NULL AND search_text IS NOT NULL
        """)
        total = cursor.fetchone()["count"]

        print(f"Found {total} studies needing embeddings")
        if total == 0:
            print("✓ Nothing to backfill! All studies have embeddings.")
            return

        if dry_run:
            print(f"[DRY RUN] Would process these studies in batches of {BATCH_SIZE}")
            return

        # Fetch and process studies in batches
        processed = 0
        while True:
            cursor.execute("""
                SELECT id, search_text
                FROM studies
                WHERE embedding IS NULL AND search_text IS NOT NULL
                ORDER BY id
                LIMIT %s
            """, (BATCH_SIZE,))

            batch = cursor.fetchall()
            if not batch:
                break

            print(f"\nProcessing batch: {processed + 1} to {processed + len(batch)}")

            # Generate embeddings for batch
            texts = [row["search_text"] for row in batch]
            try:
                embeddings = generate_embeddings_batch(texts)
            except Exception as e:
                print(f"ERROR generating embeddings: {e}")
                print("Sleeping 10 seconds before retry...")
                sleep(10)
                continue

            # Update database
            update_count = 0
            for row, embedding in zip(batch, embeddings):
                try:
                    cursor.execute("""
                        UPDATE studies
                        SET embedding = %s
                        WHERE id = %s
                    """, (embedding, row["id"]))
                    update_count += 1
                except Exception as e:
                    print(f"  ERROR updating study {row['id']}: {e}")

            conn.commit()
            processed += update_count
            progress_pct = int(100 * processed / total) if total > 0 else 100
            print(f"Progress: {processed}/{total} ({progress_pct}%)")

            # Rate limiting between batches
            if processed < total:
                sleep(RATE_LIMIT_DELAY)

        print(f"\n✓ Backfill complete! Processed {processed} studies.")


def create_index():
    """Create IVFFLAT index after backfill completes"""
    print("\nCreating IVFFLAT index for vector similarity search...")
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if index already exists
        cursor.execute("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'studies' AND indexname = 'idx_studies_embedding_ivfflat'
        """)
        if cursor.fetchone():
            print("✓ Index already exists, skipping.")
            return

        print("Building index (this may take a few minutes)...")
        cursor.execute("""
            CREATE INDEX idx_studies_embedding_ivfflat ON public.studies
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        conn.commit()
        print("✓ Index created successfully!")


def verify_embeddings():
    """Verify embedding coverage and index status"""
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)

    with get_db() as conn:
        cursor = conn.cursor()

        # Count embeddings
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(embedding) as with_embedding,
                COUNT(*) FILTER (WHERE embedding IS NULL) as missing
            FROM studies
        """)
        stats = cursor.fetchone()

        print(f"\nEmbedding Coverage:")
        print(f"  Total studies: {stats['total']}")
        print(f"  With embeddings: {stats['with_embedding']}")
        print(f"  Missing embeddings: {stats['missing']}")

        if stats['missing'] > 0:
            print(f"\n⚠ Warning: {stats['missing']} studies still missing embeddings")
        else:
            print(f"\n✓ All studies have embeddings!")

        # Check index
        cursor.execute("""
            SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes
            WHERE tablename = 'studies' AND indexname LIKE '%embedding%'
        """)
        indexes = cursor.fetchall()

        if indexes:
            print(f"\nIndexes:")
            for idx in indexes:
                print(f"  {idx['indexname']}: {idx['size']}")
        else:
            print(f"\n⚠ No embedding indexes found")

    print("=" * 60 + "\n")


def main():
    """Main backfill runner"""
    print("=" * 60)
    print("EMBEDDINGS BACKFILL SCRIPT")
    print("=" * 60)

    dry_run = "--dry-run" in sys.argv
    skip_index = "--skip-index" in sys.argv
    verify_only = "--verify" in sys.argv

    if verify_only:
        verify_embeddings()
        return

    # Run backfill
    backfill_embeddings(dry_run=dry_run)

    # Create index if requested
    if not dry_run and not skip_index:
        create_index()

    # Verify results
    if not dry_run:
        verify_embeddings()

    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
