from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject


@dataclass(frozen=True)
class EquipmentSetupOptionReadModel:
    """Internal immutable projection of one setup option payload row."""

    role: str
    label: str
    detail_label: str
    display_label: str
    suggested_position: str
    magnification: str
    true_field: str
    exit_pupil: str
    barlow: str
    score: int | float | None
    telescope_name: str
    equipment_type: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> EquipmentSetupOptionReadModel:
        return cls(
            role=_text(payload, "role"),
            label=_text(payload, "label"),
            detail_label=_text(payload, "detailLabel"),
            display_label=_text(payload, "displayLabel"),
            suggested_position=_text(payload, "suggestedPosition"),
            magnification=_text(payload, "magnification"),
            true_field=_text(payload, "trueField"),
            exit_pupil=_text(payload, "exitPupil"),
            barlow=_text(payload, "barlow"),
            score=_finite_number(payload.get("score")),
            telescope_name=_text(payload, "telescopeName"),
            equipment_type=_text(payload, "equipmentType"),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "role": self.role,
            "label": self.label,
            "detailLabel": self.detail_label,
            "displayLabel": self.display_label,
            "suggestedPosition": self.suggested_position,
            "magnification": self.magnification,
            "trueField": self.true_field,
            "exitPupil": self.exit_pupil,
            "barlow": self.barlow,
            "score": self.score,
            "telescopeName": self.telescope_name,
            "equipmentType": self.equipment_type,
        }


@dataclass(frozen=True)
class EquipmentSetupReadModel:
    """Runtime-neutral boundary between EquipmentService output and UI payload fields."""

    object_id: str
    name: str
    payload_keys: tuple[str, ...]
    best_eyepiece: str
    suggested_position: str
    barlow: str
    difficulty: str
    alternative: str
    high_magnification: str
    wide_field: str
    setup_text: str
    setup_options: tuple[EquipmentSetupOptionReadModel, ...]
    explanation: str
    telescope_id: str
    telescope_name: str
    equipment_type: str
    setup_type: str
    selection_score: int | float | None
    presenter_policy: str = "preserve_equipment_service_payload"
    nsom_policy: str = "observer_capability_reference_only"
    confidence_policy: str = "parallel_metadata_zero_score_effect"

    @property
    def recommended_setup_type(self) -> str:
        if self.setup_type:
            return self.setup_type
        if self.equipment_type == "Binocular":
            return "binocular"
        if self.equipment_type == "Telescope":
            return "telescope"
        for option in self.setup_options:
            if option.role != "Consigliato":
                continue
            if option.equipment_type == "Binocular":
                return "binocular"
            if option.equipment_type == "Telescope":
                return "telescope"
        return ""

    @property
    def requires_optical_instrument(self) -> bool:
        return self.setup_text.startswith("Serve almeno")

    def setup_options_payload(self) -> list[dict[str, object]]:
        return [option.to_payload() for option in self.setup_options]

    def to_equipment_service_payload(self) -> dict[str, object]:
        values: dict[str, object] = {
            "bestEyepiece": self.best_eyepiece,
            "suggestedPosition": self.suggested_position,
            "barlow": self.barlow,
            "difficulty": self.difficulty,
            "alternative": self.alternative,
            "highMagnification": self.high_magnification,
            "wideField": self.wide_field,
            "setupText": self.setup_text,
            "setupOptions": self.setup_options_payload(),
            "explanation": self.explanation,
            "telescopeId": self.telescope_id,
            "telescopeName": self.telescope_name,
            "equipmentType": self.equipment_type,
            "setupType": self.setup_type,
            "selectionScore": self.selection_score,
        }
        return {key: values[key] for key in self.payload_keys if key in values}

    def to_celestial_object_updates(self) -> dict[str, object]:
        return {
            "recommended_setup": self.setup_text,
            "best_eyepiece": self.best_eyepiece,
            "barlow": self.barlow,
            "difficulty": self.difficulty,
            "recommended_setup_type": self.recommended_setup_type,
            "setup_options": self.setup_options_payload(),
            "equipment_explanation": self.explanation,
        }

    def to_dict(self) -> dict[str, object]:
        return nsom_to_json_compatible(self)


class EquipmentSetupReadModelBuilder:
    """Builds immutable Equipment setup read models without changing service output."""

    def from_suggestion(
        self,
        target: CelestialObject,
        suggestion: Mapping[str, object],
    ) -> EquipmentSetupReadModel:
        return EquipmentSetupReadModel(
            object_id=target.id,
            name=target.name,
            payload_keys=tuple(str(key) for key in suggestion.keys()),
            best_eyepiece=_text(suggestion, "bestEyepiece"),
            suggested_position=_text(suggestion, "suggestedPosition"),
            barlow=_text(suggestion, "barlow"),
            difficulty=_text(suggestion, "difficulty"),
            alternative=_text(suggestion, "alternative"),
            high_magnification=_text(suggestion, "highMagnification"),
            wide_field=_text(suggestion, "wideField"),
            setup_text=_text(suggestion, "setupText"),
            setup_options=tuple(
                EquipmentSetupOptionReadModel.from_payload(option)
                for option in _setup_options(suggestion.get("setupOptions"))
            ),
            explanation=_text(suggestion, "explanation"),
            telescope_id=_text(suggestion, "telescopeId"),
            telescope_name=_text(suggestion, "telescopeName"),
            equipment_type=_text(suggestion, "equipmentType"),
            setup_type=_text(suggestion, "setupType"),
            selection_score=_finite_number(suggestion.get("selectionScore")),
        )


def _setup_options(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key, "")
    if value is None:
        return ""
    return str(value)


def _finite_number(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return None
