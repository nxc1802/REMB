"""
Cadastral Estate Optimizer - Complete Implementation
====================================================

Reads REAL cadastral data from DXF/DWG files and optimizes plot placement.

Features:
- Automatic boundary extraction from DXF/DWG
- Adaptive parameter calculation based on actual land size
- NFP-grid plot placement for irregular polygons
- Hard constraint validation
- Professional DXF export

Based on: Complete_Corrected_DXF_Implementation.md
          Critical_Input_Output_Analysis.md
"""

import os
import sys
sys.path.insert(0, '.')

import numpy as np
from shapely.geometry import Polygon, box, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from typing import List, Dict, Tuple, Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# DXF/DWG READER
# =============================================================================

class CadastralDXFReader:
    """
    Read cadastral survey data from DXF/DWG files.
    
    DWG Note: DWG files need to be converted to DXF first using ODA File Converter
    or use ODAFileConverter command line tool.
    """
    
    def __init__(self, file_path: str):
        """Initialize with DXF file path"""
        self.path = file_path
        self.doc = None
        self.msp = None
        
        # Check if it's DWG - need conversion
        if file_path.lower().endswith('.dwg'):
            # DWG requires conversion - try to find DXF version
            dxf_path = file_path.replace('.dwg', '.dxf').replace('.DWG', '.dxf')
            if os.path.exists(dxf_path):
                logger.info(f"Using DXF version: {dxf_path}")
                self.path = dxf_path
            else:
                logger.warning(f"DWG file detected. Please convert to DXF using:")
                logger.warning(f"  ODA File Converter or online converter")
                logger.warning(f"  Expected DXF at: {dxf_path}")
                return
        
        try:
            import ezdxf
            self.doc = ezdxf.readfile(self.path)
            self.msp = self.doc.modelspace()
            logger.info(f"DXF loaded: {self.path}")
        except Exception as e:
            logger.error(f"Error loading DXF: {e}")
    
    def is_loaded(self) -> bool:
        """Check if file was loaded successfully"""
        return self.doc is not None and self.msp is not None
    
    def get_all_layers(self) -> List[str]:
        """Get all layer names in the DXF"""
        if not self.is_loaded():
            return []
        return [layer.dxf.name for layer in self.doc.layers]
    
    def get_all_polylines(self) -> List[Dict]:
        """Get all polylines with their properties"""
        if not self.is_loaded():
            return []
        
        polylines = []
        
        for entity in self.msp.query('LWPOLYLINE'):
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if len(coords) >= 3:
                try:
                    poly = Polygon(coords)
                    if poly.is_valid:
                        polylines.append({
                            'layer': entity.dxf.layer,
                            'coords': coords,
                            'polygon': poly,
                            'area': poly.area,
                            'is_closed': entity.is_closed
                        })
                except:
                    pass
        
        return sorted(polylines, key=lambda x: x['area'], reverse=True)
    
    def extract_boundary(self, preferred_layers: List[str] = None) -> Tuple[Optional[Polygon], List]:
        """
        Extract boundary polygon from DXF.
        
        Args:
            preferred_layers: List of layer names to prioritize
        
        Returns:
            (Polygon, coordinates) or (None, [])
        """
        if not self.is_loaded():
            return None, []
        
        # Default preferred layers
        if preferred_layers is None:
            preferred_layers = [
                'BOUNDARY', 'SITE_BOUNDARY', 'PERIMETER', 
                'LOT', 'PARCEL', 'CADASTRAL', 'SITE', '0'
            ]
        
        candidates = []
        
        # Strategy 1: Look for specific boundary layers
        for layer_name in preferred_layers:
            for entity in self.msp.query('LWPOLYLINE'):
                if layer_name.upper() in entity.dxf.layer.upper():
                    coords = [(p[0], p[1]) for p in entity.get_points('xy')]
                    if len(coords) >= 3:
                        try:
                            poly = Polygon(coords)
                            if poly.is_valid and poly.area > 10:
                                candidates.append({
                                    'source': 'layer_match',
                                    'layer': entity.dxf.layer,
                                    'polygon': poly,
                                    'coords': coords,
                                    'area': poly.area
                                })
                        except:
                            pass
        
        # Strategy 2: Find largest closed polyline
        for entity in self.msp.query('LWPOLYLINE'):
            if entity.is_closed:
                coords = [(p[0], p[1]) for p in entity.get_points('xy')]
                if len(coords) >= 3:
                    try:
                        poly = Polygon(coords)
                        if poly.is_valid and poly.area > 10:
                            candidates.append({
                                'source': 'closed_polyline',
                                'layer': entity.dxf.layer,
                                'polygon': poly,
                                'coords': coords,
                                'area': poly.area
                            })
                    except:
                        pass
        
        # Strategy 3: Find any large polyline
        for entity in self.msp.query('LWPOLYLINE'):
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if len(coords) >= 4:
                try:
                    # Close the polyline
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    poly = Polygon(coords)
                    if poly.is_valid and poly.area > 50:
                        candidates.append({
                            'source': 'any_polyline',
                            'layer': entity.dxf.layer,
                            'polygon': poly,
                            'coords': coords,
                            'area': poly.area
                        })
                except:
                    pass
        
        if candidates:
            # Return largest valid polygon
            best = max(candidates, key=lambda x: x['area'])
            logger.info(f"Boundary found: {best['layer']} ({best['area']:.2f} m2)")
            return best['polygon'], best['coords']
        
        logger.warning("No boundary polygon found in DXF")
        return None, []
    
    def extract_survey_points(self) -> Dict[int, Dict]:
        """Extract survey control points (numbered 1, 2, 3, etc.)"""
        if not self.is_loaded():
            return {}
        
        points = {}
        
        # Find TEXT entities with numbers
        for entity in self.msp.query('TEXT'):
            try:
                text = entity.dxf.text.strip()
                if text.isdigit() and 1 <= int(text) <= 100:
                    point_num = int(text)
                    x, y, _ = entity.dxf.insert
                    points[point_num] = {'x': x, 'y': y, 'num': point_num}
            except:
                pass
        
        # Also check MTEXT
        for entity in self.msp.query('MTEXT'):
            try:
                text = entity.dxf.text.strip()
                if text.isdigit() and 1 <= int(text) <= 100:
                    point_num = int(text)
                    x, y, _ = entity.dxf.insert
                    points[point_num] = {'x': x, 'y': y, 'num': point_num}
            except:
                pass
        
        if points:
            logger.info(f"Found {len(points)} survey points")
        
        return {k: points[k] for k in sorted(points.keys())}
    
    def detect_units(self) -> Tuple[int, str]:
        """Detect unit system from DXF"""
        if not self.is_loaded():
            return 0, 'Unknown'
        
        unit_code = self.doc.header.get('$INSUNITS', 0)
        units = {
            0: 'Unitless', 1: 'Inches', 2: 'Feet', 3: 'Miles',
            4: 'Millimeters', 5: 'Centimeters', 6: 'Meters', 7: 'Kilometers'
        }
        unit_name = units.get(unit_code, 'Unknown')
        logger.info(f"Unit system: {unit_name} (code {unit_code})")
        return unit_code, unit_name


