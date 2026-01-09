"""
Spreading Activation for Semantic Context Retrieval

Based on Collins & Loftus (1975) spreading activation theory.
Activation spreads through TWO layers:
1. Entity links (direct relations)
2. Anchor layer (cross-node semantic connectivity)

The anchor layer enables entities to activate each other through shared
semantic anchors (dictionary-encoded labels) even without direct links.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from heapq import heappush, heappop
from enum import Enum

from .entity import EntityProfile, GroundingDimension
from .store import EntityStore


class SemanticBank(Enum):
    """
    Semantic banks for category-specific activation tracking.

    Each bank accumulates activation from different semantic channels,
    enabling multi-dimensional spreading activation.
    """
    SPATIAL = "SPATIAL"       # Geographic/location context
    TEMPORAL = "TEMPORAL"     # Historical/time context
    MENTAL = "MENTAL"         # Cognitive/conceptual context
    SUBSTANTIVES = "SUBSTANTIVES"  # Type/category context


# Mapping from anchor categories to semantic banks
ANCHOR_TO_BANK = {
    "SCOPE": SemanticBank.MENTAL,
    "HISTORY": SemanticBank.TEMPORAL,
    "KNOWN_FOR": SemanticBank.MENTAL,
    "GEOGRAPHY": SemanticBank.SPATIAL,
    "TYPE": SemanticBank.SUBSTANTIVES,
}


@dataclass
class ActivationResult:
    """Result of spreading activation."""
    entity: EntityProfile
    activation: float
    path: List[str]  # Entity IDs in activation path
    relations: List[str]  # Relations traversed
    bank_activations: Dict[SemanticBank, float] = field(default_factory=dict)

    def __lt__(self, other):
        return self.activation > other.activation  # Higher activation first


@dataclass
class SpreadingConfig:
    """Configuration for spreading activation."""
    decay: float = 0.7          # Activation decay per hop
    threshold: float = 0.15     # Minimum activation to continue (increased for speed)
    max_depth: int = 2          # Maximum hops from source (reduced for speed)
    max_results: int = 50       # Maximum entities to return
    use_anchors: bool = True    # Enable anchor-layer spreading
    anchor_decay: float = 0.4   # Decay for anchor-based spreading (lower than link decay)
    anchor_limit: int = 5       # Max entities to activate per anchor (reduced for speed)
    max_anchors: int = 10       # Max anchors to process per entity
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
                "capital_of": 0.8,
                "created": 0.8,
                "developed": 0.8,
                "discovered": 0.8,
                "invented": 0.8,
                "wrote": 0.8,
                "born_in": 0.7,
                "worked_at": 0.7,
                "awarded": 0.7,
                "related_to": 0.5,
            }

    def get_weight(self, relation: str) -> float:
        """Get weight for a relation type."""
        return self.relation_weights.get(relation, 0.5)


class SpreadingActivation:
    """
    Two-layer spreading activation through the entity graph.

    Layer 1: Entity Links (direct relations)
        Traditional spreading through explicit entity_links edges.

    Layer 2: Anchor Layer (cross-node connectivity)
        Spreading through shared semantic anchors. Entities connected
        to the same anchor will activate each other even without
        direct links.

    Usage:
        store = EntityStore("data/entities_demo.db")
        spreader = SpreadingActivation(store)

        # Spread from a single entity
        results = spreader.spread("Q90")  # Paris

        # Spread with anchor layer for richer connectivity
        results = spreader.spread("Q90", use_anchors=True)

        # Get bank-specific activations
        for result in results:
            print(f"{result.entity.entity.label}: {result.bank_activations}")
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
        initial_activation: float = 1.0,
        use_anchors: Optional[bool] = None
    ) -> List[ActivationResult]:
        """
        Spread activation from a single source entity.

        Args:
            source_id: Starting entity ID
            initial_activation: Starting activation level
            use_anchors: Override config.use_anchors for this call

        Returns:
            List of activated entities sorted by activation level
        """
        return self.spread_multiple(
            {source_id: initial_activation},
            use_anchors=use_anchors
        )

    def spread_multiple(
        self,
        sources: Dict[str, float],
        use_anchors: Optional[bool] = None
    ) -> List[ActivationResult]:
        """
        Spread activation from multiple source entities.

        Args:
            sources: Dict mapping entity_id -> initial_activation
            use_anchors: Override config.use_anchors for this call

        Returns:
            List of activated entities sorted by activation level
        """
        if use_anchors is None:
            use_anchors = self.config.use_anchors

        # Activation state: entity_id -> (activation, path, relations, bank_activations)
        activations: Dict[str, Tuple[float, List[str], List[str], Dict[SemanticBank, float]]] = {}
        visited: Set[str] = set()

        # Priority queue: (-activation, depth, entity_id, path, relations, bank_activations)
        queue = []

        # Initialize sources
        for entity_id, activation in sources.items():
            initial_banks = {bank: 0.0 for bank in SemanticBank}
            heappush(queue, (-activation, 0, entity_id, [entity_id], [], initial_banks))
            activations[entity_id] = (activation, [entity_id], [], initial_banks)

        # Spread activation
        while queue and len(visited) < self.config.max_results * 2:
            neg_act, depth, entity_id, path, relations, bank_acts = heappop(queue)
            activation = -neg_act

            if entity_id in visited:
                continue
            visited.add(entity_id)

            if depth >= self.config.max_depth:
                continue

            if activation < self.config.threshold:
                continue

            # =========================================================
            # Layer 1: Spread through entity_links
            # =========================================================
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
                    # Copy bank activations
                    new_banks = dict(bank_acts)
                    activations[neighbor_id] = (new_activation, new_path, new_relations, new_banks)

                    if neighbor_id not in visited:
                        heappush(queue, (
                            -new_activation, depth + 1, neighbor_id,
                            new_path, new_relations, new_banks
                        ))

            # =========================================================
            # Layer 2: Spread through anchor layer (cross-node)
            # =========================================================
            if use_anchors:
                anchors = self.store.get_entity_anchors(entity_id)

                # Limit anchors processed per entity for performance
                for anchor_id, anchor_label, category, anchor_weight in anchors[:self.config.max_anchors]:
                    # Get entities sharing this anchor
                    related_entities = self.store.get_entities_with_anchor(
                        anchor_id, limit=self.config.anchor_limit
                    )

                    # Determine semantic bank for this anchor
                    bank = ANCHOR_TO_BANK.get(category, SemanticBank.MENTAL)

                    for related_id, rel_weight in related_entities:
                        if related_id == entity_id:
                            continue  # Skip self

                        # Calculate anchor-based activation (typically lower decay)
                        anchor_activation = (
                            activation *
                            self.config.anchor_decay *
                            anchor_weight *
                            rel_weight
                        )

                        if anchor_activation < self.config.threshold:
                            continue

                        # Update if this is a new or better path
                        current = activations.get(related_id)
                        if current is None or anchor_activation > current[0]:
                            new_path = path + [related_id]
                            new_relations = relations + [f"anchor:{anchor_label}"]
                            # Update bank-specific activation
                            new_banks = dict(bank_acts)
                            new_banks[bank] = new_banks.get(bank, 0.0) + anchor_activation
                            activations[related_id] = (
                                anchor_activation, new_path, new_relations, new_banks
                            )

                            if related_id not in visited:
                                heappush(queue, (
                                    -anchor_activation, depth + 1, related_id,
                                    new_path, new_relations, new_banks
                                ))

        # Build results
        results = []
        for entity_id, (activation, path, relations, bank_acts) in activations.items():
            if entity_id in sources:
                continue  # Skip source entities

            profile = self.store.get(entity_id)
            if profile:
                results.append(ActivationResult(
                    entity=profile,
                    activation=activation,
                    path=path,
                    relations=relations,
                    bank_activations=bank_acts,
                ))

        # Sort by activation and limit
        results.sort()
        return results[:self.config.max_results]

    def context_entities(
        self,
        entity_ids: List[str],
        threshold: float = 0.2,
        use_anchors: bool = True
    ) -> List[EntityProfile]:
        """
        Get context-relevant entities for a set of entities.

        Useful for claim verification: spread from mentioned entities
        to find what else should be relevant.

        Args:
            entity_ids: Source entities
            threshold: Minimum activation to include
            use_anchors: Whether to use anchor layer
        """
        # Equal activation for all sources
        sources = {eid: 1.0 for eid in entity_ids}
        results = self.spread_multiple(sources, use_anchors=use_anchors)
        return [r.entity for r in results if r.activation >= threshold]

    def get_anchor_neighbors(
        self,
        entity_id: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Tuple[EntityProfile, str, float]]:
        """
        Get entities connected through shared anchors.

        This is useful for finding semantically related entities that
        don't have direct entity_links.

        Args:
            entity_id: Source entity
            category: Filter by anchor category (SCOPE, HISTORY, KNOWN_FOR, GEOGRAPHY)
            limit: Maximum results

        Returns:
            List of (EntityProfile, anchor_label, activation) tuples
        """
        results = []
        seen = set()

        anchors = self.store.get_entity_anchors(entity_id)

        for anchor_id, anchor_label, anchor_category, anchor_weight in anchors:
            if category and anchor_category != category:
                continue

            related = self.store.get_entities_with_anchor(anchor_id, limit=10)

            for related_id, rel_weight in related:
                if related_id == entity_id or related_id in seen:
                    continue
                seen.add(related_id)

                profile = self.store.get(related_id)
                if profile:
                    activation = anchor_weight * rel_weight
                    results.append((profile, anchor_label, activation))

        # Sort by activation and limit
        results.sort(key=lambda x: -x[2])
        return results[:limit]
