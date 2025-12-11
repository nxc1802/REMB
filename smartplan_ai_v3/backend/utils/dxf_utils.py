"""DXF file parsing utilities with robust handling."""

import logging
import tempfile
import os
import io
from typing import Tuple, List, Optional
from shapely.geometry import Polygon, LineString
from shapely.ops import polygonize

logger = logging.getLogger(__name__)


def load_dxf_content(dxf_content: bytes) -> Tuple[Optional[Polygon], List[LineString]]:
    """Load DXF content and extract boundary and roads.
    
    Robust parsing that handles:
    - Multiple encodings (utf-8, latin-1, cp1252)
    - Various entity types (LWPOLYLINE, POLYLINE, LINE)
    - Tempfile vs Stream loading
    
    Args:
        dxf_content: Raw bytes of DXF file
        
    Returns:
        Tuple of (boundary Polygon, list of road LineStrings)
    """
    try:
        import ezdxf
    except ImportError:
        logger.error("ezdxf not installed")
        return None, []
    
    doc = None
    tmp_path = None
    
    # 1. Try tempfile method (most reliable)
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.dxf', delete=False) as tmp:
            tmp.write(dxf_content)
            tmp_path = tmp.name
        
        doc = ezdxf.readfile(tmp_path)
        logger.info("Loaded DXF via tempfile")
    except Exception as e:
        logger.warning(f"Tempfile load failed: {e}. Trying streams...")
        
        # 2. Try text stream with encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
        for encoding in encodings:
            try:
                text_content = dxf_content.decode(encoding)
                doc = ezdxf.read(io.StringIO(text_content))
                logger.info(f"Loaded DXF via stream ({encoding})")
                break
            except Exception:
                continue
                
        # 3. Try binary stream
        if doc is None:
            try:
                doc = ezdxf.read(io.BytesIO(dxf_content))
                logger.info("Loaded DXF via binary stream")
            except Exception as final_e:
                logger.error(f"All load methods failed: {final_e}")
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                return None, []

    # Cleanup temp file
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except:
            pass
            
    if not doc:
        return None, []

    # Parse entities
    msp = doc.modelspace()
    polygons = []
    lines = []
    
    # helper to convert points 
    to_2d = lambda pts: [(p[0], p[1]) for p in pts]

    # 1. Process LWPOLYLINE
    for entity in msp.query('LWPOLYLINE'):
        try:
            pts = list(entity.get_points(format='xy'))
            if entity.is_closed:
                if len(pts) >= 3:
                    polygons.append(Polygon(pts))
            else:
                if len(pts) >= 2:
                    lines.append(LineString(pts))
        except Exception:
            continue
            
    # 2. Process POLYLINE (legacy)
    for entity in msp.query('POLYLINE'):
        try:
            pts = list(entity.get_points())
            coords = to_2d(pts)
            if entity.is_closed:
                if len(coords) >= 3:
                    polygons.append(Polygon(coords))
            else:
                if len(coords) >= 2:
                    lines.append(LineString(coords))
        except Exception:
            continue
            
    # 3. Process LINE
    for entity in msp.query('LINE'):
        try:
            start = entity.dxf.start
            end = entity.dxf.end
            lines.append(LineString([(start.x, start.y), (end.x, end.y)]))
        except Exception:
            continue

    # Identify Boundary (Largest closed polygon)
    boundary = None
    max_area = 0.0
    
    # Check explicitly closed polygons
    for poly in polygons:
        if poly.is_valid and poly.area > max_area:
            max_area = poly.area
            boundary = poly
            
    # If no boundary found, try to polygonize lines matching the boundary criteria
    if not boundary and lines:
        try:
            potential_polys = list(polygonize(lines))
            for poly in potential_polys:
                if poly.is_valid and poly.area > max_area:
                    max_area = poly.area
                    boundary = poly
        except Exception as e:
            logger.warning(f"Polygonize failed: {e}")

    # Roads are lines that correspond to potential roads
    # If boundary was found, we exclude it from lines (if it was derived from lines)
    # But for simplicity, we treat all non-boundary lines/open-polylines as potential roads
    
    logger.info(f"DXF Extraction: Boundary={'Found' if boundary else 'Missing'} ({max_area:.1f}m²), Roads={len(lines)}")
    
    return boundary, lines
