"""Build Home ObservableTargetValue through the canonical NSOM Sky service."""

from __future__ import annotations

from astro_viewer.app.models.condition_inputs import ObservationConditionInputs
from astro_viewer.app.models.nsom import ObservableTargetValue
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)


def build_home_observable_target_value(
    item: CelestialObject,
    *,
    condition_inputs: ObservationConditionInputs,
) -> ObservableTargetValue:
    return NsomObservationEnvironmentService().observable_target_value(
        item,
        condition_inputs,
    )
