"""Expose inspectable optical setup score components without changing policy."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from astro_viewer.app.models.nsom import nsom_to_json_compatible


EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER: tuple[str, ...] = (
    "angular_scale",
    "magnification",
    "exit_pupil",
    "light_gathering",
    "seeing_compatibility",
    "handling",
)

EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "angular_scale": 24.0,
        "magnification": 24.0,
        "exit_pupil": 16.0,
        "light_gathering": 16.0,
        "seeing_compatibility": 10.0,
        "handling": 10.0,
    }
)

EQUIPMENT_SETUP_SCORE_COMPONENT_METADATA: Mapping[str, Mapping[str, object]] = MappingProxyType(
    {
        "angular_scale": {
            "current_inputs": (
                "target apparent size",
                "true field",
                "target profile mode",
            ),
            "nsom_layers": ("universe", "observer", "presentation/setup"),
            "replacement_policy": (
                "Keep as setup compatibility; do not fold into ObservableTargetValue."
            ),
        },
        "magnification": {
            "current_inputs": ("configuration magnification", "target profile idealMag"),
            "nsom_layers": ("observer", "presentation/setup"),
            "replacement_policy": (
                "Keep as setup compatibility; Q_target may reference capability but "
                "must not replace focal-position selection."
            ),
        },
        "exit_pupil": {
            "current_inputs": (
                "configuration exit pupil",
                "target profile idealExit",
                "sky-adjusted profile",
            ),
            "nsom_layers": ("observer", "sky", "presentation/setup"),
            "replacement_policy": (
                "Requires explicit setup context because sky quality can alter ideal exit pupil."
            ),
        },
        "light_gathering": {
            "current_inputs": (
                "aperture/objective",
                "target magnitude",
                "surface brightness proxy",
                "sky quality",
            ),
            "nsom_layers": ("universe", "observer", "sky"),
            "replacement_policy": (
                "Split before replacement; target faintness and sky quality cannot be hidden inside observer capability."
            ),
        },
        "seeing_compatibility": {
            "current_inputs": (
                "configuration magnification",
                "seeing-limited maxUsefulMag",
            ),
            "nsom_layers": ("sky", "session", "observer", "presentation/setup"),
            "replacement_policy": (
                "Keep separate from ObserverCapability until seeing/session ownership is explicit."
            ),
        },
        "handling": {
            "current_inputs": (
                "Barlow multiplier",
                "binocular stabilization",
                "target profile barlowFriendly",
            ),
            "nsom_layers": ("observer", "presentation/setup"),
            "replacement_policy": (
                "Presentation/practical setup factor; not target physics and not RecommendationConfidence."
            ),
        },
    }
)

EQUIPMENT_SETUP_SCORE_FORMULA = (
    "angular_scale + magnification + exit_pupil + light_gathering + "
    "seeing_compatibility + handling"
)


@dataclass(frozen=True)
class EquipmentSetupScoreComponent:
    """Immutable internal read-model for one Equipment setup-score component."""

    name: str
    value: float
    weight: float
    current_inputs: tuple[str, ...]
    nsom_layers: tuple[str, ...]
    replacement_policy: str


@dataclass(frozen=True)
class EquipmentSetupScoreReadModel:
    """Runtime-neutral component boundary for EquipmentService setup scoring."""

    components: tuple[EquipmentSetupScoreComponent, ...]
    unclamped_score: float
    score: float
    formula: str = EQUIPMENT_SETUP_SCORE_FORMULA
    formula_source: str = "EquipmentService._configuration_score"
    score_policy: str = "sum_components_clamped_0_100"
    runtime_policy: str = "preserve_equipment_service_score"
    nsom_policy: str = "setup_score_component_boundary_not_nsom_target_value"
    confidence_policy: str = "parallel_metadata_zero_score_effect"

    def component_values(self) -> dict[str, float]:
        return {component.name: component.value for component in self.components}

    def component_weights(self) -> dict[str, float]:
        return {component.name: component.weight for component in self.components}

    def to_dict(self) -> dict[str, object]:
        return nsom_to_json_compatible(
            {
                "components": self.components,
                "component_values": self.component_values(),
                "component_weights": self.component_weights(),
                "unclamped_score": self.unclamped_score,
                "score": self.score,
                "formula": self.formula,
                "formula_source": self.formula_source,
                "score_policy": self.score_policy,
                "runtime_policy": self.runtime_policy,
                "nsom_policy": self.nsom_policy,
                "confidence_policy": self.confidence_policy,
            }
        )


class EquipmentSetupScoreReadModelBuilder:
    """Builds immutable component read-models without changing score math."""

    def from_component_values(
        self,
        component_values: Mapping[str, float],
    ) -> EquipmentSetupScoreReadModel:
        components = tuple(
            self._component(name, component_values.get(name, 0.0))
            for name in EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER
        )
        unclamped_score = sum(component.value for component in components)
        return EquipmentSetupScoreReadModel(
            components=components,
            unclamped_score=unclamped_score,
            score=max(0.0, min(100.0, unclamped_score)),
        )

    @staticmethod
    def _component(name: str, value: float) -> EquipmentSetupScoreComponent:
        metadata = EQUIPMENT_SETUP_SCORE_COMPONENT_METADATA[name]
        return EquipmentSetupScoreComponent(
            name=name,
            value=float(value),
            weight=EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS[name],
            current_inputs=tuple(str(item) for item in metadata["current_inputs"]),
            nsom_layers=tuple(str(item) for item in metadata["nsom_layers"]),
            replacement_policy=str(metadata["replacement_policy"]),
        )
