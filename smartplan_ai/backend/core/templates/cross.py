"""Cross Template - Two main axes crossing at center.

    ┌──────────────────────────────┐
    │              │               │
    │              │               │
    │──────────────┼───────────────│
    │              │               │
    │              │               │
    └──────────────────────────────┘

Best for: Large sites, sites with multiple entry points
"""

from typing import Optional, List
import numpy as np
from shapely.geometry import Polygon, LineString, Point

from .base import RoadTemplate, TemplateResult, TemplateParams


class CrossTemplate(RoadTemplate):
    """Two perpendicular main axes crossing at center."""
    
    name = "cross"
    display_name = "Chữ Thập"
    description = "Hai trục chính cắt nhau tại tâm"
    icon = "✚"
    
    def generate(
        self,
        boundary: Polygon,
        params: Optional[TemplateParams] = None
    ) -> TemplateResult:
        """Generate cross road skeleton.
        
        Args:
            boundary: Site boundary
            params: Template parameters
            
        Returns:
            TemplateResult with roads and blocks
        """
        params = params or TemplateParams()
        
        # Get OBB info
        width, length, angle, center, corners = self._get_obb_info(boundary)
        
        # Apply rotation
        total_angle = angle + params.rotation
        
        roads = []
        
        # 1. Create main horizontal axis (along length)
        main_axis = self._create_line_at_angle(center, total_angle, length * 1.5)
        main_clipped = self._clip_to_boundary(main_axis, boundary)
        
        if not main_clipped.is_empty:
            roads.append(main_clipped)
            
        # 2. Create perpendicular axis (along width)
        cross_axis = self._create_line_at_angle(center, total_angle + 90, width * 1.5)
        cross_clipped = self._clip_to_boundary(cross_axis, boundary)
        
        if not cross_clipped.is_empty:
            roads.append(cross_clipped)
            
        # 3. Entry points at all 4 axis endpoints
        entry_points = self._get_axis_endpoints(main_clipped, cross_clipped)
        
        # 4. Extract 4 quadrant blocks
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
                "main_axis_length": main_clipped.length if not main_clipped.is_empty else 0,
                "cross_axis_length": cross_clipped.length if not cross_clipped.is_empty else 0,
                "quadrants": len(blocks),
                "rotation": params.rotation
            }
        )
    
    def _get_axis_endpoints(
        self,
        main_axis: LineString,
        cross_axis: LineString
    ) -> List[Point]:
        """Get entry points at axis endpoints."""
        entry_points = []
        
        for axis in [main_axis, cross_axis]:
            if not axis.is_empty:
                coords = list(axis.coords)
                if len(coords) >= 2:
                    entry_points.append(Point(coords[0]))
                    entry_points.append(Point(coords[-1]))
                    
        return entry_points
    
    def get_params_schema(self) -> dict:
        """Return JSON schema for cross parameters."""
        schema = super().get_params_schema()
        # No additional params needed
        return schema
