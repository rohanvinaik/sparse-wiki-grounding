#!/usr/bin/env python3
"""
Spreading Activation Demo

Visualize how activation spreads through the entity graph.
"""

from wiki_grounding import EntityStore, SpreadingActivation, SpreadingConfig

def demo_spreading():
    store = EntityStore("data/entities_demo.db")

    # Configure spreading
    config = SpreadingConfig(
        decay=0.7,
        threshold=0.1,
        max_depth=3,
        max_results=20,
    )
    spreader = SpreadingActivation(store, config)

    # Start from Marie Curie
    # Search returns a list, take the first result
    sources = store.search_exact("Marie Curie")
    if not sources:
        print("Could not find Marie Curie in database")
        return
        
    source = sources[0]
    print(f"Starting from: {source.summary()}")
    print()

    results = spreader.spread(source.entity.id)

    print("Activated entities:")
    print("-" * 60)
    for i, result in enumerate(results, 1):
        path_str = " → ".join(result.path[-3:])  # Last 3 in path
        print(f"{i:2}. {result.entity.entity.label:<30} "
              f"(activation: {result.activation:.3f})")
        print(f"    Path: {path_str}")
        print(f"    Relations: {', '.join(result.relations[:3])}")
        print()


if __name__ == "__main__":
    demo_spreading()
