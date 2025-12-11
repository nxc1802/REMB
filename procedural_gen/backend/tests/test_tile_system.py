"""Tests for WFC tile system."""

import pytest
from shapely.geometry import Polygon, box

from core.tile_system import (
    WFCSolver,
    WFCConfig,
    Tile,
    TileEdge,
    TileRegistry,
    get_tile_registry,
    solve_wfc
)


@pytest.fixture
def sample_lot():
    """Create a sample lot for WFC."""
    return box(0, 0, 100, 100)


@pytest.fixture
def industrial_registry():
    """Get industrial tile registry."""
    return get_tile_registry('industrial')


class TestTileRegistry:
    """Tests for tile registry."""
    
    def test_industrial_tiles_exist(self, industrial_registry):
        """Test that industrial tiles are defined."""
        tiles = industrial_registry.get_tile_set('industrial')
        
        assert len(tiles) > 0
        
    def test_tile_edge_matching(self, industrial_registry):
        """Test tile edge matching logic."""
        tiles = industrial_registry.get_tile_set('industrial')
        
        # Find road tiles
        road_h = industrial_registry.get('road_straight_h')
        road_v = industrial_registry.get('road_straight_v')
        
        if road_h and road_v:
            # Get compatible tiles in each direction
            compatible_e = industrial_registry.get_compatible(
                road_h, 'E', 'industrial'
            )
            assert len(compatible_e) > 0
            
    def test_tile_rotation(self):
        """Test tile rotation."""
        tile = Tile(
            id="test",
            name="Test Tile",
            edges=(TileEdge.ROAD, TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.EMPTY)
        )
        
        rotated = tile.rotate(1)
        
        # After 90° rotation, N edge should now be on E
        assert rotated.edges[1] == TileEdge.ROAD


class TestWFCSolver:
    """Tests for WFC solver."""
    
    def test_solver_initialization(self, sample_lot, industrial_registry):
        """Test WFC solver setup."""
        config = WFCConfig(tile_size=20.0)
        solver = WFCSolver(sample_lot, config, industrial_registry)
        
        assert solver.rows > 0
        assert solver.cols > 0
        
    def test_solve_completes(self, sample_lot):
        """Test that WFC solve completes."""
        config = WFCConfig(tile_size=25.0, seed=42, max_iterations=1000)
        solver = WFCSolver(sample_lot, config)
        
        result = solver.solve()
        
        # Should return list of cells
        assert isinstance(result, list)
        
    def test_all_cells_collapsed(self, sample_lot):
        """Test that all cells eventually collapse."""
        config = WFCConfig(tile_size=25.0, seed=42)
        solver = WFCSolver(sample_lot, config)
        
        result = solver.solve()
        
        collapsed_count = sum(1 for c in result if c.is_collapsed)
        total_count = len(result)
        
        # Most cells should be collapsed
        assert collapsed_count >= total_count * 0.8
        
    def test_result_polygons(self, sample_lot):
        """Test polygon output generation."""
        config = WFCConfig(tile_size=25.0, seed=42)
        solver = WFCSolver(sample_lot, config)
        solver.solve()
        
        polygons = solver.get_result_polygons()
        
        assert isinstance(polygons, dict)
        

class TestSolveWFC:
    """Tests for convenience function."""
    
    def test_solve_wfc_function(self, sample_lot):
        """Test the solve_wfc convenience function."""
        result = solve_wfc(sample_lot, tile_set='industrial', seed=42)
        
        assert isinstance(result, dict)
        
    def test_different_tile_sets(self, sample_lot):
        """Test with different tile sets."""
        result_ind = solve_wfc(sample_lot, tile_set='industrial', seed=42)
        result_res = solve_wfc(sample_lot, tile_set='residential', seed=42)
        
        # Both should produce results
        assert isinstance(result_ind, dict)
        assert isinstance(result_res, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
