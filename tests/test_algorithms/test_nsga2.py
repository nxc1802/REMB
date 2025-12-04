"""
Unit tests for NSGA-II Optimizer
"""
import pytest
from shapely.geometry import box

from src.models.domain import SiteBoundary, PlotType
from src.algorithms.nsga2_optimizer import NSGA2Optimizer, IndustrialEstateProblem


class TestNSGA2Optimizer:
    """Test cases for NSGA2Optimizer"""
    
    @pytest.fixture
    def simple_site(self):
        """Create a simple rectangular site for testing"""
        site_geom = box(0, 0, 500, 500)  # 500m x 500m
        site = SiteBoundary(
            geometry=site_geom,
            area_sqm=site_geom.area
        )
        site.buildable_area_sqm = site.area_sqm
        return site
    
    def test_optimizer_initialization(self):
        """Test that optimizer initializes correctly"""
        optimizer = NSGA2Optimizer()
        assert optimizer is not None
        assert optimizer.regulations is not None
    
    def test_problem_creation(self, simple_site):
        """Test that optimization problem is created correctly"""
        problem = IndustrialEstateProblem(
            site_boundary=simple_site,
            regulations={},
            n_plots=10
        )
        
        assert problem.n_var == 50  # 10 plots * 5 variables
        assert problem.n_obj == 4  # 4 objectives
        assert problem.n_plots == 10
    
    def test_optimization_runs(self, simple_site):
        """Test that optimization runs without errors (quick test)"""
        optimizer = NSGA2Optimizer()
        
        # Run with small population for speed
        pareto_front = optimizer.optimize(
            site_boundary=simple_site,
            population_size=10,
            n_generations=5,
            n_plots=5
        )
        
        assert pareto_front is not None
        assert len(pareto_front.layouts) > 0
        assert pareto_front.generation_time_seconds >= 0
    
    def test_pareto_front_layouts_have_metrics(self, simple_site):
        """Test that generated layouts have calculated metrics"""
        optimizer = NSGA2Optimizer()
        
        pareto_front = optimizer.optimize(
            site_boundary=simple_site,
            population_size=10,
            n_generations=5,
            n_plots=5
        )
        
        for layout in pareto_front.layouts:
            assert layout.metrics is not None
            assert layout.metrics.total_area_sqm > 0
            # Note: metrics might be 0 if no valid plots generated
    
    def test_get_best_layouts(self, simple_site):
        """Test retrieval of best layouts from Pareto front"""
        optimizer = NSGA2Optimizer()
        
        pareto_front = optimizer.optimize(
            site_boundary=simple_site,
            population_size=10,
            n_generations=5,
            n_plots=5
        )
        
        max_sellable = pareto_front.get_max_sellable_layout()
        max_green = pareto_front.get_max_green_layout()
        balanced = pareto_front.get_balanced_layout()
        
        # All should exist if we have solutions
        if len(pareto_front.layouts) > 0:
            assert max_sellable is not None
            assert max_green is not None
            assert balanced is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
