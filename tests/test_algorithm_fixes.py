"""
Test Suite for Algorithm Fixes
Tests all 3 critical fixes from Complete_Algorithm_Implementation.md

FIX #1: GA Order Crossover
FIX #2: NSGA-II Hard Constraints  
FIX #3: A* Road Connectivity
"""
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from shapely.geometry import box, Polygon

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# FIX #1 Tests: GA Order Crossover
# =============================================================================

class TestGAOrderCrossover:
    """Test GA improvements: crossover, tournament selection, adaptive mutation"""
    
    def test_ga_has_crossover_rate(self):
        """Verify GA optimizer has crossover_rate parameter"""
        from src.algorithms.ga_optimizer import SimpleGAOptimizer
        
        optimizer = SimpleGAOptimizer()
        
        # FIX #1: Should have crossover_rate attribute
        assert hasattr(optimizer, 'crossover_rate'), "Missing crossover_rate attribute"
        assert optimizer.crossover_rate == 0.85, f"Expected 0.85, got {optimizer.crossover_rate}"
        
        logger.info("✅ GA crossover_rate test passed")
    
    def test_ga_has_tournament_selection(self):
        """Verify GA has tournament selection method"""
        from src.algorithms.ga_optimizer import SimpleGAOptimizer
        
        optimizer = SimpleGAOptimizer()
        
        # FIX #1: Should have _tournament_select method
        assert hasattr(optimizer, '_tournament_select'), "Missing _tournament_select method"
        
        logger.info("✅ GA tournament selection test passed")
    
    def test_ga_has_order_crossover(self):
        """Verify GA has order crossover method"""
        from src.algorithms.ga_optimizer import SimpleGAOptimizer
        
        optimizer = SimpleGAOptimizer()
        
        # FIX #1: Should have _order_crossover method
        assert hasattr(optimizer, '_order_crossover'), "Missing _order_crossover method"
        
        logger.info("✅ GA order crossover test passed")
    
    def test_ga_has_adaptive_mutation(self):
        """Verify GA has adaptive mutation method"""
        from src.algorithms.ga_optimizer import SimpleGAOptimizer
        
        optimizer = SimpleGAOptimizer()
        
        # FIX #1: Should have _adaptive_mutate method
        assert hasattr(optimizer, '_adaptive_mutate'), "Missing _adaptive_mutate method"
        
        logger.info("✅ GA adaptive mutation test passed")
    
    def test_ga_optimization_runs(self):
        """Verify GA optimization runs without errors"""
        from src.algorithms.ga_optimizer import SimpleGAOptimizer
        
        optimizer = SimpleGAOptimizer(
            population_size=5,
            n_generations=5,
            target_plots=4
        )
        
        # Simple square boundary
        coords = [[0, 0], [200, 0], [200, 200], [0, 200], [0, 0]]
        
        options = optimizer.optimize(coords)
        
        assert len(options) == 3, f"Expected 3 options, got {len(options)}"
        assert all('plots' in opt for opt in options), "Missing plots in options"
        
        logger.info(f"✅ GA optimization test passed: {len(options)} options generated")


# =============================================================================
# FIX #2 Tests: NSGA-II Hard Constraints
# =============================================================================

