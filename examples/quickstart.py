#!/usr/bin/env python3
"""Quick start example - 10 lines to claim verification."""

from wiki_grounding import EntityStore, ClaimVerifier, VerificationStatus

# Load entity database
store = EntityStore("data/entities_demo.db")
verifier = ClaimVerifier(store)

# Verify some claims
claims = [
    "Paris is the capital of France",
    "Albert Einstein developed the theory of relativity", 
    "North America is in Earth", # Should be VERIFIED
    "The Eiffel Tower is in London",  # False!
]

for claim in claims:
    result = verifier.verify(claim)
    print(result)
