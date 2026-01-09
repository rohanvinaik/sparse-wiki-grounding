#!/usr/bin/env python3
"""
Entity Explorer - Demonstrate Multi-Dimensional Grounding

Shows how entities are positioned across 5 hierarchical dimensions
with signed vector navigation and cross-node anchor connectivity.

Usage:
    PYTHONPATH=src python examples/explore_entity.py
    PYTHONPATH=src python examples/explore_entity.py "Albert Einstein"
"""

import sys
from wiki_grounding import EntityStore, SpreadingActivation
from wiki_grounding.entity import GroundingDimension


def explore_entity(query: str, store: EntityStore):
    """Explore an entity's grounding across all dimensions."""
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

    # Dimension Positions with signed vectors
    print("\n--- DIMENSION POSITIONS (Signed Vectors) ---")
    print("  Each dimension has a zero state (root). Path sign indicates direction:")
    print("    +depth: More specific than zero (e.g., Paris vs Earth)")
    print("    -depth: More abstract than zero")
    print()

    # Get all zero states
    zero_states = store.get_all_zero_states()

    for dim in GroundingDimension:
        pos = profile.get_position(dim)
        zero = zero_states.get(dim.value, "?")
        signed_dist = profile.distance_from_zero(dim)

        if pos:
            path_str = " > ".join(pos.path_nodes)
            sign_str = f"+{pos.path_depth}" if pos.path_sign > 0 else f"{pos.path_sign * pos.path_depth}"
            print(f"  {dim.value:10} [{sign_str:>3}] {path_str}")
            print(f"              (zero state: {zero})")
        else:
            print(f"  {dim.value:10} [  0] (no position, zero state: {zero})")

    # Position vector summary
    print("\n--- SIGNED POSITION VECTOR ---")
    pos_vec = profile.position_vector()
    print(f"  {pos_vec}")

    # Anchors (Cross-Node Connectivity Layer)
    print("\n--- SEMANTIC ANCHORS (Cross-Node Layer) ---")
    anchors = store.get_entity_anchors(entity.id)
    if anchors:
        # Group by category
        by_cat = {}
        for anchor_id, label, category, weight in anchors[:30]:
            cat = category or "UNKNOWN"
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append((label, weight))

        for cat, items in sorted(by_cat.items()):
            print(f"\n  {cat}:")
            for label, weight in items[:5]:
                print(f"    - {label} (weight: {weight:.2f})")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")
    else:
        print("  No anchors found")

    # Relations
    print("\n--- DIRECT RELATIONS ---")
    related = store.get_related(entity.id, limit=10)
    if related:
        for rel_profile, relation, weight in related:
            print(f"  --[{relation}]--> {rel_profile.entity.label}")
    else:
        print("  No direct relations found")

    # Spreading activation through anchor layer
    print("\n--- SPREADING ACTIVATION (with anchor layer) ---")
    activated = spreader.spread(entity.id, initial_activation=1.0, use_anchors=True)
    if activated:
        print(f"  Activated {len(activated)} entities through graph + anchor layer:")
        for result in activated[:8]:
            rel_str = " > ".join(result.relations[:2]) if result.relations else "direct"
            # Show bank activations if present
            bank_str = ""
            if result.bank_activations:
                active_banks = [(b.value, v) for b, v in result.bank_activations.items() if v > 0]
                if active_banks:
                    bank_str = f" [{', '.join(f'{b}:{v:.2f}' for b, v in active_banks[:2])}]"
            print(f"    {result.entity.entity.label:30} (act={result.activation:.3f}) via {rel_str}{bank_str}")
    else:
        print("  No entities activated")


