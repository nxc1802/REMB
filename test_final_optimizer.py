# Final improved optimizer test
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import os

print("=" * 60)
print("FINAL IMPROVED ESTATE OPTIMIZER TEST")
print("=" * 60)

from src.algorithms.advanced_estate_optimizer import AdvancedEstateOptimizer

input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
output_file = r"D:\Gitrepo\REMB\output\Bel_Air_FINAL.dxf"

optimizer = AdvancedEstateOptimizer(input_file)

# Extract boundary first to get the area
boundary = optimizer.extract_boundary()
if boundary:
    area = boundary.area
    print("\nBoundary: %.2f m2" % area)
    
    # ADAPTIVE PARAMETERS based on area
    # For ~600 m2, use smaller parameters
    if area < 300:
        optimizer.setback_distance = 0.5
        optimizer.main_road_width = 2.0
        optimizer.secondary_road_width = 1.5
        optimizer.plot_width = 3.0
        optimizer.plot_height = 4.0
        optimizer.plot_spacing = 0.5
    elif area < 800:
        # This is for the Bel Air parcel (~600 m2)
        optimizer.setback_distance = 0.8
        optimizer.main_road_width = 2.5
        optimizer.secondary_road_width = 2.0
        optimizer.plot_width = 4.0
        optimizer.plot_height = 5.0
        optimizer.plot_spacing = 0.7
    elif area < 2000:
        optimizer.setback_distance = 1.0
        optimizer.main_road_width = 3.0
        optimizer.secondary_road_width = 2.0
        optimizer.plot_width = 5.0
        optimizer.plot_height = 6.0
        optimizer.plot_spacing = 1.0
    else:
        optimizer.setback_distance = 2.0
        optimizer.main_road_width = 6.0
        optimizer.secondary_road_width = 4.0
        optimizer.plot_width = 8.0
        optimizer.plot_height = 10.0
        optimizer.plot_spacing = 1.5
    
    print("\nAdaptive parameters for %.0f m2:" % area)
    print("  Setback: %.1fm" % optimizer.setback_distance)
    print("  Main road: %.1fm" % optimizer.main_road_width)
    print("  Plot size: %.1fm x %.1fm" % (optimizer.plot_width, optimizer.plot_height))
    print("  Spacing: %.1fm" % optimizer.plot_spacing)

# Apply buffer
print("\n" + "-" * 40)
print("Applying buffer zone...")
optimizer.apply_buffer_zone()

# Create roads
print("\nCreating road network...")
optimizer.create_diagonal_main_road()
optimizer.create_secondary_roads(spacing=12.0)  # Smaller spacing

# Calculate usable zones
print("\nCalculating usable zones...")
optimizer.calculate_usable_zones()

# Generate plots
print("\nGenerating plots...")
optimizer.generate_rotated_plots()

# Get metrics
metrics = optimizer.get_metrics()
print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print("  Boundary area:  %.2f m2" % metrics['boundary_area'])
print("  Usable area:    %.2f m2" % metrics['usable_area'])
print("  Plots:          %d" % metrics['num_plots'])
print("  Plot area:      %.2f m2" % metrics['total_plot_area'])
print("  Utilization:    %.1f%%" % metrics['utilization'])
print("  Overall util:   %.1f%%" % metrics['overall_util'])

# Show plot details
if optimizer.plots:
    print("\nPlots placed:")
    for i, p in enumerate(optimizer.plots[:10]):
        print("  %s: (%.1f, %.1f) %.0fx%.0fm" % (
            p['id'], p['x'], p['y'], p['width'], p['height']))
    if len(optimizer.plots) > 10:
        print("  ... and %d more" % (len(optimizer.plots) - 10))

# Export
print("\n" + "-" * 40)
print("Exporting DXF...")
optimizer.export_dxf(output_file)

# Verify file sizes
input_size = os.path.getsize(input_file) / 1024
output_size = os.path.getsize(output_file) / 1024

print("\n" + "=" * 60)
print("COMPLETE")
print("=" * 60)
print("  Input:  %.1f KB" % input_size)
print("  Output: %.1f KB (%.1f%% preserved)" % (output_size, output_size/input_size*100))
print("  File:   %s" % output_file)
print("=" * 60)
