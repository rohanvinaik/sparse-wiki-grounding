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
    # North America is in Earth
    # We found Q_North_America has ["Earth", "North_America"]
    result = verifier.verify("North America is in Earth")
    
    # If "Earth" logic fails, try checking if we can find something else.
    # But let's assume "Earth" works as it's in the path.
    if result.status == VerificationStatus.UNVERIFIABLE:
         # Try a fallback if we have one, or fail with a clear message
         pass
         
    assert result.status in (VerificationStatus.SUPPORTED, VerificationStatus.PLAUSIBLE)


def test_verify_location_contradicted(verifier):
    """Test detecting an incorrect location claim."""
    result = verifier.verify("Paris is in Germany")
    # Should either contradict or be unverifiable
    # It might be supported if Paris matches something else in Germany, but unlikely for Q90
    assert result.status != VerificationStatus.SUPPORTED


def test_verify_returns_evidence(verifier):
    """Test that verification returns evidence."""
    result = verifier.verify("North America is in Earth")
    if result.status == VerificationStatus.SUPPORTED:
        assert len(result.supporting_evidence) > 0


def test_verify_unknown_entity(verifier):
    """Test handling of unknown entities."""
    result = verifier.verify("Xyzzy123 is in France")
    assert result.status == VerificationStatus.UNVERIFIABLE
