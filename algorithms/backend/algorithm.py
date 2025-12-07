"""Core land redistribution algorithm implementation.

This module contains the exact algorithm logic from algo.ipynb for:
- Stage 1: Grid optimization using NSGA-II genetic algorithm
- Stage 2: Block subdivision using OR-Tools
- Stage 3: Infrastructure planning
"""

import random
import numpy as np
from typing import List, Tuple, Dict, Any
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint, mapping
from shapely.affinity import translate, rotate
from deap import base, creator, tools, algorithms
from ortools.sat.python import cp_model
import networkx as nx
from scipy.spatial.distance import pdist, squareform
from scipy.sparse.csgraph import minimum_spanning_tree
from sklearn.cluster import KMeans
from shapely.ops import unary_union, voronoi_diagram


class GridOptimizer:
    """Stage 1: Optimize grid layout using NSGA-II genetic algorithm."""
    
    def __init__(self, land_polygon: Polygon, lake_polygon: Polygon = None):
        """
        Initialize grid optimizer.
        
        Args:
            land_polygon: Main land boundary
            lake_polygon: Water body to exclude (optional)
        """
        self.land_poly = land_polygon
        self.lake_poly = lake_polygon or Polygon()
        
        # Setup DEAP genetic algorithm
        self._setup_deap()
    
    def _setup_deap(self):
        """Configure DEAP toolbox for multi-objective optimization."""
        # Create fitness and individual classes
        if not hasattr(creator, "FitnessMulti"):
            creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0))  # Max area, Min fragments
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMulti)
        
        self.toolbox = base.Toolbox()
        # Gene 1: Block spacing (20m - 40m)
        self.toolbox.register("attr_spacing", random.uniform, 20, 40)
        # Gene 2: Rotation angle (0 - 90 degrees)
        self.toolbox.register("attr_angle", random.uniform, 0, 90)
        
        self.toolbox.register("individual", tools.initCycle, creator.Individual,
                             (self.toolbox.attr_spacing, self.toolbox.attr_angle), n=1)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        self.toolbox.register("evaluate", self._evaluate_layout)
        self.toolbox.register("mate", tools.cxSimulatedBinaryBounded, low=[20, 0], up=[40, 90], eta=20.0)
        self.toolbox.register("mutate", tools.mutPolynomialBounded, low=[20, 0], up=[40, 90], eta=20.0, indpb=0.2)
        self.toolbox.register("select", tools.selNSGA2)
    
    def generate_grid_candidates(self, spacing: float, angle_deg: float) -> List[Polygon]:
        """
        Generate grid blocks at given spacing and rotation.
        
        Args:
            spacing: Grid spacing in meters
            angle_deg: Rotation angle in degrees
            
        Returns:
            List of block polygons
        """
        minx, miny, maxx, maxy = self.land_poly.bounds
        diameter = ((maxx - minx)**2 + (maxy - miny)**2)**0.5
        center = self.land_poly.centroid
        
        # Create grid ranges
        x_range = np.arange(minx - diameter, maxx + diameter, spacing)
        y_range = np.arange(miny - diameter, maxy + diameter, spacing)
        
        blocks = []
        
        # Create base block at origin
        base_block = Polygon([(0, 0), (spacing, 0), (spacing, spacing), (0, spacing)])
        base_block = translate(base_block, -spacing/2, -spacing/2)
        
        for x in x_range:
            for y in y_range:
                # Translate and rotate block
                poly = translate(base_block, x, y)
                poly = rotate(poly, angle_deg, origin=center)
                
                # Only keep blocks that intersect land
                if poly.intersects(self.land_poly):
                    blocks.append(poly)
        
        return blocks
    
    def _evaluate_layout(self, individual: List[float]) -> Tuple[float, int]:
        """
        Evaluate layout fitness.
        
        Objectives:
        1. Maximize residential area
        2. Minimize fragmented blocks
        
        Args:
            individual: [spacing, angle]
            
        Returns:
            (total_residential_area, fragmented_blocks)
        """
        spacing, angle = individual
        blocks = self.generate_grid_candidates(spacing, angle)
        
        total_residential_area = 0
        fragmented_blocks = 0
        
        for blk in blocks:
            # Cut with land boundary
            intersection = blk.intersection(self.land_poly)
            if intersection.is_empty:
                continue
            
            # Subtract lake
            usable_part = intersection.difference(self.lake_poly)
            if usable_part.is_empty:
                continue
            
            # Calculate area ratio
            original_area = spacing * spacing
            actual_area = usable_part.area
            ratio = actual_area / original_area
            
            # Classify block quality
            if ratio > 0.65:
                # Good block for residential
                total_residential_area += actual_area
            elif ratio > 0.1:
                # Fragmented block (penalize)
                fragmented_blocks += 1
        
        return (total_residential_area, fragmented_blocks)
    
    def optimize(self, population_size: int = 30, generations: int = 15) -> Tuple[List[float], List[List[float]]]:
        """
        Run NSGA-II optimization.
        
        Args:
            population_size: Population size
            generations: Number of generations
            
        Returns:
            (best_solution, history)
        """
        random.seed(42)
        pop = self.toolbox.population(n=population_size)
        
        history = []
        
        # Initial evaluation
        fits = list(map(self.toolbox.evaluate, pop))
        for ind, fit in zip(pop, fits):
            ind.fitness.values = fit
        
        # Save best from generation 0
        best_ind = tools.selBest(pop, 1)[0]
        history.append(list(best_ind))
        
        # Evolution
        for gen in range(generations):
            offspring = algorithms.varAnd(pop, self.toolbox, cxpb=0.7, mutpb=0.3)
            fits = list(map(self.toolbox.evaluate, offspring))
            for ind, fit in zip(offspring, fits):
                ind.fitness.values = fit
            pop = self.toolbox.select(pop + offspring, k=len(pop))
            
            # Save best from each generation
            best_ind = tools.selBest(pop, 1)[0]
            history.append(list(best_ind))
        
        final_best = tools.selBest(pop, 1)[0]
        return list(final_best), history


