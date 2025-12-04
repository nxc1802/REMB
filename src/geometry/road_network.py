"""
Road Network Generator - Infrastructure Skeleton
Generates optimal road networks for industrial estates
"""
import numpy as np
from shapely.geometry import (
    Polygon, MultiPolygon, LineString, MultiLineString, 
    Point, box
)
from shapely.ops import unary_union, linemerge, split
from typing import List, Tuple, Optional, Dict
import logging
import yaml
from pathlib import Path

from src.models.domain import SiteBoundary, RoadNetwork, Plot, PlotType

logger = logging.getLogger(__name__)


class RoadNetworkGenerator:
    """
    Road network generator for industrial estates
    
    Responsibilities:
    - Generate primary road network from user input
    - Generate secondary road grid
    - Identify dead zones (>200m from road)
    - Optimize road layout for accessibility
    """
    
    def __init__(self, regulations_path: str = "config/regulations.yaml"):
        """
        Initialize road network generator
        
        Args:
            regulations_path: Path to regulations YAML
        """
        self.regulations_path = Path(regulations_path)
        self.regulations = self._load_regulations()
        self.logger = logging.getLogger(__name__)
        
        # Road widths from regulations
        road_config = self.regulations.get('roads', {})
        self.primary_width = road_config.get('primary_width_m', 24)
        self.secondary_width = road_config.get('secondary_width_m', 16)
        self.tertiary_width = road_config.get('tertiary_width_m', 12)
        self.max_distance = road_config.get('maximum_distance_to_road_m', 200)
    
    def _load_regulations(self) -> dict:
        """Load regulations from YAML"""
        if not self.regulations_path.exists():
            return {}
        with open(self.regulations_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def generate_grid_network(
        self,
        site: SiteBoundary,
        primary_spacing: float = 200,
        secondary_spacing: float = 100
    ) -> RoadNetwork:
        """
        Generate a grid-based road network
        
        Args:
            site: Site boundary
            primary_spacing: Distance between primary roads
            secondary_spacing: Distance between secondary roads
            
        Returns:
            RoadNetwork object
        """
        self.logger.info("Generating grid road network")
        
        bounds = site.geometry.bounds
        minx, miny, maxx, maxy = bounds
        width = maxx - minx
        height = maxy - miny
        
        # Offset roads from boundary
        setback = self.regulations.get('setbacks', {}).get('boundary_minimum', 50)
        
        primary_roads = []
        secondary_roads = []
        
        # Primary horizontal roads
        y_pos = miny + setback + primary_spacing / 2
        while y_pos < maxy - setback:
            line = LineString([(minx + setback, y_pos), (maxx - setback, y_pos)])
            clipped = line.intersection(site.geometry.buffer(-setback))
            if not clipped.is_empty:
                primary_roads.append(clipped if isinstance(clipped, LineString) else clipped)
            y_pos += primary_spacing
        
        # Primary vertical roads
        x_pos = minx + setback + primary_spacing / 2
        while x_pos < maxx - setback:
            line = LineString([(x_pos, miny + setback), (x_pos, maxy - setback)])
            clipped = line.intersection(site.geometry.buffer(-setback))
            if not clipped.is_empty:
                primary_roads.append(clipped if isinstance(clipped, LineString) else clipped)
            x_pos += primary_spacing
        
        # Secondary roads (between primary roads)
        y_pos = miny + setback + secondary_spacing
        while y_pos < maxy - setback:
            # Skip if too close to primary road
            if not any(abs(y_pos - self._get_y_coord(r)) < secondary_spacing/2 
                      for r in primary_roads if isinstance(r, LineString)):
                line = LineString([(minx + setback, y_pos), (maxx - setback, y_pos)])
                clipped = line.intersection(site.geometry.buffer(-setback))
                if not clipped.is_empty:
                    secondary_roads.append(clipped)
            y_pos += secondary_spacing
        
        x_pos = minx + setback + secondary_spacing
        while x_pos < maxx - setback:
            if not any(abs(x_pos - self._get_x_coord(r)) < secondary_spacing/2 
                      for r in primary_roads if isinstance(r, LineString)):
                line = LineString([(x_pos, miny + setback), (x_pos, maxy - setback)])
                clipped = line.intersection(site.geometry.buffer(-setback))
                if not clipped.is_empty:
                    secondary_roads.append(clipped)
            x_pos += secondary_spacing
        
        # Create MultiLineStrings
        primary_multi = MultiLineString(primary_roads) if primary_roads else None
        secondary_multi = MultiLineString(secondary_roads) if secondary_roads else None
        
        # Calculate total length
        total_length = 0
        if primary_multi:
            total_length += primary_multi.length
        if secondary_multi:
            total_length += secondary_multi.length
        
        # Calculate road area
        road_area = 0
        if primary_multi:
            road_area += primary_multi.length * self.primary_width
        if secondary_multi:
            road_area += secondary_multi.length * self.secondary_width
        
        network = RoadNetwork(
            primary_roads=primary_multi,
            secondary_roads=secondary_multi,
            tertiary_roads=None,
            total_length_m=total_length,
            total_area_sqm=road_area
        )
        
        self.logger.info(
            f"Generated road network: {len(primary_roads)} primary, "
            f"{len(secondary_roads)} secondary, total {total_length:.0f}m"
        )
        
        return network
    
    def generate_spine_network(
        self,
        site: SiteBoundary,
        entry_points: Optional[List[Tuple[float, float]]] = None
    ) -> RoadNetwork:
        """
        Generate a spine-based road network (main road with branches)
        
        Args:
            site: Site boundary
            entry_points: Optional list of entry point coordinates
            
        Returns:
            RoadNetwork object
        """
        self.logger.info("Generating spine road network")
        
        bounds = site.geometry.bounds
        minx, miny, maxx, maxy = bounds
        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        
        setback = self.regulations.get('setbacks', {}).get('boundary_minimum', 50)
        
        # Determine spine direction (along longest axis)
        width = maxx - minx
        height = maxy - miny
        
        primary_roads = []
        secondary_roads = []
        
        if width >= height:
            # Horizontal spine
            spine = LineString([
                (minx + setback, center_y),
                (maxx - setback, center_y)
            ])
            primary_roads.append(spine)
            
            # Vertical branches
            branch_spacing = self.max_distance * 1.5
            x_pos = minx + setback + branch_spacing / 2
            while x_pos < maxx - setback:
                branch = LineString([
                    (x_pos, miny + setback),
                    (x_pos, maxy - setback)
                ])
                clipped = branch.intersection(site.geometry.buffer(-setback))
                if not clipped.is_empty:
                    secondary_roads.append(clipped)
                x_pos += branch_spacing
        else:
            # Vertical spine
            spine = LineString([
                (center_x, miny + setback),
                (center_x, maxy - setback)
            ])
            primary_roads.append(spine)
            
            # Horizontal branches
            branch_spacing = self.max_distance * 1.5
            y_pos = miny + setback + branch_spacing / 2
            while y_pos < maxy - setback:
                branch = LineString([
                    (minx + setback, y_pos),
                    (maxx - setback, y_pos)
                ])
                clipped = branch.intersection(site.geometry.buffer(-setback))
                if not clipped.is_empty:
                    secondary_roads.append(clipped)
                y_pos += branch_spacing
        
        # Clip to site boundary
        primary_roads = [r.intersection(site.geometry.buffer(-setback)) 
                        for r in primary_roads if not r.is_empty]
        
        primary_multi = MultiLineString(primary_roads) if primary_roads else None
        secondary_multi = MultiLineString(secondary_roads) if secondary_roads else None
        
        total_length = 0
        road_area = 0
        
        if primary_multi:
            total_length += primary_multi.length
            road_area += primary_multi.length * self.primary_width
        if secondary_multi:
            total_length += secondary_multi.length
            road_area += secondary_multi.length * self.secondary_width
        
        return RoadNetwork(
            primary_roads=primary_multi,
            secondary_roads=secondary_multi,
            total_length_m=total_length,
            total_area_sqm=road_area
        )
    
    def identify_dead_zones(
        self,
        site: SiteBoundary,
        road_network: RoadNetwork
    ) -> List[Polygon]:
        """
        Identify areas more than max_distance from any road
        
        Args:
            site: Site boundary
            road_network: Road network
            
        Returns:
            List of polygons representing dead zones
        """
        self.logger.info(f"Identifying dead zones (>{self.max_distance}m from road)")
        
        # Combine all roads
        all_roads = []
        if road_network.primary_roads:
            if hasattr(road_network.primary_roads, 'geoms'):
                all_roads.extend(road_network.primary_roads.geoms)
            else:
                all_roads.append(road_network.primary_roads)
        
        if road_network.secondary_roads:
            if hasattr(road_network.secondary_roads, 'geoms'):
                all_roads.extend(road_network.secondary_roads.geoms)
            else:
                all_roads.append(road_network.secondary_roads)
        
        if not all_roads:
            return [site.geometry]  # Entire site is dead zone
        
        # Create buffer around all roads
        road_union = unary_union(all_roads)
        covered_area = road_union.buffer(self.max_distance)
        
        # Find uncovered areas
        dead_zones = site.geometry.difference(covered_area)
        
        if dead_zones.is_empty:
            return []
        
        if isinstance(dead_zones, Polygon):
            if dead_zones.area > 100:  # Minimum 100 sqm
                return [dead_zones]
            return []
        
        # MultiPolygon
        return [p for p in dead_zones.geoms if p.area > 100]
    
    def optimize_for_coverage(
        self,
        site: SiteBoundary,
        max_road_ratio: float = 0.25
    ) -> RoadNetwork:
        """
        Generate road network optimized for complete coverage
        within road area budget
        
        Args:
            site: Site boundary
            max_road_ratio: Maximum ratio of site area for roads
            
        Returns:
            Optimized RoadNetwork
        """
        self.logger.info("Generating coverage-optimized road network")
        
        max_road_area = site.buildable_area_sqm * max_road_ratio
        
        # Start with sparse grid and densify until covered or budget exceeded
        spacing = self.max_distance * 2  # Start sparse
        
        while spacing >= self.max_distance / 2:
            network = self.generate_grid_network(
                site,
                primary_spacing=spacing,
                secondary_spacing=spacing * 2
            )
            
            dead_zones = self.identify_dead_zones(site, network)
            dead_area = sum(z.area for z in dead_zones)
            
            if dead_area < site.buildable_area_sqm * 0.05:  # <5% dead zone
                if network.total_area_sqm <= max_road_area:
                    return network
            
            spacing *= 0.8  # Densify
        
        # Return the last generated network
        return network
    
    def get_road_polygons(self, road_network: RoadNetwork) -> List[Polygon]:
        """
        Convert road lines to polygons (for plotting/export)
        
        Args:
            road_network: Road network
            
        Returns:
            List of road polygons
        """
        polygons = []
        
        if road_network.primary_roads:
            roads = road_network.primary_roads.geoms if hasattr(road_network.primary_roads, 'geoms') else [road_network.primary_roads]
            for road in roads:
                poly = road.buffer(self.primary_width / 2, cap_style=2)
                polygons.append(poly)
        
        if road_network.secondary_roads:
            roads = road_network.secondary_roads.geoms if hasattr(road_network.secondary_roads, 'geoms') else [road_network.secondary_roads]
            for road in roads:
                poly = road.buffer(self.secondary_width / 2, cap_style=2)
                polygons.append(poly)
        
        return polygons
    
    def _get_y_coord(self, line: LineString) -> float:
        """Get average Y coordinate of a line"""
        if not isinstance(line, LineString):
            return 0
        coords = list(line.coords)
        return sum(c[1] for c in coords) / len(coords)
    
    def _get_x_coord(self, line: LineString) -> float:
        """Get average X coordinate of a line"""
        if not isinstance(line, LineString):
            return 0
        coords = list(line.coords)
        return sum(c[0] for c in coords) / len(coords)


# Example usage
if __name__ == "__main__":
    from src.geometry.site_processor import SiteProcessor
    
    # Create a test site
    processor = SiteProcessor()
    coords = [(0, 0), (500, 0), (500, 500), (0, 500), (0, 0)]
    site = processor.import_from_coordinates(coords)
    
    # Generate road network
    generator = RoadNetworkGenerator()
    
    # Grid network
    grid_network = generator.generate_grid_network(
        site,
        primary_spacing=150,
        secondary_spacing=75
    )
    
    print(f"Grid Network:")
    print(f"  Total length: {grid_network.total_length_m:.0f}m")
    print(f"  Total area: {grid_network.total_area_sqm:.0f}m²")
    
    # Check dead zones
    dead_zones = generator.identify_dead_zones(site, grid_network)
    print(f"  Dead zones: {len(dead_zones)}")
    
    # Spine network
    spine_network = generator.generate_spine_network(site)
    print(f"\nSpine Network:")
    print(f"  Total length: {spine_network.total_length_m:.0f}m")
    print(f"  Total area: {spine_network.total_area_sqm:.0f}m²")
    
    # Optimized network
    optimized = generator.optimize_for_coverage(site, max_road_ratio=0.20)
    print(f"\nOptimized Network:")
    print(f"  Total length: {optimized.total_length_m:.0f}m")
    print(f"  Total area: {optimized.total_area_sqm:.0f}m²")
