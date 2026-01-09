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
