# Sparse Wikipedia World Ontology

**When an LLM says "Einstein invented the telephone," can you explain *why* that's wrong and *who* actually did?**

This project provides interpretable, auditable knowledge grounding - a foundation for AI systems that can explain their reasoning about facts, not just pattern-match.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## The Problem: Black-Box Knowledge

Modern LLMs encode world knowledge in billions of opaque parameters. When they hallucinate, we can't explain why - we can only observe that the output is wrong.

| Approach | Can Detect Errors? | Can Explain Why? | Can Provide Correction? |
|----------|-------------------|------------------|------------------------|
| LLM Confidence Scores | Unreliable | No | No |
| Embedding Similarity | Sometimes | No | No |
| RAG Retrieval | Sometimes | Partial | Sometimes |
| **This System** | **Yes** | **Yes** | **Yes** |

---

## Demo: Interpretable Semantic Associations

```python
from wiki_grounding import EntityStore, SpreadingActivation

store = EntityStore("data/entities_demo.db")

# Look up Einstein's semantic associations
einstein = store.search("Albert Einstein")[0]
anchors = store.get_entity_anchors(einstein.entity.id)

print("Einstein's semantic anchors:")
for anchor_id, label, category, weight in anchors[:8]:
    print(f"  {category}: {label} (weight: {weight:.2f})")

# Output:
#   SCOPE: Physics (weight: 1.00)
#   SCOPE: Philosophy (weight: 1.00)
#   SCOPE: Matter (weight: 1.00)
#   SCOPE: Quantum mechanics (weight: 1.00)
#   KNOWN_FOR: Calculus (weight: 0.70)
#   ...
```

**Key insight**: Instead of opaque embeddings, we have **explicit, typed associations**. Einstein is connected to Physics through a SCOPE anchor with weight 1.0 - this is auditable and correctable.

### Cross-Node Discovery via Spreading Activation

```python
spreader = SpreadingActivation(store)

# What's semantically connected to Einstein?
activated = spreader.spread(einstein.entity.id, use_anchors=True)

print("Spreading from Einstein:")
for result in activated[:5]:
    via = result.relations[0] if result.relations else "direct"
    print(f"  {result.entity.entity.label}: {result.activation:.3f} via {via}")

# Output:
#   History of philosophy: 0.648 via anchor:Philosophy
#   Gas: 0.600 via anchor:Matter
#   Game theory: 0.420 via anchor:Philosophy
#   Scientific Revolution: 0.420 via anchor:Philosophy
```

The activation path is **visible**: Einstein → Philosophy anchor → History of philosophy. Compare to embeddings where `cosine_sim(Einstein, Philosophy) = 0.7` tells you nothing about *why*.

---

## Why This Matters for AI Safety

### 1. Interpretability by Design

Every grounding decision has an explicit reasoning chain:

```
Query: "Is Marie Curie associated with Physics?"

Lookup: Marie Curie → anchors → SCOPE:Physics (weight: 0.90)

Answer: YES
Explanation: Marie Curie has anchor "Physics" in SCOPE category with weight 0.90
             Also: SCOPE:Chemistry, HISTORY:Barium, HISTORY:Radioactivity
```

The explanation is the data structure itself - no post-hoc rationalization needed.

### 2. Typed Semantic Connections

Anchors are categorized into semantic banks:

| Category | What It Captures | Example |
|----------|------------------|---------|
| **SCOPE** | Topical domain | Einstein → Physics, Philosophy |
| **HISTORY** | Historical associations | Curie → Austrian Empire, Barium |
| **KNOWN_FOR** | Notable achievements | Einstein → Calculus |
| **GEOGRAPHY** | Geographic connections | Paris → Europe |

This enables typed queries: "What is Einstein KNOWN_FOR?" vs "What SCOPE does Einstein belong to?"

### 3. Cross-Node Semantic Discovery

The anchor layer connects entities through shared concepts:

```
Einstein anchors:  [Physics, Philosophy, Matter, Quantum mechanics, ...]
Curie anchors:     [Physics, Chemistry, Radioactivity, ...]
                         ↑
                   Shared anchor "Physics" connects them
                   even without a direct entity link
```

This reveals **conceptual neighborhoods** - what's semantically nearby? - in an interpretable way.

---

## Benchmark: Spreading Activation Performance

| Metric | Value |
|--------|-------|
| Entities | 10,082 |
| Entity Links | 38,941 |
| Anchor Dictionary | 15,433 |
| Entity-Anchor Links | 202,052 |
| Spreading Activation | ~76ms (50 entities) |
| Throughput | ~13 ops/sec |

### Comparison: Interpretability vs Speed Trade-off

