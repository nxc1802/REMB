"""
DXF Exporter - Engineering Delivery
Export layouts to AutoCAD DXF format with proper layering
"""
import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import logging
from datetime import datetime

from src.models.domain import Layout, Plot, PlotType, SiteBoundary, RoadNetwork

logger = logging.getLogger(__name__)


class DXFExporter:
    """
    AutoCAD DXF file exporter
    
    Exports industrial estate layouts with proper layering:
    - SITE_BOUNDARY: Site boundary polygon
    - ROADS_PRIMARY: Primary road network
    - ROADS_SECONDARY: Secondary road network
    - PLOTS_INDUSTRIAL: Industrial plots
    - PLOTS_GREEN: Green space plots
    - UTILITIES: Utility corridors
    - ANNOTATIONS: Text annotations and dimensions
    """
    
    # Layer configuration
    LAYERS = {
        'SITE_BOUNDARY': {'color': 7, 'linetype': 'CONTINUOUS'},  # White
        'ROADS_PRIMARY': {'color': 1, 'linetype': 'CONTINUOUS'},  # Red
        'ROADS_SECONDARY': {'color': 3, 'linetype': 'DASHED'},  # Green
        'ROADS_TERTIARY': {'color': 4, 'linetype': 'DASHED'},  # Cyan
        'PLOTS_INDUSTRIAL': {'color': 5, 'linetype': 'CONTINUOUS'},  # Blue
        'PLOTS_GREEN': {'color': 3, 'linetype': 'CONTINUOUS'},  # Green
        'PLOTS_UTILITY': {'color': 6, 'linetype': 'CONTINUOUS'},  # Magenta
        'CONSTRAINTS': {'color': 1, 'linetype': 'PHANTOM'},  # Red dashed
        'ANNOTATIONS': {'color': 7, 'linetype': 'CONTINUOUS'},  # White
        'DIMENSIONS': {'color': 2, 'linetype': 'CONTINUOUS'},  # Yellow
    }
    
    def __init__(self, version: str = "R2010"):
        """
        Initialize DXF exporter
        
        Args:
            version: DXF version ('R12', 'R2000', 'R2004', 'R2007', 'R2010', 'R2013', 'R2018')
        """
        self.version = version
        self.logger = logging.getLogger(__name__)
    
    def export(
        self,
        layout: Layout,
        filepath: str,
        include_annotations: bool = True,
        include_dimensions: bool = True
    ) -> str:
        """
        Export layout to DXF file
        
        Args:
            layout: Layout to export
            filepath: Output file path
            include_annotations: Include text annotations
            include_dimensions: Include dimensions
            
        Returns:
            Path to created file
        """
        self.logger.info(f"Exporting layout {layout.id} to DXF: {filepath}")
        
        # Create new DXF document with setup=True to include standard linetypes (DASHED, PHANTOM, etc.)
        doc = ezdxf.new(dxfversion=self.version, setup=True)
        msp = doc.modelspace()
        
        # Setup layers and dimension style
        self._setup_layers(doc)
        self._setup_dimension_style(doc)
        
        # Export site boundary
        if layout.site_boundary and layout.site_boundary.geometry:
            self._export_site_boundary(msp, layout.site_boundary)
        
        # Export road network
        if layout.road_network:
            self._export_road_network(msp, layout.road_network)
        
        # Export plots
        for plot in layout.plots:
            self._export_plot(msp, plot)
        
        # Export constraints
        if layout.site_boundary:
            for constraint in layout.site_boundary.constraints:
                self._export_constraint(msp, constraint)
        
        # Add annotations
        if include_annotations:
            self._add_annotations(msp, layout)
        
        # Add dimensions
        if include_dimensions:
            self._add_dimensions(msp, layout)
        
        # Add title block
        self._add_title_block(msp, layout)
        
        # Save file with error handling for file locking
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            doc.saveas(str(filepath))
        except PermissionError:
            # File is locked (e.g., open in AutoCAD)
            self.logger.warning(f"File is locked: {filepath}, trying alternate name")
            timestamp = datetime.now().strftime('%H%M%S')
            alt_path = output_path.with_stem(f"{output_path.stem}_{timestamp}")
            doc.saveas(str(alt_path))
            self.logger.info(f"DXF exported to alternate path: {alt_path}")
            return str(alt_path)
        
        self.logger.info(f"DXF exported successfully: {filepath}")
        return str(filepath)
    
    def _setup_layers(self, doc):
        """Setup DXF layers with colors and linetypes"""
        for layer_name, config in self.LAYERS.items():
            linetype = config.get('linetype', 'CONTINUOUS')
            # Ensure linetype exists (setup=True should provide DASHED, PHANTOM, etc.)
            if linetype not in doc.linetypes:
                linetype = 'CONTINUOUS'
            doc.layers.add(
                layer_name,
                color=config['color'],
                linetype=linetype
            )
    
    def _setup_dimension_style(self, doc):
        """
        Setup custom dimension style for stability
        Prevents crashes from malformed default dimension styles
        """
        # Create custom engineering dimension style
        if 'ENG_DIM' not in doc.dimstyles:
            dim_style = doc.dimstyles.new('ENG_DIM')
            dim_style.dxf.dimtxt = 2.5      # Text height
            dim_style.dxf.dimasz = 2.5      # Arrow size
            dim_style.dxf.dimexe = 1.5      # Extension line extension
            dim_style.dxf.dimexo = 0.625    # Extension line offset
            dim_style.dxf.dimgap = 0.625    # Gap from dimension line
            dim_style.dxf.dimdec = 2        # Decimal places
            dim_style.dxf.dimtad = 1        # Text above dimension line
            dim_style.dxf.dimclrd = 2       # Dimension line color (yellow)
            dim_style.dxf.dimclre = 2       # Extension line color (yellow)
            dim_style.dxf.dimclrt = 7       # Text color (white)
    
    def _export_site_boundary(self, msp, site: SiteBoundary):
        """Export site boundary polygon"""
        if site.geometry:
            coords = self._polygon_to_coords(site.geometry)
            msp.add_lwpolyline(
                coords,
                dxfattribs={'layer': 'SITE_BOUNDARY', 'closed': True}
            )
    
    def _export_road_network(self, msp, road_network: RoadNetwork):
        """Export road network lines"""
        # Primary roads
        if road_network.primary_roads:
            self._export_multilinestring(
                msp, road_network.primary_roads, 'ROADS_PRIMARY'
            )
        
        # Secondary roads
        if road_network.secondary_roads:
            self._export_multilinestring(
                msp, road_network.secondary_roads, 'ROADS_SECONDARY'
            )
        
        # Tertiary roads
        if road_network.tertiary_roads:
            self._export_multilinestring(
                msp, road_network.tertiary_roads, 'ROADS_TERTIARY'
            )
    
    def _export_multilinestring(self, msp, geometry, layer: str):
        """Export MultiLineString or LineString to DXF"""
        if hasattr(geometry, 'geoms'):
            lines = geometry.geoms
        else:
            lines = [geometry]
        
        for line in lines:
            if isinstance(line, LineString):
                points = [(p[0], p[1]) for p in line.coords]
                msp.add_lwpolyline(
                    points,
                    dxfattribs={'layer': layer}
                )
    
    def _export_plot(self, msp, plot: Plot):
        """Export a plot polygon"""
        if not plot.geometry:
            return
        
        # Determine layer based on plot type
        layer_map = {
            PlotType.INDUSTRIAL: 'PLOTS_INDUSTRIAL',
            PlotType.GREEN_SPACE: 'PLOTS_GREEN',
            PlotType.UTILITY: 'PLOTS_UTILITY',
            PlotType.ROAD: 'ROADS_TERTIARY',
            PlotType.BUFFER: 'CONSTRAINTS'
        }
        layer = layer_map.get(plot.type, 'PLOTS_INDUSTRIAL')
        
        # Export polygon
        coords = self._polygon_to_coords(plot.geometry)
        msp.add_lwpolyline(
            coords,
            dxfattribs={'layer': layer, 'closed': True}
        )
        
        # Add plot ID label at centroid
        centroid = plot.geometry.centroid
        msp.add_text(
            plot.id,
            dxfattribs={
                'layer': 'ANNOTATIONS',
                'height': 2,
                'insert': (centroid.x, centroid.y)
            }
        )
    
    def _export_constraint(self, msp, constraint):
        """Export constraint zone"""
        if not constraint.geometry:
            return
        
        if isinstance(constraint.geometry, Polygon):
            coords = self._polygon_to_coords(constraint.geometry)
            msp.add_lwpolyline(
                coords,
                dxfattribs={'layer': 'CONSTRAINTS', 'closed': True}
            )
    
    def _add_annotations(self, msp, layout: Layout):
        """Add text annotations"""
        # Summary annotation at top-right
        if layout.site_boundary:
            bounds = layout.site_boundary.geometry.bounds
            maxx, maxy = bounds[2], bounds[3]
            
            # Create summary text
            metrics = layout.metrics
            summary_lines = [
                f"LAYOUT SUMMARY",
                f"----------------",
                f"Total Area: {metrics.total_area_sqm:.0f} m²",
                f"Sellable: {metrics.sellable_area_sqm:.0f} m² ({metrics.sellable_ratio*100:.1f}%)",
                f"Green: {metrics.green_space_area_sqm:.0f} m² ({metrics.green_space_ratio*100:.1f}%)",
                f"Roads: {metrics.road_area_sqm:.0f} m²",
                f"Num Plots: {metrics.num_plots}",
                f"Compliant: {'Yes' if metrics.is_compliant else 'No'}"
            ]
            
            y_offset = maxy + 20
            for line in summary_lines:
                msp.add_text(
                    line,
                    dxfattribs={
                        'layer': 'ANNOTATIONS',
                        'height': 3,
                        'insert': (maxx + 20, y_offset)
                    }
                )
                y_offset -= 5
    
    def _add_dimensions(self, msp, layout: Layout):
        """Add dimension annotations"""
        if layout.site_boundary and layout.site_boundary.geometry:
            bounds = layout.site_boundary.geometry.bounds
            minx, miny, maxx, maxy = bounds
            
            # Add site dimensions using custom dimension style
            # Width dimension
            msp.add_linear_dim(
                base=(minx, miny - 10),
                p1=(minx, miny),
                p2=(maxx, miny),
                dimstyle='ENG_DIM',
                dxfattribs={'layer': 'DIMENSIONS'}
            ).render()
            
            # Height dimension
            msp.add_linear_dim(
                base=(maxx + 10, miny),
                p1=(maxx, miny),
                p2=(maxx, maxy),
                angle=90,
                dimstyle='ENG_DIM',
                dxfattribs={'layer': 'DIMENSIONS'}
            ).render()
    
    def _add_title_block(self, msp, layout: Layout):
        """Add title block with project info"""
        if not layout.site_boundary:
            return
        
        bounds = layout.site_boundary.geometry.bounds
        minx, miny = bounds[0], bounds[1]
        
        # Title block at bottom-left
        title_lines = [
            "INDUSTRIAL ESTATE MASTER PLAN",
            f"Layout ID: {layout.id}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "REMB Optimization Engine v0.1.0",
            "PiXerse.AI"
        ]
        
        y_offset = miny - 30
        for i, line in enumerate(title_lines):
            msp.add_text(
                line,
                dxfattribs={
                    'layer': 'ANNOTATIONS',
                    'height': 4 if i == 0 else 2.5,
                    'insert': (minx, y_offset)
                }
            )
            y_offset -= 6
    
    def _polygon_to_coords(self, polygon: Polygon) -> List[Tuple[float, float]]:
        """Convert Shapely polygon to coordinate list"""
        return [(p[0], p[1]) for p in polygon.exterior.coords]
    
    def export_pareto_front(
        self,
        pareto_front,
        output_dir: str,
        prefix: str = "layout"
    ) -> List[str]:
        """
        Export all layouts in a Pareto front
        
        Args:
            pareto_front: ParetoFront object
            output_dir: Output directory
            prefix: Filename prefix
            
        Returns:
            List of created file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = []
        for i, layout in enumerate(pareto_front.layouts):
            filename = f"{prefix}_{i:02d}_{layout.id[:8]}.dxf"
            filepath = output_path / filename
            self.export(layout, str(filepath))
            files.append(str(filepath))
        
        return files


# Example usage
if __name__ == "__main__":
    from shapely.geometry import box
    from src.models.domain import Layout, Plot, PlotType, SiteBoundary, RoadNetwork, LayoutMetrics
    from shapely.geometry import LineString, MultiLineString
    
    # Create example layout
    site_geom = box(0, 0, 500, 500)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm
    
    layout = Layout(site_boundary=site)
    
    # Add some plots
    layout.plots = [
        Plot(
            id="plot_001",
            geometry=box(60, 60, 160, 160),
            area_sqm=10000,
            type=PlotType.INDUSTRIAL,
            width_m=100,
            depth_m=100
        ),
        Plot(
            id="plot_002",
            geometry=box(200, 60, 300, 160),
            area_sqm=10000,
            type=PlotType.INDUSTRIAL,
            width_m=100,
            depth_m=100
        ),
        Plot(
            id="green_001",
            geometry=box(60, 200, 160, 300),
            area_sqm=10000,
            type=PlotType.GREEN_SPACE,
            width_m=100,
            depth_m=100
        )
    ]
    
    # Add road network
    layout.road_network = RoadNetwork(
        primary_roads=MultiLineString([
            LineString([(0, 250), (500, 250)]),
            LineString([(250, 0), (250, 500)])
        ]),
        total_length_m=1000
    )
    
    # Calculate metrics
    layout.metrics = LayoutMetrics(
        total_area_sqm=250000,
        sellable_area_sqm=20000,
        green_space_area_sqm=10000,
        road_area_sqm=24000,
        sellable_ratio=0.65,
        green_space_ratio=0.15,
        num_plots=2,
        is_compliant=True
    )
    
    # Export
    exporter = DXFExporter()
    output_file = exporter.export(
        layout,
        "output/test_layout.dxf",
        include_annotations=True,
        include_dimensions=True
    )
    
    print(f"Exported to: {output_file}")
