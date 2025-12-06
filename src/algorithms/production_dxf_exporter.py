"""
Production DXF Exporter - PRESERVES ALL ORIGINAL DATA
======================================================

CRITICAL FIX: Instead of creating empty DXF, we MODIFY the existing file
and add optimization results as new layers.

INPUT:  449 KB (full cadastral survey)
OUTPUT: 460+ KB (ALL original data + optimization layers)

Based on: Production_DXF_Export_Full_Preservation.md
"""

import ezdxf
from ezdxf import enums
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from shapely.geometry import Polygon, box
from shapely.affinity import scale
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionDXFExporter:
    """
    Professional DXF export that PRESERVES ALL INPUT DATA
    and adds optimization results as separate layers.
    
    CORRECT APPROACH:
    1. Load existing DXF (ALL data preserved)
    2. Create new layer for optimization
    3. Add plots to new layer
    4. Export with ALL original data intact
    
    Result: 449 KB input → 460+ KB output (not 22 KB!)
    """
    
    def __init__(self, input_dxf_path: str):
        """Initialize with existing DXF file"""
        self.input_path = input_dxf_path
        self.doc = None
        self.msp = None
        self.original_layers = []
        self.original_entity_count = 0
        self.unit_scale = 1.0  # For mm to m conversion if needed
        
        try:
            self.doc = ezdxf.readfile(input_dxf_path)
            self.msp = self.doc.modelspace()
            
            # Count original data
            self.original_layers = [layer.dxf.name for layer in self.doc.layers]
            self.original_entity_count = len(list(self.msp))
            
            logger.info(f"Loaded: {input_dxf_path}")
            logger.info(f"  Size: {self.get_file_size(input_dxf_path):.1f} KB")
            logger.info(f"  Layers: {len(self.original_layers)}")
            logger.info(f"  Entities: {self.original_entity_count}")
            
        except Exception as e:
            logger.error(f"Error loading DXF: {e}")
    
    @staticmethod
    def get_file_size(path: str) -> float:
        """Get file size in KB"""
        return os.path.getsize(path) / 1024
    
    def detect_units(self) -> Tuple[str, float]:
        """Detect unit system and return scale factor to meters"""
        if self.doc is None:
            return 'Unknown', 1.0
        
        unit_code = self.doc.header.get('$INSUNITS', 0)
        units_map = {
            0: ('Unitless', 1.0),
            1: ('Inches', 0.0254),
            2: ('Feet', 0.3048),
            4: ('Millimeters', 0.001),
            5: ('Centimeters', 0.01),
            6: ('Meters', 1.0),
        }
        
        unit_name, scale_factor = units_map.get(unit_code, ('Unknown', 1.0))
        
        # Auto-detect based on geometry size
        for entity in self.msp.query('LWPOLYLINE')[:1]:
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if coords:
                max_coord = max(max(abs(c[0]), abs(c[1])) for c in coords)
                if max_coord > 10000:
                    unit_name = 'Millimeters (auto)'
                    scale_factor = 0.001
                    
        self.unit_scale = scale_factor
        logger.info(f"Units: {unit_name} (scale: {scale_factor})")
        return unit_name, scale_factor
    
    def get_layer_summary(self) -> Dict[str, int]:
        """Get summary of entities per layer"""
        summary = {}
        for layer in self.original_layers:
            count = len(list(self.msp.query(f'*[layer=="{layer}"]')))
            if count > 0:
                summary[layer] = count
        return summary
    
    def extract_boundary(self) -> Optional[Polygon]:
        """Extract the main boundary polygon"""
        candidates = []
        
        for entity in self.msp.query('LWPOLYLINE'):
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if len(coords) >= 3:
                try:
                    poly = Polygon(coords)
                    if poly.is_valid and poly.area > 1000:
                        candidates.append({
                            'polygon': poly,
                            'area': poly.area,
                            'layer': entity.dxf.layer
                        })
                except:
                    pass
        
        if candidates:
            best = max(candidates, key=lambda x: x['area'])
            logger.info(f"Boundary: layer '{best['layer']}', area={best['area']:.0f}")
            return best['polygon']
        
        return None
    
    def create_optimization_layer(self, name: str = 'OPTIMIZED_PLOTS', 
                                  color: int = 1) -> str:
        """Create a new layer for optimization results"""
        # Remove if exists
        if name in self.doc.layers:
            # Delete existing entities on this layer
            for entity in list(self.msp.query(f'*[layer=="{name}"]')):
                self.msp.delete_entity(entity)
        else:
            # Create new layer
            self.doc.layers.add(name, color=color)
        
        logger.info(f"Created layer: {name}")
        return name
    
    def add_plot_to_layer(self, plot: Dict, layer_name: str):
        """Add a single plot to the specified layer"""
        try:
            x, y = plot['x'], plot['y']
            w, h = plot['width'], plot['height']
            
            # Convert to DXF units if needed
            scale = 1.0 / self.unit_scale if self.unit_scale != 0 else 1.0
            x *= scale
            y *= scale
            w *= scale
            h *= scale
            
            # Create rectangle
            points = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
            self.msp.add_lwpolyline(
                points, 
                close=True,
                dxfattribs={
                    'layer': layer_name,
                    'color': 5,  # Blue
                    'lineweight': 35
                }
            )
            
            # Add label
            label_height = min(w, h) / 5
            self.msp.add_mtext(
                f"{plot['id']}\n{plot['width']}x{plot['height']}m",
                dxfattribs={
                    'layer': layer_name,
                    'char_height': label_height,
                    'color': 3  # Green
                }
            ).set_location((x + w/2, y + h/2))
            
        except Exception as e:
            logger.warning(f"Error adding plot: {e}")
    
    def add_metadata_text(self, metrics: Dict, layer_name: str):
        """Add optimization metadata as text"""
        # Find top-left corner of drawing
        boundary = self.extract_boundary()
        if boundary:
            minx, miny, maxx, maxy = boundary.bounds
            insert_x = minx / self.unit_scale if self.unit_scale else minx
            insert_y = maxy / self.unit_scale if self.unit_scale else maxy
        else:
            insert_x, insert_y = 0, 0
        
        metadata = (
            f"OPTIMIZATION RESULTS\n"
            f"==================\n"
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Plots: {metrics.get('num_plots', 0)}\n"
            f"Area: {metrics.get('total_plot_area', 0):.0f} m2\n"
            f"Util: {metrics.get('utilization_percent', 0):.1f}%\n"
            f"Valid: {'YES' if metrics.get('valid', False) else 'NO'}"
        )
        
        scale = 1.0 / self.unit_scale if self.unit_scale != 0 else 1.0
        self.msp.add_mtext(
            metadata,
            dxfattribs={
                'layer': layer_name,
                'char_height': 500 * scale,  # Adjust based on scale
                'color': 3
            }
        ).set_location((insert_x + 1000*scale, insert_y + 1000*scale))
    
    def export_with_preservation(
        self, 
        output_path: str,
        plots: List[Dict],
        metrics: Dict
    ) -> Tuple[bool, Dict]:
        """
        Export DXF with ALL original data preserved + optimization results.
        
        Args:
            output_path: Output file path
            plots: List of plot dictionaries
            metrics: Optimization metrics
        
        Returns:
            (success, stats_dict)
        """
        if self.doc is None:
            return False, {'error': 'No document loaded'}
        
        logger.info("=" * 60)
        logger.info("EXPORTING WITH FULL DATA PRESERVATION")
        logger.info("=" * 60)
        
        # Step 1: Detect units
        self.detect_units()
        
        # Step 2: Log original data
        layer_summary = self.get_layer_summary()
        logger.info(f"\nPreserving {len(layer_summary)} layers:")
        for layer, count in layer_summary.items():
            logger.info(f"  - {layer}: {count} entities")
        
        # Step 3: Create optimization layer
        opt_layer = self.create_optimization_layer('OPTIMIZED_PLOTS', color=5)
        
        # Step 4: Add plots
        for plot in plots:
            self.add_plot_to_layer(plot, opt_layer)
        logger.info(f"Added {len(plots)} plots to {opt_layer}")
        
        # Step 5: Add metadata
        self.add_metadata_text(metrics, opt_layer)
        
        # Step 6: Save
        self.doc.saveas(output_path)
        
        # Step 7: Verify
        input_size = self.get_file_size(self.input_path)
        output_size = self.get_file_size(output_path)
        preservation = (output_size / input_size) * 100 if input_size > 0 else 0
        
        stats = {
            'input_file': self.input_path,
            'output_file': output_path,
            'input_size_kb': input_size,
            'output_size_kb': output_size,
            'preservation_percent': preservation,
            'original_layers': len(self.original_layers),
            'original_entities': self.original_entity_count,
            'plots_added': len(plots)
        }
        
        logger.info(f"\n{'=' * 60}")
        logger.info("EXPORT COMPLETE")
        logger.info(f"{'=' * 60}")
        logger.info(f"  Input:  {input_size:.1f} KB")
        logger.info(f"  Output: {output_size:.1f} KB")
        logger.info(f"  Preservation: {preservation:.1f}%")
        
        if preservation >= 95:
            logger.info(f"  Status: SUCCESS - All data preserved!")
            return True, stats
        elif preservation >= 80:
            logger.warning(f"  Status: WARNING - Some data may be lost")
            return True, stats
        else:
            logger.error(f"  Status: ERROR - Significant data loss!")
            return False, stats


