#!/usr/bin/env python3
"""
Quickstart: Sparse Wikipedia World Ontology

Demonstrates the key features of the grounding system:
1. Multi-dimensional hierarchical positions (SPATIAL, TEMPORAL, TAXONOMIC, SCALE, DOMAIN)
2. Cross-node anchor connectivity (dictionary-encoded semantic links)
3. Spreading activation through both entity links and anchor layer
4. Signed vector navigation (distance from zero state)

Usage:
    PYTHONPATH=src python examples/quickstart.py
"""

import time
from wiki_grounding import EntityStore, SpreadingActivation
from wiki_grounding.entity import GroundingDimension

# Load entity database
store = EntityStore("data/entities_demo.db")
spreader = SpreadingActivation(store)

print("=" * 70)
print("SPARSE WIKI GROUNDING - World Ontology Demo")
print("=" * 70)

# Database stats
entity_count = store.count()
relation_count = store.conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
anchor_count = store.count_anchors()
anchor_links = store.count_anchor_links()

print(f"\nDatabase Statistics:")
print(f"  Entities:          {entity_count:,}")
print(f"  Entity links:      {relation_count:,}")
print(f"  Anchor dictionary: {anchor_count:,}")
print(f"  Anchor links:      {anchor_links:,} (cross-node connectivity)")

# Zero states
print(f"\nZero States (Dimension Roots):")
zero_states = store.get_all_zero_states()
for dim, zero in sorted(zero_states.items()):
    print(f"  {dim:10} -> {zero}")

# Demo: Entity exploration
print("\n" + "=" * 70)
print("ENTITY EXPLORATION")
print("=" * 70)

entities = ["Albert Einstein", "Marie Curie", "Physics"]
for name in entities:
    results = store.search(name, limit=1)
    if not results:
        print(f"\n{name}: Not found")
        continue

    profile = results[0]
    print(f"\n{profile.entity.label} ({profile.entity.id})")
    print("-" * 40)

    # Dimension positions
    print("  Dimensions:")
    for dim in GroundingDimension:
        pos = profile.get_position(dim)
        if pos:
            print(f"    {dim.value:10} [{pos.path_sign:+d}:{pos.path_depth}] {' > '.join(pos.path_nodes)}")

    # EPA values
    epa = profile.epa
    print(f"  EPA: E={epa.evaluation.value:+d} P={epa.potency.value:+d} A={epa.activity.value:+d}")

    # Anchor categories
    anchors = store.get_entity_anchors(profile.entity.id)
    if anchors:
        by_cat = {}
        for _, label, cat, _ in anchors[:20]:
            by_cat.setdefault(cat or "OTHER", []).append(label)
        print("  Anchors:")
        for cat, labels in sorted(by_cat.items())[:3]:
            sample = ", ".join(labels[:3])
            if len(labels) > 3:
                sample += f", ... (+{len(labels)-3} more)"
            print(f"    {cat}: {sample}")

# Demo: Spreading activation
print("\n" + "=" * 70)
print("SPREADING ACTIVATION (with anchor layer)")
print("=" * 70)

results = store.search("Albert Einstein", limit=1)
if results:
    einstein = results[0]

    print(f"\nSpreading from: {einstein.entity.label}")
    start = time.perf_counter()
    activated = spreader.spread(einstein.entity.id, use_anchors=True)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"Activated {len(activated)} entities in {elapsed_ms:.1f}ms")
    print("\nTop 10 activated entities:")
    for result in activated[:10]:
        via = result.relations[0] if result.relations else "direct"
        if via.startswith("anchor:"):
            via = via[:30] + "..." if len(via) > 30 else via
        print(f"  {result.entity.entity.label:35} (act={result.activation:.3f}) via {via}")

# Demo: Anchor connectivity
print("\n" + "=" * 70)
print("ANCHOR-BASED CONNECTIVITY")
print("=" * 70)

results = store.search("Physics", limit=1)
if results:
    physics = results[0]
    print(f"\nEntities connected to '{physics.entity.label}' through shared anchors:")

    neighbors = spreader.get_anchor_neighbors(physics.entity.id, limit=8)
    for neighbor, anchor_label, activation in neighbors:
        print(f"  {neighbor.entity.label:35} via '{anchor_label}' (act={activation:.3f})")

# Benchmark
print("\n" + "=" * 70)
print("PERFORMANCE BENCHMARK")
print("=" * 70)

n_iterations = 100
start = time.perf_counter()
for _ in range(n_iterations):
    spreader.spread("Q_Albert_Einstein", use_anchors=True)
elapsed = time.perf_counter() - start

print(f"\nSpread activation (with anchors): {n_iterations} iterations")
print(f"  Total time:    {elapsed*1000:.1f}ms")
print(f"  Per operation: {elapsed*1000/n_iterations:.2f}ms")
print(f"  Throughput:    {n_iterations/elapsed:.0f} ops/sec")

print("\n" + "=" * 70)
print("Key for AI Safety Research:")
print("  - Multi-dimensional grounding for entity disambiguation")
print("  - Cross-node connectivity for semantic relationship discovery")
print("  - Transparent hierarchical paths for interpretable decisions")
print("  - Real-time performance for runtime verification")
print("=" * 70)
