from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.condition_inputs import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ParticulateConditionInput,
)
from astro_viewer.app.services import observation_conditions_service
from tools.check_import_cycles import find_import_cycles, find_layer_violations


def test_production_import_graph_is_acyclic() -> None:
    project_root = Path(__file__).resolve().parents[2]

    assert find_import_cycles(project_root / "astro_viewer") == []
    assert find_layer_violations(project_root / "astro_viewer") == []


def test_lower_layers_cannot_import_controller_or_composition_root(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "astro_viewer"
    model_path = source_root / "app" / "models" / "example.py"
    controller_path = source_root / "app" / "viewmodels" / "controller.py"
    model_path.parent.mkdir(parents=True)
    controller_path.parent.mkdir(parents=True)
    model_path.write_text(
        "from astro_viewer.app.viewmodels.controller import Controller\n",
        encoding="utf-8",
    )
    controller_path.write_text("class Controller:\n    pass\n", encoding="utf-8")

    assert find_layer_violations(source_root) == [
        (
            "astro_viewer.app.models.example",
            "astro_viewer.app.viewmodels.controller",
        )
    ]


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
