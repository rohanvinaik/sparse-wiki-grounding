# Sparse Wikipedia World Ontology

**Interpretable, navigable knowledge grounding for AI systems.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

This project implements a **sparse navigational scaffold** for grounding entities in multi-dimensional semantic space. Unlike dense embedding spaces that are opaque and difficult to interpret, this system positions entities along explicit hierarchical dimensions that can be traversed, compared, and reasoned about.

**Key Insight**: Rather than treating world knowledge as a black-box embedding, we structure it as a collection of **signed vector positions** across five interpretable dimensions, connected by a **dictionary-encoded anchor layer** for cross-node semantic connectivity.

---

## Architecture

### Multi-Dimensional Faceted Classification

Inspired by Ranganathan's Colon Classification, each entity is positioned in 5 orthogonal dimension trees:

| Dimension | Zero State | What It Captures |
|-----------|------------|------------------|
| **SPATIAL** | Earth | Geographic hierarchy (Earth > Europe > France > Paris) |
| **TEMPORAL** | Present | Time position relative to now |
| **TAXONOMIC** | Thing | Type hierarchy (Thing > Person > Scientist > Physicist) |
| **SCALE** | Regional | Geographic scope (Local > National > International) |
| **DOMAIN** | Knowledge | Knowledge field (Knowledge > Science > Physics) |

### Signed Vectors from Zero State

Each entity's position in a dimension is represented as a **signed distance from the zero state**:

```
Position = (sign, depth, path_nodes, zero_state)

Examples:
  Paris (SPATIAL):    +3:SPATIAL/Earth/Europe/France/Paris
  Europe (SPATIAL):   +1:SPATIAL/Earth/Europe
  Earth (SPATIAL):    0:SPATIAL/Earth  (at zero state)

  sign = +1: More specific than zero
  sign = -1: More abstract than zero
  sign = 0:  At zero state
```

This enables **directional navigation**: you can walk from any entity toward the zero state to generalize, or away from it to specialize.

### Cross-Node Anchor Layer

Beyond direct entity links, entities are connected through a **dictionary-encoded anchor layer**:

```
anchor_dictionary: {anchor_id, label, category}
entity_anchors:    {entity_id, anchor_id, weight}
```

**Anchor categories** (semantic banks):
- **SCOPE**: General topical associations
- **HISTORY**: Historical/temporal connections
- **KNOWN_FOR**: Notable achievements/attributes
- **GEOGRAPHY**: Geographic associations

This layer enables **spreading activation across semantically related entities** even when they don't have direct links.

---

## Quick Start

```bash
git clone https://github.com/rohan-vinaik/sparse-wiki-grounding
cd sparse-wiki-grounding
pip install -e .

# Build the demo database (requires source data)
python scripts/build_demo_db.py

# Run demos
PYTHONPATH=src python examples/quickstart.py
PYTHONPATH=src python examples/explore_entity.py "Albert Einstein"
```

---

## Demo Output

```
======================================================================
SPARSE WIKI GROUNDING - World Ontology Demo
======================================================================

Database Statistics:
  Entities:          10,082
  Entity links:      38,941
  Anchor dictionary: 15,433
  Anchor links:      202,052 (cross-node connectivity)

Zero States (Dimension Roots):
  DOMAIN     -> Knowledge
  SCALE      -> Regional
  SPATIAL    -> Earth
  TAXONOMIC  -> Thing
  TEMPORAL   -> Present

======================================================================
ENTITY EXPLORATION
======================================================================

Albert Einstein (Q_Albert_Einstein)
----------------------------------------
  Dimensions:
    TEMPORAL   [+0:0] Present
    TAXONOMIC  [+0:0] Thing
    SCALE      [+1:1] Regional > National
    DOMAIN     [+0:0] Knowledge
  EPA: E=+0 P=+0 A=+0
  Anchors:
    KNOWN_FOR: Calculus
    SCOPE: Matter, Philosophy, Physics, ...

======================================================================
SPREADING ACTIVATION (with anchor layer)
======================================================================

Spreading from: Albert Einstein
Activated 50 entities in 80.3ms

Top activated entities:
  History of philosophy   (act=0.648) via anchor:Philosophy
  Gas                     (act=0.600) via anchor:Matter
  Game theory             (act=0.420) via anchor:Philosophy
```

---

## Key Operations

### Hierarchical Navigation

```python
from wiki_grounding import EntityStore
from wiki_grounding.entity import GroundingDimension

store = EntityStore("data/entities_demo.db")
paris = store.search("Paris")[0]

# Navigate from Paris toward zero state (Earth)
path = paris.navigate_toward_zero(GroundingDimension.SPATIAL)
# ["Paris", "France", "Europe", "Earth"]

# Check hierarchical relationship
paris.is_descendant_of("Europe", GroundingDimension.SPATIAL)  # True
paris.is_descendant_of("Asia", GroundingDimension.SPATIAL)    # False

# Find common ancestor
london = store.search("London")[0]
ancestor = paris.shared_ancestor(london, GroundingDimension.SPATIAL)
# "Europe"

# Compute hierarchical distance
distance = paris.hierarchical_distance(london, GroundingDimension.SPATIAL)
```

