"""
Sparse Wiki Grounding - Interpretable entity grounding for claim verification.

This package provides:
- Entity lookup with multi-dimensional positions
- EPA (Evaluation/Potency/Activity) semantic coordinates
- Spreading activation for context retrieval
- Claim verification against grounded world knowledge

Quick start:
    from wiki_grounding import EntityStore, ClaimVerifier

    store = EntityStore("data/entities_demo.db")
    verifier = ClaimVerifier(store)

    result = verifier.verify("Paris is the capital of France")
    print(result.status)  # VerificationStatus.SUPPORTED
"""

__version__ = "0.1.0"

from .entity import (
    Entity,
    EntityProfile,
    DimensionPosition,
    EPAValues,
    GroundingDimension,
    TernaryValue,
)

from .store import EntityStore

from .spreading import (
    SpreadingActivation,
    SpreadingConfig,
    ActivationResult,
    SemanticBank,
    ANCHOR_TO_BANK,
)

from .verifier import (
    ClaimVerifier,
    VerificationResult,
    VerificationStatus,
    ClaimType,
)

from .epa import (
    primitives_to_epa,
    epa_similarity,
    epa_compatible,
    PRIMITIVE_TO_EPA,
)

__all__ = [
    # Core entities
    "Entity",
    "EntityProfile",
    "DimensionPosition",
    "EPAValues",
    "GroundingDimension",
    "TernaryValue",
    # Store
    "EntityStore",
    # Spreading
    "SpreadingActivation",
    "SpreadingConfig",
    "ActivationResult",
    "SemanticBank",
    "ANCHOR_TO_BANK",
    # Verification
    "ClaimVerifier",
    "VerificationResult",
    "VerificationStatus",
    "ClaimType",
    # EPA
    "primitives_to_epa",
    "epa_similarity",
    "epa_compatible",
    "PRIMITIVE_TO_EPA",
]