def show_hierarchical_comparison(store: EntityStore):
    """Show hierarchical distance and shared ancestors."""
    print("\n" + "=" * 70)
    print("HIERARCHICAL COMPARISON DEMO")
    print("=" * 70)

    # Find two entities to compare
    paris = store.search_exact("Paris", limit=1)
    london = store.search_exact("London", limit=1)
    tokyo = store.search_exact("Tokyo", limit=1)

    if paris and london:
        paris_p = paris[0]
        london_p = london[0]

        print(f"\nComparing: {paris_p.entity.label} vs {london_p.entity.label}")
        print("-" * 40)

        # Show paths
        paris_path = paris_p.navigate_from_zero(GroundingDimension.SPATIAL)
        london_path = london_p.navigate_from_zero(GroundingDimension.SPATIAL)

        print(f"  Paris SPATIAL:  {' > '.join(paris_path) if paris_path else 'N/A'}")
        print(f"  London SPATIAL: {' > '.join(london_path) if london_path else 'N/A'}")

        # Shared ancestor
        ancestor = paris_p.shared_ancestor(london_p, GroundingDimension.SPATIAL)
        if ancestor:
            print(f"  Shared ancestor: {ancestor}")

        # Hierarchical distance
        dist = paris_p.hierarchical_distance(london_p, GroundingDimension.SPATIAL)
        print(f"  Hierarchical distance: {dist}")

    if paris and tokyo:
        paris_p = paris[0]
        tokyo_p = tokyo[0]

        print(f"\nComparing: {paris_p.entity.label} vs {tokyo_p.entity.label}")
        print("-" * 40)

        paris_path = paris_p.navigate_from_zero(GroundingDimension.SPATIAL)
        tokyo_path = tokyo_p.navigate_from_zero(GroundingDimension.SPATIAL)

        print(f"  Paris SPATIAL: {' > '.join(paris_path) if paris_path else 'N/A'}")
        print(f"  Tokyo SPATIAL: {' > '.join(tokyo_path) if tokyo_path else 'N/A'}")

        ancestor = paris_p.shared_ancestor(tokyo_p, GroundingDimension.SPATIAL)
        print(f"  Shared ancestor: {ancestor if ancestor else 'N/A (different continents)'}")


def show_anchor_connectivity(store: EntityStore):
    """Demonstrate cross-node connectivity through anchors."""
    print("\n" + "=" * 70)
    print("ANCHOR LAYER CONNECTIVITY DEMO")
    print("=" * 70)

    # Get anchor stats
    stats = store.anchor_stats()
    print(f"\nAnchor Layer Statistics:")
    print(f"  Dictionary entries: {stats['anchor_dictionary']:,}")
    print(f"  Entity-anchor links: {stats['entity_anchor_links']:,}")
    print(f"  By category:")
    for cat, count in sorted(stats.get('by_category', {}).items()):
        print(f"    - {cat or 'None':15} {count:,}")

    # Show entities connected through a shared anchor
    spreader = SpreadingActivation(store)

    # Find an entity with anchors
    results = store.search("Physics", limit=1)
    if results:
        entity = results[0]
        print(f"\nEntities connected to '{entity.entity.label}' through shared anchors:")

        neighbors = spreader.get_anchor_neighbors(entity.entity.id, limit=10)
        for neighbor, anchor_label, activation in neighbors[:5]:
            print(f"  {neighbor.entity.label:30} via anchor '{anchor_label}' (act={activation:.3f})")


def demo():
    """Demo with multiple interesting entities."""
    print("=" * 70)
    print("SPARSE WIKI GROUNDING - MULTI-DIMENSIONAL NAVIGATION")
    print("=" * 70)
    print("""
This demo shows how entities are grounded across multiple hierarchical
dimensions using signed vectors and cross-node anchor connectivity.

Key Features:
- SIGNED VECTORS: Each entity has a position relative to the zero state
  (+depth = more specific, -depth = more abstract)

- ZERO STATES (Dimension Roots):
  * SPATIAL:    Earth
  * TEMPORAL:   Present
  * TAXONOMIC:  Thing
  * SCALE:      Regional
  * DOMAIN:     Knowledge

- ANCHOR LAYER: Cross-node semantic connectivity through dictionary-encoded
  labels, enabling spreading activation beyond direct entity links.

- HIERARCHICAL OPERATIONS: is_descendant_of, shared_ancestor, hierarchical_distance
""")

    store = EntityStore("data/entities_demo.db")

    # Show database stats
    print(f"Database: {store.count():,} entities")
    print(f"Anchor layer: {store.count_anchors():,} anchors, {store.count_anchor_links():,} links")
    print()

    # Explore key entities
    entities = ["Albert Einstein", "Marie Curie", "Paris"]

    for entity_name in entities:
        explore_entity(entity_name, store)
        print()

    # Show hierarchical comparison
    show_hierarchical_comparison(store)

    # Show anchor connectivity
    show_anchor_connectivity(store)


if __name__ == "__main__":
    store = EntityStore("data/entities_demo.db")
    if len(sys.argv) > 1:
        explore_entity(" ".join(sys.argv[1:]), store)
    else:
        demo()
