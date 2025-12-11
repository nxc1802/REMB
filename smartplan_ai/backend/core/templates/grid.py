"""Grid Template - Orthogonal grid pattern.

    ┌──────────────────────────────┐
    │  │     │     │     │     │   │
    │──┼─────┼─────┼─────┼─────┼───│
    │  │     │     │     │     │   │
    │──┼─────┼─────┼─────┼─────┼───│
    │  │     │     │     │     │   │
    └──────────────────────────────┘

Best for: Flexible layouts, American-style industrial parks
"""

from typing import Optional, List
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate

from .base import RoadTemplate, TemplateResult, TemplateParams


class GridTemplate(RoadTemplate):
    """Orthogonal grid road pattern aligned to OBB."""
    
    name = "grid"
    display_name = "Bàn Cờ"
    description = "Lưới đường vuông góc kiểu Mỹ/Âu"
    icon = "🔲"
    
    def generate(
        self,
        boundary: Polygon,
        params: Optional[TemplateParams] = None
    ) -> TemplateResult:
        """Generate grid road skeleton.
        
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
        cell_size = params.cell_size
        
        # 1. Create horizontal roads (along length)
        num_h_roads = int(width / cell_size) + 1
        h_spacing = width / max(1, num_h_roads - 1) if num_h_roads > 1 else width
        
        for i in range(num_h_roads):
            # Offset from center (perpendicular to main axis)
            offset = (i - (num_h_roads - 1) / 2) * h_spacing
            
            # Calculate offset direction (perpendicular to main angle)
            perp_angle = total_angle + 90
            rad = np.radians(perp_angle)
            
            road_center = Point(
                center.x + offset * np.cos(rad),
                center.y + offset * np.sin(rad)
            )
            
            # Create road along main axis
            road = self._create_line_at_angle(road_center, total_angle, length * 1.5)
            road_clipped = self._clip_to_boundary(road, boundary)
            
            if not road_clipped.is_empty and road_clipped.length > 20:
                roads.append(road_clipped)
                
        # 2. Create vertical roads (along width)  
        num_v_roads = int(length / cell_size) + 1
        v_spacing = length / max(1, num_v_roads - 1) if num_v_roads > 1 else length
        
        for i in range(num_v_roads):
            # Offset from center (along main axis)
            offset = (i - (num_v_roads - 1) / 2) * v_spacing
            
            rad = np.radians(total_angle)
            
            road_center = Point(
                center.x + offset * np.cos(rad),
                center.y + offset * np.sin(rad)
            )
            
            # Create road perpendicular to main axis
            road = self._create_line_at_angle(
                road_center, 
                total_angle + 90, 
                width * 1.5
            )
            road_clipped = self._clip_to_boundary(road, boundary)
            
            if not road_clipped.is_empty and road_clipped.length > 20:
                roads.append(road_clipped)
                
        # 3. Entry points at corners
        entry_points = self._get_corner_entries(boundary)
        
        # 4. Extract blocks
        blocks = self._get_blocks_from_roads(
            boundary, roads,
            buffer_width=params.secondary_road_width / 2
        )
        
        return TemplateResult(
            roads=roads,
            blocks=blocks,
            entry_points=entry_points,
            metadata={
                "template": self.name,
                "grid_size": f"{num_h_roads}x{num_v_roads}",
                "cell_size": cell_size,
                "rotation": params.rotation
            }
        )
    
    def _get_corner_entries(self, boundary: Polygon) -> List[Point]:
        """Get entry points at boundary corners."""
        # Use OBB corners
        obb = boundary.minimum_rotated_rectangle
        coords = list(obb.exterior.coords)[:4]
        
        # Return first and third corners (diagonal)
        return [Point(coords[0]), Point(coords[2])]
    
    def get_params_schema(self) -> dict:
        """Return JSON schema for grid parameters."""
        schema = super().get_params_schema()
        schema["properties"]["cell_size"]["description"] = "Grid cell size (m)"
        return schema
