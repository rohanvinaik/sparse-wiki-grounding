"""
Context-Aware Entity Grounding with Recursive Semantic Disambiguation.

Implements multi-layer trajectory tracking for disambiguation:
1. Build semantic decomposition trees for context and candidates
2. Track confidence trajectory at each layer (converging vs diverging)
3. Dynamic weighting based on initial match uncertainty

Example:
    When "Winston" appears in context of "storytelling, cognition, AI":
    - Winston Churchill: diverges at deeper layers (politics, war)
    - Patrick Winston: converges at deeper layers (AI, learning, knowledge)

    Result: Patrick Winston wins despite lower PageRank.
"""

from __future__ import annotations
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

from .entity import EntityProfile, Entity
from .store import EntityStore


@dataclass
class DisambiguationResult:
    """Result of context-aware disambiguation."""
    mention: str
    best_match: Optional[EntityProfile]
    confidence: float
    trajectory: List[float]  # Similarity at each decomposition layer
    trajectory_delta: float  # Change in similarity (positive = converging)
    all_candidates: List[Tuple[EntityProfile, float, List[float]]]  # (profile, score, trajectory)


@dataclass
class GroundingContext:
    """Context built from already-grounded entities."""
    entity_ids: Set[str]
    anchor_layers: List[Set[str]]  # Multi-layer anchor decomposition


