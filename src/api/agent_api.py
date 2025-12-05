"""
Agent API Endpoints
New FastAPI router for Agent-based interactions
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentChatRequest(BaseModel):
    """Request model for agent chat"""
    session_id: str
    message: str
    file_path: Optional[str] = None
    boundary_coords: Optional[List[List[float]]] = None


class AgentChatResponse(BaseModel):
    """Response model for agent chat"""
    status: str
    response: str
    tool_calls: List[Dict[str, Any]] = []
    session_id: str


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Chat with the REMB Agent
    
    The agent can:
    - Read and parse DXF files
    - Generate optimized layouts
    - Check regulatory compliance
    - Export results to DXF
    - Self-correct on errors
    """
    try:
        from src.agent import get_agent
        
        agent = get_agent()
        result = agent.invoke(
            user_input=request.message,
            session_id=request.session_id,
            file_path=request.file_path,
            boundary_coords=request.boundary_coords
        )
        
        return AgentChatResponse(**result)
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Agent chat error: {e}")
        raise HTTPException(500, f"Agent error: {str(e)}")


@router.post("/process-file")
async def agent_process_file(
    file: UploadFile = File(...),
    message: str = Form(default="Analyze this site and suggest optimal layouts"),
    session_id: str = Form(default="default")
):
    """
    Upload a CAD file and process with the agent
    
    The agent will:
    1. Parse the file
    2. Analyze the site
    3. Generate layout options
    4. Check compliance
    5. Return comprehensive results
    """
    if not file.filename:
        raise HTTPException(400, "No file provided")
    
    # Save uploaded file
    try:
        content = await file.read()
        suffix = ".dwg" if file.filename.lower().endswith(".dwg") else ".dxf"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # Process with agent
        from src.agent import get_agent
        
        agent = get_agent()
        result = agent.invoke(
            user_input=f"[File uploaded: {file.filename}]\n{message}",
            session_id=session_id,
            file_path=tmp_path
        )
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        return {
            "status": result.get("status"),
            "response": result.get("response"),
            "tool_calls": result.get("tool_calls", []),
            "session_id": session_id,
            "file_processed": file.filename
        }
        
    except Exception as e:
        logger.error(f"File processing error: {e}")
        raise HTTPException(500, f"Processing error: {str(e)}")


@router.get("/health")
async def agent_health():
    """Check agent status"""
    try:
        from src.agent import get_agent
        from src.tools import all_tools
        
        agent = get_agent()
        
        return {
            "status": "healthy",
            "agent_type": "ReAct",
            "model": agent.model_name,
            "tools_available": len(all_tools),
            "tool_names": [t.name for t in all_tools]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
