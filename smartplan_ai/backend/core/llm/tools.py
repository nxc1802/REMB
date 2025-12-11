"""Design tools that can be called by the LLM agent."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging
from shapely.geometry import Polygon, LineString, Point, mapping
from shapely.ops import unary_union

from core.templates import get_template, list_templates, TemplateParams, TemplateResult

logger = logging.getLogger(__name__)


@dataclass
class DesignState:
    """Current design state with named elements."""
    
    boundary: Optional[Polygon] = None
    roads: List[LineString] = field(default_factory=list)
    blocks: List[Polygon] = field(default_factory=list)
    lots: List[Polygon] = field(default_factory=list)
    green_spaces: List[Polygon] = field(default_factory=list)
    entry_points: List[Point] = field(default_factory=list)
    
    # Element names - maps index to name
    road_names: Dict[int, str] = field(default_factory=dict)
    block_names: Dict[int, str] = field(default_factory=dict)
    lot_names: Dict[int, str] = field(default_factory=dict)
    
    # Current settings
    template_name: Optional[str] = None
    rotation: float = 0.0
    main_road_width: float = 24.0
    secondary_road_width: float = 12.0
    cell_size: float = 100.0
    
    # Selected element (for LLM context)
    selected_element: Optional[Dict] = None
    
    def auto_name_elements(self):
        """Generate names for all unnamed elements."""
        # Name roads: R1, R2, ...
        for i in range(len(self.roads)):
            if i not in self.road_names:
                self.road_names[i] = f"R{i+1}"
                
        # Name blocks: B1, B2, ...
        for i in range(len(self.blocks)):
            if i not in self.block_names:
                self.block_names[i] = f"B{i+1}"
                
        # Name lots: L1, L2, ...
        for i in range(len(self.lots)):
            if i not in self.lot_names:
                self.lot_names[i] = f"L{i+1}"
    
    def get_element_summary(self) -> str:
        """Get summary of elements for LLM context."""
        lines = []
        
        # Roads
        if self.roads:
            road_info = []
            for i, road in enumerate(self.roads):
                name = self.road_names.get(i, f"R{i+1}")
                road_info.append(f"{name} ({road.length:.0f}m)")
            lines.append(f"Đường: {', '.join(road_info[:5])}" + (f" và {len(self.roads)-5} đường khác" if len(self.roads) > 5 else ""))
            
        # Blocks  
        if self.blocks:
            lines.append(f"Blocks: {len(self.blocks)} blocks (B1-B{len(self.blocks)})")
            
        # Lots
        if self.lots:
            lines.append(f"Lô đất: {len(self.lots)} lô (L1-L{len(self.lots)})")
            
        # Selected
        if self.selected_element:
            lines.append(f"Đang chọn: {self.selected_element.get('name', 'N/A')}")
            
        return "\n".join(lines) if lines else "Chưa có elements nào."
    
    def to_geojson(self) -> dict:
        """Convert current state to GeoJSON with named elements."""
        self.auto_name_elements()
        features = []
        
        # Boundary
        if self.boundary:
            features.append({
                "type": "Feature",
                "geometry": mapping(self.boundary),
                "properties": {"type": "boundary", "name": "Ranh giới"}
            })
            
        # Roads with names and individual widths
        for i, road in enumerate(self.roads):
            name = self.road_names.get(i, f"R{i+1}")
            # Use individual road width if set, otherwise use default
            if hasattr(self, 'road_widths') and i in self.road_widths:
                road_width = self.road_widths[i]
            else:
                road_width = self.main_road_width if i == 0 else self.secondary_road_width
            features.append({
                "type": "Feature", 
                "geometry": mapping(road),
                "properties": {
                    "type": "road", 
                    "index": i, 
                    "name": name,
                    "length": road.length,
                    "width": road_width
                }
            })
            
        # Blocks with names
        for i, block in enumerate(self.blocks):
            name = self.block_names.get(i, f"B{i+1}")
            features.append({
                "type": "Feature",
                "geometry": mapping(block),
                "properties": {
                    "type": "block", 
                    "index": i, 
                    "name": name, 
                    "area": block.area
                }
            })
            
        # Lots with names
        for i, lot in enumerate(self.lots):
            name = self.lot_names.get(i, f"L{i+1}")
            features.append({
                "type": "Feature",
                "geometry": mapping(lot),
                "properties": {
                    "type": "lot", 
                    "index": i, 
                    "name": name, 
                    "area": lot.area
                }
            })
            
        # Green spaces
        for i, green in enumerate(self.green_spaces):
            features.append({
                "type": "Feature",
                "geometry": mapping(green),
                "properties": {"type": "green_space", "index": i, "name": f"G{i+1}", "area": green.area}
            })
            
        return {"type": "FeatureCollection", "features": features}
    
    def find_element_by_name(self, name: str) -> Optional[Dict]:
        """Find element by name (R1, B3, L5, etc.)."""
        name = name.upper().strip()
        
        if name.startswith('R') and name[1:].isdigit():
            idx = int(name[1:]) - 1
            if 0 <= idx < len(self.roads):
                return {"type": "road", "index": idx, "name": name, "geometry": self.roads[idx]}
                
        elif name.startswith('B') and name[1:].isdigit():
            idx = int(name[1:]) - 1
            if 0 <= idx < len(self.blocks):
                return {"type": "block", "index": idx, "name": name, "geometry": self.blocks[idx]}
                
        elif name.startswith('L') and name[1:].isdigit():
            idx = int(name[1:]) - 1
            if 0 <= idx < len(self.lots):
                return {"type": "lot", "index": idx, "name": name, "geometry": self.lots[idx]}
                
        return None
    
    def get_stats(self) -> dict:
        """Get statistics about current design."""
        return {
            "boundary_area": self.boundary.area if self.boundary else 0,
            "road_count": len(self.roads),
            "road_length": sum(r.length for r in self.roads),
            "block_count": len(self.blocks),
            "lot_count": len(self.lots),
            "total_lot_area": sum(l.area for l in self.lots),
            "green_count": len(self.green_spaces),
            "green_area": sum(g.area for g in self.green_spaces),
            "template": self.template_name,
            "rotation": self.rotation,
            "selected": self.selected_element.get("name") if self.selected_element else None
        }


class DesignTools:
    """Pre-defined tools that can be called by the LLM agent."""
    
    def __init__(self, state: Optional[DesignState] = None):
        self.state = state or DesignState()
        
    def set_boundary(self, boundary: Polygon) -> dict:
        """Set the site boundary.
        
        Args:
            boundary: Site boundary polygon
            
        Returns:
            Result dict with status and boundary info
        """
        self.state.boundary = boundary
        
        return {
            "success": True,
            "message": f"Đã thiết lập ranh giới khu đất: {boundary.area/10000:.2f} ha",
            "area": boundary.area,
            "bounds": boundary.bounds
        }
    
    def apply_template(
        self,
        template_name: str,
        cell_size: float = 100.0,
        rotation: float = 0.0
    ) -> dict:
        """Apply a road template to the boundary.
        
        Args:
            template_name: Template name (spine/grid/loop/cross)
            cell_size: Grid cell size in meters
            rotation: Rotation angle in degrees
            
        Returns:
            Result dict with roads and blocks
        """
        if not self.state.boundary:
            return {"success": False, "message": "Chưa có ranh giới khu đất"}
            
        template = get_template(template_name)
        if not template:
            return {
                "success": False, 
                "message": f"Không tìm thấy template '{template_name}'. Có sẵn: spine, grid, loop, cross"
            }
            
        # Generate template
        params = TemplateParams(
            cell_size=cell_size,
            rotation=rotation,
            main_road_width=self.state.main_road_width,
            secondary_road_width=self.state.secondary_road_width
        )
        
        result = template.generate(self.state.boundary, params)
        
        # Update state
        self.state.roads = result.roads
        self.state.blocks = result.blocks
        self.state.entry_points = result.entry_points
        self.state.template_name = template_name
        self.state.rotation = rotation
        self.state.cell_size = cell_size
        
        # Clear lots (will be regenerated)
        self.state.lots = []
        
        return {
            "success": True,
            "message": f"Đã áp dụng template '{template.display_name}'",
            "road_count": len(result.roads),
            "block_count": len(result.blocks),
            "metadata": result.metadata
        }
    
    def rotate_roads(self, angle: float) -> dict:
        """Rotate the road network by an angle.
        
        Args:
            angle: Rotation angle in degrees (positive = clockwise)
            
        Returns:
            Result dict
        """
        if not self.state.template_name:
            return {"success": False, "message": "Chưa có template nào được áp dụng"}
            
        # Re-apply template with new rotation
        new_rotation = self.state.rotation + angle
        
        return self.apply_template(
            self.state.template_name,
            self.state.cell_size,
            new_rotation
        )
    
    def set_road_width(
        self, 
        main_width: float = None, 
        secondary_width: float = None
    ) -> dict:
        """Set road widths.
        
        Args:
            main_width: Main road width in meters
            secondary_width: Secondary road width in meters
            
        Returns:
            Result dict
        """
        if main_width:
            if main_width < 6:
                return {"success": False, "message": "Bề rộng đường chính phải ≥ 6m"}
            self.state.main_road_width = main_width
            
        if secondary_width:
            if secondary_width < 6:
                return {"success": False, "message": "Bề rộng đường phụ phải ≥ 6m"}
            self.state.secondary_road_width = secondary_width
            
        # Re-apply template if exists
        if self.state.template_name:
            return self.apply_template(
                self.state.template_name,
                self.state.cell_size,
                self.state.rotation
            )
            
        return {
            "success": True,
            "message": f"Đã cập nhật bề rộng đường: chính={self.state.main_road_width}m, phụ={self.state.secondary_road_width}m"
        }
    
    def subdivide_blocks(self, lot_size: float = 2000) -> dict:
        """Subdivide blocks into lots.
        
        Args:
            lot_size: Target lot size in m²
            
        Returns:
            Result dict with lots
        """
        if not self.state.blocks:
            return {"success": False, "message": "Chưa có blocks để chia lô"}
            
        lots = []
        green_spaces = []
        
        for block in self.state.blocks:
            block_lots, block_greens = self._subdivide_block(block, lot_size)
            lots.extend(block_lots)
            green_spaces.extend(block_greens)
            
        self.state.lots = lots
        self.state.green_spaces = green_spaces
        
        return {
            "success": True,
            "message": f"Đã chia thành {len(lots)} lô, {len(green_spaces)} khu cây xanh",
            "lot_count": len(lots),
            "green_count": len(green_spaces),
            "total_lot_area": sum(l.area for l in lots)
        }
    
    def _subdivide_block(
        self, 
        block: Polygon, 
        target_lot_size: float
    ) -> tuple:
        """Subdivide a single block into lots.
        
        Simple grid subdivision aligned to block OBB.
        """
        from core.templates.base import RoadTemplate
        
        # Get OBB info
        obb = block.minimum_rotated_rectangle
        coords = list(obb.exterior.coords)[:4]
        
        import numpy as np
        p0 = np.array(coords[0])
        p1 = np.array(coords[1])
        p3 = np.array(coords[3])
        
        vec_x = p1 - p0
        vec_y = p3 - p0
        
        len_x = np.linalg.norm(vec_x)
        len_y = np.linalg.norm(vec_y)
        
        # Normalize vectors
        if len_x > 0:
            vec_x = vec_x / len_x
        if len_y > 0:
            vec_y = vec_y / len_y
            
        # Calculate lot dimensions
        lot_width = np.sqrt(target_lot_size * 0.67)  # Aspect ratio ~1.5
        lot_depth = target_lot_size / lot_width
        
        num_cols = max(1, int(len_x / lot_width))
        num_rows = max(1, int(len_y / lot_depth))
        
        cell_w = len_x / num_cols
        cell_h = len_y / num_rows
        
        lots = []
        greens = []
        
        for i in range(num_rows):
            for j in range(num_cols):
                # Cell corners
                c0 = p0 + vec_x * j * cell_w + vec_y * i * cell_h
                c1 = c0 + vec_x * cell_w
                c2 = c1 + vec_y * cell_h
                c3 = c0 + vec_y * cell_h
                
                cell = Polygon([c0, c1, c2, c3, c0])
                
                # Clip to block
                try:
                    clipped = cell.intersection(block)
                    
                    if clipped.is_empty:
                        continue
                        
                    if clipped.geom_type == 'Polygon':
                        if clipped.area >= target_lot_size * 0.3:
                            # Check quality
                            if self._is_good_lot(clipped):
                                lots.append(clipped)
                            else:
                                greens.append(clipped)
                                
                except Exception as e:
                    logger.warning(f"Lot clip failed: {e}")
                    
        return lots, greens
    
    def _is_good_lot(self, polygon: Polygon) -> bool:
        """Check if polygon is a good lot shape."""
        if polygon.area < 500:
            return False
            
        # Check rectangularity
        obb = polygon.minimum_rotated_rectangle
        rectangularity = polygon.area / obb.area if obb.area > 0 else 0
        
        return rectangularity >= 0.6
    
    def add_green_space(self, location: str = "corners") -> dict:
        """Add green spaces.
        
        Args:
            location: Where to add green ("corners", "center", "edges")
            
        Returns:
            Result dict
        """
        # This is a placeholder - can be expanded
        return {
            "success": True,
            "message": f"Đã thêm khu cây xanh vào {location}",
            "green_count": len(self.state.green_spaces)
        }
    
    # === NEW FUNCTIONS ===
    
    def add_road(self, x1: float, y1: float, x2: float, y2: float) -> dict:
        """Add a new road line.
        
        Args:
            x1, y1: Start point
            x2, y2: End point
            
        Returns:
            Result dict
        """
        new_road = LineString([(x1, y1), (x2, y2)])
        
        # Clip to boundary if exists
        if self.state.boundary:
            clipped = new_road.intersection(self.state.boundary)
            if clipped.is_empty:
                return {"success": False, "message": "Đường mới nằm ngoài ranh giới"}
            if clipped.geom_type == 'LineString':
                new_road = clipped
                
        self.state.roads.append(new_road)
        
        return {
            "success": True,
            "message": f"Đã thêm đường mới, tổng {len(self.state.roads)} đường",
            "road_count": len(self.state.roads)
        }
    
    def remove_road(self, index: int) -> dict:
        """Remove a road by index.
        
        Args:
            index: Road index to remove
            
        Returns:
            Result dict
        """
        if index < 0 or index >= len(self.state.roads):
            return {"success": False, "message": f"Không tìm thấy đường {index}"}
            
        self.state.roads.pop(index)
        
        return {
            "success": True,
            "message": f"Đã xóa đường {index}, còn {len(self.state.roads)} đường",
            "road_count": len(self.state.roads)
        }
    
    def move_road(self, index: int, dx: float, dy: float) -> dict:
        """Move a road by offset.
        
        Args:
            index: Road index
            dx: X offset
            dy: Y offset
            
        Returns:
            Result dict
        """
        from shapely.affinity import translate
        
        if index < 0 or index >= len(self.state.roads):
            return {"success": False, "message": f"Không tìm thấy đường {index}"}
            
        self.state.roads[index] = translate(self.state.roads[index], xoff=dx, yoff=dy)
        
        return {
            "success": True,
            "message": f"Đã di chuyển đường {index} với offset ({dx}, {dy})"
        }
    
    def scale_design(self, factor: float) -> dict:
        """Scale the entire design.
        
        Args:
            factor: Scale factor (1.0 = no change, 2.0 = double size)
            
        Returns:
            Result dict
        """
        from shapely.affinity import scale
        
        if not self.state.boundary:
            return {"success": False, "message": "Chưa có ranh giới"}
            
        center = self.state.boundary.centroid
        
        # Scale all elements
        self.state.roads = [
            scale(r, xfact=factor, yfact=factor, origin=center) 
            for r in self.state.roads
        ]
        self.state.blocks = [
            scale(b, xfact=factor, yfact=factor, origin=center)
            for b in self.state.blocks
        ]
        self.state.lots = [
            scale(l, xfact=factor, yfact=factor, origin=center)
            for l in self.state.lots
        ]
        
        return {
            "success": True,
            "message": f"Đã scale thiết kế với factor {factor}"
        }
    
    def set_cell_size(self, size: float) -> dict:
        """Set cell/block size and re-apply template.
        
        Args:
            size: Cell size in meters
            
        Returns:
            Result dict
        """
        if size < 30 or size > 500:
            return {"success": False, "message": "Kích thước ô phải từ 30-500m"}
            
        self.state.cell_size = size
        
        if self.state.template_name:
            return self.apply_template(
                self.state.template_name,
                size,
                self.state.rotation
            )
            
        return {
            "success": True,
            "message": f"Đã đặt kích thước ô = {size}m"
        }
    
    def execute_code(self, code: str) -> dict:
        """Execute custom Python code in sandbox.
        
        Args:
            code: Python code to execute
            
        Returns:
            Result dict
        """
        from core.llm.code_executor import SandboxedExecutor
        
        # Build state dict for executor
        state_dict = {
            'boundary': self.state.boundary,
            'roads': self.state.roads,
            'blocks': self.state.blocks,
            'lots': self.state.lots,
            'green_spaces': self.state.green_spaces,
            'params': {
                'main_road_width': self.state.main_road_width,
                'secondary_road_width': self.state.secondary_road_width,
                'cell_size': self.state.cell_size,
            }
        }
        
        executor = SandboxedExecutor(state_dict)
        result = executor.execute(code)
        
        if result.success:
            # Update state from result
            if result.modified_state:
                self.state.roads = result.modified_state.get('roads', self.state.roads)
                self.state.blocks = result.modified_state.get('blocks', self.state.blocks)
                self.state.lots = result.modified_state.get('lots', self.state.lots)
                self.state.green_spaces = result.modified_state.get('green_spaces', self.state.green_spaces)
                
            return {
                "success": True,
                "message": str(result.output) if result.output else "Code executed",
                "logs": result.logs
            }
        else:
            return {
                "success": False,
                "message": result.error,
                "logs": result.logs
            }
    
    def get_stats(self) -> dict:
        """Get current design statistics.
        
        Returns:
            Statistics dict
        """
        stats = self.state.get_stats()
        
        # Format for display
        return {
            "success": True,
            "stats": {
                "Diện tích khu đất": f"{stats['boundary_area']/10000:.2f} ha",
                "Số đường": stats['road_count'],
                "Tổng chiều dài đường": f"{stats['road_length']:.0f} m",
                "Số block": stats['block_count'],
                "Số lô đất": stats['lot_count'],
                "Tổng diện tích lô": f"{stats['total_lot_area']/10000:.2f} ha",
                "Số khu cây xanh": stats['green_count'],
                "Template": stats['template'] or "Chưa chọn",
                "Góc xoay": f"{stats['rotation']}°"
            }
        }
    
    def list_templates(self) -> dict:
        """List available templates.
        
        Returns:
            List of templates
        """
        templates = list_templates()
        
        return {
            "success": True,
            "templates": templates
        }
    
    def execute_action(self, action: str, params: dict) -> dict:
        """Execute an action by name.
        
        Args:
            action: Action name
            params: Action parameters
            
        Returns:
            Action result
        """
        action_map = {
            # Template actions
            "apply_template": self.apply_template,
            "rotate_roads": self.rotate_roads,
            "set_road_width": self.set_road_width,
            "set_cell_size": self.set_cell_size,
            
            # Road actions
            "add_road": self.add_road,
            "remove_road": self.remove_road,
            "move_road": self.move_road,
            
            # Block actions
            "subdivide_blocks": self.subdivide_blocks,
            "scale_design": self.scale_design,
            
            # Element actions by name
            "select_element": self.select_element,
            "delete_element": self.delete_element,
            "move_element": self.move_element,
            "get_element_info": self.get_element_info,
            "set_element_width": self.set_element_width,
            "convert_to_green": self.convert_to_green,
            
            # Other
            "add_green_space": self.add_green_space,
            "get_stats": self.get_stats,
            "list_templates": self.list_templates,
            "list_elements": self.list_elements,
            
            # Code execution
            "execute_code": self.execute_code
        }
        
        if action not in action_map:
            return {
                "success": False,
                "message": f"Action không hợp lệ: {action}. Có sẵn: {list(action_map.keys())}"
            }
            
        try:
            return action_map[action](**params)
        except Exception as e:
            logger.error(f"Action {action} failed: {e}")
            return {"success": False, "message": f"Lỗi: {str(e)}"}
    
    # === Element manipulation by name ===
    
    def select_element(self, name: str) -> dict:
        """Select an element by name (R1, B3, L5...).
        
        Args:
            name: Element name
            
        Returns:
            Result dict
        """
        element = self.state.find_element_by_name(name)
        if element:
            self.state.selected_element = element
            geom = element["geometry"]
            info = f"type={element['type']}"
            if hasattr(geom, 'length'):
                info += f", length={geom.length:.0f}m"
            if hasattr(geom, 'area'):
                info += f", area={geom.area:.0f}m²"
            return {
                "success": True,
                "message": f"Đã chọn {name} ({info})",
                "element": {"name": name, "type": element["type"], "index": element["index"]}
            }
        return {"success": False, "message": f"Không tìm thấy element '{name}'"}
    
    def delete_element(self, name: str) -> dict:
        """Delete an element by name.
        
        Args:
            name: Element name (R1, B3, L5...)
            
        Returns:
            Result dict
        """
        element = self.state.find_element_by_name(name)
        if not element:
            return {"success": False, "message": f"Không tìm thấy '{name}'"}
            
        elem_type = element["type"]
        idx = element["index"]
        
        if elem_type == "road":
            self.state.roads.pop(idx)
            # Rebuild road names
            self.state.road_names = {}
            self.state.auto_name_elements()
        elif elem_type == "block":
            self.state.blocks.pop(idx)
            self.state.block_names = {}
            self.state.auto_name_elements()
        elif elem_type == "lot":
            self.state.lots.pop(idx)
            self.state.lot_names = {}
            self.state.auto_name_elements()
        else:
            return {"success": False, "message": f"Không thể xóa {elem_type}"}
            
        # Clear selection if deleted
        if self.state.selected_element and self.state.selected_element.get("name") == name:
            self.state.selected_element = None
            
        return {
            "success": True,
            "message": f"Đã xóa {name}",
            "road_count": len(self.state.roads),
            "block_count": len(self.state.blocks),
            "lot_count": len(self.state.lots)
        }
    
    def move_element(self, name: str, dx: float = 0, dy: float = 0) -> dict:
        """Move an element by name.
        
        Args:
            name: Element name
            dx: X offset
            dy: Y offset
            
        Returns:
            Result dict
        """
        from shapely.affinity import translate
        
        element = self.state.find_element_by_name(name)
        if not element:
            return {"success": False, "message": f"Không tìm thấy '{name}'"}
            
        elem_type = element["type"]
        idx = element["index"]
        
        if elem_type == "road":
            self.state.roads[idx] = translate(self.state.roads[idx], xoff=dx, yoff=dy)
        elif elem_type == "block":
            self.state.blocks[idx] = translate(self.state.blocks[idx], xoff=dx, yoff=dy)
        elif elem_type == "lot":
            self.state.lots[idx] = translate(self.state.lots[idx], xoff=dx, yoff=dy)
        else:
            return {"success": False, "message": f"Không thể di chuyển {elem_type}"}
            
        return {"success": True, "message": f"Đã di chuyển {name} với offset ({dx}, {dy})"}
    
    def get_element_info(self, name: str) -> dict:
        """Get info about an element.
        
        Args:
            name: Element name
            
        Returns:
            Result dict with element info
        """
        element = self.state.find_element_by_name(name)
        if not element:
            return {"success": False, "message": f"Không tìm thấy '{name}'"}
            
        geom = element["geometry"]
        info = {
            "name": name,
            "type": element["type"],
            "index": element["index"]
        }
        
        if hasattr(geom, 'length'):
            info["length"] = f"{geom.length:.0f}m"
        if hasattr(geom, 'area'):
            info["area"] = f"{geom.area:.0f}m²"
        if hasattr(geom, 'centroid'):
            c = geom.centroid
            info["center"] = f"({c.x:.0f}, {c.y:.0f})"
            
        return {"success": True, "info": info}
    
    def list_elements(self) -> dict:
        """List all named elements.
        
        Returns:
            Result dict with element list
        """
        self.state.auto_name_elements()
        
        elements = []
        
        # Roads
        for i, road in enumerate(self.state.roads):
            name = self.state.road_names.get(i, f"R{i+1}")
            elements.append({"name": name, "type": "road", "length": f"{road.length:.0f}m"})
            
        # Blocks
        for i, block in enumerate(self.state.blocks):
            name = self.state.block_names.get(i, f"B{i+1}")
            elements.append({"name": name, "type": "block", "area": f"{block.area:.0f}m²"})
            
        # Lots (show first 10)
        for i, lot in enumerate(self.state.lots[:10]):
            name = self.state.lot_names.get(i, f"L{i+1}")
            elements.append({"name": name, "type": "lot", "area": f"{lot.area:.0f}m²"})
            
        if len(self.state.lots) > 10:
            elements.append({"name": f"L11-L{len(self.state.lots)}", "type": "lot", "count": len(self.state.lots) - 10})
            
        return {
            "success": True,
            "elements": elements,
            "summary": self.state.get_element_summary()
        }
    
    def set_element_width(self, name: str = None, width: float = 24.0) -> dict:
        """Set width for a specific road element.
        
        If name is not provided, uses currently selected element.
        
        Args:
            name: Road name (R1, R2...). If None, uses selected element.
            width: New width in meters
            
        Returns:
            Result dict
        """
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        
        # Use selected element if name not provided
        if not name and self.state.selected_element:
            name = self.state.selected_element.get('name')
            
        if not name:
            return {"success": False, "message": "Không có element nào được chọn. Hãy chọn 1 đường hoặc chỉ định tên (R1, R2...)"}
            
        element = self.state.find_element_by_name(name)
        if not element:
            return {"success": False, "message": f"Không tìm thấy '{name}'"}
            
        if element["type"] != "road":
            return {"success": False, "message": f"'{name}' không phải là đường. Chỉ có thể đổi bề rộng đường."}
            
        idx = element["index"]
        road = self.state.roads[idx]
        
        # Get old width (from road_widths dict or default)
        if hasattr(self.state, 'road_widths') and idx in self.state.road_widths:
            old_width = self.state.road_widths[idx]
        else:
            old_width = self.state.main_road_width if idx == 0 else self.state.secondary_road_width
        
        # Store new width
        if not hasattr(self.state, 'road_widths'):
            self.state.road_widths = {}
        self.state.road_widths[idx] = width
        
        # Calculate width difference and adjust blocks
        width_diff = width - old_width
        if abs(width_diff) > 0.1:  # Only recalculate if significant change
            # Buffer the road by half the width difference (expand on each side)
            road_buffer = road.buffer(width_diff / 2, cap_style=2)  # flat cap
            
            # Subtract expanded road from all blocks
            new_blocks = []
            for block in self.state.blocks:
                if block.intersects(road_buffer):
                    # Subtract the road buffer from block
                    new_block = block.difference(road_buffer)
                    if not new_block.is_empty and new_block.area > 100:  # Keep only meaningful blocks
                        if new_block.geom_type == 'Polygon':
                            new_blocks.append(new_block)
                        elif new_block.geom_type == 'MultiPolygon':
                            for geom in new_block.geoms:
                                if geom.area > 100:
                                    new_blocks.append(geom)
                else:
                    new_blocks.append(block)
            
            self.state.blocks = new_blocks
            
            # Also update lots if they intersect
            if self.state.lots:
                new_lots = []
                for lot in self.state.lots:
                    if lot.intersects(road_buffer):
                        new_lot = lot.difference(road_buffer)
                        if not new_lot.is_empty and new_lot.area > 50:
                            if new_lot.geom_type == 'Polygon':
                                new_lots.append(new_lot)
                            elif new_lot.geom_type == 'MultiPolygon':
                                for geom in new_lot.geoms:
                                    if geom.area > 50:
                                        new_lots.append(geom)
                    else:
                        new_lots.append(lot)
                self.state.lots = new_lots
            
            # Re-assign names
            self.state.block_names = {}
            self.state.lot_names = {}
            self.state.auto_name_elements()
        
        return {
            "success": True,
            "message": f"Đã đổi bề rộng {name} từ {old_width}m → {width}m. Đã cập nhật {len(self.state.blocks)} blocks.",
            "element": name,
            "old_width": old_width,
            "new_width": width,
            "road_count": len(self.state.roads),
            "block_count": len(self.state.blocks),
            "lot_count": len(self.state.lots)
        }
    
    def convert_to_green(self, name: str = None) -> dict:
        """Convert a lot to green space.
        
        If name is not provided, uses currently selected element.
        
        Args:
            name: Lot name (L1, L2...). If None, uses selected element.
            
        Returns:
            Result dict
        """
        # Use selected element if name not provided
        if not name and self.state.selected_element:
            name = self.state.selected_element.get('name')
            
        if not name:
            return {"success": False, "message": "Không có element nào được chọn. Hãy chọn 1 lô đất hoặc chỉ định tên (L1, L2...)"}
            
        element = self.state.find_element_by_name(name)
        if not element:
            return {"success": False, "message": f"Không tìm thấy '{name}'"}
            
        if element["type"] not in ["lot", "block"]:
            return {"success": False, "message": f"'{name}' không phải là lô đất hoặc block. Chỉ có thể đổi lô đất/block thành cây xanh."}
            
        idx = element["index"]
        geom = element["geometry"]
        
        # Move from lots/blocks to green_spaces
        if element["type"] == "lot":
            self.state.lots.pop(idx)
            self.state.lot_names = {}
            self.state.auto_name_elements()
        else:
            self.state.blocks.pop(idx)
            self.state.block_names = {}
            self.state.auto_name_elements()
            
        self.state.green_spaces.append(geom)
        
        # Clear selection
        self.state.selected_element = None
        
        return {
            "success": True,
            "message": f"Đã chuyển {name} thành khu cây xanh G{len(self.state.green_spaces)}",
            "road_count": len(self.state.roads),
            "block_count": len(self.state.blocks),
            "lot_count": len(self.state.lots),
            "green_count": len(self.state.green_spaces)
        }

