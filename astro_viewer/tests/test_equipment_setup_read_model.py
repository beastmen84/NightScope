from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

from astro_viewer.app.application.dependencies import AppControllerDependencies
from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModelBuilder
from astro_viewer.app.viewmodels.app_controller import AppController


def test_equipment_setup_read_model_roundtrips_service_payload_strict_json_and_is_frozen() -> None:
    target = _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField")
    suggestion = EquipmentService().suggest_for_profile(
        target,
        [Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale")],
        [Eyepiece("e32", "32 mm", 32, 68), Eyepiece("e8", "8 mm", 8, 60)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    model = EquipmentSetupReadModelBuilder().from_suggestion(target, suggestion)

    assert model.object_id == "messier-M45"
    assert model.to_equipment_service_payload() == suggestion
    assert model.to_celestial_object_updates() == {
        "recommended_setup": suggestion["setupText"],
        "best_eyepiece": suggestion["bestEyepiece"],
        "barlow": suggestion["barlow"],
        "difficulty": suggestion["difficulty"],
        "recommended_setup_type": suggestion["setupType"],
        "setup_options": suggestion["setupOptions"],
        "equipment_explanation": suggestion["explanation"],
    }
    json.dumps(model.to_dict(), sort_keys=True, allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        model.setup_text = "changed"  # type: ignore[misc]


def test_equipment_setup_read_model_preserves_fallback_payload_key_subset() -> None:
    target = _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification")
    suggestion = EquipmentService().suggest_for_profile(
        target,
        [],
        [],
        [],
        binoculars=[],
    )

    model = EquipmentSetupReadModelBuilder().from_suggestion(target, suggestion)

    assert model.requires_optical_instrument is True
    assert model.to_equipment_service_payload() == suggestion
    assert "highMagnification" not in model.to_equipment_service_payload()
    assert "wideField" not in model.to_equipment_service_payload()
    assert model.recommended_setup_type == "naked_eye"
    assert model.to_celestial_object_updates()["setup_options"] == []


def test_equipment_setup_read_model_sanitizes_non_finite_payload_values_for_strict_json() -> None:
    target = _object("target", "Target", "Galaxy", "8.8", "12 arcmin", 0.2, "General")
    suggestion = {
        "bestEyepiece": "25 mm",
        "suggestedPosition": "",
        "barlow": "No",
        "difficulty": "Media",
        "alternative": "n/d",
        "highMagnification": "",
        "wideField": "",
        "setupText": "25 mm",
        "setupOptions": [
            {
                "role": "Consigliato",
                "label": "25 mm",
                "detailLabel": "25 mm",
                "displayLabel": "25 mm",
                "suggestedPosition": "",
                "magnification": "48x",
                "trueField": "1.08 gradi",
                "exitPupil": "4.2 mm",
                "barlow": "No",
                "score": float("nan"),
                "telescopeName": "Dobson 200",
                "equipmentType": "Telescope",
            }
        ],
        "explanation": "fixture",
        "telescopeId": "scope",
        "telescopeName": "Dobson 200",
        "equipmentType": "Telescope",
        "setupType": "telescope",
        "selectionScore": float("inf"),
    }

    model = EquipmentSetupReadModelBuilder().from_suggestion(target, suggestion)
    payload = model.to_equipment_service_payload()

    assert payload["selectionScore"] is None
    assert payload["setupOptions"][0]["score"] is None
    json.dumps(model.to_dict(), sort_keys=True, allow_nan=False)


def test_app_controller_applies_equipment_through_read_model_without_payload_shape_change() -> None:
    controller = AppController.__new__(AppController)
    target = _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification")
    telescope = Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")
    suggestion = EquipmentService().suggest_for_profile(
        target,
        [telescope],
        [Eyepiece("e10", "10 mm", 10, 60), Eyepiece("e25", "25 mm", 25, 52)],
        [],
        binoculars=[],
    )
    controller._equipment_service = _FakeEquipmentService(suggestion)
    controller._equipment_setup_read_model_builder = EquipmentSetupReadModelBuilder()
    controller._seeing_transparency = None
    controller._sky_quality = None
    controller._object_image_map = {}
    controller._object_descriptions = {}
    controller._active_profile_telescopes = lambda: [telescope]
    controller._active_profile_eyepieces = lambda: [Eyepiece("e10", "10 mm", 10, 60)]
    controller._active_profile_barlows = lambda: []
    controller._active_profile_binoculars = lambda: []
    controller._find_telescope = lambda telescope_id: telescope if telescope_id == telescope.id else None

    updated = controller._apply_equipment([target])[0]
    payload = updated.to_qml()

    assert updated.recommended_setup == suggestion["setupText"]
    assert updated.best_eyepiece == suggestion["bestEyepiece"]
    assert updated.barlow == suggestion["barlow"]
    assert updated.difficulty == suggestion["difficulty"]
    assert updated.recommended_setup_type == suggestion["setupType"]
    assert updated.setup_options == suggestion["setupOptions"]
    assert updated.equipment_explanation == suggestion["explanation"]
    assert payload["recommended_setup"] == suggestion["setupText"]
    assert payload["setupOptions"] == suggestion["setupOptions"]
    assert "equipmentSetupReadModel" not in payload
    assert controller._planner_telescopes_by_object_id([updated]) == {target.id: telescope}


def test_app_controller_preserves_the_second_profile_telescope_selected_for_a_target() -> None:
    controller = AppController.__new__(AppController)
    target = _object("messier-M51", "M51", "Galaxy", "8.4", "11 arcmin", 0.183, "General")
    compact_scope = Telescope("small", "Maksutov 90", 90, 1250, "Maksutov", "manuale")
    deep_sky_scope = Telescope("large", "Dobson 200", 200, 1200, "Newton", "Dobson")
    eyepieces = [Eyepiece("e25", "25 mm", 25, 68), Eyepiece("e10", "10 mm", 10, 60)]
    suggestion = EquipmentService().suggest_for_profile(
        target,
        [compact_scope, deep_sky_scope],
        eyepieces,
        [],
        binoculars=[],
    )
    controller._equipment_service = _FakeEquipmentService(suggestion)
    controller._equipment_setup_read_model_builder = EquipmentSetupReadModelBuilder()
    controller._seeing_transparency = None
    controller._sky_quality = None
    controller._object_image_map = {}
    controller._object_descriptions = {}
    controller._active_profile_telescopes = lambda: [compact_scope, deep_sky_scope]
    controller._active_profile_eyepieces = lambda: eyepieces
    controller._active_profile_barlows = lambda: []
    controller._active_profile_binoculars = lambda: []
    controller._find_telescope = lambda telescope_id: {
        compact_scope.id: compact_scope,
        deep_sky_scope.id: deep_sky_scope,
    }.get(telescope_id)

    updated = controller._apply_equipment([target])[0]

    assert suggestion["telescopeId"] == deep_sky_scope.id
    assert controller._planner_telescopes_by_object_id([updated]) == {target.id: deep_sky_scope}


def test_app_controller_naked_eye_block_policy_still_matches_legacy_output() -> None:
    controller = AppController.__new__(AppController)
    target = _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification")
    suggestion = EquipmentService().suggest_for_profile(target, [], [], [], binoculars=[])
    controller._equipment_service = _FakeEquipmentService(suggestion)
    controller._equipment_setup_read_model_builder = EquipmentSetupReadModelBuilder()
    controller._seeing_transparency = None
    controller._sky_quality = None
    controller._object_image_map = {}
    controller._object_descriptions = {}
    controller._active_profile_telescopes = lambda: []
    controller._active_profile_eyepieces = lambda: []
    controller._active_profile_barlows = lambda: []
    controller._active_profile_binoculars = lambda: []

    updated = controller._apply_equipment([target])[0]

    assert updated.visible is False
    assert updated.score == max(0, target.score - 45)
    assert updated.recommended_setup == suggestion["setupText"]
    assert updated.setup_options == []


def test_equipment_setup_read_model_has_no_qml_property_exposure() -> None:
    controller_source = inspect.getsource(AppController)
    dependency_source = inspect.getsource(AppControllerDependencies)

    assert "EquipmentSetupReadModelBuilder" in dependency_source
    assert "equipment_setup_read_model_builder" in controller_source
    assert "def equipmentSetupReadModel" not in controller_source
    assert "equipmentSetupReadModel" not in _qml_sources()


class _FakeEquipmentService:
    def __init__(self, suggestion: dict[str, object]) -> None:
        self.suggestion = suggestion

    def suggest_for_profile(self, *args, **kwargs) -> dict[str, object]:
        return self.suggestion


def _qml_sources() -> str:
    ui_root = __file__
    from pathlib import Path

    root = Path(ui_root).resolve().parents[1] / "app" / "ui"
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.qml"))


def _object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
    max_angular_size_deg: float,
    recommended_observation_type: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=80,
        difficulty="Media",
        apparent_size=apparent_size,
        max_angular_size_deg=max_angular_size_deg,
        recommended_observation_type=recommended_observation_type,
    )
