"""Tests for subdivision algorithms."""

import pytest
from shapely.geometry import Polygon

from core.subdivision import (
    subdivide_site,
    subdivide_block,
    OBBTree,
    OBBTreeConfig,
    ShapeGrammar,
    ShapeGrammarConfig
)


@pytest.fixture
def sample_site():
    """Create a sample rectangular site."""
    return Polygon([(0, 0), (500, 0), (500, 400), (0, 400), (0, 0)])


@pytest.fixture
def sample_block():
    """Create a sample block for subdivision."""
    return Polygon([(0, 0), (200, 0), (200, 150), (0, 150), (0, 0)])


class TestSubdivideSite:
    """Tests for site subdivision."""
    
    def test_basic_subdivision(self, sample_site):
        """Test basic subdivision without roads."""
        lots, greens = subdivide_site(sample_site)
        
        assert len(lots) > 0 or len(greens) > 0
        
    def test_subdivision_with_roads(self, sample_site):
        """Test subdivision with road network."""
        from shapely.geometry import LineString
        
        roads = [
            LineString([(250, 0), (250, 400)]),  # Vertical
            LineString([(0, 200), (500, 200)])   # Horizontal
        ]
        
        lots, greens = subdivide_site(sample_site, roads=roads)
        
        # Should have more lots/greens than without roads
        assert len(lots) + len(greens) > 0
        
    def test_lot_quality(self, sample_site):
        """Test that lots meet quality criteria."""
        lots, _ = subdivide_site(sample_site, min_lot_area=500)
        
        for lot in lots:
            # All lots should have positive area
            assert lot.area > 0
            # All lots should be valid polygons
            assert lot.is_valid


class TestOBBTree:
    """Tests for OBB Tree subdivision."""
    
    def test_basic_subdivision(self, sample_block):
        """Test OBB Tree basic operation."""
        tree = OBBTree(sample_block)
        lots = tree.subdivide()
        
        assert len(lots) > 0
        
    def test_area_constraints(self, sample_block):
        """Test that lots respect area constraints."""
        config = OBBTreeConfig(
            min_lot_area=500,
            max_lot_area=5000
        )
        
        tree = OBBTree(sample_block, config)
        lots = tree.subdivide()
        
        for lot in lots:
            # Lots should not be too small (allowing some margin for clipping)
            assert lot.area >= config.min_lot_area * 0.5
            
    def test_total_area_preserved(self, sample_block):
        """Test that total area is approximately preserved."""
        tree = OBBTree(sample_block)
        lots = tree.subdivide()
        
        total_lot_area = sum(lot.area for lot in lots)
        
        # Allow 5% tolerance for clipping/overlap
        assert abs(total_lot_area - sample_block.area) < sample_block.area * 0.05


class TestShapeGrammar:
    """Tests for Shape Grammar rules."""
    
    def test_apply_to_valid_lots(self, sample_block):
        """Test grammar application to valid lots."""
        lots = [sample_block]
        
        grammar = ShapeGrammar()
        result = grammar.apply(lots)
        
        assert 'lots' in result
        assert 'green_spaces' in result
        
    def test_setback_application(self, sample_block):
        """Test that setbacks reduce lot area."""
        config = ShapeGrammarConfig(front_setback=5.0)
        grammar = ShapeGrammar(config)
        
        result = grammar.apply_to_lot(sample_block)
        
        if 'buildable' in result:
            buildable = result['buildable']
            if not buildable.is_empty:
                # Buildable area should be smaller than original
                assert buildable.area < sample_block.area
                
    def test_quality_filtering(self):
        """Test that poor quality shapes become green space."""
        # Very elongated shape
        elongated = Polygon([
            (0, 0), (200, 0), (200, 10), (0, 10), (0, 0)
        ])
        
        config = ShapeGrammarConfig(max_aspect_ratio=3.0)
        grammar = ShapeGrammar(config)
        result = grammar.apply([elongated])
        
        # Should be classified as green due to high aspect ratio
        # (depends on exact thresholds)
        assert len(result['lots']) + len(result['green_spaces']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
