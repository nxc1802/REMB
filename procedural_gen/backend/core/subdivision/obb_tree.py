"""OBB (Oriented Bounding Box) Tree for hierarchical subdivision.

Recursively divides polygons using their oriented bounding boxes,
creating lots aligned to the dominant edge of each block.

Reference: docs/Procedural Generation.md - Section 2 (OBB Tree)
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import logging
from shapely.geometry import Polygon, LineString, Point, box
from shapely.affinity import rotate, translate

from core.geometry import get_obb_dimensions, get_dominant_edge_vector

logger = logging.getLogger(__name__)


@dataclass
class OBBTreeConfig:
    """Configuration for OBB Tree subdivision."""
    
    # Lot size constraints
    min_lot_area: float = 1000.0  # m²
    max_lot_area: float = 15000.0  # m² (increased for industrial)
    
    # Target dimensions
    target_lot_width: float = 40.0  # m
    min_lot_width: float = 20.0  # m
    max_lot_width: float = 100.0  # m
    
    # Aspect ratio limits (relaxed for industrial lots)
    max_aspect_ratio: float = 8.0
    
    # Tree limits
    max_depth: int = 6  # Reduced to prevent over-splitting
    
    # Split preferences
    prefer_perpendicular: bool = True  # Split perpendicular to longest edge
    
    # Quality thresholds
    min_rectangularity: float = 0.6


class OBBTreeNode:
    """Node in the OBB subdivision tree."""
    
    def __init__(self, polygon: Polygon, depth: int = 0):
        self.polygon = polygon
        self.depth = depth
        self.children: List['OBBTreeNode'] = []
        self.is_leaf: bool = True
        
    @property
    def area(self) -> float:
        return self.polygon.area
        
    def get_leaves(self) -> List['OBBTreeNode']:
        """Get all leaf nodes (final lots)."""
        if self.is_leaf:
            return [self]
        return sum([child.get_leaves() for child in self.children], [])


class OBBTree:
    """Hierarchical subdivision using Oriented Bounding Boxes.
    
    Creates lots by recursively splitting polygons along their
    OBB axes, ensuring lots are aligned to the dominant edge
    direction of each block.
    
    Algorithm:
    1. Compute OBB of polygon
    2. Find dominant edge (longest side)
    3. Split perpendicular to dominant edge
    4. Recurse until lots meet size constraints
    
    Example:
        >>> tree = OBBTree(block_polygon, config)
        >>> lots = tree.subdivide()
    """
    
    def __init__(
        self,
        polygon: Polygon,
        config: Optional[OBBTreeConfig] = None
    ):
        """Initialize OBB Tree.
        
        Args:
            polygon: Block polygon to subdivide
            config: Subdivision configuration
        """
        self.root_polygon = polygon
        self.config = config or OBBTreeConfig()
        self.root: Optional[OBBTreeNode] = None
        
    def subdivide(self) -> List[Polygon]:
        """Perform OBB-aligned grid subdivision.
        
        Uses a grid approach but aligns to the polygon's OBB orientation.
        
        Returns:
            List of lot polygons
        """
        logger.info(f"Starting OBB Tree subdivision, area={self.root_polygon.area:.0f}m²")
        
        # Get OBB info
        width, length, angle = get_obb_dimensions(self.root_polygon)
        obb = self.root_polygon.minimum_rotated_rectangle
        center = obb.centroid
        
        # Calculate grid dimensions
        target_width = self.config.target_lot_width
        target_depth = self.config.target_lot_width * 1.5  # Slightly deeper than wide
        
        # Number of divisions
        num_cols = max(1, int(width / target_width))
        num_rows = max(1, int(length / target_depth))
        
        # Cell sizes
        cell_width = width / num_cols
        cell_depth = length / num_rows
        
        logger.debug(f"Grid: {num_rows}x{num_cols}, cell={cell_width:.0f}x{cell_depth:.0f}m")
        
        lots = []
        
        # Get OBB corners
        obb_coords = list(obb.exterior.coords)[:4]
        
        # Calculate direction vectors from OBB
        import numpy as np
        p0 = np.array(obb_coords[0])
        p1 = np.array(obb_coords[1])
        p3 = np.array(obb_coords[3])
        
        vec_x = (p1 - p0) / np.linalg.norm(p1 - p0)  # Along width
        vec_y = (p3 - p0) / np.linalg.norm(p3 - p0)  # Along length
        
        # Generate grid cells aligned to OBB
        for i in range(num_rows):
            for j in range(num_cols):
                # Calculate cell corners in OBB space
                x0 = j * cell_width
                y0 = i * cell_depth
                x1 = (j + 1) * cell_width
                y1 = (i + 1) * cell_depth
                
                # Transform to world coordinates
                c0 = p0 + vec_x * x0 + vec_y * y0
                c1 = p0 + vec_x * x1 + vec_y * y0
                c2 = p0 + vec_x * x1 + vec_y * y1
                c3 = p0 + vec_x * x0 + vec_y * y1
                
                cell = Polygon([c0, c1, c2, c3, c0])
                
                # Clip to original polygon
                try:
                    clipped = cell.intersection(self.root_polygon)
                    
                    if clipped.is_empty:
                        continue
                        
                    if clipped.geom_type == 'Polygon':
                        if clipped.area >= self.config.min_lot_area * 0.5:
                            lots.append(clipped)
                    elif clipped.geom_type == 'MultiPolygon':
                        for part in clipped.geoms:
                            if part.area >= self.config.min_lot_area * 0.5:
                                lots.append(part)
                except Exception as e:
                    logger.warning(f"Cell clip failed: {e}")
                    continue
        
        logger.info(f"Subdivision complete: {len(lots)} lots")
        
        return lots
        
    def _subdivide_node(self, node: OBBTreeNode) -> bool:
        """Recursively subdivide a node.
        
        Args:
            node: Node to subdivide
            
        Returns:
            True if subdivision was performed
        """
        # Check stopping conditions
        if not self._should_split(node):
            return False
            
        # Find split line
        split_line = self._compute_split_line(node.polygon)
        
        if split_line is None:
            return False
            
        # Perform split
        children = self._split_polygon(node.polygon, split_line)
        
        if len(children) < 2:
            return False
            
        # Create child nodes and recurse
        node.is_leaf = False
        
        for child_poly in children:
            if child_poly.is_empty or child_poly.area < self.config.min_lot_area * 0.5:
                continue
                
            child_node = OBBTreeNode(child_poly, depth=node.depth + 1)
            node.children.append(child_node)
            
            # Recurse
            self._subdivide_node(child_node)
            
        return True
        
    def _should_split(self, node: OBBTreeNode) -> bool:
        """Determine if a node should be split further.
        
        Args:
            node: Node to check
            
        Returns:
            True if should continue splitting
        """
        area = node.polygon.area
        width, length, _ = get_obb_dimensions(node.polygon)
        aspect = length / width if width > 0 else float('inf')
        
        # Don't split if below minimum
        if area < self.config.min_lot_area * 2:
            return False
            
        # Depth limit
        if node.depth >= self.config.max_depth:
            return False
            
        # Always split if aspect ratio is too high (elongated)
        if aspect > self.config.max_aspect_ratio:
            return True
            
        # Don't split if already good size and aspect ratio
        if area <= self.config.max_lot_area:
            return False
            
        return True
        
    def _compute_split_line(self, polygon: Polygon) -> Optional[LineString]:
        """Compute the optimal split line for a polygon.
        
        Splits perpendicular to the longest dimension to reduce aspect ratio.
        
        Args:
            polygon: Polygon to compute split for
            
        Returns:
            Split line or None if cannot split
        """
        # Get OBB dimensions and orientation
        width, length, angle = get_obb_dimensions(polygon)
        
        # Can't split if too small in both dimensions
        if width < self.config.min_lot_width and length < self.config.min_lot_width:
            return None
            
        # Get OBB center
        obb = polygon.minimum_rotated_rectangle
        center = obb.centroid
        
        # Determine split direction:
        # Always split perpendicular to the longest dimension
        # This reduces aspect ratio with each split
        
        if length > width:
            # Length is longer - split perpendicular to length (cut across length)
            # This creates two shorter pieces
            split_angle = np.radians(angle)  # Perpendicular to length
        else:
            # Width is longer (or equal) - split perpendicular to width
            split_angle = np.radians(angle + 90)
            
        # Create split line through center
        diagonal = max(width, length) * 2
        
        dx = np.cos(split_angle) * diagonal
        dy = np.sin(split_angle) * diagonal
        
        split_line = LineString([
            (center.x - dx, center.y - dy),
            (center.x + dx, center.y + dy)
        ])
        
        return split_line
        
    def _split_polygon(
        self, 
        polygon: Polygon, 
        split_line: LineString
    ) -> List[Polygon]:
        """Split polygon along a line.
        
        Args:
            polygon: Polygon to split
            split_line: Line to split along
            
        Returns:
            List of resulting polygons
        """
        from shapely.ops import split
        
        try:
            # Use shapely split
            result = split(polygon, split_line)
            
            # Extract polygons
            children = []
            for geom in result.geoms:
                if geom.geom_type == 'Polygon' and not geom.is_empty:
                    # Clean up polygon
                    cleaned = geom.buffer(0)
                    if cleaned.geom_type == 'Polygon':
                        children.append(cleaned)
                    elif cleaned.geom_type == 'MultiPolygon':
                        children.extend(list(cleaned.geoms))
                        
            return children
            
        except Exception as e:
            logger.warning(f"Split failed: {e}")
            return []


def obb_tree_subdivide(
    polygon: Polygon,
    min_lot_area: float = 1000.0,
    max_lot_area: float = 10000.0,
    target_lot_width: float = 40.0,
    max_depth: int = 8
) -> List[Polygon]:
    """Convenience function for OBB Tree subdivision.
    
    Args:
        polygon: Block polygon to subdivide
        min_lot_area: Minimum lot area (m²)
        max_lot_area: Maximum lot area (m²)
        target_lot_width: Target lot width (m)
        max_depth: Maximum tree depth
        
    Returns:
        List of lot polygons
    """
    config = OBBTreeConfig(
        min_lot_area=min_lot_area,
        max_lot_area=max_lot_area,
        target_lot_width=target_lot_width,
        max_depth=max_depth
    )
    
    tree = OBBTree(polygon, config)
    return tree.subdivide()