class SubdivisionSolver:
    """Stage 2: Optimize block subdivision using OR-Tools."""
    
    @staticmethod
    def solve_subdivision(total_length: float, min_width: float, max_width: float, 
                         target_width: float, time_limit: float = 5.0) -> List[float]:
        """
        Solve optimal lot widths using constraint programming.
        
        Args:
            total_length: Total length to subdivide
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            time_limit: Solver time limit in seconds
            
        Returns:
            List of lot widths
        """
        # Safety check: prevent division by zero
        if total_length <= 0 or min_width <= 0 or total_length < min_width:
            return []
        
        model = cp_model.CpModel()
        
        # Estimate number of lots
        max_lots = int(total_length / min_width) + 1
        
        # Decision variables: lot widths (scaled to integers)
        scale = 100  # 1cm precision
        lot_vars = [model.NewIntVar(int(min_width * scale), int(max_width * scale), f'lot_{i}')
                    for i in range(max_lots)]
        
        # Used lot indicators
        used = [model.NewBoolVar(f'used_{i}') for i in range(max_lots)]
        
        # Constraints
        # Sum of widths must equal total length
        model.Add(sum(lot_vars[i] for i in range(max_lots)) == int(total_length * scale))
        
        # Lot ordering (if used, previous must be used)
        for i in range(1, max_lots):
            model.Add(used[i] <= used[i-1])
        
        # Connect lot values to usage
        for i in range(max_lots):
            model.Add(lot_vars[i] >= int(min_width * scale)).OnlyEnforceIf(used[i])
            model.Add(lot_vars[i] == 0).OnlyEnforceIf(used[i].Not())
        
        # Minimize deviation from target
        deviations = [model.NewIntVar(0, int((max_width - min_width) * scale), f'dev_{i}')
                     for i in range(max_lots)]
        
        target_scaled = int(target_width * scale)
        for i in range(max_lots):
            model.AddAbsEquality(deviations[i], lot_vars[i] - target_scaled)
        
        model.Minimize(sum(deviations))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        status = solver.Solve(model)
        
        # Extract solution
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            widths = []
            for i in range(max_lots):
                if solver.Value(used[i]):
                    widths.append(solver.Value(lot_vars[i]) / scale)
            return widths
        else:
            # Fallback: uniform division
            num_lots = int(total_length / target_width)
            return [total_length / num_lots] * num_lots
    
    @staticmethod
    def subdivide_block(block_geom: Polygon, spacing: float, min_width: float, 
                       max_width: float, target_width: float, time_limit: float = 5.0) -> Dict[str, Any]:
        """
        Subdivide a block into lots.
        
        Args:
            block_geom: Block geometry
            spacing: Grid spacing
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            setback: Setback distance in meters (default 6.0)
            
        Returns:
            Dictionary with subdivision info
        """
        # Determine block quality
        original_area = spacing * spacing
        current_area = block_geom.area
        ratio = current_area / original_area
        
        result = {
            'geometry': block_geom,
            'type': 'unknown',
            'lots': []
        }
        
        # Fragmented blocks become parks
        if ratio < 0.6:
            result['type'] = 'park'
            return result
        
        # Good blocks become residential
        result['type'] = 'residential'
        
        # Solve subdivision
        minx, miny, maxx, maxy = block_geom.bounds
        total_width = maxx - minx
        
        lot_widths = SubdivisionSolver.solve_subdivision(
            total_width, min_width, max_width, target_width, time_limit
        )
        
        # Create lot geometries
        current_x = minx
        setback_dist = 6.0 # Default setback
        
        for width in lot_widths:
            lot_poly = Polygon([
                (current_x, miny),
                (current_x + width, miny),
                (current_x + width, maxy),
                (current_x, maxy)
            ])
            # Clip to block
            clipped = lot_poly.intersection(block_geom)
            if not clipped.is_empty:
                # Calculate setback (buildable area)
                buildable = clipped.buffer(-setback_dist)
                if buildable.is_empty:
                    buildable = None
                    
                result['lots'].append({
                    'geometry': clipped,
                    'width': width,
                    'buildable': buildable
                })
            current_x += width
        
        return result


