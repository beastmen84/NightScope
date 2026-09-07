"""Calculate observing refreshes on detached state, without a Qt controller.

Outer containers are copied at capture. Frozen domain records and stateless
services are borrowed read-only; neither the worker nor presentation may mutate
their nested setup options. Only the returned fields are eligible for publication.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, replace

from astro_viewer.app.application.catalogue_recommendations import (
    apply_object_content_from_sources,
    moon_geometry_summary_to_condition_input,
    sky_compass_observable_target,
)
from astro_viewer.app.application.observing_calculations import ObservingCalculations, ObservingRefreshCancelled
from astro_viewer.app.application.snapshots import CatalogueRecommendationPreparationContext
from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.observing import CelestialObject, MoonGeometrySummary
from astro_viewer.app.services.catalogue_query_service import CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG
from astro_viewer.app.services.home_target_timing import HomeTargetTimingSnapshot
from astro_viewer.app.services.observing_time import first_observing_datetime
from astro_viewer.app.services.sky_compass_service import SkyCompassService


logger = logging.getLogger(__name__)

# Explicit boundary: no repositories, settings, QObject, signals or timers.
STATE_FIELDS = (
    "_base_solar_system_objects", "_base_deep_sky", "_solar_system_objects", "_visible_planets", "_deep_sky",
    "_equipment_setup_read_models_by_object_id", "_deep_sky_raw_condition_input_by_id", "_deep_sky_pollution_read_model",
    "_conditioned_deep_sky", "_conditioned_home_objects", "_conditioned_deep_sky_read_model", "_conditioned_home_read_model",
    "_category_scores", "_best_object", "_night_plan", "_moon_geometry_condition_cache",
)
SERVICE_FIELDS = (
    "_equipment_service", "_equipment_setup_read_model_builder", "_conditions_service", "_conditions_read_model_builder",
    "_home_recommended_deep_sky_nsom_ranking_service", "_nsom_category_score_service", "_best_object_nsom_selection_service",
    "_night_planner_service",
)


@dataclass(frozen=True)
class ObservingEquipmentSnapshot:
    """Retain a rebuild's inputs, not calculations or a controller reference."""

    context: CatalogueRecommendationPreparationContext
    solar_system_source: tuple[CelestialObject, ...]
    deep_sky_source: tuple[CelestialObject, ...]

    def same_equipment_inputs(self, other: ObservingEquipmentSnapshot | None) -> bool:
        if other is None:
            return False
        fields = ("telescopes", "eyepieces", "barlows", "binoculars", "seeing_transparency", "sky_quality")
        return (self.solar_system_source == other.solar_system_source
                and self.deep_sky_source == other.deep_sky_source
                and all(getattr(self.context, name) == getattr(other.context, name) for name in fields))


@dataclass(frozen=True)
class ObservingRefreshInputs:
    context: CatalogueRecommendationPreparationContext
    state: dict[str, object]
    location: ObserverLocation | None
    enabled_objects: dict[str, bool]
    catalogue_rows: tuple[dict, ...]
    catalogue_year: int
    catalogue_month: int
    visibility_cached: bool
    visibility: dict[str, bool] | None
    rebuild_equipment: bool
    apply_pollution: bool
    recalculate_outputs: bool | None = True
    refresh_pollution_context: bool = False
    equipment_snapshot: ObservingEquipmentSnapshot | None = None
    pollution_snapshot: ObservingEquipmentSnapshot | None = None


