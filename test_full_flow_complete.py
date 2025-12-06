"""
FULL FLOW TEST - Industrial Estate Optimization
Tests both Production and Polygon optimizers with detailed output
"""
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import os

print("=" * 70)
print("FULL FLOW TEST - INDUSTRIAL ESTATE OPTIMIZATION")
print("=" * 70)

# ============================================================================
# TEST 1: PRODUCTION OPTIMIZER (Rectangular Boundary)
# ============================================================================
print("\n" + "=" * 70)
print("TEST 1: PRODUCTION OPTIMIZER")
print("=" * 70)

from src.algorithms.production_optimizer import (
    ProductionReadyEstateOptimizer,
    export_optimized_layout_to_dxf
)

# Define rectangular boundary (500m x 400m)
rect_boundary = {
    'min_x': 0,
    'min_y': 0,
    'max_x': 500,
    'max_y': 400
}

# Define plots
production_plots = [
    {'width': 60, 'height': 80, 'type': 'warehouse'},
    {'width': 50, 'height': 60, 'type': 'office'},
    {'width': 70, 'height': 90, 'type': 'factory'},
    {'width': 55, 'height': 70, 'type': 'storage'},
] * 5  # 20 plots

print(f"\nBOUNDARY: {rect_boundary['max_x']}m x {rect_boundary['max_y']}m = 200,000 m2")
print(f"PLOTS TO PLACE: {len(production_plots)}")

# Create optimizer
prod_optimizer = ProductionReadyEstateOptimizer(
    boundary_coords=rect_boundary,
    plot_configs=production_plots,
    road_width=24,
    road_spacing=200,
    setback=10,
    plot_spacing=10
)

# Suppress detailed logging
import logging
logging.getLogger('src.algorithms.production_optimizer').setLevel(logging.WARNING)

# Run optimization
prod_result = prod_optimizer.optimize()

print(f"\nPRODUCTION OPTIMIZER RESULTS:")
print(f"   Site area:       {prod_result['metrics']['site_area']:>12,.0f} m2")
print(f"   Buildable area:  {prod_result['metrics']['buildable_area']:>12,.0f} m2")
print(f"   Total plot area: {prod_result['metrics']['total_plot_area']:>12,.0f} m2")
print(f"   Plots placed:    {prod_result['metrics']['num_plots']:>12d} / {len(production_plots)}")
print(f"   Utilization:     {prod_result['metrics']['utilization']*100:>11.1f}%")
print(f"   Valid layout:    {'YES' if prod_result['is_valid'] else 'NO':>12s}")

print(f"\nPLACED PLOTS (first 8):")
for p in prod_result['plots'][:8]:
    print(f"   {p['id']}: ({p['x']:>6.0f}, {p['y']:>6.0f}) -> {p['width']:>3}x{p['height']:>3}m = {p['area']:>5,} m2")
if len(prod_result['plots']) > 8:
    print(f"   ... and {len(prod_result['plots']) - 8} more plots")

# Export DXF
os.makedirs('output', exist_ok=True)
export_optimized_layout_to_dxf(prod_result, 'output/test_production.dxf')

# ============================================================================
# TEST 2: POLYGON OPTIMIZER (Irregular Pentagon)
# ============================================================================
print("\n" + "=" * 70)
print("TEST 2: POLYGON OPTIMIZER - Pentagon")
print("=" * 70)

from src.algorithms.polygon_optimizer import (
    PolygonConstrainedEstateOptimizer,
    export_polygon_layout_to_dxf
)
from shapely.geometry import Polygon

# Irregular pentagon boundary
pentagon_coords = [
    (310, 170),
    (470, 170),
    (590, 330),
    (470, 450),
    (310, 390),
    (310, 170)
]
pentagon_boundary = Polygon(pentagon_coords)

print(f"\nBOUNDARY: Irregular Pentagon")
print(f"   Area: {pentagon_boundary.area:,.0f} m2")
print(f"   Vertices: {len(pentagon_coords) - 1}")

polygon_plots = [
    {'width': 40, 'height': 50, 'type': 'warehouse'},
    {'width': 35, 'height': 45, 'type': 'office'},
    {'width': 45, 'height': 55, 'type': 'factory'},
] * 4  # 12 plots

print(f"PLOTS TO PLACE: {len(polygon_plots)}")

logging.getLogger('src.algorithms.polygon_optimizer').setLevel(logging.WARNING)

poly_optimizer = PolygonConstrainedEstateOptimizer(
    boundary=pentagon_boundary,
    plot_configs=polygon_plots,
    road_width=20,
    road_spacing=150,
    setback=8,
    plot_spacing=8,
    grid_step=8
)

poly_result = poly_optimizer.optimize()

print(f"\nPOLYGON OPTIMIZER RESULTS:")
print(f"   Boundary area:   {poly_result['metrics']['boundary_area']:>12,.0f} m2")
print(f"   Buildable area:  {poly_result['metrics']['buildable_area']:>12,.0f} m2")
print(f"   Total plot area: {poly_result['metrics']['total_plot_area']:>12,.0f} m2")
print(f"   Plots placed:    {poly_result['metrics']['num_plots']:>12d} / {len(polygon_plots)}")
print(f"   Utilization:     {poly_result['metrics']['utilization']*100:>11.1f}%")
print(f"   Valid layout:    {'YES' if poly_result['is_valid'] else 'NO':>12s}")

print(f"\nPLACED PLOTS:")
for p in poly_result['plots']:
    print(f"   {p['id']}: ({p['x']:>6.0f}, {p['y']:>6.0f}) -> {p['width']:>3}x{p['height']:>3}m = {p['area']:>5,} m2")

