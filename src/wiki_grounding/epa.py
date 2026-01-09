"""
EPA (Evaluation-Potency-Activity) encoding.

Maps EPA values to and from semantic primitives (NSM).
Based on Osgood's semantic differential (1957).
"""

from .entity import EPAValues, TernaryValue


# Mapping from NSM primitives to EPA contributions
# EPA is a 3D projection of the full primitive space
PRIMITIVE_TO_EPA = {
    # Evaluation (GOOD/BAD dimension)
    "GOOD": {"E": +1},
    "BAD": {"E": -1},

    # Potency (BIG/SMALL + CAN/MUST dimensions)
    "BIG": {"P": +1},
    "SMALL": {"P": -1},
    "CAN": {"P": +0.5},  # Ability implies some potency
    "MUST": {"P": -0.3}, # Obligation implies external control

    # Activity (DO/HAPPEN + MOVE dimensions)
    "DO": {"A": +1},
    "MOVE": {"A": +0.8},
    "HAPPEN": {"A": +0.5},
    "ALIVE": {"A": +0.3},
    "DEAD": {"A": -1},

    # Mixed contributions
    "WANT": {"A": +0.3, "P": +0.2},  # Desire is active, implies agency
    "THINK": {"A": +0.2},            # Cognitive activity
    "FEEL": {"E": +0.2, "A": +0.2},  # Emotion has valence and activity
}

# Entity type defaults (when no other info available)
ENTITY_TYPE_EPA = {
    "person": EPAValues(TernaryValue.NEUTRAL, TernaryValue.NEUTRAL, TernaryValue.POSITIVE),
    "place": EPAValues(TernaryValue.NEUTRAL, TernaryValue.NEUTRAL, TernaryValue.NEGATIVE),
    "event": EPAValues(TernaryValue.NEUTRAL, TernaryValue.NEUTRAL, TernaryValue.POSITIVE),
    "organization": EPAValues(TernaryValue.NEUTRAL, TernaryValue.POSITIVE, TernaryValue.NEUTRAL),
    "concept": EPAValues(TernaryValue.NEUTRAL, TernaryValue.NEGATIVE, TernaryValue.NEGATIVE),
}


def primitives_to_epa(primitives: dict) -> EPAValues:
    """
    Convert primitive values to EPA coordinates.

    Args:
        primitives: Dict mapping primitive names to values (-1, 0, +1)

    Returns:
        EPAValues with ternary E, P, A values
    """
    e_sum, p_sum, a_sum = 0.0, 0.0, 0.0
    count = 0

    for prim, value in primitives.items():
        if prim in PRIMITIVE_TO_EPA:
            mapping = PRIMITIVE_TO_EPA[prim]
            e_sum += mapping.get("E", 0) * value
            p_sum += mapping.get("P", 0) * value
            a_sum += mapping.get("A", 0) * value
            count += 1

    # Normalize to ternary
    def to_ternary(x: float) -> TernaryValue:
        if x > 0.3:
            return TernaryValue.POSITIVE
        elif x < -0.3:
            return TernaryValue.NEGATIVE
        return TernaryValue.NEUTRAL

    return EPAValues(
        evaluation=to_ternary(e_sum),
        potency=to_ternary(p_sum),
        activity=to_ternary(a_sum),
        confidence=min(1.0, count / 3.0),
    )


def epa_similarity(epa1: EPAValues, epa2: EPAValues) -> float:
    """
    Compute similarity between two EPA profiles.

    Returns value in [0, 1] where 1 = identical.
    """
    distance = epa1.distance(epa2)
    max_distance = (3 * 4) ** 0.5  # Max possible distance
    return 1.0 - (distance / max_distance)


def epa_compatible(epa1: EPAValues, epa2: EPAValues, threshold: float = 0.5) -> bool:
    """Check if two EPA profiles are compatible (similar enough)."""
    return epa_similarity(epa1, epa2) >= threshold
