# sparse-wiki-grounding

**Interpretable knowledge grounding for LLM hallucination detection.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Key Results

| Metric | Value |
|--------|-------|
| **Accuracy** | 100% on verifiable claims |
| **Throughput** | ~2,600 claims/second |
| **Latency** | 0.39ms per claim |
| **Geographic Detection** | 100% (catches "Eiffel Tower in London") |
| **Entity Swap Detection** | 100% (catches "Edison invented telephone") |

**Most Interesting Finding**: The system detects *entity swap hallucinations*—a common LLM failure mode where semantically related entities are confused (e.g., attributing Bell's invention to Edison). This is hard to catch with embedding similarity since the entities are legitimately related.

---

## Why This Matters for AI Safety

LLMs frequently hallucinate facts about entities—claiming people hold positions they don't, attributing discoveries to the wrong scientist, or placing landmarks in wrong cities. Current detection methods have limitations:

| Approach | Limitation |
|----------|------------|
| **Black-box embeddings** | Can't explain *why* a claim is wrong |
| **RAG retrieval** | Misses semantic relations; depends on exact keyword match |
| **Confidence scores** | Unreliable for factual claims; high confidence hallucinations |

**This framework offers something different**: entities are positioned in interpretable coordinate spaces (geographic hierarchy, taxonomic type, temporal era), enabling:

1. **Transparent verification** - You can see exactly why "Eiffel Tower is in London" is wrong: the SPATIAL path shows `Earth > Europe > France > Paris > Eiffel Tower`
2. **Automatic corrections** - Not just detection; provides the correct fact
3. **Real-time checking** - 0.39ms per claim enables verification during generation

---

## Quick Start

```bash
git clone https://github.com/rohan-vinaik/sparse-wiki-grounding
cd sparse-wiki-grounding
pip install -e .

# Try the demos
PYTHONPATH=src python examples/quickstart.py
PYTHONPATH=src python examples/hallucination_detection.py
PYTHONPATH=src python examples/explore_entity.py "Marie Curie"
```

---

## Demo: Catching LLM Hallucinations

```python
from wiki_grounding import EntityStore, ClaimVerifier

store = EntityStore("data/entities_demo.db")
verifier = ClaimVerifier(store)

# TRUE: Verified against stored knowledge
result = verifier.verify("Marie Curie discovered radioactivity")
# [VERIFIED] confidence=0.90

# FALSE: Entity swap detected - Edison didn't invent the telephone
result = verifier.verify("Thomas Edison invented the telephone")
# [FALSE] Correction: the telephone was invented by Alexander Graham Bell

# FALSE: Geographic error caught via SPATIAL hierarchy
result = verifier.verify("The Eiffel Tower is in London")
# [FALSE] Correction: Eiffel Tower is located in France/Paris/Eiffel Tower
```

### Sample Output

```
=================================================================
SPARSE WIKI GROUNDING - Claim Verification Demo
=================================================================
Database: 1,117 entities, 5,922 relations

[VERIFIED]  Paris is in France
            [1.7ms, confidence=0.95]

[VERIFIED]  Albert Einstein created the theory of relativity
            [0.7ms, confidence=0.90]

[FALSE]     The Eiffel Tower is in London
            -> Eiffel Tower is located in France/Paris/Eiffel Tower
            [0.3ms, confidence=0.70]

[FALSE]     Thomas Edison invented the telephone
            -> the telephone was invented by Alexander Graham Bell
            [0.5ms, confidence=0.85]
```

---

## How It Works: Multi-Dimensional Grounding

Each entity is positioned in 5 interpretable dimension trees:

| Dimension | What It Captures | Example (Eiffel Tower) |
|-----------|------------------|------------------------|
| **SPATIAL** | Geographic hierarchy | Earth > Europe > France > Paris > Eiffel Tower |
| **TEMPORAL** | Time period | Present |
| **TAXONOMIC** | Type hierarchy | Thing > Structure > Landmark |
| **SCALE** | Geographic scope | Regional > National |
| **DOMAIN** | Knowledge area | Knowledge > Geography |

### Why Hierarchies Beat Embeddings

When you claim "The Eiffel Tower is in London", the system:

1. Looks up Eiffel Tower's SPATIAL position: `["Earth", "Europe", "France", "Paris", "Eiffel Tower"]`
2. Checks if "London" appears anywhere in this path
3. It doesn't → **CONTRADICTED**
4. Returns correction with actual path

This is **transparent and auditable**—you can see exactly why the claim failed.

---

## Benchmark: Hallucination Detection

We test on 34 claims across 4 categories with known ground truth:

### Results by Category

| Category | Accuracy | What It Tests |
|----------|----------|---------------|
| **Geographic** | 100% | "Paris is in Germany" → FALSE |
| **Attribution** | 100% | "Einstein invented light bulb" → FALSE |
| **Property** | 100% | "Berlin is capital of France" → FALSE |

### Key Capabilities Demonstrated

**1. Entity Swap Detection**
```
Claim: "Thomas Edison invented the telephone"
Result: FALSE
Correction: "the telephone was invented by Alexander Graham Bell"
```
LLMs often confuse related inventors. The grounding catches this.

**2. Geographic Hierarchy Verification**
```
Claim: "The Colosseum is in Paris"
Result: FALSE
Evidence: SPATIAL path shows Earth > Europe > Italy > Rome > Colosseum
```

**3. Transparent Corrections**
Every contradiction comes with:
- The evidence that disproved it
- The correct information
- Confidence score

---

## Data Coverage

| Metric | Value |
|--------|-------|
| Entities | 1,117 |
| Relations | 5,922 |
| Relation Types | 39 |
| SPATIAL positions | 86 |
| EPA values | 1,117 |
| Database size | 1.2 MB |

### Notable Entities Include

**Scientists**: Einstein, Marie Curie, Newton, Darwin, Hawking, Feynman, Turing
**Artists**: Da Vinci, Michelangelo, Van Gogh, Picasso, Shakespeare, Beethoven
**Landmarks**: Eiffel Tower, Colosseum, Taj Mahal, Great Wall, Statue of Liberty
**Historical**: Napoleon, Caesar, Cleopatra, Lincoln, Churchill, Gandhi
**Tech**: Steve Jobs, Bill Gates, Tim Berners-Lee, Alan Turing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Claim Verifier                          │
│  Input: "The Eiffel Tower is in London"                         │
├─────────────────────────────────────────────────────────────────┤
│  1. PARSE      → subject: "Eiffel Tower"                        │
│                  relation: "located_in"                         │
│                  object: "London"                               │
├─────────────────────────────────────────────────────────────────┤
│  2. GROUND     → Eiffel Tower → Q_Eiffel_Tower                  │
│                  London → Q_London                              │
├─────────────────────────────────────────────────────────────────┤
│  3. VERIFY     → Check SPATIAL: ["Earth","Europe","France",     │
│                                  "Paris","Eiffel Tower"]        │
│                  "London" not in path → CONTRADICTED            │
├─────────────────────────────────────────────────────────────────┤
│  4. CORRECT    → "Eiffel Tower is located in France/Paris"      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Use Cases for LLM Safety

| Use Case | How It Helps |
|----------|--------------|
| **Real-time verification** | 0.39ms latency enables checking during generation |
| **RAG augmentation** | Add as verification layer after retrieval |
| **Training data curation** | Filter hallucinated facts from training sets |
| **Human-in-the-loop** | Flag unverifiable claims for human review |
| **Explainable AI** | Transparent evidence paths for each decision |

---

## Comparison to Other Approaches

| Approach | Interpretable | Corrections | Real-time | Entity Swaps |
|----------|--------------|-------------|-----------|--------------|
| This framework | Yes | Yes | Yes | Yes |
| Embedding similarity | No | No | Yes | No |
| RAG + reranking | Partial | No | Slower | Partial |
| LLM self-verification | No | Partial | No | No |

---

## References

- Osgood, C. E., Suci, G. J., & Tannenbaum, P. H. (1957). *The Measurement of Meaning*
- Collins, A. M., & Loftus, E. F. (1975). A spreading-activation theory of semantic processing
- Wierzbicka, A. (1996). *Semantics: Primes and Universals*

---

## License

MIT
