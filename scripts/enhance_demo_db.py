#!/usr/bin/env python3
"""
Enhance the demo database for impressive demonstrations.

This script:
1. Rebuilds from source with more entities (vital level 1-4)
2. Adds SPATIAL dimension positions based on location relations
3. Adds important showcase entities even if above vital threshold
4. Normalizes relation names for verifier compatibility
"""

import sqlite3
import shutil
import json
from pathlib import Path

SOURCE_DB = Path("/Users/rohanvinaik/relational-ai/data/sparse_wiki.db")
OUTPUT_DB = Path(__file__).parent.parent / "data" / "entities_demo.db"

# Important entities to always include (for impressive demos)
SHOWCASE_ENTITIES = [
    "Q_Albert_Einstein", "Q_Marie_Curie", "Q_Isaac_Newton", "Q_Charles_Darwin",
    "Q_Galileo_Galilei", "Q_Nikola_Tesla", "Q_Thomas_Edison", "Q_Leonardo_da_Vinci",
    "Q_William_Shakespeare", "Q_Wolfgang_Amadeus_Mozart", "Q_Ludwig_van_Beethoven",
    "Q_Paris", "Q_London", "Q_New_York_City", "Q_Tokyo", "Q_Rome", "Q_Berlin",
    "Q_France", "Q_United_Kingdom", "Q_United_States", "Q_Germany", "Q_Italy", "Q_Japan", "Q_China", "Q_India",
    "Q_Earth", "Q_Moon", "Q_Sun", "Q_Mars", "Q_Jupiter",
    "Q_Eiffel_Tower", "Q_Statue_of_Liberty", "Q_Great_Wall_of_China", "Q_Colosseum",
    "Q_Theory_of_relativity", "Q_Evolution", "Q_Gravity", "Q_Quantum_mechanics",
    "Q_World_War_I", "Q_World_War_II", "Q_French_Revolution", "Q_Renaissance",
    "Q_DNA", "Q_Atom", "Q_Light", "Q_Electricity",
    "Q_Telephone", "Q_Light_bulb", "Q_Printing_press", "Q_Steam_engine",
    "Q_Hamlet", "Q_Mona_Lisa", "Q_Symphony_No._9_(Beethoven)",
    "Q_Nobel_Prize", "Q_Nobel_Prize_in_Physics", "Q_Nobel_Prize_in_Chemistry",
    "Q_Harvard_University", "Q_University_of_Cambridge", "Q_University_of_Oxford",
    "Q_Napoleon", "Q_Julius_Caesar", "Q_Alexander_the_Great", "Q_Cleopatra",
    "Q_Radioactivity", "Q_Polonium", "Q_Radium", "Q_Pierre_Curie",
]

# SPATIAL positions to add (entity_id -> path)
SPATIAL_DATA = {
    # Cities
    "Q_Paris": ["Earth", "Europe", "France", "Paris"],
    "Q_London": ["Earth", "Europe", "United Kingdom", "England", "London"],
    "Q_New_York_City": ["Earth", "North America", "United States", "New York", "New York City"],
    "Q_Tokyo": ["Earth", "Asia", "Japan", "Tokyo"],
    "Q_Rome": ["Earth", "Europe", "Italy", "Rome"],
    "Q_Berlin": ["Earth", "Europe", "Germany", "Berlin"],

    # Countries
    "Q_France": ["Earth", "Europe", "France"],
    "Q_United_Kingdom": ["Earth", "Europe", "United Kingdom"],
    "Q_United_States": ["Earth", "North America", "United States"],
    "Q_Germany": ["Earth", "Europe", "Germany"],
    "Q_Italy": ["Earth", "Europe", "Italy"],
    "Q_Japan": ["Earth", "Asia", "Japan"],
    "Q_China": ["Earth", "Asia", "China"],
    "Q_India": ["Earth", "Asia", "India"],

    # Landmarks
    "Q_Eiffel_Tower": ["Earth", "Europe", "France", "Paris", "Eiffel Tower"],
    "Q_Statue_of_Liberty": ["Earth", "North America", "United States", "New York", "Statue of Liberty"],
    "Q_Great_Wall_of_China": ["Earth", "Asia", "China", "Great Wall of China"],
    "Q_Colosseum": ["Earth", "Europe", "Italy", "Rome", "Colosseum"],

    # Continents
    "Q_Europe": ["Earth", "Europe"],
    "Q_Asia": ["Earth", "Asia"],
    "Q_North_America": ["Earth", "North America"],
    "Q_South_America": ["Earth", "South America"],
    "Q_Africa": ["Earth", "Africa"],

    # Universities
    "Q_Harvard_University": ["Earth", "North America", "United States", "Massachusetts", "Cambridge", "Harvard University"],
    "Q_University_of_Cambridge": ["Earth", "Europe", "United Kingdom", "England", "Cambridge", "University of Cambridge"],
    "Q_University_of_Oxford": ["Earth", "Europe", "United Kingdom", "England", "Oxford", "University of Oxford"],
}

