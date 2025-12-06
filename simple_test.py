# Simple test script
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import logging
logging.basicConfig(level=logging.ERROR)
import os

print("FULL FLOW TEST")
print("=" * 50)

# Test 1: Production Optimizer
print("\n[TEST 1] Production Optimizer")
from src.algorithms.production_optimizer import ProductionReadyEstateOptimizer, export_optimized_layout_to_dxf

boundary = {'min_x': 0, 'min_y': 0, 'max_x': 500, 'max_y': 400}
plots = [{'width': 60, 'height': 80}, {'width': 50, 'height': 60}, {'width': 70, 'height': 90}] * 5

opt = ProductionReadyEstateOptimizer(boundary, plots, road_width=24, road_spacing=200)
r = opt.optimize()

print("  Plots placed: %d / %d" % (r['metrics']['num_plots'], len(plots)))
print("  Total area: %.0f m2" % r['metrics']['total_plot_area'])
print("  Utilization: %.1f%%" % (r['metrics']['utilization']*100))
print("  Valid: %s" % r['is_valid'])

os.makedirs('output', exist_ok=True)
export_optimized_layout_to_dxf(r, 'output/final_production.dxf')

# Test 2: Polygon Optimizer
print("\n[TEST 2] Polygon Optimizer (Pentagon)")
from src.algorithms.polygon_optimizer import PolygonConstrainedEstateOptimizer, export_polygon_layout_to_dxf
from shapely.geometry import Polygon

poly = Polygon([(310,170),(470,170),(590,330),(470,450),(310,390),(310,170)])
plots2 = [{'width': 40, 'height': 50}, {'width': 35, 'height': 45}] * 5

opt2 = PolygonConstrainedEstateOptimizer(poly, plots2, road_spacing=150, grid_step=8)
r2 = opt2.optimize()

print("  Plots placed: %d / %d" % (r2['metrics']['num_plots'], len(plots2)))
print("  Total area: %.0f m2" % r2['metrics']['total_plot_area'])
print("  Utilization: %.1f%%" % (r2['metrics']['utilization']*100))
print("  Valid: %s" % r2['is_valid'])

export_polygon_layout_to_dxf(r2, 'output/final_polygon.dxf')

# Summary
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
print("  Production: %d plots, %.1f%% util, valid=%s" % (
    r['metrics']['num_plots'], 
    r['metrics']['utilization']*100, 
    r['is_valid']))
print("  Polygon: %d plots, %.1f%% util, valid=%s" % (
    r2['metrics']['num_plots'], 
    r2['metrics']['utilization']*100, 
    r2['is_valid']))

v1 = [v for v in r.get('violations',[]) if isinstance(v,dict) and v.get('type')=='OVERLAP']
v2 = r2['violations'].get('overlaps', [])
print("  Overlaps: Prod=%d, Poly=%d" % (len(v1), len(v2)))

print("\nDXF FILES:")
print("  output/final_production.dxf")
print("  output/final_polygon.dxf")

print("\n" + "=" * 50)
if r['is_valid'] and r2['is_valid'] and len(v1)==0 and len(v2)==0:
    print("ALL TESTS PASSED!")
else:
    print("TESTS FAILED")
print("=" * 50)
