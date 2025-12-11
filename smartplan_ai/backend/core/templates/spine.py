"""Spine Template - Central axis with perpendicular branches.

    ┌──────────────────────────────┐
    │                              │
    │    ════════════════════════  │  ← Main spine
    │    │    │    │    │    │     │
    │    │    │    │    │    │     │  ← Perpendicular branches
    │    │    │    │    │    │     │
    └──────────────────────────────┘

Best for: Long rectangular sites, industrial parks with central logistics axis
"""

from typing import Optional, List
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate

from .base import RoadTemplate, TemplateResult, TemplateParams


class SpineTemplate(RoadTemplate):
    """Central spine road with perpendicular branches."""
    
    name = "spine"
    display_name = "Trục Trung Tâm"
    description = "Trục đường lớn giữa đất với các nhánh xương cá hai bên"
    icon = "🦴"
    
    def generate(
        self,
        boundary: Polygon,
        params: Optional[TemplateParams] = None
    ) -> TemplateResult:
        """Generate spine road skeleton.
        
        Args:
            boundary: Site boundary
            params: Template parameters
            
        Returns:
            TemplateResult with roads and blocks
        """
        params = params or TemplateParams()
        
        # Get OBB info
        width, length, angle, center, corners = self._get_obb_info(boundary)
        
        # Apply rotation if specified
        total_angle = angle + params.rotation
        
        roads = []
        
        # 1. Create main spine along longer axis
        spine = self._create_line_at_angle(center, total_angle, length * 1.5)
        spine_clipped = self._clip_to_boundary(spine, boundary)
        
        if not spine_clipped.is_empty:
            roads.append(spine_clipped)
            
        # 2. Create perpendicular branches
        branch_angle = total_angle + 90
        branch_spacing = params.cell_size
        
        # Calculate number of branches
        num_branches = int(length / branch_spacing)
        
        if num_branches > 1:
            # Start and end offsets
            start_offset = branch_spacing / 2
            
            for i in range(num_branches):
                # Position along spine
                offset = start_offset + i * branch_spacing - length / 2
                
                # Branch center point
                rad = np.radians(total_angle)
                branch_center = Point(
                    center.x + offset * np.cos(rad),
                    center.y + offset * np.sin(rad)
                )
                
                # Create branch
                branch = self._create_line_at_angle(
                    branch_center, 
                    branch_angle,
                    width * 1.5
                )
                branch_clipped = self._clip_to_boundary(branch, boundary)
                
                if not branch_clipped.is_empty and branch_clipped.length > 20:
                    roads.append(branch_clipped)
                    
        # 3. Get entry point (on longer edge at entry_position)
        entry_points = self._get_entry_points(boundary, spine_clipped, params)
        
        # 4. Extract blocks
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
                "spine_length": spine_clipped.length if not spine_clipped.is_empty else 0,
                "branch_count": len(roads) - 1,
                "rotation": params.rotation
            }
        )
    
    def _get_entry_points(
        self,
        boundary: Polygon,
        spine: LineString,
        params: TemplateParams
    ) -> List[Point]:
        """Get entry points where spine meets boundary."""
        if spine.is_empty:
            return []
            
        # Get spine endpoints (they should be on boundary)
        coords = list(spine.coords)
        if len(coords) >= 2:
            return [Point(coords[0]), Point(coords[-1])]
            
        return []
    
    def get_params_schema(self) -> dict:
        """Return JSON schema for spine parameters."""
        schema = super().get_params_schema()
        schema["properties"]["branch_spacing"] = {
            "type": "number",
            "default": 100.0,
            "description": "Distance between branches (m)"
        }
        return schema
