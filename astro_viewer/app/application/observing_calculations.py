"""Share observing calculations between Qt orchestration and detached worker state.

The host supplies input snapshots, domain services and publication adapters. These
methods retain the existing controller arithmetic and admission policies; they do
not create Qt objects, emit signals, access repositories or choose refresh cadence.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import replace

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.condition_inputs import MoonGeometryConditionInput, ObservationConditionInputs
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonGeometrySummary
from astro_viewer.app.services.nsom_target import unique_targets_by_id
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionedTargetReadModel,
    ObservationConditionsReadModelBuilder,
)

logger = logging.getLogger(__name__)


class ObservingRefreshCancelled(Exception):
    """A newer request superseded the calculation before publication."""


class ObservingCalculations:
    """Calculation-only mixin; mutable outputs belong exclusively to its host."""

    def _check_observing_cancelled(self) -> None:
        """Synchronous hosts need no cancellation; workers override this boundary."""

    def _recalculate_observing_outputs(self) -> None:
        self._check_observing_cancelled()
        self._category_scores = self._nsom_category_score_service.scores(
            self._build_observation_condition_inputs()
        )
        self._refresh_conditioned_observing_candidates()
        self._check_observing_cancelled()
        planning_objects = self._home_visible_objects(self._visible_planets + self._deep_sky)
        planning_objects = planning_objects or list(
            unique_targets_by_id(self._visible_planets + self._deep_sky)
        )
        planner_moon_geometry = self._planner_moon_geometry_inputs(planning_objects)
        planner_telescopes = self._planner_telescopes_by_object_id(planning_objects)
        condition_inputs = self._build_observation_condition_inputs()
        self._best_object = self._select_best_object(
            planning_objects,
            condition_inputs=condition_inputs,
            moon_geometry_by_object_id=planner_moon_geometry,
            telescope_by_object_id=planner_telescopes,
        )
        self._check_observing_cancelled()
        planner_kwargs = {}
        if planner_moon_geometry is not None:
            planner_kwargs["moon_geometry_by_object_id"] = planner_moon_geometry
        if getattr(self._night_planner_service, "uses_target_equipment", False):
            planner_kwargs["telescope_by_object_id"] = planner_telescopes
        planner_kwargs["condition_inputs"] = condition_inputs
        night_window = getattr(self, "_observing_night_window", None)
        if isinstance(night_window, ObservingNightWindow) and night_window.has_observing_window:
            planner_kwargs["night_window"] = night_window
        self._night_plan = self._night_planner_service.plan(
            planning_objects,
            self._weather_summary,
            self._current_telescope(),
            **planner_kwargs,
        )
        self._check_observing_cancelled()
        self._refresh_sky_compass()

    def _planner_telescopes_by_object_id(
        self,
        targets: list[CelestialObject],
    ) -> dict[str, Telescope]:
        setup_models = getattr(self, "_equipment_setup_read_models_by_object_id", {})
        telescopes: dict[str, Telescope] = {}
        for target in targets:
            setup = setup_models.get(target.id)
            if setup is None or setup.equipment_type != "Telescope" or not setup.telescope_id:
                continue
            telescope = self._find_telescope(setup.telescope_id)
            if telescope is not None:
                telescopes[target.id] = telescope
        return telescopes

    def _planner_moon_geometry_inputs(
        self,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometryConditionInput]:
        self._populate_moon_geometry_condition_cache(targets)
        geometry_by_id: dict[str, MoonGeometryConditionInput] = {}
        for target in targets:
            geometry = self._moon_geometry_condition_input(target)
            if geometry is not None:
                geometry_by_id[target.id] = geometry
        return geometry_by_id

    def _populate_moon_geometry_condition_cache(self, targets: list[CelestialObject]) -> None:
        cache = getattr(self, "_moon_geometry_condition_cache", None)
        if cache is None:
            cache = {}
            self._moon_geometry_condition_cache = cache
        missing = [target for target in targets if target.id not in cache]
        batch_method = getattr(getattr(self, "_astronomy_engine", None), "moon_geometry_batch", None)
        if not missing or not callable(batch_method):
            return
        try:
            with self._astronomy_engine_lock_instance():
                self._check_observing_cancelled()
                summaries = batch_method(self._location, missing)
        except ObservingRefreshCancelled:
            raise
        except Exception:
            logger.debug("Moon geometry batch failed; using per-target fallback.", exc_info=True)
            return
        if not isinstance(summaries, Mapping):
            return
        for target in missing:
            if target.id not in summaries:
                continue
            summary = summaries[target.id]
            cache[target.id] = self._moon_geometry_summary_to_condition_input(
                summary if isinstance(summary, MoonGeometrySummary) else None
            )

    def _select_best_object(
        self,
        planning_objects: list[CelestialObject],
        *,
        condition_inputs: ObservationConditionInputs | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
        telescope_by_object_id: Mapping[str, Telescope] | None = None,
    ) -> CelestialObject | None:
        if not self._weather_summary:
            return None
        candidate_read_models = self._best_object_read_models(planning_objects)
        selected_raw_target = self._best_object_nsom_selection_service.best_object(
            [model.nsom_target_input for model in candidate_read_models],
            weather=self._weather_summary,
            telescope=self._current_telescope(),
            condition_inputs=condition_inputs or self._build_observation_condition_inputs(),
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            telescope_by_object_id=telescope_by_object_id,
        )
        if selected_raw_target is None:
            return None
        display_targets_by_raw_id = {
            model.nsom_target_input.id: model.qml_display_target
            for model in candidate_read_models
        }
        return display_targets_by_raw_id.get(selected_raw_target.id, selected_raw_target)

    def _best_object_read_models(
        self,
        planning_objects: list[CelestialObject],
    ) -> tuple[ObservationConditionedTargetReadModel, ...]:
        existing_models = {
            model.object_id: model
            for model in getattr(self, "_conditioned_home_read_model", [])
        }
        missing_objects = [
            item
            for item in planning_objects
            if item.id not in existing_models
        ]
        if missing_objects:
            fallback_models = self._conditions_read_model_builder_instance().from_display_targets(
                missing_objects,
                source="best_object_nsom_raw_observable_order_fallback",
                raw_targets_by_id=self._conditioned_raw_targets_by_id(),
            )
            existing_models.update({model.object_id: model for model in fallback_models})
        return tuple(
            existing_models[item.id]
            for item in planning_objects
            if item.id in existing_models
        )

    def _sky_compass_candidates(self) -> list[CelestialObject]:
        return self._tonight_target_pool()

    def _sky_compass_observable_targets_by_id(
        self,
        candidates: list[CelestialObject],
    ) -> dict[str, CelestialObject]:
        read_models = {
            model.object_id: model
            for model in getattr(self, "_conditioned_home_read_model", [])
        }
        raw_targets_by_id = self._conditioned_raw_targets_by_id()
        observable_targets = {}
        for display_target in candidates:
            model = read_models.get(display_target.id)
            raw_target = model.nsom_target_input if model else raw_targets_by_id.get(display_target.id, display_target)
            observable_targets[display_target.id] = self._sky_compass_observable_target(
                raw_target,
                display_target,
            )
        return observable_targets

    def _refresh_equipment_recommendations_for_current_objects(
        self,
        *,
        refresh_conditioned: bool = True,
    ) -> None:
        solar_system_source = self._base_solar_system_objects or self._solar_system_objects
        deep_sky_source = self._base_deep_sky or self._deep_sky
        deep_sky_source = self._recommendation_eligible_objects(deep_sky_source)
        self._equipment_setup_read_models_by_object_id = {}
        self._solar_system_objects = self._apply_equipment(solar_system_source)
        self._visible_planets = [
            item
            for item in self._solar_system_objects
            if item.object_type == "Pianeta"
            and item.visible
            and self._solar_system_monthly_visible_for_home(item)
        ]
        self._deep_sky = self._apply_equipment(deep_sky_source)
        if refresh_conditioned:
            self._refresh_conditioned_observing_candidates()

    def _recommendation_eligible_objects(
        self,
        objects: list[CelestialObject],
    ) -> list[CelestialObject]:
        enabled_by_id = getattr(
            self,
            "_recommendation_enabled_by_object_id",
            {},
        )
        return [
            item
            for item in objects
            if enabled_by_id.get(item.id.strip().casefold(), True)
        ]

    def _apply_equipment(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        telescopes = self._active_profile_telescopes()
        eyepieces = self._active_profile_eyepieces()
        barlows = self._active_profile_barlows()
        binoculars = self._active_profile_binoculars()
        updated = []
        for item in objects:
            suggestion = self._equipment_service.suggest_for_profile(
                item,
                telescopes,
                eyepieces,
                barlows,
                self._seeing_transparency,
                self._sky_quality,
                binoculars,
            )
            setup_read_model = self._equipment_setup_read_model_builder.from_suggestion(item, suggestion)
            setup_models = getattr(self, "_equipment_setup_read_models_by_object_id", None)
            if setup_models is None:
                setup_models = {}
                self._equipment_setup_read_models_by_object_id = setup_models
            setup_models[item.id] = setup_read_model
            naked_eye_blocked = (
                not telescopes
                and not binoculars
                and setup_read_model.requires_optical_instrument
            )
            setup_updates = setup_read_model.to_celestial_object_updates()
            updated.append(
                self._apply_object_content(
                    replace(
                        item,
                        visible=item.visible and not naked_eye_blocked,
                        score=max(0, item.score - 45) if naked_eye_blocked else item.score,
                        **setup_updates,
                    )
                )
            )
        return updated

    def _apply_deep_sky_pollution_context(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        self._deep_sky_raw_condition_input_by_id = {item.id: item for item in objects}
        conditioned = self._conditions_service.condition_deep_sky_pollution_context(
            objects,
            self._sky_quality,
            self._build_observation_condition_inputs(include_moon=False),
        )
        builder = self._conditions_read_model_builder_instance()
        self._deep_sky_pollution_read_model = list(
            builder.from_conditioned_targets(
                conditioned,
                source="deep_sky_pollution_context",
                raw_targets_by_id=self._deep_sky_raw_condition_input_by_id,
            )
        )
        return [model.display_target for model in self._deep_sky_pollution_read_model]

    def _conditions_read_model_builder_instance(self) -> ObservationConditionsReadModelBuilder:
        builder = getattr(self, "_conditions_read_model_builder", None)
        if builder is None:
            builder = ObservationConditionsReadModelBuilder()
            self._conditions_read_model_builder = builder
        return builder

    def _home_visible_objects(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        return list(
            unique_targets_by_id(
                item
                for item in objects
                if self._first_observing_datetime(item.best_time)
                or self._first_observing_datetime(item.observing_window)
            )
        )

    def _tonight_target_pool(self) -> list[CelestialObject]:
        candidates = self._home_visible_objects(self._visible_planets)
        candidates.extend(self._conditioned_deep_sky_candidates())
        return list(unique_targets_by_id(candidates))

    def _refresh_conditioned_observing_candidates(self) -> None:
        conditioned_deep_sky_read_model = self._recommended_deep_sky_read_models(
            self._home_visible_objects(self._deep_sky)
        )
        conditioned_deep_sky = [
            model.qml_display_target for model in conditioned_deep_sky_read_model
        ]
        self._conditioned_deep_sky = conditioned_deep_sky
        self._conditioned_deep_sky_read_model = list(conditioned_deep_sky_read_model)
        visible_planets = self._home_visible_objects(self._visible_planets)
        self._conditioned_home_objects = list(
            unique_targets_by_id(visible_planets + conditioned_deep_sky)
        )
        visible_planet_read_model = self._conditions_read_model_builder_instance().from_display_targets(
            visible_planets,
            source="home_observing_candidates_planets",
            raw_targets_by_id=self._conditioned_raw_targets_by_id(),
        )
        self._conditioned_home_read_model = list(
            unique_targets_by_id(
                (*visible_planet_read_model, *conditioned_deep_sky_read_model)
            )
        )

    def _recommended_deep_sky_read_models(
        self,
        objects: list[CelestialObject],
    ) -> tuple[ObservationConditionedTargetReadModel, ...]:
        raw_targets_by_id = self._conditioned_raw_targets_by_id()
        builder = self._conditions_read_model_builder_instance()
        candidate_read_models = builder.from_display_targets(
            objects,
            source="home_recommended_deep_sky_nsom_raw_observable_order",
            raw_targets_by_id=raw_targets_by_id,
        )
        ranked_nsom_targets = self._home_recommended_deep_sky_nsom_ranking_service.rank_by_observable_target_value(
            [model.nsom_target_input for model in candidate_read_models],
            condition_inputs=self._build_observation_condition_inputs(),
            moon_geometry_by_object_id=self._planner_moon_geometry_inputs(
                [model.nsom_target_input for model in candidate_read_models]
            ),
        )
        models_by_raw_id = {model.nsom_target_input.id: model for model in candidate_read_models}
        return tuple(
            models_by_raw_id[target.id]
            for target in ranked_nsom_targets
            if target.id in models_by_raw_id
        )

    def _conditioned_deep_sky_candidates(self) -> list[CelestialObject]:
        if not hasattr(self, "_conditioned_deep_sky"):
            self._refresh_conditioned_observing_candidates()
        if not self._conditioned_deep_sky and self._home_visible_objects(self._deep_sky):
            self._refresh_conditioned_observing_candidates()
        return list(self._conditioned_deep_sky)

    def _conditioned_raw_targets_by_id(self) -> dict[str, CelestialObject]:
        raw_targets = dict(getattr(self, "_deep_sky_raw_condition_input_by_id", {}))
        raw_targets.update({item.id: item for item in getattr(self, "_visible_planets", [])})
        return raw_targets
