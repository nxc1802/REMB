"""Validation module - The Gatekeeper.

This is the most critical module that ensures AI-generated assets
do not violate spatial constraints.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from shapely.geometry import Polygon, shape
import logging

from .polygon_utils import coords_to_polygon

logger = logging.getLogger(__name__)


def has_real_overlap(poly1: Polygon, poly2: Polygon, min_area: float = 0.1) -> bool:
    """Check if two polygons actually overlap (not just touch at edge/corner).
    
    Args:
        poly1: First polygon
        poly2: Second polygon  
        min_area: Minimum intersection area to be considered a real overlap
        
    Returns:
        True if they have a real overlap with area > min_area
    """
    if not poly1.intersects(poly2):
        return False
    intersection = poly1.intersection(poly2)
    return intersection.area > min_area


@dataclass
class ValidationResult:
    """Result of validation check."""
    
    success: bool
    merged_assets: List[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.merged_assets is None:
            self.merged_assets = []


def validate_and_merge(
    boundary: Polygon,
    existing_assets: List[Dict[str, Any]],
    new_assets: List[Dict[str, Any]],
    margin: float = 1.0
) -> ValidationResult:
    """Validate new assets and merge with existing if valid.
    
    This is the Gatekeeper function that ensures:
    1. All new_assets are within boundary
    2. new_assets do not overlap with existing_assets
    3. new_assets do not overlap with each other
    
    Args:
        boundary: Site boundary polygon
        existing_assets: List of existing asset dicts with 'type' and 'polygon'
        new_assets: List of new asset dicts from LLM with 'type' and 'polygon'
        margin: Safety margin in meters (assets should maintain this distance)
        
    Returns:
        ValidationResult with success status and merged assets or errors
    """
    errors = []
    warnings = []
    
    if boundary is None or boundary.is_empty:
        return ValidationResult(
            success=False,
            errors=["Boundary is empty or invalid"]
        )
    
    # Convert existing assets to polygons
    existing_polygons: List[Tuple[int, Polygon]] = []
    for idx, asset in enumerate(existing_assets):
        poly = _extract_polygon(asset)
        if poly:
            existing_polygons.append((idx, poly))
    
    # Validate and convert new assets
    valid_new_assets = []
    new_polygons: List[Tuple[int, Polygon]] = []
    
    for idx, asset in enumerate(new_assets):
        poly = _extract_polygon(asset)
        
        if poly is None:
            errors.append(f"Asset mới #{idx} có polygon không hợp lệ")
            continue
        
        asset_type = asset.get("type", "unknown")
        
        # Rule 1: Boundary Check - Clip to boundary if partial overlap
        if not boundary.contains(poly):
            if boundary.intersects(poly):
                # Clip to boundary instead of rejecting
                clipped = poly.intersection(boundary)
                if clipped.is_empty or clipped.area < 10:  # Too small after clipping
                    errors.append(
                        f"Asset '{asset_type}' #{idx} quá nhỏ sau khi cắt theo ranh giới"
                    )
                    continue
                # Update the polygon to clipped version
                if clipped.geom_type == 'Polygon':
                    poly = clipped
                    # Update asset polygon coords
                    asset["polygon"] = list(clipped.exterior.coords)
                    warnings.append(f"Asset '{asset_type}' #{idx} đã được cắt theo ranh giới")
                else:
                    # MultiPolygon or other - use largest
                    if hasattr(clipped, 'geoms'):
                        poly = max(clipped.geoms, key=lambda g: g.area)
                        asset["polygon"] = list(poly.exterior.coords)
                        warnings.append(f"Asset '{asset_type}' #{idx} đã được cắt theo ranh giới")
                    else:
                        errors.append(f"Asset '{asset_type}' #{idx} không thể cắt theo ranh giới")
                        continue
            else:
                errors.append(
                    f"Asset '{asset_type}' #{idx} nằm hoàn toàn ngoài ranh giới"
                )
                continue
        
        # Check margin from boundary
        buffered_boundary = boundary.buffer(-margin)
        if not buffered_boundary.is_empty and not buffered_boundary.contains(poly):
            warnings.append(
                f"Asset '{asset_type}' #{idx} quá gần ranh giới (< {margin}m)"
            )
        
        # Rule 2a: Collision with existing assets
        collision_found = False
        for exist_idx, exist_poly in existing_polygons:
            if has_real_overlap(poly, exist_poly):
                exist_type = existing_assets[exist_idx].get("type", "unknown")
                # Allow roads to overlap existing roads (edit/replace scenario)
                if asset_type == "internal_road" and exist_type == "internal_road":
                    warnings.append(f"Đường mới #{idx} giao với đường cũ - có thể là chỉnh sửa")
                    continue
                errors.append(
                    f"Asset '{asset_type}' #{idx} đè lên asset cũ '{exist_type}'"
                )
                collision_found = True
                break
        
        if collision_found:
            continue
        
        # Rule 2b: Collision with other new assets (skip for roads - they can intersect)
        if asset_type != "internal_road":
            for new_idx, new_poly in new_polygons:
                if has_real_overlap(poly, new_poly):
                    other_type = valid_new_assets[new_idx].get("type", "unknown")
                    # Allow roads to intersect other roads
                    if other_type == "internal_road":
                        continue
                    errors.append(
                        f"Asset '{asset_type}' #{idx} đè lên asset mới '{other_type}' #{new_idx}"
                    )
                    collision_found = True
                    break
        
        if collision_found:
            continue
        
        # Asset passed all checks
        new_polygons.append((len(valid_new_assets), poly))
        valid_new_assets.append(asset)
    
    # If any errors, return failure
    if errors:
        return ValidationResult(
            success=False,
            errors=errors,
            warnings=warnings
        )
    
    # Merge assets
    merged = existing_assets + valid_new_assets
    
    return ValidationResult(
        success=True,
        merged_assets=merged,
        warnings=warnings
    )


def _extract_polygon(asset: Dict[str, Any]) -> Optional[Polygon]:
    """Extract Shapely Polygon from asset dict.
    
    Args:
        asset: Asset dict with 'polygon' (coords) or 'geometry' (GeoJSON)
        
    Returns:
        Shapely Polygon or None
    """
    try:
        # Try 'polygon' field (coordinate list)
        if "polygon" in asset:
            coords = asset["polygon"]
            
            # Helper to auto-fix 2-point lines (e.g. roads)
            if coords and len(coords) == 2:
                from shapely.geometry import LineString
                line = LineString(coords)
                return line.buffer(2.0) # Default buffer for lines
            
            return coords_to_polygon(coords)
        
        # Try 'geometry' field (GeoJSON format)
        if "geometry" in asset:
            return shape(asset["geometry"])
        
        return None
    except Exception as e:
        logger.warning(f"Failed to extract polygon: {e}")
        return None


def check_asset_spacing(
    assets: List[Dict[str, Any]],
    min_spacing: float = 5.0
) -> List[str]:
    """Check spacing between all assets.
    
    Args:
        assets: List of asset dicts
        min_spacing: Minimum distance in meters
        
    Returns:
        List of warning messages
    """
    warnings = []
    polygons = []
    
    for idx, asset in enumerate(assets):
        poly = _extract_polygon(asset)
        if poly:
            polygons.append((idx, asset.get("type", "unknown"), poly))
    
    # Check pairwise distances
    for i in range(len(polygons)):
        for j in range(i + 1, len(polygons)):
            idx_i, type_i, poly_i = polygons[i]
            idx_j, type_j, poly_j = polygons[j]
            
            distance = poly_i.distance(poly_j)
            if distance < min_spacing:
                warnings.append(
                    f"Asset '{type_i}' và '{type_j}' quá gần nhau ({distance:.1f}m < {min_spacing}m)"
                )
    
    return warnings


def calculate_coverage(
    boundary: Polygon,
    assets: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Calculate land coverage statistics.
    
    Args:
        boundary: Site boundary
        assets: List of placed assets
        
    Returns:
        Dict with coverage statistics
    """
    if boundary is None or boundary.is_empty:
        return {"total_area": 0, "used_area": 0, "coverage_ratio": 0}
    
    total_area = boundary.area
    used_area = 0
    
    for asset in assets:
        poly = _extract_polygon(asset)
        if poly:
            used_area += poly.area
    
    return {
        "total_area": total_area,
        "used_area": used_area,
        "free_area": total_area - used_area,
        "coverage_ratio": used_area / total_area if total_area > 0 else 0
    }
