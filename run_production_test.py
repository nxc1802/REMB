"""Simple test for production optimizer - creates DXF output"""
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(level=logging.WARNING)

# Import after suppressing warnings
from src.algorithms.production_optimizer import (
    ProductionReadyEstateOptimizer, 
    export_optimized_layout_to_dxf
)
import os

print("=" * 60)
print("🧪 PRODUCTION OPTIMIZER TEST")
print("=" * 60)

# Define boundary
boundary = {
    'min_x': 0,
    'min_y': 0,
    'max_x': 500,
    'max_y': 400
}

# Plot configs
plots = [
    {'width': 60, 'height': 80, 'type': 'warehouse'},
    {'width': 50, 'height': 60, 'type': 'office'},
    {'width': 70, 'height': 90, 'type': 'factory'},
    {'width': 55, 'height': 70, 'type': 'storage'},
] * 5  # 20 plots

# Create and run optimizer
optimizer = ProductionReadyEstateOptimizer(
    boundary_coords=boundary,
    plot_configs=plots,
    road_width=24,
    road_spacing=200,
    setback=10,
    plot_spacing=10
)

# Suppress detailed logging for test
import src.algorithms.production_optimizer as po
po.logger.setLevel(logging.WARNING)

result = optimizer.optimize()

# Export DXF
os.makedirs('output', exist_ok=True)
export_optimized_layout_to_dxf(result, 'output/production_layout.dxf')

# Results
print("\n📊 RESULTS:")
print(f"   Site: 500m × 400m = 200,000 m²")
print(f"   Roads: {len(result['roads'])} segments")
print(f"   Plots placed: {result['metrics']['num_plots']} / {len(plots)}")
print(f"   Total area: {result['metrics']['total_plot_area']:,.0f} m²")
print(f"   Utilization: {result['metrics']['utilization']*100:.1f}%")

print("\n✅ VALIDATION:")
overlaps = [v for v in result['violations'] if v['type'] == 'OVERLAP']
road_conflicts = [v for v in result['violations'] if v['type'] == 'ROAD_CONFLICT']
print(f"   Valid: {'YES ✅' if result['is_valid'] else 'NO ❌'}")
print(f"   Overlaps: {len(overlaps)}")
print(f"   Road conflicts: {len(road_conflicts)}")

print("\n📍 SAMPLE PLOTS:")
for p in result['plots'][:5]:
    print(f"   {p['id']}: ({p['x']:.0f}, {p['y']:.0f}) → {p['width']}×{p['height']}m")

print("\n" + "=" * 60)
if result['is_valid'] and len(overlaps) == 0 and len(road_conflicts) == 0:
    print("🎉 ALL TESTS PASSED!")
else:
    print("⚠️ SOME ISSUES FOUND")
print("=" * 60)
print(f"\n📄 DXF saved to: output/production_layout.dxf")