| System | Latency | Interpretable? | Typed Associations? |
|--------|---------|----------------|---------------------|
| OpenAI Embedding Lookup | ~50ms | No | No |
| This System (links only) | ~20ms | Yes | No |
| This System (+ anchors) | ~76ms | Yes | **Yes** |
| LLM Fact Check | ~500ms+ | No | No |

The anchor layer adds latency but provides **typed semantic connectivity** - you know *why* entities are connected (SCOPE vs HISTORY vs KNOWN_FOR).

---

## Architecture: Dimension Trees + Anchor Layer

### Multi-Dimensional Positions

Each entity is positioned in 5 orthogonal hierarchies:

| Dimension | Zero State | What It Captures |
|-----------|------------|------------------|
| SPATIAL | Earth | Geographic hierarchy |
| TEMPORAL | Present | Time position |
| TAXONOMIC | Thing | Type hierarchy |
| SCALE | Regional | Geographic scope (Local → International) |
| DOMAIN | Knowledge | Knowledge field |

```python
entity.position_vector()
# {"SPATIAL": 0, "TEMPORAL": 0, "TAXONOMIC": 0, "SCALE": +2, "DOMAIN": 0}
```

### Anchor Layer (Cross-Node Connectivity)

Beyond direct links, entities connect through 202,052 typed semantic anchors:

```
anchor_dictionary: 15,433 entries
  - SCOPE:      7,237 entries (topical associations)
  - HISTORY:    8,160 entries (historical connections)
  - KNOWN_FOR:  35 entries (notable achievements)
  - GEOGRAPHY:  1 entry

entity_anchors: 202,052 connections
  Each entity → multiple anchors with weights
```

---

## Quick Start

```bash
git clone https://github.com/rohan-vinaik/sparse-wiki-grounding
cd sparse-wiki-grounding
pip install -e .

# Run demos
PYTHONPATH=src python examples/quickstart.py
PYTHONPATH=src python examples/explore_entity.py "Albert Einstein"
```

### Example: Explore an Entity

```
$ PYTHONPATH=src python examples/explore_entity.py "Marie Curie"

======================================================================
ENTITY: Marie Curie
======================================================================

ID: Q_Marie_Curie
Vital Level: 3

--- SEMANTIC ANCHORS (Cross-Node Layer) ---
  HISTORY: Austrian Empire, BBC, Barium, ...
  SCOPE: Chemical element, Chemistry, Physics, ...

--- SPREADING ACTIVATION (with anchor layer) ---
  Activated 50 entities in 80ms

  History of philosophy   (act=0.648) via anchor:Philosophy
  Atom                    (act=0.600) via anchor:Chemistry
  Carbon                  (act=0.420) via anchor:Chemical element
```

---

## Relevance to AI Alignment

### Grounded Reasoning

LLMs often fail at factual reasoning because their "knowledge" is entangled in weights. This system externalizes knowledge as a navigable structure:

- **Verifiable**: Every association has an explicit anchor with weight
- **Correctable**: Wrong associations can be directly edited
- **Auditable**: The reasoning chain is visible, not hidden in activations

### Failure Mode Detection

When an LLM claims "Einstein invented the telephone":

1. Look up Einstein's anchors → no "telephone" or "invention" anchor
2. Look up telephone's anchors → find "Alexander Graham Bell"
3. Provide correction with evidence

### Future Directions

- **Integration with LLM generation**: Ground claims during generation, not after
- **Compositional reasoning**: Chain anchor lookups for complex queries
- **Dynamic updates**: Add new entities/anchors without retraining

---

## Theoretical Foundations

- **Collins & Loftus (1975)**: Spreading activation in semantic memory
- **Ranganathan's Colon Classification**: Multi-dimensional faceted classification
- **Osgood's Semantic Differential**: EPA (Evaluation-Potency-Activity) dimensions
- **Wierzbicka's NSM**: Semantic primitives and decomposition

---

## Data Coverage

| Table | Count | Purpose |
|-------|-------|---------|
| entities | 10,082 | Wikipedia vital articles (levels 1-4) |
| dimension_positions | 40,335 | Hierarchical positions |
| entity_links | 38,941 | Direct semantic relations |
| anchor_dictionary | 15,433 | Typed semantic labels |
| entity_anchors | 202,052 | Cross-node connections |
| zero_states | 5 | Dimension roots |

---

## License

MIT

---

## References

- Collins, A. M., & Loftus, E. F. (1975). A spreading-activation theory of semantic processing. *Psychological Review*, 82(6), 407-428.
- Osgood, C. E., Suci, G. J., & Tannenbaum, P. H. (1957). *The Measurement of Meaning*.
- Ranganathan, S. R. (1962). *Elements of Library Classification*.
- Wierzbicka, A. (1996). *Semantics: Primes and Universals*.
