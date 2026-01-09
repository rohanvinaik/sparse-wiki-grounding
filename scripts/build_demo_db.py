#!/usr/bin/env python3
"""
Build Demo Database from Sparse Wiki Source

Creates a compact demo database by copying REAL structured data from the source:
- All vital level 1-4 entities (preserves natural hierarchy)
- Actual dimension_positions (no fabrication)
- Zero states for all 5 dimensions
- Anchor dictionary (dictionary-encoded semantic labels)
- Entity anchors (cross-node connectivity layer)
- Entity links from source

NO fabricated data. NO cherry-picked entities. NO hardcoded paths.
"""

import sqlite3
import json
from pathlib import Path

SOURCE_DB = Path("/Users/rohanvinaik/relational-ai/data/sparse_wiki.db")
OUTPUT_DB = Path(__file__).parent.parent / "data" / "entities_demo.db"


def main():
    if not SOURCE_DB.exists():
        print(f"Source DB not found: {SOURCE_DB}")
        return

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    # Create new database
    conn = sqlite3.connect(OUTPUT_DB)
    conn.row_factory = sqlite3.Row

    # Create schema with full anchor layer support
    conn.executescript("""
        -- Core entity table
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            wikipedia_title TEXT,
            label TEXT NOT NULL,
            description TEXT,
            vital_level INTEGER,
            pagerank REAL
        );

        -- Hierarchical dimension positions
        CREATE TABLE dimension_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            dimension TEXT NOT NULL,       -- SPATIAL, TEMPORAL, TAXONOMIC, SCALE, DOMAIN
            path_sign INTEGER NOT NULL,    -- +1 (specific), -1 (abstract), 0 (at zero)
            path_depth INTEGER NOT NULL,   -- Distance from zero state
            path_nodes TEXT NOT NULL,      -- JSON array of path nodes
            zero_state TEXT NOT NULL       -- Root node for this dimension
        );

        -- EPA semantic differential values
        CREATE TABLE epa_values (
            entity_id TEXT PRIMARY KEY,
            evaluation INTEGER NOT NULL DEFAULT 0,  -- -1/0/+1
            potency INTEGER NOT NULL DEFAULT 0,     -- -1/0/+1
            activity INTEGER NOT NULL DEFAULT 0,    -- -1/0/+1
            confidence REAL DEFAULT 1.0
        );

        -- Entity properties
        CREATE TABLE properties (
            entity_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (entity_id, key)
        );

        -- Entity-to-entity links
        CREATE TABLE entity_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            UNIQUE(source_id, target_id, relation)
        );

        -- Zero states for each dimension tree
        CREATE TABLE zero_states (
            dimension TEXT PRIMARY KEY,
            zero_node TEXT NOT NULL,
            score REAL,
            computed_at TEXT
        );

        -- Anchor dictionary: dictionary-encoded semantic labels
        CREATE TABLE anchor_dictionary (
            anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT UNIQUE NOT NULL,     -- Human-readable label
            entity_id TEXT,                 -- Link to entity if exists
            category TEXT                   -- SCOPE, HISTORY, KNOWN_FOR, GEOGRAPHY
        );

        -- Entity anchors: cross-node connectivity layer
        CREATE TABLE entity_anchors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            anchor_id INTEGER NOT NULL,
            weight REAL DEFAULT 1.0,
            source TEXT DEFAULT 'pagelinks',
            UNIQUE(entity_id, anchor_id),
            FOREIGN KEY(anchor_id) REFERENCES anchor_dictionary(anchor_id)
        );

        -- Semantic anchors view for easy querying
        CREATE VIEW semantic_anchors AS
        SELECT
            ea.id,
            ea.entity_id,
            ad.category as anchor_type,
            ad.entity_id as anchor_entity_id,
            ad.label as anchor_label,
            ea.weight,
            ea.source
        FROM entity_anchors ea
        JOIN anchor_dictionary ad ON ea.anchor_id = ad.anchor_id;

        -- Indexes for performance
        CREATE INDEX idx_entities_label ON entities(label);
        CREATE INDEX idx_entities_label_lower ON entities(LOWER(label));
        CREATE INDEX idx_entities_vital ON entities(vital_level);
        CREATE INDEX idx_dim_pos_entity ON dimension_positions(entity_id);
        CREATE INDEX idx_dim_pos_dimension ON dimension_positions(dimension);
        CREATE INDEX idx_links_source ON entity_links(source_id);
        CREATE INDEX idx_links_target ON entity_links(target_id);
        CREATE INDEX idx_anchor_dict_label ON anchor_dictionary(label);
        CREATE INDEX idx_anchor_dict_category ON anchor_dictionary(category);
        CREATE INDEX idx_entity_anchors_entity ON entity_anchors(entity_id);
        CREATE INDEX idx_entity_anchors_anchor ON entity_anchors(anchor_id);
    """)

    # Connect to source
    src = sqlite3.connect(SOURCE_DB)
    src.row_factory = sqlite3.Row

    # ==========================================================================
    # Step 1: Copy zero_states (dimension roots)
    # ==========================================================================
    print("Copying zero states...")
    zero_states = src.execute("SELECT * FROM zero_states").fetchall()
    for zs in zero_states:
        conn.execute("""
            INSERT INTO zero_states (dimension, zero_node, score, computed_at)
            VALUES (?, ?, ?, ?)
        """, (zs["dimension"], zs["zero_node"], zs["score"], zs["computed_at"]))
    print(f"  Copied {len(zero_states)} zero states")

    # ==========================================================================
    # Step 2: Select entities - vital level 1-4 (preserves natural hierarchy)
    # ==========================================================================
    print("Selecting entities (vital level 1-4)...")
    entities = src.execute("""
        SELECT * FROM entities
        WHERE vital_level IS NOT NULL AND vital_level <= 4
    """).fetchall()

    # Filter out wiki markup junk
    valid_entities = []
    for e in entities:
        label = e["label"] or ""
        # Skip markup-contaminated entries
        if "[[" in label or "{{" in label or "==" in label or "|" in label:
            continue
        # Skip overly long labels (likely parsing errors)
        if len(label) > 100:
            continue
        valid_entities.append(e)

    entity_ids = {e["id"] for e in valid_entities}
    print(f"  Selected {len(valid_entities)} entities")

    # ==========================================================================
    # Step 3: Copy entities
    # ==========================================================================
    print("Copying entities...")
    for e in valid_entities:
        conn.execute("""
            INSERT INTO entities (id, wikipedia_title, label, description, vital_level, pagerank)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (e["id"], e["wikipedia_title"], e["label"], e["description"],
              e["vital_level"], e["pagerank"]))

    # ==========================================================================
    # Step 4: Copy dimension positions (REAL paths, not fabricated)
    # ==========================================================================
    print("Copying dimension positions...")
    position_count = 0
    for e_id in entity_ids:
        positions = src.execute("""
            SELECT * FROM dimension_positions WHERE entity_id = ?
        """, (e_id,)).fetchall()
        for p in positions:
            conn.execute("""
                INSERT INTO dimension_positions
                (entity_id, dimension, path_sign, path_depth, path_nodes, zero_state)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (p["entity_id"], p["dimension"], p["path_sign"],
                  p["path_depth"], p["path_nodes"], p["zero_state"]))
            position_count += 1
    print(f"  Copied {position_count} dimension positions")

    # ==========================================================================
    # Step 5: Copy EPA values
    # ==========================================================================
    print("Copying EPA values...")
    epa_count = 0
    for e_id in entity_ids:
        epa = src.execute("SELECT * FROM epa_values WHERE entity_id = ?", (e_id,)).fetchone()
        if epa:
            conn.execute("""
                INSERT INTO epa_values (entity_id, evaluation, potency, activity, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (epa["entity_id"], epa["evaluation"], epa["potency"],
                  epa["activity"], epa["confidence"]))
            epa_count += 1
    print(f"  Copied {epa_count} EPA values")

    # ==========================================================================
    # Step 6: Copy properties
    # ==========================================================================
    print("Copying properties...")
    prop_count = 0
    for e_id in entity_ids:
        props = src.execute("SELECT * FROM properties WHERE entity_id = ?", (e_id,)).fetchall()
        for p in props:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO properties (entity_id, key, value)
                    VALUES (?, ?, ?)
                """, (p["entity_id"], p["key"], p["value"]))
                prop_count += 1
            except:
                pass
    print(f"  Copied {prop_count} properties")

    # ==========================================================================
    # Step 7: Copy entity links (only between included entities)
    # ==========================================================================
    print("Copying entity links...")
    links = src.execute("""
        SELECT source_id, target_id, relation, weight FROM entity_links
    """).fetchall()

    link_count = 0
    for link in links:
        if link["source_id"] in entity_ids and link["target_id"] in entity_ids:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO entity_links (source_id, target_id, relation, weight)
                    VALUES (?, ?, ?, ?)
                """, (link["source_id"], link["target_id"], link["relation"], link["weight"]))
                link_count += 1
            except:
                pass
    print(f"  Copied {link_count} entity links")

    # ==========================================================================
    # Step 8: Copy anchor dictionary (for anchors used by included entities)
    # ==========================================================================
    print("Copying anchor dictionary...")

    # First, find which anchor_ids are used by our entities
    anchor_ids_used = set()
    for e_id in entity_ids:
        anchors = src.execute("""
            SELECT anchor_id FROM entity_anchors WHERE entity_id = ?
        """, (e_id,)).fetchall()
        for a in anchors:
            anchor_ids_used.add(a["anchor_id"])

    print(f"  Found {len(anchor_ids_used)} anchors used by included entities")

    # Copy those anchors from the dictionary
    anchor_id_mapping = {}  # old_id -> new_id
    if anchor_ids_used:
        anchor_ids_str = ", ".join(str(a) for a in anchor_ids_used)
        anchors = src.execute(f"""
            SELECT * FROM anchor_dictionary
            WHERE anchor_id IN ({anchor_ids_str})
        """).fetchall()

        for a in anchors:
            cursor = conn.execute("""
                INSERT INTO anchor_dictionary (label, entity_id, category)
                VALUES (?, ?, ?)
            """, (a["label"], a["entity_id"], a["category"]))
            anchor_id_mapping[a["anchor_id"]] = cursor.lastrowid

    print(f"  Copied {len(anchor_id_mapping)} anchor dictionary entries")

    # ==========================================================================
    # Step 9: Copy entity anchors (cross-node connectivity layer)
    # ==========================================================================
    print("Copying entity anchors (cross-node connectivity)...")
    anchor_link_count = 0
    for e_id in entity_ids:
        anchors = src.execute("""
            SELECT * FROM entity_anchors WHERE entity_id = ?
        """, (e_id,)).fetchall()
        for a in anchors:
            old_anchor_id = a["anchor_id"]
            new_anchor_id = anchor_id_mapping.get(old_anchor_id)
            if new_anchor_id:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO entity_anchors (entity_id, anchor_id, weight, source)
                        VALUES (?, ?, ?, ?)
                    """, (a["entity_id"], new_anchor_id, a["weight"], a["source"]))
                    anchor_link_count += 1
                except:
                    pass
    print(f"  Copied {anchor_link_count} entity-anchor links")

    src.close()
    conn.commit()

    # Vacuum to optimize
    print("Optimizing database...")
    conn.execute("VACUUM")
    conn.commit()

    # ==========================================================================
    # Final stats
    # ==========================================================================
    stats = {
        'entities': conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
        'positions': conn.execute("SELECT COUNT(*) FROM dimension_positions").fetchone()[0],
        'spatial': conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'SPATIAL'").fetchone()[0],
        'temporal': conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'TEMPORAL'").fetchone()[0],
        'taxonomic': conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'TAXONOMIC'").fetchone()[0],
        'scale': conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'SCALE'").fetchone()[0],
        'domain': conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'DOMAIN'").fetchone()[0],
        'epa': conn.execute("SELECT COUNT(*) FROM epa_values").fetchone()[0],
        'links': conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0],
        'unique_relations': conn.execute("SELECT COUNT(DISTINCT relation) FROM entity_links").fetchone()[0],
        'anchors': conn.execute("SELECT COUNT(*) FROM anchor_dictionary").fetchone()[0],
        'anchor_links': conn.execute("SELECT COUNT(*) FROM entity_anchors").fetchone()[0],
        'zero_states': conn.execute("SELECT COUNT(*) FROM zero_states").fetchone()[0],
    }

    # Check anchor categories
    anchor_cats = conn.execute("""
        SELECT category, COUNT(*) as cnt FROM anchor_dictionary GROUP BY category
    """).fetchall()

    conn.close()
    size_mb = OUTPUT_DB.stat().st_size / 1024 / 1024

    print()
    print("=" * 60)
    print(f"Created {OUTPUT_DB}")
    print("=" * 60)
    print(f"  Entities:              {stats['entities']:,}")
    print(f"  Dimension Positions:   {stats['positions']:,}")
    print(f"    - SPATIAL:           {stats['spatial']:,}")
    print(f"    - TEMPORAL:          {stats['temporal']:,}")
    print(f"    - TAXONOMIC:         {stats['taxonomic']:,}")
    print(f"    - SCALE:             {stats['scale']:,}")
    print(f"    - DOMAIN:            {stats['domain']:,}")
    print(f"  EPA values:            {stats['epa']:,}")
    print(f"  Entity links:          {stats['links']:,}")
    print(f"  Relation types:        {stats['unique_relations']}")
    print(f"  Zero states:           {stats['zero_states']}")
    print(f"  Anchor dictionary:     {stats['anchors']:,}")
    print(f"  Entity-anchor links:   {stats['anchor_links']:,}")
    print()
    print("  Anchor categories:")
    for cat in anchor_cats:
        print(f"    - {cat['category'] or 'None':15} {cat['cnt']:,}")
    print()
    print(f"  Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
