"""
Plot Generator - Industrial Plot Layout Generation
Generates optimal plot layouts within buildable area
"""
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box, LineString
from shapely.ops import unary_union
from shapely.affinity import rotate, translate
from typing import List, Tuple, Optional, Dict
import logging
import yaml
from pathlib import Path
import uuid

from src.models.domain import SiteBoundary, Plot, PlotType, RoadNetwork

logger = logging.getLogger(__name__)


class PlotGenerator:
    """
    Industrial plot generator
    
    Responsibilities:
    - Generate plot subdivisions within buildable area
    - Optimize plot orientation for efficiency
    - Ensure road access for all plots
    - Handle varied plot sizes
    """
    
    def __init__(self, regulations_path: str = "config/regulations.yaml"):
        """
        Initialize plot generator
        
        Args:
            regulations_path: Path to regulations YAML
        """
        self.regulations_path = Path(regulations_path)
        self.regulations = self._load_regulations()
        self.logger = logging.getLogger(__name__)
        
        # Load plot requirements
        plot_config = self.regulations.get('plot', {})
        self.min_area = plot_config.get('minimum_area_sqm', 1000)
        self.max_area = plot_config.get('maximum_area_sqm', 50000)
        self.min_width = plot_config.get('minimum_width_m', 20)
        self.min_frontage = plot_config.get('minimum_frontage_m', 15)
    
    def _load_regulations(self) -> dict:
        """Load regulations from YAML"""
        if not self.regulations_path.exists():
            return {}
        with open(self.regulations_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def generate_grid_plots(
        self,
        site: SiteBoundary,
        road_network: RoadNetwork,
        plot_width: float = 100,
        plot_depth: float = 100,
        road_setback: float = 5
    ) -> List[Plot]:
        """
        Generate plots in a regular grid pattern
        
        Args:
            site: Site boundary
            road_network: Road network for access checking
            plot_width: Standard plot width
            plot_depth: Standard plot depth
            road_setback: Setback from roads
            
        Returns:
            List of Plot objects
        """
        self.logger.info(f"Generating grid plots: {plot_width}m x {plot_depth}m")
        
        # Get buildable area (after boundary setback)
        setback = self.regulations.get('setbacks', {}).get('boundary_minimum', 50)
        buildable = site.geometry.buffer(-setback)
        
        if buildable.is_empty:
            self.logger.warning("No buildable area after setback")
            return []
        
        # Get road polygons to avoid
        road_polygons = self._get_road_polygons(road_network)
        if road_polygons:
            road_union = unary_union(road_polygons)
            buildable = buildable.difference(road_union.buffer(road_setback))
        
        if buildable.is_empty:
            self.logger.warning("No buildable area after road subtraction")
            return []
        
        # Get bounds
        minx, miny, maxx, maxy = buildable.bounds
        
        plots = []
        plot_id = 0
        
        # Generate grid of plots
        y = miny
        while y + plot_depth <= maxy:
            x = minx
            while x + plot_width <= maxx:
                plot_geom = box(x, y, x + plot_width, y + plot_depth)
                
                # Check if plot fits in buildable area
                if buildable.contains(plot_geom):
                    # Check if plot area meets minimum
                    if plot_geom.area >= self.min_area:
                        plot = Plot(
                            id=f"plot_{plot_id:03d}",
                            geometry=plot_geom,
                            area_sqm=plot_geom.area,
                            type=PlotType.INDUSTRIAL,
                            width_m=plot_width,
                            depth_m=plot_depth,
                            frontage_m=plot_width,
                            has_road_access=self._check_road_access(plot_geom, road_network),
                            orientation_degrees=0
                        )
                        plots.append(plot)
                        plot_id += 1
                elif buildable.intersects(plot_geom):
                    # Try to fit partial plot
                    intersection = buildable.intersection(plot_geom)
                    if isinstance(intersection, Polygon) and intersection.area >= self.min_area:
                        plot = Plot(
                            id=f"plot_{plot_id:03d}",
                            geometry=intersection,
                            area_sqm=intersection.area,
                            type=PlotType.INDUSTRIAL,
                            width_m=self._estimate_width(intersection),
                            depth_m=self._estimate_depth(intersection),
                            frontage_m=self._estimate_width(intersection),
                            has_road_access=self._check_road_access(intersection, road_network),
                            orientation_degrees=0
                        )
                        plots.append(plot)
                        plot_id += 1
                
                x += plot_width
            y += plot_depth
        
        self.logger.info(f"Generated {len(plots)} grid plots")
        return plots
    
    def generate_varied_plots(
        self,
        site: SiteBoundary,
        road_network: RoadNetwork,
        size_distribution: Dict[str, float] = None
    ) -> List[Plot]:
        """
        Generate plots with varied sizes
        
        Args:
            site: Site boundary
            road_network: Road network for access checking
            size_distribution: Dict of size:percentage, e.g., {'small': 0.3, 'medium': 0.5, 'large': 0.2}
            
        Returns:
            List of Plot objects
        """
        if size_distribution is None:
            size_distribution = {
                'small': 0.3,   # 1000-2000 sqm
                'medium': 0.5,  # 2000-5000 sqm
                'large': 0.2    # 5000-10000 sqm
            }
        
        size_specs = {
            'small': {'width': 40, 'depth': 50},
            'medium': {'width': 70, 'depth': 70},
            'large': {'width': 100, 'depth': 100}
        }
        
        self.logger.info("Generating varied size plots")
        
        setback = self.regulations.get('setbacks', {}).get('boundary_minimum', 50)
        buildable = site.geometry.buffer(-setback)
        
        road_polygons = self._get_road_polygons(road_network)
        if road_polygons:
            road_union = unary_union(road_polygons)
            buildable = buildable.difference(road_union.buffer(5))
        
        if buildable.is_empty:
            return []
        
        plots = []
        remaining_area = buildable
        plot_id = 0
        
        # Target area for each size category
        total_buildable = buildable.area
        target_areas = {
            size: total_buildable * pct for size, pct in size_distribution.items()
        }
        
        for size, target_area in target_areas.items():
            generated_area = 0
            specs = size_specs[size]
            
            while generated_area < target_area and not remaining_area.is_empty:
                # Find valid placement
                plot = self._place_plot(
                    remaining_area, 
                    specs['width'], 
                    specs['depth'],
                    road_network,
                    f"plot_{plot_id:03d}"
                )
                
                if plot:
                    plots.append(plot)
                    remaining_area = remaining_area.difference(plot.geometry.buffer(5))
                    generated_area += plot.area_sqm
                    plot_id += 1
                else:
                    break
        
        self.logger.info(f"Generated {len(plots)} varied plots")
        return plots
    
    def _place_plot(
        self,
        available_area: Polygon,
        width: float,
        depth: float,
        road_network: RoadNetwork,
        plot_id: str
    ) -> Optional[Plot]:
        """
        Try to place a single plot in available area
        """
        if available_area.is_empty:
            return None
        
        minx, miny, maxx, maxy = available_area.bounds
        
        # Try different positions
        for _ in range(50):  # Max attempts
            x = np.random.uniform(minx, maxx - width)
            y = np.random.uniform(miny, maxy - depth)
            
            plot_geom = box(x, y, x + width, y + depth)
            
            if available_area.contains(plot_geom):
                return Plot(
                    id=plot_id,
                    geometry=plot_geom,
                    area_sqm=plot_geom.area,
                    type=PlotType.INDUSTRIAL,
                    width_m=width,
                    depth_m=depth,
                    frontage_m=width,
                    has_road_access=self._check_road_access(plot_geom, road_network)
                )
        
        return None
    
    def generate_green_spaces(
        self,
        site: SiteBoundary,
        industrial_plots: List[Plot],
        road_network: RoadNetwork,
        target_ratio: float = 0.15
    ) -> List[Plot]:
        """
        Generate green space plots to meet minimum requirement
        
        Args:
            site: Site boundary
            industrial_plots: Existing industrial plots
            road_network: Road network
            target_ratio: Target green space ratio (default 15%)
            
        Returns:
            List of green space Plot objects
        """
        self.logger.info(f"Generating green spaces (target: {target_ratio*100}%)")
        
        target_area = site.buildable_area_sqm * target_ratio
        
        # Get used area
        used_polys = [p.geometry for p in industrial_plots]
        road_polys = self._get_road_polygons(road_network)
        
        all_used = unary_union(used_polys + road_polys)
        
        # Remaining area for green
        setback = self.regulations.get('setbacks', {}).get('boundary_minimum', 50)
        buildable = site.geometry.buffer(-setback)
        remaining = buildable.difference(all_used.buffer(2))
        
        green_plots = []
        
        if remaining.is_empty:
            self.logger.warning("No remaining area for green space")
            return green_plots
        
        # Convert remaining area to green plots
        if isinstance(remaining, MultiPolygon):
            polygons = list(remaining.geoms)
        else:
            polygons = [remaining]
        
        for i, poly in enumerate(polygons):
            if poly.area >= 50:  # Minimum 50 sqm for green space
                green_plot = Plot(
                    id=f"green_{i:03d}",
                    geometry=poly,
                    area_sqm=poly.area,
                    type=PlotType.GREEN_SPACE,
                    width_m=self._estimate_width(poly),
                    depth_m=self._estimate_depth(poly)
                )
                green_plots.append(green_plot)
        
        total_green = sum(p.area_sqm for p in green_plots)
        self.logger.info(
            f"Generated {len(green_plots)} green plots, "
            f"total: {total_green:.0f}m² ({total_green/site.buildable_area_sqm*100:.1f}%)"
        )
        
        return green_plots
    
    def _get_road_polygons(self, road_network: RoadNetwork) -> List[Polygon]:
        """Get road polygons from road network"""
        if not road_network:
            return []
        
        road_config = self.regulations.get('roads', {})
        primary_width = road_config.get('primary_width_m', 24)
        secondary_width = road_config.get('secondary_width_m', 16)
        
        polygons = []
        
        if road_network.primary_roads:
            roads = road_network.primary_roads.geoms if hasattr(road_network.primary_roads, 'geoms') else [road_network.primary_roads]
            for road in roads:
                if isinstance(road, LineString):
                    polygons.append(road.buffer(primary_width / 2, cap_style=2))
        
        if road_network.secondary_roads:
            roads = road_network.secondary_roads.geoms if hasattr(road_network.secondary_roads, 'geoms') else [road_network.secondary_roads]
            for road in roads:
                if isinstance(road, LineString):
                    polygons.append(road.buffer(secondary_width / 2, cap_style=2))
        
        return polygons
    
    def _check_road_access(
        self,
        plot_geom: Polygon,
        road_network: RoadNetwork,
        max_distance: float = 200
    ) -> bool:
        """Check if plot has road access within max distance"""
        if not road_network:
            return False
        
        all_roads = []
        if road_network.primary_roads:
            roads = road_network.primary_roads.geoms if hasattr(road_network.primary_roads, 'geoms') else [road_network.primary_roads]
            all_roads.extend(roads)
        if road_network.secondary_roads:
            roads = road_network.secondary_roads.geoms if hasattr(road_network.secondary_roads, 'geoms') else [road_network.secondary_roads]
            all_roads.extend(roads)
        
        for road in all_roads:
            if plot_geom.distance(road) <= max_distance:
                return True
        
        return False
    
    def _estimate_width(self, geom: Polygon) -> float:
        """Estimate plot width from geometry"""
        minx, miny, maxx, maxy = geom.bounds
        return maxx - minx
    
    def _estimate_depth(self, geom: Polygon) -> float:
        """Estimate plot depth from geometry"""
        minx, miny, maxx, maxy = geom.bounds
        return maxy - miny


# Example usage
if __name__ == "__main__":
    from src.geometry.site_processor import SiteProcessor
    from src.geometry.road_network import RoadNetworkGenerator
    
    # Create test site
    processor = SiteProcessor()
    coords = [(0, 0), (500, 0), (500, 500), (0, 500), (0, 0)]
    site = processor.import_from_coordinates(coords)
    
    # Generate road network
    road_gen = RoadNetworkGenerator()
    roads = road_gen.generate_grid_network(site, primary_spacing=150)
    
    # Generate plots
    plot_gen = PlotGenerator()
    
    # Grid plots
    grid_plots = plot_gen.generate_grid_plots(
        site, roads,
        plot_width=80,
        plot_depth=100
    )
    
    print(f"Grid plots: {len(grid_plots)}")
    total_area = sum(p.area_sqm for p in grid_plots)
    print(f"Total industrial area: {total_area:.0f}m²")
    
    # Green spaces
    green_plots = plot_gen.generate_green_spaces(
        site, grid_plots, roads,
        target_ratio=0.15
    )
    
    print(f"Green plots: {len(green_plots)}")
    green_area = sum(p.area_sqm for p in green_plots)
    print(f"Total green area: {green_area:.0f}m²")
    
    # Check road access
    with_access = sum(1 for p in grid_plots if p.has_road_access)
    print(f"Plots with road access: {with_access}/{len(grid_plots)}")
