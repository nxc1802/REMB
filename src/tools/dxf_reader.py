"""
DXF Boundary Extractor
======================
Reads actual cadastral boundaries from professional DXF files.

Features:
- Extract LWPOLYLINE entities
- Extract LINE entities and combine into polygon
- Convert to Shapely Polygon
- Export to GeoJSON format
"""

import ezdxf
from shapely.geometry import Polygon, LinearRing
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DXFBoundaryExtractor:
    """Extract cadastral boundaries from DXF files"""
    
    def __init__(self, dxf_path: str):
        """
        Initialize with DXF file path
        
        Args:
            dxf_path: Path to DXF file
        """
        self.dxf_path = dxf_path
        self.doc = None
        
        try:
            self.doc = ezdxf.readfile(dxf_path)
            logger.info(f"✅ Loaded DXF: {Path(dxf_path).name}")
            print(f"✅ Loaded DXF: {Path(dxf_path).name}")
        except Exception as e:
            logger.error(f"❌ Error loading DXF: {e}")
            print(f"❌ Error loading DXF: {e}")
            self.doc = None
    
    def extract_boundary_polygon(self, layer_name: Optional[str] = None) -> Optional[Polygon]:
        """
        Extract outer boundary polygon from DXF
        
        Tries multiple strategies:
        1. Find LWPOLYLINE on specified layer
        2. Find closed LWPOLYLINE entities
        3. Combine LINE entities to form boundary
        
        Args:
            layer_name: Optional specific layer to search
            
        Returns:
            Shapely Polygon or None
        """
        if self.doc is None:
            return None
        
        msp = self.doc.modelspace()
        
        # Strategy 1: Find LWPOLYLINE (most common for cadastral data)
        candidates = []
        
        # If layer specified, search that layer first
        if layer_name:
            for entity in msp.query(f'LWPOLYLINE[layer=="{layer_name}"]'):
                if self._is_valid_boundary(entity):
                    candidates.append(entity)
        
        # Search all LWPOLYLINE entities
        for entity in msp.query('LWPOLYLINE'):
            if self._is_valid_boundary(entity):
                candidates.append(entity)
        
        # Find the largest (outer boundary)
        if candidates:
            largest = max(candidates, key=lambda e: self._get_area(e))
            poly = self._lwpolyline_to_polygon(largest)
            if poly and poly.is_valid:
                logger.info(f"✅ Extracted boundary: {poly.area:.2f} m²")
                return poly
        
        # Strategy 2: Find closed LINE entities
        lines = list(msp.query('LINE'))
        if lines:
            poly = self._lines_to_polygon(lines)
            if poly and poly.is_valid:
                logger.info(f"✅ Extracted boundary from LINE entities: {poly.area:.2f} m²")
                return poly
        
        logger.warning("⚠️ No suitable boundary found in DXF")
        print("⚠️ No suitable boundary found in DXF")
        return None
    
    def _is_valid_boundary(self, entity) -> bool:
        """Check if LWPOLYLINE is suitable boundary"""
        try:
            # Must be closed or almost closed
            if hasattr(entity, 'close'):
                is_closed = entity.close
            else:
                points = list(entity.get_points())
                if len(points) < 3:
                    return False
                dist = ((points[0][0] - points[-1][0])**2 + 
                       (points[0][1] - points[-1][1])**2)**0.5
                is_closed = dist < 1  # within 1 unit
            
            # Must have reasonable area
            area = self._get_area(entity)
            return is_closed and area > 100  # At least 100 m²
        except Exception:
            return False
    
    def _get_area(self, entity) -> float:
        """Calculate polygon area from entity using shoelace formula"""
        try:
            points = list(entity.get_points())
            if len(points) < 3:
                return 0
            
            # Shoelace formula
            area = 0
            for i in range(len(points)):
                j = (i + 1) % len(points)
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            return abs(area) / 2
        except Exception:
            return 0
    
    def _lwpolyline_to_polygon(self, entity) -> Optional[Polygon]:
        """Convert LWPOLYLINE entity to Shapely Polygon"""
        try:
            points = list(entity.get_points('xy'))
            if len(points) < 3:
                return None
            
            # Ensure closed
            if points[0] != points[-1]:
                points.append(points[0])
            
            return Polygon(points)
        except Exception as e:
            logger.warning(f"⚠️ Error converting LWPOLYLINE: {e}")
            return None
    
    def _lines_to_polygon(self, lines: List) -> Optional[Polygon]:
        """Try to connect LINE entities into a polygon"""
        try:
            # Build point list by connecting lines
            points = []
            for line in lines:
                start = (line.dxf.start[0], line.dxf.start[1])
                end = (line.dxf.end[0], line.dxf.end[1])
                if start not in points:
                    points.append(start)
                if end not in points:
                    points.append(end)
            
            if len(points) < 3:
                return None
            
            return Polygon(points)
        except Exception as e:
            logger.warning(f"⚠️ Error converting LINE entities: {e}")
            return None
    
    def get_all_layers(self) -> List[str]:
        """List all layers in DXF"""
        if self.doc is None:
            return []
        return [layer.dxf.name for layer in self.doc.layers]
    
    def extract_to_json(self, layer_name: Optional[str] = None) -> Optional[Dict]:
        """
        Extract boundary and return as GeoJSON
        
        Returns:
            GeoJSON FeatureCollection dict or None
        """
        boundary = self.extract_boundary_polygon(layer_name)
        
        if boundary is None:
            return None
        
        coords = [list(boundary.exterior.coords)]
        
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coords
                },
                "properties": {
                    "name": Path(self.dxf_path).stem,
                    "area_m2": boundary.area,
                    "area_hectares": boundary.area / 10000,
                    "source": "DXF cadastral boundary",
                    "crs": "Local/Custom",
                    "dxf_layers": self.get_all_layers()
                }
            }]
        }
        
        return geojson
    
    def get_all_entities_info(self) -> Dict[str, int]:
        """Get count of all entity types in DXF"""
        if self.doc is None:
            return {}
        
        msp = self.doc.modelspace()
        entity_counts = {}
        
        for entity in msp:
            entity_type = entity.dxftype()
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        return entity_counts


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_boundary_from_dxf(dxf_path: str, layer_name: Optional[str] = None) -> Optional[Polygon]:
    """
    One-line function to load boundary from DXF
    
    Args:
        dxf_path: Path to DXF file
        layer_name: Optional layer name to search
        
    Returns:
        Shapely Polygon or None
    """
    extractor = DXFBoundaryExtractor(dxf_path)
    boundary = extractor.extract_boundary_polygon(layer_name)
    
    if boundary:
        print(f"✅ Loaded boundary: {boundary.area:.2f} m²")
        return boundary
    else:
        print("❌ Failed to extract boundary")
        return None


