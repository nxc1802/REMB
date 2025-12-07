"""
Main land redistribution pipeline orchestration.

Coordinates all stages of the optimization pipeline:
1. Road network generation (Voronoi or Grid-based)
2. Block subdivision (OR-Tools)
3. Infrastructure planning (MST, Transformers, Drainage)
"""

import logging
import random
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
from shapely.geometry import Polygon, Point, mapping
from shapely.ops import unary_union

from core.config.settings import (
    AlgorithmSettings, 
    DEFAULT_SETTINGS,
    ROAD_MAIN_WIDTH,
    ROAD_INTERNAL_WIDTH,
    SIDEWALK_WIDTH,
    TURNING_RADIUS,
    SERVICE_AREA_RATIO,
    MIN_BLOCK_AREA,
)
from core.geometry.polygon_utils import (
    get_elevation,
    normalize_geometry_list,
    filter_by_min_area,
    sort_by_elevation,
)
from core.geometry.voronoi import (
    generate_voronoi_seeds,
    create_voronoi_diagram,
    extract_voronoi_edges,
    classify_road_type,
    create_road_buffer,
)
from core.optimization.grid_optimizer import GridOptimizer
from core.optimization.subdivision_solver import SubdivisionSolver
from core.infrastructure.network_planner import generate_loop_network
from core.infrastructure.transformer_planner import generate_transformers
from core.infrastructure.drainage_planner import calculate_drainage

logger = logging.getLogger(__name__)


