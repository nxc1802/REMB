"""Main orchestration pipeline for procedural generation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from shapely.geometry import Polygon, LineString

from core.road_network import generate_road_network
from core.subdivision import subdivide_site
from core.post_processing import generate_sidewalks
from core.geometry import analyze_shape_quality


@dataclass
class PipelineConfig:
    """Configuration for the procedural pipeline."""
    # Road generation
    road_algorithm: str = 'skeleton'  # 'skeleton', 'l_systems', 'hybrid'
    road_fillet_radius: float = 12.0
    
    # Subdivision
    min_lot_area: float = 1000.0
    max_lot_area: float = 10000.0
    target_lot_width: float = 40.0
    
    # Post-processing
    sidewalk_width: float = 2.0
    green_buffer_width: float = 5.0
    
    # Quality (relaxed thresholds for procedural generation)
    min_rectangularity: float = 0.60
    max_aspect_ratio: float = 6.0


@dataclass
class PipelineResult:
    """Result from pipeline execution."""
    roads: List[LineString] = field(default_factory=list)
    lots: List[Polygon] = field(default_factory=list)
    sidewalks: List[Polygon] = field(default_factory=list)
    green_spaces: List[Polygon] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProceduralPipeline:
    """Main pipeline orchestrating all generation stages.
    
    Stages:
    1. Road Network Generation
    2. Block Division (by roads)
    3. Lot Subdivision
    4. Quality Filtering
    5. Post-Processing (sidewalks, buffers)
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.intermediate_results: Dict[str, Any] = {}
        
    def run_full(self, site_boundary: Polygon) -> PipelineResult:
        """Run complete procedural generation pipeline.
        
        Args:
            site_boundary: Site boundary polygon
            
        Returns:
            PipelineResult with all generated elements
        """
        result = PipelineResult()
        
        # Stage 1: Road Network
        result.roads = self.stage_road_network(site_boundary)
        self.intermediate_results['roads'] = result.roads
        
        # Stage 2 & 3: Block Division + Lot Subdivision
        lots, green_spaces = self.stage_subdivision(site_boundary, result.roads)
        
        # Stage 4: Quality Filter
        result.lots, additional_green = self.stage_quality_filter(lots)
        result.green_spaces = green_spaces + additional_green
        
        # Stage 5: Post-Processing
        result.sidewalks = self.stage_post_processing(result.roads)
        
        # Compute metadata
        result.metadata = {
            'config': {
                'road_algorithm': self.config.road_algorithm,
                'min_lot_area': self.config.min_lot_area,
                'target_lot_width': self.config.target_lot_width
            },
            'stats': {
                'road_count': len(result.roads),
                'road_total_length': sum(r.length for r in result.roads),
                'lot_count': len(result.lots),
                'lot_total_area': sum(l.area for l in result.lots),
                'green_count': len(result.green_spaces),
                'green_total_area': sum(g.area for g in result.green_spaces),
                'sidewalk_count': len(result.sidewalks)
            }
        }
        
        return result
        
    def stage_road_network(self, site: Polygon) -> List[LineString]:
        """Stage 1: Generate road network."""
        return generate_road_network(
            site_boundary=site,
            algorithm=self.config.road_algorithm,
            fillet_radius=self.config.road_fillet_radius
        )
        
    def stage_subdivision(
        self, 
        site: Polygon, 
        roads: List[LineString]
    ) -> tuple:
        """Stage 2 & 3: Divide site and subdivide into lots."""
        return subdivide_site(
            site_boundary=site,
            roads=roads,
            min_lot_area=self.config.min_lot_area,
            max_lot_area=self.config.max_lot_area
        )
        
    def stage_quality_filter(
        self, 
        lots: List[Polygon]
    ) -> tuple:
        """Stage 4: Filter lots by quality."""
        good_lots = []
        green_spaces = []
        
        for lot in lots:
            score, is_valid = analyze_shape_quality(
                lot,
                min_rectangularity=self.config.min_rectangularity,
                max_aspect_ratio=self.config.max_aspect_ratio,
                min_area=self.config.min_lot_area
            )
            
            if is_valid:
                good_lots.append(lot)
            else:
                green_spaces.append(lot)
                
        return good_lots, green_spaces
        
    def stage_post_processing(
        self, 
        roads: List[LineString]
    ) -> List[Polygon]:
        """Stage 5: Add sidewalks and buffers."""
        return generate_sidewalks(
            roads, 
            width=self.config.sidewalk_width
        )


# Convenience function
def run_procedural_generation(
    site_boundary: Polygon,
    config: Optional[PipelineConfig] = None
) -> PipelineResult:
    """Run procedural generation with default or custom config.
    
    Args:
        site_boundary: Site boundary polygon
        config: Optional pipeline configuration
        
    Returns:
        PipelineResult with all generated elements
    """
    pipeline = ProceduralPipeline(config)
    return pipeline.run_full(site_boundary)