class TestNSGA2HardConstraints:
    """Test NSGA-II with hard constraints"""
    
    def test_constrained_problem_exists(self):
        """Verify constrained problem class exists"""
        from src.algorithms.nsga2_constrained import IndustrialEstateConstrainedProblem
        
        assert IndustrialEstateConstrainedProblem is not None
        logger.info("✅ NSGA-II constrained problem exists")
    
    def test_problem_has_constraints(self):
        """Verify problem defines constraints (n_ieq_constr > 0)"""
        from src.algorithms.nsga2_constrained import IndustrialEstateConstrainedProblem
        
        site = box(0, 0, 500, 400)
        buildable = site.buffer(-50)
        
        problem = IndustrialEstateConstrainedProblem(
            site_boundary=site,
            buildable_area=buildable,
            n_plots=4
        )
        
        # FIX #2: Should have inequality constraints
        assert problem.n_ieq_constr > 0, "No inequality constraints defined"
        
        # Expected: n_plots*(n_plots-1)/2 overlap + n_plots containment
        expected_overlap = int(4 * 3 / 2)  # 6
        expected_containment = 4
        expected_total = expected_overlap + expected_containment  # 10
        
        assert problem.n_ieq_constr == expected_total, \
            f"Expected {expected_total} constraints, got {problem.n_ieq_constr}"
        
        logger.info(f"✅ NSGA-II has {problem.n_ieq_constr} hard constraints")
    
    def test_problem_has_3_objectives_not_5(self):
        """Verify problem has 3 objectives (not 5 with soft constraint)"""
        from src.algorithms.nsga2_constrained import IndustrialEstateConstrainedProblem
        
        site = box(0, 0, 500, 400)
        buildable = site.buffer(-50)
        
        problem = IndustrialEstateConstrainedProblem(
            site_boundary=site,
            buildable_area=buildable,
            n_plots=4
        )
        
        # FIX #2: Should have 3 objectives (not 5)
        assert problem.n_obj == 3, f"Expected 3 objectives, got {problem.n_obj}"
        
        logger.info("✅ NSGA-II has 3 objectives (hard constraints separate)")
    
    def test_constrained_solver_runs(self):
        """Verify constrained solver runs and returns results"""
        from src.algorithms.nsga2_constrained import solve_constrained_layout
        
        site = box(0, 0, 500, 400)
        buildable = site.buffer(-50)
        
        result = solve_constrained_layout(
            site_boundary=site,
            buildable_area=buildable,
            n_plots=4,
            population_size=20,
            n_generations=10,
            seed=42
        )
        
        assert 'success' in result
        assert 'n_solutions' in result
        assert 'layouts' in result
        
        logger.info(f"✅ NSGA-II constrained solver: {result['n_solutions']} solutions")


# =============================================================================
# FIX #3 Tests: A* Road Connectivity
# =============================================================================

class TestRoadConnectivity:
    """Test A* road connectivity validator"""
    
    def test_validator_exists(self):
        """Verify road validator class exists"""
        from src.geometry.road_validator import RoadConnectivityValidator
        
        assert RoadConnectivityValidator is not None
        logger.info("✅ Road validator exists")
    
    def test_astar_pathfinding(self):
        """Test A* pathfinding finds correct path"""
        from src.geometry.road_validator import RoadConnectivityValidator
        
        # Create simple grid with road
        road_cells = {(i, 5) for i in range(10)}  # Horizontal road at y=5
        
        validator = RoadConnectivityValidator(
            grid_size=(10, 10),
            road_cells=road_cells
        )
        
        # Find path from (5, 0) to road at (5, 5)
        path = validator.find_path((5, 0), (5, 5))
        
        assert path is not None, "No path found when one exists"
        assert len(path) == 6, f"Expected path length 6, got {len(path)}"
        assert path[0] == (5, 0), "Path doesn't start at start"
        assert path[-1] == (5, 5), "Path doesn't end at goal"
        
        logger.info(f"✅ A* pathfinding: path length {len(path)}")
    
    def test_road_access_check(self):
        """Test road accessibility checking"""
        from src.geometry.road_validator import RoadConnectivityValidator
        
        # Create road cells
        road_cells = {(i, 5) for i in range(10)}
        
        validator = RoadConnectivityValidator(
            grid_size=(10, 10),
            road_cells=road_cells
        )
        
        # Plot near road should be accessible
        accessible = validator.can_reach_road((5, 3))
        assert accessible, "Plot near road should be accessible"
        
        logger.info("✅ Road access check works")
    
    def test_roads_to_grid_conversion(self):
        """Test road to grid conversion"""
        from src.geometry.road_validator import roads_to_grid
        
        roads = [
            {'start': (0, 100), 'end': (500, 100)},  # Horizontal
        ]
        
        boundary = {'min_x': 0, 'max_x': 500, 'min_y': 0, 'max_y': 200}
        grid_size = (50, 20)
        
        road_cells = roads_to_grid(roads, boundary, grid_size)
        
        assert len(road_cells) > 0, "No road cells generated"
        assert len(road_cells) >= 50, f"Expected ~50 cells, got {len(road_cells)}"
        
        logger.info(f"✅ Roads to grid: {len(road_cells)} cells")


# =============================================================================
# Integration Tests
# =============================================================================