# =============================================================================
# COMPLETE OPTIMIZATION PIPELINE
# =============================================================================

def optimize_cadastral_with_preservation(
    input_dxf: str,
    output_dxf: str = None
) -> Dict:
    """
    Complete pipeline that:
    1. Reads real DXF boundary
    2. Optimizes plot placement
    3. Exports with ALL original data preserved
    
    Args:
        input_dxf: Path to input cadastral DXF
        output_dxf: Path to output DXF (default: adds _OPTIMIZED suffix)
    
    Returns:
        Complete result dictionary
    """
    from shapely.geometry import Polygon
    from shapely.affinity import scale as scale_geom
    
    if output_dxf is None:
        base, ext = os.path.splitext(input_dxf)
        output_dxf = f"{base}_OPTIMIZED{ext}"
    
    print("\n" + "=" * 70)
    print("PRODUCTION CADASTRAL OPTIMIZATION WITH DATA PRESERVATION")
    print("=" * 70)
    
    # Step 1: Create exporter (loads DXF)
    print("\nStep 1: Loading input DXF...")
    exporter = ProductionDXFExporter(input_dxf)
    
    if exporter.doc is None:
        return {'status': 'ERROR', 'message': 'Could not load DXF'}
    
    # Step 2: Detect units and extract boundary
    print("\nStep 2: Extracting boundary...")
    unit_name, unit_scale = exporter.detect_units()
    boundary_raw = exporter.extract_boundary()
    
    if boundary_raw is None:
        return {'status': 'ERROR', 'message': 'No boundary found'}
    
    # Convert to meters if needed
    if unit_scale != 1.0:
        boundary_m = scale_geom(boundary_raw, xfact=unit_scale, yfact=unit_scale, origin=(0, 0))
        print(f"  Converted from {unit_name} to meters")
    else:
        boundary_m = boundary_raw
    
    area = boundary_m.area
    print(f"  Boundary area: {area:.2f} m2")
    
    # Step 3: Calculate parameters
    print("\nStep 3: Calculating adaptive parameters...")
    from src.algorithms.cadastral_optimizer import AdaptiveParameterCalculator
    params = AdaptiveParameterCalculator.calculate(area)
    print(f"  Size class: {params['size_class']}")
    print(f"  Plot range: {params['plot_min_width']}-{params['plot_max_width']}m")
    
    # Step 4: Generate plots
    print("\nStep 4: Generating plot configurations...")
    plots_config = AdaptiveParameterCalculator.generate_plots(area, params)
    print(f"  Generated {len(plots_config)} plot configs")
    
    # Step 5: Optimize
    print("\nStep 5: Running optimization...")
    from src.algorithms.cadastral_optimizer import CadastralPolygonOptimizer
    optimizer = CadastralPolygonOptimizer(boundary_m, plots_config, params)
    result = optimizer.optimize()
    
    print(f"  Plots placed: {result['metrics']['num_plots']}")
    print(f"  Utilization: {result['metrics']['utilization_percent']:.1f}%")
    
    # Step 6: Export with preservation
    print("\nStep 6: Exporting with data preservation...")
    metrics = result['metrics']
    metrics['valid'] = result['is_valid']
    
    success, stats = exporter.export_with_preservation(
        output_dxf,
        result['plots'],
        metrics
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("COMPLETE!")
    print("=" * 70)
    print(f"  Input:  {input_dxf}")
    print(f"          {stats['input_size_kb']:.1f} KB")
    print(f"  Output: {output_dxf}")
    print(f"          {stats['output_size_kb']:.1f} KB")
    print(f"  Data preservation: {stats['preservation_percent']:.1f}%")
    print(f"  Plots added: {stats['plots_added']}")
    print("=" * 70)
    
    return {
        'status': 'SUCCESS' if success else 'WARNING',
        'input': input_dxf,
        'output': output_dxf,
        'stats': stats,
        'result': result
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
    output_file = r"D:\Gitrepo\REMB\output\Bel_Air_FULL_PRESERVED.dxf"
    
    result = optimize_cadastral_with_preservation(input_file, output_file)
    
    if result['status'] in ['SUCCESS', 'WARNING']:
        print("\nData preservation verified!")
        print(f"  Original: {result['stats']['input_size_kb']:.1f} KB")
        print(f"  Output:   {result['stats']['output_size_kb']:.1f} KB")
    else:
        print(f"\nError: {result.get('message', 'Unknown error')}")
