from __future__ import annotations

from astro_viewer.app.models.nsom import IntrinsicTargetQuality, ObservableTargetValue, ObservationEnvironment
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ParticulateConditionInput,
)


def build_home_observable_target_value(
    item: CelestialObject,
    *,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
    seeing: SeeingTransparency | None = None,
    aod: AodConditionInput | None = None,
    particulate: ParticulateConditionInput | None = None,
    moon_geometry: MoonGeometryConditionInput | None = None,
    condition_inputs: ObservationConditionInputs | None = None,
) -> ObservableTargetValue:
    inputs = condition_inputs or ObservationConditionInputs(
        moon=moon,
        sky_quality=sky_quality,
        seeing=seeing,
        aod=aod,
        particulate=particulate,
        moon_geometry=moon_geometry,
    )
    return NsomObservationEnvironmentService().observable_target_value(item, inputs)


def build_home_observation_environment(
    item: CelestialObject,
    intrinsic: IntrinsicTargetQuality,
    *,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
    seeing: SeeingTransparency | None = None,
    aod: AodConditionInput | None = None,
    particulate: ParticulateConditionInput | None = None,
    moon_geometry: MoonGeometryConditionInput | None = None,
    condition_inputs: ObservationConditionInputs | None = None,
) -> ObservationEnvironment:
    del intrinsic
    inputs = condition_inputs or ObservationConditionInputs(
        moon=moon,
        sky_quality=sky_quality,
        seeing=seeing,
        aod=aod,
        particulate=particulate,
        moon_geometry=moon_geometry,
    )
    return NsomObservationEnvironmentService().environment(item, inputs)