class ContextGrounder:
    """
    Context-aware entity grounding with recursive semantic disambiguation.

    Uses multi-layer trajectory tracking to resolve ambiguous mentions:
    - Layer 0: Direct anchors from entity
    - Layer 1+: Recursive decomposition (anchors of anchors)
    - Trajectory: Track if overlap converges or diverges with depth

    Dynamic weighting lets trajectory override popularity when:
    - Initial match confidence is low (ambiguous)
    - Trajectory shows strong convergence

    Usage:
        store = EntityStore("wiki_grounding.db")
        grounder = ContextGrounder(store)

        # Ground multiple terms with context awareness
        context = grounder.build_context(["storytelling", "cognition", "AI"])
        result = grounder.disambiguate("Winston", context)

        # result.best_match will be Patrick Winston (AI researcher)
        # instead of Winston Churchill (higher PageRank but diverging context)
    """

    def __init__(
        self,
        store: EntityStore,
        max_decomposition_depth: int = 2,
        anchors_per_layer: int = 15,
        trajectory_base_weight: float = 0.3,
    ):
        """
        Initialize context grounder.

        Args:
            store: EntityStore for entity/anchor lookups
            max_decomposition_depth: How many layers deep to decompose (default 2)
            anchors_per_layer: Max anchors to process per layer (performance limit)
            trajectory_base_weight: Minimum weight for trajectory (scales up with uncertainty)
        """
        self.store = store
        self.max_depth = max_decomposition_depth
        self.anchors_per_layer = anchors_per_layer
        self.trajectory_base_weight = trajectory_base_weight

    def build_context(
        self,
        grounded_terms: List[str],
        grounded_entity_ids: Optional[List[str]] = None,
    ) -> GroundingContext:
        """
        Build multi-layer context from grounded terms.

        Args:
            grounded_terms: Text terms that have been grounded (for search)
            grounded_entity_ids: Optional pre-resolved entity IDs

        Returns:
            GroundingContext with multi-layer anchor decomposition
        """
        entity_ids: Set[str] = set()
        layer0_anchors: Set[str] = set()

        # Resolve terms to entities if IDs not provided
        if grounded_entity_ids:
            entity_ids = set(grounded_entity_ids)
        else:
            for term in grounded_terms:
                results = self.store.search_exact(term, limit=1)
                if not results:
                    results = self.store.search(term, limit=1)
                if results:
                    entity_ids.add(results[0].entity.id)

        # Build layer 0: direct anchors from grounded entities
        for eid in entity_ids:
            anchors = self.store.get_entity_anchors(eid)
            for anchor_id, anchor_label, category, weight in anchors[:self.anchors_per_layer]:
                layer0_anchors.add(anchor_label.lower())

        # Build deeper layers by decomposing anchors
        anchor_layers = [layer0_anchors]

        for depth in range(self.max_depth):
            prev_layer = anchor_layers[-1]
            next_layer: Set[str] = set()

            for anchor_label in list(prev_layer)[:self.anchors_per_layer * 2]:
                # Search for entity matching this anchor
                anchor_results = self.store.search_exact(anchor_label, limit=1)
                if anchor_results:
                    anchor_entity = anchor_results[0]
                    # Get this entity's anchors (decomposition)
                    sub_anchors = self.store.get_entity_anchors(anchor_entity.entity.id)
                    for sa in sub_anchors[:self.anchors_per_layer]:
                        next_layer.add(sa[1].lower())

            anchor_layers.append(next_layer)

        return GroundingContext(
            entity_ids=entity_ids,
            anchor_layers=anchor_layers,
        )

    def disambiguate(
        self,
        mention: str,
        context: GroundingContext,
        max_candidates: int = 20,
        min_confidence: float = 0.3,
    ) -> DisambiguationResult:
        """
        Disambiguate a mention using context with trajectory tracking.

        Args:
            mention: Text mention to disambiguate (e.g., "Winston")
            context: GroundingContext from build_context()
            max_candidates: Maximum candidates to consider
            min_confidence: Minimum confidence to return a match

        Returns:
            DisambiguationResult with best match and trajectory info
        """
        # Search for candidates
        results = self.store.search_exact(mention, limit=max_candidates)
        if not results:
            results = self.store.search(mention, limit=max_candidates)

        if not results:
            return DisambiguationResult(
                mention=mention,
                best_match=None,
                confidence=0.0,
                trajectory=[],
                trajectory_delta=0.0,
                all_candidates=[],
            )

        # Score each candidate with trajectory tracking
        all_candidates: List[Tuple[EntityProfile, float, List[float]]] = []

        for profile in results:
            base_score = self._compute_base_score(mention, profile)
            trajectory = self._compute_trajectory(profile, context)
            trajectory_score, trajectory_delta = self._score_trajectory(trajectory)

            # Description keyword matching with context anchors
            desc_score = 0.0
            if profile.entity.description:
                desc_lower = profile.entity.description.lower()
                for layer_idx, ctx_layer in enumerate(context.anchor_layers):
                    matches = sum(1 for anchor in ctx_layer if anchor in desc_lower)
                    desc_score += matches * 0.15 * (1 + layer_idx * 0.2)

            # Dynamic weighting: uncertainty increases trajectory influence
            uncertainty = 1.0 - min(base_score, 1.0)
            trajectory_influence = self.trajectory_base_weight + (uncertainty * 0.7)

            # Normalize and combine
            normalized_trajectory = trajectory_score * 0.4
            total_score = (
                base_score * (1.0 - trajectory_influence * 0.5) +
                normalized_trajectory * trajectory_influence +
                desc_score
            )

            all_candidates.append((profile, total_score, trajectory))

        # Sort by score
        all_candidates.sort(key=lambda x: x[1], reverse=True)

        # Determine best match
        best_match = None
        best_confidence = 0.0
        best_trajectory: List[float] = []
        best_delta = 0.0

        if all_candidates:
            best_profile, best_score, best_traj = all_candidates[0]
            if best_score >= min_confidence:
                best_match = best_profile
                best_confidence = min(best_score, 1.0)
                best_trajectory = best_traj
                _, best_delta = self._score_trajectory(best_traj)

        return DisambiguationResult(
            mention=mention,
            best_match=best_match,
            confidence=best_confidence,
            trajectory=best_trajectory,
            trajectory_delta=best_delta,
            all_candidates=all_candidates,
        )

    def _compute_base_score(self, mention: str, profile: EntityProfile) -> float:
        """Compute base score from label matching and importance."""
        score = 0.0
        mention_lower = mention.lower()
        label_lower = profile.entity.label.lower()

        # Label matching
        if label_lower == mention_lower:
            score += 0.5
        elif mention_lower in label_lower.split():
            score += 0.4
        elif mention_lower in label_lower:
            score += 0.3
        else:
            score += 0.1

        # Importance boost
        if profile.entity.vital_level:
            score += max(0, 1 - profile.entity.vital_level / 10) * 0.1
        if profile.entity.pagerank:
            score += min(profile.entity.pagerank * 0.5, 0.1)

        return score

    def _compute_trajectory(
        self,
        profile: EntityProfile,
        context: GroundingContext,
    ) -> List[float]:
        """
        Compute similarity trajectory at each decomposition layer.

        Returns list of similarities: [layer0_sim, layer1_sim, layer2_sim, ...]
        """
        trajectory = []

        # Build candidate's anchor layers
        candidate_layers: List[Set[str]] = []

        # Layer 0: direct anchors
        anchors = self.store.get_entity_anchors(profile.entity.id)
        layer0 = {a[1].lower() for a in anchors[:self.anchors_per_layer]}
        candidate_layers.append(layer0)

        # Deeper layers
        for depth in range(self.max_depth):
            prev = candidate_layers[-1]
            next_layer: Set[str] = set()

            for anchor_label in list(prev)[:self.anchors_per_layer]:
                anchor_results = self.store.search_exact(anchor_label, limit=1)
                if anchor_results:
                    sub_anchors = self.store.get_entity_anchors(anchor_results[0].entity.id)
                    for sa in sub_anchors[:self.anchors_per_layer // 2]:
                        next_layer.add(sa[1].lower())

            candidate_layers.append(next_layer)

        # Compute overlap at each layer
        for layer_idx in range(min(len(context.anchor_layers), len(candidate_layers))):
            ctx_layer = context.anchor_layers[layer_idx]
            cand_layer = candidate_layers[layer_idx]

            if len(ctx_layer) > 0 and len(cand_layer) > 0:
                overlap = ctx_layer & cand_layer
                union_size = len(ctx_layer | cand_layer)
                similarity = len(overlap) / union_size if union_size > 0 else 0
                trajectory.append(similarity)
            else:
                # No anchors at this layer
                trajectory.append(0.0 if layer_idx == 0 else trajectory[-1] if trajectory else 0.0)

        return trajectory

    def _score_trajectory(self, trajectory: List[float]) -> Tuple[float, float]:
        """
        Score trajectory based on convergence/divergence pattern.

        Returns:
            (trajectory_score, trajectory_delta)
            - trajectory_score: Overall score from trajectory
            - trajectory_delta: Net change (positive = converging, negative = diverging)
        """
        if len(trajectory) < 2:
            # Can't compute trajectory with <2 layers
            if trajectory:
                return trajectory[0] * 2.0, 0.0
            return -0.5, 0.0  # Penalty for no anchors

        score = 0.0
        total_delta = 0.0

        # Trajectory delta: convergence vs divergence
        for i in range(1, len(trajectory)):
            delta = trajectory[i] - trajectory[i-1]
            layer_weight = 1.0 + (i * 0.5)  # Deeper layers weighted more
            score += delta * layer_weight
            total_delta += delta

        # Absolute overlap at each layer
        for i, sim in enumerate(trajectory):
            layer_weight = 1.0 + (i * 0.3)
            score += sim * layer_weight

        return score, total_delta

    def ground_with_context(
        self,
        mentions: List[str],
        initial_context: Optional[List[str]] = None,
    ) -> Dict[str, DisambiguationResult]:
        """
        Ground multiple mentions with progressive context building.

        First grounds unambiguous mentions, builds context from them,
        then uses that context to disambiguate harder mentions.

        Args:
            mentions: List of text mentions to ground
            initial_context: Optional initial context terms

        Returns:
            Dict mapping mention -> DisambiguationResult
        """
        results: Dict[str, DisambiguationResult] = {}
        grounded_entity_ids: Set[str] = set()

        # Build initial context if provided
        if initial_context:
            context = self.build_context(initial_context)
            grounded_entity_ids = context.entity_ids

        # First pass: ground unambiguous mentions
        ambiguous: List[str] = []

        for mention in mentions:
            search_results = self.store.search_exact(mention, limit=5)
            if not search_results:
                search_results = self.store.search(mention, limit=5)

            if not search_results:
                # No matches
                results[mention] = DisambiguationResult(
                    mention=mention,
                    best_match=None,
                    confidence=0.0,
                    trajectory=[],
                    trajectory_delta=0.0,
                    all_candidates=[],
                )
            elif len(search_results) == 1:
                # Single match - unambiguous
                profile = search_results[0]
                results[mention] = DisambiguationResult(
                    mention=mention,
                    best_match=profile,
                    confidence=0.9,
                    trajectory=[1.0],
                    trajectory_delta=0.0,
                    all_candidates=[(profile, 0.9, [1.0])],
                )
                grounded_entity_ids.add(profile.entity.id)
            elif search_results[0].entity.label.lower() == mention.lower():
                # Exact label match with single entity of that name
                exact = [r for r in search_results if r.entity.label.lower() == mention.lower()]
                if len(exact) == 1:
                    profile = exact[0]
                    results[mention] = DisambiguationResult(
                        mention=mention,
                        best_match=profile,
                        confidence=0.9,
                        trajectory=[1.0],
                        trajectory_delta=0.0,
                        all_candidates=[(profile, 0.9, [1.0])],
                    )
                    grounded_entity_ids.add(profile.entity.id)
                else:
                    ambiguous.append(mention)
            else:
                ambiguous.append(mention)

        # Second pass: disambiguate using context
        if ambiguous and grounded_entity_ids:
            context = self.build_context([], list(grounded_entity_ids))

            for mention in ambiguous:
                result = self.disambiguate(mention, context)
                results[mention] = result
                if result.best_match:
                    grounded_entity_ids.add(result.best_match.entity.id)
        elif ambiguous:
            # No context available - use pure PageRank
            for mention in ambiguous:
                search_results = self.store.search(mention, limit=10)
                if search_results:
                    best = search_results[0]
                    results[mention] = DisambiguationResult(
                        mention=mention,
                        best_match=best,
                        confidence=0.5,  # Lower confidence without context
                        trajectory=[],
                        trajectory_delta=0.0,
                        all_candidates=[(r, r.entity.pagerank or 0.5, []) for r in search_results],
                    )
                else:
                    results[mention] = DisambiguationResult(
                        mention=mention,
                        best_match=None,
                        confidence=0.0,
                        trajectory=[],
                        trajectory_delta=0.0,
                        all_candidates=[],
                    )

        return results
