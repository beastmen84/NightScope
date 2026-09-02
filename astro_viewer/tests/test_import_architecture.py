from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.condition_inputs import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ParticulateConditionInput,
)
from astro_viewer.app.services import observation_conditions_service
from tools.check_import_cycles import find_import_cycles


def test_production_import_graph_is_acyclic() -> None:
    project_root = Path(__file__).resolve().parents[2]

    assert find_import_cycles(project_root / "astro_viewer") == []


def test_condition_input_service_exports_remain_compatible() -> None:
    assert observation_conditions_service.AodConditionInput is AodConditionInput
    assert (
        observation_conditions_service.ParticulateConditionInput
        is ParticulateConditionInput
    )
    assert (
        observation_conditions_service.MoonGeometryConditionInput
        is MoonGeometryConditionInput
    )
    assert (
        observation_conditions_service.ObservationConditionInputs
        is ObservationConditionInputs
    )
