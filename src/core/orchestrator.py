"""
Core Orchestrator - The Brain/Nhạc trưởng
Coordinates between LLM understanding and CP Module execution
Following the "Handshake Loop" pattern from Core_document.md
"""
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

from src.models.domain import Layout, SiteBoundary, Plot, ParetoFront, ComplianceReport
from src.algorithms.nsga2_optimizer import NSGA2Optimizer
from src.algorithms.milp_solver import MILPSolver, MILPResult
from src.algorithms.regulation_checker import RegulationChecker
from src.geometry.site_processor import SiteProcessor
from src.geometry.road_network import RoadNetworkGenerator
from src.geometry.plot_generator import PlotGenerator
from src.export.dxf_exporter import DXFExporter

logger = logging.getLogger(__name__)


class OrchestrationStatus(str, Enum):
    """Status of orchestration step"""
    SUCCESS = "success"
    FAILURE = "failure"
    CONFLICT = "conflict"
    PENDING = "pending"


@dataclass
class OrchestrationResult:
    """Result from orchestration step"""
    status: OrchestrationStatus
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)  # For conflict resolution
    
    def to_json(self) -> str:
        """Convert to JSON for LLM interpretation"""
        return json.dumps({
            'status': self.status.value,
            'message': self.message,
            'data': self.data,
            'suggestions': self.suggestions
        }, indent=2, default=str)


