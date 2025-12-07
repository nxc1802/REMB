# Tối Ưu Thuật Toán - Khu Công Nghiệp Ảo

> **Tài liệu phân tích chi tiết các tối ưu thuật toán** cho hệ thống "Khởi tạo khu công nghiệp bằng kỹ sư ảo"

---

## Mục Lục

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Stage 1: Grid Optimization (NSGA-II)](#2-stage-1-grid-optimization-nsga-ii)
3. [Stage 1 Alt: Voronoi Road Network](#3-stage-1-alternative-voronoi-road-network)
4. [Stage 2: Block Subdivision (OR-Tools)](#4-stage-2-block-subdivision-or-tools)
5. [Stage 3: Infrastructure Planning](#5-stage-3-infrastructure-planning)
6. [Cross-Stage Optimizations](#6-cross-stage-optimizations)
7. [Parallelization](#7-algorithm-level-parallelization)
8. [Priority Roadmap](#8-priority-roadmap)

---

## 1. Tổng Quan Kiến Trúc

### 1.1 Pipeline Hiện Tại

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAND REDISTRIBUTION PIPELINE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │  STAGE 1    │───▶│  STAGE 2    │───▶│       STAGE 3           │ │
│  │ Grid/Voronoi│    │ Subdivision │    │    Infrastructure       │ │
│  │  NSGA-II    │    │  OR-Tools   │    │ MST + K-Means + Drainage│ │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Các Module Chính

| Module | File | Thuật toán | Complexity |
|--------|------|------------|------------|
| Grid Optimizer | `grid_optimizer.py` | NSGA-II Genetic Algorithm | O(pop × gen × eval) |
| Voronoi Generator | `voronoi.py` | Fortune's Algorithm (Shapely) | O(n log n) |
| Subdivision Solver | `subdivision_solver.py` | OR-Tools CP-SAT | NP-hard (bounded) |
| Network Planner | `network_planner.py` | Kruskal's MST + Redundancy | O(E log V) |
| Transformer Planner | `transformer_planner.py` | K-Means Clustering | O(n × k × iterations) |
| Drainage Planner | `drainage_planner.py` | Vector Projection | O(n) |

---

## 2. Stage 1: Grid Optimization (NSGA-II)

### 2.1 Phân Tích Hiện Trạng

**File**: `core/optimization/grid_optimizer.py`

```python
# Genome hiện tại: 2 genes
individual = [spacing, angle]  # spacing: 20-80m, angle: 0-90°

# Fitness: 2 objectives
objectives = (
    total_residential_area,  # maximize
    fragmented_blocks        # minimize
)
```

**Bottleneck chính**:
- `generate_grid_candidates()`: Tạo grid và tính intersection với O(n²) Shapely operations
- Mỗi fitness evaluation yêu cầu duyệt tất cả blocks

### 2.2 Tối Ưu 1: Mở Rộng Không Gian Tìm Kiếm

#### Vấn đề
Grid vuông (square) không tối ưu cho khu công nghiệp cần lots chữ nhật.

#### Giải pháp

```python
# Đề xuất: 5 genes thay vì 2
class EnhancedGridOptimizer:
    def _setup_deap(self):
        # Gene definitions
        self.toolbox.register("attr_spacing_x", random.uniform, 20, 100)
        self.toolbox.register("attr_spacing_y", random.uniform, 20, 100)
        self.toolbox.register("attr_angle", random.uniform, 0, 90)
        self.toolbox.register("attr_offset_x", random.uniform, 0, 50)
        self.toolbox.register("attr_offset_y", random.uniform, 0, 50)
        
        self.toolbox.register(
            "individual", 
            tools.initCycle, 
            creator.Individual,
            (
                self.toolbox.attr_spacing_x,
                self.toolbox.attr_spacing_y,
                self.toolbox.attr_angle,
                self.toolbox.attr_offset_x,
                self.toolbox.attr_offset_y,
            ), 
            n=1
        )
    
    def generate_grid_candidates(
        self, 
        spacing_x: float,
        spacing_y: float, 
        angle_deg: float,
        offset_x: float,
        offset_y: float
    ) -> List[Polygon]:
        """Generate rectangular grid blocks."""
        # Create rectangular base block
        base_block = Polygon([
            (0, 0), 
            (spacing_x, 0), 
            (spacing_x, spacing_y), 
            (0, spacing_y)
        ])
        base_block = translate(base_block, -spacing_x/2 + offset_x, -spacing_y/2 + offset_y)
        # ... rotation and placement logic
```

#### Metrics
- **Flexibility**: Hỗ trợ lots 40x80m, 50x100m, etc.
- **Trade-off**: Tăng search space → cần tăng population hoặc generations
- **Implementation effort**: Thấp (2-4 giờ)

---

### 2.3 Tối Ưu 2: Adaptive Island Model

#### Vấn đề
Single population dễ bị kẹt ở local optima.

#### Giải pháp

```python
from deap import tools, algorithms
from concurrent.futures import ProcessPoolExecutor

class IslandGridOptimizer:
    def __init__(self, land_polygon, num_islands=4, migration_interval=5):
        self.num_islands = num_islands
        self.migration_interval = migration_interval
        self.islands = [self._create_population() for _ in range(num_islands)]
    
    def optimize(self, population_size=50, generations=100):
        for gen in range(generations):
            # Evolve each island independently
            for island in self.islands:
                self._evolve_one_generation(island)
            
            # Migration: exchange best individuals between islands
            if gen % self.migration_interval == 0:
                self._migrate()
        
        # Return best from all islands
        all_individuals = [ind for island in self.islands for ind in island]
        return tools.selBest(all_individuals, 1)[0]
    
    def _migrate(self):
        """Ring topology migration."""
        migrants = []
        for island in self.islands:
            best = tools.selBest(island, 2)
            migrants.append([toolbox.clone(ind) for ind in best])
        
        for i in range(self.num_islands):
            next_island = (i + 1) % self.num_islands
            # Replace worst with migrants
            worst = tools.selWorst(self.islands[next_island], 2)
            for w, m in zip(worst, migrants[i]):
                self.islands[next_island].remove(w)
                self.islands[next_island].append(m)
```

#### Metrics
- **Diversity**: Giữ được đa dạng di truyền
- **Parallel potential**: Mỗi island có thể chạy trên core riêng
- **Speedup**: 2-4x với 4 islands trên 4 cores
- **Implementation effort**: Trung bình (1-2 ngày)

---

### 2.4 Tối Ưu 3: Surrogate-Assisted Optimization

#### Vấn đề
Fitness evaluation (Shapely intersections) rất chậm.

#### Giải pháp

```python
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel
import numpy as np

class SurrogateAssistedOptimizer:
    def __init__(self, land_polygon):
        self.land_poly = land_polygon
        self.surrogate = None
        self.training_data = {'X': [], 'y': []}
        self.real_eval_count = 0
        
    def _build_surrogate(self):
        """Build GP surrogate model from collected samples."""
        if len(self.training_data['X']) < 20:
            return None
        
        X = np.array(self.training_data['X'])
        y = np.array(self.training_data['y'])
        
        kernel = ConstantKernel(1.0) * RBF(length_scale=[10, 10])
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5)
        gp.fit(X, y)
        return gp
    
    def _evaluate_with_surrogate(self, individual):
        """Evaluate using surrogate, with uncertainty-based real evaluation."""
        if self.surrogate is None:
            # No surrogate yet, use real evaluation
            return self._real_evaluate(individual)
        
        X = np.array([[individual[0], individual[1]]])
        pred, std = self.surrogate.predict(X, return_std=True)
        
        # If uncertainty is high, do real evaluation
        if std[0] > 0.1 * abs(pred[0]):  # 10% uncertainty threshold
            return self._real_evaluate(individual)
        
        return (pred[0], 0)  # Use surrogate prediction
    
    def _real_evaluate(self, individual):
        """Expensive real evaluation with Shapely."""
        self.real_eval_count += 1
        fitness = self._evaluate_layout(individual)
        
        # Store for training
        self.training_data['X'].append([individual[0], individual[1]])
        self.training_data['y'].append(fitness[0])
        
        # Rebuild surrogate periodically
        if len(self.training_data['X']) % 50 == 0:
            self.surrogate = self._build_surrogate()
        
        return fitness
```

#### Metrics
- **Speedup**: 5-20x reduction in real evaluations
- **Accuracy**: ~95% of true optimum
- **Trade-off**: Cần initial samples để train surrogate
- **Implementation effort**: Cao (1 tuần)

---

## 3. Stage 1 Alternative: Voronoi Road Network

### 3.1 Phân Tích Hiện Trạng

**File**: `core/geometry/voronoi.py`

```python
def generate_voronoi_seeds(site, num_seeds=15, seed=None):
    # Random uniform distribution within bounding box
    for _ in range(num_seeds):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        seeds.append(Point(x, y))
```

**Vấn đề**: Random seeds → blocks không đều, nhiều fragmented blocks.

---

### 3.2 Tối Ưu 1: Centroidal Voronoi Tessellation (CVT)

#### Giải pháp

```python
def generate_cvt_seeds(
    site: Polygon,
    num_seeds: int = 15,
    iterations: int = 20,
    seed: Optional[int] = None
) -> List[Point]:
    """
    Generate Centroidal Voronoi Tessellation seeds.
    
    CVT iteratively moves seeds to the centroid of their Voronoi regions,
    resulting in more uniform block sizes.
    """
    if seed is not None:
        random.seed(seed)
    
    minx, miny, maxx, maxy = site.bounds
    
    # Initialize with random seeds
    seeds = []
    for _ in range(num_seeds):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        seeds.append(Point(x, y))
    
    # CVT iterations
    for iteration in range(iterations):
        # Create Voronoi regions
        multi_point = MultiPoint(seeds)
        regions = voronoi_diagram(multi_point, envelope=site)
        
        # Move seeds to centroids
        new_seeds = []
        for region in regions.geoms:
            if region.geom_type == 'Polygon':
                # Clip to site boundary
                clipped = region.intersection(site)
                if not clipped.is_empty and clipped.geom_type == 'Polygon':
                    new_seeds.append(clipped.centroid)
                else:
                    # Keep original if clipped is invalid
                    new_seeds.append(region.centroid)
        
        # Check convergence
        if len(new_seeds) == len(seeds):
            max_movement = max(
                s1.distance(s2) for s1, s2 in zip(seeds, new_seeds)
            )
            if max_movement < 0.1:  # Convergence threshold
                break
            seeds = new_seeds
    
    return seeds


def generate_weighted_cvt_seeds(
    site: Polygon,
    density_function: Callable[[float, float], float],
    num_seeds: int = 15,
    iterations: int = 30
) -> List[Point]:
    """
    Weighted CVT with density function.
    
    Args:
        density_function: f(x, y) -> weight, higher = smaller blocks
    """
    # Use importance sampling for initial seeds
    candidates = []
    weights = []
    
    minx, miny, maxx, maxy = site.bounds
    for _ in range(num_seeds * 100):  # Oversample
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        p = Point(x, y)
        if site.contains(p):
            candidates.append(p)
            weights.append(density_function(x, y))
    
    # Weighted sampling
    weights = np.array(weights) / sum(weights)
    selected_idx = np.random.choice(
        len(candidates), size=num_seeds, replace=False, p=weights
    )
    seeds = [candidates[i] for i in selected_idx]
    
    # Run weighted CVT iterations
    for _ in range(iterations):
        # ... similar to regular CVT but with weighted centroids
        pass
    
    return seeds
```

#### Use Case: Industrial Park Zoning

```python
def industrial_density(x, y):
    """
    Higher density near main access roads and utilities.
    """
    # Assume main road at y=0
    dist_to_main_road = abs(y)
    
    # High density (smaller blocks) near road
    if dist_to_main_road < 100:
        return 2.0
    elif dist_to_main_road < 200:
        return 1.5
    else:
        return 1.0

seeds = generate_weighted_cvt_seeds(
    site=land_polygon,
    density_function=industrial_density,
    num_seeds=20
)
```

#### Metrics
- **Block uniformity**: +40-60% more uniform areas
- **Fragmentation reduction**: -30-50% fragmented blocks
- **Time overhead**: 20 iterations × O(n log n) = acceptable
- **Implementation effort**: Trung bình (2-3 ngày)

---

### 3.3 Tối Ưu 2: Constrained Voronoi

#### Vấn đề
Voronoi edges có thể không align với preferred road directions.

#### Giải pháp

```python
from shapely.geometry import LineString
from shapely.ops import split

class ConstrainedVoronoi:
    """
    Voronoi with hard constraints (e.g., main roads must be axis-aligned).
    """
    
    def __init__(self, site: Polygon, main_roads: List[LineString]):
        self.site = site
        self.main_roads = main_roads  # Pre-defined main road axes
    
    def generate(self, num_internal_seeds: int = 10) -> List[Polygon]:
        # Step 1: Split site by main roads
        regions = [self.site]
        for road in self.main_roads:
            new_regions = []
            for region in regions:
                if road.intersects(region):
                    parts = split(region, road)
                    new_regions.extend(parts.geoms)
                else:
                    new_regions.append(region)
            regions = [r for r in new_regions if r.geom_type == 'Polygon']
        
        # Step 2: Apply Voronoi within each region
        all_blocks = []
        for region in regions:
            seeds_per_region = max(2, int(num_internal_seeds * region.area / self.site.area))
            seeds = generate_cvt_seeds(region, seeds_per_region)
            voronoi_regions = create_voronoi_diagram(seeds, region)
            
            if voronoi_regions:
                for v in voronoi_regions.geoms:
                    clipped = v.intersection(region)
                    if clipped.geom_type == 'Polygon' and clipped.area > 100:
                        all_blocks.append(clipped)
        
        return all_blocks


# Usage
main_roads = [
    LineString([(0, 500), (1000, 500)]),    # Horizontal main road
    LineString([(500, 0), (500, 1000)]),     # Vertical main road
]

cv = ConstrainedVoronoi(land_polygon, main_roads)
blocks = cv.generate(num_internal_seeds=15)
```

#### Metrics
- **Road alignment**: Main roads guaranteed straight
- **Flexibility**: Sub-blocks use organic Voronoi
- **Implementation effort**: Trung bình (2 ngày)

---

## 4. Stage 2: Block Subdivision (OR-Tools)

### 4.1 Phân Tích Hiện Trạng

**File**: `core/optimization/subdivision_solver.py`

```python
# Hiện tại: 1D subdivision (width only)
def solve_subdivision(total_length, min_width, max_width, target_width):
    # lot_vars[i] = width of lot i
    # Constraint: sum(lot_vars) == total_length
    # Objective: minimize deviation from target_width
```

**Hạn chế**: Chỉ chia theo 1 chiều, không tối ưu cho lots cần aspect ratio cụ thể.

---

### 4.2 Tối Ưu 1: 2D Bin Packing

#### Giải pháp

```python
from ortools.sat.python import cp_model
from typing import List, Tuple, Dict

class TwoDimensionalSubdivisionSolver:
    """
    2D bin packing for lot placement within a block.
    
    Optimizes both lot placement and dimensions.
    """
    
    @staticmethod
    def solve_2d_subdivision(
        block_width: float,
        block_height: float,
        min_lot_width: float,
        max_lot_width: float,
        min_lot_height: float,
        max_lot_height: float,
        target_aspect_ratio: float = 2.0,  # height/width
        time_limit: float = 10.0
    ) -> List[Dict]:
        """
        Solve 2D lot placement using constraint programming.
        
        Returns:
            List of lots with {x, y, width, height}
        """
        model = cp_model.CpModel()
        scale = 100  # 1cm precision
        
        # Estimate max lots
        min_lot_area = min_lot_width * min_lot_height
        max_lots = int((block_width * block_height) / min_lot_area) + 1
        max_lots = min(max_lots, 50)  # Cap for performance
        
        # Decision variables for each lot
        lots = []
        for i in range(max_lots):
            lot = {
                'x': model.NewIntVar(0, int(block_width * scale), f'x_{i}'),
                'y': model.NewIntVar(0, int(block_height * scale), f'y_{i}'),
                'width': model.NewIntVar(
                    int(min_lot_width * scale),
                    int(max_lot_width * scale),
                    f'w_{i}'
                ),
                'height': model.NewIntVar(
                    int(min_lot_height * scale),
                    int(max_lot_height * scale),
                    f'h_{i}'
                ),
                'used': model.NewBoolVar(f'used_{i}'),
                'area': model.NewIntVar(0, int(block_width * block_height * scale * scale), f'area_{i}')
            }
            lots.append(lot)
        
        # Constraints
        for i, lot in enumerate(lots):
            # Lot must fit within block
            model.Add(lot['x'] + lot['width'] <= int(block_width * scale)).OnlyEnforceIf(lot['used'])
            model.Add(lot['y'] + lot['height'] <= int(block_height * scale)).OnlyEnforceIf(lot['used'])
            
            # If not used, dimensions are 0
            model.Add(lot['width'] == 0).OnlyEnforceIf(lot['used'].Not())
            model.Add(lot['height'] == 0).OnlyEnforceIf(lot['used'].Not())
            
            # Area calculation
            model.AddMultiplicationEquality(lot['area'], [lot['width'], lot['height']])
        
        # No overlap constraint (using intervals)
        x_intervals = []
        y_intervals = []
        for i, lot in enumerate(lots):
            x_interval = model.NewOptionalIntervalVar(
                lot['x'], lot['width'], lot['x'] + lot['width'],
                lot['used'], f'x_interval_{i}'
            )
            y_interval = model.NewOptionalIntervalVar(
                lot['y'], lot['height'], lot['y'] + lot['height'],
                lot['used'], f'y_interval_{i}'
            )
            x_intervals.append(x_interval)
            y_intervals.append(y_interval)
        
        model.AddNoOverlap2D(x_intervals, y_intervals)
        
        # Objective: Maximize total used area + Aspect ratio penalty
        total_area = sum(lot['area'] for lot in lots)
        
        # Aspect ratio deviation penalty
        aspect_penalties = []
        target_ratio_scaled = int(target_aspect_ratio * 100)
        for i, lot in enumerate(lots):
            # height/width should be close to target_aspect_ratio
            deviation = model.NewIntVar(0, 1000, f'aspect_dev_{i}')
            actual_ratio = model.NewIntVar(0, 1000, f'ratio_{i}')
            # actual_ratio ≈ (height * 100) / width
            model.AddDivisionEquality(
                actual_ratio,
                lot['height'] * 100,
                lot['width']
            )
            model.AddAbsEquality(deviation, actual_ratio - target_ratio_scaled)
            aspect_penalties.append(deviation)
        
        # Multi-objective: maximize area, minimize aspect deviation
        model.Maximize(total_area - sum(aspect_penalties) * 100)
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        status = solver.Solve(model)
        
        # Extract solution
        result = []
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            for lot in lots:
                if solver.Value(lot['used']):
                    result.append({
                        'x': solver.Value(lot['x']) / scale,
                        'y': solver.Value(lot['y']) / scale,
                        'width': solver.Value(lot['width']) / scale,
                        'height': solver.Value(lot['height']) / scale,
                    })
        
        return result
```

#### Metrics
- **Space utilization**: +15-25% more efficient packing
- **Aspect ratio control**: Lots match industrial requirements
- **Time complexity**: Higher, nhưng bounded by time_limit
- **Implementation effort**: Cao (1 tuần)

---

### 4.3 Tối Ưu 2: Hierarchical Decomposition

#### Giải pháp

```python
from concurrent.futures import ProcessPoolExecutor
from shapely.geometry import box

class HierarchicalSubdivisionSolver:
    """
    Divide large blocks into quadrants, solve each in parallel.
    """
    
    @staticmethod
    def subdivide_hierarchically(
        block: Polygon,
        max_block_size: float = 10000,  # m²
        **solver_kwargs
    ) -> List[Dict]:
        """
        Recursively subdivide large blocks before optimization.
        """
        if block.area <= max_block_size:
            # Small enough, solve directly
            return SubdivisionSolver.subdivide_block(block, **solver_kwargs)
        
        # Split into quadrants
        minx, miny, maxx, maxy = block.bounds
        midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
        
        quadrants = [
            box(minx, miny, midx, midy),
            box(midx, miny, maxx, midy),
            box(minx, midy, midx, maxy),
            box(midx, midy, maxx, maxy),
        ]
        
        sub_blocks = []
        for quad in quadrants:
            intersection = block.intersection(quad)
            if not intersection.is_empty and intersection.area > 100:
                sub_blocks.append(intersection)
        
        # Solve in parallel
        with ProcessPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(
                lambda b: HierarchicalSubdivisionSolver.subdivide_hierarchically(
                    b, max_block_size, **solver_kwargs
                ),
                sub_blocks
            ))
        
        # Merge results
        all_lots = []
        for result in results:
            if 'lots' in result:
                all_lots.extend(result['lots'])
        
        return {'geometry': block, 'type': 'residential', 'lots': all_lots}
```

#### Metrics
- **Parallel speedup**: 2-4x with 4 cores
- **Scalability**: Handles very large blocks
- **Implementation effort**: Trung bình (2-3 ngày)

---

## 5. Stage 3: Infrastructure Planning

### 5.1 Network Planner - Steiner Tree

**File**: `core/infrastructure/network_planner.py`

#### Vấn đề Hiện Tại
MST + 15% redundancy là heuristic, không optimal.

#### Giải pháp: Steiner Tree

```python
import networkx as nx
from networkx.algorithms.approximation import steiner_tree
from scipy.spatial import Delaunay

def generate_steiner_network(
    lots: List[Polygon],
    steiner_candidates: int = 20,
    max_distance: float = 500.0,
    redundancy_ratio: float = 0.15
) -> Tuple[List[List[float]], List[LineString]]:
    """
    Generate network using Steiner Tree approximation.
    
    Steiner Tree allows intermediate nodes (not at lot centroids)
    which can reduce total cable length by 15-20%.
    """
    if len(lots) < 2:
        return [], []
    
    # Get lot centroids (terminal nodes)
    centroids = [lot.centroid for lot in lots]
    terminal_coords = [(p.x, p.y) for p in centroids]
    
    # Generate candidate Steiner points
    # Use centroid of triangles from Delaunay triangulation
    all_coords = np.array(terminal_coords)
    if len(all_coords) >= 3:
        tri = Delaunay(all_coords)
        steiner_candidates_points = []
        for simplex in tri.simplices:
            triangle_points = all_coords[simplex]
            centroid = triangle_points.mean(axis=0)
            steiner_candidates_points.append(tuple(centroid))
    else:
        steiner_candidates_points = []
    
    # Build graph with terminals and Steiner candidates
    all_points = terminal_coords + steiner_candidates_points
    G = nx.Graph()
    
    for i, p in enumerate(all_points):
        G.add_node(i, pos=p, terminal=(i < len(terminal_coords)))
    
    # Add edges between nearby points
    for i in range(len(all_points)):
        for j in range(i + 1, len(all_points)):
            dist = np.sqrt(
                (all_points[i][0] - all_points[j][0])**2 +
                (all_points[i][1] - all_points[j][1])**2
            )
            if dist < max_distance:
                G.add_edge(i, j, weight=dist)
    
    # Find Steiner tree connecting all terminals
    terminal_nodes = list(range(len(terminal_coords)))
    try:
        st = steiner_tree(G, terminal_nodes, weight='weight')
    except Exception:
        # Fallback to MST
        st = nx.minimum_spanning_tree(G)
    
    # Add redundancy
    loop_graph = st.copy()
    all_edges = sorted(G.edges(data=True), key=lambda x: x[2]['weight'])
    target_extra = int(len(terminal_coords) * redundancy_ratio)
    added = 0
    
    for u, v, data in all_edges:
        if not loop_graph.has_edge(u, v):
            loop_graph.add_edge(u, v, **data)
            added += 1
            if added >= target_extra:
                break
    
    # Convert to LineStrings
    connections = []
    for u, v in loop_graph.edges():
        p1 = Point(all_points[u])
        p2 = Point(all_points[v])
        connections.append(LineString([p1, p2]))
    
    return [list(p) for p in all_points], connections
```

#### Metrics
- **Cable length reduction**: 15-20%
- **Cost savings**: Significant for large projects
- **Implementation effort**: Thấp (1 ngày)

---

### 5.2 Transformer Placement - Multi-Objective

#### Giải pháp

```python
from scipy.optimize import minimize
from sklearn.cluster import KMeans
import numpy as np

def generate_transformers_multiobjective(
    lots: List[Polygon],
    power_per_lot: float = 100.0,  # kW
    transformer_capacity: float = 1000.0,  # kVA
    cable_cost_per_meter: float = 50.0,  # USD
    transformer_cost: float = 50000.0  # USD
) -> Tuple[List[Tuple[float, float]], Dict]:
    """
    Multi-objective transformer placement:
    1. Minimize total cable length
    2. Balance load across transformers
    3. Minimize total cost (transformers + cables)
    """
    if not lots:
        return [], {}
    
    lot_coords = np.array([[lot.centroid.x, lot.centroid.y] for lot in lots])
    lot_powers = np.array([power_per_lot] * len(lots))
    
    # Step 1: Find optimal number of transformers
    total_power = sum(lot_powers)
    min_transformers = int(np.ceil(total_power / transformer_capacity))
    max_transformers = min(len(lots), min_transformers * 2)
    
    best_cost = float('inf')
    best_solution = None
    best_k = min_transformers
    
    for k in range(min_transformers, max_transformers + 1):
        # K-Means clustering
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(lot_coords)
        centers = kmeans.cluster_centers_
        
        # Calculate total cable length
        total_cable = 0
        load_imbalance = 0
        
        cluster_loads = [0] * k
        for i, label in enumerate(labels):
            dist = np.sqrt(
                (lot_coords[i][0] - centers[label][0])**2 +
                (lot_coords[i][1] - centers[label][1])**2
            )
            total_cable += dist
            cluster_loads[label] += lot_powers[i]
        
        # Check capacity constraints
        capacity_ok = all(load <= transformer_capacity for load in cluster_loads)
        if not capacity_ok:
            continue
        
        # Load imbalance (variance)
        load_imbalance = np.var(cluster_loads)
        
        # Total cost
        cable_cost = total_cable * cable_cost_per_meter
        total_cost = k * transformer_cost + cable_cost
        
        # Penalize imbalance
        total_cost += load_imbalance * 0.1
        
        if total_cost < best_cost:
            best_cost = total_cost
            best_k = k
            best_solution = {
                'centers': [tuple(c) for c in centers],
                'labels': labels.tolist(),
                'cluster_loads': cluster_loads,
                'total_cable': total_cable,
                'total_cost': total_cost,
            }
    
    return best_solution['centers'], best_solution
```

---

### 5.3 Drainage - Shortest Path on Road Network

#### Giải pháp

```python
import networkx as nx
from shapely.geometry import LineString

def calculate_drainage_on_network(
    lots: List[Polygon],
    road_network: nx.Graph,
    wwtp_node: int,
    arrow_length: float = 20.0
) -> List[Dict]:
    """
    Calculate drainage paths following the road network.
    
    More realistic than direct vectors - pipes follow roads.
    """
    arrows = []
    
    if not road_network.nodes():
        return arrows
    
    # Precompute shortest paths from all nodes to WWTP
    try:
        lengths, paths = nx.single_source_dijkstra(
            road_network, wwtp_node, weight='length'
        )
    except nx.NetworkXError:
        return arrows
    
    for lot in lots:
        c = lot.centroid
        
        # Find nearest road network node
        nearest_node = None
        min_dist = float('inf')
        for node, data in road_network.nodes(data=True):
            pos = data.get('pos', (node, node))
            dist = c.distance(Point(pos))
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        
        if nearest_node is None or nearest_node not in paths:
            continue
        
        # Get path to WWTP
        path = paths[nearest_node]
        if len(path) < 2:
            continue
        
        # Arrow direction: first segment of path
        first_node = path[0]
        second_node = path[1]
        
        pos1 = road_network.nodes[first_node].get('pos', (first_node, first_node))
        pos2 = road_network.nodes[second_node].get('pos', (second_node, second_node))
        
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        length = np.sqrt(dx*dx + dy*dy)
        
        if length > 0:
            arrows.append({
                'start': (c.x, c.y),
                'vector': (dx/length * arrow_length, dy/length * arrow_length),
                'path_length': lengths.get(nearest_node, 0)
            })
    
    return arrows
```

---

## 6. Cross-Stage Optimizations

### 6.1 Spatial Indexing với STRtree

**Vấn đề**: O(n²) intersection checks trong nhiều modules.

#### Giải pháp

```python
from shapely.strtree import STRtree
from shapely.geometry import Polygon

class SpatiallyIndexedOperations:
    """
    Use R-Tree spatial index for efficient geometric queries.
    """
    
    def __init__(self, geometries: List[Polygon]):
        self.geometries = geometries
        self.tree = STRtree(geometries)
    
    def query_intersects(self, query_geom: Polygon) -> List[Polygon]:
        """O(log n) instead of O(n) for intersection queries."""
        return self.tree.query(query_geom)
    
    def query_within_distance(
        self, 
        query_geom: Polygon, 
        distance: float
    ) -> List[Polygon]:
        """Find geometries within distance."""
        buffered = query_geom.buffer(distance)
        return self.tree.query(buffered)


# Integration into GridOptimizer
class OptimizedGridOptimizer(GridOptimizer):
    def _evaluate_layout(self, individual):
        spacing, angle = individual
        blocks = self.generate_grid_candidates(spacing, angle)
        
        # Use spatial index for intersection checks
        tree = STRtree(blocks)
        candidates = tree.query(self.land_poly)
        
        total_residential_area = 0.0
        fragmented_blocks = 0
        original_area = spacing * spacing
        
        for blk in candidates:
            # Only evaluate blocks that actually intersect
            if not blk.intersects(self.land_poly):
                continue
            
            intersection = blk.intersection(self.land_poly)
            # ... rest of evaluation
```

#### Metrics
- **Speedup**: 10-100x for large grids
- **Memory**: Slightly higher (index storage)
- **Implementation effort**: Thấp (vài giờ)

---

### 6.2 Geometry Simplification

```python
def preprocess_geometry(polygon: Polygon, tolerance: float = 0.5) -> Polygon:
    """
    Simplify polygon before heavy operations.
    
    tolerance=0.5 means 50cm maximum deviation - acceptable for planning.
    """
    # Remove redundant vertices
    simplified = polygon.simplify(tolerance, preserve_topology=True)
    
    # Fix any topology issues
    if not simplified.is_valid:
        simplified = simplified.buffer(0)
    
    return simplified


# Apply before optimization
class PreprocessedPipeline(LandRedistributionPipeline):
    def __init__(self, land_polygons, config, settings=None):
        # Simplify input geometry
        simplified_polygons = [
            preprocess_geometry(p, tolerance=0.5) 
            for p in land_polygons
        ]
        super().__init__(simplified_polygons, config, settings)
```

---

### 6.3 Caching Layer

```python
import hashlib
from functools import lru_cache
from typing import Tuple

class CachedGridOptimizer(GridOptimizer):
    """
    Cache fitness evaluations for identical or similar parameters.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eval_cache = {}
    
    def _discretize_params(self, spacing: float, angle: float) -> Tuple[int, int]:
        """Round to create discrete cache keys."""
        return (round(spacing, 1), round(angle, 1))
    
    def _evaluate_layout(self, individual):
        spacing, angle = individual
        cache_key = self._discretize_params(spacing, angle)
        
        if cache_key in self.eval_cache:
            return self.eval_cache[cache_key]
        
        # Compute and cache
        result = super()._evaluate_layout(individual)
        self.eval_cache[cache_key] = result
        
        return result
```

---

## 7. Algorithm-Level Parallelization

### 7.1 Parallel Fitness Evaluation

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
from deap import base, creator, tools
import multiprocessing

class ParallelGridOptimizer(GridOptimizer):
    def __init__(self, *args, num_workers=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_workers = num_workers or multiprocessing.cpu_count()
    
    def optimize(self, population_size=50, generations=100):
        pop = self.toolbox.population(n=population_size)
        
        # Use ProcessPoolExecutor for parallel evaluation
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            for gen in range(generations):
                # Parallel fitness evaluation
                futures = {
                    executor.submit(self._evaluate_layout, ind): ind 
                    for ind in pop
                }
                
                for future in as_completed(futures):
                    ind = futures[future]
                    ind.fitness.values = future.result()
                
                # Selection and variation (sequential)
                offspring = algorithms.varAnd(
                    pop, self.toolbox, 
                    cxpb=0.7, mutpb=0.2
                )
                
                # Parallel evaluation of offspring
                futures = {
                    executor.submit(self._evaluate_layout, ind): ind 
                    for ind in offspring
                }
                
                for future in as_completed(futures):
                    ind = futures[future]
                    ind.fitness.values = future.result()
                
                pop = self.toolbox.select(pop + offspring, k=population_size)
        
        return tools.selBest(pop, 1)[0]
```

### 7.2 DEAP Built-in Parallelization

```python
from deap import base
from scoop import futures

# For distributed computing across machines
toolbox.register("map", futures.map)

# Usage:
# python -m scoop -n 8 optimize.py
```

---

## 8. Priority Roadmap

### 8.1 Impact vs Effort Matrix

```
                              IMPACT
                    Low                    High
              ┌────────────────┬────────────────┐
         Low  │ • Caching      │ • STRtree      │
              │                │ • Parallel Eval│
    EFFORT    │                │ • Steiner Tree │
              ├────────────────┼────────────────┤
         High │ • Column Gen   │ • Surrogate    │
              │                │ • 2D Packing   │
              │                │ • CVT + Constr │
              └────────────────┴────────────────┘
```

### 8.2 Recommended Implementation Order

#### Phase 1: Quick Wins (1-2 weeks)
| # | Optimization | Est. Time | Expected Speedup |
|---|--------------|-----------|------------------|
| 1 | STRtree Spatial Indexing | 4h | 10-50x for intersection |
| 2 | Geometry Simplification | 2h | 2-3x for boolean ops |
| 3 | Evaluation Caching | 4h | 1.5-2x |
| 4 | Parallel Fitness Eval | 1d | 2-4x (CPU cores) |

#### Phase 2: Medium-term (2-4 weeks)
| # | Optimization | Est. Time | Expected Improvement |
|---|--------------|-----------|---------------------|
| 5 | Steiner Tree Network | 2d | 15-20% shorter cables |
| 6 | CVT Voronoi Seeds | 3d | 30-50% less fragmentation |
| 7 | Multi-obj Transformer | 2d | Better load balance + cost |
| 8 | Island Model GA | 3d | Better global optimum |

#### Phase 3: Advanced (1-2 months)
| # | Optimization | Est. Time | Expected Improvement |
|---|--------------|-----------|---------------------|
| 9 | Extended Genome (5D) | 1w | Rectangular lots support |
| 10 | Surrogate-Assisted | 2w | 5-20x fewer real evals |
| 11 | 2D Bin Packing | 2w | 15-25% better space util |
| 12 | Constrained Voronoi | 1w | Aligned main roads |

---

## Appendix A: Benchmark Template

```python
import time
from typing import Callable, Dict, Any

def benchmark_optimization(
    optimizer_class: type,
    land_polygon: Polygon,
    configs: List[Dict[str, Any]],
    num_runs: int = 5
) -> Dict:
    """
    Standard benchmark for comparing optimizers.
    """
    results = []
    
    for config in configs:
        run_times = []
        fitness_values = []
        
        for run in range(num_runs):
            optimizer = optimizer_class(land_polygon, **config)
            
            start = time.perf_counter()
            solution, history = optimizer.optimize()
            elapsed = time.perf_counter() - start
            
            run_times.append(elapsed)
            fitness_values.append(solution.fitness.values)
        
        results.append({
            'config': config,
            'avg_time': sum(run_times) / num_runs,
            'std_time': np.std(run_times),
            'avg_fitness': np.mean(fitness_values, axis=0),
            'best_fitness': max(fitness_values),
        })
    
    return results
```

---

## Appendix B: References

1. **NSGA-II**: Deb et al., "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II" (2002)
2. **Centroidal Voronoi Tessellation**: Du, Faber, Gunzburger (1999)
3. **Steiner Tree**: Hwang, Richards, Winter, "The Steiner Tree Problem" (1992)
4. **OR-Tools**: Google Operations Research Tools documentation
5. **Surrogate-Assisted Optimization**: Jin, "Surrogate-assisted evolutionary computation" (2011)
6. **Shapely STRtree**: Guttman, "R-trees: A Dynamic Index Structure for Spatial Searching" (1984)

---

> **Document Version**: 1.0  
> **Created**: 2025-12-08  
> **Author**: AI Analysis System  
> **Status**: Draft - Pending Review