# =============================================================================
# ADAPTIVE PARAMETER CALCULATOR
# =============================================================================

class AdaptiveParameterCalculator:
    """Calculate optimal parameters based on actual land size"""
    
    @staticmethod
    def calculate(boundary_area: float) -> Dict:
        """
        Calculate all parameters based on actual land area.
        NOT one-size-fits-all!
        """
        
        if boundary_area < 100:
            return {
                'size_class': 'Micro',
                'description': 'Very small parcel (< 100 m2)',
                'plot_min_width': 3, 'plot_min_height': 3,
                'plot_max_width': 8, 'plot_max_height': 10,
                'grid_step': 1, 'road_width': 2, 'setback': 0.5,
                'plot_spacing': 0.5, 'max_plots': 4,
                'target_utilization': 60
            }
        
        elif boundary_area < 500:
            return {
                'size_class': 'Tiny',
                'description': 'Small parcel (100-500 m2)',
                'plot_min_width': 4, 'plot_min_height': 5,
                'plot_max_width': 15, 'plot_max_height': 20,
                'grid_step': 1.5, 'road_width': 2.5, 'setback': 0.75,
                'plot_spacing': 0.75, 'max_plots': 8,
                'target_utilization': 65
            }
        
        elif boundary_area < 1000:
            return {
                'size_class': 'Small',
                'description': 'Small cadastral parcel (500-1000 m2)',
                'plot_min_width': 5, 'plot_min_height': 7,
                'plot_max_width': 25, 'plot_max_height': 35,
                'grid_step': 2, 'road_width': 3, 'setback': 1,
                'plot_spacing': 1, 'max_plots': 15,
                'target_utilization': 70
            }
        
        elif boundary_area < 5000:
            return {
                'size_class': 'Medium',
                'description': 'Medium parcel (1000-5000 m2)',
                'plot_min_width': 10, 'plot_min_height': 15,
                'plot_max_width': 40, 'plot_max_height': 60,
                'grid_step': 4, 'road_width': 5, 'setback': 2,
                'plot_spacing': 2, 'max_plots': 40,
                'target_utilization': 65
            }
        
        elif boundary_area < 50000:
            return {
                'size_class': 'Large',
                'description': 'Large estate (5000-50000 m2)',
                'plot_min_width': 30, 'plot_min_height': 40,
                'plot_max_width': 100, 'plot_max_height': 150,
                'grid_step': 10, 'road_width': 12, 'setback': 5,
                'plot_spacing': 5, 'max_plots': 100,
                'target_utilization': 60
            }
        
        else:
            return {
                'size_class': 'Industrial',
                'description': 'Very large industrial (50000+ m2)',
                'plot_min_width': 50, 'plot_min_height': 60,
                'plot_max_width': 200, 'plot_max_height': 300,
                'grid_step': 15, 'road_width': 24, 'setback': 10,
                'plot_spacing': 10, 'max_plots': 500,
                'target_utilization': 55
            }
    
    @staticmethod
    def generate_plots(boundary_area: float, params: Dict) -> List[Dict]:
        """Generate appropriate plot configurations"""
        available = boundary_area * 0.7  # 70% for plots
        min_plot = params['plot_min_width'] * params['plot_min_height']
        
        num_plots = min(
            max(3, int(available / (min_plot * 1.5))),
            params['max_plots']
        )
        
        plots = []
        for i in range(num_plots):
            factor = 0.8 + (i % 5) * 0.1
            w = int(params['plot_min_width'] * factor + (i % 3) * 2)
            h = int(params['plot_min_height'] * factor + (i % 4) * 3)
            
            plots.append({
                'width': w,
                'height': h,
                'type': f'plot_{i+1:03d}',
                'area': w * h
            })
        
        return plots


