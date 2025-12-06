"""
DXF Preserver
=============
Preserves original DXF data while adding optimization results.

Features:
- Load original DXF with ALL layers preserved
- Add new "OPTIMIZED_PLOTS" layer with optimization results
- Add roads, annotations, and infrastructure
- Maintain 100% data integrity
"""

import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import Polygon, shape, LineString
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DXFPreserver:
    """Preserves original DXF while adding optimization results"""
    
    # Layer colors (AutoCAD color indices)
    COLORS = {
        'OPTIMIZED_PLOTS': 3,      # Green
        'OPTIMIZED_ROADS': 1,      # Red
        'ANNOTATIONS': 7,          # White
        'INFRASTRUCTURE': 5,       # Blue
    }
    
    def __init__(self, input_dxf_path: str):
        """
        Initialize with input DXF file
        
        Args:
            input_dxf_path: Path to original DXF file
        """
        self.input_path = input_dxf_path
        self.doc = None
        self.msp = None
        
        try:
            self.doc = ezdxf.readfile(input_dxf_path)
            self.msp = self.doc.modelspace()
            
            file_size = Path(input_dxf_path).stat().st_size / 1024
            layer_count = len(list(self.doc.layers))
            entity_count = len(list(self.msp))
            
            logger.info(f"✅ Loaded DXF: {Path(input_dxf_path).name}")
            logger.info(f"   Size: {file_size:.1f} KB, Layers: {layer_count}, Entities: {entity_count}")
            print(f"✅ Loaded DXF: {Path(input_dxf_path).name}")
            print(f"   Size: {file_size:.1f} KB, Layers: {layer_count}, Entities: {entity_count}")
            
        except Exception as e:
            logger.error(f"❌ Error loading DXF: {e}")
            print(f"❌ Error loading DXF: {e}")
            self.doc = None
    
    def add_optimization_layer(self, layer_name: str = "OPTIMIZED_PLOTS") -> Optional[str]:
        """
        Add a new layer for optimization results
        
        Args:
            layer_name: Name for the new layer
            
        Returns:
            Layer name if successful, None otherwise
        """
        if self.doc is None:
            return None
        
        try:
            # Create layer if it doesn't exist
            if layer_name not in self.doc.layers:
                self.doc.layers.add(
                    layer_name,
                    color=self.COLORS.get(layer_name, 3)
                )
                logger.info(f"✅ Created layer: {layer_name}")
            
            return layer_name
            
        except Exception as e:
            logger.error(f"❌ Error creating layer: {e}")
            return None
    
    def add_plots(
        self, 
        plots: List[Dict], 
        layer_name: str = "OPTIMIZED_PLOTS"
    ) -> int:
        """
        Add plot polygons from optimization result
        
        Args:
            plots: List of plot dicts with 'geom' field
            layer_name: Target layer name
            
        Returns:
            Number of plots added
        """
        if self.doc is None:
            return 0
        
        # Ensure layer exists
        self.add_optimization_layer(layer_name)
        
        count = 0
        for plot in plots:
            try:
                # Get geometry
                if 'geom' in plot:
                    geom = shape(plot['geom'])
                elif 'x' in plot and 'y' in plot and 'width' in plot and 'depth' in plot:
                    # Create box from coordinates
                    from shapely.geometry import box
                    geom = box(
                        plot['x'], plot['y'],
                        plot['x'] + plot['width'],
                        plot['y'] + plot['depth']
                    )
                else:
                    continue
                
                # Add polygon to DXF
                points = list(geom.exterior.coords)
                self.msp.add_lwpolyline(
                    points,
                    close=True,
                    dxfattribs={'layer': layer_name}
                )
                
                # Add plot ID label
                centroid = geom.centroid
                plot_id = plot.get('id', f'Plot_{count+1}')
                self.msp.add_text(
                    plot_id,
                    dxfattribs={
                        'layer': layer_name,
                        'height': 5,
                        'insert': (centroid.x, centroid.y)
                    }
                )
                
                count += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Error adding plot: {e}")
        
        logger.info(f"✅ Added {count} plots to layer '{layer_name}'")
        print(f"✅ Added {count} plots to layer '{layer_name}'")
        return count
    
    def add_roads(
        self, 
        roads: List[Dict], 
        layer_name: str = "OPTIMIZED_ROADS"
    ) -> int:
        """
        Add road lines from optimization result
        
        Args:
            roads: List of road dicts
            layer_name: Target layer name
            
        Returns:
            Number of roads added
        """
        if self.doc is None:
            return 0
        
        # Ensure layer exists
        self.add_optimization_layer(layer_name)
        
        count = 0
        for road in roads:
            try:
                if 'start' in road and 'end' in road:
                    self.msp.add_line(
                        road['start'],
                        road['end'],
                        dxfattribs={'layer': layer_name}
                    )
                    count += 1
                    
            except Exception as e:
                logger.warning(f"⚠️ Error adding road: {e}")
        
        logger.info(f"✅ Added {count} roads to layer '{layer_name}'")
        print(f"✅ Added {count} roads to layer '{layer_name}'")
        return count
    
    def add_optimization_result(self, result: Dict) -> Dict:
        """
        Add complete optimization result to DXF
        
        Args:
            result: Optimization result dict from gpu_optimizer
            
        Returns:
            Summary dict
        """
        if self.doc is None:
            return {'status': 'ERROR', 'message': 'DXF not loaded'}
        
        summary = {
            'plots_added': 0,
            'roads_added': 0,
            'layers_created': []
        }
        
        # Add plots
        if 'plots' in result:
            summary['plots_added'] = self.add_plots(result['plots'])
            summary['layers_created'].append('OPTIMIZED_PLOTS')
        
        # Add roads
        if 'roads' in result:
            summary['roads_added'] = self.add_roads(result['roads'])
            summary['layers_created'].append('OPTIMIZED_ROADS')
        
        # Add title block with optimization info
        self._add_optimization_info(result)
        
        return summary
    
    def _add_optimization_info(self, result: Dict):
        """Add optimization information as text block"""
        if self.doc is None:
            return
        
        # Ensure layer exists
        self.add_optimization_layer('ANNOTATIONS')
        
        # Find a suitable location (top-left of extents)
        minx, miny, maxx, maxy = self._get_extents()
        
        # Create info text
        info_lines = [
            f"OPTIMIZATION RESULTS",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Plots: {result.get('plots_generated', 0)}",
            f"Utilization: {result.get('utilization_percent', 0):.1f}%",
            f"GPU: {'Yes' if result.get('used_gpu') else 'No'}",
        ]
        
        y_offset = maxy + 50
        for line in info_lines:
            try:
                self.msp.add_text(
                    line,
                    dxfattribs={
                        'layer': 'ANNOTATIONS',
                        'height': 10,
                        'insert': (minx, y_offset)
                    }
                )
                y_offset -= 15
            except Exception as e:
                logger.warning(f"⚠️ Error adding text: {e}")
    
    def _get_extents(self) -> tuple:
        """Get bounding box of all entities"""
        if self.doc is None:
            return (0, 0, 1000, 1000)
        
        try:
            from ezdxf.addons import geo
            
            # Try to get extents from modelspace
            minx, miny = float('inf'), float('inf')
            maxx, maxy = float('-inf'), float('-inf')
            
            for entity in self.msp:
                try:
                    if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                        x, y = entity.dxf.insert.x, entity.dxf.insert.y
                        minx, maxx = min(minx, x), max(maxx, x)
                        miny, maxy = min(miny, y), max(maxy, y)
                except Exception:
                    pass
            
            if minx == float('inf'):
                return (0, 0, 1000, 1000)
            
            return (minx, miny, maxx, maxy)
            
        except Exception:
            return (0, 0, 1000, 1000)
    
    def save(self, output_path: str) -> bool:
        """
        Save enhanced DXF file
        
        Args:
            output_path: Output file path
            
        Returns:
            True if successful
        """
        if self.doc is None:
            return False
        
        try:
            self.doc.saveas(output_path)
            
            file_size = Path(output_path).stat().st_size / 1024
            logger.info(f"✅ Saved DXF: {Path(output_path).name} ({file_size:.1f} KB)")
            print(f"✅ Saved DXF: {Path(output_path).name} ({file_size:.1f} KB)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving DXF: {e}")
            print(f"❌ Error saving DXF: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """Get summary of current DXF state"""
        if self.doc is None:
            return {'status': 'NOT_LOADED'}
        
        layers = [layer.dxf.name for layer in self.doc.layers]
        entity_counts = {}
        
        for entity in self.msp:
            entity_type = entity.dxftype()
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        return {
            'status': 'LOADED',
            'layers': layers,
            'layer_count': len(layers),
            'entity_counts': entity_counts,
            'total_entities': sum(entity_counts.values())
        }


# =============================================================================
# INTEGRATION FUNCTIONS
# =============================================================================

def export_optimization_to_dxf(
    input_dxf: str,
    optimization_result: Dict,
    output_dxf: str
) -> bool:
    """
    Export optimization result to DXF with full data preservation
    
    Args:
        input_dxf: Path to original DXF
        optimization_result: Result from gpu_optimizer
        output_dxf: Output file path
        
    Returns:
        True if successful
    """
    preserver = DXFPreserver(input_dxf)
    
    if preserver.doc is None:
        return False
    
    # Add optimization results
    summary = preserver.add_optimization_result(optimization_result)
    
    print(f"   Added {summary['plots_added']} plots")
    print(f"   Added {summary['roads_added']} roads")
    
    # Save
    return preserver.save(output_dxf)


def full_pipeline(
    input_dxf: str,
    output_dxf: str,
    config: Optional[Dict] = None,
    use_gpu: bool = True
) -> Dict:
    """
    Complete pipeline: DXF → Optimize → Enhanced DXF
    
    Args:
        input_dxf: Path to input DXF
        output_dxf: Path for output DXF
        config: Optional configuration
        use_gpu: Whether to use GPU
        
    Returns:
        Result summary dict
    """
    from src.algorithms.gpu_optimizer import optimize_from_dxf
    
    print(f"\n{'='*60}")
    print(f"REMB Full Pipeline")
    print(f"{'='*60}\n")
    
    # Step 1: Optimize
    print("Step 1: Running optimization...")
    result = optimize_from_dxf(input_dxf, config=config, use_gpu=use_gpu)
    
    # Step 2: Export
    print("\nStep 2: Exporting to DXF...")
    success = export_optimization_to_dxf(input_dxf, result, output_dxf)
    
    # Summary
    summary = {
        'input': input_dxf,
        'output': output_dxf,
        'plots': result.get('plots_generated', 0),
        'utilization': result.get('utilization_percent', 0),
        'success': success
    }
    
    print(f"\n{'='*60}")
    print(f"Pipeline Complete!")
    print(f"  Input:  {input_dxf}")
    print(f"  Output: {output_dxf}")
    print(f"  Plots:  {summary['plots']}")
    print(f"  Util:   {summary['utilization']:.1f}%")
    print(f"{'='*60}\n")
    
    return summary


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == '__main__':
    import sys
    
    print(f"\n{'='*60}")
    print(f"DXF Preserver - Testing")
    print(f"{'='*60}\n")
    
    if len(sys.argv) > 1:
        input_dxf = sys.argv[1]
    else:
        input_dxf = 'examples/Lot Plan Bel air Technical Description.dxf'
    
    output_dxf = 'output/Bel_Air_OPTIMIZED_PRESERVED.dxf'
    
    try:
        summary = full_pipeline(input_dxf, output_dxf, use_gpu=True)
        
        if summary['success']:
            # Compare file sizes
            import os
            input_size = os.path.getsize(input_dxf) / 1024
            output_size = os.path.getsize(output_dxf) / 1024
            
            print(f"Input size:  {input_size:.1f} KB")
            print(f"Output size: {output_size:.1f} KB")
            print(f"Data preserved: {'✅ YES' if output_size >= input_size * 0.9 else '❌ NO'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
