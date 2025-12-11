"""Preprocessing module for DXF parsing and Block extraction."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union, split
import logging

from .polygon_utils import polygon_to_coords, coords_to_polygon

logger = logging.getLogger(__name__)


@dataclass
class Block:
    """A subdividable block extracted from boundary minus roads."""
    
    id: str
    polygon: Polygon
    area: float = 0.0
    assets: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.polygon and self.area == 0:
            self.area = self.polygon.area
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "polygon": polygon_to_coords(self.polygon),
            "area": self.area,
            "assets": self.assets
        }


def extract_blocks(
    boundary: Polygon,
    road_network: List[LineString],
    road_width: float = 12.0,
    min_block_area: float = 500.0
) -> List[Block]:
    """Extract blocks by subtracting road network from boundary.
    
    Block = Boundary - Road_Network (buffered roads)
    
    Args:
        boundary: Site boundary polygon
        road_network: List of road centerlines
        road_width: Road width in meters (for buffering)
        min_block_area: Minimum block area to keep (m²)
        
    Returns:
        List of Block objects
    """
    if boundary is None or boundary.is_empty:
        logger.warning("Empty boundary provided")
        return []
    
    if not road_network:
        # No roads - entire boundary is one block
        return [Block(id="B1", polygon=boundary, area=boundary.area)]
    
    # Buffer roads to create road polygons
    road_polygons = []
    for road in road_network:
        if road and not road.is_empty:
            buffered = road.buffer(road_width / 2, cap_style=2)  # flat caps
            if not buffered.is_empty:
                road_polygons.append(buffered)
    
    if not road_polygons:
        return [Block(id="B1", polygon=boundary, area=boundary.area)]
    
    # Merge all road polygons
    road_union = unary_union(road_polygons)
    
    # Subtract roads from boundary
    remaining = boundary.difference(road_union)
    
    # Extract individual blocks
    blocks = []
    block_id = 1
    
    if remaining.is_empty:
        logger.warning("No blocks remaining after road subtraction")
        return []
    
    # Handle both Polygon and MultiPolygon results
    if remaining.geom_type == 'Polygon':
        geometries = [remaining]
    elif remaining.geom_type == 'MultiPolygon':
        geometries = list(remaining.geoms)
    else:
        logger.warning(f"Unexpected geometry type: {remaining.geom_type}")
        return []
    
    for geom in geometries:
        if geom.area >= min_block_area:
            blocks.append(Block(
                id=f"B{block_id}",
                polygon=geom,
                area=geom.area
            ))
            block_id += 1
    
    logger.info(f"Extracted {len(blocks)} blocks from boundary")
    return blocks


def parse_road_from_geojson(geojson: dict) -> Optional[LineString]:
    """Parse road LineString from GeoJSON feature.
    
    Args:
        geojson: GeoJSON Feature dict
        
    Returns:
        Shapely LineString or None
    """
    try:
        geometry = geojson.get("geometry", geojson)
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates", [])
        
        if geom_type == "LineString":
            return LineString(coords)
        elif geom_type == "MultiLineString":
            # Return first line or merge
            if coords:
                return LineString(coords[0])
        
        return None
    except Exception as e:
        logger.warning(f"Failed to parse road: {e}")
        return None


def parse_boundary_from_geojson(geojson: dict) -> Optional[Polygon]:
    """Parse boundary Polygon from GeoJSON.
    
    Args:
        geojson: GeoJSON Feature or FeatureCollection
        
    Returns:
        Shapely Polygon or None
    """
    try:
        # Handle FeatureCollection
        if geojson.get("type") == "FeatureCollection":
            features = geojson.get("features", [])
            for feature in features:
                poly = parse_boundary_from_geojson(feature)
                if poly:
                    return poly
            return None
        
        # Handle Feature
        geometry = geojson.get("geometry", geojson)
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates", [])
        
        if geom_type == "Polygon":
            return Polygon(coords[0] if coords else [])
        elif geom_type == "MultiPolygon":
            # Return largest polygon
            polys = [Polygon(c[0]) for c in coords if c]
            return max(polys, key=lambda p: p.area) if polys else None
        
        return None
    except Exception as e:
        logger.warning(f"Failed to parse boundary: {e}")
        return None


def blocks_to_geojson(blocks: List[Block]) -> dict:
    """Convert blocks to GeoJSON FeatureCollection.
    
    Args:
        blocks: List of Block objects
        
    Returns:
        GeoJSON FeatureCollection dict
    """
    features = []
    
    for block in blocks:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_to_coords(block.polygon) + [polygon_to_coords(block.polygon)[0]]]
            },
            "properties": {
                "id": block.id,
                "area": block.area,
                "asset_count": len(block.assets)
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }
