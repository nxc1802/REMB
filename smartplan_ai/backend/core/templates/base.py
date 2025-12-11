"""Base template class and common utilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.affinity import rotate, translate


@dataclass
class TemplateResult:
    """Result from template generation."""
    
    # Main roads (LineString list)
    roads: List[LineString] = field(default_factory=list)
    
    # Blocks created by roads (Polygon list)
    blocks: List[Polygon] = field(default_factory=list)
    
    # Entry/exit points
    entry_points: List[Point] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_geojson(self) -> dict:
        """Convert to GeoJSON FeatureCollection."""
        from shapely.geometry import mapping
        
        features = []
        
        # Roads
        for i, road in enumerate(self.roads):
            features.append({
                "type": "Feature",
                "geometry": mapping(road),
                "properties": {"type": "road", "index": i}
            })
            
        # Blocks
        for i, block in enumerate(self.blocks):
            features.append({
                "type": "Feature",
                "geometry": mapping(block),
                "properties": {"type": "block", "index": i, "area": block.area}
            })
            
        # Entry points
        for i, point in enumerate(self.entry_points):
            features.append({
                "type": "Feature",
                "geometry": mapping(point),
                "properties": {"type": "entry", "index": i}
            })
            
        return {
            "type": "FeatureCollection",
            "features": features
        }


@dataclass
class TemplateParams:
    """Common template parameters."""
    
    # Road dimensions
    main_road_width: float = 24.0  # m (2 lanes each direction)
    secondary_road_width: float = 12.0  # m
    
    # Grid settings
    cell_size: float = 100.0  # m (block size)
    
    # Entry point (relative to boundary, 0-1)
    entry_position: float = 0.5  # 0=start, 1=end of longer edge
    
    # Rotation angle (degrees)
    rotation: float = 0.0
    
    # Buffer from boundary
    boundary_buffer: float = 10.0  # m


class RoadTemplate(ABC):
    """Abstract base class for road skeleton templates."""
    
    # Template metadata
    name: str = "base"
    display_name: str = "Base Template"
    description: str = "Abstract base template"
    icon: str = "🛣️"
    
    @abstractmethod
    def generate(
        self, 
        boundary: Polygon,
        params: Optional[TemplateParams] = None
    ) -> TemplateResult:
        """Generate road skeleton for the given boundary.
        
        Args:
            boundary: Site boundary polygon
            params: Template parameters
            
        Returns:
            TemplateResult with roads, blocks, entry points
        """
        pass
    
    def get_params_schema(self) -> dict:
        """Return JSON schema for template parameters."""
        return {
            "type": "object",
            "properties": {
                "main_road_width": {
                    "type": "number",
                    "default": 24.0,
                    "description": "Main road width (m)"
                },
                "secondary_road_width": {
                    "type": "number", 
                    "default": 12.0,
                    "description": "Secondary road width (m)"
                },
                "cell_size": {
                    "type": "number",
                    "default": 100.0,
                    "description": "Block/cell size (m)"
                },
                "entry_position": {
                    "type": "number",
                    "default": 0.5,
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Entry position (0-1)"
                },
                "rotation": {
                    "type": "number",
                    "default": 0,
                    "description": "Rotation angle (degrees)"
                }
            }
        }
    
    def to_dict(self) -> dict:
        """Convert template info to dict."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "params_schema": self.get_params_schema()
        }
    
    # === Utility methods ===
    
    def _get_obb_info(self, polygon: Polygon) -> tuple:
        """Get OBB dimensions and orientation.
        
        Returns:
            (width, length, angle, center, corners)
        """
        obb = polygon.minimum_rotated_rectangle
        coords = list(obb.exterior.coords)[:4]
        
        # Calculate edge lengths
        edge1 = np.array(coords[1]) - np.array(coords[0])
        edge2 = np.array(coords[2]) - np.array(coords[1])
        
        len1 = np.linalg.norm(edge1)
        len2 = np.linalg.norm(edge2)
        
        # Width is shorter, length is longer
        if len1 <= len2:
            width, length = len1, len2
            angle = np.degrees(np.arctan2(edge2[1], edge2[0]))
        else:
            width, length = len2, len1
            angle = np.degrees(np.arctan2(edge1[1], edge1[0]))
            
        center = obb.centroid
        
        return width, length, angle, center, coords
    
    def _create_line_at_angle(
        self, 
        center: Point, 
        angle: float, 
        length: float
    ) -> LineString:
        """Create a line through center at given angle."""
        rad = np.radians(angle)
        dx = np.cos(rad) * length / 2
        dy = np.sin(rad) * length / 2
        
        return LineString([
            (center.x - dx, center.y - dy),
            (center.x + dx, center.y + dy)
        ])
    
    def _clip_to_boundary(
        self, 
        line: LineString, 
        boundary: Polygon
    ) -> LineString:
        """Clip line to boundary."""
        clipped = line.intersection(boundary)
        
        if clipped.is_empty:
            return LineString()
        if clipped.geom_type == 'LineString':
            return clipped
        if clipped.geom_type == 'MultiLineString':
            # Return longest segment
            return max(clipped.geoms, key=lambda g: g.length)
            
        return LineString()
    
    def _get_blocks_from_roads(
        self, 
        boundary: Polygon, 
        roads: List[LineString],
        buffer_width: float = 6.0
    ) -> List[Polygon]:
        """Extract blocks by subtracting road buffers from boundary."""
        from shapely.ops import unary_union
        
        if not roads:
            return [boundary]
            
        # Create road buffer
        road_buffers = [r.buffer(buffer_width) for r in roads if not r.is_empty]
        road_union = unary_union(road_buffers)
        
        # Subtract from boundary
        remaining = boundary.difference(road_union)
        
        if remaining.is_empty:
            return []
        if remaining.geom_type == 'Polygon':
            return [remaining]
        if remaining.geom_type == 'MultiPolygon':
            return list(remaining.geoms)
            
        return []


class TemplateRegistry:
    """Registry for road templates."""
    
    def __init__(self):
        self._templates: Dict[str, RoadTemplate] = {}
        
    def register(self, template: RoadTemplate):
        """Register a template."""
        self._templates[template.name] = template
        
    def get(self, name: str) -> Optional[RoadTemplate]:
        """Get template by name."""
        return self._templates.get(name)
        
    def list_all(self) -> List[dict]:
        """List all templates."""
        return [t.to_dict() for t in self._templates.values()]
        
    def list_names(self) -> List[str]:
        """List template names."""
        return list(self._templates.keys())