class CoreOrchestrator:
    """
    Core Orchestrator - The central coordinator
    
    Implements the "Handshake Loop" pattern:
    1. Dịch (Translation): Convert natural language to technical parameters
    2. Giải (Execution): Run CP Module algorithms
    3. Hiểu (Interpretation): Evaluate results against requirements
    4. Quyết định (Reasoning & Action): Report success or propose alternatives
    
    Key principle: LLM handles semantics, CP handles math
    - All numbers come from CP (no hallucination)
    - LLM provides flexibility in input/output
    """
    
    def __init__(self, regulations_path: str = "config/regulations.yaml"):
        """
        Initialize orchestrator with all modules
        
        Args:
            regulations_path: Path to regulations YAML
        """
        self.regulations_path = regulations_path
        
        # Initialize all modules
        self.site_processor = SiteProcessor(regulations_path)
        self.road_generator = RoadNetworkGenerator(regulations_path)
        self.plot_generator = PlotGenerator(regulations_path)
        self.nsga2_optimizer = NSGA2Optimizer(regulations_path)
        self.milp_solver = MILPSolver()
        self.regulation_checker = RegulationChecker(regulations_path)
        self.dxf_exporter = DXFExporter()
        
        self.logger = logging.getLogger(__name__)
        
        # Current session state
        self.current_site: Optional[SiteBoundary] = None
        self.current_layouts: List[Layout] = []
        self.current_pareto: Optional[ParetoFront] = None
    
    # =========================================================================
    # STAGE 1: Digital Twin Initialization (Dịch + Giải)
    # =========================================================================
    
    def initialize_site(
        self,
        source: str,
        source_type: str = "coordinates"
    ) -> OrchestrationResult:
        """
        Initialize site from various sources
        
        Args:
            source: File path or coordinate string
            source_type: 'shapefile', 'geojson', 'dxf', 'coordinates'
            
        Returns:
            OrchestrationResult
        """
        self.logger.info(f"Initializing site from {source_type}")
        
        try:
            # Dịch (Translation): Parse input based on type
            if source_type == "shapefile":
                self.current_site = self.site_processor.import_from_shapefile(source)
            elif source_type == "geojson":
                self.current_site = self.site_processor.import_from_geojson(source)
            elif source_type == "dxf":
                self.current_site = self.site_processor.import_from_dxf(source)
            elif source_type == "coordinates":
                # Parse coordinates from string or list
                if isinstance(source, str):
                    coords = json.loads(source)
                else:
                    coords = source
                self.current_site = self.site_processor.import_from_coordinates(coords)
            else:
                return OrchestrationResult(
                    status=OrchestrationStatus.FAILURE,
                    message=f"Unknown source type: {source_type}"
                )
            
            # Giải (Execution): Site processor has calculated buildable area
            
            # Hiểu (Interpretation): Check if site is valid
            if self.current_site.buildable_area_sqm <= 0:
                return OrchestrationResult(
                    status=OrchestrationStatus.CONFLICT,
                    message="Site too small after applying setbacks",
                    suggestions=[
                        "Reduce boundary setback requirement",
                        "Choose a larger site",
                        "Apply for variance permit"
                    ]
                )
            
            # Quyết định: Success
            return OrchestrationResult(
                status=OrchestrationStatus.SUCCESS,
                message="Site initialized successfully",
                data={
                    'site_id': self.current_site.id,
                    'total_area_sqm': self.current_site.area_sqm,
                    'buildable_area_sqm': self.current_site.buildable_area_sqm,
                    'buildable_ratio': self.current_site.buildable_area_sqm / self.current_site.area_sqm,
                    'num_constraints': len(self.current_site.constraints)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Site initialization failed: {e}")
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Failed to initialize site: {str(e)}"
            )
    
    # =========================================================================
    # STAGE 2: Infrastructure Skeleton (Dịch + Giải)
    # =========================================================================
    
    def generate_road_network(
        self,
        pattern: str = "grid",
        primary_spacing: float = 200,
        secondary_spacing: float = 100
    ) -> OrchestrationResult:
        """
        Generate road network
        
        Args:
            pattern: 'grid' or 'spine'
            primary_spacing: Primary road spacing
            secondary_spacing: Secondary road spacing
            
        Returns:
            OrchestrationResult
        """
        if not self.current_site:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message="No site initialized. Call initialize_site first."
            )
        
        self.logger.info(f"Generating {pattern} road network")
        
        try:
            # Giải (Execution): Generate road network
            if pattern == "spine":
                road_network = self.road_generator.generate_spine_network(self.current_site)
            else:
                road_network = self.road_generator.generate_grid_network(
                    self.current_site,
                    primary_spacing=primary_spacing,
                    secondary_spacing=secondary_spacing
                )
            
            # Check for dead zones
            dead_zones = self.road_generator.identify_dead_zones(
                self.current_site, road_network
            )
            
            # Hiểu (Interpretation)
            if dead_zones:
                dead_area = sum(z.area for z in dead_zones)
                if dead_area > self.current_site.buildable_area_sqm * 0.1:
                    return OrchestrationResult(
                        status=OrchestrationStatus.CONFLICT,
                        message=f"Road network leaves {len(dead_zones)} dead zones ({dead_area:.0f}m²)",
                        data={'road_network': road_network, 'dead_zones': len(dead_zones)},
                        suggestions=[
                            f"Try pattern='grid' with smaller spacing",
                            f"Add more secondary roads",
                            f"Accept dead zones as green space"
                        ]
                    )
            
            # Store road network in site for later use
            self._current_road_network = road_network
            
            return OrchestrationResult(
                status=OrchestrationStatus.SUCCESS,
                message="Road network generated successfully",
                data={
                    'total_length_m': road_network.total_length_m,
                    'total_area_sqm': road_network.total_area_sqm,
                    'dead_zones': len(dead_zones) if dead_zones else 0,
                    'pattern': pattern
                }
            )
            
        except Exception as e:
            self.logger.error(f"Road network generation failed: {e}")
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Failed to generate road network: {str(e)}"
            )
    
    # =========================================================================
    # STAGE 3: Constraint Mapping (Dịch + Giải)
    # =========================================================================
    
    def add_constraint(
        self,
        constraint_type: str,
        description: str,
        geometry: Any,
        buffer_m: float = 0
    ) -> OrchestrationResult:
        """
        Add a constraint to the site
        
        Natural language examples that LLM would translate:
        - "Tránh kho xăng 200m" -> constraint_type="hazard", buffer_m=200
        - "Cách sông 100m" -> constraint_type="waterway", buffer_m=100
        
        Args:
            constraint_type: Type of constraint
            description: Human-readable description
            geometry: Constraint geometry (coordinates or polygon)
            buffer_m: Buffer distance in meters
            
        Returns:
            OrchestrationResult
        """
        if not self.current_site:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message="No site initialized"
            )
        
        try:
            from src.models.domain import ConstraintType
            
            # Dịch (Translation): Map string to enum
            type_map = {
                'setback': ConstraintType.SETBACK,
                'fire_safety': ConstraintType.FIRE_SAFETY,
                'waterway': ConstraintType.WATERWAY,
                'hazard': ConstraintType.HAZARD_ZONE,
                'no_build': ConstraintType.NO_BUILD
            }
            
            constraint_enum = type_map.get(constraint_type.lower(), ConstraintType.NO_BUILD)
            
            # Giải (Execution)
            constraint = self.site_processor.add_constraint(
                self.current_site,
                constraint_enum,
                geometry,
                buffer_distance=buffer_m,
                description=description
            )
            
            # Hiểu (Interpretation)
            if self.current_site.buildable_area_sqm <= 0:
                return OrchestrationResult(
                    status=OrchestrationStatus.CONFLICT,
                    message="Site no longer has buildable area after constraint",
                    suggestions=[
                        "Reduce buffer distance",
                        "Move constraint location",
                        "Request exemption"
                    ]
                )
            
            return OrchestrationResult(
                status=OrchestrationStatus.SUCCESS,
                message=f"Constraint added: {description}",
                data={
                    'constraint_type': constraint_type,
                    'buffer_m': buffer_m,
                    'remaining_buildable_sqm': self.current_site.buildable_area_sqm
                }
            )
            
        except Exception as e:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Failed to add constraint: {str(e)}"
            )
    
    # =========================================================================
    # STAGE 4: Automated Optimization (Hybrid AI: GA + MILP)
    # =========================================================================
    
    def run_optimization(
        self,
        population_size: int = 100,
        n_generations: int = 200,
        n_plots: int = 20
    ) -> OrchestrationResult:
        """
        Run full optimization pipeline (NSGA-II + MILP + Compliance)
        
        This is the core of the "Handshake Loop" - multiple iterations
        between GA exploration and MILP validation.
        
        Args:
            population_size: NSGA-II population size
            n_generations: Number of GA generations
            n_plots: Target number of plots
            
        Returns:
            OrchestrationResult with Pareto front
        """
        if not self.current_site:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message="No site initialized"
            )
        
        self.logger.info("Starting optimization pipeline")
        
        try:
            # STEP 1: NSGA-II Exploration (Giải)
            self.logger.info("Step 1: NSGA-II multi-objective optimization")
            pareto_front = self.nsga2_optimizer.optimize(
                site_boundary=self.current_site,
                population_size=population_size,
                n_generations=n_generations,
                n_plots=n_plots
            )
            
            if not pareto_front.layouts:
                return OrchestrationResult(
                    status=OrchestrationStatus.FAILURE,
                    message="NSGA-II failed to generate valid layouts",
                    suggestions=[
                        "Reduce number of plots",
                        "Relax constraints",
                        "Check site configuration"
                    ]
                )
            
            # STEP 2: MILP Validation for each layout (Giải)
            self.logger.info("Step 2: MILP validation")
            validated_layouts = []
            
            for layout in pareto_front.layouts:
                refined_layout, milp_result = self.milp_solver.validate_and_refine(layout)
                
                if milp_result.is_success():
                    validated_layouts.append(refined_layout)
            
            if not validated_layouts:
                return OrchestrationResult(
                    status=OrchestrationStatus.CONFLICT,
                    message="No layouts passed MILP validation",
                    data={'original_count': len(pareto_front.layouts)},
                    suggestions=[
                        "Reduce plot density",
                        "Increase road network",
                        "Review constraint compatibility"
                    ]
                )
            
            # STEP 3: Regulatory Compliance Check (Giải)
            self.logger.info("Step 3: Regulatory compliance check")
            compliant_layouts = []
            violations_summary = []
            
            for layout in validated_layouts:
                report = self.regulation_checker.validate_compliance(layout)
                layout.metrics.is_compliant = report.is_compliant
                layout.metrics.compliance_violations = report.violations
                
                if report.is_compliant:
                    compliant_layouts.append(layout)
                else:
                    violations_summary.extend(report.violations[:2])  # Top 2 violations
            
            # Hiểu (Interpretation) + Quyết định (Reasoning)
            if not compliant_layouts:
                return OrchestrationResult(
                    status=OrchestrationStatus.CONFLICT,
                    message="No layouts meet regulatory compliance",
                    data={
                        'validated_count': len(validated_layouts),
                        'sample_violations': violations_summary[:5]
                    },
                    suggestions=[
                        "Increase green space ratio",
                        "Review boundary setbacks",
                        "Reduce plot density"
                    ]
                )
            
            # Success - store Pareto front
            self.current_pareto = ParetoFront(
                layouts=compliant_layouts,
                generation_time_seconds=pareto_front.generation_time_seconds
            )
            self.current_layouts = compliant_layouts
            
            # Generate summary
            max_sellable = self.current_pareto.get_max_sellable_layout()
            max_green = self.current_pareto.get_max_green_layout()
            balanced = self.current_pareto.get_balanced_layout()
            
            return OrchestrationResult(
                status=OrchestrationStatus.SUCCESS,
                message=f"Generated {len(compliant_layouts)} compliant layouts",
                data={
                    'num_layouts': len(compliant_layouts),
                    'generation_time_seconds': pareto_front.generation_time_seconds,
                    'max_sellable_area': max_sellable.metrics.sellable_area_sqm if max_sellable else 0,
                    'max_green_ratio': max_green.metrics.green_space_ratio if max_green else 0,
                    'balanced_sellable': balanced.metrics.sellable_area_sqm if balanced else 0,
                    'scenarios': [
                        {
                            'name': 'Max Sellable',
                            'id': max_sellable.id if max_sellable else None,
                            'sellable_sqm': max_sellable.metrics.sellable_area_sqm if max_sellable else 0
                        },
                        {
                            'name': 'Max Green',
                            'id': max_green.id if max_green else None,
                            'green_ratio': max_green.metrics.green_space_ratio if max_green else 0
                        },
                        {
                            'name': 'Balanced',
                            'id': balanced.id if balanced else None
                        }
                    ]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Optimization pipeline failed: {str(e)}"
            )
    
    # =========================================================================
    # STAGE 5: Engineering Delivery (Giải + Output)
    # =========================================================================
    
    def export_layout(
        self,
        layout_id: str,
        output_path: str,
        format: str = "dxf"
    ) -> OrchestrationResult:
        """
        Export a specific layout to file
        
        Args:
            layout_id: Layout ID to export
            output_path: Output file path
            format: Export format ('dxf')
            
        Returns:
            OrchestrationResult
        """
        # Find layout
        layout = None
        for l in self.current_layouts:
            if l.id == layout_id:
                layout = l
                break
        
        if not layout:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Layout not found: {layout_id}"
            )
        
        try:
            if format.lower() == "dxf":
                filepath = self.dxf_exporter.export(layout, output_path)
                return OrchestrationResult(
                    status=OrchestrationStatus.SUCCESS,
                    message=f"Layout exported to {filepath}",
                    data={'filepath': filepath, 'format': 'DXF'}
                )
            else:
                return OrchestrationResult(
                    status=OrchestrationStatus.FAILURE,
                    message=f"Unsupported format: {format}"
                )
                
        except Exception as e:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Export failed: {str(e)}"
            )
    
    def export_all_layouts(self, output_dir: str) -> OrchestrationResult:
        """
        Export all layouts in Pareto front
        
        Args:
            output_dir: Output directory
            
        Returns:
            OrchestrationResult
        """
        if not self.current_pareto:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message="No optimization results available"
            )
        
        try:
            files = self.dxf_exporter.export_pareto_front(
                self.current_pareto,
                output_dir,
                prefix="layout"
            )
            
            return OrchestrationResult(
                status=OrchestrationStatus.SUCCESS,
                message=f"Exported {len(files)} layouts",
                data={'files': files}
            )
            
        except Exception as e:
            return OrchestrationResult(
                status=OrchestrationStatus.FAILURE,
                message=f"Export failed: {str(e)}"
            )
    
    # =========================================================================
    # JSON Interface for LLM Function Calling
    # =========================================================================
    
    def execute_command(self, command_json: str) -> str:
        """
        Execute a command from LLM via JSON
        
        This is the standardized interface for LLM → Orchestrator communication.
        
        Input format:
        {
            "action": "initialize_site" | "generate_roads" | "add_constraint" | "optimize" | "export",
            "parameters": {...}
        }
        
        Args:
            command_json: JSON command string
            
        Returns:
            JSON response string
        """
        try:
            command = json.loads(command_json)
            action = command.get('action')
            params = command.get('parameters', {})
            
            if action == 'initialize_site':
                result = self.initialize_site(**params)
            elif action == 'generate_roads':
                result = self.generate_road_network(**params)
            elif action == 'add_constraint':
                result = self.add_constraint(**params)
            elif action == 'optimize':
                result = self.run_optimization(**params)
            elif action == 'export':
                result = self.export_layout(**params)
            elif action == 'export_all':
                result = self.export_all_layouts(**params)
            else:
                result = OrchestrationResult(
                    status=OrchestrationStatus.FAILURE,
                    message=f"Unknown action: {action}"
                )
            
            return result.to_json()
            
        except json.JSONDecodeError as e:
            return json.dumps({
                'status': 'failure',
                'message': f'Invalid JSON: {str(e)}'
            })
        except Exception as e:
            return json.dumps({
                'status': 'failure',
                'message': f'Execution error: {str(e)}'
            })


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize orchestrator
    orchestrator = CoreOrchestrator()
    
    # Stage 1: Initialize site
    coords = [(0, 0), (500, 0), (500, 500), (0, 500), (0, 0)]
    result = orchestrator.initialize_site(coords, source_type="coordinates")
    print(f"Site init: {result.status.value}")
    print(result.to_json())
    
    # Stage 2: Generate roads
    result = orchestrator.generate_road_network(pattern="grid", primary_spacing=150)
    print(f"\nRoad gen: {result.status.value}")
    
    # Stage 4: Run optimization
    result = orchestrator.run_optimization(
        population_size=50,
        n_generations=50,
        n_plots=10
    )
    print(f"\nOptimization: {result.status.value}")
    print(result.to_json())
    
    # Stage 5: Export
    if result.status == OrchestrationStatus.SUCCESS:
        result = orchestrator.export_all_layouts("output/")
        print(f"\nExport: {result.status.value}")