class LandRedistributionPipeline:
    """
    Main pipeline orchestrating all optimization stages.
    
    Supports two modes:
    1. Voronoi-based road network (default, more organic layout)
    2. Grid-based optimization using NSGA-II (fallback)
    """
    
    def __init__(
        self, 
        land_polygons: List[Polygon], 
        config: Dict[str, Any],
        settings: Optional[AlgorithmSettings] = None
    ):
        """
        Initialize pipeline.
        
        Args:
            land_polygons: Input land plots
            config: API configuration dictionary
            settings: Algorithm settings (optional)
        """
        self.land_poly = unary_union(land_polygons)
        self.config = config
        self.settings = settings or AlgorithmSettings.from_dict(config)
        self.lake_poly = Polygon()  # No lake by default
        
        logger.info(f"Pipeline initialized with land area: {self.land_poly.area:.2f} m²")
    
    def generate_road_network(
        self, 
        num_seeds: int = 15
    ) -> Tuple[Polygon, List[Polygon], List[Polygon]]:
        """
        Generate road network using Voronoi diagram.
        
        Args:
            num_seeds: Number of Voronoi seed points
            
        Returns:
            (road_network, service_blocks, commercial_blocks)
        """
        site = self.land_poly
        
        # Generate Voronoi seeds
        seeds = generate_voronoi_seeds(site, num_seeds)
        
        # Create Voronoi diagram
        regions = create_voronoi_diagram(seeds, site)
        if regions is None:
            logger.warning("Voronoi generation failed, returning empty")
            return Polygon(), [], [site]
        
        # Extract edges
        edges = extract_voronoi_edges(regions)
        if not edges:
            return Polygon(), [], [site]
        
        # Create road buffers
        center = site.centroid
        road_polys = []
        
        for line in edges:
            road_type = classify_road_type(line, center)
            road_buffer = create_road_buffer(
                line, 
                road_type,
                main_width=ROAD_MAIN_WIDTH,
                internal_width=ROAD_INTERNAL_WIDTH,
                sidewalk_width=SIDEWALK_WIDTH
            )
            road_polys.append(road_buffer)
        
        if not road_polys:
            return Polygon(), [], [site]
        
        # Merge road network
        network_poly = unary_union(road_polys)
        
        # Apply turning radius smoothing
        smooth_network = network_poly.buffer(
            TURNING_RADIUS, join_style=1
        ).buffer(-TURNING_RADIUS, join_style=1)
        
        # Extract blocks (land minus roads)
        blocks_rough = site.difference(smooth_network)
        candidates = normalize_geometry_list(blocks_rough)
        
        # Filter by minimum area
        valid_blocks = filter_by_min_area(candidates, MIN_BLOCK_AREA)
        
        if not valid_blocks:
            return smooth_network, [], []
        
        # Sort by elevation (lowest first for WWTP)
        sorted_blocks = sort_by_elevation(valid_blocks)
        
        # Allocate service areas (10% of total)
        total_area = sum(b.area for b in valid_blocks)
        service_target = total_area * SERVICE_AREA_RATIO
        
        service_blocks = []
        commercial_blocks = []
        accumulated = 0.0
        
        for block in sorted_blocks:
            if accumulated < service_target:
                service_blocks.append(block)
                accumulated += block.area
            else:
                commercial_blocks.append(block)
        
        # Ensure at least one commercial block
        if not commercial_blocks and service_blocks:
            commercial_blocks.append(service_blocks.pop())
        
        logger.info(f"Road network: {len(service_blocks)} service, {len(commercial_blocks)} commercial blocks")
        return smooth_network, service_blocks, commercial_blocks
    
    def run_stage1(self) -> Dict[str, Any]:
        """Run grid optimization stage (NSGA-II)."""
        optimizer = GridOptimizer(self.land_poly, self.lake_poly)
        
        best_solution, history = optimizer.optimize(
            population_size=self.config.get('population_size', 30),
            generations=self.config.get('generations', 15)
        )
        
        spacing, angle = best_solution
        blocks = optimizer.generate_grid_candidates(spacing, angle)
        
        # Filter to usable blocks
        usable_blocks = []
        for blk in blocks:
            intersection = blk.intersection(self.land_poly).difference(self.lake_poly)
            if not intersection.is_empty:
                usable_blocks.append(intersection)
        
        return {
            'spacing': spacing,
            'angle': angle,
            'blocks': usable_blocks,
            'history': history,
            'metrics': {
                'total_blocks': len(usable_blocks),
                'optimal_spacing': spacing,
                'optimal_angle': angle
            }
        }
    
    def run_stage2(
        self, 
        blocks: List[Polygon], 
        spacing: float
    ) -> Dict[str, Any]:
        """Run subdivision stage (OR-Tools)."""
        all_lots = []
        parks = []
        
        for block in blocks:
            result = SubdivisionSolver.subdivide_block(
                block,
                spacing,
                self.config.get('min_lot_width', 20.0),
                self.config.get('max_lot_width', 80.0),
                self.config.get('target_lot_width', 40.0),
                self.config.get('ortools_time_limit', 5)
            )
            
            if result['type'] == 'park':
                parks.append(result['geometry'])
            else:
                all_lots.extend(result['lots'])
        
        avg_width = np.mean([lot['width'] for lot in all_lots]) if all_lots else 0
        
        return {
            'lots': all_lots,
            'parks': parks,
            'metrics': {
                'total_lots': len(all_lots),
                'total_parks': len(parks),
                'avg_lot_width': avg_width
            }
        }
    
    def classify_blocks(
        self, 
        blocks: List[Polygon]
    ) -> Dict[str, List[Polygon]]:
        """Classify blocks into service and commercial categories."""
        if not blocks:
            return {'service': [], 'commercial': [], 'xlnt': []}
        
        sorted_blocks = sort_by_elevation(blocks)
        
        total_area = sum(b.area for b in blocks)
        service_target = total_area * SERVICE_AREA_RATIO
        accumulated = 0.0
        
        xlnt_block = []
        service_blocks = []
        commercial_blocks = []
        
        # Lowest block is XLNT (Wastewater Treatment)
        if sorted_blocks:
            xlnt = sorted_blocks.pop(0)
            xlnt_block.append(xlnt)
            accumulated += xlnt.area
        
        # Fill remaining service quota
        for b in sorted_blocks:
            if accumulated < service_target:
                service_blocks.append(b)
                accumulated += b.area
            else:
                commercial_blocks.append(b)
        
        return {
            'xlnt': xlnt_block,
            'service': service_blocks,
            'commercial': commercial_blocks
        }
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run complete optimization pipeline with Voronoi road generation."""
        logger.info("Starting full pipeline...")
        
        # Stage 0: Voronoi Road Network
        road_network, service_blocks_voronoi, commercial_blocks_voronoi = \
            self.generate_road_network(num_seeds=15)
        
        # Fallback to grid-based if Voronoi fails
        if not commercial_blocks_voronoi:
            logger.info("Voronoi failed, using grid-based approach")
            stage1_result = self.run_stage1()
            classification = self.classify_blocks(stage1_result['blocks'])
            commercial_blocks_voronoi = classification['commercial']
            service_blocks_voronoi = classification['service']
            xlnt_blocks = classification['xlnt']
            all_blocks = stage1_result['blocks']
            road_network = self.land_poly.difference(unary_union(all_blocks))
            spacing_for_subdivision = stage1_result['spacing']
        else:
            # Separate XLNT from service blocks
            if service_blocks_voronoi:
                xlnt_blocks = [service_blocks_voronoi[0]]
                service_blocks_voronoi = service_blocks_voronoi[1:]
            else:
                xlnt_blocks = []
            
            # Estimate spacing for subdivision
            if commercial_blocks_voronoi:
                avg_area = sum(b.area for b in commercial_blocks_voronoi) / len(commercial_blocks_voronoi)
                spacing_for_subdivision = max(20.0, (avg_area ** 0.5) * 0.7)
            else:
                spacing_for_subdivision = 25.0
        
        # Stage 2: Subdivision
        stage2_result = self.run_stage2(
            commercial_blocks_voronoi,
            spacing_for_subdivision
        )
        
        # Collect all polygons for infrastructure
        all_network_nodes = stage2_result['lots'] + \
            [{'geometry': b, 'type': 'service'} for b in service_blocks_voronoi] + \
            [{'geometry': b, 'type': 'xlnt'} for b in xlnt_blocks]
        
        infra_polys = [item['geometry'] for item in all_network_nodes]
        
        # Stage 3: Infrastructure
        points, connections = generate_loop_network(infra_polys)
        transformers = generate_transformers(infra_polys)
        
        wwtp_center = xlnt_blocks[0].centroid if xlnt_blocks else None
        drainage = calculate_drainage(infra_polys, wwtp_center)
        
        logger.info(f"Pipeline complete: {len(stage2_result['lots'])} lots, {len(connections)} connections")
        
        return {
            'stage1': {
                'blocks': commercial_blocks_voronoi + service_blocks_voronoi + xlnt_blocks,
                'metrics': {
                    'total_blocks': len(commercial_blocks_voronoi) + len(service_blocks_voronoi) + len(xlnt_blocks)
                },
                'spacing': spacing_for_subdivision,
                'angle': 0.0
            },
            'stage2': stage2_result,
            'classification': {
                'xlnt_count': len(xlnt_blocks),
                'service_count': len(service_blocks_voronoi),
                'commercial_count': len(commercial_blocks_voronoi),
                'xlnt': xlnt_blocks,
                'service': service_blocks_voronoi
            },
            'stage3': {
                'points': points,
                'connections': [list(line.coords) for line in connections],
                'drainage': drainage,
                'transformers': transformers,
                'road_network': mapping(road_network)
            },
            'total_lots': stage2_result['metrics']['total_lots'],
            'service_blocks': [list(b.exterior.coords) for b in service_blocks_voronoi],
            'xlnt_blocks': [list(b.exterior.coords) for b in xlnt_blocks]
        }
