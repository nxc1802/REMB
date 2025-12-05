"""
IO Tools for REMB Agent
Tools for reading/writing CAD files and rendering images
"""
from langchain_core.tools import tool
from typing import Dict, Any, Optional, List
import tempfile
import os

import ezdxf
from shapely.geometry import Polygon


@tool
def read_dxf(file_path: str) -> Dict[str, Any]:
    """
    Read and parse a DXF or DWG CAD file to extract site boundary geometry.
    
    Args:
        file_path: Path to DXF or DWG file
        
    Returns:
        Dictionary containing:
        - boundary: GeoJSON Feature with polygon geometry
        - metadata: Area, perimeter, bounds, centroid
        - status: Success or error info
    """
    if not os.path.exists(file_path):
        return {
            "status": "error",
            "message": f"File not found: {file_path}"
        }
    
    filename_lower = file_path.lower()
    if not (filename_lower.endswith('.dxf') or filename_lower.endswith('.dwg')):
        return {
            "status": "error", 
            "message": "File must be .dxf or .dwg format"
        }
    
    try:
        # Parse the file
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        # Find closed polylines (potential boundaries)
        polygons = []
        for entity in msp:
            if entity.dxftype() == 'LWPOLYLINE':
                if entity.closed:
                    points = list(entity.get_points())
                    if len(points) >= 3:
                        coords = [(p[0], p[1]) for p in points]
                        coords.append(coords[0])  # Close polygon
                        poly = Polygon(coords)
                        if poly.is_valid:
                            polygons.append((poly, coords))
            elif entity.dxftype() == 'POLYLINE':
                if entity.is_closed:
                    points = list(entity.points())
                    if len(points) >= 3:
                        coords = [(p[0], p[1]) for p in points]
                        coords.append(coords[0])
                        poly = Polygon(coords)
                        if poly.is_valid:
                            polygons.append((poly, coords))
        
        if not polygons:
            return {
                "status": "error",
                "message": "No closed polygons found in file"
            }
        
        # Get largest polygon as site boundary
        polygon, coords = max(polygons, key=lambda x: x[0].area)
        
        # Create GeoJSON
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": {"source": os.path.basename(file_path)}
        }
        
        # Calculate metadata
        metadata = {
            "area": polygon.area,
            "perimeter": polygon.length,
            "bounds": list(polygon.bounds),
            "centroid": [polygon.centroid.x, polygon.centroid.y],
            "vertex_count": len(coords) - 1
        }
        
        return {
            "status": "success",
            "boundary": geojson_data,
            "metadata": metadata,
            "coords": coords
        }
        
    except IOError as e:
        if filename_lower.endswith('.dwg'):
            return {
                "status": "error",
                "message": "DWG files require conversion to DXF first. Please convert using AutoCAD or online converter."
            }
        return {
            "status": "error",
            "message": f"Failed to read file: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error processing file: {str(e)}"
        }


