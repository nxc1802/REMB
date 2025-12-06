"""
AIOptimize™ MVP API
FastAPI backend for industrial estate planning optimization
Per MVP-24h.md specification
"""
import os
import io
import json
import zipfile
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from shapely.geometry import Polygon, shape

# Import services
from src.services.session_manager import session_manager
from src.services.gemini_service import gemini_service
from src.algorithms.ga_optimizer import SimpleGAOptimizer
from src.export.dxf_exporter import DXFExporter
from src.models.domain import Layout, Plot, PlotType, SiteBoundary, LayoutMetrics

# Sample data
SAMPLE_BOUNDARY = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [0, 0], [500, 0], [500, 400], [0, 400], [0, 0]
        ]]
    },
    "properties": {"name": "Sample Industrial Site"}
}


# === Pydantic Models ===

class UploadResponse(BaseModel):
    session_id: str
    boundary: Dict[str, Any]
    metadata: Dict[str, Any]


class GenerateRequest(BaseModel):
    session_id: str
    target_plots: int = 8
    setback: float = 50.0


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    message: str
    model: str


class ExportRequest(BaseModel):
    session_id: str
    option_id: int


class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_available: bool


# === FastAPI App ===

app = FastAPI(
    title="AIOptimize™ API",
    description="AI-Powered Industrial Estate Planning Engine",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include Agent API router
from src.api.agent_api import router as agent_router
app.include_router(agent_router)

# Initialize optimizer and exporter
ga_optimizer = SimpleGAOptimizer()
dxf_exporter = DXFExporter()


# === API Endpoints ===

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        gemini_available=gemini_service.is_available
    )


@app.get("/api/sample-data")
async def get_sample_data():
    """Get sample GeoJSON boundary data"""
    return SAMPLE_BOUNDARY


@app.post("/api/upload-boundary", response_model=UploadResponse)
async def upload_boundary(file: UploadFile = File(None), geojson: str = Form(None)):
    """
    Upload site boundary (GeoJSON)
    
    Accepts either file upload or JSON string
    """
    try:
        # Get GeoJSON data
        if file and file.filename:
            content = await file.read()
            geojson_data = json.loads(content)
        elif geojson:
            geojson_data = json.loads(geojson)
        else:
            raise HTTPException(400, "No boundary data provided")
        
        # Extract coordinates from GeoJSON
        if geojson_data.get("type") == "Feature":
            geometry = geojson_data.get("geometry", {})
        elif geojson_data.get("type") == "FeatureCollection":
            features = geojson_data.get("features", [])
            if features:
                geometry = features[0].get("geometry", {})
            else:
                raise HTTPException(400, "No features in FeatureCollection")
        elif geojson_data.get("type") == "Polygon":
            geometry = geojson_data
        else:
            raise HTTPException(400, "Invalid GeoJSON format")
        
        # Get coordinates
        coords = geometry.get("coordinates", [[]])[0]
        if not coords:
            raise HTTPException(400, "No coordinates found")
        
        # Create Shapely polygon and validate
        polygon = Polygon(coords)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        
        # Calculate metadata
        metadata = {
            "area": polygon.area,
            "perimeter": polygon.length,
            "bounds": list(polygon.bounds),
            "centroid": [polygon.centroid.x, polygon.centroid.y]
        }
        
        # Create session and store data
        session = session_manager.create_session()
        session_manager.set_boundary(
            session.id,
            boundary=geojson_data,
            coords=coords,
            metadata=metadata
        )
        
        return UploadResponse(
            session_id=session.id,
            boundary=geojson_data,
            metadata=metadata
        )
        
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid JSON format: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error processing boundary: {str(e)}")


# Alternative JSON endpoint for easier frontend integration
class UploadBoundaryRequest(BaseModel):
    geojson: Dict[str, Any]


