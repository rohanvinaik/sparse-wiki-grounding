"""
Entity models for sparse wiki grounding.

Core data structures representing entities with:
- Multi-dimensional positions (spatial, temporal, taxonomic, scale, domain)
- EPA values (Evaluation, Potency, Activity)
- Properties and relations
"""

from __future__ import annotations
from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
import json


class GroundingDimension(str, Enum):
    """
    Five hierarchical dimension trees for entity grounding.

    Each dimension has a tree structure with a "zero state" at the center.
    Paths toward leaves are +depth, paths toward root are -depth.
    """
    SPATIAL = "SPATIAL"       # Earth -> continents -> countries -> cities
    TEMPORAL = "TEMPORAL"     # Present -> centuries -> decades -> years
    TAXONOMIC = "TAXONOMIC"   # Thing -> Person/Place/Event -> subtypes
    SCALE = "SCALE"           # Regional -> Local/National/Global
    DOMAIN = "DOMAIN"         # Knowledge -> fields -> subfields


class TernaryValue(IntEnum):
    """Balanced ternary for EPA values: {-1, 0, +1}."""
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1


@dataclass(frozen=True)
class Entity:
    """
    A Wikipedia/Wikidata entity.

    Attributes:
        id: Wikidata Q-number (e.g., "Q90" for Paris)
        wikipedia_title: Canonical Wikipedia article title
        label: Human-readable name (may be ambiguous)
        description: Short disambiguating description
        vital_level: 1-5 from Wikipedia Vital Articles (1 = most important)
        pagerank: Importance score from link graph
    """
    id: str
    wikipedia_title: str
    label: str
    description: Optional[str] = None
    vital_level: Optional[int] = None
    pagerank: Optional[float] = None


@dataclass(frozen=True)
class DimensionPosition:
    """
    Position in one dimension tree.

    Example for Paris in SPATIAL:
        dimension: SPATIAL
        path_sign: +1 (specific)
        path_depth: 3
        path_nodes: ["Earth", "Europe", "France", "Paris"]
        zero_state: "Earth"

    Formatted: +3:SPATIAL/Earth/Europe/France/Paris
    """
    dimension: GroundingDimension
    path_sign: int           # +1 (specific), -1 (general), 0 (at zero)
    path_depth: int          # Distance from zero state
    path_nodes: tuple        # Immutable path (use tuple for frozen)
    zero_state: str

    def __post_init__(self):
        # Convert list to tuple if needed for frozen dataclass
        if isinstance(self.path_nodes, list):
            object.__setattr__(self, 'path_nodes', tuple(self.path_nodes))

    @property
    def formatted(self) -> str:
        """Human-readable path notation."""
        sign = "+" if self.path_sign > 0 else ("-" if self.path_sign < 0 else "")
        return f"{sign}{self.path_depth}:{self.dimension.value}/{'/'.join(self.path_nodes)}"

    @classmethod
    def from_db_row(cls, row: dict) -> "DimensionPosition":
        """Create from database row."""
        return cls(
            dimension=GroundingDimension(row["dimension"]),
            path_sign=row["path_sign"],
            path_depth=row["path_depth"],
            path_nodes=tuple(json.loads(row["path_nodes"])),
            zero_state=row["zero_state"],
        )


@dataclass(frozen=True)
class EPAValues:
    """
    Evaluation-Potency-Activity coordinates (Osgood 1957).

    Three orthogonal dimensions of affective meaning:
        Evaluation: good/bad (-1 to +1)
        Potency: weak/strong (-1 to +1)
        Activity: passive/active (-1 to +1)

    Example:
        "hero": E=+1, P=+1, A=+1 (good, strong, active)
        "villain": E=-1, P=+1, A=+1 (bad, strong, active)
        "victim": E=+1, P=-1, A=-1 (good, weak, passive)
    """
    evaluation: TernaryValue = TernaryValue.NEUTRAL
    potency: TernaryValue = TernaryValue.NEUTRAL
    activity: TernaryValue = TernaryValue.NEUTRAL
    confidence: float = 1.0

    def as_vector(self) -> tuple:
        """Return as (E, P, A) tuple."""
        return (self.evaluation, self.potency, self.activity)

    def distance(self, other: "EPAValues") -> float:
        """Euclidean distance in EPA space."""
        return (
            (self.evaluation - other.evaluation) ** 2 +
            (self.potency - other.potency) ** 2 +
            (self.activity - other.activity) ** 2
        ) ** 0.5


@dataclass
class EntityProfile:
    """Complete entity profile with all grounding information."""
    entity: Entity
    positions: List[DimensionPosition] = field(default_factory=list)
    epa: EPAValues = field(default_factory=EPAValues)
    properties: Dict[str, Union[str, List[str]]] = field(default_factory=dict)

    def get_position(self, dimension: GroundingDimension) -> Optional[DimensionPosition]:
        """Get position for a specific dimension."""
        for pos in self.positions:
            if pos.dimension == dimension:
                return pos
        return None

    def summary(self) -> str:
        """Human-readable summary."""
        e = self.entity
        epa = f"E={self.epa.evaluation:+d} P={self.epa.potency:+d} A={self.epa.activity:+d}"
        dims = ", ".join(p.formatted for p in self.positions[:3])
        return f"{e.label} ({e.id}): {epa} | {dims}"