# Additional relations to add for impressive demos
EXTRA_RELATIONS = [
    # Einstein's works
    ("Q_Albert_Einstein", "Q_Theory_of_relativity", "created", 1.0),
    ("Q_Albert_Einstein", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Albert_Einstein", "Q_Germany", "born_in", 1.0),
    ("Q_Albert_Einstein", "Q_United_States", "lived_in", 1.0),

    # Marie Curie
    ("Q_Marie_Curie", "Q_Radioactivity", "discovered", 1.0),
    ("Q_Marie_Curie", "Q_Polonium", "discovered", 1.0),
    ("Q_Marie_Curie", "Q_Radium", "discovered", 1.0),
    ("Q_Marie_Curie", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Marie_Curie", "Q_Nobel_Prize_in_Chemistry", "awarded", 1.0),
    ("Q_Marie_Curie", "Q_Pierre_Curie", "spouse_of", 1.0),
    ("Q_Pierre_Curie", "Q_Marie_Curie", "spouse_of", 1.0),

    # Thomas Edison
    ("Q_Thomas_Edison", "Q_Light_bulb", "invented", 1.0),
    ("Q_Thomas_Edison", "Q_United_States", "born_in", 1.0),

    # Shakespeare
    ("Q_William_Shakespeare", "Q_Hamlet", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_United_Kingdom", "born_in", 1.0),

    # Da Vinci
    ("Q_Leonardo_da_Vinci", "Q_Mona_Lisa", "created", 1.0),
    ("Q_Leonardo_da_Vinci", "Q_Italy", "born_in", 1.0),

    # Beethoven
    ("Q_Ludwig_van_Beethoven", "Q_Symphony_No._9_(Beethoven)", "composed", 1.0),
    ("Q_Ludwig_van_Beethoven", "Q_Germany", "born_in", 1.0),

    # Newton
    ("Q_Isaac_Newton", "Q_Gravity", "discovered", 1.0),
    ("Q_Isaac_Newton", "Q_United_Kingdom", "born_in", 1.0),

    # Darwin
    ("Q_Charles_Darwin", "Q_Evolution", "developed", 1.0),
    ("Q_Charles_Darwin", "Q_United_Kingdom", "born_in", 1.0),

    # Landmarks -> locations (inverse)
    ("Q_Eiffel_Tower", "Q_Paris", "located_in", 1.0),
    ("Q_Eiffel_Tower", "Q_France", "located_in", 1.0),
    ("Q_Statue_of_Liberty", "Q_New_York_City", "located_in", 1.0),
    ("Q_Statue_of_Liberty", "Q_United_States", "located_in", 1.0),
    ("Q_Colosseum", "Q_Rome", "located_in", 1.0),
    ("Q_Colosseum", "Q_Italy", "located_in", 1.0),
    ("Q_Great_Wall_of_China", "Q_China", "located_in", 1.0),

    # Cities -> countries
    ("Q_Paris", "Q_France", "capital_of", 1.0),
    ("Q_Paris", "Q_France", "located_in", 1.0),
    ("Q_London", "Q_United_Kingdom", "capital_of", 1.0),
    ("Q_London", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_Berlin", "Q_Germany", "capital_of", 1.0),
    ("Q_Rome", "Q_Italy", "capital_of", 1.0),
    ("Q_Tokyo", "Q_Japan", "capital_of", 1.0),

    # Universities
    ("Q_Harvard_University", "Q_United_States", "located_in", 1.0),
    ("Q_University_of_Cambridge", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_University_of_Oxford", "Q_United_Kingdom", "located_in", 1.0),

    # Historical figures
    ("Q_Napoleon", "Q_France", "leader_of", 1.0),
    ("Q_Napoleon", "Q_France", "born_in", 1.0),
    ("Q_Julius_Caesar", "Q_Rome", "leader_of", 1.0),
    ("Q_Cleopatra", "Q_Egypt", "leader_of", 1.0),
]

# Relation name normalization (ConceptNet -> our format)
RELATION_NORMALIZATION = {
    "AtLocation": "located_in",
    "PartOf": "part_of",
    "IsA": "instance_of",
    "HasA": "has",
    "CapableOf": "can",
    "UsedFor": "used_for",
    "Causes": "causes",
    "HasProperty": "has_property",
    "SymbolOf": "symbol_of",
    "DefinedAs": "defined_as",
    "MadeOf": "made_of",
    "ReceivesAction": "receives_action",
    "CreatedBy": "created_by",
    "Synonym": "same_as",
    "Antonym": "opposite_of",
    "DerivedFrom": "derived_from",
    "RelatedTo": "related_to",
    "FormOf": "form_of",
    "SimilarTo": "similar_to",
    "EtymologicallyRelatedTo": "etymologically_related",
    "FieldOf": "field_of",
}


def main():
    if not SOURCE_DB.exists():
        print(f"Source DB not found: {SOURCE_DB}")
        return

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)

    # Copy full DB
    print(f"Copying from {SOURCE_DB}...")
    shutil.copy(SOURCE_DB, OUTPUT_DB)

    conn = sqlite3.connect(OUTPUT_DB)
    conn.row_factory = sqlite3.Row

    # 1. Delete non-vital entities (keep level 1-4 + showcase)
    print("Filtering entities...")
    showcase_ids = ", ".join(f"'{e}'" for e in SHOWCASE_ENTITIES)
    conn.execute(f"""
        DELETE FROM entities
        WHERE (vital_level IS NULL OR vital_level > 4)
        AND id NOT IN ({showcase_ids})
        AND label LIKE '%[%'
    """)

    # Also remove wiki markup junk
    conn.execute("DELETE FROM entities WHERE label LIKE '%[[%'")
    conn.execute("DELETE FROM entities WHERE label LIKE '%{{%'")
    conn.execute("DELETE FROM entities WHERE label LIKE '%==%'")

    # 2. Cascade deletes
    print("Cleaning orphaned records...")
    conn.execute("DELETE FROM dimension_positions WHERE entity_id NOT IN (SELECT id FROM entities)")
    conn.execute("DELETE FROM epa_values WHERE entity_id NOT IN (SELECT id FROM entities)")
    conn.execute("DELETE FROM properties WHERE entity_id NOT IN (SELECT id FROM entities)")
    conn.execute("""
        DELETE FROM entity_links
        WHERE source_id NOT IN (SELECT id FROM entities)
        OR target_id NOT IN (SELECT id FROM entities)
    """)

    # 3. Add SPATIAL positions
    print("Adding SPATIAL dimension positions...")
    for entity_id, path in SPATIAL_DATA.items():
        # Check if entity exists
        exists = conn.execute("SELECT 1 FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if not exists:
            continue

        # Check if already has SPATIAL
        has_spatial = conn.execute(
            "SELECT 1 FROM dimension_positions WHERE entity_id = ? AND dimension = 'SPATIAL'",
            (entity_id,)
        ).fetchone()

        if not has_spatial:
            conn.execute("""
                INSERT INTO dimension_positions
                (entity_id, dimension, path_sign, path_depth, path_nodes, zero_state)
                VALUES (?, 'SPATIAL', 1, ?, ?, 'Earth')
            """, (entity_id, len(path) - 1, json.dumps(path)))
            print(f"  Added SPATIAL for {entity_id}: {'/'.join(path)}")

    # 4. Normalize relation names
    print("Normalizing relation names...")
    for old_name, new_name in RELATION_NORMALIZATION.items():
        cursor = conn.execute(
            "UPDATE entity_links SET relation = ? WHERE relation = ?",
            (new_name, old_name)
        )
        if cursor.rowcount > 0:
            print(f"  {old_name} -> {new_name}: {cursor.rowcount} relations")

    # 5. Add extra relations for demos
    print("Adding showcase relations...")
    for source, target, relation, weight in EXTRA_RELATIONS:
        # Check both entities exist
        s_exists = conn.execute("SELECT 1 FROM entities WHERE id = ?", (source,)).fetchone()
        t_exists = conn.execute("SELECT 1 FROM entities WHERE id = ?", (target,)).fetchone()

        if s_exists and t_exists:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO entity_links (source_id, target_id, relation, weight)
                    VALUES (?, ?, ?, ?)
                """, (source, target, relation, weight))
            except:
                pass  # Ignore duplicates

    # 6. Vacuum
    conn.commit()
    print("Vacuuming...")
    conn.execute("VACUUM")
    conn.commit()

    # Report
    stats = {}
    stats['entities'] = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    stats['positions'] = conn.execute("SELECT COUNT(*) FROM dimension_positions").fetchone()[0]
    stats['spatial'] = conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'SPATIAL'").fetchone()[0]
    stats['epa'] = conn.execute("SELECT COUNT(*) FROM epa_values").fetchone()[0]
    stats['links'] = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]

    size_mb = OUTPUT_DB.stat().st_size / 1024 / 1024

    print()
    print("=" * 50)
    print(f"Created {OUTPUT_DB}")
    print("=" * 50)
    print(f"  Entities:     {stats['entities']:,}")
    print(f"  Positions:    {stats['positions']:,}")
    print(f"  SPATIAL:      {stats['spatial']:,}")
    print(f"  EPA values:   {stats['epa']:,}")
    print(f"  Entity links: {stats['links']:,}")
    print(f"  Size:         {size_mb:.1f} MB")

    conn.close()


if __name__ == "__main__":
    main()