@app.post("/api/upload-boundary-json", response_model=UploadResponse)
async def upload_boundary_json(request: UploadBoundaryRequest):
    """Upload site boundary via JSON body"""
    try:
        geojson_data = request.geojson
        
        # Extract coordinates from GeoJSON
        if geojson_data.get("type") == "Feature":
            geometry = geojson_data.get("geometry", {})
        elif geojson_data.get("type") == "FeatureCollection":
            features = geojson_data.get("features", [])
            if features:
                geometry = features[0].get("geometry", {})
            else:
                raise HTTPException(400, "No features in FeatureCollection")
        elif geojson_data.get("type") == "Polygon":
            geometry = geojson_data
        else:
            raise HTTPException(400, "Invalid GeoJSON format")
        
        coords = geometry.get("coordinates", [[]])[0]
        if not coords:
            raise HTTPException(400, "No coordinates found")
        
        polygon = Polygon(coords)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        
        metadata = {
            "area": polygon.area,
            "perimeter": polygon.length,
            "bounds": list(polygon.bounds),
            "centroid": [polygon.centroid.x, polygon.centroid.y]
        }
        
        session = session_manager.create_session()
        session_manager.set_boundary(
            session.id,
            boundary=geojson_data,
            coords=coords,
            metadata=metadata
        )
        
        return UploadResponse(
            session_id=session.id,
            boundary=geojson_data,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/api/upload-dxf", response_model=UploadResponse)
async def upload_dxf(file: UploadFile = File(...)):
    """
    Upload site boundary from DXF or DWG file
    
    Parses LWPOLYLINE entities to extract site boundary polygon
    Supports both DXF and DWG formats (AutoCAD R13-R2021)
    """
    import ezdxf
    import tempfile
    
    if not file.filename:
        raise HTTPException(400, "No file provided")
    
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.dxf') or filename_lower.endswith('.dwg')):
        raise HTTPException(400, "Please upload a valid .dxf or .dwg file")
    
    try:
        # Save to temp file for ezdxf to read
        content = await file.read()
        suffix = '.dwg' if filename_lower.endswith('.dwg') else '.dxf'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # Parse DXF/DWG
        try:
            doc = ezdxf.readfile(tmp_path)
        except IOError as e:
            # ezdxf cannot read DWG files directly
            if filename_lower.endswith('.dwg'):
                raise HTTPException(
                    400, 
                    "DWG file format requires conversion. "
                    "Please convert your DWG file to DXF using AutoCAD, LibreCAD, or an online converter, "
                    "then upload the DXF file. "
                    "Alternatively, most CAD software can export/save as DXF format."
                )
            raise HTTPException(400, f"Failed to read file: {str(e)}")
        msp = doc.modelspace()
        
        # Find closed polylines
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
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if not polygons:
            raise HTTPException(400, "No closed polygons found in DXF file")
        
        # Get largest polygon as site boundary
        polygon, coords = max(polygons, key=lambda x: x[0].area)
        
        # Create GeoJSON boundary
        geojson_data = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": {"source": file.filename}
        }
        
        # Calculate metadata
        metadata = {
            "area": polygon.area,
            "perimeter": polygon.length,
            "bounds": list(polygon.bounds),
            "centroid": [polygon.centroid.x, polygon.centroid.y],
            "dxf_source": file.filename
        }
        
        # Create session
        session = session_manager.create_session()
        session_manager.set_boundary(
            session.id,
            boundary=geojson_data,
            coords=coords,
            metadata=metadata
        )
        
        print(f"[{suffix.upper()[1:]}] Parsed {file.filename}: {len(coords)-1} vertices, area={polygon.area:.0f}m²")
        
        return UploadResponse(
            session_id=session.id,
            boundary=geojson_data,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"DXF parsing error: {str(e)}")


@app.post("/api/generate-layouts")
async def generate_layouts(request: GenerateRequest):
    """
    Generate optimized layout options using Genetic Algorithm
    
    Returns 3 diverse layout options:
    1. Maximum Profit
    2. Balanced
    3. Premium
    """
    # Get session
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if not session.boundary_coords:
        raise HTTPException(400, "No boundary uploaded for this session")
    
    try:
        # Configure and run optimizer
        optimizer = SimpleGAOptimizer(
            setback=request.setback,
            target_plots=request.target_plots
        )
        
        options = optimizer.optimize(session.boundary_coords)
        
        # Store in session
        session_manager.set_layouts(request.session_id, options)
        
        return {
            "session_id": request.session_id,
            "options": options,
            "count": len(options)
        }
        
    except Exception as e:
        raise HTTPException(500, f"Optimization failed: {str(e)}")


