"""Road skeleton templates for SmartPlan AI.

4 human-curated templates:
- Spine: Central axis with perpendicular branches
- Grid: Orthogonal grid pattern
- Loop: Ring road around boundary
- Cross: Two main axes crossing at center
"""

from .base import RoadTemplate, TemplateResult, TemplateRegistry, TemplateParams
from .spine import SpineTemplate
from .grid import GridTemplate
from .loop import LoopTemplate
from .cross import CrossTemplate

# Register all templates
TEMPLATE_REGISTRY = TemplateRegistry()
TEMPLATE_REGISTRY.register(SpineTemplate())
TEMPLATE_REGISTRY.register(GridTemplate())
TEMPLATE_REGISTRY.register(LoopTemplate())
TEMPLATE_REGISTRY.register(CrossTemplate())


def get_template(name: str) -> RoadTemplate:
    """Get template by name."""
    return TEMPLATE_REGISTRY.get(name)


def list_templates() -> list:
    """List all available templates."""
    return TEMPLATE_REGISTRY.list_all()


__all__ = [
    "RoadTemplate",
    "TemplateResult", 
    "TemplateRegistry",
    "SpineTemplate",
    "GridTemplate",
    "LoopTemplate",
    "CrossTemplate",
    "TEMPLATE_REGISTRY",
    "get_template",
    "list_templates"
]
