"""
Full Flow Test: Boundary → Optimization → DXF Export
Tests the complete pipeline and generates a real DXF output file.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shapely.geometry import Polygon, box, LineString, MultiLineString
from src.algorithms.ga_optimizer import SimpleGAOptimizer
from src.algorithms.remb_optimizer import REMBOptimizer
from src.export.dxf_exporter import DXFExporter
from src.models.domain import Layout, Plot, PlotType, SiteBoundary, RoadNetwork, LayoutMetrics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_full_flow_test():
    """Run complete optimization pipeline and export DXF"""
    
    print("\n" + "="*70)
    print("REMB FULL FLOW TEST")
    print("="*70)
    
    # =========================================================================
    # STEP 1: Define Site Boundary (500m x 400m industrial estate)
    # =========================================================================
    print("\n📍 STEP 1: Define Site Boundary")
    
    boundary_coords = [
        [0, 0], [500, 0], [500, 400], [0, 400], [0, 0]
    ]
    
    site_polygon = Polygon(boundary_coords)
    print(f"   Site area: {site_polygon.area:,.0f} m² ({site_polygon.area/10000:.2f} ha)")
    print(f"   Dimensions: 500m × 400m")
    
    # =========================================================================
    # STEP 2: Run GA Optimization
    # =========================================================================
    print("\n⚙️ STEP 2: Running GA Optimization...")
    
    optimizer = SimpleGAOptimizer(
        population_size=20,
        n_generations=30,
        elite_size=3,
        mutation_rate=0.3,
        setback=50.0,
        target_plots=8
    )
    
    options = optimizer.optimize(boundary_coords)
    
    print(f"   Generated {len(options)} layout options:")
    for opt in options:
        metrics = opt['metrics']
        print(f"   - {opt['name']}: {metrics['total_plots']} plots, "
              f"{metrics['total_area']:,.0f} m², fitness={metrics['fitness']:.3f}")
    
    # =========================================================================
    # STEP 3: Select Best Option & Create Layout Object
    # =========================================================================
    print("\n📊 STEP 3: Selecting Best Layout (Maximum Profit)")
    
    best_option = options[0]  # Maximum Profit
    
    # Create Layout object for DXF export
    site = SiteBoundary(geometry=site_polygon, area_sqm=site_polygon.area)
    site.buildable_area_sqm = site_polygon.buffer(-50).area
    
    layout = Layout(site_boundary=site)
    
    # Convert plots from dict to Plot objects
    for i, plot_dict in enumerate(best_option['plots']):
        plot_geom = box(
            plot_dict['x'], 
            plot_dict['y'], 
            plot_dict['x'] + plot_dict['width'], 
            plot_dict['y'] + plot_dict['height']
        )
        
        plot = Plot(
            id=f"PLOT_{i+1:03d}",
            geometry=plot_geom,
            area_sqm=plot_dict['area'],
            type=PlotType.INDUSTRIAL,
            width_m=plot_dict['width'],
            depth_m=plot_dict['height'],
            has_road_access=True
        )
        layout.plots.append(plot)
    
    # Add simple road network
    roads = MultiLineString([
        LineString([(0, 200), (500, 200)]),   # Horizontal main road
        LineString([(250, 0), (250, 400)]),   # Vertical main road
    ])
    
    layout.road_network = RoadNetwork(
        primary_roads=roads,
        total_length_m=900,
        total_area_sqm=900 * 24  # 24m road width
    )
    
    # Calculate metrics
    layout.metrics = LayoutMetrics(
        total_area_sqm=site_polygon.area,
        sellable_area_sqm=best_option['metrics']['total_area'],
        green_space_area_sqm=site_polygon.area * 0.15,
        road_area_sqm=900 * 24,
        num_plots=len(layout.plots),
        is_compliant=True
    )
    layout.metrics.calculate_ratios()
    
    print(f"   Layout created with {len(layout.plots)} plots")
    print(f"   Total sellable area: {layout.metrics.sellable_area_sqm:,.0f} m²")
    
    # =========================================================================
    # STEP 4: Export to DXF
    # =========================================================================
    print("\n📤 STEP 4: Exporting to DXF...")
    
    os.makedirs("output", exist_ok=True)
    output_path = "output/full_flow_test_layout.dxf"
    
    exporter = DXFExporter()
    filepath = exporter.export(layout, output_path)
    
    file_size = os.path.getsize(filepath)
    print(f"   ✅ DXF exported: {filepath}")
    print(f"   File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    # =========================================================================
    # STEP 5: Verify DXF Contents
    # =========================================================================
    print("\n🔍 STEP 5: Verifying DXF Contents...")
    
    import ezdxf
    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    
    # Count entities by type
    entity_counts = {}
    for entity in msp:
        entity_type = entity.dxftype()
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
    
    print("   DXF Entities:")
    for etype, count in sorted(entity_counts.items()):
        print(f"   - {etype}: {count}")
    
    # Check layers
    print("\n   DXF Layers:")
    for layer in doc.layers:
        print(f"   - {layer.dxf.name}")
    
    # =========================================================================
    # STEP 6: Summary
    # =========================================================================
    print("\n" + "="*70)
    print("📋 FULL FLOW TEST SUMMARY")
    print("="*70)
    
    summary = {
        "Site Area": f"{site_polygon.area:,.0f} m²",
        "Buildable Area": f"{site.buildable_area_sqm:,.0f} m²",
        "Number of Plots": len(layout.plots),
        "Sellable Area": f"{layout.metrics.sellable_area_sqm:,.0f} m²",
        "Sellable Ratio": f"{layout.metrics.sellable_ratio*100:.1f}%",
        "DXF File": filepath,
        "DXF Size": f"{file_size:,} bytes",
        "DXF Entities": sum(entity_counts.values())
    }
    
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n✅ FULL FLOW TEST COMPLETED SUCCESSFULLY!")
    print("="*70)
    
    return filepath, layout, summary


if __name__ == "__main__":
    filepath, layout, summary = run_full_flow_test()
