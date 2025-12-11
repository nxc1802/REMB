"""Sandboxed Code Executor for SmartPlan AI.

Allows LLM to execute custom geometry operations safely.
Only whitelisted modules and functions are allowed.
"""

import ast
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, mapping
from shapely.ops import unary_union, split
from shapely.affinity import rotate, translate, scale

logger = logging.getLogger(__name__)

# Whitelisted modules and their allowed functions
ALLOWED_BUILTINS = {
    'len', 'range', 'enumerate', 'zip', 'map', 'filter', 'list', 'dict', 
    'tuple', 'set', 'int', 'float', 'str', 'bool', 'abs', 'min', 'max',
    'sum', 'sorted', 'round', 'print', 'True', 'False', 'None'
}

# Allowed import modules
ALLOWED_IMPORTS = {
    'numpy': np,
    'np': np,
    'shapely': True,
    'shapely.geometry': True,
    'shapely.affinity': True,
    'shapely.ops': True,
}


@dataclass
class ExecutionResult:
    """Result from code execution."""
    success: bool
    output: Any = None
    error: str = None
    logs: List[str] = None
    modified_state: Dict = None


class CodeValidator(ast.NodeVisitor):
    """AST validator to check code safety."""
    
    def __init__(self):
        self.errors = []
        
    def visit_Import(self, node):
        for alias in node.names:
            if alias.name not in ALLOWED_IMPORTS:
                self.errors.append(f"Import '{alias.name}' không được phép")
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module not in ALLOWED_IMPORTS:
            self.errors.append(f"Import từ '{node.module}' không được phép")
        self.generic_visit(node)
        
    def visit_Call(self, node):
        # Check for dangerous function calls
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in ('eval', 'exec', 'compile', '__import__', 'open', 
                        'input', 'globals', 'locals', 'vars', 'dir'):
                self.errors.append(f"Function '{name}' không được phép")
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        # Block dangerous attributes
        if node.attr.startswith('_'):
            self.errors.append(f"Truy cập attribute private '{node.attr}' không được phép")
        self.generic_visit(node)


def validate_code(code: str) -> List[str]:
    """Validate code for safety.
    
    Returns:
        List of error messages (empty if valid)
    """
    try:
        tree = ast.parse(code)
        validator = CodeValidator()
        validator.visit(tree)
        return validator.errors
    except SyntaxError as e:
        return [f"Lỗi cú pháp: {e.msg} (dòng {e.lineno})"]


