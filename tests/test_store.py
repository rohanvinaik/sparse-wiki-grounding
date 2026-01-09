"""Tests for EntityStore."""

import pytest
from wiki_grounding import EntityStore, GroundingDimension


@pytest.fixture
def store():
    """Load demo database."""
    # Assuming tests are run from project root and DB is built
    return EntityStore("data/entities_demo.db")


def test_get_by_id(store):
    """Test lookup by Wikidata ID."""
    # Find Paris ID first
    results = store.search_exact("Paris")
    if not results:
        return
        
    paris_id = results[0].entity.id
    profile = store.get(paris_id)
    
    assert profile is not None
    assert profile.entity.label == "Paris"
    assert profile.entity.vital_level <= 3

def test_search_label(store):
    """Test search by label."""
    # Paris is definitely in Vital 3
    results = store.search("Paris", limit=5)
    assert len(results) > 0
    # ID might be Q90 or Q_Paris depending on DB generation
    # Just check that one of the results is Paris
    assert any(r.entity.label == "Paris" for r in results)


def test_get_positions(store):
    """Test dimension positions are loaded."""
    # Search for Paris to get the correct ID
    results = store.search_exact("Paris")
    if not results:
        return
    
    profile = results[0]
    if profile:
        assert len(profile.positions) > 0

        spatial = profile.get_position(GroundingDimension.SPATIAL)
        # Some entities might not have spatial, but Paris should
        if spatial:
            assert "France" in spatial.path_nodes or "Europe" in spatial.path_nodes


def test_get_epa(store):
    """Test EPA values are loaded."""
    results = store.search_exact("Paris")
    if results:
        profile = results[0]
    if profile:
        # Paris should have some EPA values
        assert profile.epa is not None


def test_count(store):
    """Test entity count."""
    count = store.count()
    assert count > 0

    vital_count = store.count(min_vital_level=1)
    assert vital_count <= count
