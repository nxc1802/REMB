"""Simple test script to verify backend installation and basic functionality."""

import sys
import traceback

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    try:
        import fastapi
        import uvicorn
        import pydantic
        import numpy
        import shapely
        import matplotlib
        import ortools
        import deap
        
        # Test new module imports
        from core.optimization.grid_optimizer import GridOptimizer
        from core.optimization.subdivision_solver import SubdivisionSolver
        from pipeline.land_redistribution import LandRedistributionPipeline
        
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_algorithm():
    """Test basic algorithm functionality."""
    print("\nTesting algorithm...")
    try:
        from shapely.geometry import Polygon
        from core.optimization.grid_optimizer import GridOptimizer
        from core.optimization.subdivision_solver import SubdivisionSolver
        
        # Create simple test polygon
        land_poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        
        # Test grid optimizer
        optimizer = GridOptimizer(land_poly)
        blocks = optimizer.generate_grid_candidates(25.0, 0.0)
        print(f"  Generated {len(blocks)} grid blocks")
        
        # Test subdivision solver
        widths = SubdivisionSolver.solve_subdivision(50.0, 5.0, 8.0, 6.0, time_limit=5)
        print(f"  Subdivision result: {len(widths)} lots")
        
        print("✅ Algorithm tests passed")
        return True
    except Exception as e:
        print(f"❌ Algorithm test failed: {e}")
        traceback.print_exc()
        return False


def test_api_models():
    """Test Pydantic models."""
    print("\nTesting API models...")
    try:
        from api.schemas.request_schemas import AlgorithmConfig, LandPlot, OptimizationRequest
        
        # Create test config
        config = AlgorithmConfig()
        print(f"  Default config created: spacing={config.spacing_min}-{config.spacing_max}m")
        
        # Create test land plot
        land_plot = LandPlot(
            type="Polygon",
            coordinates=[[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]]
        )
        print(f"  Land plot created: {land_plot.type}")
        
        # Create request
        request = OptimizationRequest(config=config, land_plots=[land_plot])
        print(f"  Request created with {len(request.land_plots)} plots")
        
        print("✅ API models tests passed")
        return True
    except Exception as e:
        print(f"❌ API models test failed: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Algorithm Backend Test Suite (Modular Architecture)")
    print("=" * 50)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("API Models", test_api_models()))
    results.append(("Algorithm", test_algorithm()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
