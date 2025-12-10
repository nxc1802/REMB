"""Tests for aesthetic optimization functions."""

import sys
import traceback

def test_shape_quality():
    """Test shape quality analysis functions."""
    print("Testing shape quality functions...")
    try:
        from shapely.geometry import Polygon
        from core.geometry.shape_quality import (
            analyze_shape_quality,
            get_dominant_edge_vector,
            classify_lot_type,
            get_obb_dimensions
        )
        
        # Test 1: Perfect rectangle should have high score and be valid
        # Must be > 1000 m² to pass min area check
        rect = Polygon([(0, 0), (50, 0), (50, 40), (0, 40)])  # 2000 m²
        score, valid = analyze_shape_quality(rect)
        print(f"  Rectangle (2000m²): score={score:.3f}, valid={valid}")
        assert valid, "Rectangle should be valid"
        assert score > 0.8, "Rectangle should have high score"
        
        # Test 2: Triangle should have low rectangularity and be invalid
        tri = Polygon([(0, 0), (40, 0), (20, 30)])
        score, valid = analyze_shape_quality(tri)
        print(f"  Triangle: score={score:.3f}, valid={valid}")
        assert not valid, "Triangle should be invalid (low rectangularity)"
        
        # Test 3: Very elongated shape should be invalid
        elongated = Polygon([(0, 0), (200, 0), (200, 10), (0, 10)])
        score, valid = analyze_shape_quality(elongated)
        print(f"  Elongated: score={score:.3f}, valid={valid}")
        assert not valid, "Elongated shape should be invalid"
        
        # Test 4: Small lot should be invalid
        small = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])  # 100 m²
        score, valid = analyze_shape_quality(small)
        print(f"  Small lot: score={score:.3f}, valid={valid}")
        assert not valid, "Small lot should be invalid"
        
        # Test 5: Dominant edge vector
        vec = get_dominant_edge_vector(rect)
        print(f"  Dominant edge vector: {vec}")
        assert vec is not None, "Should return vector"
        
        # Test 6: OBB dimensions
        w, l, angle = get_obb_dimensions(rect)
        print(f"  OBB dimensions: width={w:.1f}, length={l:.1f}, angle={angle:.1f}°")
        assert abs(w - 40) < 1, "Width should be ~40"
        assert abs(l - 50) < 1, "Length should be ~50"
        
        # Test 7: Lot classification
        lot_type = classify_lot_type(rect)
        print(f"  Rectangle type: {lot_type}")
        assert lot_type == 'commercial', "Good lot should be commercial"
        
        # Triangle must be large enough (>1000m²) to be green_space, otherwise it's unusable
        large_tri = Polygon([(0, 0), (60, 0), (30, 50)])  # 1500 m²
        lot_type = classify_lot_type(large_tri)
        print(f"  Triangle type: {lot_type}")
        assert lot_type == 'green_space', "Bad lot (large enough) should be green_space"
        
        print("✅ Shape quality tests passed")
        return True
    except Exception as e:
        print(f"❌ Shape quality test failed: {e}")
        traceback.print_exc()
        return False


def test_orthogonal_slicer():
    """Test orthogonal slicing functions."""
    print("\nTesting orthogonal slicer functions...")
    try:
        from shapely.geometry import Polygon
        from core.geometry.orthogonal_slicer import (
            orthogonal_slice,
            subdivide_with_uniform_widths
        )
        
        # Test 1: Subdivide a rectangular block
        block = Polygon([(0, 0), (100, 0), (100, 50), (0, 50)])
        widths = [25, 25, 25, 25]
        
        lots = orthogonal_slice(block, widths)
        print(f"  Orthogonal slice: {len(lots)} lots from 4 widths")
        assert len(lots) == 4, "Should create 4 lots"
        
        # Test 2: Uniform width subdivision
        lots2, actual_widths = subdivide_with_uniform_widths(block, target_width=20)
        print(f"  Uniform subdivision: {len(lots2)} lots, widths={[round(w,1) for w in actual_widths]}")
        assert len(lots2) > 0, "Should create lots"
        
        print("✅ Orthogonal slicer tests passed")
        return True
    except Exception as e:
        print(f"❌ Orthogonal slicer test failed: {e}")
        traceback.print_exc()
        return False


def test_settings():
    """Test aesthetic settings in config."""
    print("\nTesting aesthetic settings...")
    try:
        from core.config.settings import (
            DEFAULT_SETTINGS,
            MIN_RECTANGULARITY,
            MAX_ASPECT_RATIO,
            MIN_LOT_AREA,
            DEVIATION_PENALTY_WEIGHT,
            ENABLE_LEFTOVER_MANAGEMENT
        )
        
        print(f"  MIN_RECTANGULARITY = {MIN_RECTANGULARITY}")
        print(f"  MAX_ASPECT_RATIO = {MAX_ASPECT_RATIO}")
        print(f"  MIN_LOT_AREA = {MIN_LOT_AREA}")
        print(f"  DEVIATION_PENALTY_WEIGHT = {DEVIATION_PENALTY_WEIGHT}")
        print(f"  ENABLE_LEFTOVER_MANAGEMENT = {ENABLE_LEFTOVER_MANAGEMENT}")
        
        assert MIN_RECTANGULARITY == 0.75, "Should match Beauti_mode spec"
        assert MAX_ASPECT_RATIO == 4.0, "Should match Beauti_mode spec"
        assert MIN_LOT_AREA == 1000.0, "Should match Beauti_mode spec"
        
        print("✅ Settings tests passed")
        return True
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Aesthetic Optimization Test Suite")
    print("=" * 50)
    
    results = []
    results.append(("Shape Quality", test_shape_quality()))
    results.append(("Orthogonal Slicer", test_orthogonal_slicer()))
    results.append(("Settings", test_settings()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL AESTHETIC TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
