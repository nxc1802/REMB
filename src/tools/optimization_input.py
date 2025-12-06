"""
Optimization Input Format
========================
JSON Intermediate Format for Optimization Pipeline.
Allows reproducibility, testing, and GPU acceleration.

Features:
- Standardized input format as dataclass
- JSON serialization/deserialization
- Configuration parameters for optimization
- Integration with DXF reader
"""

import json
from shapely.geometry import Polygon, shape
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptimizationInput:
    """Standard input format for optimization"""
    
    # Cadastral boundary (GeoJSON Polygon)
    boundary_geojson: Dict
    
    # Metadata
    site_name: str
    site_area_m2: float
    site_area_ha: float
    
    # Road configuration
    road_main_width: float = 30.0
    road_internal_width: float = 15.0
    
    # Setback and spacing
    sidewalk_width: float = 4.0
    setback_distance: float = 6.0
    plot_spacing: float = 10.0
    
    # Lot size constraints
    min_lot_width: float = 20.0
    max_lot_width: float = 80.0
    target_lot_width: float = 40.0
    min_lot_depth: float = 30.0
    max_lot_depth: float = 100.0
    target_lot_depth: float = 50.0
    
    # Optional constraints
    protected_zones: Optional[List[Dict]] = None
    existing_structures: Optional[List[Dict]] = None
    utilities: Optional[List[Dict]] = None
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(asdict(self), indent=2)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_file(self, filepath: str):
        """Save to JSON file"""
        with open(filepath, 'w') as f:
            f.write(self.to_json())
        logger.info(f"✅ Saved optimization input to {filepath}")
        print(f"✅ Saved optimization input to {filepath}")
    
    @classmethod
    def from_file(cls, filepath: str) -> 'OptimizationInput':
        """Load from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle None values for optional fields
        for field_name in ['protected_zones', 'existing_structures', 'utilities']:
            if field_name not in data:
                data[field_name] = None
        
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OptimizationInput':
        """Create from dictionary"""
        return cls(**data)
    
    def get_boundary_polygon(self) -> Polygon:
        """Get Shapely Polygon from GeoJSON"""
        return shape(self.boundary_geojson['features'][0]['geometry'])
    
    def get_boundary_bounds(self) -> tuple:
        """Get bounding box of boundary"""
        poly = self.get_boundary_polygon()
        return poly.bounds  # (minx, miny, maxx, maxy)


# =============================================================================
# CREATE INPUT FROM DXF
# =============================================================================

def create_optimization_input_from_dxf(
    dxf_path: str, 
    config: Optional[Dict] = None
) -> OptimizationInput:
    """
    Complete pipeline: DXF → GeoJSON → OptimizationInput
    
    Args:
        dxf_path: Path to DXF file
        config: Optional configuration overrides
        
    Returns:
        OptimizationInput object
    """
    from src.tools.dxf_reader import DXFBoundaryExtractor
    
    # Extract boundary
    extractor = DXFBoundaryExtractor(dxf_path)
    geojson = extractor.extract_to_json()
    
    if not geojson:
        raise ValueError(f"Failed to extract boundary from {dxf_path}")
    
    # Get area info
    boundary_polygon = shape(geojson['features'][0]['geometry'])
    area_m2 = boundary_polygon.area
    area_ha = area_m2 / 10000
    
    # Default configuration
    default_config = {
        'road_main_width': 30.0,
        'road_internal_width': 15.0,
        'sidewalk_width': 4.0,
        'setback_distance': 6.0,
        'plot_spacing': 10.0,
        'min_lot_width': 20.0,
        'max_lot_width': 80.0,
        'target_lot_width': 40.0,
        'min_lot_depth': 30.0,
        'max_lot_depth': 100.0,
        'target_lot_depth': 50.0,
    }
    
    if config:
        default_config.update(config)
    
    # Create input
    opt_input = OptimizationInput(
        boundary_geojson=geojson,
        site_name=geojson['features'][0]['properties']['name'],
        site_area_m2=area_m2,
        site_area_ha=area_ha,
        **default_config
    )
    
    logger.info(f"✅ Created optimization input for {opt_input.site_name}")
    print(f"✅ Created optimization input: {opt_input.site_name} ({area_ha:.2f} ha)")
    
    return opt_input


def create_optimization_input_from_polygon(
    polygon: Polygon,
    site_name: str = "Custom Site",
    config: Optional[Dict] = None
) -> OptimizationInput:
    """
    Create OptimizationInput from Shapely Polygon
    
    Args:
        polygon: Shapely Polygon object
        site_name: Name of the site
        config: Optional configuration overrides
        
    Returns:
        OptimizationInput object
    """
    # Create GeoJSON
    coords = [list(polygon.exterior.coords)]
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": coords
            },
            "properties": {
                "name": site_name,
                "area_m2": polygon.area,
                "area_hectares": polygon.area / 10000,
                "source": "Manual input",
            }
        }]
    }
    
    area_m2 = polygon.area
    area_ha = area_m2 / 10000
    
    # Default configuration
    default_config = {
        'road_main_width': 30.0,
        'road_internal_width': 15.0,
        'sidewalk_width': 4.0,
        'setback_distance': 6.0,
        'plot_spacing': 10.0,
        'min_lot_width': 20.0,
        'max_lot_width': 80.0,
        'target_lot_width': 40.0,
        'min_lot_depth': 30.0,
        'max_lot_depth': 100.0,
        'target_lot_depth': 50.0,
    }
    
    if config:
        default_config.update(config)
    
    return OptimizationInput(
        boundary_geojson=geojson,
        site_name=site_name,
        site_area_m2=area_m2,
        site_area_ha=area_ha,
        **default_config
    )


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == '__main__':
    import sys
    
    print(f"\n{'='*60}")
    print(f"Optimization Input Format - Testing")
    print(f"{'='*60}\n")
    
    # Test with DXF file
    if len(sys.argv) > 1:
        dxf_file = sys.argv[1]
    else:
        dxf_file = 'examples/Lot Plan Bel air Technical Description.dxf'
    
    try:
        opt_input = create_optimization_input_from_dxf(dxf_file)
        
        print(f"\nSite: {opt_input.site_name}")
        print(f"Area: {opt_input.site_area_m2:.2f} m² ({opt_input.site_area_ha:.4f} ha)")
        print(f"Road width: {opt_input.road_main_width}m (main), {opt_input.road_internal_width}m (internal)")
        print(f"Lot size: {opt_input.min_lot_width}-{opt_input.max_lot_width}m width")
        
        # Save to JSON
        json_path = 'output/optimization_input.json'
        opt_input.to_file(json_path)
        
        # Load back
        loaded = OptimizationInput.from_file(json_path)
        print(f"\n✅ Successfully saved and loaded from {json_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
