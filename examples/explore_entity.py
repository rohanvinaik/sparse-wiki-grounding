#!/usr/bin/env python3
"""
Entity Explorer - Demonstrate Multi-Dimensional Grounding

Shows how entities are positioned across 5 hierarchical dimensions,
enabling structured semantic reasoning.

Usage:
    PYTHONPATH=src python examples/explore_entity.py
    PYTHONPATH=src python examples/explore_entity.py "Albert Einstein"
"""

import sys
from wiki_grounding import EntityStore, SpreadingActivation


def explore_entity(query: str):
    """Explore an entity's grounding across all dimensions."""
    store = EntityStore("data/entities_demo.db")
    spreader = SpreadingActivation(store)

    # Search for entity
    results = store.search(query, limit=1)
    if not results:
        print(f"Entity not found: {query}")
        return

    profile = results[0]
    entity = profile.entity

    print("=" * 70)
    print(f"ENTITY: {entity.label}")
    print("=" * 70)

    # Basic info
    print(f"\nID: {entity.id}")
    if entity.description:
        print(f"Description: {entity.description}")
    if entity.vital_level:
        print(f"Vital Level: {entity.vital_level} (1=most important)")
    if entity.pagerank:
        print(f"PageRank: {entity.pagerank:.4f}")

    # EPA Values (Osgood's Semantic Differential)
    print("\n--- EPA VALUES (Semantic Differential) ---")
    epa = profile.epa
    print(f"  Evaluation: {epa.evaluation.name:8} ({epa.evaluation.value:+d})")
    print(f"  Potency:    {epa.potency.name:8} ({epa.potency.value:+d})")
    print(f"  Activity:   {epa.activity.name:8} ({epa.activity.value:+d})")
    print(f"  Confidence: {epa.confidence:.2f}")

    # Dimension Positions
    print("\n--- DIMENSION POSITIONS (Hierarchical) ---")
    if profile.positions:
        for pos in profile.positions:
            path_str = " > ".join(pos.path_nodes)
            sign_str = {1: "+", -1: "-", 0: "0"}[pos.path_sign]
            print(f"  {pos.dimension.value:10} [{sign_str}] {path_str}")
    else:
        print("  No dimension positions")

    # Relations
    print("\n--- RELATIONS ---")
    related = store.get_related(entity.id, limit=15)
    if related:
        for rel_profile, relation, weight in related:
            print(f"  --[{relation}]--> {rel_profile.entity.label}")
    else:
        print("  No relations found")

    # Incoming relations
    incoming = store.get_related(entity.id, direction="incoming", limit=10)
    if incoming:
        print("\n--- INCOMING RELATIONS ---")
        for rel_profile, relation, weight in incoming:
            rel_type = relation.replace("inverse_", "")
            print(f"  {rel_profile.entity.label} --[{rel_type}]--> {entity.label}")

    # Spreading activation
    print("\n--- SPREADING ACTIVATION (Top 10) ---")
    activated = spreader.spread(entity.id, initial_activation=1.0)
    for result in activated[:10]:
        rel_str = " -> ".join(result.relations[:3]) if result.relations else ""
        print(f"  {result.entity.entity.label:30} (activation={result.activation:.3f}) via {rel_str}")


def demo_multiple():
    """Demo with multiple interesting entities."""
    entities = [
        "Albert Einstein",
        "Paris",
        "Marie Curie",
        "Theory of relativity",
        "Eiffel Tower",
    ]

    print("=" * 70)
    print("MULTI-DIMENSIONAL ENTITY GROUNDING DEMO")
    print("=" * 70)
    print("""
This demo shows how entities are grounded across multiple dimensions:

- SPATIAL:    Geographic hierarchy (Earth > Europe > France > Paris)
- TEMPORAL:   Time position (Past, Present, Future)
- TAXONOMIC:  Type hierarchy (Thing > Person > Scientist)
- SCALE:      Geographic scale (Local, National, Global)
- DOMAIN:     Knowledge domain (Science, Art, Politics)

Each dimension provides a different axis for semantic reasoning.
""")

    for entity_name in entities:
        explore_entity(entity_name)
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        explore_entity(" ".join(sys.argv[1:]))
    else:
        demo_multiple()
