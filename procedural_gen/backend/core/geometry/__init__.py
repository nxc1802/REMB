"""Geometry utilities package."""

from .shape_quality import (
    analyze_shape_quality,
    get_dominant_edge_vector,
    get_perpendicular_vector,
    get_obb_dimensions,
    classify_lot_type,
    DEFAULT_MIN_RECTANGULARITY,
    DEFAULT_MAX_ASPECT_RATIO,
    DEFAULT_MIN_LOT_AREA
)

from .polygon_utils import (
    get_elevation,
    normalize_geometry_list,
    merge_polygons,
    filter_by_min_area,
    sort_by_elevation,
    calculate_block_quality_ratio
)

__all__ = [
    # Shape quality
    "analyze_shape_quality",
    "get_dominant_edge_vector",
    "get_perpendicular_vector",
    "get_obb_dimensions",
    "classify_lot_type",
    "DEFAULT_MIN_RECTANGULARITY",
    "DEFAULT_MAX_ASPECT_RATIO",
    "DEFAULT_MIN_LOT_AREA",
    # Polygon utils
    "get_elevation",
    "normalize_geometry_list",
    "merge_polygons",
    "filter_by_min_area",
    "sort_by_elevation",
    "calculate_block_quality_ratio"
]
