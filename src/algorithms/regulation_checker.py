"""
Regulation Checker - Module C: The Inspector
Rule-based expert system for Vietnamese industrial estate regulatory compliance
"""
import yaml
from pathlib import Path
from typing import List, Dict
import logging
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union
import geopandas as gpd

from src.models.domain import Layout, Plot, PlotType, ComplianceReport, Constraint, ConstraintType

logger = logging.getLogger(__name__)


class RegulationChecker:
    """
    Automated regulatory compliance checker for industrial estate layouts
    Based on Vietnamese industrial estate regulations
    """
    
    def __init__(self, regulations_path: str = "config/regulations.yaml"):
        """
        Initialize regulation checker
        
        Args:
            regulations_path: Path to regulations YAML configuration
        """
        self.regulations_path = Path(regulations_path)
        self.regulations = self._load_regulations()
        self.logger = logging.getLogger(__name__)
    
    def _load_regulations(self) -> dict:
        """Load regulations from YAML file"""
        if not self.regulations_path.exists():
            self.logger.warning(f"Regulations file not found: {self.regulations_path}")
            return self._get_default_regulations()
        
        with open(self.regulations_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_default_regulations(self) -> dict:
        """Get default regulations if file not found"""
        return {
            'setbacks': {
                'boundary_minimum': 50,
                'fire_safety_distance': 30,
                'waterway_buffer': 100
            },
            'far': {
                'maximum': 0.7,
                'minimum': 0.3
            },
            'green_space': {
                'minimum_percentage': 0.15
            },
            'plot': {
                'minimum_area_sqm': 1000,
                'minimum_width_m': 20
            },
            'roads': {
                'maximum_distance_to_road_m': 200
            }
        }
    
    def validate_compliance(self, layout: Layout) -> ComplianceReport:
        """
        Comprehensive regulatory compliance validation
        
        Args:
            layout: Layout to validate
            
        Returns:
            ComplianceReport with violations and warnings
        """
        report = ComplianceReport(
            layout_id=layout.id,
            is_compliant=True
        )
        
        self.logger.info(f"Validating layout {layout.id} against Vietnamese regulations")
        
        # Run all checks
        self._check_boundary_setbacks(layout, report)
        self._check_far_compliance(layout, report)
        self._check_green_space_requirements(layout, report)
        self._check_plot_dimensions(layout, report)
        self._check_road_accessibility(layout, report)
        self._check_fire_safety_distances(layout, report)
        self._check_no_overlaps(layout, report)
        
        # Final determination
        if len(report.violations) == 0:
            report.is_compliant = True
            self.logger.info(f"Layout {layout.id} is COMPLIANT")
        else:
            report.is_compliant = False
            self.logger.warning(f"Layout {layout.id} has {len(report.violations)} violations")
        
        return report
    
    def _check_boundary_setbacks(self, layout: Layout, report: ComplianceReport):
        """Check minimum setback from site boundary"""
        min_setback = self.regulations['setbacks']['boundary_minimum']
        
        # Create buffer zone inside boundary
        boundary = layout.site_boundary.geometry
        setback_zone = boundary.buffer(-min_setback)
        
        for plot in layout.plots:
            if plot.type == PlotType.INDUSTRIAL:
                if not setback_zone.contains(plot.geometry):
                    report.add_violation(
                        f"Plot {plot.id} violates {min_setback}m boundary setback requirement"
                    )
                    return
        
        report.add_pass("Boundary setback compliance")
    
    def _check_far_compliance(self, layout: Layout, report: ComplianceReport):
        """Check Floor Area Ratio (FAR) compliance"""
        max_far = self.regulations['far']['maximum']
        min_far = self.regulations['far'].get('minimum', 0.0)
        
        metrics = layout.metrics
        
        # FAR = Total floor area / Land area
        # Simplified: assuming single story, FAR = Building area / Land area
        if metrics.sellable_ratio > max_far:
            report.add_violation(
                f"FAR {metrics.sellable_ratio:.2f} exceeds maximum {max_far}"
            )
        elif metrics.sellable_ratio < min_far:
            report.add_warning(
                f"FAR {metrics.sellable_ratio:.2f} below recommended minimum {min_far}"
            )
        else:
            report.add_pass(f"FAR compliance ({metrics.sellable_ratio:.2f})")
    
    def _check_green_space_requirements(self, layout: Layout, report: ComplianceReport):
        """Check minimum green space requirement"""
        min_green = self.regulations['green_space']['minimum_percentage']
        
        metrics = layout.metrics
        
        if metrics.green_space_ratio < min_green:
            deficit = (min_green - metrics.green_space_ratio) * 100
            report.add_violation(
                f"Green space {metrics.green_space_ratio*100:.1f}% is below minimum {min_green*100}% "
                f"(deficit: {deficit:.1f}%)"
            )
        else:
            report.add_pass(f"Green space compliance ({metrics.green_space_ratio*100:.1f}%)")
    
    def _check_plot_dimensions(self, layout: Layout, report: ComplianceReport):
        """Check plot minimum dimensions"""
        min_area = self.regulations['plot']['minimum_area_sqm']
        min_width = self.regulations['plot']['minimum_width_m']
        
        violations = []
        for plot in layout.plots:
            if plot.type == PlotType.INDUSTRIAL:
                if plot.area_sqm < min_area:
                    violations.append(
                        f"Plot {plot.id} area {plot.area_sqm:.0f}m² below minimum {min_area}m²"
                    )
                
                if plot.width_m < min_width:
                    violations.append(
                        f"Plot {plot.id} width {plot.width_m:.1f}m below minimum {min_width}m"
                    )
        
        if violations:
            for v in violations:
                report.add_violation(v)
        else:
            report.add_pass("Plot dimension compliance")
    
    def _check_road_accessibility(self, layout: Layout, report: ComplianceReport):
        """Check that all plots have road access within maximum distance"""
        max_distance = self.regulations['roads']['maximum_distance_to_road_m']
        
        if not layout.road_network or not layout.road_network.primary_roads:
            report.add_warning("No road network defined for accessibility check")
            return
        
        # Simplified check: ensure plots are within max_distance of roads
        # In practice, would check actual road connectivity
        
        violations = []
        for plot in layout.plots:
            if plot.type == PlotType.INDUSTRIAL:
                if not plot.has_road_access:
                    violations.append(f"Plot {plot.id} lacks road access")
        
        if violations:
            for v in violations:
                report.add_violation(v)
        else:
            report.add_pass("Road accessibility compliance")
    
    def _check_fire_safety_distances(self, layout: Layout, report: ComplianceReport):
        """Check fire safety distance requirements"""
        fire_distance = self.regulations['setbacks']['fire_safety_distance']
        
        # Check spacing between industrial plots
        industrial_plots = [p for p in layout.plots if p.type == PlotType.INDUSTRIAL]
        
        for i, plot1 in enumerate(industrial_plots):
            for plot2 in industrial_plots[i+1:]:
                distance = plot1.geometry.distance(plot2.geometry)
                if distance < fire_distance:
                    report.add_violation(
                        f"Plots {plot1.id} and {plot2.id} violate {fire_distance}m fire safety distance "
                        f"(actual: {distance:.1f}m)"
                    )
                    return
        
        report.add_pass("Fire safety distance compliance")
    
    def _check_no_overlaps(self, layout: Layout, report: ComplianceReport):
        """Check that no plots overlap"""
        plots = layout.plots
        
        for i, plot1 in enumerate(plots):
            for plot2 in plots[i+1:]:
                if plot1.geometry.intersects(plot2.geometry):
                    intersection = plot1.geometry.intersection(plot2.geometry)
                    if intersection.area > 0.01:  # Small tolerance for numerical errors
                        report.add_violation(
                            f"Plots {plot1.id} and {plot2.id} overlap by {intersection.area:.2f}m²"
                        )
                        return
        
        report.add_pass("No plot overlaps")
    
    def check_constraint_compliance(self, layout: Layout, constraints: List[Constraint]) -> ComplianceReport:
        """
        Check compliance against specific spatial constraints
        
        Args:
            layout: Layout to check
            constraints: List of spatial constraints
            
        Returns:
            ComplianceReport
        """
        report = ComplianceReport(
            layout_id=layout.id,
            is_compliant=True
        )
        
        for constraint in constraints:
            violations = self._check_single_constraint(layout, constraint)
            for v in violations:
                report.add_violation(v)
        
        return report
    
    def _check_single_constraint(self, layout: Layout, constraint: Constraint) -> List[str]:
        """Check a single constraint"""
        violations = []
        
        for plot in layout.plots:
            if plot.type == PlotType.INDUSTRIAL:
                if plot.geometry.intersects(constraint.geometry):
                    violations.append(
                        f"Plot {plot.id} violates {constraint.type.value} constraint: {constraint.description}"
                    )
        
        return violations


# Example usage
if __name__ == "__main__":
    from shapely.geometry import box
    from src.models.domain import SiteBoundary
    
    # Create example site and layout
    site_geom = box(0, 0, 500, 500)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm
    
    layout = Layout(site_boundary=site)
    
    # Add some example plots
    plot1 = Plot(
        geometry=box(60, 60, 150, 150),
        area_sqm=8100,
        type=PlotType.INDUSTRIAL,
        width_m=90,
        depth_m=90,
        has_road_access=True
    )
    
    plot2 = Plot(
        geometry=box(200, 60, 290, 150),
        area_sqm=8100,
        type=PlotType.INDUSTRIAL,
        width_m=90,
        depth_m=90,
        has_road_access=True
    )
    
    green_plot = Plot(
        geometry=box(60, 200, 150, 290),
        area_sqm=8100,
        type=PlotType.GREEN_SPACE
    )
    
    layout.plots = [plot1, plot2, green_plot]
    layout.calculate_metrics()
    
    # Check compliance
    checker = RegulationChecker()
    report = checker.validate_compliance(layout)
    
    print(f"Compliance: {report.is_compliant}")
    print(f"Violations: {len(report.violations)}")
    for v in report.violations:
        print(f"  - {v}")
    print(f"Warnings: {len(report.warnings)}")
    for w in report.warnings:
        print(f"  - {w}")
    print(f"Checks passed: {len(report.checks_passed)}")
    for c in report.checks_passed:
        print(f"  ✓ {c}")