# =============================================================================
# POLYGON-CONSTRAINED OPTIMIZER
# =============================================================================

class CadastralPolygonOptimizer:
    """
    Optimizes plot placement within actual cadastral boundary.
    Uses NFP-grid algorithm for irregular polygons.
    """
    
    def __init__(
        self,
        boundary: Polygon,
        plot_configs: List[Dict],
        params: Dict
    ):
        self.boundary = boundary
        self.plot_configs = plot_configs
        self.params = params
        
        self.grid_step = params.get('grid_step', 2)
        self.setback = params.get('setback', 1)
        self.plot_spacing = params.get('plot_spacing', 1)
        self.road_width = params.get('road_width', 3)
        
        # Pre-compute inner boundary
        self.inner_boundary = boundary.buffer(-self.setback)
        
        # State
        self.placed_plots = []
        self.plot_geometries = []
    
    def optimize(self) -> Dict:
        """Run optimization"""
        logger.info("Starting cadastral polygon optimization...")
        
        # Calculate buildable area
        buildable = self.inner_boundary
        if buildable.is_empty:
            buildable = self.boundary
        
        minx, miny, maxx, maxy = buildable.bounds
        
        # Sort plots by area (largest first)
        sorted_configs = sorted(
            enumerate(self.plot_configs),
            key=lambda x: x[1]['width'] * x[1]['height'],
            reverse=True
        )
        
        # Place each plot
        for orig_idx, config in sorted_configs:
            w, h = config['width'], config['height']
            placed = False
            
            # Grid search
            for x in np.arange(minx + self.plot_spacing, 
                              maxx - w - self.plot_spacing, 
                              self.grid_step):
                if placed:
                    break
                for y in np.arange(miny + self.plot_spacing, 
                                  maxy - h - self.plot_spacing, 
                                  self.grid_step):
                    candidate = box(x, y, x + w, y + h)
                    
                    # Check inside boundary
                    if not buildable.contains(candidate):
                        continue
                    
                    # Check no overlaps
                    overlap = False
                    for existing in self.placed_plots:
                        if candidate.buffer(self.plot_spacing/2).intersects(
                            existing.buffer(self.plot_spacing/2)):
                            overlap = True
                            break
                    
                    if not overlap:
                        self.placed_plots.append(candidate)
                        self.plot_geometries.append({
                            'id': f'PLOT_{len(self.placed_plots):03d}',
                            'x': x, 'y': y,
                            'width': w, 'height': h,
                            'area': w * h,
                            'type': config.get('type', 'plot'),
                            'geom': candidate
                        })
                        placed = True
                        break
        
        # Calculate metrics
        total_plot_area = sum(p['area'] for p in self.plot_geometries)
        boundary_area = self.boundary.area
        utilization = total_plot_area / boundary_area if boundary_area > 0 else 0
        
        # Validate
        violations = {'outside_boundary': [], 'overlaps': []}
        for i, geom in enumerate(self.placed_plots):
            if not self.boundary.contains(geom):
                violations['outside_boundary'].append(i)
        
        for i in range(len(self.placed_plots)):
            for j in range(i + 1, len(self.placed_plots)):
                if self.placed_plots[i].intersects(self.placed_plots[j]):
                    violations['overlaps'].append((i, j))
        
        is_valid = len(violations['outside_boundary']) == 0 and len(violations['overlaps']) == 0
        
        logger.info(f"Placed {len(self.plot_geometries)}/{len(self.plot_configs)} plots")
        logger.info(f"Utilization: {utilization*100:.1f}%")
        logger.info(f"Valid: {is_valid}")
        
        return {
            'boundary': self.boundary,
            'plots': self.plot_geometries,
            'placed_geometries': self.placed_plots,
            'is_valid': is_valid,
            'violations': violations,
            'metrics': {
                'boundary_area': boundary_area,
                'total_plot_area': total_plot_area,
                'utilization': utilization,
                'num_plots': len(self.plot_geometries),
                'plots_placed': len(self.plot_geometries),
                'utilization_percent': utilization * 100
            }
        }