class TestREMBOptimizer:
    """Test unified REMB optimizer"""
    
    def test_remb_optimizer_exists(self):
        """Verify REMB optimizer class exists"""
        from src.algorithms.remb_optimizer import REMBOptimizer
        
        assert REMBOptimizer is not None
        logger.info("✅ REMB optimizer exists")
    
    def test_remb_optimizer_fast_mode(self):
        """Test fast optimization mode"""
        from src.algorithms.remb_optimizer import REMBOptimizer
        
        site = box(0, 0, 300, 300)
        roads = [{'start': (0, 150), 'end': (300, 150)}]
        
        optimizer = REMBOptimizer(
            site_boundary=site,
            roads=roads,
            setback=30
        )
        
        options = optimizer.optimize_fast(
            target_plots=4,
            population_size=5,
            n_generations=5
        )
        
        assert len(options) == 3, f"Expected 3 options, got {len(options)}"
        
        logger.info(f"✅ REMB fast mode: {len(options)} options")
    
    def test_remb_optimizer_validation(self):
        """Test layout validation"""
        from src.algorithms.remb_optimizer import REMBOptimizer
        
        site = box(0, 0, 300, 300)
        
        optimizer = REMBOptimizer(
            site_boundary=site,
            setback=30
        )
        
        # Valid layout
        valid_layout = [
            {'x': 50, 'y': 50, 'width': 40, 'height': 40},
            {'x': 150, 'y': 50, 'width': 40, 'height': 40},
        ]
        
        result = optimizer.validate_layout(valid_layout)
        
        assert 'is_valid' in result
        assert 'has_overlaps' in result
        assert result['has_overlaps'] == False, "No overlap expected"
        
        logger.info("✅ REMB validation works")


# =============================================================================
# Run All Tests
# =============================================================================

def run_all_tests():
    """Run all algorithm fix tests"""
    print("\n" + "="*60)
    print("ALGORITHM FIX TESTS")
    print("="*60)
    
    results = {}
    
    # FIX #1 Tests
    print("\n--- FIX #1: GA Order Crossover ---")
    ga_tests = TestGAOrderCrossover()
    
    tests_1 = [
        ("crossover_rate", ga_tests.test_ga_has_crossover_rate),
        ("tournament_selection", ga_tests.test_ga_has_tournament_selection),
        ("order_crossover", ga_tests.test_ga_has_order_crossover),
        ("adaptive_mutation", ga_tests.test_ga_has_adaptive_mutation),
        ("optimization_runs", ga_tests.test_ga_optimization_runs),
    ]
    
    for name, test_func in tests_1:
        try:
            test_func()
            results[f"FIX1_{name}"] = "✅ PASS"
        except Exception as e:
            results[f"FIX1_{name}"] = f"❌ FAIL: {str(e)[:40]}"
            print(f"  ❌ {name}: {e}")
    
    # FIX #2 Tests
    print("\n--- FIX #2: NSGA-II Hard Constraints ---")
    nsga_tests = TestNSGA2HardConstraints()
    
    tests_2 = [
        ("problem_exists", nsga_tests.test_constrained_problem_exists),
        ("has_constraints", nsga_tests.test_problem_has_constraints),
        ("3_objectives", nsga_tests.test_problem_has_3_objectives_not_5),
        ("solver_runs", nsga_tests.test_constrained_solver_runs),
    ]
    
    for name, test_func in tests_2:
        try:
            test_func()
            results[f"FIX2_{name}"] = "✅ PASS"
        except Exception as e:
            results[f"FIX2_{name}"] = f"❌ FAIL: {str(e)[:40]}"
            print(f"  ❌ {name}: {e}")
    
    # FIX #3 Tests
    print("\n--- FIX #3: A* Road Connectivity ---")
    road_tests = TestRoadConnectivity()
    
    tests_3 = [
        ("validator_exists", road_tests.test_validator_exists),
        ("astar_pathfinding", road_tests.test_astar_pathfinding),
        ("road_access", road_tests.test_road_access_check),
        ("roads_to_grid", road_tests.test_roads_to_grid_conversion),
    ]
    
    for name, test_func in tests_3:
        try:
            test_func()
            results[f"FIX3_{name}"] = "✅ PASS"
        except Exception as e:
            results[f"FIX3_{name}"] = f"❌ FAIL: {str(e)[:40]}"
            print(f"  ❌ {name}: {e}")
    
    # Integration Tests
    print("\n--- INTEGRATION: REMB Optimizer ---")
    remb_tests = TestREMBOptimizer()
    
    tests_int = [
        ("exists", remb_tests.test_remb_optimizer_exists),
        ("fast_mode", remb_tests.test_remb_optimizer_fast_mode),
        ("validation", remb_tests.test_remb_optimizer_validation),
    ]
    
    for name, test_func in tests_int:
        try:
            test_func()
            results[f"INT_{name}"] = "✅ PASS"
        except Exception as e:
            results[f"INT_{name}"] = f"❌ FAIL: {str(e)[:40]}"
            print(f"  ❌ {name}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if "PASS" in v)
    total = len(results)
    
    for name, status in results.items():
        if "FAIL" in status:
            print(f"  {name}: {status}")
    
    print(f"\n  TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
