"""Protect synchronous catalogue recommendation preparation and stale-result safety."""

from __future__ import annotations

from dataclasses import replace

from astro_viewer.app.application.catalogue_recommendations import (
    apply_object_content_from_sources,
    home_visible_objects_for_window,
    moon_geometry_summary_to_condition_input,
    sky_compass_observable_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonGeometrySummary


def _target(
    object_id: str,
    *,
    best_time: str = "",
    observing_window: str = "",
    object_type: str = "Nebula",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id,
        object_type=object_type,
        image="",
        magnitude="",
        distance="",
        max_altitude="",
        direction="",
        best_time=best_time,
        observing_window=observing_window,
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="",
    )


def test_home_visible_objects_require_a_parseable_observing_time() -> None:
    timed = _target("timed", best_time="22:30")
    windowed = _target("windowed", observing_window="01:15 - 03:00")
    untimed = _target("untimed", best_time="n/d")

    assert home_visible_objects_for_window(
        (timed, windowed, untimed),
        None,
    ) == (timed, windowed)


def test_moon_geometry_adapter_preserves_condition_fields() -> None:
    summary = MoonGeometrySummary(
        object_id="M 42",
        moon_altitude_deg=18.5,
        moon_target_separation_deg=71.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=False,
        moon_set_before_target_window=True,
    )

    adapted = moon_geometry_summary_to_condition_input(summary)

    assert adapted is not None
    assert adapted.moon_altitude_deg == 18.5
    assert adapted.moon_target_separation_deg == 71.0
    assert adapted.moon_above_horizon is True
    assert adapted.moon_visible_during_target_window is False
    assert adapted.moon_set_before_target_window is True
    assert moon_geometry_summary_to_condition_input(None) is None


def test_sky_compass_adapter_keeps_raw_identity_and_display_geometry() -> None:
    raw = replace(_target("M 31"), notes="raw notes", direction="old")
    display = replace(
        raw,
        name="localized display name",
        direction="NE",
        visible=False,
        current_altitude="42°",
        current_azimuth="63°",
        current_altitude_degrees=42.0,
        current_azimuth_degrees=63.0,
        observable_now=True,
    )

    adapted = sky_compass_observable_target(raw, display)

    assert adapted.name == raw.name
    assert adapted.notes == "raw notes"
    assert adapted.direction == "NE"
    assert adapted.visible is False
    assert adapted.current_altitude_degrees == 42.0
    assert adapted.current_azimuth_degrees == 63.0
    assert adapted.observable_now is True


def test_content_adapter_applies_catalogue_metadata_and_fallback_image() -> None:
    target = _target("M 42")

    adapted = apply_object_content_from_sources(
        target,
        {"messier-default-nebula": {"image_path": "images/nebula.webp"}},
        {},
        {
            "m 42": {
                "catalogue": "Messier",
                "best_filter_class": "UHC",
                "fallback_filter_class": "OIII",
                "imaging_reducer_recommended": True,
            }
        },
    )

    assert adapted.image == "images/nebula.webp"
    assert adapted.best_filter_class == "UHC"
    assert adapted.fallback_filter_class == "OIII"
    assert adapted.imaging_reducer_recommended is True
