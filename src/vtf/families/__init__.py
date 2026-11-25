"""Registry of all visual task families."""

from __future__ import annotations

from vtf.families.base import VisualTaskFamily
from vtf.families.blueprints import BlueprintsGaugesTaskFamily
from vtf.families.charts import ChartsTaskFamily
from vtf.families.circuits import LogicCircuitsTaskFamily
from vtf.families.documents import StructuredDocsTaskFamily
from vtf.families.spatial import SpatialInventoryTaskFamily
from vtf.schema import FamilyName

FAMILY_REGISTRY: dict[FamilyName, VisualTaskFamily] = {
    FamilyName.CHARTS: ChartsTaskFamily(),
    FamilyName.SPATIAL_INVENTORY: SpatialInventoryTaskFamily(),
    FamilyName.LOGIC_CIRCUITS: LogicCircuitsTaskFamily(),
    FamilyName.STRUCTURED_DOCS: StructuredDocsTaskFamily(),
    FamilyName.BLUEPRINTS_GAUGES: BlueprintsGaugesTaskFamily(),
}


def get_family(name: FamilyName | str) -> VisualTaskFamily:
    key = name if isinstance(name, FamilyName) else FamilyName(name)
    return FAMILY_REGISTRY[key]
