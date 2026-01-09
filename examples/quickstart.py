#!/usr/bin/env python3
"""
Quickstart: Grounded Claim Verification in 10 Lines

Demonstrates sparse knowledge grounding for factual claim verification -
a key technique for detecting LLM hallucinations and improving AI safety.

Usage:
    PYTHONPATH=src python examples/quickstart.py
"""

import time
from wiki_grounding import EntityStore, ClaimVerifier, VerificationStatus

# Load entity database (~1K entities, <2MB)
store = EntityStore("data/entities_demo.db")
verifier = ClaimVerifier(store)

# Test claims: mix of true, false, and ambiguous
claims = [
    "Paris is in France",                              # True (SPATIAL hierarchy)
    "Albert Einstein created the theory of relativity", # True (relation)
    "Marie Curie discovered radioactivity",            # True (relation)
    "The Eiffel Tower is in London",                   # False! (contradiction)
    "Shakespeare wrote Hamlet",                        # True (relation)
    "Thomas Edison invented the telephone",            # False! (Bell did)
]

print("=" * 65)
print("SPARSE WIKI GROUNDING - Claim Verification Demo")
print("=" * 65)
entity_count = store.count()
relation_count = store.conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
print(f"Database: {entity_count:,} entities, {relation_count:,} relations")
print()

# Verify with timing
total_ms = 0
for claim in claims:
    start = time.perf_counter()
    result = verifier.verify(claim)
    elapsed_ms = (time.perf_counter() - start) * 1000
    total_ms += elapsed_ms

    # Status indicator
    status_map = {
        VerificationStatus.SUPPORTED: "\033[92m[VERIFIED]\033[0m",
        VerificationStatus.CONTRADICTED: "\033[91m[FALSE]\033[0m",
        VerificationStatus.UNVERIFIABLE: "\033[93m[UNKNOWN]\033[0m",
        VerificationStatus.PLAUSIBLE: "\033[94m[PLAUSIBLE]\033[0m",
    }

    print(f"{status_map[result.status]:20} {claim}")
    if result.status == VerificationStatus.CONTRADICTED and result.correction:
        print(f"                     -> {result.correction}")
    print(f"                     [{elapsed_ms:.1f}ms, confidence={result.confidence:.2f}]")
    print()

print("-" * 65)
print(f"Verified {len(claims)} claims in {total_ms:.1f}ms ({total_ms/len(claims):.1f}ms avg)")
print()
print("Key for LLM Safety: This grounding approach enables:")
print("  - Real-time factual verification of generated text")
print("  - Detection of geographic/relational hallucinations")
print("  - Transparent corrections with evidence paths")