@tool  
def write_dxf(layout: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """
    Export a layout with plots to a DXF file for CAD software.
    
    Args:
        layout: Dictionary containing boundary coords and plots list
        output_path: Path for output DXF file
        
    Returns:
        Dictionary with status and file path
    """
    from datetime import datetime
    from ezdxf.enums import TextEntityAlignment
    
    try:
        # Create new DXF document
        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()
        
        # Setup layers
        layers = {
            'BOUNDARY': {'color': 7},      # White
            'SETBACK': {'color': 1},       # Red
            'PLOTS': {'color': 5},         # Blue
            'LABELS': {'color': 7},        # White
            'ANNOTATIONS': {'color': 2},   # Yellow
        }
        
        for name, props in layers.items():
            doc.layers.add(name, color=props['color'])
        
        # Draw boundary
        boundary_coords = layout.get("boundary_coords", [])
        if boundary_coords:
            msp.add_lwpolyline(boundary_coords, dxfattribs={'layer': 'BOUNDARY', 'closed': True})
            
            # Draw setback zone (50m buffer)
            boundary_poly = Polygon(boundary_coords)
            setback = boundary_poly.buffer(-50)
            if not setback.is_empty:
                setback_coords = list(setback.exterior.coords)
                msp.add_lwpolyline(setback_coords, dxfattribs={'layer': 'SETBACK', 'closed': True})
        
        # Draw plots
        plots = layout.get("plots", [])
        for i, plot in enumerate(plots):
            coords = plot.get("coords", [])
            if coords:
                msp.add_lwpolyline(coords, dxfattribs={'layer': 'PLOTS', 'closed': True})
                
                # Add label
                plot_poly = Polygon(coords)
                centroid = plot_poly.centroid
                msp.add_text(
                    f"P{i+1}",
                    dxfattribs={
                        'layer': 'LABELS',
                        'height': 5,
                        'insert': (centroid.x, centroid.y)
                    }
                )
                
                # Add area annotation
                area = plot.get("area", plot_poly.area)
                msp.add_text(
                    f"{area:.0f}m²",
                    dxfattribs={
                        'layer': 'ANNOTATIONS',
                        'height': 3,
                        'insert': (centroid.x, centroid.y - 8)
                    }
                )
        
        # Save file
        doc.saveas(output_path)
        
        return {
            "status": "success",
            "file_path": output_path,
            "plots_exported": len(plots)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write DXF: {str(e)}"
        }


@tool
def validate_geometry(coords: List[List[float]]) -> Dict[str, Any]:
    """
    Validate geometry coordinates for correctness and fix if possible.
    
    Args:
        coords: List of [x, y] coordinate pairs forming a polygon
        
    Returns:
        Dictionary with validation status and fixed geometry if needed
    """
    try:
        # Create polygon
        polygon = Polygon(coords)
        
        # Check validity
        is_valid = polygon.is_valid
        
        if not is_valid:
            # Try to fix with buffer(0)
            fixed = polygon.buffer(0)
            if fixed.is_valid:
                fixed_coords = list(fixed.exterior.coords)
                return {
                    "status": "fixed",
                    "original_valid": False,
                    "fixed_coords": fixed_coords,
                    "area": fixed.area,
                    "message": "Geometry was invalid but has been fixed"
                }
            else:
                return {
                    "status": "invalid",
                    "original_valid": False,
                    "message": "Geometry is invalid and could not be fixed"
                }
        
        return {
            "status": "valid",
            "original_valid": True,
            "area": polygon.area,
            "perimeter": polygon.length,
            "is_convex": polygon.convex_hull.area == polygon.area
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}"
        }


@tool
def render_layout_preview(
    boundary_coords: List[List[float]], 
    plots: List[Dict[str, Any]],
    width: int = 800,
    height: int = 600
) -> Dict[str, Any]:
    """
    Generate a preview image of the layout for visualization.
    
    Args:
        boundary_coords: Site boundary coordinates
        plots: List of plot dictionaries with coords
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        Dictionary with base64 encoded image or error
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon as MplPolygon
        from matplotlib.collections import PatchCollection
        import io
        import base64
        
        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
        
        # Draw boundary
        if boundary_coords:
            boundary_patch = MplPolygon(boundary_coords, fill=False, edgecolor='black', linewidth=2)
            ax.add_patch(boundary_patch)
            
            # Draw setback
            boundary_poly = Polygon(boundary_coords)
            setback = boundary_poly.buffer(-50)
            if not setback.is_empty:
                setback_coords = list(setback.exterior.coords)
                setback_patch = MplPolygon(setback_coords, fill=False, edgecolor='red', linestyle='--', linewidth=1)
                ax.add_patch(setback_patch)
        
        # Draw plots with colors
        colors = plt.cm.Set3.colors
        for i, plot in enumerate(plots):
            coords = plot.get("coords", [])
            if coords:
                color = colors[i % len(colors)]
                plot_patch = MplPolygon(coords, alpha=0.6, facecolor=color, edgecolor='blue', linewidth=1)
                ax.add_patch(plot_patch)
                
                # Add label
                plot_poly = Polygon(coords)
                centroid = plot_poly.centroid
                ax.text(centroid.x, centroid.y, f"P{i+1}", ha='center', va='center', fontsize=8)
        
        # Set axis limits
        if boundary_coords:
            xs = [c[0] for c in boundary_coords]
            ys = [c[1] for c in boundary_coords]
            margin = 50
            ax.set_xlim(min(xs) - margin, max(xs) + margin)
            ax.set_ylim(min(ys) - margin, max(ys) + margin)
        
        ax.set_aspect('equal')
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_title('Layout Preview')
        ax.grid(True, alpha=0.3)
        
        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close(fig)
        
        return {
            "status": "success",
            "image_base64": image_base64,
            "format": "png"
        }
        
    except ImportError:
        return {
            "status": "error",
            "message": "matplotlib not installed for rendering"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Render error: {str(e)}"
        }


# Export all tools
io_tools = [read_dxf, write_dxf, validate_geometry, render_layout_preview]
