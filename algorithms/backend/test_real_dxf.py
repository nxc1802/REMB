"""
Test script to run aesthetic optimization on real DXF example.
Target: examples/663409.dxf
"""

import os
import sys
import logging

# Add current directory to path
sys.path.append(os.getcwd())

from utils.dxf_utils import load_boundary_from_dxf
from pipeline.land_redistribution import LandRedistributionPipeline
from core.geometry.shape_quality import analyze_shape_quality

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dxf_optimization():
    dxf_path = "../../examples/663409.dxf"
    
    if not os.path.exists(dxf_path):
        logger.error(f"DXF file not found: {dxf_path}")
        return
    
    logger.info(f"Loading DXF: {dxf_path}")
    with open(dxf_path, 'rb') as f:
        dxf_content = f.read()
        
    land_poly = load_boundary_from_dxf(dxf_content)
    
    if not land_poly:
        logger.error("Failed to load polygon from DXF")
        return
        
    logger.info(f"Loaded land polygon: {land_poly.area:.2f} m²")
    
    # Simplify geometry to speed up testing
    land_poly = land_poly.simplify(1.0, preserve_topology=True)
    
    # Initialize pipeline
    config = {
        'min_lot_width': 20.0,
        'target_lot_width': 40.0,
        'population_size': 10,  # Speed up
        'generations': 5,       # Speed up
        'ortools_time_limit': 5.0
    }
    
    pipeline = LandRedistributionPipeline([land_poly], config)
    
    # Run full pipeline with GRID method (Orthogonal Alignment)
    logger.info("Running optimization pipeline with GRID method...")
    result = pipeline.run_full_pipeline(layout_method='grid')
    
    # Analyze Aesthetic Metrics
    stage2 = result.get('stage2', {})
    lots = stage2.get('lots', [])
    green_spaces = stage2.get('green_spaces', [])
    parks = stage2.get('parks', [])
    
    print("\n" + "="*50)
    print("AESTHETIC OPTIMIZATION RESULTS (GRID MODE)")
    print("="*50)
    
    print(f"Total Commercial Lots: {len(lots)}")
    print(f"Total Green Spaces (Leftovers): {len(green_spaces)}")
    
    # Calculate quality metrics
    rectangularities = []
    
    for lot_info in lots:
        geom = lot_info['geometry']
        obb = geom.minimum_rotated_rectangle
        rectangularity = geom.area / obb.area
        rectangularities.append(rectangularity)
            
    if rectangularities:
        avg_rect = sum(rectangularities) / len(rectangularities)
        print(f"  Average Rectangularity:  {avg_rect:.3f} (target > 0.75)")
        
        perfect_rects = sum(1 for r in rectangularities if r > 0.95)
        print(f"  Perfect Rectangles (>0.95): {perfect_rects} ({perfect_rects/len(lots)*100:.1f}%)")
    else:
        print("\nNo commercial lots generated!")

if __name__ == "__main__":
    test_dxf_optimization()
