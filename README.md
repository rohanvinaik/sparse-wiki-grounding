# sparse-wiki-grounding

**Interpretable entity grounding for claim verification.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Why This Matters for AI Safety

LLMs frequently hallucinate facts about entities—claiming people hold positions
they don't, attributing false locations to events, or inventing relationships.
Current detection methods rely on:

- **Black-box embeddings** (uninterpretable)
- **RAG retrieval** (keyword-dependent, misses semantic relations)
- **Confidence calibration** (unreliable for factual claims)

This framework offers a **complementary approach**: project entities into a
semantically-grounded coordinate space with known dimensions, enabling:

| Capability | Description |
|------------|-------------|
| **Entity Lookup** | O(1) retrieval of semantic coordinates for 250K entities |
| **EPA Profiling** | Evaluation (+/-), Potency (strong/weak), Activity (active/passive) |
| **Spreading Activation** | Find semantically related entities through graph traversal |
| **Claim Verification** | Check if assertions match stored relations |

---

## Quick Demo

```python
from wiki_grounding import EntityStore, ClaimVerifier

store = EntityStore("data/entities_demo.db")
verifier = ClaimVerifier(store)

# Verify claims
result = verifier.verify("Albert Einstein developed the theory of relativity")
print(result)  # [✓] ... (0.90)

result = verifier.verify("Albert Einstein invented the lightbulb")
print(result)  # [✗] ... Correction: The lightbulb was invented by Thomas Edison
```

---

## Installation

```bash
pip install sparse-wiki-grounding
```

Or from source:

```bash
git clone https://github.com/rohan-vinaik/sparse-wiki-grounding
cd sparse-wiki-grounding
pip install -e .
```

---

## Entity Coordinates

### Multi-Dimensional Positions

Each entity has positions in 5 hierarchical dimension trees:

| Dimension | Zero State | Example (Paris) |
|-----------|------------|-----------------|
| **SPATIAL** | Earth | +3: Earth/Europe/France/Paris |
| **TEMPORAL** | Present | 0: Present |
| **TAXONOMIC** | Thing | +2: Thing/Place/City |
| **SCALE** | Regional | +1: Regional/National |
| **DOMAIN** | Knowledge | +2: Knowledge/Geography/Cities |

### EPA Values

Entities also have EPA (Evaluation-Potency-Activity) coordinates from Osgood's
semantic differential:

| Entity | E (Evaluation) | P (Potency) | A (Activity) |
|--------|----------------|-------------|--------------|
| Hero | +1 (good) | +1 (strong) | +1 (active) |
| Villain | -1 (bad) | +1 (strong) | +1 (active) |
| Victim | +1 (good) | -1 (weak) | -1 (passive) |

---

## Spreading Activation

Find semantically related entities through graph traversal:

```python
from wiki_grounding import EntityStore, SpreadingActivation

store = EntityStore("data/entities_demo.db")
spreader = SpreadingActivation(store)

# Spread from Marie Curie
results = spreader.spread("Q7186")  # Marie Curie's Wikidata ID

for r in results[:5]:
    print(f"{r.entity.entity.label}: {r.activation:.3f}")
    # Pierre Curie: 0.850
    # Radioactivity: 0.720
    # Nobel Prize in Physics: 0.680
    # ...
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Entity Store                           │
├──────────────┬──────────────┬──────────────┬───────────────┤
│  Wikidata ID │  Positions   │  EPA Vector  │  Properties   │
│    Q937      │ SPATIAL:+3   │ [+1,+1,+1]   │ occupation:   │
│              │ TAXONOMIC:+2 │              │  physicist    │
└──────────────┴──────────────┴──────────────┴───────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Claim Verifier                           │
│  Input: "Einstein invented the lightbulb"                   │
│                                                             │
│  1. Parse → entity: Einstein, relation: invented, target: X │
│  2. Lookup → Einstein.created = {relativity, E=mc²...}      │
│  3. Spread → lightbulb → Edison (activation 0.92)           │
│  4. Result → CONTRADICTED (lightbulb attributed to Edison)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Coverage

| Metric | Demo DB | Full DB |
|--------|---------|---------|
| Entities | ~5,000 | 250,000 |
| Dimension Positions | ~20,000 | 1,000,000 |
| Entity Links | ~10,000 | 500,000 |
| File Size | ~15 MB | ~500 MB |

---

## Related Work

- **FEVER** - Fact verification benchmark
- **Wikidata embeddings** - Black-box entity representations
- **Knowledge graphs** - Structured relation storage

This project differs by providing **interpretable coordinates** rather than
opaque embeddings, enabling transparent verification decisions.

---

## References

- Osgood, C. E., Suci, G. J., & Tannenbaum, P. H. (1957). *The Measurement of Meaning*
- Collins, A. M., & Loftus, E. F. (1975). A spreading-activation theory of semantic processing
- Wierzbicka, A. (1996). *Semantics: Primes and Universals*

---

## License

MIT