def save_boundary_as_json(dxf_path: str, json_path: str, layer_name: Optional[str] = None) -> Optional[Dict]:
    """
    Save DXF boundary as JSON for reproducibility
    
    Args:
        dxf_path: Path to DXF file
        json_path: Output JSON file path
        layer_name: Optional layer name to search
        
    Returns:
        GeoJSON dict or None
    """
    extractor = DXFBoundaryExtractor(dxf_path)
    geojson = extractor.extract_to_json(layer_name)
    
    if geojson:
        with open(json_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        print(f"✅ Saved to {json_path}")
        return geojson
    return None


def analyze_dxf(dxf_path: str) -> Dict:
    """
    Analyze DXF file and return summary
    
    Args:
        dxf_path: Path to DXF file
        
    Returns:
        Summary dict with layers, entities, etc.
    """
    extractor = DXFBoundaryExtractor(dxf_path)
    
    summary = {
        "file": dxf_path,
        "loaded": extractor.doc is not None,
        "layers": extractor.get_all_layers(),
        "entities": extractor.get_all_entities_info(),
    }
    
    boundary = extractor.extract_boundary_polygon()
    if boundary:
        summary["boundary"] = {
            "area_m2": boundary.area,
            "area_hectares": boundary.area / 10000,
            "bounds": boundary.bounds
        }
    
    return summary


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        dxf_file = sys.argv[1]
    else:
        dxf_file = 'examples/Lot Plan Bel air Technical Description.dxf'
    
    print(f"\n{'='*60}")
    print(f"DXF Boundary Extractor - Testing")
    print(f"{'='*60}\n")
    
    summary = analyze_dxf(dxf_file)
    
    print(f"File: {summary['file']}")
    print(f"Loaded: {summary['loaded']}")
    print(f"Layers: {len(summary['layers'])}")
    print(f"Entities: {summary['entities']}")
    
    if 'boundary' in summary:
        print(f"\nBoundary found:")
        print(f"  Area: {summary['boundary']['area_m2']:.2f} m²")
        print(f"  Area: {summary['boundary']['area_hectares']:.4f} hectares")
        print(f"  Bounds: {summary['boundary']['bounds']}")
