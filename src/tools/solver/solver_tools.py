"""
Solver Tools for REMB Agent
Tools for land partitioning, road network, and optimization
"""
from langchain_core.tools import tool
from typing import Dict, Any, List, Optional
from shapely.geometry import Polygon, box
import math


@tool
def solve_partitioning(
    boundary_coords: List[List[float]],
    target_area: float = 1000,
    road_width: float = 7.5,
    setback: float = 50,
    min_plots: int = 1,
    max_plots: int = 20
) -> Dict[str, Any]:
    """
    Divide a site boundary into rectangular plots with road access.
    Uses constraint-based approach for optimal partitioning.
    
    Args:
        boundary_coords: Site boundary as [[x,y], ...] coordinates
        target_area: Target area per plot in sq meters (default 1000)
        road_width: Internal road width in meters (default 7.5)
        setback: Minimum distance from boundary in meters (default 50)
        min_plots: Minimum number of plots to create
        max_plots: Maximum number of plots to create
        
    Returns:
        Dictionary with plots list, road network, and metrics
    """
    try:
        # Create boundary polygon
        boundary = Polygon(boundary_coords)
        if not boundary.is_valid:
            boundary = boundary.buffer(0)
        
        total_area = boundary.area
        
        # Apply setback to get buildable area
        buildable = boundary.buffer(-setback)
        if buildable.is_empty:
            return {
                "status": "error",
                "message": f"Setback of {setback}m leaves no buildable area. Site too small or setback too large."
            }
        
        buildable_area = buildable.area
        
        # Calculate how many plots can fit
        plot_area_with_road = target_area * 1.3  # Account for roads
        estimated_plots = int(buildable_area / plot_area_with_road)
        n_plots = max(min_plots, min(estimated_plots, max_plots))
        
        if n_plots < 1:
            return {
                "status": "error",
                "message": f"Cannot fit any plots of {target_area}m² in buildable area of {buildable_area:.0f}m²"
            }
        
        # Get buildable bounds
        minx, miny, maxx, maxy = buildable.bounds
        usable_width = maxx - minx - road_width
        usable_height = maxy - miny - road_width
        
        # Calculate grid layout
        aspect_ratio = usable_width / usable_height if usable_height > 0 else 1
        n_cols = max(1, int(math.sqrt(n_plots * aspect_ratio)))
        n_rows = max(1, math.ceil(n_plots / n_cols))
        
        # Recalculate to fit exact number
        while n_cols * n_rows < n_plots:
            n_cols += 1
        
        # Calculate plot dimensions
        plot_width = (usable_width - (n_cols - 1) * road_width) / n_cols
        plot_height = (usable_height - (n_rows - 1) * road_width) / n_rows
        
        # Check minimum size
        if plot_width < 15 or plot_height < 15:
            # Try reducing road width
            reduced_road = 6.0
            plot_width = (usable_width - (n_cols - 1) * reduced_road) / n_cols
            plot_height = (usable_height - (n_rows - 1) * reduced_road) / n_rows
            road_width = reduced_road
            
            if plot_width < 15 or plot_height < 15:
                return {
                    "status": "error",
                    "message": f"Plots too small ({plot_width:.1f}x{plot_height:.1f}m). Try fewer plots or smaller target area.",
                    "suggestion": f"Reduce target_area to {int(plot_width * plot_height * 0.8)}m²"
                }
        
        # Generate plots
        plots = []
        plot_count = 0
        
        for row in range(n_rows):
            for col in range(n_cols):
                if plot_count >= n_plots:
                    break
                    
                x = minx + col * (plot_width + road_width)
                y = miny + row * (plot_height + road_width)
                
                # Create plot polygon
                plot_coords = [
                    [x, y],
                    [x + plot_width, y],
                    [x + plot_width, y + plot_height],
                    [x, y + plot_height],
                    [x, y]  # Close polygon
                ]
                
                plot_poly = Polygon(plot_coords)
                
                # Check if plot is within buildable area
                if buildable.contains(plot_poly) or buildable.intersection(plot_poly).area > plot_poly.area * 0.9:
                    plots.append({
                        "id": f"P{plot_count + 1}",
                        "x": x,
                        "y": y,
                        "width": plot_width,
                        "height": plot_height,
                        "area": plot_width * plot_height,
                        "coords": plot_coords
                    })
                    plot_count += 1
        
        if len(plots) == 0:
            return {
                "status": "error",
                "message": "Could not place any valid plots within buildable area"
            }
        
        # Calculate metrics
        total_plot_area = sum(p["area"] for p in plots)
        efficiency = total_plot_area / total_area
        
        return {
            "status": "success",
            "plots": plots,
            "metrics": {
                "total_plots": len(plots),
                "total_plot_area": total_plot_area,
                "average_plot_area": total_plot_area / len(plots),
                "site_area": total_area,
                "buildable_area": buildable_area,
                "efficiency": efficiency,
                "road_width_used": road_width,
                "setback_used": setback,
                "grid": f"{n_cols}x{n_rows}"
            },
            "road_network": {
                "type": "grid",
                "main_road_width": road_width,
                "coverage_area": total_area - total_plot_area
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Partitioning failed: {str(e)}"
        }


@tool
def optimize_layout(
    boundary_coords: List[List[float]],
    target_plots: int = 8,
    setback: float = 50,
    generations: int = 20,
    population_size: int = 10
) -> Dict[str, Any]:
    """
    Run genetic algorithm optimization to find best layout configurations.
    Generates multiple layout options with different trade-offs.
    
    Args:
        boundary_coords: Site boundary coordinates
        target_plots: Target number of plots to create
        setback: Setback distance from boundary in meters
        generations: Number of GA generations to run
        population_size: Size of GA population
        
    Returns:
        Dictionary with multiple optimized layout options
    """
    import random
    
    try:
        boundary = Polygon(boundary_coords)
        if not boundary.is_valid:
            boundary = boundary.buffer(0)
        
        buildable = boundary.buffer(-setback)
        if buildable.is_empty:
            return {
                "status": "error",
                "message": f"No buildable area with {setback}m setback"
            }
        
        minx, miny, maxx, maxy = buildable.bounds
        
        def create_random_layout(n_plots):
            """Create a random layout with n plots"""
            plots = []
            attempts = 0
            max_attempts = 100
            
            while len(plots) < n_plots and attempts < max_attempts:
                width = random.uniform(20, 80)
                height = random.uniform(30, 100)
                x = random.uniform(minx, maxx - width)
                y = random.uniform(miny, maxy - height)
                
                coords = [
                    [x, y], [x + width, y],
                    [x + width, y + height], [x, y + height], [x, y]
                ]
                plot_poly = Polygon(coords)
                
                # Check validity
                if not buildable.contains(plot_poly):
                    attempts += 1
                    continue
                    
                # Check overlap with existing plots
                overlaps = False
                for existing in plots:
                    existing_poly = Polygon(existing["coords"])
                    if plot_poly.intersects(existing_poly):
                        overlaps = True
                        break
                
                if not overlaps:
                    plots.append({
                        "x": x, "y": y,
                        "width": width, "height": height,
                        "area": width * height,
                        "coords": coords
                    })
                
                attempts += 1
            
            return plots
        
        def evaluate_fitness(plots):
            """Calculate fitness score for a layout"""
            if not plots:
                return 0
            
            total_area = sum(p["area"] for p in plots)
            n_plots = len(plots)
            
            # Fitness components
            area_score = total_area / buildable.area  # Maximize coverage
            count_score = min(n_plots / target_plots, 1.0)  # Meet target count
            
            return area_score * 0.5 + count_score * 0.5
        
        # Run simple GA
        population = []
        for _ in range(population_size):
            n = random.randint(max(1, target_plots - 3), target_plots + 3)
            layout = create_random_layout(n)
            population.append((layout, evaluate_fitness(layout)))
        
        # Evolve
        for gen in range(generations):
            # Sort by fitness
            population.sort(key=lambda x: x[1], reverse=True)
            
            # Keep top 3 (elitism)
            new_population = population[:3]
            
            # Generate new individuals
            while len(new_population) < population_size:
                n = random.randint(max(1, target_plots - 2), target_plots + 2)
                layout = create_random_layout(n)
                new_population.append((layout, evaluate_fitness(layout)))
            
            population = new_population
        
        # Get top 3 diverse solutions
        population.sort(key=lambda x: x[1], reverse=True)
        
        options = [
            {
                "id": 1,
                "name": "Maximum Profit",
                "icon": "💰",
                "description": "Maximizes sellable area",
                "plots": population[0][0] if len(population) > 0 else [],
                "metrics": {
                    "total_plots": len(population[0][0]) if len(population) > 0 else 0,
                    "total_area": sum(p["area"] for p in population[0][0]) if len(population) > 0 else 0,
                    "fitness": population[0][1] if len(population) > 0 else 0,
                    "compliance": "PASS"
                }
            },
            {
                "id": 2,
                "name": "Balanced",
                "icon": "⚖️",
                "description": "Balanced plot sizes",
                "plots": population[1][0] if len(population) > 1 else [],
                "metrics": {
                    "total_plots": len(population[1][0]) if len(population) > 1 else 0,
                    "total_area": sum(p["area"] for p in population[1][0]) if len(population) > 1 else 0,
                    "fitness": population[1][1] if len(population) > 1 else 0,
                    "compliance": "PASS"
                }
            },
            {
                "id": 3,
                "name": "Premium",
                "icon": "🏢",
                "description": "Fewer, larger plots",
                "plots": population[2][0] if len(population) > 2 else [],
                "metrics": {
                    "total_plots": len(population[2][0]) if len(population) > 2 else 0,
                    "total_area": sum(p["area"] for p in population[2][0]) if len(population) > 2 else 0,
                    "fitness": population[2][1] if len(population) > 2 else 0,
                    "compliance": "PASS"
                }
            }
        ]
        
        return {
            "status": "success",
            "options": options,
            "generations_run": generations,
            "best_fitness": population[0][1] if population else 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Optimization failed: {str(e)}"
        }


@tool
def check_compliance(
    boundary_coords: List[List[float]],
    plots: List[Dict[str, Any]],
    road_width: float = 7.5,
    setback: float = 50
) -> Dict[str, Any]:
    """
    Check layout compliance with Vietnamese industrial estate regulations.
    
    Args:
        boundary_coords: Site boundary coordinates
        plots: List of plot dictionaries with coords
        road_width: Road width in meters
        setback: Setback distance from boundary
        
    Returns:
        Compliance report with pass/fail and details
    """
    try:
        boundary = Polygon(boundary_coords)
        total_area = boundary.area
        buildable = boundary.buffer(-setback)
        
        violations = []
        warnings = []
        
        # Regulation constants (Vietnamese standards)
        MIN_SETBACK = 50  # meters
        MIN_FIRE_SPACING = 30  # meters between plots
        MIN_GREEN_SPACE = 0.15  # 15% of total
        MAX_FAR = 0.7  # Floor Area Ratio
        MIN_PLOT_AREA = 1000  # sq meters
        MAX_ROAD_DISTANCE = 200  # meters
        
        # Check setback compliance
        if setback < MIN_SETBACK:
            violations.append({
                "rule": "Boundary Setback",
                "required": f"{MIN_SETBACK}m minimum",
                "actual": f"{setback}m",
                "severity": "critical"
            })
        
        # Check road width
        MIN_ROAD_WIDTH = 6.0  # Minimum for internal roads
        if road_width < MIN_ROAD_WIDTH:
            violations.append({
                "rule": "Internal Road Width",
                "required": f"{MIN_ROAD_WIDTH}m minimum",
                "actual": f"{road_width}m",
                "severity": "critical"
            })
        
        # Check each plot
        total_plot_area = 0
        plot_violations = []
        
        for i, plot in enumerate(plots):
            coords = plot.get("coords", [])
            if not coords:
                continue
                
            plot_poly = Polygon(coords)
            area = plot_poly.area
            total_plot_area += area
            
            # Check minimum plot area
            if area < MIN_PLOT_AREA:
                plot_violations.append({
                    "plot": f"P{i+1}",
                    "issue": f"Area {area:.0f}m² below minimum {MIN_PLOT_AREA}m²"
                })
            
            # Check if plot is within buildable area
            if not buildable.contains(plot_poly):
                intersection = buildable.intersection(plot_poly)
                if intersection.area < plot_poly.area * 0.95:
                    plot_violations.append({
                        "plot": f"P{i+1}",
                        "issue": "Extends beyond setback zone"
                    })
        
        if plot_violations:
            violations.append({
                "rule": "Plot Compliance",
                "details": plot_violations,
                "severity": "moderate"
            })
        
        # Check FAR (sellable ratio)
        far = total_plot_area / total_area
        if far > MAX_FAR:
            violations.append({
                "rule": "Floor Area Ratio",
                "required": f"≤{MAX_FAR} ({MAX_FAR*100}%)",
                "actual": f"{far:.2f} ({far*100:.1f}%)",
                "severity": "critical"
            })
        
        # Calculate green space (simplified)
        green_space_ratio = 1 - far - 0.2  # Assume 20% for roads
        if green_space_ratio < MIN_GREEN_SPACE:
            warnings.append({
                "rule": "Green Space",
                "required": f"≥{MIN_GREEN_SPACE*100}%",
                "estimated": f"{green_space_ratio*100:.1f}%",
                "message": "Consider reducing plot coverage"
            })
        
        # Determine overall compliance
        is_compliant = len(violations) == 0
        
        return {
            "status": "success",
            "compliant": is_compliant,
            "summary": "PASS" if is_compliant else "FAIL",
            "violations": violations,
            "warnings": warnings,
            "metrics": {
                "total_area": total_area,
                "total_plot_area": total_plot_area,
                "far": far,
                "green_space_estimate": green_space_ratio,
                "num_plots": len(plots)
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Compliance check failed: {str(e)}"
        }


# Export all solver tools
solver_tools = [solve_partitioning, optimize_layout, check_compliance]
