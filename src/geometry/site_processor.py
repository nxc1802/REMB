"""
Site Processor - Digital Twin Initialization
Handles site boundary import, normalization, and buildable area calculation
"""
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.validation import make_valid
from shapely.ops import unary_union
import json
from pathlib import Path
from typing import Optional, List, Tuple, Union
import logging
import yaml

from src.models.domain import SiteBoundary, Constraint, ConstraintType

logger = logging.getLogger(__name__)


class SiteProcessor:
    """
    Site boundary processor for CAD/GIS file import and normalization
    
    Responsibilities:
    - Import Shapefile, GeoJSON, DXF files
    - Normalize and validate geometry
    - Calculate buildable area after constraints
    - Identify no-build zones
    """
    
    def __init__(self, regulations_path: str = "config/regulations.yaml"):
        """
        Initialize site processor
        
        Args:
            regulations_path: Path to regulations YAML
        """
        self.regulations_path = Path(regulations_path)
        self.regulations = self._load_regulations()
        self.logger = logging.getLogger(__name__)
    
    def _load_regulations(self) -> dict:
        """Load regulations from YAML"""
        if not self.regulations_path.exists():
            return {}
        with open(self.regulations_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def import_from_shapefile(self, filepath: str) -> SiteBoundary:
        """
        Import site boundary from Shapefile (.shp)
        
        Args:
            filepath: Path to .shp file
            
        Returns:
            SiteBoundary object
        """
        self.logger.info(f"Importing Shapefile: {filepath}")
        
        gdf = gpd.read_file(filepath)
        
        if len(gdf) == 0:
            raise ValueError("Shapefile contains no geometry")
        
        # Get the first geometry (or union all)
        if len(gdf) == 1:
            geometry = gdf.geometry.iloc[0]
        else:
            geometry = unary_union(gdf.geometry)
        
        # Ensure it's a Polygon
        if isinstance(geometry, MultiPolygon):
            geometry = max(geometry.geoms, key=lambda g: g.area)
        
        # Validate and fix geometry
        geometry = self._normalize_geometry(geometry)
        
        # Create SiteBoundary
        site = SiteBoundary(
            geometry=geometry,
            area_sqm=geometry.area,
            metadata={
                'source': filepath,
                'crs': str(gdf.crs) if gdf.crs else 'unknown'
            }
        )
        
        # Calculate buildable area
        self._calculate_buildable_area(site)
        
        return site
    
    def import_from_geojson(self, filepath: str) -> SiteBoundary:
        """
        Import site boundary from GeoJSON file
        
        Args:
            filepath: Path to .geojson file
            
        Returns:
            SiteBoundary object
        """
        self.logger.info(f"Importing GeoJSON: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle FeatureCollection or single Feature
        if data.get('type') == 'FeatureCollection':
            features = data.get('features', [])
            if not features:
                raise ValueError("GeoJSON contains no features")
            geometries = [shape(f['geometry']) for f in features]
            geometry = unary_union(geometries)
        elif data.get('type') == 'Feature':
            geometry = shape(data['geometry'])
        else:
            geometry = shape(data)
        
        # Ensure it's a Polygon
        if isinstance(geometry, MultiPolygon):
            geometry = max(geometry.geoms, key=lambda g: g.area)
        
        geometry = self._normalize_geometry(geometry)
        
        site = SiteBoundary(
            geometry=geometry,
            area_sqm=geometry.area,
            metadata={'source': filepath}
        )
        
        self._calculate_buildable_area(site)
        
        return site
    
    def import_from_dxf(self, filepath: str) -> SiteBoundary:
        """
        Import site boundary from DXF (AutoCAD) file
        
        Args:
            filepath: Path to .dxf file
            
        Returns:
            SiteBoundary object
        """
        import ezdxf
        
        self.logger.info(f"Importing DXF: {filepath}")
        
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()
        
        # Find closed polylines or LWPolylines
        polygons = []
        
        for entity in msp:
            if entity.dxftype() == 'LWPOLYLINE':
                if entity.closed:
                    points = list(entity.get_points())
                    if len(points) >= 3:
                        polygons.append(Polygon([(p[0], p[1]) for p in points]))
            
            elif entity.dxftype() == 'POLYLINE':
                if entity.is_closed:
                    points = list(entity.points())
                    if len(points) >= 3:
                        polygons.append(Polygon([(p[0], p[1]) for p in points]))
            
            elif entity.dxftype() == 'LINE':
                # Lines would need to be assembled into polygons
                pass
        
        if not polygons:
            raise ValueError("No closed polygons found in DXF file")
        
        # Get the largest polygon as site boundary
        geometry = max(polygons, key=lambda p: p.area)
        geometry = self._normalize_geometry(geometry)
        
        site = SiteBoundary(
            geometry=geometry,
            area_sqm=geometry.area,
            metadata={
                'source': filepath,
                'dxf_version': doc.dxfversion
            }
        )
        
        self._calculate_buildable_area(site)
        
        return site
    
    def import_from_coordinates(self, coordinates: List[Tuple[float, float]]) -> SiteBoundary:
        """
        Create site boundary from list of coordinates
        
        Args:
            coordinates: List of (x, y) tuples forming polygon
            
        Returns:
            SiteBoundary object
        """
        if len(coordinates) < 3:
            raise ValueError("At least 3 coordinates required")
        
        geometry = Polygon(coordinates)
        geometry = self._normalize_geometry(geometry)
        
        site = SiteBoundary(
            geometry=geometry,
            area_sqm=geometry.area,
            metadata={'source': 'coordinates'}
        )
        
        self._calculate_buildable_area(site)
        
        return site
    
    def _normalize_geometry(self, geometry: Polygon) -> Polygon:
        """
        Normalize and validate geometry
        
        - Fix self-intersections
        - Ensure counter-clockwise orientation
        - Remove duplicate points
        - Simplify if too complex
        """
        if not geometry.is_valid:
            self.logger.warning("Invalid geometry detected, attempting fix")
            geometry = make_valid(geometry)
            
            # make_valid might return a collection
            if isinstance(geometry, MultiPolygon):
                geometry = max(geometry.geoms, key=lambda g: g.area)
        
        # Ensure counter-clockwise exterior
        if not geometry.exterior.is_ccw:
            geometry = Polygon(
                list(geometry.exterior.coords)[::-1],
                [list(ring.coords)[::-1] for ring in geometry.interiors]
            )
        
        # Simplify if too many vertices (> 1000)
        if len(geometry.exterior.coords) > 1000:
            # Tolerance of 0.1m
            geometry = geometry.simplify(0.1, preserve_topology=True)
        
        return geometry
    
    def _calculate_buildable_area(self, site: SiteBoundary):
        """
        Calculate buildable area after applying setbacks
        
        Args:
            site: SiteBoundary to update
        """
        setback = self.regulations.get('setbacks', {}).get('boundary_minimum', 50)
        
        # Create setback constraint
        setback_zone = site.geometry.buffer(-setback)
        
        if setback_zone.is_empty:
            self.logger.warning(f"Site too small for {setback}m setback")
            site.buildable_area_sqm = 0
        else:
            site.buildable_area_sqm = setback_zone.area
            
            # Add setback as constraint
            no_build_zone = site.geometry.difference(setback_zone)
            if not no_build_zone.is_empty:
                constraint = Constraint(
                    type=ConstraintType.SETBACK,
                    geometry=no_build_zone if isinstance(no_build_zone, Polygon) else no_build_zone.convex_hull,
                    buffer_distance_m=setback,
                    description=f"Boundary setback zone ({setback}m)",
                    is_hard=True
                )
                site.constraints.append(constraint)
        
        self.logger.info(
            f"Site area: {site.area_sqm:.0f}m², "
            f"Buildable: {site.buildable_area_sqm:.0f}m² "
            f"({site.buildable_area_sqm/site.area_sqm*100:.1f}%)"
        )
    
    def add_constraint(
        self,
        site: SiteBoundary,
        constraint_type: ConstraintType,
        geometry: Union[Polygon, List[Tuple[float, float]]],
        buffer_distance: float = 0,
        description: str = "",
        is_hard: bool = True
    ) -> Constraint:
        """
        Add a constraint to the site
        
        Args:
            site: SiteBoundary to update
            constraint_type: Type of constraint
            geometry: Constraint geometry or coordinates
            buffer_distance: Buffer distance in meters
            description: Human-readable description
            is_hard: Whether constraint is mandatory
            
        Returns:
            Created Constraint object
        """
        if isinstance(geometry, list):
            geom = Polygon(geometry)
        else:
            geom = geometry
        
        # Apply buffer if specified
        if buffer_distance > 0:
            geom = geom.buffer(buffer_distance)
        
        constraint = Constraint(
            type=constraint_type,
            geometry=geom,
            buffer_distance_m=buffer_distance,
            description=description or f"{constraint_type.value} constraint",
            is_hard=is_hard
        )
        
        site.constraints.append(constraint)
        
        # Recalculate buildable area
        site.calculate_buildable_area()
        
        return constraint
    
    def get_buildable_polygon(self, site: SiteBoundary) -> Polygon:
        """
        Get the actual buildable polygon after all constraints
        
        Args:
            site: SiteBoundary
            
        Returns:
            Polygon representing buildable area
        """
        buildable = site.geometry
        
        for constraint in site.constraints:
            if constraint.is_hard:
                buildable = buildable.difference(constraint.geometry)
        
        if isinstance(buildable, MultiPolygon):
            buildable = max(buildable.geoms, key=lambda g: g.area)
        
        return buildable
    
    def identify_no_build_zones(self, site: SiteBoundary) -> List[Constraint]:
        """
        Identify all no-build zones on the site
        
        Returns list of constraints representing no-build areas
        """
        return [c for c in site.constraints if c.is_hard and c.type == ConstraintType.NO_BUILD]


# Example usage
if __name__ == "__main__":
    from shapely.geometry import box
    
    # Create processor
    processor = SiteProcessor()
    
    # Example: Create from coordinates
    coords = [
        (0, 0), (500, 0), (500, 400), (300, 500), (0, 400), (0, 0)
    ]
    
    site = processor.import_from_coordinates(coords)
    
    print(f"Site ID: {site.id}")
    print(f"Total area: {site.area_sqm:.0f} m²")
    print(f"Buildable area: {site.buildable_area_sqm:.0f} m²")
    print(f"Number of constraints: {len(site.constraints)}")
    
    # Add a hazard zone
    hazard_coords = [(200, 200), (250, 200), (250, 250), (200, 250)]
    processor.add_constraint(
        site,
        ConstraintType.HAZARD_ZONE,
        hazard_coords,
        buffer_distance=100,
        description="Chemical storage buffer zone"
    )
    
    print(f"After hazard zone - Buildable: {site.buildable_area_sqm:.0f} m²")
    print(f"Total constraints: {len(site.constraints)}")
