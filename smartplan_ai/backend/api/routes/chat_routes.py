"""Chat API routes for LLM interaction."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from shapely.geometry import shape

from core.llm import DesignAgent

logger = logging.getLogger(__name__)
router = APIRouter()

# Reuse agents from design_routes
from api.routes.design_routes import get_agent


class ChatInput(BaseModel):
    """Chat message input."""
    message: str = Field(..., description="User message in Vietnamese")
    session_id: str = Field(default="default")
    boundary: Optional[dict] = Field(default=None, description="Optional boundary GeoJSON")
    selected_element: Optional[dict] = Field(default=None, description="Currently selected element {name, type, index}")


class ChatResponse(BaseModel):
    """Chat response."""
    text: str
    action: Optional[dict] = None
    action_result: Optional[dict] = None
    state: dict
    success: bool = True


@router.post("/chat", response_model=ChatResponse)
async def chat(input: ChatInput):
    """Send message to design agent.
    
    The agent will interpret the message and execute design commands.
    
    Examples:
    - "Tạo lưới đường bàn cờ 100m"
    - "Xoay 15 độ"
    - "Chia lô 2000m²"
    - "Áp dụng template vành đai"
    """
    try:
        agent = get_agent(input.session_id)
        
        # Set boundary if provided
        if input.boundary:
            try:
                boundary = shape(input.boundary)
                agent.set_boundary(boundary)
            except Exception as e:
                logger.warning(f"Invalid boundary: {e}")
        
        # Process message with selected element context
        response = agent.chat(input.message, selected_element=input.selected_element)
        
        return ChatResponse(
            text=response["text"],
            action=response.get("action"),
            action_result=response.get("action_result"),
            state=response["state"],
            success=True
        )
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return ChatResponse(
            text=f"Xin lỗi, có lỗi xảy ra: {str(e)}",
            state={},
            success=False
        )


@router.get("/history")
async def get_chat_history(session_id: str = "default"):
    """Get conversation history for session."""
    agent = get_agent(session_id)
    return {
        "success": True,
        "history": agent.conversation_history
    }


@router.delete("/history")
async def clear_chat_history(session_id: str = "default"):
    """Clear conversation history."""
    agent = get_agent(session_id)
    agent.conversation_history = []
    return {"success": True, "message": "History cleared"}
