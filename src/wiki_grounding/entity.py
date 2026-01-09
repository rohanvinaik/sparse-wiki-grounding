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

    # =========================================================================
    # Signed Vector Navigation
    # =========================================================================

    def navigate_toward_zero(self, dimension: GroundingDimension) -> List[str]:
        """
        Walk from current position toward the zero state.

        Returns path nodes in order from most specific to zero state.
        For example, for Paris in SPATIAL:
            ["Paris", "France", "Europe", "Earth"]

        This is useful for hierarchical reasoning - each step moves
        toward a more general/abstract concept.

        Args:
            dimension: Which dimension tree to navigate

        Returns:
            List of path nodes from current position toward zero
        """
        position = self.get_position(dimension)
        if position is None:
            return []
        # Reverse: specific → abstract
        return list(reversed(position.path_nodes))

    def navigate_from_zero(self, dimension: GroundingDimension) -> List[str]:
        """
        Walk from zero state toward current position.

        Returns path nodes in order from zero state to most specific.
        For example, for Paris in SPATIAL:
            ["Earth", "Europe", "France", "Paris"]

        Args:
            dimension: Which dimension tree to navigate

        Returns:
            List of path nodes from zero toward current position
        """
        position = self.get_position(dimension)
        if position is None:
            return []
        return list(position.path_nodes)

    def distance_from_zero(self, dimension: GroundingDimension) -> int:
        """
        Signed distance from zero state in a dimension.

        Positive: More specific than zero (e.g., Paris vs Earth)
        Negative: More abstract than zero
        Zero: At the zero state itself

        Args:
            dimension: Which dimension to measure

        Returns:
            Signed integer distance (path_sign * path_depth)
        """
        position = self.get_position(dimension)
        if position is None:
            return 0
        return position.path_sign * position.path_depth

    def is_descendant_of(
        self,
        ancestor_label: str,
        dimension: GroundingDimension
    ) -> bool:
        """
        Check if this entity is a descendant of an ancestor in a dimension tree.

        For example, Paris.is_descendant_of("Europe", SPATIAL) -> True
        This is the key operation for hierarchical verification.

        Args:
            ancestor_label: Label to check for in path
            dimension: Which dimension tree

        Returns:
            True if ancestor_label appears in the entity's path
        """
        position = self.get_position(dimension)
        if position is None:
            return False
        # Case-insensitive check
        path_lower = [n.lower() for n in position.path_nodes]
        return ancestor_label.lower() in path_lower

    def shared_ancestor(
        self,
        other: "EntityProfile",
        dimension: GroundingDimension
    ) -> Optional[str]:
        """
        Find the lowest common ancestor with another entity.

        For example:
            Paris.shared_ancestor(London, SPATIAL) -> "Europe"
            Paris.shared_ancestor(Tokyo, SPATIAL) -> "Earth"

        Args:
            other: Other entity to compare
            dimension: Which dimension tree

        Returns:
            Lowest common ancestor label, or None if no shared path
        """
        self_pos = self.get_position(dimension)
        other_pos = other.get_position(dimension)

        if self_pos is None or other_pos is None:
            return None

        # Find longest common prefix
        for i, (a, b) in enumerate(zip(self_pos.path_nodes, other_pos.path_nodes)):
            if a.lower() != b.lower():
                return self_pos.path_nodes[i - 1] if i > 0 else None

        # One path is a prefix of the other
        min_len = min(len(self_pos.path_nodes), len(other_pos.path_nodes))
        return self_pos.path_nodes[min_len - 1] if min_len > 0 else None

    def hierarchical_distance(
        self,
        other: "EntityProfile",
        dimension: GroundingDimension
    ) -> int:
        """
        Compute hierarchical distance in a dimension tree.

        This is the sum of steps from each entity to their common ancestor.
        Smaller distance = more closely related in the hierarchy.

        Args:
            other: Other entity to compare
            dimension: Which dimension tree

        Returns:
            Total steps to reach common ancestor, or -1 if no common path
        """
        self_pos = self.get_position(dimension)
        other_pos = other.get_position(dimension)

        if self_pos is None or other_pos is None:
            return -1

        # Find common prefix length
        common_depth = 0
        for a, b in zip(self_pos.path_nodes, other_pos.path_nodes):
            if a.lower() == b.lower():
                common_depth += 1
            else:
                break

        if common_depth == 0:
            return -1

        # Distance is sum of depths from common ancestor
        self_to_ancestor = len(self_pos.path_nodes) - common_depth
        other_to_ancestor = len(other_pos.path_nodes) - common_depth

        return self_to_ancestor + other_to_ancestor

    def position_vector(self) -> Dict[str, int]:
        """
        Get signed position vector across all dimensions.

        Returns:
            Dict mapping dimension name to signed distance from zero.
            Example: {"SPATIAL": 3, "TEMPORAL": 0, "TAXONOMIC": 2, ...}
        """
        return {
            dim.value: self.distance_from_zero(dim)
            for dim in GroundingDimension
        }
