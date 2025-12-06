"""
Advanced Industrial Estate Optimizer
=====================================

Implements professional layout like the reference images:
1. Diagonal main road through the land
2. Secondary perpendicular roads creating grid
3. Rotated plot grid aligned with road direction
4. Maximum utilization with proper spacing
5. Buffer zones and setbacks
6. Data-preserving DXF export

Reference: Industrial Estate Planning with Python and Geo Libraries
           by Donato_TH (Medium)
"""

import os
import numpy as np
import ezdxf
from shapely.geometry import Polygon, LineString, box, MultiPolygon, Point
from shapely.ops import unary_union, split, linemerge
from shapely.affinity import scale as scale_geom, rotate, translate
from shapely.validation import make_valid
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import math


class AdvancedEstateOptimizer:
    """
    Professional estate optimizer with:
    - Diagonal main road
    - Grid road network
    - Rotated plot placement
    - Maximum utilization
    """
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.doc = None
        self.msp = None
        
        # Geometry
        self.boundary_raw = None
        self.boundary_m = None
        self.buffer_zone = None
        self.main_road = None
        self.secondary_roads = []
        self.usable_zones = []
        self.plots = []
        
        # Parameters
        self.unit_scale = 0.001  # mm to m
        self.buffer_distance = 2.0  # outer buffer
        self.setback_distance = 1.5  # inner setback
        self.main_road_width = 6.0
        self.secondary_road_width = 4.0
        self.plot_width = 8.0
        self.plot_height = 10.0
        self.plot_spacing = 1.5
        
        # Load
        self._load_dxf()
    
    def _load_dxf(self):
        """Load DXF file"""
        try:
            self.doc = ezdxf.readfile(self.dxf_path)
            self.msp = self.doc.modelspace()
            print("Loaded: %s" % self.dxf_path)
        except Exception as e:
            print("Error: %s" % e)
    
    def extract_boundary(self) -> Optional[Polygon]:
        """Extract and convert boundary to meters"""
        for entity in self.msp.query('LWPOLYLINE'):
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if len(coords) >= 3:
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                try:
                    poly = Polygon(coords)
                    if not poly.is_valid:
                        poly = make_valid(poly)
                    if poly.is_valid and poly.area > 1000:
                        self.boundary_raw = poly
                        
                        # Detect scale
                        max_coord = max(abs(c) for c in poly.bounds)
                        if max_coord > 10000:
                            self.unit_scale = 0.001
                        else:
                            self.unit_scale = 1.0
                        
                        # Convert to meters
                        self.boundary_m = scale_geom(
                            poly, 
                            xfact=self.unit_scale, 
                            yfact=self.unit_scale, 
                            origin=(0, 0)
                        )
                        
                        print("Boundary: %.2f m2" % self.boundary_m.area)
                        return self.boundary_m
                except:
                    pass
        return None
    
    def apply_buffer_zone(self) -> Polygon:
        """Create buffer zone (outer) and setback (inner)"""
        if self.boundary_m is None:
            return None
        
        # Buffer zone = boundary buffered inward
        self.buffer_zone = self.boundary_m.buffer(-self.setback_distance)
        
        if self.buffer_zone.is_empty:
            self.setback_distance = self.setback_distance / 2
            self.buffer_zone = self.boundary_m.buffer(-self.setback_distance)
        
        print("Buffer zone: %.2f m2 (setback: %.1fm)" % (
            self.buffer_zone.area, self.setback_distance))
        return self.buffer_zone
    
    def create_diagonal_main_road(self) -> LineString:
        """
        Create diagonal main road through the land.
        This is the key feature from the reference images.
        """
        if self.buffer_zone is None:
            self.apply_buffer_zone()
        
        # Get the longest diagonal of the boundary
        minx, miny, maxx, maxy = self.buffer_zone.bounds
        
        # Find the principal axis of the polygon
        # Use the longest side as the road direction
        coords = list(self.buffer_zone.exterior.coords)
        
        # Find longest edge
        max_length = 0
        best_angle = 0
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            length = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            if length > max_length:
                max_length = length
                best_angle = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
        
        # Create diagonal line through centroid
        centroid = self.buffer_zone.centroid
        cx, cy = centroid.x, centroid.y
        
        # Extend line far beyond boundary
        extent = max(maxx - minx, maxy - miny) * 2
        
        p1 = (cx - extent * math.cos(best_angle), 
              cy - extent * math.sin(best_angle))
        p2 = (cx + extent * math.cos(best_angle), 
              cy + extent * math.sin(best_angle))
        
        full_line = LineString([p1, p2])
        
        # Clip to buffer zone
        self.main_road = full_line.intersection(self.buffer_zone)
        
        if self.main_road.is_empty:
            # Fallback: use centroid-based diagonal
            p1 = (minx - 10, miny - 10)
            p2 = (maxx + 10, maxy + 10)
            full_line = LineString([p1, p2])
            self.main_road = full_line.intersection(self.buffer_zone)
        
        if not self.main_road.is_empty:
            print("Main road created: %.2fm length" % self.main_road.length)
        
        return self.main_road
    
    def create_secondary_roads(self, spacing: float = 20.0) -> List[LineString]:
        """
        Create secondary roads perpendicular to main road.
        These form the grid pattern.
        """
        if self.main_road is None or self.main_road.is_empty:
            self.create_diagonal_main_road()
        
        if self.main_road.is_empty:
            return []
        
        self.secondary_roads = []
        
        # Get main road direction
        coords = list(self.main_road.coords)
        if len(coords) < 2:
            return []
        
        p1, p2 = coords[0], coords[-1]
        road_angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        perp_angle = road_angle + math.pi / 2  # Perpendicular
        
        # Create perpendicular roads at intervals
        road_length = self.main_road.length
        extent = max(self.buffer_zone.bounds[2] - self.buffer_zone.bounds[0],
                    self.buffer_zone.bounds[3] - self.buffer_zone.bounds[1])
        
        num_secondary = max(2, int(road_length / spacing))
        
        for i in range(num_secondary):
            # Point along main road
            fraction = (i + 1) / (num_secondary + 1)
            point = self.main_road.interpolate(fraction, normalized=True)
            
            # Create perpendicular line
            p1 = (point.x - extent * math.cos(perp_angle),
                  point.y - extent * math.sin(perp_angle))
            p2 = (point.x + extent * math.cos(perp_angle),
                  point.y + extent * math.sin(perp_angle))
            
            perp_line = LineString([p1, p2])
            
            # Clip to buffer zone
            clipped = perp_line.intersection(self.buffer_zone)
            
            if not clipped.is_empty:
                self.secondary_roads.append(clipped)
        
        print("Secondary roads: %d" % len(self.secondary_roads))
        return self.secondary_roads
    
    def calculate_usable_zones(self) -> List[Polygon]:
        """
        Calculate usable zones by subtracting roads from buffer zone.
        """
        if self.buffer_zone is None:
            self.apply_buffer_zone()
        
        # Buffer all roads
        road_buffers = []
        
        if self.main_road and not self.main_road.is_empty:
            road_buffers.append(self.main_road.buffer(self.main_road_width / 2))
        
        for road in self.secondary_roads:
            if not road.is_empty:
                road_buffers.append(road.buffer(self.secondary_road_width / 2))
        
        if road_buffers:
            all_roads = unary_union(road_buffers)
            usable = self.buffer_zone.difference(all_roads)
        else:
            usable = self.buffer_zone
        
        # Handle MultiPolygon
        if isinstance(usable, MultiPolygon):
            self.usable_zones = list(usable.geoms)
        elif isinstance(usable, Polygon) and not usable.is_empty:
            self.usable_zones = [usable]
        else:
            self.usable_zones = []
        
        total_usable = sum(z.area for z in self.usable_zones)
        print("Usable zones: %d (%.2f m2)" % (len(self.usable_zones), total_usable))
        return self.usable_zones
    
    def generate_rotated_plots(self) -> List[Dict]:
        """
        Generate plots aligned with the main road direction.
        This creates the professional grid layout.
        """
        if not self.usable_zones:
            self.calculate_usable_zones()
        
        self.plots = []
        plot_id = 1
        
        # Get road angle for rotation
        if self.main_road and not self.main_road.is_empty:
            coords = list(self.main_road.coords)
            if len(coords) >= 2:
                p1, p2 = coords[0], coords[-1]
                road_angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
            else:
                road_angle = 0
        else:
            road_angle = 0
        
        for zone_idx, zone in enumerate(self.usable_zones):
            if zone.is_empty or zone.area < 50:
                continue
            
            # Rotate zone to align with grid
            centroid = zone.centroid
            zone_rotated = rotate(zone, -road_angle, origin=centroid)
            
            minx, miny, maxx, maxy = zone_rotated.bounds
            
            # Grid placement in rotated space
            x = minx + self.plot_spacing
            while x + self.plot_width < maxx - self.plot_spacing:
                y = miny + self.plot_spacing
                while y + self.plot_height < maxy - self.plot_spacing:
                    # Create plot in rotated space
                    plot_rotated = box(x, y, x + self.plot_width, y + self.plot_height)
                    
                    # Check if inside rotated zone
                    if zone_rotated.contains(plot_rotated):
                        # Rotate back to original orientation
                        plot_original = rotate(plot_rotated, road_angle, origin=centroid)
                        
                        # Verify inside original zone
                        if zone.contains(plot_original):
                            # Check no overlaps
                            overlap = False
                            for existing in self.plots:
                                if plot_original.intersects(existing['geom']):
                                    overlap = True
                                    break
                            
                            if not overlap:
                                pminx, pminy, pmaxx, pmaxy = plot_original.bounds
                                self.plots.append({
                                    'id': 'PLOT_%03d' % plot_id,
                                    'x': pminx,
                                    'y': pminy,
                                    'width': self.plot_width,
                                    'height': self.plot_height,
                                    'area': self.plot_width * self.plot_height,
                                    'zone': zone_idx,
                                    'angle': road_angle,
                                    'geom': plot_original
                                })
                                plot_id += 1
                    
                    y += self.plot_height + self.plot_spacing
                x += self.plot_width + self.plot_spacing
        
        print("Plots generated: %d" % len(self.plots))
        return self.plots
    
    def get_metrics(self) -> Dict:
        """Calculate layout metrics"""
        total_plot_area = sum(p['area'] for p in self.plots)
        boundary_area = self.boundary_m.area if self.boundary_m else 0
        usable_area = sum(z.area for z in self.usable_zones) if self.usable_zones else 0
        
        return {
            'boundary_area': boundary_area,
            'buffer_area': self.buffer_zone.area if self.buffer_zone else 0,
            'usable_area': usable_area,
            'total_plot_area': total_plot_area,
            'num_plots': len(self.plots),
            'utilization': (total_plot_area / usable_area * 100) if usable_area > 0 else 0,
            'overall_util': (total_plot_area / boundary_area * 100) if boundary_area > 0 else 0
        }
    
    def export_dxf(self, output_path: str) -> bool:
        """Export with data preservation"""
        if self.doc is None:
            return False
        
        # Create layers
        layers = {
            'EST_BUFFER': 4,      # Cyan - buffer zone
            'EST_MAIN_ROAD': 30,  # Orange - main road
            'EST_SEC_ROADS': 7,   # White - secondary roads
            'EST_PLOTS': 5,       # Blue - plots
            'EST_LABELS': 3,      # Green - labels
            'EST_METRICS': 2      # Yellow - metrics
        }
        
        for name, color in layers.items():
            if name not in self.doc.layers:
                self.doc.layers.add(name, color=color)
        
        scale = 1.0 / self.unit_scale if self.unit_scale else 1.0
        
        # Draw buffer zone
        if self.buffer_zone and not self.buffer_zone.is_empty:
            coords = [(c[0] * scale, c[1] * scale) for c in self.buffer_zone.exterior.coords]
            self.msp.add_lwpolyline(coords, close=True, 
                                   dxfattribs={'layer': 'EST_BUFFER', 'color': 4})
        
        # Draw main road
        if self.main_road and not self.main_road.is_empty:
            try:
                coords = [(c[0] * scale, c[1] * scale) for c in self.main_road.coords]
                self.msp.add_lwpolyline(coords, 
                                       dxfattribs={'layer': 'EST_MAIN_ROAD', 'lineweight': 70})
            except:
                pass
        
        # Draw secondary roads
        for road in self.secondary_roads:
            if not road.is_empty:
                try:
                    coords = [(c[0] * scale, c[1] * scale) for c in road.coords]
                    self.msp.add_lwpolyline(coords,
                                           dxfattribs={'layer': 'EST_SEC_ROADS', 'lineweight': 50})
                except:
                    pass
        
        # Draw plots
        for plot in self.plots:
            geom = plot['geom']
            coords = [(c[0] * scale, c[1] * scale) for c in geom.exterior.coords]
            self.msp.add_lwpolyline(coords, close=True,
                                   dxfattribs={'layer': 'EST_PLOTS', 'color': 5})
            
            # Label
            cx = (geom.bounds[0] + geom.bounds[2]) / 2 * scale
            cy = (geom.bounds[1] + geom.bounds[3]) / 2 * scale
            self.msp.add_mtext(
                "%s\n%.0fx%.0fm" % (plot['id'], plot['width'], plot['height']),
                dxfattribs={'layer': 'EST_LABELS', 'char_height': 150}
            ).set_location((cx, cy))
        
        # Metrics
        metrics = self.get_metrics()
        if self.boundary_m:
            minx = self.boundary_m.bounds[0] * scale
            maxy = self.boundary_m.bounds[3] * scale
            
            info = """ESTATE LAYOUT
Boundary: %.0f m2
Plots: %d
Plot Area: %.0f m2
Utilization: %.1f%%
Date: %s""" % (
                metrics['boundary_area'],
                metrics['num_plots'],
                metrics['total_plot_area'],
                metrics['utilization'],
                datetime.now().strftime('%Y-%m-%d')
            )
            
            self.msp.add_mtext(info, 
                              dxfattribs={'layer': 'EST_METRICS', 'char_height': 300}
                             ).set_location((minx, maxy + 1000))
        
        # Save
        self.doc.saveas(output_path)
        
        # Verify
        input_size = os.path.getsize(self.dxf_path) / 1024
        output_size = os.path.getsize(output_path) / 1024
        print("Export: %.1f KB -> %.1f KB (%.1f%%)" % (
            input_size, output_size, output_size/input_size*100))
        
        return True
    
    def optimize(self, output_path: str = None) -> Dict:
        """Run complete optimization pipeline"""
        print("\n" + "=" * 60)
        print("ADVANCED ESTATE OPTIMIZER")
        print("=" * 60)
        
        # Step 1: Extract boundary
        print("\nStep 1: Extracting boundary...")
        if not self.extract_boundary():
            return {'status': 'ERROR', 'message': 'No boundary found'}
        
        # Step 2: Apply buffer
        print("\nStep 2: Applying buffer zone...")
        self.apply_buffer_zone()
        
        # Step 3: Create diagonal main road
        print("\nStep 3: Creating diagonal main road...")
        self.create_diagonal_main_road()
        
        # Step 4: Create secondary roads
        print("\nStep 4: Creating secondary roads...")
        self.create_secondary_roads(spacing=15.0)
        
        # Step 5: Calculate usable zones
        print("\nStep 5: Calculating usable zones...")
        self.calculate_usable_zones()
        
        # Step 6: Generate rotated plots
        print("\nStep 6: Generating rotated plots...")
        self.generate_rotated_plots()
        
        # Step 7: Get metrics
        print("\nStep 7: Getting metrics...")
        metrics = self.get_metrics()
        print("  - Plots: %d" % metrics['num_plots'])
        print("  - Area: %.2f m2" % metrics['total_plot_area'])
        print("  - Utilization: %.1f%%" % metrics['utilization'])
        
        # Step 8: Export
        if output_path is None:
            base = os.path.splitext(os.path.basename(self.dxf_path))[0]
            output_path = os.path.join('output', base + '_ADVANCED.dxf')
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else 'output', exist_ok=True)
        
        print("\nStep 8: Exporting DXF...")
        self.export_dxf(output_path)
        
        print("\n" + "=" * 60)
        print("COMPLETE")
        print("  Output: %s" % output_path)
        print("=" * 60)
        
        return {
            'status': 'SUCCESS',
            'output': output_path,
            'metrics': metrics
        }


if __name__ == "__main__":
    input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
    output_file = r"D:\Gitrepo\REMB\output\Bel_Air_ADVANCED.dxf"
    
    optimizer = AdvancedEstateOptimizer(input_file)
    
    # Configure for the small parcel
    optimizer.setback_distance = 1.0
    optimizer.main_road_width = 3.0
    optimizer.secondary_road_width = 2.0
    optimizer.plot_width = 5.0
    optimizer.plot_height = 6.0
    optimizer.plot_spacing = 1.0
    
    result = optimizer.optimize(output_file)
    
    if result['status'] == 'SUCCESS':
        print("\nPlots: %d, Utilization: %.1f%%" % (
            result['metrics']['num_plots'],
            result['metrics']['utilization']
        ))
