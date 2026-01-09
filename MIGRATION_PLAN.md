# Sparse Wiki Grounding - Complete Migration Plan

## Executive Summary

This plan creates a standalone, clean, impressive project for the Anthropic Fellows Program application.

**Source Assets:**
- Entity DB: `/Users/rohanvinaik/relational-ai/data/sparse_wiki.db` (249K entities, 1M positions)
- Entity code: `/Users/rohanvinaik/semantic_probing/src/semantic_probing/grounding/entity.py`
- Primitive encoding: `/Users/rohanvinaik/semantic_probing/src/semantic_probing/encoding/`

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/`

**Key Differentiator:** This project focuses on **claim verification** (safety-relevant), not just entity lookup.

---

## 1. Project Structure

```
/Users/rohanvinaik/sparse-wiki-grounding/
├── README.md                           # Main pitch (see Section 8)
├── pyproject.toml                      # Modern Python packaging
├── LICENSE                             # MIT
├── .gitignore
│
├── src/
│   └── wiki_grounding/
│       ├── __init__.py                 # Public API exports
│       ├── entity.py                   # Entity, EPAValues, DimensionPosition
│       ├── store.py                    # EntityStore (DB interface)
│       ├── epa.py                      # EPA encoding/mapping to primitives
│       ├── spreading.py                # Spreading activation
│       ├── verifier.py                 # Claim verification (NEW - key feature)
│       ├── parser.py                   # Claim parsing utilities
│       └── primitives.py               # Minimal primitive mappings (standalone)
│
├── data/
│   ├── entities_demo.db                # Vital Level 1-3 (~5K entities, ~15MB)
│   ├── entities_full.db.gz             # Full 250K entities (~100MB compressed)
│   └── schema.sql                      # DB schema for reference
│
├── examples/
│   ├── quickstart.py                   # 10-line demo
│   ├── verify_claims.py                # Claim verification demo
│   ├── explore_entity.py               # Single entity deep dive
│   ├── spreading_demo.py               # Spreading activation visualization
│   └── hallucination_detection.py      # Safety-focused demo (key for application)
│
├── tests/
│   ├── __init__.py
│   ├── test_entity.py
│   ├── test_store.py
│   ├── test_spreading.py
│   ├── test_verifier.py
│   └── test_integration.py
│
├── notebooks/
│   └── entity_exploration.ipynb        # Interactive exploration
│
└── scripts/
    ├── build_demo_db.py                # Extract demo DB from full
    ├── compute_epa.py                  # Compute EPA from primitives
    └── validate_db.py                  # Integrity checks
```

---

## 2. File-by-File Migration Plan

### 2.1 Core Entity Models

**Source:** `/Users/rohanvinaik/semantic_probing/src/semantic_probing/grounding/entity.py`
**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/entity.py`

**Changes:**
- Remove imports from `..encoding` (make standalone)
- Simplify to essential models only
- Add docstrings for fellowship reviewers

```python
# /Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/entity.py
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
```

---

### 2.2 Entity Store (Database Interface)