class InfrastructurePlanner:
    """Stage 3: Plan infrastructure network."""
    
    @staticmethod
    def get_elevation(x: float, y: float) -> float:
        """Simulate elevation (sloping from NW to SE)."""
        return 50.0 - (x * 0.02) - (y * 0.03)

    def generate_network(lots: List[Polygon]) -> Tuple[List[Tuple[float, float]], List[LineString]]:
        """
        Generate Loop Network for electrical infrastructure (MST + 15% redundancy).
        Matches notebook's create_loop_network function.
        
        Args:
            lots: List of lot polygons
            
        Returns:
            (points, connection_lines)
        """
        if len(lots) < 2:
            return [], []
            
        centroids = [lot.centroid for lot in lots]
        points = np.array([(p.x, p.y) for p in centroids])
        
        # 1. Create full graph with all nearby connections
        G = nx.Graph()
        for i, p in enumerate(centroids):
            G.add_node(i, pos=(p.x, p.y))
        
        # Add edges for all pairs within 500m
        for i in range(len(centroids)):
            for j in range(i+1, len(centroids)):
                dist = centroids[i].distance(centroids[j])
                if dist < 500:
                    G.add_edge(i, j, weight=dist)
        
        # 2. Create MST (Minimum Spanning Tree)
        if not nx.is_connected(G):
            # Handle disconnected graph - use largest component
            components = list(nx.connected_components(G))
            largest_comp = max(components, key=len)
            subgraph = G.subgraph(largest_comp).copy()
            mst = nx.minimum_spanning_tree(subgraph)
        else:
            mst = nx.minimum_spanning_tree(G)
        
        # 3. CREATE LOOP: Add back 15% of edges for redundancy (safety)
        all_edges = sorted(G.edges(data=True), key=lambda x: x[2]['weight'])
        loop_graph = mst.copy()
        
        added_count = 0
        target_extra = int(len(lots) * 0.15)  # 15% extra edges
        
        for u, v, data in all_edges:
            if not loop_graph.has_edge(u, v):
                loop_graph.add_edge(u, v, **data)
                added_count += 1
                if added_count >= target_extra:
                    break
        
        # Convert NetworkX graph to LineString list
        connections = []
        for u, v in loop_graph.edges():
            connections.append(LineString([centroids[u], centroids[v]]))
            
        return points.tolist(), connections

    @staticmethod
    def generate_transformers(lots: List[Polygon], radius: float = 300.0) -> List[Tuple[float, float]]:
        """
        Cluster lots to place transformers using K-Means.
        """
        if not lots:
            return []
            
        lot_coords = np.array([(lot.centroid.x, lot.centroid.y) for lot in lots])
        
        # Estimate number of transformers (approx 1 per 15 lots)
        num_transformers = max(1, int(len(lots) / 15))
        
        if len(lots) < num_transformers:
            num_transformers = len(lots)
            
        kmeans = KMeans(n_clusters=num_transformers, n_init=10).fit(lot_coords)
        return kmeans.cluster_centers_.tolist()

    @staticmethod
    def calculate_drainage(lots: List[Polygon], wwtp_centroid: Point) -> List[Dict[str, Any]]:
        """
        Calculate drainage flow direction towards Wastewater Treatment Plant (XLNT).
        """
        arrows = []
        if not wwtp_centroid:
            return arrows
            
        for lot in lots:
            c = lot.centroid
            dx = wwtp_centroid.x - c.x
            dy = wwtp_centroid.y - c.y
            length = (dx**2 + dy**2)**0.5
            
            if length > 0:
                # Normalize vector to 30m arrow length
                arrows.append({
                    'start': (c.x, c.y),
                    'vector': (dx/length * 30, dy/length * 30)
                })
        return arrows

