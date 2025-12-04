"""
Core domain models for REMB Optimization Engine
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point
import uuid


class PlotType(str, Enum):
    """Types of plots in industrial estate"""
    INDUSTRIAL = "industrial"
    GREEN_SPACE = "green_space"
    ROAD = "road"
    UTILITY = "utility"
    BUFFER = "buffer"


class ConstraintType(str, Enum):
    """Types of constraints"""
    SETBACK = "setback"
    FIRE_SAFETY = "fire_safety"
    WATERWAY = "waterway"
    HAZARD_ZONE = "hazard_zone"
    NO_BUILD = "no_build"


@dataclass
class Constraint:
    """Spatial constraint"""
    type: ConstraintType
    geometry: Polygon
    buffer_distance_m: float
    description: str
    is_hard: bool = True  # Hard constraint vs soft constraint


@dataclass
class SiteBoundary:
    """Site boundary representation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    geometry: Polygon = None
    area_sqm: float = 0.0
    constraints: List[Constraint] = field(default_factory=list)
    buildable_area_sqm: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_buildable_area(self) -> float:
        """Calculate buildable area after applying constraints"""
        buildable = self.geometry
        for constraint in self.constraints:
            if constraint.is_hard:
                buildable = buildable.difference(constraint.geometry)
        self.buildable_area_sqm = buildable.area
        return self.buildable_area_sqm


@dataclass
class Plot:
    """Industrial plot representation"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    geometry: Polygon = None
    area_sqm: float = 0.0
    type: PlotType = PlotType.INDUSTRIAL
    frontage_m: float = 0.0
    width_m: float = 0.0
    depth_m: float = 0.0
    has_road_access: bool = False
    orientation_degrees: float = 0.0  # 0-360 degrees
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoadNetwork:
    """Road network representation"""
    primary_roads: MultiLineString = None
    secondary_roads: MultiLineString = None
    tertiary_roads: MultiLineString = None
    total_length_m: float = 0.0
    total_area_sqm: float = 0.0
    
    def calculate_total_length(self) -> float:
        """Calculate total road network length"""
        length = 0.0
        if self.primary_roads:
            length += self.primary_roads.length
        if self.secondary_roads:
            length += self.secondary_roads.length
        if self.tertiary_roads:
            length += self.tertiary_roads.length
        self.total_length_m = length
        return length


@dataclass
class LayoutMetrics:
    """Metrics for evaluating a layout"""
    total_area_sqm: float = 0.0
    sellable_area_sqm: float = 0.0
    green_space_area_sqm: float = 0.0
    road_area_sqm: float = 0.0
    utility_area_sqm: float = 0.0
    
    # Ratios
    sellable_ratio: float = 0.0  # Sellable / Total
    green_space_ratio: float = 0.0  # Green / Total
    road_ratio: float = 0.0  # Road / Total
    
    # Compliance
    far_value: float = 0.0
    is_compliant: bool = False
    compliance_violations: List[str] = field(default_factory=list)
    
    # Efficiency
    road_efficiency: float = 0.0  # Lower is better (less road per sellable area)
    num_plots: int = 0
    avg_plot_size_sqm: float = 0.0
    
    def calculate_ratios(self):
        """Calculate all ratios"""
        if self.total_area_sqm > 0:
            self.sellable_ratio = self.sellable_area_sqm / self.total_area_sqm
            self.green_space_ratio = self.green_space_area_sqm / self.total_area_sqm
            self.road_ratio = self.road_area_sqm / self.total_area_sqm
            
            if self.sellable_area_sqm > 0:
                self.road_efficiency = self.road_area_sqm / self.sellable_area_sqm


@dataclass
class Layout:
    """Complete industrial estate layout"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    site_boundary: SiteBoundary = None
    plots: List[Plot] = field(default_factory=list)
    road_network: RoadNetwork = None
    metrics: LayoutMetrics = field(default_factory=LayoutMetrics)
    
    # Optimization metadata
    generation: int = 0
    fitness_scores: Dict[str, float] = field(default_factory=dict)
    pareto_rank: int = 0
    
    def calculate_metrics(self) -> LayoutMetrics:
        """Calculate all layout metrics"""
        self.metrics = LayoutMetrics()
        self.metrics.total_area_sqm = self.site_boundary.area_sqm
        
        # Calculate areas by type
        for plot in self.plots:
            if plot.type == PlotType.INDUSTRIAL:
                self.metrics.sellable_area_sqm += plot.area_sqm
            elif plot.type == PlotType.GREEN_SPACE:
                self.metrics.green_space_area_sqm += plot.area_sqm
            elif plot.type == PlotType.UTILITY:
                self.metrics.utility_area_sqm += plot.area_sqm
        
        # Road area
        if self.road_network:
            self.metrics.road_area_sqm = self.road_network.total_area_sqm
        
        # Calculate ratios
        self.metrics.num_plots = len([p for p in self.plots if p.type == PlotType.INDUSTRIAL])
        if self.metrics.num_plots > 0:
            self.metrics.avg_plot_size_sqm = self.metrics.sellable_area_sqm / self.metrics.num_plots
        
        self.metrics.calculate_ratios()
        
        return self.metrics


@dataclass
class ParetoFront:
    """Collection of Pareto-optimal solutions"""
    layouts: List[Layout] = field(default_factory=list)
    optimization_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generation_time_seconds: float = 0.0
    
    def get_max_sellable_layout(self) -> Optional[Layout]:
        """Get layout with maximum sellable area"""
        if not self.layouts:
            return None
        return max(self.layouts, key=lambda l: l.metrics.sellable_area_sqm)
    
    def get_max_green_layout(self) -> Optional[Layout]:
        """Get layout with maximum green space"""
        if not self.layouts:
            return None
        return max(self.layouts, key=lambda l: l.metrics.green_space_area_sqm)
    
    def get_balanced_layout(self) -> Optional[Layout]:
        """Get most balanced layout (normalized multi-objective)"""
        if not self.layouts:
            return None
        # Simple balanced score: normalize and average objectives
        def balance_score(layout: Layout):
            return (
                layout.metrics.sellable_ratio * 0.4 +
                layout.metrics.green_space_ratio * 0.3 +
                (1 - layout.metrics.road_efficiency) * 0.3
            )
        return max(self.layouts, key=balance_score)


@dataclass
class ComplianceReport:
    """Regulatory compliance report"""
    layout_id: str
    is_compliant: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    
    def add_violation(self, message: str):
        """Add compliance violation"""
        self.violations.append(message)
        self.is_compliant = False
    
    def add_warning(self, message: str):
        """Add warning (non-critical)"""
        self.warnings.append(message)
    
    def add_pass(self, check_name: str):
        """Add passed check"""
        self.checks_passed.append(check_name)
