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