class LandRedistributionPipeline:
    """Main pipeline orchestrating all optimization stages."""
    
    def __init__(self, land_polygons: List[Polygon], config: Dict[str, Any]):
        """
        Initialize pipeline.
        
        Args:
            land_polygons: Input land plots
            config: Algorithm configuration
        """
        # Merge all input polygons
        from shapely.ops import unary_union
        self.land_poly = unary_union(land_polygons)
        self.config = config
        self.lake_poly = Polygon()  # No lake by default
        
    def generate_road_network(self, num_seeds: int = 15) -> Tuple[Polygon, List[Polygon], List[Polygon]]:
        """
        Generate road network using Voronoi diagram (matches notebook's generate_road_network).
        
        Args:
            num_seeds: Number of Voronoi seed points
            
        Returns:
            (road_network, service_blocks, commercial_blocks)
        """
        # Constants from notebook
        ROAD_MAIN_WIDTH = 25.0      # Main road width (m)
        ROAD_INTERNAL_WIDTH = 15.0  # Internal road width (m)
        SIDEWALK_WIDTH = 4.0        # Sidewalk width each side (m)
        TURNING_RADIUS = 15.0       # Turning radius for intersections (m)
        SERVICE_AREA_RATIO = 0.10   # 10% for service areas
        MIN_BLOCK_AREA = 5000       # Minimum block area (m2)
        
        site = self.land_poly
        minx, miny, maxx, maxy = site.bounds
        
        # 1. Generate random Voronoi seeds
        seeds = []
        for _ in range(num_seeds):
            seeds.append(Point(random.uniform(minx, maxx), random.uniform(miny, maxy)))
        
        # 2. Create Voronoi diagram
        try:
            regions = voronoi_diagram(MultiPoint(seeds), envelope=site)
        except:
            # Fallback if Voronoi fails
            return Polygon(), [], [site]
        
        # 3. Extract edges from Voronoi regions
        edges = []
        if hasattr(regions, 'geoms'):
            for region in regions.geoms:
                if region.geom_type == 'Polygon':
                    edges.append(region.exterior)
        elif regions.geom_type == 'Polygon':
            edges.append(regions.exterior)
        
        # 4. Classify roads and create buffers
        center = site.centroid
        road_polys = []
        
        all_lines = []
        for geom in edges:
            all_lines.append(geom)
        
        merged_lines = unary_union(all_lines)
        
        # Normalize to list of LineStrings
        lines_to_process = []
        if hasattr(merged_lines, 'geoms'):
            lines_to_process = list(merged_lines.geoms)
        else:
            lines_to_process = [merged_lines]
        
        for line in lines_to_process:
            if line.geom_type != 'LineString':
                continue
            
            # Heuristic: roads near center or very long = main roads
            dist_to_center = line.distance(center)
            if dist_to_center < 100 or line.length > 400:
                # Main road: wider + sidewalks
                width = ROAD_MAIN_WIDTH + 2 * SIDEWALK_WIDTH
                road_polys.append(line.buffer(width / 2, cap_style=2, join_style=2))
            else:
                # Internal road: narrower
                width = ROAD_INTERNAL_WIDTH + 2 * SIDEWALK_WIDTH
                road_polys.append(line.buffer(width / 2, cap_style=2, join_style=2))
        
        if not road_polys:
            # No roads generated - fallback
            return Polygon(), [], [site]
        
        network_poly = unary_union(road_polys)
        
        # 5. Apply turning radius smoothing (vạt góc)
        smooth_network = network_poly.buffer(TURNING_RADIUS, join_style=1).buffer(-TURNING_RADIUS, join_style=1)
        
        # 6. Extract blocks (land minus roads)
        blocks_rough = site.difference(smooth_network)
        
        service_blocks = []
        commercial_blocks = []
        
        # Normalize blocks list
        candidates = []
        if hasattr(blocks_rough, 'geoms'):
            candidates = list(blocks_rough.geoms)
        else:
            candidates = [blocks_rough]
        
        # Filter by minimum area
        valid_blocks = [b for b in candidates if b.geom_type == 'Polygon' and b.area >= MIN_BLOCK_AREA]
        
        if not valid_blocks:
            return smooth_network, [], []
        
        # 7. Sort by elevation to find XLNT (lowest)
        blocks_with_elev = [(b, InfrastructurePlanner.get_elevation(b.centroid.x, b.centroid.y)) for b in valid_blocks]
        blocks_with_elev.sort(key=lambda x: x[1])
        
        # 8. Allocate service areas (10% of total)
        total_area = sum(b.area for b in valid_blocks)
        
        # Safety check: prevent division issues
        if total_area <= 0 or len(valid_blocks) == 0:
            return smooth_network, [], valid_blocks
        
        service_area_needed = total_area * SERVICE_AREA_RATIO
        
        accumulated_service_area = 0
        for block, elev in blocks_with_elev:
            if accumulated_service_area < service_area_needed:
                service_blocks.append(block)
                accumulated_service_area += block.area
            else:
                commercial_blocks.append(block)
        
        # Ensure at least one commercial block exists
        if not commercial_blocks and service_blocks:
            # Move one service block to commercial
            commercial_blocks.append(service_blocks.pop())
        
        return smooth_network, service_blocks, commercial_blocks
    
    def run_stage1(self) -> Dict[str, Any]:
        """Run grid optimization stage."""
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
    
    def run_stage2(self, blocks: List[Polygon], spacing: float) -> Dict[str, Any]:
        """Run subdivision stage."""
        all_lots = []
        parks = []
        
        for block in blocks:
            result = SubdivisionSolver.subdivide_block(
                block,
                spacing,
                self.config.get('min_lot_width', 5.0),
                self.config.get('max_lot_width', 8.0),
                self.config.get('target_lot_width', 6.0),
                self.config.get('ortools_time_limit', 5)
            )
            
            if result['type'] == 'park':
                parks.append(result['geometry'])
            else:
                all_lots.extend(result['lots'])
        
        return {
            'lots': all_lots,
            'parks': parks,
            'metrics': {
                'total_lots': len(all_lots),
                'total_parks': len(parks),
                'avg_lot_width': np.mean([lot['width'] for lot in all_lots]) if all_lots else 0
            }
        }
    
    def classify_blocks(self, blocks: List[Polygon]) -> Dict[str, List[Polygon]]:
        """
        Classify blocks into Service (XLNT, Operations) and Commercial.
        Logic: 
        - Sort by elevation (lowest -> XLNT)
        - Reserve 10% for Service/Parking
        - Rest -> Commercial (Residential/Industrial)
        """
        if not blocks:
            return {'service': [], 'commercial': [], 'xlnt': []}
            
        # Sort by elevation
        sorted_blocks = sorted(blocks, key=lambda b: InfrastructurePlanner.get_elevation(b.centroid.x, b.centroid.y))
        
        total_area = sum(b.area for b in blocks)
        service_area_target = total_area * 0.10
        current_service_area = 0
        
        service_blocks = []
        commercial_blocks = []
        xlnt_block = []
        
        # Lowest block is XLNT
        if sorted_blocks:
            xlnt = sorted_blocks.pop(0)
            xlnt_block.append(xlnt)
            current_service_area += xlnt.area
            
        # Fill remaining service quota
        for b in sorted_blocks:
            if current_service_area < service_area_target:
                service_blocks.append(b)
                current_service_area += b.area
            else:
                commercial_blocks.append(b)
                
        return {
            'xlnt': xlnt_block,
            'service': service_blocks,
            'commercial': commercial_blocks
        }

    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run complete optimization pipeline with Voronoi road generation."""
        # NEW: Stage 0 - Voronoi Road Network Generation
        road_network, service_blocks_voronoi, commercial_blocks_voronoi = self.generate_road_network(num_seeds=15)
        
        # If Voronoi fails, fallback to old approach
        if not commercial_blocks_voronoi:
            # Old approach: Grid-based
            stage1_result = self.run_stage1()
            classification = self.classify_blocks(stage1_result['blocks'])
            commercial_blocks_voronoi = classification['commercial']
            service_blocks_voronoi = classification['service']
            xlnt_blocks = classification['xlnt']
            # Old road network
            all_blocks = stage1_result['blocks']
            road_network = self.land_poly.difference(unary_union(all_blocks))
            spacing_for_subdivision = stage1_result['spacing']
        else:
            # Voronoi succeeded - separate XLNT from service blocks
            # XLNT is the first service block (lowest elevation)
            if service_blocks_voronoi:
                xlnt_blocks = [service_blocks_voronoi[0]]
                service_blocks_voronoi = service_blocks_voronoi[1:]
            else:
                xlnt_blocks = []
            
            # Estimate spacing for subdivision (use average block dimension)
            if commercial_blocks_voronoi and len(commercial_blocks_voronoi) > 0:
                avg_area = sum(b.area for b in commercial_blocks_voronoi) / len(commercial_blocks_voronoi)
                spacing_for_subdivision = max(20.0, (avg_area ** 0.5) * 0.7)  # Heuristic, min 20m
            else:
                spacing_for_subdivision = 25.0
        
        # Stage 2: Subdivision (only for commercial blocks)
        stage2_result = self.run_stage2(
            commercial_blocks_voronoi,
            spacing_for_subdivision
        )
        
        # Construct final list of all network nodes
        all_network_nodes = stage2_result['lots'] + \
                          [{'geometry': b, 'type': 'service'} for b in service_blocks_voronoi] + \
                          [{'geometry': b, 'type': 'xlnt'} for b in xlnt_blocks]
        
        # Extract polygons for Infrastructure
        infra_polys = [item['geometry'] for item in all_network_nodes]
        
        # Stage 3: Infrastructure
        points, connections = InfrastructurePlanner.generate_network(infra_polys)
        
        # Transformers
        transformers = InfrastructurePlanner.generate_transformers(infra_polys)
        
        # Drainage
        wwtp_center = xlnt_blocks[0].centroid if xlnt_blocks else None
        drainage = InfrastructurePlanner.calculate_drainage(infra_polys, wwtp_center)
        
        return {
            'stage1': {
                'blocks': commercial_blocks_voronoi + service_blocks_voronoi + xlnt_blocks,
                'metrics': {
                    'total_blocks': len(commercial_blocks_voronoi) + len(service_blocks_voronoi) + len(xlnt_blocks)
                },
                'spacing': spacing_for_subdivision,
                'angle': 0.0  # Voronoi doesn't use angle
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
