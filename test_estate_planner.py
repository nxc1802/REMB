# Test Professional Industrial Estate Planner with correct parameters
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')

from src.algorithms.industrial_estate_planner import IndustrialEstatePlanner

print("=" * 70)
print("PROFESSIONAL ESTATE PLANNER TEST")
print("=" * 70)

input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
output_file = r"D:\Gitrepo\REMB\output\Bel_Air_ESTATE_CORRECT.dxf"

planner = IndustrialEstatePlanner(input_file)

# Extract boundary first to check the size
boundary = planner.extract_boundary()
if boundary:
    print("\nBoundary info:")
    print("  Area: %.2f m2" % boundary.area)
    print("  Bounds: %.2f x %.2f m" % (
        boundary.bounds[2] - boundary.bounds[0],
        boundary.bounds[3] - boundary.bounds[1]
    ))
    
    # Calculate appropriate parameters based on area
    area = boundary.area
    
    if area < 200:
        # Very small parcel - tiny plots
        planner.setback_distance = 0.5  
        planner.road_width = 2.0        
        planner.min_plot_width = 3.0    
        planner.min_plot_height = 4.0   
        planner.plot_spacing = 0.5      
    elif area < 500:
        # Small parcel
        planner.setback_distance = 1.0  
        planner.road_width = 2.5        
        planner.min_plot_width = 4.0    
        planner.min_plot_height = 5.0   
        planner.plot_spacing = 0.75     
    elif area < 1000:
        # Medium-small parcel
        planner.setback_distance = 1.5  
        planner.road_width = 3.0        
        planner.min_plot_width = 5.0    
        planner.min_plot_height = 6.0   
        planner.plot_spacing = 1.0      
    else:
        # Normal parcel
        planner.setback_distance = 2.0  
        planner.road_width = 4.0        
        planner.min_plot_width = 6.0    
        planner.min_plot_height = 8.0   
        planner.plot_spacing = 1.0      
    
    print("\nAdaptive parameters for %.0f m2:" % area)
    print("  Setback: %.1fm" % planner.setback_distance)
    print("  Road width: %.1fm" % planner.road_width)
    print("  Min plot: %.1fm x %.1fm" % (planner.min_plot_width, planner.min_plot_height))
    print("  Spacing: %.1fm" % planner.plot_spacing)

# Run planning
result = planner.plan_estate(output_file)

print("\n" + "=" * 70)
print("RESULT SUMMARY")
print("=" * 70)
print("Status: %s" % result['status'])
print("Plots: %d" % result['metrics']['num_plots'])
print("Area: %.2f m2" % result['metrics']['total_plot_area'])
print("Utilization: %.1f%%" % result['metrics']['utilization'])
print("Valid: %s" % result['is_valid'])
print("Output: %s" % result['output'])
print("=" * 70)

# Show file sizes
import os
input_size = os.path.getsize(input_file) / 1024
output_size = os.path.getsize(output_file) / 1024
print("\nFile sizes:")
print("  Input: %.1f KB" % input_size)
print("  Output: %.1f KB" % output_size)
print("  Preservation: %.1f%%" % ((output_size/input_size)*100))