@app.post("/api/generate-advanced")
async def generate_advanced(request: GenerateRequest):
    """
    Generate layouts using advanced optimization pipeline (NSGA-II + MILP).
    
    This endpoint uses the CoreOrchestrator for:
    - Multi-objective optimization (NSGA-II) with overlap penalty
    - MILP-based validation and refinement
    - Full regulatory compliance checking
    
    Returns multiple Pareto-optimal layout options.
    """
    # Get session
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if not session.boundary_coords:
        raise HTTPException(400, "No boundary uploaded for this session")
    
    try:
        from src.core.orchestrator import CoreOrchestrator, OrchestrationStatus
        
        orchestrator = CoreOrchestrator()
        
        # Stage 1: Initialize site from coordinates
        init_result = orchestrator.initialize_site(
            session.boundary_coords, 
            source_type="coordinates"
        )
        
        if init_result.status != OrchestrationStatus.SUCCESS:
            raise HTTPException(400, f"Site initialization failed: {init_result.message}")
        
        # Stage 2: Generate road network
        road_result = orchestrator.generate_road_network(pattern="grid", primary_spacing=150)
        
        # Stage 4: Run NSGA-II + MILP optimization
        opt_result = orchestrator.run_optimization(
            population_size=50,
            n_generations=30,
            n_plots=request.target_plots
        )
        
        if opt_result.status == OrchestrationStatus.SUCCESS:
            # Convert to frontend-compatible format
            options = []
            scenarios = opt_result.data.get("scenarios", [])
            
            for i, scenario in enumerate(scenarios):
                layout_id = scenario.get("id")
                if layout_id:
                    # Find the layout in orchestrator
                    layout = next(
                        (l for l in orchestrator.current_layouts if l.id == layout_id),
                        None
                    )
                    if layout:
                        plots_data = [{
                            "id": p.id,
                            "x": p.geometry.bounds[0] if p.geometry else 0,
                            "y": p.geometry.bounds[1] if p.geometry else 0,
                            "width": p.width_m,
                            "height": p.depth_m,
                            "area": p.area_sqm,
                            "coords": list(p.geometry.exterior.coords) if p.geometry else []
                        } for p in layout.plots if p.type == PlotType.INDUSTRIAL]
                        
                        options.append({
                            "id": i + 1,
                            "name": scenario.get("name", f"Option {i+1}"),
                            "icon": ["💰", "⚖️", "🏢"][i] if i < 3 else "📊",
                            "description": f"NSGA-II optimized layout",
                            "plots": plots_data,
                            "metrics": {
                                "total_plots": len(plots_data),
                                "total_area": layout.metrics.sellable_area_sqm,
                                "avg_size": layout.metrics.avg_plot_size_sqm,
                                "fitness": 1.0 - (layout.metrics.road_ratio or 0),
                                "compliance": "PASS" if layout.metrics.is_compliant else "FAIL"
                            }
                        })
            
            # Store in session
            session_manager.set_layouts(request.session_id, options)
            
            return {
                "session_id": request.session_id,
                "options": options,
                "count": len(options),
                "optimizer": "NSGA-II + MILP",
                "generation_time": opt_result.data.get("generation_time_seconds", 0)
            }
        else:
            # Fall back to simple GA if advanced fails
            optimizer = SimpleGAOptimizer(
                setback=request.setback,
                target_plots=request.target_plots
            )
            options = optimizer.optimize(session.boundary_coords)
            session_manager.set_layouts(request.session_id, options)
            
            return {
                "session_id": request.session_id,
                "options": options,
                "count": len(options),
                "optimizer": "SimpleGA (fallback)",
                "message": opt_result.message
            }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Advanced optimization error: {traceback.format_exc()}")
        raise HTTPException(500, f"Advanced optimization failed: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AI about layout options
    
    Uses Gemini Flash 2.0 if available, otherwise falls back to hardcoded responses
    """
    # Get session
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Add user message to history
    session_manager.add_chat_message(request.session_id, "user", request.message)
    
    # Generate response
    response = gemini_service.chat(
        message=request.message,
        layouts=session.layouts,
        boundary_metadata=session.metadata
    )
    
    # Add assistant message to history
    session_manager.add_chat_message(
        request.session_id, 
        "assistant", 
        response["message"],
        response["model"]
    )
    
    return ChatResponse(**response)


@app.post("/api/export-dxf")
async def export_dxf(request: ExportRequest):
    """
    Export single layout option to DXF
    
    Returns DXF file as download
    """
    # Get session
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if not session.layouts:
        raise HTTPException(400, "No layouts generated")
    
    # Find requested option
    option = None
    for layout in session.layouts:
        if layout.get("id") == request.option_id:
            option = layout
            break
    
    if not option:
        raise HTTPException(404, f"Option {request.option_id} not found")
    
    try:
        # Create Layout object for exporter
        layout_obj = _create_layout_from_option(option, session)
        
        # Generate DXF to bytes
        dxf_bytes = _export_layout_to_bytes(layout_obj, option)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"option_{request.option_id}_{timestamp}.dxf"
        
        return StreamingResponse(
            io.BytesIO(dxf_bytes),
            media_type="application/x-autocad-dxf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


@app.post("/api/export-all-dxf")
async def export_all_dxf(session_id: str = Form(...)):
    """
    Export all layout options as ZIP file
    
    Returns ZIP containing 3 DXF files
    """
    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    if not session.layouts:
        raise HTTPException(400, "No layouts generated")
    
    try:
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for option in session.layouts:
                # Create Layout object
                layout_obj = _create_layout_from_option(option, session)
                
                # Generate DXF
                dxf_bytes = _export_layout_to_bytes(layout_obj, option)
                
                # Add to ZIP
                filename = f"option_{option.get('id', 0)}_{option.get('name', 'layout').replace(' ', '_')}.dxf"
                zf.writestr(filename, dxf_bytes)
        
        zip_buffer.seek(0)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"layouts_{timestamp}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session info"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    return session.to_dict()


# === Helper Functions ===

def _create_layout_from_option(option: Dict, session) -> Layout:
    """Convert GA option to Layout object for DXF export"""
    from shapely.geometry import box, Polygon
    
    # Create site boundary
    boundary_poly = Polygon(session.boundary_coords)
    site = SiteBoundary(
        geometry=boundary_poly,
        area_sqm=boundary_poly.area
    )
    site.buildable_area_sqm = boundary_poly.buffer(-50).area
    
    # Create layout
    layout = Layout(site_boundary=site)
    
    # Add plots
    plots = []
    for i, plot_data in enumerate(option.get("plots", [])):
        coords = plot_data.get("coords", [])
        if coords:
            plot_geom = Polygon(coords)
        else:
            plot_geom = box(
                plot_data["x"],
                plot_data["y"],
                plot_data["x"] + plot_data["width"],
                plot_data["y"] + plot_data["height"]
            )
        
        plot = Plot(
            id=f"P{i+1}",
            geometry=plot_geom,
            area_sqm=plot_data.get("area", plot_geom.area),
            type=PlotType.INDUSTRIAL,
            width_m=plot_data.get("width", 50),
            depth_m=plot_data.get("height", 50)
        )
        plots.append(plot)
    
    layout.plots = plots
    
    # Set metrics
    metrics = option.get("metrics", {})
    layout.metrics = LayoutMetrics(
        total_area_sqm=site.area_sqm,
        sellable_area_sqm=metrics.get("total_area", 0),
        green_space_area_sqm=0,
        road_area_sqm=0,
        num_plots=metrics.get("total_plots", len(plots)),
        is_compliant=True
    )
    layout.metrics.sellable_ratio = layout.metrics.sellable_area_sqm / layout.metrics.total_area_sqm if layout.metrics.total_area_sqm > 0 else 0
    
    return layout


def _export_layout_to_bytes(layout: Layout, option: Dict) -> bytes:
    """Export layout to DXF bytes"""
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    
    # Create DXF document
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    
    # Setup layers
    layers = {
        'BOUNDARY': {'color': 7},      # White
        'SETBACK': {'color': 1},       # Red
        'PLOTS': {'color': 5},         # Blue
        'LABELS': {'color': 7},        # White
        'ANNOTATIONS': {'color': 2},   # Yellow
        'TITLEBLOCK': {'color': 7}     # White
    }
    
    for name, props in layers.items():
        doc.layers.add(name, color=props['color'])
    
    # Draw boundary
    if layout.site_boundary and layout.site_boundary.geometry:
        coords = list(layout.site_boundary.geometry.exterior.coords)
        msp.add_lwpolyline(coords, dxfattribs={'layer': 'BOUNDARY', 'closed': True})
        
        # Draw setback zone
        setback = layout.site_boundary.geometry.buffer(-50)
        if not setback.is_empty:
            setback_coords = list(setback.exterior.coords)
            msp.add_lwpolyline(setback_coords, dxfattribs={'layer': 'SETBACK', 'closed': True})
    
    # Draw plots
    for plot in layout.plots:
        if plot.geometry:
            coords = list(plot.geometry.exterior.coords)
            msp.add_lwpolyline(coords, dxfattribs={'layer': 'PLOTS', 'closed': True})
            
            # Add label
            centroid = plot.geometry.centroid
            msp.add_text(
                plot.id,
                dxfattribs={
                    'layer': 'LABELS',
                    'height': 5,
                    'insert': (centroid.x, centroid.y)
                }
            )
            
            # Add area annotation
            msp.add_text(
                f"{plot.area_sqm:.0f}m²",
                dxfattribs={
                    'layer': 'ANNOTATIONS',
                    'height': 3,
                    'insert': (centroid.x, centroid.y - 8)
                }
            )
    
    # Add title block
    if layout.site_boundary:
        bounds = layout.site_boundary.geometry.bounds
        minx, miny = bounds[0], bounds[1]
        
        title_lines = [
            f"AIOptimize™ - {option.get('name', 'Layout')}",
            f"Plots: {option.get('metrics', {}).get('total_plots', 0)}",
            f"Total Area: {option.get('metrics', {}).get('total_area', 0):.0f} m²",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ]
        
        y = miny - 20
        for line in title_lines:
            msp.add_text(
                line,
                dxfattribs={
                    'layer': 'TITLEBLOCK',
                    'height': 4,
                    'insert': (minx, y)
                }
            )
            y -= 8
    
    # Save to bytes
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode('utf-8')


# Run with: uvicorn src.api.mvp_api:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
