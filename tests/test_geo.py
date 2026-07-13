"""Tests for GeoService (Haversine distance calculations)"""
import pytest
from app.services.geo_service import GeoService


class MockWorker:
    def __init__(self, name, latitude, longitude):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude


def test_haversine_known_distance():
    """Test Haversine with known Cairo-to-Alexandria distance (~180km)."""
    # Cairo: 30.0444, 31.2357
    # Alexandria: 31.2001, 29.9187
    distance = GeoService.haversine_distance(30.0444, 31.2357, 31.2001, 29.9187)
    assert 170 < distance < 190  # ~180 km


def test_haversine_same_point():
    """Test that distance from a point to itself is zero."""
    distance = GeoService.haversine_distance(30.0, 31.0, 30.0, 31.0)
    assert distance == 0.0


def test_haversine_very_close():
    """Test distance for two very close points."""
    # About 100 meters apart
    d = GeoService.haversine_distance(30.0444, 31.2357, 30.0445, 31.2358)
    assert d < 1.0  # Less than 1 km


def test_filter_by_proximity():
    """Test filtering objects by distance."""
    workers = [
        MockWorker("Nearby", 30.05, 31.24),      # ~1 km away
        MockWorker("Medium", 30.10, 31.30),       # ~8 km away
        MockWorker("Far Away", 31.20, 29.92),     # ~180 km away
        MockWorker("No Location", None, None),     # Should be excluded
    ]

    results = GeoService.filter_by_proximity(
        workers,
        center_lat=30.0444,
        center_lng=31.2357,
        radius_km=50.0,
    )

    # Only "Nearby" and "Medium" should be within 50 km
    assert len(results) == 2
    names = [r[0].name for r in results]
    assert "Nearby" in names
    assert "Medium" in names
    assert "Far Away" not in names
    assert "No Location" not in names

    # Should be sorted by distance (nearest first)
    assert results[0][1] < results[1][1]


def test_filter_with_zero_radius():
    """Test that zero radius returns nothing (or only exact matches)."""
    workers = [MockWorker("A", 30.05, 31.24)]
    results = GeoService.filter_by_proximity(
        workers, 30.0444, 31.2357, radius_km=0.0
    )
    assert len(results) == 0


def test_filter_large_radius_includes_all():
    """Test that a very large radius includes all workers with coordinates."""
    workers = [
        MockWorker("A", 30.05, 31.24),
        MockWorker("B", 31.20, 29.92),
    ]
    results = GeoService.filter_by_proximity(
        workers, 30.0444, 31.2357, radius_km=500.0
    )
    assert len(results) == 2
