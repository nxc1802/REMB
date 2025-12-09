from core.geometry.polygon_utils import (
    get_elevation,
    normalize_geometry_list,
    merge_polygons,
)
from core.geometry.voronoi import (
    generate_voronoi_seeds,
    create_voronoi_diagram,
    extract_voronoi_edges,
)
from core.geometry.shape_quality import (
    analyze_shape_quality,
    get_dominant_edge_vector,
    classify_lot_type,
)
from core.geometry.orthogonal_slicer import (
    orthogonal_slice,
    subdivide_with_uniform_widths,
)
