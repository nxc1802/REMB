"""
REMB ReAct Agent
Industrial Estate Planning Agent using LangGraph
"""
import os
import logging
from typing import Dict, Any, List, Optional, Annotated, TypedDict
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)


# Import tools
from src.tools import all_tools


# System prompt for the agent
SYSTEM_PROMPT = """You are an AI-powered Industrial Estate Planning Assistant (AIOptimize™).

Your role is to help users design optimal land subdivision layouts for industrial estates. You have access to specialized tools for:

1. **Reading CAD Files** (read_dxf): Parse DXF/DWG files to extract site boundaries
2. **Layout Optimization** (optimize_layout): Generate multiple layout options using genetic algorithms
3. **Land Partitioning** (solve_partitioning): Divide land into plots with roads
4. **Compliance Checking** (check_compliance): Verify layouts meet Vietnamese regulations
5. **Rendering** (render_layout_preview): Generate visual previews
6. **Exporting** (write_dxf): Export layouts to DXF files

## Your Workflow

### Phase 1: Perception
When a user uploads a file or provides geometry, use read_dxf to understand the site.

### Phase 2: Planning
Analyze the user's requirements (target plot size, road width, number of plots).
Plan which tools to use and in what order.

### Phase 3: Execution with Self-Correction
- If a tool returns an error, analyze why and adjust parameters
- For example, if road_width=7.5m fails, try road_width=6.0m
- Keep trying until you find a working solution or exhaust options
- Maximum 3 retry attempts per operation

### Phase 4: Synthesis
Summarize results clearly, including:
- Number of plots created
- Total sellable area
- Any adjustments you made
- Compliance status

## Important Guidelines

1. **Always validate geometry** before optimization
2. **Explain adjustments** when you modify user parameters
3. **Check compliance** after generating layouts
4. **Provide metrics** (area, efficiency, FAR)
5. **Be proactive** - if something might not work, suggest alternatives

## Vietnamese Regulations (Reference)
- Minimum setback: 50m from boundary
- Minimum road width: 6m (internal), 7.5m (recommended)
- Minimum green space: 15%
- Maximum FAR: 0.7 (70%)
- Fire spacing: 30m between plots

Communicate clearly in the language the user uses. Be concise but thorough.
"""


class REMBAgent:
    """
    ReAct Agent for Industrial Estate Planning
    Uses LangGraph for stateful tool execution with self-correction
    """
    
    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.3,
        max_iterations: int = 15
    ):
        """
        Initialize the REMB Agent
        
        Args:
            model_name: Gemini model to use
            temperature: LLM temperature (lower = more focused)
            max_iterations: Maximum tool call iterations
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_iterations = max_iterations
        
        # Initialize LLM
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            api_key=api_key,
            convert_system_message_to_human=True
        )
        
        # Initialize memory (for conversation history)
        self.memory = MemorySaver()
        
        # Create ReAct agent with tools
        self.agent = create_react_agent(
            model=self.llm,
            tools=all_tools,
            prompt=SYSTEM_PROMPT,
            checkpointer=self.memory
        )
        
        logger.info(f"REMB Agent initialized with {len(all_tools)} tools")
    
    def invoke(
        self,
        user_input: str,
        session_id: str = "default",
        file_path: Optional[str] = None,
        boundary_coords: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request through the agent
        
        Args:
            user_input: User's message
            session_id: Session ID for memory
            file_path: Optional path to uploaded file
            boundary_coords: Optional pre-loaded boundary
            
        Returns:
            Agent response with results
        """
        # Build context
        context_parts = []
        
        if file_path:
            context_parts.append(f"[File uploaded: {file_path}]")
        
        if boundary_coords:
            from shapely.geometry import Polygon
            poly = Polygon(boundary_coords)
            context_parts.append(
                f"[Site loaded: {poly.area:.0f}m² area, {len(boundary_coords)-1} vertices]"
            )
        
        # Combine with user input
        full_message = "\n".join(context_parts + [user_input]) if context_parts else user_input
        
        # Create input state
        input_state = {
            "messages": [HumanMessage(content=full_message)]
        }
        
        # Config with session thread
        config = {"configurable": {"thread_id": session_id}}
        
        try:
            # Invoke agent
            result = self.agent.invoke(input_state, config=config)
            
            # Extract response
            messages = result.get("messages", [])
            
            # Get the last AI message
            ai_messages = [m for m in messages if isinstance(m, AIMessage)]
            
            if ai_messages:
                content = ai_messages[-1].content
                # Handle both string and list content formats
                if isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    response_text = "\n".join(text_parts)
                else:
                    response_text = content
            else:
                response_text = "No response generated"
            
            # Extract tool calls for transparency
            tool_calls = []
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_calls.extend(msg.tool_calls)
            
            return {
                "status": "success",
                "response": response_text,
                "tool_calls": [
                    {"name": tc.get("name"), "id": tc.get("id")}
                    for tc in tool_calls
                ],
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "session_id": session_id
            }
    
    async def astream(
        self,
        user_input: str,
        session_id: str = "default"
    ):
        """
        Stream agent responses for real-time updates
        
        Args:
            user_input: User's message
            session_id: Session ID
            
        Yields:
            Streaming events
        """
        input_state = {
            "messages": [HumanMessage(content=user_input)]
        }
        config = {"configurable": {"thread_id": session_id}}
        
        async for event in self.agent.astream_events(input_state, config=config, version="v2"):
            yield event


# Singleton instance
_agent_instance: Optional[REMBAgent] = None


def get_agent() -> REMBAgent:
    """Get or create agent singleton"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = REMBAgent()
    return _agent_instance
