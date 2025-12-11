"""API schemas package."""

from .request_schemas import (
    Coordinates,
    RoadNetworkConfig,
    SubdivisionConfig,
    TileSystemConfig,
    PostProcessingConfig,
    QualityConfig,
    RoadGenerationRequest,
    SubdivisionRequest,
    FullPipelineRequest
)

from .response_schemas import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    StageResult,
    RoadGenerationResponse,
    SubdivisionResponse,
    FullPipelineResponse,
    ErrorResponse
)

__all__ = [
    # Request schemas
    "Coordinates",
    "RoadNetworkConfig",
    "SubdivisionConfig", 
    "TileSystemConfig",
    "PostProcessingConfig",
    "QualityConfig",
    "RoadGenerationRequest",
    "SubdivisionRequest",
    "FullPipelineRequest",
    # Response schemas
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
    "StageResult",
    "RoadGenerationResponse",
    "SubdivisionResponse",
    "FullPipelineResponse",
    "ErrorResponse"
]
