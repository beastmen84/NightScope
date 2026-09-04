"""Prepare catalogue recommendation results outside the mutable Qt boundary."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace

from astro_viewer.app.application.snapshots import (
    AstronomyRefreshSnapshot,
    CatalogueRecommendationPreparationContext,
    PreparedCatalogueRecommendationSnapshot,
)
from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.condition_inputs import MoonGeometryConditionInput
from astro_viewer.app.models.observing import CelestialObject, MoonGeometrySummary
from astro_viewer.app.services.best_object_nsom_ranking import (
    BestObjectNsomSelectionService,
)
from astro_viewer.app.services.catalogue_records import is_editorial_placeholder
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupReadModel,
    EquipmentSetupReadModelBuilder,
)
from astro_viewer.app.services.home_nsom_ranking import (
    HomeRecommendedDeepSkyNsomRankingService,
)
from astro_viewer.app.services.localization import join_text, presentation_text
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_category_score_service import (
    NsomCategoryScoreService,
)
from astro_viewer.app.services.nsom_target import unique_targets_by_id
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionsService,
)
from astro_viewer.app.services.sky_compass_service import SkyCompassService


logger = logging.getLogger(__name__)
SOLAR_SYSTEM_CATALOGUE = "Sistema Solare"


class CatalogueRecommendationWorkflow:
    """Prepares a complete recommendation snapshot away from the Qt boundary."""

    def __init__(
        self,
        *,
        equipment_service: EquipmentService,
        equipment_setup_read_model_builder: EquipmentSetupReadModelBuilder,
        conditions_service: ObservationConditionsService,
        conditions_read_model_builder: ObservationConditionsReadModelBuilder,
        home_ranking_service: HomeRecommendedDeepSkyNsomRankingService,
        category_score_service: NsomCategoryScoreService,
        best_object_service: BestObjectNsomSelectionService,
        night_planner_service: NightPlannerService,
        sky_compass_service: SkyCompassService,
    ) -> None:
        self._equipment_service = equipment_service
        self._equipment_setup_read_model_builder = equipment_setup_read_model_builder
        self._conditions_service = conditions_service
        self._conditions_read_model_builder = conditions_read_model_builder
        self._home_ranking_service = home_ranking_service
        self._category_score_service = category_score_service
        self._best_object_service = best_object_service
        self._night_planner_service = night_planner_service
        self._sky_compass_service = sky_compass_service

    def prepare(
        self,
        astronomy: AstronomyRefreshSnapshot,
        context: CatalogueRecommendationPreparationContext,
    ) -> PreparedCatalogueRecommendationSnapshot:
        deep_sky, deep_sky_setup_models = self._prepare_equipment(
            astronomy.deep_sky,
            context,
        )
        setup_models = dict(context.solar_setup_models)
        setup_models.update(deep_sky_setup_models)
        raw_deep_sky_by_id = {item.id: item for item in deep_sky}

        conditioned_pollution = (
            self._conditions_service.condition_deep_sky_pollution_context(
                list(deep_sky),
                context.sky_quality,
                context.pollution_condition_inputs,
            )
        )
        pollution_read_models = (
            self._conditions_read_model_builder.from_conditioned_targets(
                conditioned_pollution,
                source="deep_sky_pollution_context",
                raw_targets_by_id=raw_deep_sky_by_id,
            )
        )
        pollution_adjusted_deep_sky = tuple(
            model.display_target for model in pollution_read_models
        )

        moon_geometry_by_id = dict(context.moon_geometry_by_object_id)
        moon_geometry_by_id.update(
            (
                object_id,
                moon_geometry_summary_to_condition_input(summary),
            )
            for object_id, summary in astronomy.moon_geometry
        )
        home_deep_sky = home_visible_objects_for_window(
            pollution_adjusted_deep_sky,
            context.observing_night_window,
        )
        candidate_read_models = (
            self._conditions_read_model_builder.from_display_targets(
                list(home_deep_sky),
                source="home_recommended_deep_sky_nsom_raw_observable_order",
                raw_targets_by_id=raw_deep_sky_by_id,
            )
        )
        ranked_nsom_targets = self._home_ranking_service.rank_by_observable_target_value(
            [model.nsom_target_input for model in candidate_read_models],
            condition_inputs=context.condition_inputs,
            moon_geometry_by_object_id=moon_geometry_by_id,
        )
        models_by_raw_id = {
            model.nsom_target_input.id: model for model in candidate_read_models
        }
        conditioned_deep_sky_read_models = tuple(
            models_by_raw_id[target.id]
            for target in ranked_nsom_targets
            if target.id in models_by_raw_id
        )
        conditioned_deep_sky = tuple(
            model.qml_display_target for model in conditioned_deep_sky_read_models
        )

        visible_planets = home_visible_objects_for_window(
            context.visible_planets,
            context.observing_night_window,
        )
        raw_targets_by_id = dict(raw_deep_sky_by_id)
        raw_targets_by_id.update((item.id, item) for item in context.visible_planets)
        visible_planet_read_models = (
            self._conditions_read_model_builder.from_display_targets(
                list(visible_planets),
                source="home_observing_candidates_planets",
                raw_targets_by_id=raw_targets_by_id,
            )
        )
        conditioned_home_read_models = tuple(
            unique_targets_by_id(
                (
                    *visible_planet_read_models,
                    *conditioned_deep_sky_read_models,
                )
            )
        )
        conditioned_home_objects = tuple(
            unique_targets_by_id((*visible_planets, *conditioned_deep_sky))
        )

        category_scores = self._category_score_service.scores(
            context.condition_inputs
        )
        planning_objects = list(
            home_visible_objects_for_window(
                (*context.visible_planets, *pollution_adjusted_deep_sky),
                context.observing_night_window,
            )
        )
        if not planning_objects:
            planning_objects = list(
                unique_targets_by_id(
                    (
                        *context.visible_planets,
                        *pollution_adjusted_deep_sky,
                    )
                )
            )

        telescopes_by_id = dict(context.telescopes_by_id)
        planner_telescopes = {}
        for target in planning_objects:
            setup = setup_models.get(target.id)
            if (
                setup is None
                or setup.equipment_type != "Telescope"
                or not setup.telescope_id
            ):
                continue
            telescope = telescopes_by_id.get(setup.telescope_id)
            if telescope is not None:
                planner_telescopes[target.id] = telescope

        existing_models = {
            model.object_id: model for model in conditioned_home_read_models
        }
        missing_objects = [
            item for item in planning_objects if item.id not in existing_models
        ]
        if missing_objects:
            fallback_models = self._conditions_read_model_builder.from_display_targets(
                missing_objects,
                source="best_object_nsom_raw_observable_order_fallback",
                raw_targets_by_id=raw_targets_by_id,
            )
            existing_models.update(
                (model.object_id, model) for model in fallback_models
            )
        best_object_read_models = tuple(
            existing_models[item.id]
            for item in planning_objects
            if item.id in existing_models
        )

        best_object = None
        night_plan = ()
        if context.weather_summary is not None:
            selected_raw_target = self._best_object_service.best_object(
                [model.nsom_target_input for model in best_object_read_models],
                weather=context.weather_summary,
                telescope=context.current_telescope,
                condition_inputs=context.condition_inputs,
                moon_geometry_by_object_id=moon_geometry_by_id,
                telescope_by_object_id=planner_telescopes,
            )
            if selected_raw_target is not None:
                display_targets_by_raw_id = {
                    model.nsom_target_input.id: model.qml_display_target
                    for model in best_object_read_models
                }
                best_object = display_targets_by_raw_id.get(
                    selected_raw_target.id,
                    selected_raw_target,
                )

            planner_kwargs = {
                "condition_inputs": context.condition_inputs,
                "moon_geometry_by_object_id": moon_geometry_by_id,
            }
            if context.use_target_equipment:
                planner_kwargs["telescope_by_object_id"] = planner_telescopes
            if context.observing_night_window.has_observing_window:
                planner_kwargs["night_window"] = context.observing_night_window
            night_plan = tuple(
                self._night_planner_service.plan(
                    planning_objects,
                    context.weather_summary,
                    context.current_telescope,
                    **planner_kwargs,
                )
            )

        sky_compass_candidates = tuple(
            unique_targets_by_id((*visible_planets, *conditioned_deep_sky))
        )
        conditioned_models_by_id = {
            model.object_id: model for model in conditioned_home_read_models
        }
        observable_targets_by_id = {}
        for display_target in sky_compass_candidates:
            model = conditioned_models_by_id.get(display_target.id)
            raw_target = (
                model.nsom_target_input
                if model is not None
                else raw_targets_by_id.get(display_target.id, display_target)
            )
            observable_targets_by_id[display_target.id] = (
                sky_compass_observable_target(raw_target, display_target)
            )
        try:
            sky_compass = self._sky_compass_service.compass(
                list(sky_compass_candidates),
                list(night_plan),
                best_object,
                has_location=True,
                caution_text=context.sky_compass_caution_text,
                observable_objects_by_id=observable_targets_by_id,
                condition_inputs=context.condition_inputs,
                moon_geometry_by_object_id=moon_geometry_by_id,
            )
        except Exception:
            logger.warning(
                "NSOM Sky Compass selection failed; using geometry fallback.",
                exc_info=True,
            )
            sky_compass = self._sky_compass_service.compass(
                list(sky_compass_candidates),
                list(night_plan),
                best_object,
                has_location=True,
                caution_text=context.sky_compass_caution_text,
            )

        return PreparedCatalogueRecommendationSnapshot(
            runtime_signature=context.runtime_signature,
            astronomy=astronomy,
            deep_sky=pollution_adjusted_deep_sky,
            equipment_setup_models=tuple(setup_models.items()),
            deep_sky_pollution_read_model=tuple(pollution_read_models),
            deep_sky_raw_condition_inputs=tuple(raw_deep_sky_by_id.items()),
            conditioned_deep_sky=conditioned_deep_sky,
            conditioned_home_objects=conditioned_home_objects,
            conditioned_deep_sky_read_model=conditioned_deep_sky_read_models,
            conditioned_home_read_model=conditioned_home_read_models,
            category_scores=category_scores,
            best_object=best_object,
            night_plan=night_plan,
            sky_compass=sky_compass,
            sky_compass_candidates=sky_compass_candidates,
        )

    def _prepare_equipment(
        self,
        objects: tuple[CelestialObject, ...],
        context: CatalogueRecommendationPreparationContext,
    ) -> tuple[
        tuple[CelestialObject, ...],
        dict[str, EquipmentSetupReadModel],
    ]:
        updated = []
        setup_models = {}
        telescopes = list(context.telescopes)
        eyepieces = list(context.eyepieces)
        barlows = list(context.barlows)
        binoculars = list(context.binoculars)
        for item in objects:
            suggestion = self._equipment_service.suggest_for_profile(
                item,
                telescopes,
                eyepieces,
                barlows,
                context.seeing_transparency,
                context.sky_quality,
                binoculars,
            )
            setup_read_model = (
                self._equipment_setup_read_model_builder.from_suggestion(
                    item,
                    suggestion,
                )
            )
            setup_models[item.id] = setup_read_model
            naked_eye_blocked = (
                not telescopes
                and not binoculars
                and setup_read_model.requires_optical_instrument
            )
            setup_updates = setup_read_model.to_celestial_object_updates()
            updated.append(
                apply_object_content_from_sources(
                    replace(
                        item,
                        visible=item.visible and not naked_eye_blocked,
                        score=(
                            max(0, item.score - 45)
                            if naked_eye_blocked
                            else item.score
                        ),
                        **setup_updates,
                    ),
                    context.object_image_map,
                    context.object_descriptions,
                    context.catalogue_identifier_index,
                )
            )
        return tuple(updated), setup_models


def home_visible_objects_for_window(
    objects: Sequence[CelestialObject],
    night_window: ObservingNightWindow | None,
) -> tuple[CelestialObject, ...]:
    def has_useful_time(value: str) -> bool:
        times = _all_times(value)
        if night_window is None:
            return bool(times)
        return any(
            night_window.datetime_for_clock(hour, minute) is not None
            for hour, minute in times
        )

    return tuple(
        unique_targets_by_id(
            item
            for item in objects
            if has_useful_time(item.best_time)
            or has_useful_time(item.observing_window)
        )
    )


def moon_geometry_summary_to_condition_input(
    summary: MoonGeometrySummary | None,
) -> MoonGeometryConditionInput | None:
    if summary is None:
        return None
    return MoonGeometryConditionInput(
        moon_altitude_deg=summary.moon_altitude_deg,
        moon_target_separation_deg=summary.moon_target_separation_deg,
        moon_above_horizon=summary.moon_above_horizon,
        moon_visible_during_target_window=summary.moon_visible_during_target_window,
        moon_set_before_target_window=summary.moon_set_before_target_window,
    )


def sky_compass_observable_target(
    raw_target: CelestialObject,
    display_target: CelestialObject,
) -> CelestialObject:
    return replace(
        raw_target,
        direction=display_target.direction,
        visible=display_target.visible,
        max_altitude=display_target.max_altitude,
        azimuth=display_target.azimuth,
        current_altitude=display_target.current_altitude,
        current_azimuth=display_target.current_azimuth,
        observable_now=display_target.observable_now,
        current_altitude_degrees=display_target.current_altitude_degrees,
        current_azimuth_degrees=display_target.current_azimuth_degrees,
        time_above_horizon=display_target.time_above_horizon,
        rise_time=display_target.rise_time,
        set_time=display_target.set_time,
        culmination_time=display_target.culmination_time,
    )


def apply_object_content_from_sources(
    item: CelestialObject,
    object_image_map: Mapping[str, dict],
    object_descriptions: Mapping[str, dict],
    catalogue_identifier_index: Mapping[str, dict],
) -> CelestialObject:
    image = object_image_map.get(item.id)
    description = object_descriptions.get(item.id)
    catalogue_item = catalogue_identifier_index.get(item.id.strip().casefold())
    if (
        not image
        and catalogue_item
        and str(catalogue_item.get("catalogue", "")) != SOLAR_SYSTEM_CATALOGUE
    ):
        object_type = item.object_type.lower()
        if "galaxy" in object_type or "galassia" in object_type:
            image = object_image_map.get("messier-default-galaxy")
        elif any(
            fragment in object_type for fragment in ("nebula", "nebul", "remnant")
        ):
            image = object_image_map.get("messier-default-nebula")
        else:
            image = object_image_map.get("messier-default-cluster")
    notes = item.notes
    if description:
        observing_notes = presentation_text(
            description["observing_notes"],
            strip=True,
        )
        if observing_notes and is_editorial_placeholder(notes):
            notes = ""
        if observing_notes and observing_notes not in notes:
            notes = join_text([observing_notes, notes], " ")
    return replace(
        item,
        image=image["image_path"] if image else item.image,
        notes=notes,
        best_filter_class=(
            item.best_filter_class
            or str((catalogue_item or {}).get("best_filter_class") or "")
        ),
        fallback_filter_class=(
            item.fallback_filter_class
            or str((catalogue_item or {}).get("fallback_filter_class") or "")
        ),
        optional_color_filter_class=(
            item.optional_color_filter_class
            or str(
                (catalogue_item or {}).get("optional_color_filter_class") or ""
            )
        ),
        imaging_reducer_recommended=(
            item.imaging_reducer_recommended
            or bool((catalogue_item or {}).get("imaging_reducer_recommended"))
        ),
    )


def _all_times(value: str) -> list[tuple[int, int]]:
    return [
        (int(hour), int(minute))
        for hour, minute in re.findall(r"\b([0-2]?\d):([0-5]\d)\b", value or "")
        if 0 <= int(hour) <= 23
    ]