# =============================================================================
# DXF EXPORTER
# =============================================================================

def export_cadastral_layout_dxf(
    result: Dict,
    output_path: str,
    survey_points: Dict = None
) -> str:
    """Export optimized layout to DXF"""
    import ezdxf
    
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    # Layers
    doc.layers.add('BOUNDARY', color=1)
    doc.layers.add('PLOTS', color=5)
    doc.layers.add('LABELS', color=3)
    doc.layers.add('SURVEY_POINTS', color=6)
    
    # Draw boundary
    boundary = result.get('boundary')
    if boundary:
        coords = list(boundary.exterior.coords)
        msp.add_lwpolyline(
            [(c[0], c[1]) for c in coords],
            close=True,
            dxfattribs={'layer': 'BOUNDARY', 'lineweight': 50}
        )
    
    # Draw plots
    for plot in result.get('plots', []):
        x, y, w, h = plot['x'], plot['y'], plot['width'], plot['height']
        points = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
        msp.add_lwpolyline(points, close=True, dxfattribs={'layer': 'PLOTS'})
        
        # Label
        msp.add_mtext(
            f"{plot['id']}\n{w}x{h}m",
            dxfattribs={'layer': 'LABELS', 'char_height': max(1, w/10)}
        ).set_location((x + w/2, y + h/2))
    
    # Draw survey points
    if survey_points:
        for num, pt in survey_points.items():
            msp.add_circle((pt['x'], pt['y']), radius=0.5, 
                          dxfattribs={'layer': 'SURVEY_POINTS'})
            msp.add_text(str(num), dxfattribs={'layer': 'SURVEY_POINTS', 'height': 1}
                        ).set_placement((pt['x'], pt['y'] + 1))
    
    # Metrics text
    metrics = result.get('metrics', {})
    if metrics and boundary:
        info = (f"CADASTRAL LAYOUT\n"
                f"Plots: {metrics.get('num_plots', 0)}\n"
                f"Area: {metrics.get('total_plot_area', 0):.0f} m2\n"
                f"Util: {metrics.get('utilization_percent', 0):.1f}%")
        minx, miny, maxx, maxy = boundary.bounds
        msp.add_mtext(info, dxfattribs={'layer': 'LABELS', 'char_height': max(1, (maxx-minx)/50)}
                     ).set_location((minx, maxy + 5))
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    doc.saveas(output_path)
    logger.info(f"DXF exported: {output_path}")
    return output_path


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def optimize_cadastral_dxf(dxf_path: str, output_dir: str = 'output') -> Dict:
    """
    Complete pipeline: Read DXF -> Extract boundary -> Calculate params -> Optimize -> Export
    
    Args:
        dxf_path: Path to input DXF/DWG file
        output_dir: Output directory
    
    Returns:
        Complete result dictionary
    """
    print("\n" + "=" * 60)
    print("CADASTRAL ESTATE OPTIMIZATION PIPELINE")
    print("=" * 60)
    
    # Step 1: Load DXF
    print(f"\nStep 1: Loading {dxf_path}...")
    reader = CadastralDXFReader(dxf_path)
    
    if not reader.is_loaded():
        print("ERROR: Could not load DXF file")
        print("If file is DWG, please convert to DXF first using:")
        print("  - ODA File Converter (free)")
        print("  - Online DWG to DXF converter")
        return {'status': 'ERROR', 'message': 'Could not load file'}
    
    # List layers
    layers = reader.get_all_layers()
    print(f"   Layers found: {layers}")
    
    # List polylines
    polylines = reader.get_all_polylines()
    print(f"   Polylines found: {len(polylines)}")
    for i, p in enumerate(polylines[:5]):
        print(f"      {i+1}. Layer '{p['layer']}': area={p['area']:.1f} m2")
    
    # Step 2: Extract boundary
    print("\nStep 2: Extracting boundary...")
    boundary, coords = reader.extract_boundary()
    
    if boundary is None:
        print("ERROR: Could not find boundary polygon")
        return {'status': 'ERROR', 'message': 'No boundary found'}
    
    boundary_area = boundary.area
    print(f"   Boundary area: {boundary_area:.2f} m2")
    print(f"   Bounds: {boundary.bounds}")
    
    # Step 3: Extract survey points
    print("\nStep 3: Extracting survey points...")
    survey_points = reader.extract_survey_points()
    print(f"   Found {len(survey_points)} survey points")
    
    # Step 4: Calculate parameters
    print("\nStep 4: Calculating adaptive parameters...")
    params = AdaptiveParameterCalculator.calculate(boundary_area)
    print(f"   Size class: {params['size_class']}")
    print(f"   Grid step: {params['grid_step']}m")
    print(f"   Plot range: {params['plot_min_width']}-{params['plot_max_width']}m")
    print(f"   Road width: {params['road_width']}m")
    
    # Step 5: Generate plots
    print("\nStep 5: Generating plot configurations...")
    plot_configs = AdaptiveParameterCalculator.generate_plots(boundary_area, params)
    print(f"   Generated {len(plot_configs)} plot types")
    for p in plot_configs[:5]:
        print(f"      - {p['width']}x{p['height']}m = {p['area']} m2")
    
    # Step 6: Optimize
    print("\nStep 6: Running optimization...")
    optimizer = CadastralPolygonOptimizer(boundary, plot_configs, params)
    result = optimizer.optimize()
    
    print(f"   Plots placed: {result['metrics']['num_plots']}/{len(plot_configs)}")
    print(f"   Utilization: {result['metrics']['utilization_percent']:.1f}%")
    print(f"   Valid: {result['is_valid']}")
    
    # Step 7: Export
    print("\nStep 7: Exporting DXF...")
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(dxf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_OPTIMIZED.dxf")
    
    export_cadastral_layout_dxf(result, output_path, survey_points)
    print(f"   Output: {output_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"Input:  {dxf_path}")
    print(f"Output: {output_path}")
    print(f"Area:   {boundary_area:.2f} m2")
    print(f"Plots:  {result['metrics']['num_plots']}")
    print(f"Util:   {result['metrics']['utilization_percent']:.1f}%")
    print("=" * 60 + "\n")
    
    return {
        'status': 'SUCCESS',
        'input_path': dxf_path,
        'output_path': output_path,
        'boundary': boundary,
        'boundary_coords': coords,
        'survey_points': survey_points,
        'parameters': params,
        'plot_configs': plot_configs,
        'result': result
    }


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Test with the user's actual file
    input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dwg"
    
    # Convert DWG to DXF path
    dxf_file = input_file.replace('.dwg', '.dxf')
    
    if os.path.exists(dxf_file):
        result = optimize_cadastral_dxf(dxf_file)
    elif os.path.exists(input_file):
        print(f"DWG file found: {input_file}")
        print(f"Please convert to DXF and save as: {dxf_file}")
        print("\nYou can use:")
        print("  1. ODA File Converter (free): https://www.opendesign.com/guestfiles/oda_file_converter")
        print("  2. Online converter: https://cloudconvert.com/dwg-to-dxf")
        print("\nOr open in AutoCAD and Save As DXF")
    else:
        print(f"File not found: {input_file}")