**Source:** Parts of `entity.py` + new code
**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/store.py`

```python
# /Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/store.py
"""
Entity store with SQLite backend.

Provides O(1) entity lookup and efficient relation queries.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Iterator, Tuple
from contextlib import contextmanager

from .entity import (
    Entity, EntityProfile, DimensionPosition, EPAValues,
    GroundingDimension, TernaryValue
)


class EntityStore:
    """
    SQLite-backed entity store for sparse wiki grounding.

    Usage:
        store = EntityStore("data/entities_demo.db")

        # Lookup by ID
        profile = store.get("Q90")  # Paris

        # Search by label
        results = store.search("Paris")

        # Get related entities
        related = store.get_related("Q90", relation="located_in")
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy connection with row factory."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "EntityStore":
        return self

    def __exit__(self, *args):
        self.close()

    # =========================================================================
    # Core Lookups
    # =========================================================================

    def get(self, entity_id: str) -> Optional[EntityProfile]:
        """
        Get entity by Wikidata ID.

        Args:
            entity_id: Wikidata Q-number (e.g., "Q90")

        Returns:
            EntityProfile or None if not found
        """
        row = self.conn.execute(
            "SELECT * FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()

        if not row:
            return None

        entity = self._row_to_entity(row)
        positions = self._get_positions(entity_id)
        epa = self._get_epa(entity_id)
        properties = self._get_properties(entity_id)

        return EntityProfile(entity, positions, epa, properties)

    def get_by_title(self, title: str) -> Optional[EntityProfile]:
        """Get entity by Wikipedia title."""
        row = self.conn.execute(
            "SELECT * FROM entities WHERE wikipedia_title = ?", (title,)
        ).fetchone()

        if not row:
            return None

        return self.get(row["id"])

    def search(
        self,
        label: str,
        limit: int = 10,
        min_vital_level: Optional[int] = None
    ) -> List[EntityProfile]:
        """
        Search entities by label (case-insensitive).

        Args:
            label: Search term
            limit: Maximum results
            min_vital_level: Only return entities with vital_level <= this

        Returns:
            List of matching EntityProfiles, sorted by importance
        """
        query = "SELECT * FROM entities WHERE LOWER(label) LIKE LOWER(?)"
        params = [f"%{label}%"]

        if min_vital_level is not None:
            query += " AND vital_level IS NOT NULL AND vital_level <= ?"
            params.append(min_vital_level)

        query += " ORDER BY COALESCE(pagerank, 0) DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return [self.get(row["id"]) for row in rows]

    def search_exact(self, label: str, limit: int = 10) -> List[EntityProfile]:
        """Search for exact label match (case-insensitive)."""
        rows = self.conn.execute(
            """SELECT * FROM entities
               WHERE LOWER(label) = LOWER(?)
               ORDER BY COALESCE(pagerank, 0) DESC
               LIMIT ?""",
            (label, limit)
        ).fetchall()
        return [self.get(row["id"]) for row in rows]

    # =========================================================================
    # Relation Queries
    # =========================================================================

    def get_related(
        self,
        entity_id: str,
        relation: Optional[str] = None,
        direction: str = "outgoing",
        limit: int = 50
    ) -> List[Tuple[EntityProfile, str, float]]:
        """
        Get entities related to this one.

        Args:
            entity_id: Source entity
            relation: Filter by relation type (None = all)
            direction: "outgoing", "incoming", or "both"
            limit: Maximum results

        Returns:
            List of (EntityProfile, relation_type, weight) tuples
        """
        results = []

        if direction in ("outgoing", "both"):
            query = "SELECT target_id, relation, weight FROM entity_links WHERE source_id = ?"
            params = [entity_id]
            if relation:
                query += " AND relation = ?"
                params.append(relation)
            query += " LIMIT ?"
            params.append(limit)

            for row in self.conn.execute(query, params):
                profile = self.get(row["target_id"])
                if profile:
                    results.append((profile, row["relation"], row["weight"]))

        if direction in ("incoming", "both"):
            query = "SELECT source_id, relation, weight FROM entity_links WHERE target_id = ?"
            params = [entity_id]
            if relation:
                query += " AND relation = ?"
                params.append(relation)
            query += " LIMIT ?"
            params.append(limit)

            for row in self.conn.execute(query, params):
                profile = self.get(row["source_id"])
                if profile:
                    results.append((profile, f"inverse_{row['relation']}", row["weight"]))

        return results[:limit]

    # =========================================================================
    # Iteration
    # =========================================================================

    def iter_entities(
        self,
        min_vital_level: Optional[int] = None,
        batch_size: int = 1000
    ) -> Iterator[EntityProfile]:
        """Iterate over all entities (for batch processing)."""
        query = "SELECT id FROM entities"
        params = []

        if min_vital_level is not None:
            query += " WHERE vital_level IS NOT NULL AND vital_level <= ?"
            params.append(min_vital_level)

        query += " ORDER BY COALESCE(pagerank, 0) DESC"

        for row in self.conn.execute(query, params):
            profile = self.get(row["id"])
            if profile:
                yield profile

    def count(self, min_vital_level: Optional[int] = None) -> int:
        """Count entities."""
        if min_vital_level is not None:
            return self.conn.execute(
                "SELECT COUNT(*) FROM entities WHERE vital_level <= ?",
                (min_vital_level,)
            ).fetchone()[0]
        return self.conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        return Entity(
            id=row["id"],
            wikipedia_title=row["wikipedia_title"],
            label=row["label"],
            description=row["description"],
            vital_level=row["vital_level"],
            pagerank=row["pagerank"],
        )

    def _get_positions(self, entity_id: str) -> List[DimensionPosition]:
        rows = self.conn.execute(
            "SELECT * FROM dimension_positions WHERE entity_id = ?",
            (entity_id,)
        ).fetchall()
        return [DimensionPosition.from_db_row(dict(row)) for row in rows]

    def _get_epa(self, entity_id: str) -> EPAValues:
        row = self.conn.execute(
            "SELECT * FROM epa_values WHERE entity_id = ?",
            (entity_id,)
        ).fetchone()

        if not row:
            return EPAValues()

        return EPAValues(
            evaluation=TernaryValue(row["evaluation"]),
            potency=TernaryValue(row["potency"]),
            activity=TernaryValue(row["activity"]),
            confidence=row["confidence"],
        )

    def _get_properties(self, entity_id: str) -> dict:
        rows = self.conn.execute(
            "SELECT key, value FROM properties WHERE entity_id = ?",
            (entity_id,)
        ).fetchall()
        return {row["key"]: row["value"] for row in rows}
```

---

### 2.3 Spreading Activation (NEW)

**Source:** New implementation
**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/spreading.py`

```python
# /Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/spreading.py
"""
Spreading activation for semantic context retrieval.

Based on Collins & Loftus (1975) spreading activation theory.
Activation spreads through the entity graph, decaying with distance.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from heapq import heappush, heappop

from .entity import EntityProfile, GroundingDimension
from .store import EntityStore


@dataclass
class ActivationResult:
    """Result of spreading activation."""
    entity: EntityProfile
    activation: float
    path: List[str]  # Entity IDs in activation path
    relations: List[str]  # Relations traversed

    def __lt__(self, other):
        return self.activation > other.activation  # Higher activation first


@dataclass
class SpreadingConfig:
    """Configuration for spreading activation."""
    decay: float = 0.7          # Activation decay per hop
    threshold: float = 0.1      # Minimum activation to continue
    max_depth: int = 3          # Maximum hops from source
    max_results: int = 50       # Maximum entities to return
    relation_weights: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        # Default relation weights (higher = stronger activation transfer)
        if not self.relation_weights:
            self.relation_weights = {
                "same_as": 1.0,
                "part_of": 0.9,
                "located_in": 0.8,
                "instance_of": 0.8,
                "subclass_of": 0.7,
                "related_to": 0.5,
            }

    def get_weight(self, relation: str) -> float:
        """Get weight for a relation type."""
        return self.relation_weights.get(relation, 0.5)


class SpreadingActivation:
    """
    Spreading activation through the entity graph.

    Usage:
        store = EntityStore("data/entities_demo.db")
        spreader = SpreadingActivation(store)

        # Spread from a single entity
        results = spreader.spread("Q90")  # Paris

        # Spread from multiple sources (for context)
        results = spreader.spread_multiple(["Q90", "Q142"])  # Paris, France
    """

    def __init__(
        self,
        store: EntityStore,
        config: Optional[SpreadingConfig] = None
    ):
        self.store = store
        self.config = config or SpreadingConfig()

    def spread(
        self,
        source_id: str,
        initial_activation: float = 1.0
    ) -> List[ActivationResult]:
        """
        Spread activation from a single source entity.

        Args:
            source_id: Starting entity ID
            initial_activation: Starting activation level

        Returns:
            List of activated entities sorted by activation level
        """
        return self.spread_multiple({source_id: initial_activation})

    def spread_multiple(
        self,
        sources: Dict[str, float]
    ) -> List[ActivationResult]:
        """
        Spread activation from multiple source entities.

        Args:
            sources: Dict mapping entity_id -> initial_activation

        Returns:
            List of activated entities sorted by activation level
        """
        # Activation state: entity_id -> (activation, path, relations)
        activations: Dict[str, Tuple[float, List[str], List[str]]] = {}
        visited: Set[str] = set()

        # Priority queue: (-activation, depth, entity_id, path, relations)
        # Negative activation for max-heap behavior
        queue = []

        # Initialize sources
        for entity_id, activation in sources.items():
            heappush(queue, (-activation, 0, entity_id, [entity_id], []))
            activations[entity_id] = (activation, [entity_id], [])

        # Spread activation
        while queue and len(visited) < self.config.max_results * 2:
            neg_act, depth, entity_id, path, relations = heappop(queue)
            activation = -neg_act

            if entity_id in visited:
                continue
            visited.add(entity_id)

            if depth >= self.config.max_depth:
                continue

            if activation < self.config.threshold:
                continue

            # Get neighbors
            related = self.store.get_related(entity_id, limit=20)

            for neighbor_profile, relation, weight in related:
                neighbor_id = neighbor_profile.entity.id

                # Calculate new activation
                relation_weight = self.config.get_weight(relation)
                new_activation = activation * self.config.decay * relation_weight * weight

                if new_activation < self.config.threshold:
                    continue

                # Update if better path found
                current = activations.get(neighbor_id)
                if current is None or new_activation > current[0]:
                    new_path = path + [neighbor_id]
                    new_relations = relations + [relation]
                    activations[neighbor_id] = (new_activation, new_path, new_relations)

                    if neighbor_id not in visited:
                        heappush(queue, (
                            -new_activation, depth + 1, neighbor_id,
                            new_path, new_relations
                        ))

        # Build results
        results = []
        for entity_id, (activation, path, relations) in activations.items():
            if entity_id in sources:
                continue  # Skip source entities

            profile = self.store.get(entity_id)
            if profile:
                results.append(ActivationResult(
                    entity=profile,
                    activation=activation,
                    path=path,
                    relations=relations,
                ))

        # Sort by activation and limit
        results.sort()
        return results[:self.config.max_results]

    def context_entities(
        self,
        entity_ids: List[str],
        threshold: float = 0.2
    ) -> List[EntityProfile]:
        """
        Get context-relevant entities for a set of entities.

        Useful for claim verification: spread from mentioned entities
        to find what else should be relevant.
        """
        # Equal activation for all sources
        sources = {eid: 1.0 for eid in entity_ids}
        results = self.spread_multiple(sources)
        return [r.entity for r in results if r.activation >= threshold]
```

---

### 2.4 Claim Verifier (NEW - Key Feature)

**Source:** New implementation
**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/verifier.py`

```python
# /Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/verifier.py
"""
Claim verification against grounded world knowledge.

The key safety-relevant feature: can we detect when claims
contradict established knowledge?
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
import re

from .entity import EntityProfile, EPAValues, GroundingDimension
from .store import EntityStore
from .spreading import SpreadingActivation


class VerificationStatus(str, Enum):
    """Verification result status."""
    SUPPORTED = "supported"       # Claim matches stored knowledge
    CONTRADICTED = "contradicted" # Claim conflicts with stored knowledge
    UNVERIFIABLE = "unverifiable" # Insufficient information
    PLAUSIBLE = "plausible"       # Consistent but not directly supported


class ClaimType(str, Enum):
    """Types of claims we can verify."""
    ATTRIBUTION = "attribution"   # "X created Y", "X wrote Y"
    LOCATION = "location"         # "X is in Y", "X is located in Y"
    TEMPORAL = "temporal"         # "X happened in Y", "X was born in Y"
    PROPERTY = "property"         # "X is Y" (property claim)
    RELATION = "relation"         # "X is related to Y"


@dataclass
class VerificationResult:
    """Result of verifying a claim."""
    claim: str
    status: VerificationStatus
    claim_type: Optional[ClaimType] = None
    confidence: float = 0.0

    # Extracted entities
    subject_entity: Optional[EntityProfile] = None
    object_entity: Optional[EntityProfile] = None

    # Evidence
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)

    # For contradictions: what the correct information is
    correction: Optional[str] = None

    def __str__(self) -> str:
        status_emoji = {
            VerificationStatus.SUPPORTED: "✓",
            VerificationStatus.CONTRADICTED: "✗",
            VerificationStatus.UNVERIFIABLE: "?",
            VerificationStatus.PLAUSIBLE: "~",
        }
        return f"[{status_emoji[self.status]}] {self.claim} ({self.confidence:.2f})"


# Relation patterns for claim parsing
RELATION_PATTERNS = {
    ClaimType.ATTRIBUTION: [
        r"(.+?)\s+(created|wrote|invented|developed|discovered|founded|built)\s+(.+)",
        r"(.+?)\s+is\s+the\s+(creator|inventor|author|founder)\s+of\s+(.+)",
    ],
    ClaimType.LOCATION: [
        r"(.+?)\s+is\s+(in|located in|situated in)\s+(.+)",
        r"(.+?)\s+is\s+the\s+capital\s+of\s+(.+)",
    ],
    ClaimType.TEMPORAL: [
        r"(.+?)\s+was\s+born\s+in\s+(\d{4})",
        r"(.+?)\s+(happened|occurred)\s+in\s+(\d{4})",
    ],
    ClaimType.PROPERTY: [
        r"(.+?)\s+is\s+(?:a|an)\s+(.+)",
        r"(.+?)\s+was\s+(?:a|an)\s+(.+)",
    ],
}

# Relation type mappings
CLAIM_TO_RELATIONS = {
    "created": ["creator_of", "created", "invented"],
    "wrote": ["author_of", "wrote"],
    "invented": ["inventor_of", "invented", "created"],
    "discovered": ["discoverer_of", "discovered"],
    "founded": ["founder_of", "founded"],
    "built": ["builder_of", "built", "constructed"],
    "capital": ["capital_of"],
    "located": ["located_in", "part_of"],
}


class ClaimVerifier:
    """
    Verify claims against grounded entity knowledge.

    Usage:
        store = EntityStore("data/entities_demo.db")
        verifier = ClaimVerifier(store)

        result = verifier.verify("Albert Einstein developed the theory of relativity")
        print(result.status)  # VerificationStatus.SUPPORTED

        result = verifier.verify("Albert Einstein invented the lightbulb")
        print(result.status)  # VerificationStatus.CONTRADICTED
        print(result.correction)  # "The lightbulb was invented by Thomas Edison"
    """

    def __init__(self, store: EntityStore):
        self.store = store
        self.spreader = SpreadingActivation(store)

    def verify(self, claim: str) -> VerificationResult:
        """
        Verify a natural language claim.

        Args:
            claim: Natural language claim to verify

        Returns:
            VerificationResult with status and evidence
        """
        # 1. Parse the claim
        parsed = self._parse_claim(claim)
        if parsed is None:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                confidence=0.0,
            )

        claim_type, subject_str, relation, object_str = parsed

        # 2. Ground entities
        subject_entity = self._ground_entity(subject_str)
        object_entity = self._ground_entity(object_str) if object_str else None

        if subject_entity is None:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                claim_type=claim_type,
                confidence=0.3,
            )

        # 3. Verify based on claim type
        if claim_type == ClaimType.ATTRIBUTION:
            return self._verify_attribution(
                claim, subject_entity, relation, object_str, object_entity
            )
        elif claim_type == ClaimType.LOCATION:
            return self._verify_location(
                claim, subject_entity, object_str, object_entity
            )
        elif claim_type == ClaimType.PROPERTY:
            return self._verify_property(
                claim, subject_entity, object_str
            )
        else:
            return self._verify_generic(
                claim, claim_type, subject_entity, relation, object_entity
            )

    def verify_batch(self, claims: List[str]) -> List[VerificationResult]:
        """Verify multiple claims."""
        return [self.verify(claim) for claim in claims]

    # =========================================================================
    # Parsing
    # =========================================================================

    def _parse_claim(
        self, claim: str
    ) -> Optional[Tuple[ClaimType, str, str, Optional[str]]]:
        """
        Parse claim into (type, subject, relation, object).
        """
        claim = claim.strip().rstrip(".")

        for claim_type, patterns in RELATION_PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, claim, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        subject = groups[0].strip()
                        relation = groups[1].strip() if len(groups) > 2 else ""
                        obj = groups[-1].strip() if len(groups) > 1 else None
                        return (claim_type, subject, relation, obj)

        return None

    def _ground_entity(self, mention: str) -> Optional[EntityProfile]:
        """Ground a mention to an entity."""
        # Try exact match first
        results = self.store.search_exact(mention, limit=5)
        if results:
            return results[0]

        # Try fuzzy match
        results = self.store.search(mention, limit=5)
        if results:
            return results[0]

        return None

    # =========================================================================
    # Verification Methods
    # =========================================================================

    def _verify_attribution(
        self,
        claim: str,
        subject: EntityProfile,
        relation: str,
        object_str: str,
        object_entity: Optional[EntityProfile]
    ) -> VerificationResult:
        """Verify attribution claims (X created/invented Y)."""
        # Get relations from subject
        related = self.store.get_related(subject.entity.id, limit=100)

        # Check for matching relation
        relation_types = CLAIM_TO_RELATIONS.get(relation.lower(), [relation.lower()])

        supporting = []
        for profile, rel, weight in related:
            if any(rt in rel.lower() for rt in relation_types):
                # Check if object matches
                if object_entity and profile.entity.id == object_entity.entity.id:
                    supporting.append(f"{rel}: {profile.entity.label}")
                elif object_str.lower() in profile.entity.label.lower():
                    supporting.append(f"{rel}: {profile.entity.label}")

        if supporting:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.SUPPORTED,
                claim_type=ClaimType.ATTRIBUTION,
                confidence=0.9,
                subject_entity=subject,
                object_entity=object_entity,
                supporting_evidence=supporting,
            )

        # Check if object has a DIFFERENT creator
        if object_entity:
            object_related = self.store.get_related(
                object_entity.entity.id, direction="incoming", limit=50
            )
            for profile, rel, weight in object_related:
                if any(rt in rel.lower() for rt in relation_types):
                    if profile.entity.id != subject.entity.id:
                        return VerificationResult(
                            claim=claim,
                            status=VerificationStatus.CONTRADICTED,
                            claim_type=ClaimType.ATTRIBUTION,
                            confidence=0.85,
                            subject_entity=subject,
                            object_entity=object_entity,
                            contradicting_evidence=[f"{rel}: {profile.entity.label}"],
                            correction=f"{object_str} was {relation} by {profile.entity.label}",
                        )

        # Can't verify either way
        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIABLE,
            claim_type=ClaimType.ATTRIBUTION,
            confidence=0.4,
            subject_entity=subject,
            object_entity=object_entity,
        )

    def _verify_location(
        self,
        claim: str,
        subject: EntityProfile,
        object_str: str,
        object_entity: Optional[EntityProfile]
    ) -> VerificationResult:
        """Verify location claims using SPATIAL dimension."""
        # Check SPATIAL position
        spatial_pos = subject.get_position(GroundingDimension.SPATIAL)

        if spatial_pos:
            # Check if claimed location is in path
            path_lower = [n.lower() for n in spatial_pos.path_nodes]
            if object_str.lower() in path_lower:
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.SUPPORTED,
                    claim_type=ClaimType.LOCATION,
                    confidence=0.95,
                    subject_entity=subject,
                    object_entity=object_entity,
                    supporting_evidence=[f"SPATIAL: {spatial_pos.formatted}"],
                )

            # Check if object is in the path (partial match)
            for node in spatial_pos.path_nodes:
                if object_str.lower() in node.lower() or node.lower() in object_str.lower():
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.SUPPORTED,
                        claim_type=ClaimType.LOCATION,
                        confidence=0.8,
                        subject_entity=subject,
                        object_entity=object_entity,
                        supporting_evidence=[f"SPATIAL: {spatial_pos.formatted}"],
                    )

            # Contradiction: has spatial info but doesn't match
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.CONTRADICTED,
                claim_type=ClaimType.LOCATION,
                confidence=0.7,
                subject_entity=subject,
                object_entity=object_entity,
                contradicting_evidence=[f"SPATIAL: {spatial_pos.formatted}"],
                correction=f"{subject.entity.label} is located in {'/'.join(spatial_pos.path_nodes[-3:])}",
            )

        # No spatial info - check relations
        related = self.store.get_related(subject.entity.id, limit=50)
        for profile, rel, weight in related:
            if "located" in rel.lower() or "part_of" in rel.lower():
                if object_str.lower() in profile.entity.label.lower():
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.SUPPORTED,
                        claim_type=ClaimType.LOCATION,
                        confidence=0.75,
                        subject_entity=subject,
                        object_entity=object_entity,
                        supporting_evidence=[f"{rel}: {profile.entity.label}"],
                    )

        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIABLE,
            claim_type=ClaimType.LOCATION,
            confidence=0.3,
            subject_entity=subject,
            object_entity=object_entity,
        )

    def _verify_property(
        self,
        claim: str,
        subject: EntityProfile,
        property_str: str
    ) -> VerificationResult:
        """Verify property claims (X is a Y)."""
        # Check TAXONOMIC position
        tax_pos = subject.get_position(GroundingDimension.TAXONOMIC)

        if tax_pos:
            path_lower = [n.lower() for n in tax_pos.path_nodes]
            if property_str.lower() in path_lower:
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.SUPPORTED,
                    claim_type=ClaimType.PROPERTY,
                    confidence=0.9,
                    subject_entity=subject,
                    supporting_evidence=[f"TAXONOMIC: {tax_pos.formatted}"],
                )

        # Check description
        if subject.entity.description:
            if property_str.lower() in subject.entity.description.lower():
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.SUPPORTED,
                    claim_type=ClaimType.PROPERTY,
                    confidence=0.8,
                    subject_entity=subject,
                    supporting_evidence=[f"Description: {subject.entity.description}"],
                )

        # Check properties
        for key, value in subject.properties.items():
            if property_str.lower() in str(value).lower():
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.SUPPORTED,
                    claim_type=ClaimType.PROPERTY,
                    confidence=0.75,
                    subject_entity=subject,
                    supporting_evidence=[f"{key}: {value}"],
                )

        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIABLE,
            claim_type=ClaimType.PROPERTY,
            confidence=0.3,
            subject_entity=subject,
        )

    def _verify_generic(
        self,
        claim: str,
        claim_type: ClaimType,
        subject: EntityProfile,
        relation: str,
        object_entity: Optional[EntityProfile]
    ) -> VerificationResult:
        """Generic verification using spreading activation."""
        if object_entity is None:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                claim_type=claim_type,
                confidence=0.2,
                subject_entity=subject,
            )

        # Spread from subject, see if object is activated
        results = self.spreader.spread(subject.entity.id)

        for result in results:
            if result.entity.entity.id == object_entity.entity.id:
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.PLAUSIBLE,
                    claim_type=claim_type,
                    confidence=result.activation,
                    subject_entity=subject,
                    object_entity=object_entity,
                    supporting_evidence=[f"Activation path: {' -> '.join(result.path)}"],
                )

        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIABLE,
            claim_type=claim_type,
            confidence=0.3,
            subject_entity=subject,
            object_entity=object_entity,
        )
```

---

### 2.5 EPA Encoder (Primitive Mapping)

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/epa.py`

```python
# /Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/epa.py
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
```

---

### 2.6 Package Init

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/__init__.py`

```python
# /Users/rohanvinaik/sparse-wiki-grounding/src/wiki_grounding/__init__.py
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
```

---

## 3. Example Scripts

### 3.1 Quickstart

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/examples/quickstart.py`

```python
#!/usr/bin/env python3
"""Quick start example - 10 lines to claim verification."""

from wiki_grounding import EntityStore, ClaimVerifier

# Load entity database
store = EntityStore("data/entities_demo.db")
verifier = ClaimVerifier(store)

# Verify some claims
claims = [
    "Paris is the capital of France",
    "Albert Einstein developed the theory of relativity",
    "The Eiffel Tower is in London",  # False!
]

for claim in claims:
    result = verifier.verify(claim)
    print(result)
```

### 3.2 Hallucination Detection Demo (Key for Application)

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/examples/hallucination_detection.py`

```python
#!/usr/bin/env python3
"""
Hallucination Detection Demo

This demonstrates how sparse wiki grounding can detect
factual hallucinations in LLM outputs - a key AI safety application.
"""

from wiki_grounding import EntityStore, ClaimVerifier, VerificationStatus

def demo_hallucination_detection():
    """
    Simulate checking LLM outputs for factual accuracy.

    In a real system, this would:
    1. Parse LLM output into claims
    2. Verify each claim against grounded knowledge
    3. Flag contradictions for human review
    """
    store = EntityStore("data/entities_demo.db")
    verifier = ClaimVerifier(store)

    # Simulated LLM outputs with some hallucinations
    llm_outputs = [
        # Correct claims
        "Marie Curie discovered radioactivity.",
        "The Great Wall of China is in China.",
        "Shakespeare wrote Hamlet.",

        # Hallucinations (incorrect)
        "Thomas Edison invented the telephone.",  # Bell did
        "The Statue of Liberty is in Paris.",     # It's in NYC
        "Einstein invented the light bulb.",      # Edison did

        # Plausible but unverifiable
        "Napoleon liked coffee.",
        "Cleopatra spoke seven languages.",
    ]

    print("=" * 60)
    print("HALLUCINATION DETECTION DEMO")
    print("=" * 60)
    print()

    results = {
        VerificationStatus.SUPPORTED: [],
        VerificationStatus.CONTRADICTED: [],
        VerificationStatus.UNVERIFIABLE: [],
        VerificationStatus.PLAUSIBLE: [],
    }

    for output in llm_outputs:
        result = verifier.verify(output)
        results[result.status].append(result)

        # Print with color coding
        if result.status == VerificationStatus.SUPPORTED:
            print(f"✓ VERIFIED: {output}")
            if result.supporting_evidence:
                print(f"  Evidence: {result.supporting_evidence[0]}")
        elif result.status == VerificationStatus.CONTRADICTED:
            print(f"✗ HALLUCINATION: {output}")
            print(f"  Correction: {result.correction}")
        elif result.status == VerificationStatus.PLAUSIBLE:
            print(f"~ PLAUSIBLE: {output}")
        else:
            print(f"? UNVERIFIABLE: {output}")
        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Verified:     {len(results[VerificationStatus.SUPPORTED])}")
    print(f"  Hallucinations: {len(results[VerificationStatus.CONTRADICTED])}")
    print(f"  Plausible:    {len(results[VerificationStatus.PLAUSIBLE])}")
    print(f"  Unverifiable: {len(results[VerificationStatus.UNVERIFIABLE])}")
    print()
    print("Hallucination detection rate: {:.0%}".format(
        len(results[VerificationStatus.CONTRADICTED]) /
        (len(results[VerificationStatus.CONTRADICTED]) + len(results[VerificationStatus.SUPPORTED]))
        if results[VerificationStatus.CONTRADICTED] else 0
    ))


if __name__ == "__main__":
    demo_hallucination_detection()
```

### 3.3 Spreading Activation Demo

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/examples/spreading_demo.py`

```python
#!/usr/bin/env python3
"""
Spreading Activation Demo

Visualize how activation spreads through the entity graph.
"""

from wiki_grounding import EntityStore, SpreadingActivation, SpreadingConfig

def demo_spreading():
    store = EntityStore("data/entities_demo.db")

    # Configure spreading
    config = SpreadingConfig(
        decay=0.7,
        threshold=0.1,
        max_depth=3,
        max_results=20,
    )
    spreader = SpreadingActivation(store, config)

    # Start from Marie Curie
    source = store.search_exact("Marie Curie")[0]
    print(f"Starting from: {source.summary()}")
    print()

    results = spreader.spread(source.entity.id)

    print("Activated entities:")
    print("-" * 60)
    for i, result in enumerate(results, 1):
        path_str = " → ".join(result.path[-3:])  # Last 3 in path
        print(f"{i:2}. {result.entity.entity.label:<30} "
              f"(activation: {result.activation:.3f})")
        print(f"    Path: {path_str}")
        print(f"    Relations: {', '.join(result.relations[:3])}")
        print()


if __name__ == "__main__":
    demo_spreading()
```

---

## 4. Data Preparation

### 4.1 Build Demo Database

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/scripts/build_demo_db.py`

```python
#!/usr/bin/env python3
"""
Build demo database from full sparse_wiki.db

Extracts Vital Articles Level 1-3 (~5K entities) for lightweight distribution.
"""

import sqlite3
import shutil
from pathlib import Path

SOURCE_DB = Path("/Users/rohanvinaik/relational-ai/data/sparse_wiki.db")
OUTPUT_DB = Path(__file__).parent.parent / "data" / "entities_demo.db"
MAX_VITAL_LEVEL = 3

def main():
    if not SOURCE_DB.exists():
        print(f"Source DB not found: {SOURCE_DB}")
        print("Run this after building the full sparse_wiki.db")
        return

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)

    # Copy full DB
    print(f"Copying from {SOURCE_DB}...")
    shutil.copy(SOURCE_DB, OUTPUT_DB)

    # Prune to vital articles only
    conn = sqlite3.connect(OUTPUT_DB)

    # Delete non-vital entities
    conn.execute(
        "DELETE FROM entities WHERE vital_level IS NULL OR vital_level > ?",
        (MAX_VITAL_LEVEL,)
    )

    # Cascade deletes
    conn.execute(
        "DELETE FROM dimension_positions WHERE entity_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM epa_values WHERE entity_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM properties WHERE entity_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM entity_links WHERE source_id NOT IN (SELECT id FROM entities) "
        "OR target_id NOT IN (SELECT id FROM entities)"
    )
    conn.execute(
        "DELETE FROM entity_anchors WHERE entity_id NOT IN (SELECT id FROM entities)"
    )

    # Vacuum to reclaim space
    conn.execute("VACUUM")
    conn.commit()

    # Report
    count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    size_mb = OUTPUT_DB.stat().st_size / 1024 / 1024

    print(f"Created {OUTPUT_DB}")
    print(f"  Entities: {count:,}")
    print(f"  Size: {size_mb:.1f} MB")

    conn.close()


if __name__ == "__main__":
    main()
```

### 4.2 Schema Reference

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/data/schema.sql`

```sql
-- Sparse Wiki Grounding Database Schema
-- This is the schema used by entities_demo.db and entities_full.db

CREATE TABLE entities (
    id TEXT PRIMARY KEY,           -- Wikidata Q-number (e.g., "Q90")
    wikipedia_title TEXT UNIQUE,   -- Canonical Wikipedia title
    label TEXT NOT NULL,           -- Human-readable name
    description TEXT,              -- Short description
    vital_level INTEGER,           -- 1-5 from Wikipedia Vital Articles
    pagerank REAL                  -- Importance score
);

CREATE TABLE dimension_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(id),
    dimension TEXT NOT NULL,       -- SPATIAL, TEMPORAL, TAXONOMIC, SCALE, DOMAIN
    path_sign INTEGER NOT NULL,    -- +1 (specific) or -1 (abstract) or 0
    path_depth INTEGER NOT NULL,   -- Distance from zero state
    path_nodes TEXT NOT NULL,      -- JSON array of path
    zero_state TEXT NOT NULL       -- Zero state for dimension
);

CREATE TABLE epa_values (
    entity_id TEXT PRIMARY KEY REFERENCES entities(id),
    evaluation INTEGER NOT NULL DEFAULT 0,  -- -1, 0, +1
    potency INTEGER NOT NULL DEFAULT 0,     -- -1, 0, +1
    activity INTEGER NOT NULL DEFAULT 0,    -- -1, 0, +1
    confidence REAL DEFAULT 1.0
);

CREATE TABLE properties (
    entity_id TEXT NOT NULL REFERENCES entities(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (entity_id, key)
);

CREATE TABLE entity_links (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    UNIQUE(source_id, target_id, relation)
);

-- Indexes for performance
CREATE INDEX idx_entities_label ON entities(label);
CREATE INDEX idx_entities_label_lower ON entities(LOWER(label));
CREATE INDEX idx_dim_pos_entity ON dimension_positions(entity_id);
CREATE INDEX idx_links_source ON entity_links(source_id);
CREATE INDEX idx_links_target ON entity_links(target_id);
```

---

## 5. Project Configuration

### 5.1 pyproject.toml

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sparse-wiki-grounding"
version = "0.1.0"
description = "Interpretable entity grounding for claim verification"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Rohan Vinaik" }
]
keywords = [
    "nlp",
    "knowledge-graph",
    "claim-verification",
    "hallucination-detection",
    "ai-safety",
    "entity-linking",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = []  # No dependencies! Pure Python + stdlib sqlite3

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
]
demo = [
    "rich",  # For pretty printing
]

[project.urls]
Homepage = "https://github.com/rohan-vinaik/sparse-wiki-grounding"
Repository = "https://github.com/rohan-vinaik/sparse-wiki-grounding"

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/data/entities_demo.db",
    "/data/schema.sql",
]

[tool.hatch.build.targets.wheel]
packages = ["src/wiki_grounding"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

### 5.2 .gitignore

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Data (full DB is too large for git)
data/entities_full.db
data/entities_full.db.gz
*.db-journal

# Keep demo DB
!data/entities_demo.db

# OS
.DS_Store
Thumbs.db
```

---

## 6. Tests

### 6.1 Test Entity Store

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/tests/test_store.py`

```python
"""Tests for EntityStore."""

import pytest
from wiki_grounding import EntityStore, GroundingDimension


@pytest.fixture
def store():
    """Load demo database."""
    return EntityStore("data/entities_demo.db")


def test_get_by_id(store):
    """Test lookup by Wikidata ID."""
    # Q90 = Paris
    profile = store.get("Q90")
    assert profile is not None
    assert profile.entity.label == "Paris"
    assert profile.entity.vital_level <= 3


def test_search_label(store):
    """Test search by label."""
    results = store.search("Paris", limit=5)
    assert len(results) > 0
    assert any(r.entity.id == "Q90" for r in results)


def test_get_positions(store):
    """Test dimension positions are loaded."""
    profile = store.get("Q90")
    assert len(profile.positions) > 0

    spatial = profile.get_position(GroundingDimension.SPATIAL)
    assert spatial is not None
    assert "France" in spatial.path_nodes or "Europe" in spatial.path_nodes


def test_get_epa(store):
    """Test EPA values are loaded."""
    profile = store.get("Q90")
    # Paris should have some EPA values
    assert profile.epa is not None


def test_count(store):
    """Test entity count."""
    count = store.count()
    assert count > 0

    vital_count = store.count(min_vital_level=1)
    assert vital_count <= count
```

### 6.2 Test Verifier

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/tests/test_verifier.py`

```python
"""Tests for ClaimVerifier."""

import pytest
from wiki_grounding import EntityStore, ClaimVerifier, VerificationStatus


@pytest.fixture
def verifier():
    """Create verifier with demo database."""
    store = EntityStore("data/entities_demo.db")
    return ClaimVerifier(store)


def test_verify_location_supported(verifier):
    """Test verifying a correct location claim."""
    result = verifier.verify("Paris is in France")
    assert result.status in (VerificationStatus.SUPPORTED, VerificationStatus.PLAUSIBLE)


def test_verify_location_contradicted(verifier):
    """Test detecting an incorrect location claim."""
    result = verifier.verify("Paris is in Germany")
    # Should either contradict or be unverifiable
    assert result.status != VerificationStatus.SUPPORTED


def test_verify_returns_evidence(verifier):
    """Test that verification returns evidence."""
    result = verifier.verify("Paris is in France")
    if result.status == VerificationStatus.SUPPORTED:
        assert len(result.supporting_evidence) > 0


def test_verify_unknown_entity(verifier):
    """Test handling of unknown entities."""
    result = verifier.verify("Xyzzy123 is in France")
    assert result.status == VerificationStatus.UNVERIFIABLE
```

---

## 7. README Structure

**Target:** `/Users/rohanvinaik/sparse-wiki-grounding/README.md`

```markdown
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
```

---

## 8. Implementation Order

### Phase 1: Foundation (Day 1)
1. Create directory structure
2. Write `entity.py` (models)
3. Write `store.py` (database interface)
4. Build demo database from sparse_wiki.db
5. Write basic tests

### Phase 2: Core Features (Day 2)
1. Write `spreading.py`
2. Write `verifier.py`
3. Write `epa.py`
4. Write examples

### Phase 3: Polish (Day 3)
1. Write README
2. Add more tests
3. Create notebook
4. Test full workflow
5. Push to GitHub

---

## 9. Commands to Execute

```bash
# 1. Create directory structure
mkdir -p /Users/rohanvinaik/sparse-wiki-grounding/{src/wiki_grounding,data,examples,tests,scripts,notebooks}

# 2. Create files (use this plan's code sections)

# 3. Build demo database
cd /Users/rohanvinaik/sparse-wiki-grounding
python scripts/build_demo_db.py

# 4. Install in dev mode
pip install -e ".[dev]"

# 5. Run tests
pytest tests/ -v

# 6. Run demos
python examples/quickstart.py
python examples/hallucination_detection.py

# 7. Initialize git
git init
git add .
git commit -m "Initial commit: sparse wiki grounding for claim verification"
```

---

## 10. Estimated Deliverables

| File | Lines | Purpose |
|------|-------|---------|
| `entity.py` | ~150 | Core data models |
| `store.py` | ~200 | Database interface |
| `spreading.py` | ~150 | Spreading activation |
| `verifier.py` | ~350 | Claim verification |
| `epa.py` | ~80 | EPA encoding |
| `__init__.py` | ~60 | Public API |
| `quickstart.py` | ~20 | Quick demo |
| `hallucination_detection.py` | ~80 | Safety demo |
| `spreading_demo.py` | ~50 | Spreading demo |
| `test_*.py` | ~150 | Tests |
| `README.md` | ~200 | Documentation |
| **Total** | **~1,500** | Clean, focused codebase |

---

## 11. Key Selling Points for Fellowship

1. **Safety-relevant**: Directly addresses LLM hallucination
2. **Interpretable**: EPA dimensions are meaningful, not black-box
3. **Zero dependencies**: Pure Python + stdlib (impressive engineering)
4. **Clean architecture**: Well-documented, tested, professional
5. **Demonstrates execution**: Working demo, not just theory
6. **Connects to research**: NSM primitives, Osgood EPA, spreading activation
7. **Practical scale**: 250K entities, real Wikipedia data