class SandboxedExecutor:
    """Execute Python code in a sandboxed environment."""
    
    def __init__(self, state_dict: Dict[str, Any] = None):
        """Initialize with design state.
        
        Args:
            state_dict: Current design state with roads, blocks, lots, etc.
        """
        self.state = state_dict or {}
        self.logs = []
        
    def execute(self, code: str) -> ExecutionResult:
        """Execute code safely.
        
        Args:
            code: Python code to execute
            
        Returns:
            ExecutionResult with output or error
        """
        # Validate code
        errors = validate_code(code)
        if errors:
            return ExecutionResult(
                success=False,
                error="\n".join(errors),
                logs=self.logs
            )
            
        # Build safe execution environment
        safe_globals = self._build_safe_globals()
        safe_locals = self._build_safe_locals()
        
        # Capture prints
        self.logs = []
        
        try:
            # Execute code
            exec(code, safe_globals, safe_locals)
            
            # Get result (last expression or 'result' variable)
            result = safe_locals.get('result', None)
            
            # Extract modified state
            modified_state = self._extract_state(safe_locals)
            
            return ExecutionResult(
                success=True,
                output=result,
                logs=self.logs,
                modified_state=modified_state
            )
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=f"Lỗi thực thi: {str(e)}",
                logs=self.logs
            )
            
    def _build_safe_globals(self) -> dict:
        """Build safe globals dict."""
        import builtins as _builtins
        
        def safe_print(*args, **kwargs):
            self.logs.append(" ".join(str(a) for a in args))
        
        # Build safe builtins
        safe_builtins = {}
        for name in ALLOWED_BUILTINS:
            if hasattr(_builtins, name):
                safe_builtins[name] = getattr(_builtins, name)
        safe_builtins['print'] = safe_print
        safe_builtins['True'] = True
        safe_builtins['False'] = False
        safe_builtins['None'] = None
            
        return {
            '__builtins__': safe_builtins,
            'np': np,
            'numpy': np,
            # Shapely
            'Polygon': Polygon,
            'LineString': LineString,
            'Point': Point,
            'MultiPolygon': MultiPolygon,
            'unary_union': unary_union,
            'split': split,
            'rotate': rotate,
            'translate': translate,
            'scale': scale,
            'mapping': mapping,
        }
        
    def _build_safe_locals(self) -> dict:
        """Build safe locals dict with current state."""
        return {
            'boundary': self.state.get('boundary'),
            'roads': self.state.get('roads', []),
            'blocks': self.state.get('blocks', []),
            'lots': self.state.get('lots', []),
            'green_spaces': self.state.get('green_spaces', []),
            'params': self.state.get('params', {}),
        }
        
    def _extract_state(self, locals_dict: dict) -> dict:
        """Extract modified state from locals."""
        return {
            'roads': locals_dict.get('roads', []),
            'blocks': locals_dict.get('blocks', []),
            'lots': locals_dict.get('lots', []),
            'green_spaces': locals_dict.get('green_spaces', []),
        }


# === Code Templates for common operations ===

CODE_TEMPLATES = {
    "widen_road": '''
# Làm đường rộng hơn bằng cách tăng buffer
new_roads = []
for road in roads:
    # Mở rộng đường (thực tế chỉ lưu width, visual sẽ buffer sau)
    new_roads.append(road)
roads = new_roads
params['main_road_width'] = {width}
result = f"Đã đổi bề rộng đường thành {{params['main_road_width']}}m"
''',

    "move_road": '''
# Di chuyển đường
from shapely.affinity import translate
if roads and {index} < len(roads):
    roads[{index}] = translate(roads[{index}], xoff={dx}, yoff={dy})
    result = f"Đã di chuyển đường {{index}} với offset ({{dx}}, {{dy}})"
else:
    result = "Không tìm thấy đường để di chuyển"
''',

    "add_road": '''
# Thêm đường mới
new_road = LineString([({x1}, {y1}), ({x2}, {y2})])
if boundary and new_road.intersects(boundary):
    new_road = new_road.intersection(boundary)
    roads.append(new_road)
    result = f"Đã thêm đường mới, tổng {{len(roads)}} đường"
else:
    result = "Đường mới nằm ngoài ranh giới"
''',

    "remove_road": '''
# Xóa đường
if roads and {index} < len(roads):
    roads.pop({index})
    result = f"Đã xóa đường {{index}}, còn {{len(roads)}} đường"
else:
    result = "Không tìm thấy đường để xóa"
''',

    "scale_blocks": '''
# Thu phóng blocks
from shapely.affinity import scale
new_blocks = []
for block in blocks:
    center = block.centroid
    scaled = scale(block, xfact={factor}, yfact={factor}, origin=center)
    new_blocks.append(scaled)
blocks = new_blocks
result = f"Đã scale {{len(blocks)}} blocks với factor {{{factor}}}"
''',

    "custom": '''
# Custom code - thực thi trực tiếp
{code}
'''
}


def generate_code_from_intent(intent: str, params: dict) -> str:
    """Generate code from user intent.
    
    Args:
        intent: Intent name (widen_road, move_road, etc.)
        params: Parameters for the code template
        
    Returns:
        Generated code string
    """
    template = CODE_TEMPLATES.get(intent, CODE_TEMPLATES['custom'])
    return template.format(**params)
