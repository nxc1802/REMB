# Complete Optimization with Millimeter to Meter Conversion
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import os
import ezdxf
from shapely.geometry import Polygon
from shapely.affinity import scale

dxf_path = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"

print("=" * 60)
print("BEL AIR CADASTRAL OPTIMIZATION")
print("=" * 60)

# Load DXF
doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

# Extract all polylines
polylines = []
for entity in msp.query('LWPOLYLINE'):
    coords = [(p[0], p[1]) for p in entity.get_points('xy')]
    if len(coords) >= 3:
        try:
            poly = Polygon(coords)
            if poly.is_valid and poly.area > 1000:  # Filter small objects
                polylines.append({
                    'layer': entity.dxf.layer,
                    'polygon': poly,
                    'area_mm2': poly.area,
                    'is_closed': entity.is_closed
                })
        except:
            pass

# Sort by area and get largest (the boundary)
polylines.sort(key=lambda x: x['area_mm2'], reverse=True)
boundary_mm = polylines[0]['polygon'] if polylines else None

if boundary_mm is None:
    print("ERROR: No boundary found!")
    sys.exit(1)

# Convert from millimeters to meters
# Scale factor: 1 meter = 1000 mm, so divide by 1000
boundary_m = scale(boundary_mm, xfact=0.001, yfact=0.001, origin=(0, 0))

print("\nBoundary extracted:")
print("  Layer: %s" % polylines[0]['layer'])
print("  Original area: %.0f mm2" % polylines[0]['area_mm2'])
print("  Converted area: %.2f m2" % boundary_m.area)

minx, miny, maxx, maxy = boundary_m.bounds
print("  Size: %.2f m x %.2f m" % (maxx - minx, maxy - miny))

# Extract survey points and convert
survey_points = {}
for entity in msp.query('TEXT'):
    try:
        text = entity.dxf.text.strip()
        if text.isdigit() and 1 <= int(text) <= 100:
            x, y, _ = entity.dxf.insert
            # Convert mm to m
            survey_points[int(text)] = {'x': x/1000, 'y': y/1000}
    except:
        pass

print("\nSurvey points found: %d" % len(survey_points))

# Now run optimization
from src.algorithms.cadastral_optimizer import (
    AdaptiveParameterCalculator,
    CadastralPolygonOptimizer,
    export_cadastral_layout_dxf
)

area = boundary_m.area
params = AdaptiveParameterCalculator.calculate(area)

print("\n" + "-" * 40)
print("Parameters for %.2f m2 (%s):" % (area, params['size_class']))
print("  Plot sizes: %d-%dm x %d-%dm" % (
    params['plot_min_width'], params['plot_max_width'],
    params['plot_min_height'], params['plot_max_height']
))
print("  Grid step: %.1fm" % params['grid_step'])
print("  Max plots: %d" % params['max_plots'])

# Generate plots
plots = AdaptiveParameterCalculator.generate_plots(area, params)
print("\nGenerated %d plot configurations" % len(plots))

# Optimize
print("\nRunning optimization...")
optimizer = CadastralPolygonOptimizer(boundary_m, plots, params)
result = optimizer.optimize()

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print("  Boundary area:   %.2f m2" % result['metrics']['boundary_area'])
print("  Plots placed:    %d / %d" % (result['metrics']['num_plots'], len(plots)))
print("  Total plot area: %.2f m2" % result['metrics']['total_plot_area'])
print("  Utilization:     %.1f%%" % result['metrics']['utilization_percent'])
print("  Valid layout:    %s" % ("YES" if result['is_valid'] else "NO"))

print("\nPlots:")
for p in result['plots']:
    print("  %s: (%.2f, %.2f) %dx%dm = %dm2" % (
        p['id'], p['x'], p['y'], p['width'], p['height'], p['area']
    ))

# Export
os.makedirs('output', exist_ok=True)
output_path = 'output/Bel_Air_REAL_OPTIMIZED.dxf'
export_cadastral_layout_dxf(result, output_path, survey_points)

print("\n" + "=" * 60)
print("COMPLETE!")
print("  Input:  %s" % dxf_path)
print("  Output: %s" % output_path)
print("  Area:   %.2f m2" % area)
print("  Plots:  %d" % result['metrics']['num_plots'])
print("  Util:   %.1f%%" % result['metrics']['utilization_percent'])
print("=" * 60)