class ObservingRefreshCalculation(ObservingCalculations):
    """Worker-owned host for the exact routines also used by AppController."""

    def __init__(self, inputs: ObservingRefreshInputs, services: dict, engine, engine_lock,
                 cancelled: Callable[[], bool] = lambda: False):
        self.inputs = inputs
        self._context = inputs.context
        self._cancelled = cancelled
        for name in STATE_FIELDS:
            value = inputs.state[name]
            setattr(self, name, value.copy() if isinstance(value, (dict, list)) else value)
        for name in SERVICE_FIELDS:
            setattr(self, name, services[name])
        self._location = inputs.location
        self._astronomy_engine = engine
        self._engine_lock = engine_lock
        self._observing_night_window = self._context.observing_night_window
        self._seeing_transparency = self._context.seeing_transparency
        self._sky_quality = self._context.sky_quality
        self._weather_summary = self._context.weather_summary
        self._telescopes_by_id = dict(self._context.telescopes_by_id)
        self._recommendation_enabled_by_object_id = inputs.enabled_objects
        self._sky_compass_service = SkyCompassService()
        self.sky_compass = None
        self.sky_compass_candidates = None
        self._visibility_ready = inputs.visibility_cached
        self.visibility = inputs.visibility
        self.home_target_timing = None

    def check_cancelled(self):
        if self._cancelled():
            raise ObservingRefreshCancelled()

    _check_observing_cancelled = check_cancelled

    def calculate(self):
        self.check_cancelled()
        equipment = self.inputs.equipment_snapshot
        pollution = self.inputs.pollution_snapshot
        separate_pollution = pollution is not None and not pollution.same_equipment_inputs(equipment)
        if separate_pollution:
            # Preserve the earlier profile/VIIRS raw inputs even if weather has
            # since changed the equipment advice. Intermediate rankings are not
            # needed, and no intermediate result leaves this worker.
            self._rebuild_equipment(pollution)
            self.check_cancelled()
            with self._using_equipment_snapshot(pollution):
                self._apply_deep_sky_pollution_context(self._deep_sky)
            self.check_cancelled()
        if self.inputs.rebuild_equipment:
            self._rebuild_equipment(equipment)
        self.check_cancelled()
        if not separate_pollution and (self.inputs.apply_pollution or self.inputs.refresh_pollution_context):
            # A profile/VIIRS refresh also replaces raw NSOM inputs and the
            # pollution read model. A later weather/month rebuild retains those
            # effects, but leaves the final deep-sky display unconditioned.
            with self._using_equipment_snapshot(pollution or equipment):
                conditioned = self._apply_deep_sky_pollution_context(self._deep_sky)
            if self.inputs.apply_pollution:
                self._deep_sky = conditioned
        self.check_cancelled()
        if self.inputs.recalculate_outputs is True:
            self._recalculate_observing_outputs()
        elif self.inputs.recalculate_outputs is False:
            self._refresh_conditioned_observing_candidates()
            self._best_object = None
            self._night_plan = []
            self._refresh_sky_compass()
        else:
            self._refresh_conditioned_observing_candidates()
        self.check_cancelled()
        self.home_target_timing = HomeTargetTimingSnapshot.build(
            self._tonight_target_pool(), self._observing_night_window,
            check_cancelled=self.check_cancelled,
        )
        self.check_cancelled()
        return self

    def _rebuild_equipment(self, snapshot: ObservingEquipmentSnapshot | None):
        with self._using_equipment_snapshot(snapshot):
            if snapshot is not None:
                # Empty sources must not fall back to an earlier preparation.
                self._solar_system_objects = list(snapshot.solar_system_source)
                self._deep_sky = list(snapshot.deep_sky_source)
            self._refresh_equipment_recommendations_for_current_objects(refresh_conditioned=False)

    @contextmanager
    def _using_equipment_snapshot(self, snapshot: ObservingEquipmentSnapshot | None):
        if snapshot is None:
            yield
            return
        context, sky, seeing = self._context, self._sky_quality, self._seeing_transparency
        solar, deep_sky = self._base_solar_system_objects, self._base_deep_sky
        captured = snapshot.context
        self._context = replace(
            context, telescopes=captured.telescopes, eyepieces=captured.eyepieces,
            barlows=captured.barlows, binoculars=captured.binoculars,
            pollution_condition_inputs=captured.pollution_condition_inputs,
        )
        self._sky_quality, self._seeing_transparency = captured.sky_quality, captured.seeing_transparency
        self._base_solar_system_objects = list(snapshot.solar_system_source)
        self._base_deep_sky = list(snapshot.deep_sky_source)
        try:
            yield
        finally:
            self._context, self._sky_quality, self._seeing_transparency = context, sky, seeing
            self._base_solar_system_objects, self._base_deep_sky = solar, deep_sky

    def results(self):
        return {name: getattr(self, name) for name in STATE_FIELDS}

    def _active_profile_telescopes(self):
        return list(self._context.telescopes)

    def _active_profile_eyepieces(self):
        return list(self._context.eyepieces)

    def _active_profile_barlows(self):
        return list(self._context.barlows)

    def _active_profile_binoculars(self):
        return list(self._context.binoculars)

    def _current_telescope(self):
        return self._context.current_telescope

    def _find_telescope(self, telescope_id):
        return self._telescopes_by_id.get(telescope_id)

    def _build_observation_condition_inputs(self, *, include_moon=True):
        return self._context.condition_inputs if include_moon else self._context.pollution_condition_inputs

    def _apply_object_content(self, item):
        self.check_cancelled()
        return apply_object_content_from_sources(item, self._context.object_image_map, self._context.object_descriptions,
                                                self._context.catalogue_identifier_index)

    def _first_observing_datetime(self, value):
        return first_observing_datetime(value, self._observing_night_window)

    def _solar_system_monthly_visible_for_home(self, item):
        row = self._context.catalogue_identifier_index.get(item.id.strip().casefold())
        if row is None or self._location is None:
            return True
        if not self._visibility_ready:
            self._visibility_ready = True
            method = getattr(self._astronomy_engine, "catalogue_month_visibility", None)
            self.visibility = {}
            if callable(method):
                try:
                    with self._engine_lock:
                        self.check_cancelled()
                        result = method(self.inputs.catalogue_rows, self._location, self.inputs.catalogue_year,
                                        self.inputs.catalogue_month, CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG)
                    self.visibility = {str(key): bool(value) for key, value in result.items()}
                except ObservingRefreshCancelled:
                    raise
                except Exception:
                    logger.warning("Catalogue monthly visibility calculation failed.", exc_info=True)
                    self.visibility = None
        return (self.visibility or {}).get(str(row.get("object_id", ""))) is not False

    def _astronomy_engine_lock_instance(self):
        self.check_cancelled()
        return self._engine_lock

    _moon_geometry_summary_to_condition_input = staticmethod(moon_geometry_summary_to_condition_input)
    _sky_compass_observable_target = staticmethod(sky_compass_observable_target)

    def _moon_geometry_condition_input(self, target):
        self.check_cancelled()
        if target.id in self._moon_geometry_condition_cache:
            return self._moon_geometry_condition_cache[target.id]
        summary = None
        method = getattr(self._astronomy_engine, "moon_geometry", None)
        if self._location is not None and callable(method):
            try:
                with self._engine_lock:
                    self.check_cancelled()
                    summary = method(self._location, target)
            except ObservingRefreshCancelled:
                raise
            except Exception:
                logger.debug("Moon geometry unavailable for observing refresh.", exc_info=True)
        value = moon_geometry_summary_to_condition_input(summary if isinstance(summary, MoonGeometrySummary) else None)
        self._moon_geometry_condition_cache[target.id] = value
        return value

    def _refresh_sky_compass(self):
        self.check_cancelled()
        candidates = self._sky_compass_candidates()
        self.sky_compass_candidates = list(candidates)
        self._sky_compass_service.reset_live_direction_stability()
        kwargs = dict(has_location=self._location is not None, caution_text=self._context.sky_compass_caution_text)
        try:
            self.sky_compass = self._sky_compass_service.live_compass(
                candidates, self._night_plan, self._best_object, **kwargs,
                observable_objects_by_id=self._sky_compass_observable_targets_by_id(candidates),
                condition_inputs=self._build_observation_condition_inputs(),
                moon_geometry_by_object_id=self._planner_moon_geometry_inputs(candidates),
            )
        except ObservingRefreshCancelled:
            raise
        except Exception:
            logger.warning("NSOM Sky Compass selection failed; using geometry fallback.", exc_info=True)
            self.sky_compass = self._sky_compass_service.live_compass(candidates, self._night_plan, self._best_object, **kwargs)
