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
    """AI Spatial Planner with multi-provider support.
    
    Supports:
    - MegaLLM (llama3.3-70b-instruct) - OpenAI-compatible API
    - Google Gemini 2.5 Flash - Native Google API
    """
    
    # Provider configurations
    PROVIDERS = {
        "megallm": {
            "base_url": "https://ai.megallm.io/v1",
            "models": [
                "llama3.3-70b-instruct",
                "deepseek-v3",
                "deepseek-r1-distill-llama-70b",
                "deepseek-ai/deepseek-v3.1-terminus",
                "deepseek-ai/deepseek-v3.1",
                "qwen3-coder-480b-a35b-instruct"
            ],
            "api_key_env": "MEGALLM_API_KEY",
        },
        "gemini": {
            "models": ["gemini-2.5-flash", "gemini-2.0-flash"],
            "api_key_env": "GOOGLE_API_KEY",
        }
    }
    
    DEFAULT_PROVIDER = "megallm"
    DEFAULT_MODEL = "llama3.3-70b-instruct"
    
    def __init__(
        self, 
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """Initialize agent.
        
        Args:
            provider: Provider name (megallm, gemini)
            model: Model name
            api_key: API key (or from env)
        """
        self.provider = provider or os.environ.get("LLM_PROVIDER", self.DEFAULT_PROVIDER)
        self.model_name = model or os.environ.get("LLM_MODEL", self.DEFAULT_MODEL)
        
        # Get API key based on provider
        provider_config = self.PROVIDERS.get(self.provider, {})
        key_env = provider_config.get("api_key_env", "")
        self.api_key = api_key or os.environ.get(key_env)
        self.base_url = provider_config.get("base_url")
        
        self._openai_client = None
        self._gemini_model = None
        
        if not self.api_key:
            logger.warning(f"No API key found for {self.provider} - will use mock responses")
    
    def set_model(self, provider: str, model: str):
        """Switch to a different model/provider.
        
        Args:
            provider: Provider name
            model: Model name
        """
        self.provider = provider
        self.model_name = model
        provider_config = self.PROVIDERS.get(provider, {})
        key_env = provider_config.get("api_key_env", "")
        self.api_key = os.environ.get(key_env)
        self.base_url = provider_config.get("base_url")
        self._openai_client = None
        self._gemini_model = None
        logger.info(f"Switched to {provider}/{model}")
    
    @property
    def openai_client(self):
        """Lazy load OpenAI client for MegaLLM."""
        if self._openai_client is None and self.api_key and self.provider == "megallm":
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info(f"MegaLLM client initialized (model: {self.model_name})")
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize MegaLLM client: {e}")
        return self._openai_client
    
    @property
    def gemini_model(self):
        """Lazy load Google Gemini model."""
        if self._gemini_model is None and self.api_key and self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._gemini_model = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini model initialized: {self.model_name}")
            except ImportError:
                logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        return self._gemini_model
    
    @property
    def client(self):
        """Get current client based on provider (for backward compat)."""
        if self.provider == "gemini":
            return self.gemini_model
        return self.openai_client
    
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
        
        # Log input prompt
        logger.info("=" * 80)
        logger.info("🔵 LLM INPUT - SYSTEM PROMPT:")
        logger.info(SYSTEM_PROMPT[:500] + "..." if len(SYSTEM_PROMPT) > 500 else SYSTEM_PROMPT)
        logger.info("-" * 80)
        logger.info("🔵 LLM INPUT - CONTEXT:")
        logger.info(context)
        logger.info("=" * 80)
        
        # Use mock if no client
        if not self.client:
            logger.info("Using mock response (no API key)")
            return self._mock_generate(boundary_coords, user_request)
        
        try:
            # Get generation config
            gen_config = get_generation_config()
            
            logger.info(f"🚀 Calling {self.provider}/{self.model_name}...")
            
            # Choose API based on provider
            if self.provider == "gemini":
                # Use Google Gemini native API
                full_prompt = f"{SYSTEM_PROMPT}\n\n{context}"
                response = self.gemini_model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": gen_config.get("temperature", 0.2),
                        "max_output_tokens": gen_config.get("max_output_tokens", 4096),
                    }
                )
                raw_text = response.text
            else:
                # Use OpenAI-compatible API (MegaLLM)
                response = self.openai_client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context}
                    ],
                    temperature=gen_config.get("temperature", 0.2),
                    max_tokens=gen_config.get("max_output_tokens", 4096),
                )
                raw_text = response.choices[0].message.content
            
            # Log output response
            logger.info("=" * 80)
            logger.info("🟢 LLM OUTPUT - RAW RESPONSE:")
            logger.info(raw_text)
            logger.info("=" * 80)
            
            # Parse JSON from response
            result = self._parse_response(raw_text)
            result.raw_response = raw_text
            
            # Log parsed result
            if result.success:
                logger.info(f"✅ Parsed successfully: action={result.action}, assets={len(result.new_assets)}")
                for i, asset in enumerate(result.new_assets):
                    logger.info(f"   Asset #{i}: type={asset.get('type')}, polygon has {len(asset.get('polygon', []))} points")
            else:
                logger.warning(f"❌ Parse failed: {result.error}")
            
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
            
            # Repair common JSON errors from LLMs
            json_str = self._repair_json(json_str)
            
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
    
    def _repair_json(self, json_str: str) -> str:
        """Repair common JSON errors from LLMs.
        
        Fixes:
        - Missing ] before } in arrays
        - Missing ] before , in arrays
        - Unbalanced brackets
        """
        import re
        
        # Fix pattern: ]], } should sometimes be ]]} 
        # Fix pattern: ]} should be ]]}
        # The issue: polygon ends with ]] but LLM outputs ] only
        
        # Count brackets to check balance
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        if open_brackets > close_brackets:
            # Add missing closing brackets
            diff = open_brackets - close_brackets
            # Find position before closing brace of polygon objects
            # Pattern: ]}, should be ]]},
            json_str = re.sub(r'\]\s*\}', ']]}'   , json_str)
            json_str = re.sub(r'\]\s*,\s*\{', ']],{', json_str)
            
            # Recount
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')
            diff = open_brackets - close_brackets
            
            if diff > 0:
                # Add at the end before final }
                last_brace = json_str.rfind('}')
                if last_brace > 0:
                    json_str = json_str[:last_brace] + ']' * diff + json_str[last_brace:]
        
        return json_str
    
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
