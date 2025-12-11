"""Loop Template - Ring road around boundary.

    ┌──────────────────────────────┐
    │  ╔════════════════════════╗  │
    │  ║                        ║  │
    │  ║                        ║  │
    │  ║                        ║  │
    │  ╚════════════════════════╝  │
    └──────────────────────────────┘

Best for: Sites with central features, logistics centers
"""

from typing import Optional, List
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import linemerge

from .base import RoadTemplate, TemplateResult, TemplateParams


class LoopTemplate(RoadTemplate):
    """Ring road running around the boundary interior."""
    
    name = "loop"
    display_name = "Vành Đai"
    description = "Đường chạy vòng quanh biên, công trình ở giữa"
    icon = "⭕"
    
    def generate(
        self,
        boundary: Polygon,
        params: Optional[TemplateParams] = None
    ) -> TemplateResult:
        """Generate loop road skeleton.
        
        Args:
            boundary: Site boundary
            params: Template parameters
            
        Returns:
            TemplateResult with roads and blocks
        """
        params = params or TemplateParams()
        
        roads = []
        
        # 1. Create ring road by buffering boundary inward
        buffer_distance = params.boundary_buffer + params.main_road_width
        inner_boundary = boundary.buffer(-buffer_distance)
        
        if inner_boundary.is_empty or inner_boundary.area < 100:
            # Site too small for loop, fall back to perimeter road
            return self._generate_perimeter_road(boundary, params)
            
        # Get ring road as the boundary of inner area
        if inner_boundary.geom_type == 'Polygon':
            ring_road = LineString(inner_boundary.exterior.coords)
            roads.append(ring_road)
        elif inner_boundary.geom_type == 'MultiPolygon':
            # Multiple inner areas - use largest
            largest = max(inner_boundary.geoms, key=lambda g: g.area)
            ring_road = LineString(largest.exterior.coords)
            roads.append(ring_road)
            
        # 2. Create connector road from boundary to ring
        connector = self._create_connector(boundary, ring_road, params)
        if connector and not connector.is_empty:
            roads.append(connector)
            
        # 3. Entry point where connector meets boundary
        entry_points = []
        if connector and not connector.is_empty:
            coords = list(connector.coords)
            entry_points.append(Point(coords[0]))
            
        # 4. Extract blocks (central area + outer strip)
        blocks = self._get_blocks_from_roads(
            boundary, roads,
            buffer_width=params.main_road_width / 2
        )
        
        return TemplateResult(
            roads=roads,
            blocks=blocks,
            entry_points=entry_points,
            metadata={
                "template": self.name,
                "ring_length": ring_road.length if roads else 0,
                "inner_area": inner_boundary.area if not inner_boundary.is_empty else 0
            }
        )
    
    def _create_connector(
        self,
        boundary: Polygon,
        ring_road: LineString,
        params: TemplateParams
    ) -> Optional[LineString]:
        """Create connector road from boundary edge to ring."""
        # Find point on ring closest to boundary center perpendicular
        _, length, angle, center, _ = self._get_obb_info(boundary)
        
        # Get entry position on longer edge
        entry_pos = params.entry_position
        rad = np.radians(angle)
        
        # Point on boundary at entry position
        offset = (entry_pos - 0.5) * length
        entry_direction = Point(
            center.x + offset * np.cos(rad),
            center.y + offset * np.sin(rad)
        )
        
        # Find nearest point on boundary exterior
        boundary_line = LineString(boundary.exterior.coords)  
        nearest_on_boundary = boundary_line.interpolate(
            boundary_line.project(entry_direction)
        )
        
        # Find nearest point on ring
        nearest_on_ring = ring_road.interpolate(
            ring_road.project(nearest_on_boundary)
        )
        
        # Create connector line
        return LineString([
            (nearest_on_boundary.x, nearest_on_boundary.y),
            (nearest_on_ring.x, nearest_on_ring.y)
        ])
    
    def _generate_perimeter_road(
        self,
        boundary: Polygon,
        params: TemplateParams
    ) -> TemplateResult:
        """Fallback: Generate simple perimeter road."""
        buffer_dist = params.boundary_buffer
        inner = boundary.buffer(-buffer_dist)
        
        if inner.is_empty:
            return TemplateResult(roads=[], blocks=[boundary])
            
        road = LineString(inner.exterior.coords)
        
        return TemplateResult(
            roads=[road],
            blocks=[inner],
            entry_points=[Point(road.coords[0])],
            metadata={"template": self.name, "type": "perimeter_fallback"}
        )
    
    def get_params_schema(self) -> dict:
        """Return JSON schema for loop parameters."""
        schema = super().get_params_schema()
        schema["properties"]["boundary_buffer"] = {
            "type": "number",
            "default": 10.0,
            "description": "Distance from boundary to ring road (m)"
        }
        return schema
