# Sparse Wiki Grounding

When an LLM says "Einstein invented the telephone," can you explain *why* that's wrong and *who* actually did?

This system provides interpretable knowledge grounding with explicit reasoning chains. Every association has a type (SCOPE, HISTORY, KNOWN_FOR) and a weight - auditable and correctable.

---

## The Problem

LLMs encode world knowledge in opaque parameters. When they hallucinate, we observe the output is wrong but can't explain why.

| Approach | Detects Errors | Explains Why | Provides Correction |
|----------|---------------|--------------|---------------------|
| LLM Confidence | Unreliable | No | No |
| Embedding Similarity | Sometimes | No | No |
| RAG Retrieval | Sometimes | Partial | Sometimes |
| **This System** | **Yes** | **Yes** | **Yes** |

---

## How It Works

```python
from wiki_grounding import EntityStore, SpreadingActivation

store = EntityStore("data/entities_demo.db")
einstein = store.search("Albert Einstein")[0]
anchors = store.get_entity_anchors(einstein.entity.id)

for anchor_id, label, category, weight in anchors[:5]:
    print(f"  {category}: {label} (weight: {weight:.2f})")

# Output:
#   SCOPE: Physics (1.00)
#   SCOPE: Philosophy (1.00)
#   SCOPE: Quantum mechanics (1.00)
#   KNOWN_FOR: Relativity (0.70)
```

Einstein → Physics is an explicit SCOPE anchor with weight 1.0. No "telephone" anchor exists.

### Spreading Activation

```python
spreader = SpreadingActivation(store)
activated = spreader.spread(einstein.entity.id, use_anchors=True)

for result in activated[:3]:
    print(f"  {result.entity.entity.label}: {result.activation:.3f}")

# History of philosophy: 0.648 via anchor:Philosophy
# Game theory: 0.420 via anchor:Philosophy
```

The activation path is visible. Compare to embeddings where `cosine_sim(Einstein, Philosophy) = 0.7` tells you nothing about *why*.

---

## Data Coverage

| Table | Count |
|-------|-------|
| Entities | 10,082 |
| Entity Links | 38,941 |
| Anchor Dictionary | 15,433 |
| Entity-Anchor Links | 202,052 |

Wikipedia vital articles (levels 1-4) with typed semantic connections.

---

## Performance

| Operation | Latency |
|-----------|---------|
| Links only | ~20ms |
| With anchor layer | ~76ms |

The anchor layer adds latency but provides typed connectivity - you know *why* entities are connected.

---

## Quick Start

```bash
git clone https://github.com/rohan-vinaik/sparse-wiki-grounding
cd sparse-wiki-grounding
pip install -e .

PYTHONPATH=src python examples/explore_entity.py "Marie Curie"
```

---

## Failure Mode Detection

When an LLM claims "Einstein invented the telephone":

1. Look up Einstein's anchors → no "telephone" or "invention" anchor
2. Look up telephone's anchors → find "Alexander Graham Bell"
3. Provide correction with evidence

The explanation is the data structure itself.

---

## Foundation

- Collins & Loftus (1975): Spreading activation in semantic memory
- Ranganathan: Multi-dimensional faceted classification
- Wierzbicka: Semantic primitives and decomposition

---

MIT License
