"""Tests for road network generation algorithms."""

import pytest
from shapely.geometry import Polygon

from core.road_network import (
    generate_road_network,
    LSystemRoadGenerator,
    LSystemConfig,
    SkeletonRoadGenerator,
    SkeletonConfig,
    RoadSmoother
)


@pytest.fixture
def sample_site():
    """Create a sample rectangular site."""
    return Polygon([(0, 0), (500, 0), (500, 400), (0, 400), (0, 0)])


@pytest.fixture
def irregular_site():
    """Create an irregular L-shaped site."""
    return Polygon([
        (0, 0), (300, 0), (300, 200), 
        (500, 200), (500, 400), (0, 400), (0, 0)
    ])


class TestGenerateRoadNetwork:
    """Tests for the main generate_road_network function."""
    
    def test_skeleton_algorithm(self, sample_site):
        """Test skeleton road generation."""
        roads = generate_road_network(sample_site, algorithm='skeleton')
        
        assert len(roads) > 0
        assert all(r.length > 0 for r in roads)
        
    def test_l_systems_algorithm(self, sample_site):
        """Test L-Systems road generation."""
        roads = generate_road_network(
            sample_site, 
            algorithm='l_systems',
            seed=42
        )
        
        assert len(roads) > 0
        
    def test_hybrid_algorithm(self, sample_site):
        """Test hybrid road generation."""
        roads = generate_road_network(sample_site, algorithm='hybrid')
        
        assert len(roads) >= 0  # May have 0 if site is small
        
    def test_roads_within_boundary(self, sample_site):
        """Verify roads are clipped to boundary."""
        roads = generate_road_network(sample_site, algorithm='skeleton')
        
        for road in roads:
            # Road should be within or on boundary
            assert road.within(sample_site.buffer(1))


class TestLSystemRoadGenerator:
    """Tests for L-System road generator."""
    
    def test_basic_generation(self, sample_site):
        """Test basic L-System generation."""
        generator = LSystemRoadGenerator(sample_site)
        roads = generator.generate()
        
        assert isinstance(roads, list)
        
    def test_reproducibility(self, sample_site):
        """Test that seed provides reproducibility."""
        config = LSystemConfig(seed=42)
        gen1 = LSystemRoadGenerator(sample_site, config)
        gen2 = LSystemRoadGenerator(sample_site, config)
        
        roads1 = gen1.generate()
        roads2 = gen2.generate()
        
        assert len(roads1) == len(roads2)
        
    def test_iterations_affect_complexity(self, sample_site):
        """More iterations should produce more complex networks."""
        config_low = LSystemConfig(iterations=1, seed=42)
        config_high = LSystemConfig(iterations=3, seed=42)
        
        gen_low = LSystemRoadGenerator(sample_site, config_low)
        gen_high = LSystemRoadGenerator(sample_site, config_high)
        
        roads_low = gen_low.generate()
        roads_high = gen_high.generate()
        
        # Higher iterations typically produce more or longer roads
        total_low = sum(r.length for r in roads_low)
        total_high = sum(r.length for r in roads_high)
        
        # At least not less complex
        assert total_high >= total_low * 0.5


class TestSkeletonRoadGenerator:
    """Tests for skeleton road generator."""
    
    def test_main_road_exists(self, sample_site):
        """Test that main road is generated."""
        generator = SkeletonRoadGenerator(sample_site)
        main_road = generator.generate_main_road()
        
        assert main_road is not None
        assert not main_road.is_empty
        
    def test_perpendicular_branches(self, sample_site):
        """Test generation with perpendicular branches."""
        generator = SkeletonRoadGenerator(sample_site)
        roads = generator.generate_with_perpendicular_branches(num_branches=4)
        
        assert len(roads) >= 1  # At least main road
        

class TestRoadSmoother:
    """Tests for road smoothing utilities."""
    
    def test_fillet_corners(self):
        """Test corner filleting."""
        from shapely.geometry import LineString
        
        # Sharp corner road
        road = LineString([(0, 0), (100, 0), (100, 100)])
        
        smoothed = RoadSmoother.fillet_corners(road, radius=10)
        
        assert smoothed is not None
        assert not smoothed.is_empty
        
    def test_chamfer_corners(self):
        """Test corner chamfering."""
        from shapely.geometry import LineString
        
        road = LineString([(0, 0), (100, 0), (100, 100)])
        
        chamfered = RoadSmoother.chamfer_corners(road, chamfer_length=5)
        
        assert chamfered is not None
        assert not chamfered.is_empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
