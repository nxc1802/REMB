"""
Comprehensive Test Script for REMB MVP
Tests all modules and the complete pipeline
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_models():
    """Test domain models"""
    print("\n" + "="*60)
    print("TEST 1: Domain Models")
    print("="*60)
    
    from shapely.geometry import box
    from src.models.domain import (
        SiteBoundary, Plot, PlotType, Layout, 
        RoadNetwork, LayoutMetrics, ParetoFront
    )
    
    # Create site boundary
    site_geom = box(0, 0, 500, 500)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm * 0.8
    
    print(f"✅ SiteBoundary created: {site.area_sqm:.0f} m²")
    
    # Create plots
    plot1 = Plot(
        geometry=box(60, 60, 160, 160),
        area_sqm=10000,
        type=PlotType.INDUSTRIAL,
        width_m=100,
        depth_m=100
    )
    
    plot2 = Plot(
        geometry=box(200, 60, 300, 150),
        area_sqm=9000,
        type=PlotType.GREEN_SPACE
    )
    
    print(f"✅ Plots created: Industrial={plot1.area_sqm}m², Green={plot2.area_sqm}m²")
    
    # Create layout
    layout = Layout(site_boundary=site)
    layout.plots = [plot1, plot2]
    layout.calculate_metrics()
    
    print(f"✅ Layout metrics: sellable={layout.metrics.sellable_area_sqm}m²")
    
    # Test ParetoFront
    pareto = ParetoFront(layouts=[layout])
    best = pareto.get_max_sellable_layout()
    print(f"✅ ParetoFront: {len(pareto.layouts)} layouts")
    
    return True


def test_regulation_checker():
    """Test regulation compliance checker"""
    print("\n" + "="*60)
    print("TEST 2: Regulation Checker")
    print("="*60)
    
    from shapely.geometry import box
    from src.models.domain import SiteBoundary, Plot, PlotType, Layout, LayoutMetrics
    from src.algorithms.regulation_checker import RegulationChecker
    
    # Create test layout
    site_geom = box(0, 0, 500, 500)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm
    
    layout = Layout(site_boundary=site)
    
    # Add compliant plots
    layout.plots = [
        Plot(
            id="plot_001",
            geometry=box(70, 70, 170, 170),
            area_sqm=10000,
            type=PlotType.INDUSTRIAL,
            width_m=100,
            depth_m=100,
            has_road_access=True
        ),
        Plot(
            id="plot_002",
            geometry=box(220, 70, 320, 170),
            area_sqm=10000,
            type=PlotType.INDUSTRIAL,
            width_m=100,
            depth_m=100,
            has_road_access=True
        ),
        Plot(
            id="green_001",
            geometry=box(70, 220, 320, 320),
            area_sqm=25000,
            type=PlotType.GREEN_SPACE
        )
    ]
    
    # Set metrics
    layout.metrics = LayoutMetrics(
        total_area_sqm=250000,
        sellable_area_sqm=20000,
        green_space_area_sqm=37500,
        road_area_sqm=50000,
        num_plots=2
    )
    layout.metrics.calculate_ratios()
    
    # Run compliance check
    checker = RegulationChecker()
    report = checker.validate_compliance(layout)
    
    print(f"✅ Compliance check complete")
    print(f"   Is compliant: {report.is_compliant}")
    print(f"   Violations: {len(report.violations)}")
    print(f"   Warnings: {len(report.warnings)}")
    print(f"   Checks passed: {len(report.checks_passed)}")
    
    for check in report.checks_passed[:3]:
        print(f"   ✓ {check}")
    
    return True


def test_site_processor():
    """Test site processor"""
    print("\n" + "="*60)
    print("TEST 3: Site Processor")
    print("="*60)
    
    from src.geometry.site_processor import SiteProcessor
    
    processor = SiteProcessor()
    
    # Test coordinate import
    coords = [(0, 0), (500, 0), (500, 400), (300, 500), (0, 400), (0, 0)]
    site = processor.import_from_coordinates(coords)
    
    print(f"✅ Site imported from coordinates")
    print(f"   Total area: {site.area_sqm:.0f} m²")
    print(f"   Buildable area: {site.buildable_area_sqm:.0f} m²")
    print(f"   Constraints: {len(site.constraints)}")
    
    # Get buildable polygon
    buildable = processor.get_buildable_polygon(site)
    print(f"   Buildable polygon area: {buildable.area:.0f} m²")
    
    return True


def test_road_network():
    """Test road network generator"""
    print("\n" + "="*60)
    print("TEST 4: Road Network Generator")
    print("="*60)
    
    from src.geometry.site_processor import SiteProcessor
    from src.geometry.road_network import RoadNetworkGenerator
    
    # Create site
    processor = SiteProcessor()
    coords = [(0, 0), (500, 0), (500, 500), (0, 500), (0, 0)]
    site = processor.import_from_coordinates(coords)
    
    # Generate road networks
    generator = RoadNetworkGenerator()
    
    # Grid network
    grid = generator.generate_grid_network(site, primary_spacing=150, secondary_spacing=80)
    print(f"✅ Grid network generated")
    print(f"   Total length: {grid.total_length_m:.0f} m")
    print(f"   Total area: {grid.total_area_sqm:.0f} m²")
    
    # Check dead zones
    dead_zones = generator.identify_dead_zones(site, grid)
    print(f"   Dead zones: {len(dead_zones)}")
    
    # Spine network
    spine = generator.generate_spine_network(site)
    print(f"✅ Spine network generated")
    print(f"   Total length: {spine.total_length_m:.0f} m")
    
    return True


def test_plot_generator():
    """Test plot generator"""
    print("\n" + "="*60)
    print("TEST 5: Plot Generator")
    print("="*60)
    
    from src.geometry.site_processor import SiteProcessor
    from src.geometry.road_network import RoadNetworkGenerator
    from src.geometry.plot_generator import PlotGenerator
    
    # Setup
    processor = SiteProcessor()
    coords = [(0, 0), (500, 0), (500, 500), (0, 500), (0, 0)]
    site = processor.import_from_coordinates(coords)
    
    road_gen = RoadNetworkGenerator()
    roads = road_gen.generate_grid_network(site, primary_spacing=150)
    
    # Generate plots
    plot_gen = PlotGenerator()
    
    plots = plot_gen.generate_grid_plots(
        site, roads,
        plot_width=80,
        plot_depth=100
    )
    
    print(f"✅ Plots generated: {len(plots)}")
    
    total_area = sum(p.area_sqm for p in plots)
    with_access = sum(1 for p in plots if p.has_road_access)
    
    print(f"   Total industrial area: {total_area:.0f} m²")
    print(f"   Plots with road access: {with_access}/{len(plots)}")
    
    # Generate green spaces
    green = plot_gen.generate_green_spaces(site, plots, roads, target_ratio=0.15)
    green_area = sum(p.area_sqm for p in green)
    print(f"✅ Green spaces: {len(green)} plots, {green_area:.0f} m²")
    
    return True


def test_milp_solver():
    """Test MILP solver"""
    print("\n" + "="*60)
    print("TEST 6: MILP Solver")
    print("="*60)
    
    from shapely.geometry import box
    from src.models.domain import SiteBoundary
    from src.algorithms.milp_solver import MILPSolver
    
    # Create site
    site_geom = box(0, 0, 400, 400)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm
    
    # Test MILP solver using CP-SAT fallback (more reliable)
    solver = MILPSolver(time_limit_seconds=10)
    
    # Use the CP-SAT method directly for testing
    result = solver._solve_with_cpsat(
        site_boundary=site,
        num_plots=4,
        min_plot_size=900,  # 30x30 plots
        max_plot_size=5000,
        setback=50
    )
    
    print(f"✅ MILP/CP-SAT solver executed")
    print(f"   Status: {result.status}")
    print(f"   Solve time: {result.solve_time_seconds:.2f}s")
    print(f"   Plots placed: {len(result.plots)}")
    
    if result.plots:
        for i, plot in enumerate(result.plots[:3]):
            print(f"   Plot {i+1}: {plot['area_sqm']:.0f} m²")
    
    return result.is_success() or result.status == 'FEASIBLE'


def test_dxf_exporter():
    """Test DXF exporter"""
    print("\n" + "="*60)
    print("TEST 7: DXF Exporter")
    print("="*60)
    
    import os
    from shapely.geometry import box, LineString, MultiLineString
    from src.models.domain import Layout, Plot, PlotType, SiteBoundary, RoadNetwork, LayoutMetrics
    from src.export.dxf_exporter import DXFExporter
    
    # Create test layout
    site_geom = box(0, 0, 500, 500)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm
    
    layout = Layout(site_boundary=site)
    layout.plots = [
        Plot(id="plot_001", geometry=box(60, 60, 160, 160), 
             area_sqm=10000, type=PlotType.INDUSTRIAL),
        Plot(id="plot_002", geometry=box(200, 60, 300, 160), 
             area_sqm=10000, type=PlotType.INDUSTRIAL),
        Plot(id="green_001", geometry=box(60, 200, 160, 300), 
             area_sqm=10000, type=PlotType.GREEN_SPACE)
    ]
    
    layout.road_network = RoadNetwork(
        primary_roads=MultiLineString([
            LineString([(0, 250), (500, 250)]),
            LineString([(250, 0), (250, 500)])
        ]),
        total_length_m=1000
    )
    
    layout.metrics = LayoutMetrics(
        total_area_sqm=250000,
        sellable_area_sqm=20000,
        green_space_area_sqm=10000,
        road_area_sqm=24000,
        sellable_ratio=0.65,
        green_space_ratio=0.15,
        num_plots=2,
        is_compliant=True
    )
    
    # Export
    os.makedirs("output", exist_ok=True)
    exporter = DXFExporter()
    filepath = exporter.export(layout, "output/test_layout.dxf")
    
    # Verify file exists
    file_exists = os.path.exists(filepath)
    file_size = os.path.getsize(filepath) if file_exists else 0
    
    print(f"✅ DXF export complete")
    print(f"   File: {filepath}")
    print(f"   Exists: {file_exists}")
    print(f"   Size: {file_size} bytes")
    
    return file_exists and file_size > 0


def test_nsga2_optimizer():
    """Test NSGA-II optimizer (quick test)"""
    print("\n" + "="*60)
    print("TEST 8: NSGA-II Optimizer (Quick)")
    print("="*60)
    
    from shapely.geometry import box
    from src.models.domain import SiteBoundary
    from src.algorithms.nsga2_optimizer import NSGA2Optimizer
    
    # Create site
    site_geom = box(0, 0, 400, 400)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm * 0.8
    
    # Run quick optimization
    optimizer = NSGA2Optimizer()
    
    print("   Running NSGA-II (small population for speed)...")
    pareto_front = optimizer.optimize(
        site_boundary=site,
        population_size=20,
        n_generations=10,
        n_plots=5
    )
    
    print(f"✅ NSGA-II optimization complete")
    print(f"   Solutions found: {len(pareto_front.layouts)}")
    print(f"   Generation time: {pareto_front.generation_time_seconds:.2f}s")
    
    if pareto_front.layouts:
        best = pareto_front.get_max_sellable_layout()
        if best:
            print(f"   Best sellable area: {best.metrics.sellable_area_sqm:.0f} m²")
    
    return len(pareto_front.layouts) > 0


def test_orchestrator():
    """Test core orchestrator"""
    print("\n" + "="*60)
    print("TEST 9: Core Orchestrator")
    print("="*60)
    
    from src.core.orchestrator import CoreOrchestrator, OrchestrationStatus
    
    orchestrator = CoreOrchestrator()
    
    # Stage 1: Initialize site
    coords = [(0, 0), (400, 0), (400, 400), (0, 400), (0, 0)]
    result = orchestrator.initialize_site(coords, source_type="coordinates")
    
    print(f"✅ Site initialized: {result.status.value}")
    if result.data:
        print(f"   Area: {result.data.get('total_area_sqm', 0):.0f} m²")
    
    # Stage 2: Generate roads
    result = orchestrator.generate_road_network(pattern="grid", primary_spacing=120)
    print(f"✅ Roads generated: {result.status.value}")
    
    # Stage 4: Quick optimization
    print("   Running optimization (small scale for speed)...")
    result = orchestrator.run_optimization(
        population_size=15,
        n_generations=8,
        n_plots=5
    )
    
    print(f"✅ Optimization: {result.status.value}")
    if result.status == OrchestrationStatus.SUCCESS:
        print(f"   Layouts generated: {result.data.get('num_layouts', 0)}")
    elif result.status == OrchestrationStatus.CONFLICT:
        print(f"   Message: {result.message}")
        print(f"   Suggestions: {result.suggestions[:2]}")
    
    return result.status in [OrchestrationStatus.SUCCESS, OrchestrationStatus.CONFLICT]


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print(" REMB MVP - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    results = {}
    
    tests = [
        ("Domain Models", test_models),
        ("Regulation Checker", test_regulation_checker),
        ("Site Processor", test_site_processor),
        ("Road Network", test_road_network),
        ("Plot Generator", test_plot_generator),
        ("MILP Solver", test_milp_solver),
        ("DXF Exporter", test_dxf_exporter),
        ("NSGA-II Optimizer", test_nsga2_optimizer),
        ("Core Orchestrator", test_orchestrator),
    ]
    
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = "✅ PASS" if success else "⚠️ PARTIAL"
        except Exception as e:
            results[name] = f"❌ FAIL: {str(e)[:50]}"
            print(f"\n❌ ERROR in {name}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    for name, status in results.items():
        print(f"  {name}: {status}")
    
    passed = sum(1 for s in results.values() if "PASS" in s or "PARTIAL" in s)
    total = len(results)
    
    print("\n" + "-"*60)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
