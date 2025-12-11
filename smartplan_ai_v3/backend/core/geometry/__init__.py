"""Geometry utilities for polygon operations and validation."""

from .polygon_utils import (
    polygon_to_coords,
    coords_to_polygon,
    calculate_centroid,
    buffer_polygon,
)
from .validation import validate_and_merge, ValidationResult, calculate_coverage
from .preprocessing import extract_blocks, Block

__all__ = [
    "polygon_to_coords",
    "coords_to_polygon", 
    "calculate_centroid",
    "buffer_polygon",
    "validate_and_merge",
    "ValidationResult",
    "calculate_coverage",
    "extract_blocks",
    "Block",
]

