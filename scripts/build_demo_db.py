#!/usr/bin/env python3
"""
Build demo database from full sparse_wiki.db

Extracts Vital Articles Level 1-3 (~5K entities) for lightweight distribution.
"""

import sqlite3
import shutil
from pathlib import Path

SOURCE_DB = Path("/Users/rohanvinaik/relational-ai/data/sparse_wiki.db")
OUTPUT_DB = Path(__file__).parent.parent / "data" / "entities_demo.db"
MAX_VITAL_LEVEL = 3

def main():
    if not SOURCE_DB.exists():
        print(f"Source DB not found: {SOURCE_DB}")
        print("Run this after building the full sparse_wiki.db")
        return

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)

    # Copy full DB
    print(f"Copying from {SOURCE_DB}...")
    shutil.copy(SOURCE_DB, OUTPUT_DB)

    # Prune to vital articles only
    conn = sqlite3.connect(OUTPUT_DB)

    # Delete non-vital entities
    conn.execute(
        "DELETE FROM entities WHERE vital_level IS NULL OR vital_level > ?",
        (MAX_VITAL_LEVEL,)
    )

    # Cascade deletes
    conn.execute(
        "DELETE FROM dimension_positions WHERE entity_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM epa_values WHERE entity_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM properties WHERE entity_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM entity_links WHERE source_id NOT IN (SELECT id FROM entities) "
        "OR target_id NOT IN (SELECT id FROM entities)"
    )
    # The MIGRATION_PLAN references entity_anchors but it is not in the schema.sql I just wrote!
    # I will assume the table exists in the source DB and needs deletion.
    # However, if it's not in the schema, maybe it's not needed. 
    # But for safety, I will wrap it in try-except or just execute it if table exists.
    # Actually, the user's plan explicitly included it in the delete section but implied it's not in new schema.
    # So I will check if table exists first.
    
    try:
        conn.execute(
            "DELETE FROM entity_anchors WHERE entity_id NOT IN (SELECT id FROM entities)"
        )
    except sqlite3.OperationalError:
        pass # Table might not exist or not needed

    # Vacuum to reclaim space
    conn.commit()  # Commit deletes before VACUUM
    
    # VACUUM cannot be run in a transaction, so we need to ensure autocommit mode or similar.
    # But conn.commit() ends the current transaction. 
    # However, Python sqlite3 might start a new one automatically.
    # The safest way is to set isolation_level to None temporarily or just rely on commit() being enough if we are not in a new one yet.
    # Actually, execute() will start a transaction for DML. VACUUM is mainenance.
    # Let's try setting isolation_level to None for the VACUUM.
    
    old_isolation = conn.isolation_level
    conn.isolation_level = None
    conn.execute("VACUUM")
    conn.isolation_level = old_isolation

    # Report
    count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    size_mb = OUTPUT_DB.stat().st_size / 1024 / 1024

    print(f"Created {OUTPUT_DB}")
    print(f"  Entities: {count:,}")
    print(f"  Size: {size_mb:.1f} MB")

    conn.close()


if __name__ == "__main__":
    main()