### Anchor-Based Spreading Activation

```python
from wiki_grounding import SpreadingActivation

spreader = SpreadingActivation(store)

# Spread through both entity links AND anchor layer
results = spreader.spread("Q_Physics", use_anchors=True)

for result in results[:5]:
    print(f"{result.entity.entity.label}: {result.activation:.3f}")
    # Bank-specific activations
    print(f"  Banks: {result.bank_activations}")

# Find entities connected through shared anchors
neighbors = spreader.get_anchor_neighbors("Q_Physics", category="SCOPE")
```

### Signed Position Vector

```python
# Get entity's position across all dimensions
pos_vector = entity.position_vector()
# {"SPATIAL": 3, "TEMPORAL": 0, "TAXONOMIC": 2, "SCALE": 1, "DOMAIN": 0}
```

---

## Database Schema

```sql
-- Core entity table
CREATE TABLE entities (
    id TEXT PRIMARY KEY,        -- Wikidata Q-number
    label TEXT NOT NULL,
    description TEXT,
    vital_level INTEGER,        -- 1-5 importance level
    pagerank REAL
);

-- Hierarchical dimension positions
CREATE TABLE dimension_positions (
    entity_id TEXT NOT NULL,
    dimension TEXT NOT NULL,    -- SPATIAL, TEMPORAL, TAXONOMIC, SCALE, DOMAIN
    path_sign INTEGER NOT NULL, -- +1 (specific), -1 (abstract), 0 (at zero)
    path_depth INTEGER NOT NULL,
    path_nodes TEXT NOT NULL,   -- JSON array
    zero_state TEXT NOT NULL
);

-- Zero states (dimension roots)
CREATE TABLE zero_states (
    dimension TEXT PRIMARY KEY,
    zero_node TEXT NOT NULL     -- "Earth", "Present", "Thing", etc.
);

-- Cross-node anchor layer
CREATE TABLE anchor_dictionary (
    anchor_id INTEGER PRIMARY KEY,
    label TEXT UNIQUE NOT NULL,
    category TEXT               -- SCOPE, HISTORY, KNOWN_FOR, GEOGRAPHY
);

CREATE TABLE entity_anchors (
    entity_id TEXT NOT NULL,
    anchor_id INTEGER NOT NULL,
    weight REAL DEFAULT 1.0
);

-- EPA semantic differential
CREATE TABLE epa_values (
    entity_id TEXT PRIMARY KEY,
    evaluation INTEGER,         -- -1/0/+1
    potency INTEGER,
    activity INTEGER,
    confidence REAL
);
```

---

## Relevance to AI Safety

### Interpretable Grounding

Unlike black-box embeddings, this system provides **transparent paths** for any grounding decision:

- **Why is Paris in France?** Path: `Earth > Europe > France > Paris`
- **How is Einstein related to Physics?** Anchor: `SCOPE:Physics` with weight 0.9

### OOV (Out-of-Vocabulary) Handling

When encountering unknown terms, the hierarchical structure enables **graceful degradation**:

1. Try exact match in entity store
2. Fall back to anchor-based semantic similarity
3. Navigate up dimension trees to find related concepts

### Verifiable Claims

The hierarchical structure enables systematic claim verification:

```python
# "The Eiffel Tower is in London" -> Check SPATIAL path
# Path shows: Earth > Europe > France > Paris > Eiffel Tower
# "London" not in path -> CONTRADICTED
```

### Cross-Node Semantic Discovery

The anchor layer enables discovery of **implicit relationships**:

- Entities sharing anchors are semantically related
- Anchor categories provide typed semantic connections
- Spreading activation reveals contextually relevant entities

---

## Theoretical Foundations

This work draws on several established frameworks:

- **Collins & Loftus (1975)**: Spreading activation theory
- **Ranganathan's Colon Classification**: Multi-dimensional faceted classification
- **Osgood's Semantic Differential (1957)**: EPA (Evaluation-Potency-Activity) dimensions
- **Wierzbicka's Natural Semantic Metalanguage**: Semantic primitives and decomposition

---

## Data Coverage (Demo Database)

| Metric | Value |
|--------|-------|
| Entities | 10,082 |
| Dimension Positions | 40,335 |
| Entity Links | 38,941 |
| Anchor Dictionary | 15,433 |
| Entity-Anchor Links | 202,052 |
| Zero States | 5 |

---

## License

MIT

---

## References

- Collins, A. M., & Loftus, E. F. (1975). A spreading-activation theory of semantic processing. *Psychological Review*, 82(6), 407-428.
- Osgood, C. E., Suci, G. J., & Tannenbaum, P. H. (1957). *The Measurement of Meaning*.
- Ranganathan, S. R. (1962). *Elements of Library Classification*.
- Wierzbicka, A. (1996). *Semantics: Primes and Universals*.
