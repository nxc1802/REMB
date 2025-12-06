# Test Cadastral Optimizer with Bel Air Lot Plan
# Since DWG requires conversion, we'll work with boundary from Image 1

import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(level=logging.WARNING)
import os

print("=" * 60)
print("CADASTRAL OPTIMIZER TEST - Bel Air Lot Plan")
print("=" * 60)

# The boundary from Image 1 (Lot Plan Bel air Technical Description.dwg)
# Based on the visible measurements and survey points in the image:
# - LOT 12 area = 541 sm (square meters)
# - Survey points 1-10
# - Edge measurements: 23.06m, 14.5m, 18.67m, etc.
# - Irregular diamond/pentagon shape

# Estimated coordinates from the image (scaled to approximate real values)
# The shape is approximately a rotated diamond/pentagon
# Using the measurements to estimate the polygon vertices

# From the image, the shape appears to be:
# - Point 1 (top): approximately at the top
# - Points 2-8 on the right side (curving down)
# - Point 9 at bottom
# - Point 10 on the left side

# Creating an approximate boundary based on LOT 12 = 541 m2
# and edge measurements shown (23.06m, 14.5m, 18.67m)

# For a polygon with area ~541 m2 and sides ~15-25m, 
# approximate coordinates (in meters, local origin):

boundary_lot12 = [
    (0, 23),       # Point 1 (top)
    (15, 22),      # Point 2 
    (20, 18),      # Point 3
    (22, 12),      # Point 4
    (22, 6),       # Point 5
    (20, 2),       # Point 6
    (15, 0),       # Point 7
    (8, 0),        # Point 8
    (0, 8),        # Point 9 (bottom left)
    (-5, 15),      # Point 10 (left side)
    (0, 23)        # Close polygon
]

# Alternative: Use the bigger combined area (LOT 11 + 12 + 13)
# The outer boundary appears to be approximately 40m x 35m based on the image
boundary_combined = [
    (0, 35),       # Top
    (30, 35),      # Top right
    (40, 20),      # Right
    (30, 0),       # Bottom right  
    (0, 5),        # Bottom left
    (-10, 20),     # Left
    (0, 35)        # Close
]

from shapely.geometry import Polygon

# Test with LOT 12 (541 m2)
poly_lot12 = Polygon(boundary_lot12)
print("\n[LOT 12 Boundary]")
print("  Area: %.1f m2 (target: 541 m2)" % poly_lot12.area)
print("  Bounds: %.1f x %.1f m" % (
    poly_lot12.bounds[2] - poly_lot12.bounds[0],
    poly_lot12.bounds[3] - poly_lot12.bounds[1]
))

# Test with combined area
poly_combined = Polygon(boundary_combined)
print("\n[Combined LOT 11+12+13 Boundary]")
print("  Area: %.1f m2" % poly_combined.area)

# Use the combined boundary for more space
from src.algorithms.cadastral_optimizer import (
    AdaptiveParameterCalculator,
    CadastralPolygonOptimizer,
    export_cadastral_layout_dxf
)

# Calculate parameters based on actual area
area = poly_combined.area
params = AdaptiveParameterCalculator.calculate(area)

print("\n[Adaptive Parameters for %.0f m2]" % area)
print("  Size class: %s" % params['size_class'])
print("  Plot size: %d-%dm x %d-%dm" % (
    params['plot_min_width'], params['plot_max_width'],
    params['plot_min_height'], params['plot_max_height']
))
print("  Grid step: %.1fm" % params['grid_step'])
print("  Road width: %.1fm" % params['road_width'])
print("  Max plots: %d" % params['max_plots'])

# Generate appropriate plot configs
plots = AdaptiveParameterCalculator.generate_plots(area, params)
print("\n[Generated Plot Configs]")
print("  Total: %d plots" % len(plots))
for p in plots[:5]:
    print("    - %dx%dm = %d m2" % (p['width'], p['height'], p['area']))

# Run optimizer
print("\n[Running Optimization]")
optimizer = CadastralPolygonOptimizer(poly_combined, plots, params)
result = optimizer.optimize()

print("  Plots placed: %d/%d" % (result['metrics']['num_plots'], len(plots)))
print("  Total area: %.0f m2" % result['metrics']['total_plot_area'])
print("  Utilization: %.1f%%" % result['metrics']['utilization_percent'])
print("  Valid: %s" % result['is_valid'])

# Export DXF
os.makedirs('output', exist_ok=True)
export_cadastral_layout_dxf(result, 'output/bel_air_optimized.dxf')

print("\n[Placed Plots]")
for p in result['plots']:
    print("  %s: (%.1f, %.1f) -> %dx%dm" % (p['id'], p['x'], p['y'], p['width'], p['height']))

print("\n" + "=" * 60)
print("DXF EXPORTED: output/bel_air_optimized.dxf")
print("=" * 60)

# Also test with the smaller LOT 12
print("\n\n" + "=" * 60)
print("TEST 2: LOT 12 ONLY (541 m2)")
print("=" * 60)

area2 = poly_lot12.area
params2 = AdaptiveParameterCalculator.calculate(area2)
plots2 = AdaptiveParameterCalculator.generate_plots(area2, params2)

print("[Parameters for %.0f m2]" % area2)
print("  Size class: %s" % params2['size_class'])
print("  Plots generated: %d" % len(plots2))

optimizer2 = CadastralPolygonOptimizer(poly_lot12, plots2, params2)
result2 = optimizer2.optimize()

print("[Results]")
print("  Plots placed: %d" % result2['metrics']['num_plots'])
print("  Utilization: %.1f%%" % result2['metrics']['utilization_percent'])

export_cadastral_layout_dxf(result2, 'output/bel_air_lot12_only.dxf')

print("\n" + "=" * 60)
print("COMPLETE! Check:")
print("  - output/bel_air_optimized.dxf (combined lots)")
print("  - output/bel_air_lot12_only.dxf (LOT 12 only)")
print("=" * 60)
