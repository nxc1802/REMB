"""Design API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from shapely.geometry import shape, mapping

from core.templates import get_template, list_templates, TemplateParams
from core.llm import DesignAgent

logger = logging.getLogger(__name__)
router = APIRouter()

# Global agent instance (per-session in production)
_agents = {}


def get_agent(session_id: str = "default") -> DesignAgent:
    """Get or create agent for session."""
    if session_id not in _agents:
        _agents[session_id] = DesignAgent()
    return _agents[session_id]


# === Schemas ===

class BoundaryInput(BaseModel):
    """Site boundary input."""
    boundary: dict = Field(..., description="GeoJSON Polygon")
    session_id: str = Field(default="default")


class TemplateInput(BaseModel):
    """Template application input."""
    template_name: str = Field(..., description="Template name: spine/grid/loop/cross")
    cell_size: float = Field(default=100.0, ge=50, le=500)
    rotation: float = Field(default=0.0, ge=-180, le=180)
    session_id: str = Field(default="default")


class SubdivisionInput(BaseModel):
    """Subdivision input."""
    lot_size: float = Field(default=2000.0, ge=500, le=50000)
    session_id: str = Field(default="default")


# === Endpoints ===

@router.get("/templates")
async def get_templates():
    """List available road templates."""
    return {
        "success": True,
        "templates": list_templates()
    }


@router.post("/set-boundary")
async def set_boundary(input: BoundaryInput):
    """Set site boundary for design session."""
    try:
        # Parse GeoJSON to Shapely
        boundary = shape(input.boundary)
        
        if not boundary.is_valid:
            boundary = boundary.buffer(0)
            
        if boundary.is_empty:
            raise HTTPException(400, "Invalid boundary geometry")
            
        # Set in agent
        agent = get_agent(input.session_id)
        result = agent.set_boundary(boundary)
        
        return {
            "success": True,
            **result,
            "boundary": mapping(boundary)
        }
        
    except Exception as e:
        logger.error(f"Set boundary failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/apply-template")
async def apply_template(input: TemplateInput):
    """Apply a road template to the current boundary."""
    try:
        agent = get_agent(input.session_id)
        
        if not agent.tools.state.boundary:
            raise HTTPException(400, "No boundary set. Call /set-boundary first.")
            
        result = agent.tools.apply_template(
            input.template_name,
            input.cell_size,
            input.rotation
        )
        
        if not result["success"]:
            raise HTTPException(400, result["message"])
            
        return {
            **result,
            "state": agent.get_state()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Apply template failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/rotate")
async def rotate_roads(angle: float = 15.0, session_id: str = "default"):
    """Rotate road network by angle (degrees)."""
    try:
        agent = get_agent(session_id)
        result = agent.tools.rotate_roads(angle)
        
        if not result["success"]:
            raise HTTPException(400, result["message"])
            
        return {
            **result,
            "state": agent.get_state()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rotate failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/subdivide")
async def subdivide_blocks(input: SubdivisionInput):
    """Subdivide blocks into lots."""
    try:
        agent = get_agent(input.session_id)
        result = agent.tools.subdivide_blocks(input.lot_size)
        
        if not result["success"]:
            raise HTTPException(400, result["message"])
            
        return {
            **result,
            "state": agent.get_state()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subdivide failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/state")
async def get_state(session_id: str = "default"):
    """Get current design state as GeoJSON."""
    agent = get_agent(session_id)
    return {
        "success": True,
        "state": agent.get_state(),
        "stats": agent.get_stats()
    }


@router.get("/stats")
async def get_stats(session_id: str = "default"):
    """Get design statistics."""
    agent = get_agent(session_id)
    return agent.get_stats()


@router.post("/reset")
async def reset_session(session_id: str = "default"):
    """Reset design session."""
    if session_id in _agents:
        del _agents[session_id]
    return {"success": True, "message": "Session reset"}
