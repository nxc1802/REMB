"""Spatial Planner Agent using MegaLLM (Gemini 2.5 Flash).

Handles asset generation based on user requests with validation.
Uses OpenAI-compatible API for MegaLLM integration.
"""

import os
import json
import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .prompts import SYSTEM_PROMPT, build_context_prompt, get_generation_config, ASSET_KEYWORDS

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of asset generation."""
    
    success: bool
    action: str = "add"  # add, clear, replace
    new_assets: List[Dict[str, Any]] = None
    explanation: str = ""
    error: str = None
    raw_response: str = None
    
    def __post_init__(self):
        if self.new_assets is None:
            self.new_assets = []


class SpatialPlannerAgent:
    """AI Spatial Planner using MegaLLM (Gemini 2.5 Flash).
    
    Generates asset placements based on user requests while
    respecting boundary and existing asset constraints.
    
    Uses OpenAI-compatible API with MegaLLM as provider.
    """
    
    # MegaLLM configuration
    MEGALLM_BASE_URL = "https://ai.megallm.io/v1"
    DEFAULT_MODEL = "llama3.3-70b-instruct"
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """Initialize agent.
        
        Args:
            api_key: MegaLLM API key (or from MEGALLM_API_KEY env)
            base_url: API base URL (default: MegaLLM endpoint)
            model: Model name (default: gemini-2.5-flash)
        """
        self.api_key = api_key or os.environ.get("MEGALLM_API_KEY")
        self.base_url = base_url or os.environ.get("MEGALLM_BASE_URL", self.MEGALLM_BASE_URL)
        self.model_name = model or os.environ.get("MEGALLM_MODEL", self.DEFAULT_MODEL)
        self._client = None
        
        if not self.api_key:
            logger.warning("No MEGALLM_API_KEY found - will use mock responses")
    
    @property
    def client(self):
        """Lazy load OpenAI client configured for MegaLLM."""
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info(f"MegaLLM client initialized (model: {self.model_name})")
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to initialize MegaLLM client: {e}")
                self._client = None
        
        return self._client
    
    def generate_assets(
        self,
        boundary_coords: List[List[float]],
        existing_assets: List[Dict[str, Any]],
        user_request: str
    ) -> GenerationResult:
        """Generate new assets based on user request.
        
        Args:
            boundary_coords: Block boundary coordinates
            existing_assets: List of existing asset dicts
            user_request: Natural language request
            
        Returns:
            GenerationResult with new assets or error
        """
        if not boundary_coords:
            return GenerationResult(
                success=False,
                error="Boundary coordinates are required"
            )
        
        # Build context prompt
        context = build_context_prompt(
            boundary_coords=boundary_coords,
            existing_assets=existing_assets,
            user_request=user_request
        )
        
        # Use mock if no client
        if not self.client:
            logger.info("Using mock response (no API key)")
            return self._mock_generate(boundary_coords, user_request)
        
        try:
            # Get generation config
            gen_config = get_generation_config()
            
            # Call MegaLLM via OpenAI-compatible API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                temperature=gen_config.get("temperature", 0.2),
                max_tokens=gen_config.get("max_output_tokens", 4096),
            )
            
            raw_text = response.choices[0].message.content
            
            
            logger.info(f"Raw LLM response: {raw_text}")
            
            # Parse JSON from response
            result = self._parse_response(raw_text)
            result.raw_response = raw_text
            
            return result
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e)
            )
    
    def _parse_response(self, text: str) -> GenerationResult:
        """Parse JSON response from LLM.
        
        Args:
            text: Raw LLM response text
            
        Returns:
            GenerationResult
        """
        try:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return GenerationResult(
                        success=False,
                        error="No JSON found in response"
                    )
            
            data = json.loads(json_str)
            
            action = data.get("action", "add")
            new_assets = data.get("new_assets", [])
            explanation = data.get("explanation", "")
            
            # Validate asset types
            valid_assets = []
            for asset in new_assets:
                asset_type = asset.get("type", "")
                if asset_type in ASSET_KEYWORDS:
                    valid_assets.append(asset)
                else:
                    logger.warning(f"Invalid asset type '{asset_type}' - skipping")
            
            return GenerationResult(
                success=True,
                action=action,
                new_assets=valid_assets,
                explanation=explanation
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return GenerationResult(
                success=False,
                error=f"Invalid JSON: {e}"
            )
    
    def _mock_generate(
        self,
        boundary_coords: List[List[float]],
        user_request: str
    ) -> GenerationResult:
        """Generate mock response when API is not available.
        
        Creates simple rectangular assets within boundary.
        """
        if not boundary_coords:
            return GenerationResult(success=False, error="No boundary")
        
        # Calculate boundary extents
        xs = [c[0] for c in boundary_coords]
        ys = [c[1] for c in boundary_coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Determine asset type from request
        request_lower = user_request.lower()
        if "kho" in request_lower or "warehouse" in request_lower:
            asset_type = "warehouse_cold"
        elif "văn phòng" in request_lower or "office" in request_lower:
            asset_type = "office_hq"
        elif "nhà máy" in request_lower or "factory" in request_lower:
            asset_type = "factory_standard"
        elif "bãi xe" in request_lower or "parking" in request_lower:
            asset_type = "parking_lot"
        elif "cây xanh" in request_lower or "green" in request_lower:
            asset_type = "green_buffer"
        else:
            asset_type = "factory_standard"
        
        # Create a simple rectangular asset
        margin = 10
        width = (max_x - min_x) * 0.3
        height = (max_y - min_y) * 0.3
        
        x1 = min_x + margin
        y1 = min_y + margin
        x2 = x1 + width
        y2 = y1 + height
        
        new_assets = [{
            "type": asset_type,
            "polygon": [[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]
        }]
        
        return GenerationResult(
            success=True,
            new_assets=new_assets,
            explanation=f"[MOCK] Đã tạo 1 {asset_type} trong khu đất"
        )
    
    def regenerate_with_constraints(
        self,
        boundary_coords: List[List[float]],
        existing_assets: List[Dict[str, Any]],
        user_request: str,
        failed_assets: List[Dict[str, Any]],
        errors: List[str]
    ) -> GenerationResult:
        """Regenerate assets after validation failure.
        
        Provides additional context about what went wrong.
        
        Args:
            boundary_coords: Block boundary
            existing_assets: Existing assets
            user_request: Original request
            failed_assets: Assets that failed validation
            errors: Error messages from validation
            
        Returns:
            GenerationResult with corrected assets
        """
        # Build enhanced prompt with error feedback
        enhanced_request = f"""
{user_request}

⚠️ LẦN TẠO TRƯỚC ĐÃ THẤT BẠI VỚI CÁC LỖI SAU:
{chr(10).join(f'- {e}' for e in errors)}

Hãy tạo lại assets, đảm bảo:
1. Không đè lên existing_assets
2. Nằm hoàn toàn trong boundary
3. Giữ khoảng cách an toàn với các vật thể khác
"""
        
        return self.generate_assets(
            boundary_coords=boundary_coords,
            existing_assets=existing_assets,
            user_request=enhanced_request
        )
