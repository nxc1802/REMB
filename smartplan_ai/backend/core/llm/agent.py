"""Design Agent using Google Gemini 2.5 Flash."""

import os
import re
import json
import logging
from typing import Optional, Dict, Any

from .prompts import SYSTEM_PROMPT, get_context_prompt
from .tools import DesignTools, DesignState

logger = logging.getLogger(__name__)


class DesignAgent:
    """LLM-powered design assistant using Gemini 2.5 Flash.
    
    Handles conversation with user, interprets commands,
    and executes design tools.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        state: Optional[DesignState] = None
    ):
        """Initialize agent.
        
        Args:
            api_key: Google API key (or from GOOGLE_API_KEY env)
            state: Initial design state
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.tools = DesignTools(state)
        self.conversation_history = []
        self._model = None
        
    @property
    def model(self):
        """Lazy load Gemini model."""
        if self._model is None:
            try:
                import google.generativeai as genai
                
                if not self.api_key:
                    logger.warning("No GOOGLE_API_KEY found, using mock mode")
                    return None
                    
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("Gemini model initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                return None
                
        return self._model
    
    def set_boundary(self, boundary) -> dict:
        """Set site boundary.
        
        Args:
            boundary: Shapely Polygon
            
        Returns:
            Result dict
        """
        return self.tools.set_boundary(boundary)
    
    def chat(self, message: str, selected_element: dict = None) -> dict:
        """Process user message and return response.
        
        Args:
            message: User message in Vietnamese
            selected_element: Currently selected element from UI (name, type, index)
            
        Returns:
            Response dict with text and optional action result
        """
        # Update selected element in state
        if selected_element:
            self.tools.state.selected_element = selected_element
        
        # Build context with full info
        context = ""
        if self.tools.state.boundary:
            # Get element summary
            element_summary = self.tools.state.get_element_summary()
            
            # Get current config
            config = {
                'main_road_width': self.tools.state.main_road_width,
                'secondary_road_width': self.tools.state.secondary_road_width,
                'cell_size': self.tools.state.cell_size,
                'rotation': self.tools.state.rotation
            }
            
            context = get_context_prompt(
                boundary_area=self.tools.state.boundary.area,
                current_template=self.tools.state.template_name,
                element_summary=element_summary,
                config=config,
                selected_element=self.tools.state.selected_element,
                conversation_history=self.conversation_history
            )
            
        # Build full prompt
        full_prompt = f"{SYSTEM_PROMPT}\n{context}\n\nUser: {message}"
        
        # Get LLM response
        try:
            if self.model:
                response = self.model.generate_content(full_prompt)
                response_text = response.text
                logger.info(f"Gemini response received ({len(response_text)} chars)")
            else:
                # Mock mode - simple pattern matching
                response_text = self._mock_response(message)
                logger.info("Using mock response")
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            response_text = self._mock_response(message)
            logger.info("Fallback to mock response due to API error")
        
        # Log raw response for debugging
        logger.debug(f"Raw response:\n{response_text[:500]}...")
            
        # Parse response for actions
        action_result = None
        action_data = self._extract_action(response_text)
        
        if action_data:
            logger.info(f"Action extracted: {action_data['action']} with params: {action_data.get('params', {})}")
            action_result = self.tools.execute_action(
                action_data["action"],
                action_data.get("params", {})
            )
            logger.info(f"Action result: {action_result.get('success')} - {action_result.get('message', 'N/A')}")
        else:
            logger.warning(f"No action found in response. Response preview: {response_text[:200]}...")
            
        # Clean response text (remove JSON block for display)
        display_text = self._clean_response(response_text)
        
        # Store in history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        self.conversation_history.append({
            "role": "assistant", 
            "content": display_text
        })
        
        return {
            "text": display_text,
            "action": action_data,
            "action_result": action_result,
            "state": self.tools.state.to_geojson()
        }
    
    def _extract_action(self, text: str) -> Optional[dict]:
        """Extract JSON action from response text."""
        # Look for JSON block
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass
                
        # Also try without code block
        json_pattern2 = r'\{["\']action["\']:\s*["\'](\w+)["\'].*?\}'
        matches2 = re.findall(json_pattern2, text, re.DOTALL)
        
        if matches2:
            try:
                # Find full JSON object
                start = text.find('{"action"')
                if start == -1:
                    start = text.find("{'action")
                if start != -1:
                    # Find matching closing brace
                    depth = 0
                    for i, c in enumerate(text[start:]):
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                json_str = text[start:start+i+1]
                                return json.loads(json_str.replace("'", '"'))
            except:
                pass
                
        return None
    
    def _clean_response(self, text: str) -> str:
        """Remove JSON blocks from response for display."""
        # Remove JSON code blocks
        text = re.sub(r'```json\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
        # Remove trailing whitespace
        return text.strip()
    
    def _mock_response(self, message: str) -> str:
        """Generate mock response when API is not available."""
        message_lower = message.lower()
        
        # ===== PRIORITY 1: Modification commands (check BEFORE template selection) =====
        
        # Road width - check first because "trục rộng hơn" should not trigger spine template
        if "rộng" in message_lower and any(kw in message_lower for kw in ["đường", "road", "trục", "chính"]):
            # Extract width if specified
            width_match = re.search(r'(\d+)\s*(?:m|mét|meter)', message)
            if width_match:
                width = int(width_match.group(1))
            elif "gấp đôi" in message_lower or "gấp 2" in message_lower:
                width = 48  # Double default 24
            elif "rộng hơn" in message_lower or "tăng" in message_lower:
                width = 30  # Increase from default 24
            else:
                width = 24
            return f'''Đã đổi bề rộng đường chính thành {width}m.
```json
{{"action": "set_road_width", "params": {{"main_width": {width}}}}}
```'''
        
        # To/nhỏ - scale width/size
        elif ("to hơn" in message_lower or "lớn hơn" in message_lower) and any(kw in message_lower for kw in ["đường", "trục"]):
            return '''Đã đổi bề rộng đường chính thành 36m.
```json
{"action": "set_road_width", "params": {"main_width": 36}}
```'''
        
        # ===== PRIORITY 2: Template selection =====
        
        # Only match template if clearly asking to create/apply template
        elif "bàn cờ" in message_lower or "grid" in message_lower:
            return '''Tôi sẽ áp dụng template bàn cờ với lưới 100m.
```json
{"action": "apply_template", "params": {"template_name": "grid", "cell_size": 100}}
```'''
            
        elif ("áp dụng" in message_lower or "tạo" in message_lower or "dùng" in message_lower) and "trục" in message_lower:
            return '''Tôi sẽ áp dụng template trục trung tâm.
```json
{"action": "apply_template", "params": {"template_name": "spine", "cell_size": 100}}
```'''
            
        elif "spine" in message_lower or "xương cá" in message_lower:
            return '''Tôi sẽ áp dụng template trục trung tâm.
```json
{"action": "apply_template", "params": {"template_name": "spine", "cell_size": 100}}
```'''
            
        elif "vành đai" in message_lower or "loop" in message_lower or "vòng" in message_lower:
            return '''Tôi sẽ áp dụng template vành đai.
```json
{"action": "apply_template", "params": {"template_name": "loop"}}
```'''
            
        elif "chữ thập" in message_lower or "cross" in message_lower:
            return '''Tôi sẽ áp dụng template chữ thập.
```json
{"action": "apply_template", "params": {"template_name": "cross"}}
```'''
        
        # ===== PRIORITY 3: Other modifications =====
            
        # Rotation
        elif "xoay" in message_lower:
            # Extract angle
            angle_match = re.search(r'(\d+)\s*(?:độ|degree|°)', message)
            angle = int(angle_match.group(1)) if angle_match else 15
            return f'''Đã xoay lưới đường {angle} độ.
```json
{{"action": "rotate_roads", "params": {{"angle": {angle}}}}}
```'''
        
        # Cell size
        elif "ô" in message_lower and ("lớn" in message_lower or "nhỏ" in message_lower or "kích thước" in message_lower):
            size_match = re.search(r'(\d+)\s*(?:m|mét|meter)', message)
            if size_match:
                size = int(size_match.group(1))
            elif "lớn hơn" in message_lower:
                size = 150
            elif "nhỏ hơn" in message_lower:
                size = 75
            else:
                size = 100
            return f'''Đã đổi kích thước ô thành {size}m. Áp dụng lại template...
```json
{{"action": "apply_template", "params": {{"template_name": "grid", "cell_size": {size}}}}}
```'''
            
        # Subdivision
        elif "chia lô" in message_lower or "subdivide" in message_lower or "lô" in message_lower:
            size_match = re.search(r'(\d+)\s*(?:m²|m2|mét vuông)', message)
            lot_size = int(size_match.group(1)) if size_match else 2000
            return f'''Tôi sẽ chia lô tự động với kích thước {lot_size}m².
```json
{{"action": "subdivide_blocks", "params": {{"lot_size": {lot_size}}}}}
```'''
        
        # Remove road
        elif "xóa" in message_lower and "đường" in message_lower:
            index_match = re.search(r'(?:đường\s*(?:số|thứ)?\s*)?(\d+)', message)
            index = int(index_match.group(1)) - 1 if index_match else 0  # Convert to 0-indexed
            return f'''Đã xóa đường số {index + 1}.
```json
{{"action": "remove_road", "params": {{"index": {index}}}}}
```'''
        
        # Move road
        elif "di chuyển" in message_lower or "dịch" in message_lower:
            dx_match = re.search(r'(\d+)\s*(?:m|mét)', message)
            dx = int(dx_match.group(1)) if dx_match else 50
            if "trái" in message_lower:
                dx = -dx
            if "xuống" in message_lower:
                dy = -dx
                dx = 0
            elif "lên" in message_lower:
                dy = dx
                dx = 0
            else:
                dy = 0
            
            # Check if moving all or specific road
            if "tất cả" in message_lower or "hết" in message_lower:
                return f'''Tôi sẽ di chuyển tất cả đường.
```json
{{"action": "execute_code", "params": {{"code": "from shapely.affinity import translate\\nroads = [translate(r, xoff={dx}, yoff={dy}) for r in roads]\\nresult = f'Đã di chuyển {{len(roads)}} đường'"}}}}
```'''
            else:
                return f'''Đã di chuyển đường với offset ({dx}, {dy}).
```json
{{"action": "move_road", "params": {{"index": 0, "dx": {dx}, "dy": {dy}}}}}
```'''
        
        # Scale
        elif "phóng to" in message_lower or "thu nhỏ" in message_lower or "scale" in message_lower:
            if "phóng to" in message_lower or "gấp" in message_lower:
                factor = 1.5
            elif "thu nhỏ" in message_lower:
                factor = 0.7
            else:
                factor = 1.0
            return f'''Đã scale thiết kế với factor {factor}.
```json
{{"action": "scale_design", "params": {{"factor": {factor}}}}}
```'''
            
        # Stats
        elif "thống kê" in message_lower or "thông tin" in message_lower or "stats" in message_lower:
            return '''Đây là thống kê hiện tại:
```json
{"action": "get_stats", "params": {}}
```'''
            
        # List templates
        elif "template" in message_lower or "mẫu" in message_lower:
            return '''Có 4 template sẵn sàng:

1. **spine** 🦴 - Trục Trung Tâm: Đường chính với nhánh xương cá
2. **grid** 🔲 - Bàn Cờ: Lưới vuông góc 
3. **loop** ⭕ - Vành Đai: Đường vòng quanh biên
4. **cross** ✚ - Chữ Thập: Hai trục cắt nhau

Bạn muốn dùng template nào?'''
            
        # Default - more helpful
        else:
            return '''Tôi có thể giúp bạn với các lệnh sau:

**Chọn template:**
- "Tạo lưới bàn cờ" hoặc "grid"
- "Trục trung tâm" hoặc "spine"  
- "Vành đai" hoặc "loop"
- "Chữ thập" hoặc "cross"

**Điều chỉnh:**
- "Xoay 15 độ"
- "Làm đường rộng hơn" hoặc "đường rộng 30m"
- "Ô lớn hơn" hoặc "kích thước ô 150m"
- "Di chuyển sang phải 50m"
- "Xóa đường số 3"

**Chia lô:**
- "Chia lô" hoặc "chia lô 3000m²"

**Thống kê:**
- "Thống kê" hoặc "thông tin"

Hãy thử một lệnh!'''
    
    def get_state(self) -> dict:
        """Get current design state as GeoJSON."""
        return self.tools.state.to_geojson()
    
    def get_stats(self) -> dict:
        """Get current design statistics."""
        return self.tools.get_stats()