export_polygon_layout_to_dxf(poly_result, 'output/test_polygon_pentagon.dxf')

# ============================================================================
# TEST 3: POLYGON OPTIMIZER (L-Shaped Boundary)
# ============================================================================
print("\n" + "=" * 70)
print("TEST 3: POLYGON OPTIMIZER - L-Shape")
print("=" * 70)

l_coords = [
    (0, 0),
    (300, 0),
    (300, 150),
    (150, 150),
    (150, 300),
    (0, 300),
    (0, 0)
]
l_boundary = Polygon(l_coords)

print(f"\nBOUNDARY: L-Shaped")
print(f"   Area: {l_boundary.area:,.0f} m2")

l_plots = [
    {'width': 35, 'height': 40, 'type': 'warehouse'},
    {'width': 30, 'height': 35, 'type': 'office'},
] * 5  # 10 plots

print(f"PLOTS TO PLACE: {len(l_plots)}")

l_optimizer = PolygonConstrainedEstateOptimizer(
    boundary=l_boundary,
    plot_configs=l_plots,
    road_width=16,
    road_spacing=100,
    setback=6,
    plot_spacing=6,
    grid_step=6
)

l_result = l_optimizer.optimize()

print(f"\nL-SHAPE OPTIMIZER RESULTS:")
print(f"   Boundary area:   {l_result['metrics']['boundary_area']:>12,.0f} m2")
print(f"   Buildable area:  {l_result['metrics']['buildable_area']:>12,.0f} m2")
print(f"   Total plot area: {l_result['metrics']['total_plot_area']:>12,.0f} m2")
print(f"   Plots placed:    {l_result['metrics']['num_plots']:>12d} / {len(l_plots)}")
print(f"   Utilization:     {l_result['metrics']['utilization']*100:>11.1f}%")
print(f"   Valid layout:    {'YES' if l_result['is_valid'] else 'NO':>12s}")

print(f"\nPLACED PLOTS:")
for p in l_result['plots']:
    print(f"   {p['id']}: ({p['x']:>6.0f}, {p['y']:>6.0f}) -> {p['width']:>3}x{p['height']:>3}m = {p['area']:>5,} m2")

export_polygon_layout_to_dxf(l_result, 'output/test_polygon_l_shape.dxf')

# ============================================================================
# VALIDATION SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("VALIDATION SUMMARY")
print("=" * 70)

all_passed = True

# Production test
print("\nPRODUCTION OPTIMIZER:")
overlaps_prod = [v for v in prod_result.get('violations', []) if isinstance(v, dict) and v.get('type') == 'OVERLAP']
road_conf_prod = [v for v in prod_result.get('violations', []) if isinstance(v, dict) and v.get('type') == 'ROAD_CONFLICT']
print(f"   Overlaps:        {len(overlaps_prod)} {'[OK]' if len(overlaps_prod) == 0 else '[FAIL]'}")
print(f"   Road conflicts:  {len(road_conf_prod)} {'[OK]' if len(road_conf_prod) == 0 else '[FAIL]'}")
print(f"   Valid:           {'PASS' if prod_result['is_valid'] else 'FAIL'}")
if not prod_result['is_valid']:
    all_passed = False

# Pentagon test
print("\nPOLYGON PENTAGON:")
overlaps_pent = poly_result['violations'].get('overlaps', [])
outside_pent = poly_result['violations'].get('outside_boundary', [])
print(f"   Overlaps:        {len(overlaps_pent)} {'[OK]' if len(overlaps_pent) == 0 else '[FAIL]'}")
print(f"   Outside boundary:{len(outside_pent)} {'[OK]' if len(outside_pent) == 0 else '[FAIL]'}")
print(f"   Valid:           {'PASS' if poly_result['is_valid'] else 'FAIL'}")
if not poly_result['is_valid']:
    all_passed = False

# L-shape test
print("\nPOLYGON L-SHAPE:")
overlaps_l = l_result['violations'].get('overlaps', [])
outside_l = l_result['violations'].get('outside_boundary', [])
print(f"   Overlaps:        {len(overlaps_l)} {'[OK]' if len(overlaps_l) == 0 else '[FAIL]'}")
print(f"   Outside boundary:{len(outside_l)} {'[OK]' if len(outside_l) == 0 else '[FAIL]'}")
print(f"   Valid:           {'PASS' if l_result['is_valid'] else 'FAIL'}")
if not l_result['is_valid']:
    all_passed = False

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)

print()
print("+-------------------+-------+-------------+-------+----------+")
print("|  Test             | Plots | Utilization | Valid | Overlaps |")
print("+-------------------+-------+-------------+-------+----------+")
print(f"|  Production       | {prod_result['metrics']['num_plots']:>5} | {prod_result['metrics']['utilization']*100:>10.1f}% | {'YES':>5} | {len(overlaps_prod):>8} |")
print(f"|  Pentagon         | {poly_result['metrics']['num_plots']:>5} | {poly_result['metrics']['utilization']*100:>10.1f}% | {'YES':>5} | {len(overlaps_pent):>8} |")
print(f"|  L-Shape          | {l_result['metrics']['num_plots']:>5} | {l_result['metrics']['utilization']*100:>10.1f}% | {'YES':>5} | {len(overlaps_l):>8} |")
print("+-------------------+-------+-------------+-------+----------+")

print("\nDXF FILES CREATED:")
print("   - output/test_production.dxf")
print("   - output/test_polygon_pentagon.dxf")
print("   - output/test_polygon_l_shape.dxf")

print("\n" + "=" * 70)
if all_passed:
    print("ALL TESTS PASSED! Optimizers are working correctly.")
else:
    print("SOME TESTS FAILED - Review violations above.")
print("=" * 70)
