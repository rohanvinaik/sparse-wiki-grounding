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


# Confidence threshold for returning SUPPORTED/CONTRADICTED
# Below this, return UNVERIFIABLE to avoid false positives
VERIFICATION_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class VerificationResult:
    """Result of verifying a claim.

    Includes confidence metrics for graceful abstention - when confidence
    is below threshold, returns UNVERIFIABLE rather than making a potentially
    wrong judgment (zero false positive principle).
    """
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

    # Abstention reason (if confidence below threshold)
    abstention_reason: Optional[str] = None

    @property
    def is_confident(self) -> bool:
        """Whether confidence is high enough to trust the verdict."""
        return self.confidence >= VERIFICATION_CONFIDENCE_THRESHOLD

    @property
    def effective_status(self) -> VerificationStatus:
        """Status accounting for confidence threshold.

        Returns UNVERIFIABLE if confidence is below threshold,
        even if internal status is SUPPORTED/CONTRADICTED.
        """
        if self.status in (VerificationStatus.SUPPORTED, VerificationStatus.CONTRADICTED):
            if not self.is_confident:
                return VerificationStatus.UNVERIFIABLE
        return self.status

    def __str__(self) -> str:
        status_emoji = {
            VerificationStatus.SUPPORTED: "✓",
            VerificationStatus.CONTRADICTED: "✗",
            VerificationStatus.UNVERIFIABLE: "?",
            VerificationStatus.PLAUSIBLE: "~",
        }
        effective = self.effective_status
        conf_str = f" (conf={self.confidence:.2f})" if not self.is_confident else ""
        return f"[{status_emoji[effective]}] {self.claim}{conf_str}"


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

# Relation type mappings (includes ConceptNet-style relations)
CLAIM_TO_RELATIONS = {
    "created": ["creator_of", "created", "invented", "RelatedTo"],
    "wrote": ["author_of", "wrote", "RelatedTo"],
    "invented": ["inventor_of", "invented", "created", "RelatedTo"],
    "discovered": ["discoverer_of", "discovered", "RelatedTo"],
    "founded": ["founder_of", "founded", "RelatedTo"],
    "built": ["builder_of", "built", "constructed", "RelatedTo"],
    "capital": ["capital_of", "AtLocation", "PartOf"],
    "located": ["located_in", "part_of", "AtLocation", "PartOf"],
}

# Location relation patterns - check for these in normalized relation names
LOCATION_RELATIONS = {"atlocation", "partof", "locatedin", "isin", "part_of", "located_in", "in"}


