"""
Comprehensive test for Polygon-Constrained Estate Optimizer
Tests irregular polygon boundaries, validation, and DXF export
"""
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(level=logging.WARNING)

from shapely.geometry import Polygon
from src.algorithms.polygon_optimizer import (
    PolygonConstrainedEstateOptimizer,
    export_polygon_layout_to_dxf,
    PolygonConstraintValidator
)
import os

def test_polygon_optimizer():
    """Test polygon optimizer with irregular boundary"""
    print("=" * 70)
    print("🔷 POLYGON-CONSTRAINED OPTIMIZER TEST")
    print("=" * 70)
    
    # Test 1: Irregular pentagon boundary (from document)
    print("\n📍 TEST 1: Irregular Pentagon Boundary")
    print("-" * 50)
    
    pentagon_coords = [
        (310, 170),  # Corner 1
        (470, 170),  # Corner 2
        (590, 330),  # Corner 3
        (470, 450),  # Corner 4
        (310, 390),  # Corner 5
        (310, 170)   # Close
    ]
    
    boundary = Polygon(pentagon_coords)
    print(f"   Boundary area: {boundary.area:,.0f} m²")
    print(f"   Is valid: {boundary.is_valid}")
    
    plots = [
        {'width': 40, 'height': 50, 'type': 'warehouse'},
        {'width': 35, 'height': 45, 'type': 'office'},
        {'width': 45, 'height': 55, 'type': 'factory'},
        {'width': 40, 'height': 45, 'type': 'storage'},
    ] * 3  # 12 plots
    
    optimizer = PolygonConstrainedEstateOptimizer(
        boundary=boundary,
        plot_configs=plots,
        road_width=20,
        road_spacing=120,
        setback=8,
        plot_spacing=8,
        grid_step=8
    )
    
    # Suppress logging for cleaner output
    import src.algorithms.polygon_optimizer as po
    po.logger.setLevel(logging.WARNING)
    
    result = optimizer.optimize()
    
    print(f"\n   📊 RESULTS:")
    print(f"   Plots placed: {result['metrics']['num_plots']} / {len(plots)}")
    print(f"   Total area: {result['metrics']['total_plot_area']:,.0f} m²")
    print(f"   Utilization: {result['metrics']['utilization']*100:.1f}%")
    print(f"   Valid: {'✅ YES' if result['is_valid'] else '❌ NO'}")
    
    # Export DXF
    os.makedirs('output', exist_ok=True)
    export_polygon_layout_to_dxf(result, 'output/polygon_pentagon.dxf')
    
    # Test 2: L-shaped boundary
    print("\n📍 TEST 2: L-Shaped Boundary")
    print("-" * 50)
    
    l_shape_coords = [
        (0, 0),
        (300, 0),
        (300, 150),
        (150, 150),
        (150, 300),
        (0, 300),
        (0, 0)
    ]
    
    l_boundary = Polygon(l_shape_coords)
    print(f"   Boundary area: {l_boundary.area:,.0f} m²")
    
    optimizer2 = PolygonConstrainedEstateOptimizer(
        boundary=l_boundary,
        plot_configs=plots[:8],  # 8 plots
        road_width=18,
        road_spacing=120,
        setback=8,
        plot_spacing=8,
        grid_step=8
    )
    
    result2 = optimizer2.optimize()
    
    print(f"\n   📊 RESULTS:")
    print(f"   Plots placed: {result2['metrics']['num_plots']} / 8")
    print(f"   Total area: {result2['metrics']['total_plot_area']:,.0f} m²")
    print(f"   Utilization: {result2['metrics']['utilization']*100:.1f}%")
    print(f"   Valid: {'✅ YES' if result2['is_valid'] else '❌ NO'}")
    
    export_polygon_layout_to_dxf(result2, 'output/polygon_l_shape.dxf')
    
    # Test 3: Rectangular boundary (compatibility test)
    print("\n📍 TEST 3: Rectangular Boundary (Compatibility)")
    print("-" * 50)
    
    rect_boundary = {'min_x': 0, 'min_y': 0, 'max_x': 500, 'max_y': 400}
    
    optimizer3 = PolygonConstrainedEstateOptimizer(
        boundary=rect_boundary,  # Dict format
        plot_configs=plots,
        road_width=24,
        road_spacing=200,
        setback=10,
        plot_spacing=10,
        grid_step=15
    )
    
    result3 = optimizer3.optimize()
    
    print(f"\n   📊 RESULTS:")
    print(f"   Plots placed: {result3['metrics']['num_plots']} / {len(plots)}")
    print(f"   Total area: {result3['metrics']['total_plot_area']:,.0f} m²")
    print(f"   Utilization: {result3['metrics']['utilization']*100:.1f}%")
    print(f"   Valid: {'✅ YES' if result3['is_valid'] else '❌ NO'}")
    
    export_polygon_layout_to_dxf(result3, 'output/polygon_rectangle.dxf')
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    
    # Check 1: Pentagon plots inside boundary
    if result['is_valid'] and len(result['violations']['outside_boundary']) == 0:
        print("   ✅ Pentagon: All plots inside boundary")
    else:
        print("   ❌ Pentagon: Plots outside boundary")
        all_passed = False
    
    # Check 2: L-shape plots inside boundary
    if result2['is_valid'] and len(result2['violations']['outside_boundary']) == 0:
        print("   ✅ L-Shape: All plots inside boundary")
    else:
        print("   ❌ L-Shape: Plots outside boundary")
        all_passed = False
    
    # Check 3: No overlaps
    if len(result['violations']['overlaps']) == 0:
        print("   ✅ Pentagon: No overlaps")
    else:
        print(f"   ❌ Pentagon: {len(result['violations']['overlaps'])} overlaps")
        all_passed = False
    
    if len(result2['violations']['overlaps']) == 0:
        print("   ✅ L-Shape: No overlaps")
    else:
        print(f"   ❌ L-Shape: {len(result2['violations']['overlaps'])} overlaps")
        all_passed = False
    
    # Check 4: Utilization > 20%
    if result['metrics']['utilization'] > 0.20:
        print(f"   ✅ Pentagon: Utilization {result['metrics']['utilization']*100:.1f}% > 20%")
    else:
        print(f"   ❌ Pentagon: Low utilization {result['metrics']['utilization']*100:.1f}%")
        all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED - Review violations above")
    print("=" * 70)
    
    print("\n📄 DXF FILES CREATED:")
    print("   • output/polygon_pentagon.dxf")
    print("   • output/polygon_l_shape.dxf")
    print("   • output/polygon_rectangle.dxf")
    
    return all_passed


if __name__ == "__main__":
    test_polygon_optimizer()