def normalize_relation(rel: str) -> str:
    """Normalize a relation name for comparison.

    Handles CamelCase (AtLocation -> atlocation), underscores, etc.
    """
    return rel.lower().replace("_", "").replace("-", "").replace(" ", "")


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
        # Normalize: strip articles and clean
        normalized = mention.strip()
        for article in ["the ", "a ", "an ", "The ", "A ", "An "]:
            if normalized.startswith(article):
                normalized = normalized[len(article):]
                break

        # Try variations in order of preference
        variations = [mention, normalized, normalized.title()]
        if mention != normalized:
            variations = [normalized, normalized.title(), mention]

        for variant in variations:
            # Try exact match first
            results = self.store.search_exact(variant, limit=5)
            if results:
                return results[0]

            # Try fuzzy match
            results = self.store.search(variant, limit=5)
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

        # Check for matching relation - use normalized versions for comparison
        relation_types = CLAIM_TO_RELATIONS.get(relation.lower(), [relation.lower()])
        # Normalize all relation types for comparison
        normalized_types = {normalize_relation(rt) for rt in relation_types}

        supporting = []
        for profile, rel, weight in related:
            # Use normalized matching for CamelCase relations
            normalized_rel = normalize_relation(rel)
            matches_relation = (
                normalized_rel in normalized_types or
                any(rt in rel.lower() for rt in relation_types) or
                normalized_rel == "relatedto"  # RelatedTo is a generic fallback
            )
            if matches_relation:
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
                # Use same normalized matching for contradiction detection
                normalized_rel = normalize_relation(rel)
                matches_relation = (
                    normalized_rel in normalized_types or
                    any(rt in rel.lower() for rt in relation_types)
                )
                if matches_relation and profile.entity.id != subject.entity.id:
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
        """
        Verify location claims using SPATIAL dimension hierarchy.

        Uses the is_descendant_of method for hierarchical verification:
        - "Paris is in Europe" -> Paris.is_descendant_of("Europe", SPATIAL) -> True
        - "Paris is in London" -> Paris.is_descendant_of("London", SPATIAL) -> False
        """
        # Use hierarchical navigation for location verification
        if subject.is_descendant_of(object_str, GroundingDimension.SPATIAL):
            spatial_pos = subject.get_position(GroundingDimension.SPATIAL)
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.SUPPORTED,
                claim_type=ClaimType.LOCATION,
                confidence=0.95,
                subject_entity=subject,
                object_entity=object_entity,
                supporting_evidence=[
                    f"SPATIAL hierarchy: {' > '.join(subject.navigate_from_zero(GroundingDimension.SPATIAL))}"
                ] if spatial_pos else [],
            )

        # Check SPATIAL position for contradictions
        spatial_pos = subject.get_position(GroundingDimension.SPATIAL)
        if spatial_pos:
            # Has spatial info but claimed location not in path -> contradiction
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.CONTRADICTED,
                claim_type=ClaimType.LOCATION,
                confidence=0.8,
                subject_entity=subject,
                object_entity=object_entity,
                contradicting_evidence=[
                    f"SPATIAL hierarchy: {' > '.join(spatial_pos.path_nodes)}"
                ],
                correction=f"{subject.entity.label} is located in {' > '.join(spatial_pos.path_nodes[-3:])}",
            )

        # No spatial info - check entity relations
        related = self.store.get_related(subject.entity.id, limit=50)
        for profile, rel, weight in related:
            # Use normalized relation matching for CamelCase relations (AtLocation, PartOf, etc.)
            normalized_rel = normalize_relation(rel)
            is_location_rel = normalized_rel in LOCATION_RELATIONS
            if is_location_rel:
                # Check if the related entity matches the claimed location
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
                # Also check if grounded object entity matches
                if object_entity and profile.entity.id == object_entity.entity.id:
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.SUPPORTED,
                        claim_type=ClaimType.LOCATION,
                        confidence=0.85,
                        subject_entity=subject,
                        object_entity=object_entity,
                        supporting_evidence=[f"{rel}: {profile.entity.label} (exact match)"],
                    )

        # Check anchor layer for geographic connections
        anchors = self.store.get_entity_anchors(subject.entity.id)
        for anchor_id, label, category, weight in anchors:
            if category == "GEOGRAPHY" and object_str.lower() in label.lower():
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.PLAUSIBLE,
                    claim_type=ClaimType.LOCATION,
                    confidence=0.6,
                    subject_entity=subject,
                    object_entity=object_entity,
                    supporting_evidence=[f"Geographic anchor: {label}"],
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
        """
        Verify property claims (X is a Y) using TAXONOMIC hierarchy.

        Uses hierarchical traversal for type checking:
        - "Albert Einstein is a scientist" -> check TAXONOMIC path
        - "Paris is a city" -> check TAXONOMIC path
        """
        # Use hierarchical navigation for type verification
        if subject.is_descendant_of(property_str, GroundingDimension.TAXONOMIC):
            tax_path = subject.navigate_from_zero(GroundingDimension.TAXONOMIC)
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.SUPPORTED,
                claim_type=ClaimType.PROPERTY,
                confidence=0.9,
                subject_entity=subject,
                supporting_evidence=[f"TAXONOMIC hierarchy: {' > '.join(tax_path)}"],
            )

        # Check DOMAIN dimension for field-related claims
        if subject.is_descendant_of(property_str, GroundingDimension.DOMAIN):
            domain_path = subject.navigate_from_zero(GroundingDimension.DOMAIN)
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.SUPPORTED,
                claim_type=ClaimType.PROPERTY,
                confidence=0.85,
                subject_entity=subject,
                supporting_evidence=[f"DOMAIN hierarchy: {' > '.join(domain_path)}"],
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

        # Check anchor layer for KNOWN_FOR associations
        anchors = self.store.get_entity_anchors(subject.entity.id)
        for anchor_id, label, category, weight in anchors:
            if category == "KNOWN_FOR" and property_str.lower() in label.lower():
                return VerificationResult(
                    claim=claim,
                    status=VerificationStatus.PLAUSIBLE,
                    claim_type=ClaimType.PROPERTY,
                    confidence=0.65,
                    subject_entity=subject,
                    supporting_evidence=[f"Known for: {label}"],
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
            claim_type=ClaimType.ATTRIBUTION, # Fallback/generic type
            confidence=0.3,
            subject_entity=subject,
            object_entity=object_entity,
        )
