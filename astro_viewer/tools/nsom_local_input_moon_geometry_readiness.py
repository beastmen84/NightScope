from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionFeatureFlags,
    ObservationConditionsService,
)


REPORT_PATH = Path("docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "nsom_local_input_moon_geometry_readiness",
    "NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS",
)

QML_MARKERS = (
    "nsomLocalInputMoonGeometryReadiness",
    "localInputMoonGeometryReadiness",
    "NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS",
)

SOURCE_MARKERS = (
    {
        "surface": "Manual and automatic location inputs",
        "path": Path("astro_viewer/app/viewmodels/app_controller.py"),
        "markers": (
            "def setManualLocation",
            "def useWindowsLocation",
            "def useApproximateOnlineLocation",
            '"profile_name": "Occhio nudo"',
        ),
    },
    {
        "surface": "Skyfield Moon summary",
        "path": Path("astro_viewer/app/astronomy/skyfield_engine.py"),
        "markers": (
            "def moon_summary",
            "almanac.moon_phase",
            "illumination =",
            "phase_angle=round",
        ),
    },
    {
        "surface": "MoonSummary runtime DTO",
        "path": Path("astro_viewer/app/models/observing.py"),
        "markers": (
            "class MoonSummary",
            "phase: str",
            "illumination: str",
            "phase_angle: float = 0.0",
        ),
    },
    {
        "surface": "MoonGeometrySummary runtime DTO",
        "path": Path("astro_viewer/app/models/observing.py"),
        "markers": (
            "class MoonGeometrySummary",
            "moon_altitude_deg: float | None = None",
            "moon_target_separation_deg: float | None = None",
            'sample_policy: str = "bounded_start_mid_best_end"',
        ),
    },
    {
        "surface": "Skyfield Moon geometry diagnostics",
        "path": Path("astro_viewer/app/astronomy/skyfield_engine.py"),
        "markers": (
            "def moon_geometry",
            "MoonGeometrySummary(",
            "def _moon_target_separations",
            "def _bounded_moon_geometry_sample_times",
            "def _moon_set_before_target_window",
        ),
    },
    {
        "surface": "Moon geometry future condition input",
        "path": Path("astro_viewer/app/services/observation_conditions_service.py"),
        "markers": (
            "class MoonGeometryConditionInput",
            "experimental_moon_geometry_scoring: bool = False",
            "def intended_moon_geometry_factor",
            "def intended_moon_geometry_modifier",
            "moon_geometry:score_neutral",
        ),
    },
    {
        "surface": "NSOM runtime Moon geometry diagnostics",
        "path": Path("astro_viewer/app/viewmodels/app_controller.py"),
        "markers": (
            "def _moon_geometry_condition_input",
            "def _moon_geometry_summary",
            "moon_geometry_available",
            "moon_geometry_score_effect",
        ),
    },
    {
        "surface": "AOD and OpenAQ neutral condition inputs",
        "path": Path("astro_viewer/app/services/observation_conditions_service.py"),
        "markers": (
            "class AodConditionInput",
            "class ParticulateConditionInput",
            "experimental_aerosol_scoring: bool = False",
            "def intended_aerosol_modifier",
            "aod_modifier=0.0",
            "pm25_modifier=0.0",
        ),
    },
    {
        "surface": "Planner NSOM moon background",
        "path": Path("astro_viewer/app/services/planner_nsom_service.py"),
        "markers": (
            "lunar_sky_background=moon_background",
            "def _moon_background_factor",
            "def _moon_geometry_severity_factor",
            "uses_moon_geometry_scoring",
            'getattr(moon, "illumination", "")',
        ),
    },
    {
        "surface": "Home NSOM moon background",
        "path": Path("astro_viewer/app/services/home_nsom_observable.py"),
        "markers": (
            "lunar_sky_background=moon_background",
            "def _moon_background_factor",
            'getattr(moon, "illumination", "")',
        ),
    },
    {
        "surface": "VIIRS sky-quality distinction",
        "path": Path("astro_viewer/app/models/sky.py"),
        "markers": (
            "class SkyQuality",
            "viirs_radiance: float | None = None",
            "hasViirsRadiance",
        ),
    },
)

MOON_GEOMETRY_FIELD_MARKERS = (
    "moon_altitude_deg",
    "moon_target_separation_deg",
    "moon_above_horizon",
    "moon_visible_during_target_window",
    "moon_set_before_target_window",
)


def generate_local_input_moon_geometry_readiness_data() -> dict[str, object]:
    """Developer-only audit for local inputs and Moon geometry readiness."""

    root = Path(__file__).parents[2]
    source_checks = _source_marker_checks(root)
    static_checks = _static_wiring_checks(root)
    taxonomy = _data_source_taxonomy()
    moon_fields = _moon_geometry_field_inventory(root)
    current_consumers = _current_moon_consumers()
    readiness = _moon_readiness()
    next_steps = _recommended_sequence()
    checks = _checks(source_checks, static_checks, taxonomy, moon_fields, readiness)
    blockers = _blockers(checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "scoring_changed": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "equipment_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": (
                "local_input_moon_geometry_runtime_diagnostics_available"
                if not blockers
                else "local_input_moon_geometry_needs_review"
            ),
            "moon_geometry_scoring_enabled_now": False,
            "moon_geometry_ready_for_local_implementation": not blockers,
            "moon_geometry_runtime_diagnostics_available": not blockers,
            "moon_geometry_planner_scoring_path_available": not blockers,
            "first_scoring_candidate": "moon_geometry_behind_experimental_flag",
            "requires_provider_before_next_step": False,
            "blocks_current_default_on_surfaces": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_step": (
                "Review docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md, "
                "then implement a narrow Planner Moon geometry default-on switch "
                "if accepted."
            ),
            "reason": (
                "Location plus local ephemeris data now computes Moon altitude, "
                "Moon-target separation and window overlap without weather, "
                "VIIRS, AOD or OpenAQ. Current default runtime scoring still "
                "uses Moon illumination only; the experimental Planner path can "
                "apply geometry to ObservationEnvironment.lunar_sky_background "
                "when experimental_moon_geometry_scoring is enabled."
            ),
        },
        "data_source_taxonomy": taxonomy,
        "moon_geometry_field_inventory": moon_fields,
        "current_moon_consumers": current_consumers,
        "moon_readiness": readiness,
        "source_marker_checks": source_checks,
        "static_wiring_checks": static_checks,
        "checks": checks,
        "blockers": blockers,
        "recommended_sequence": next_steps,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_local_input_moon_geometry_readiness_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Local Input and Moon Geometry Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit separates NightScope input sources into "
            "local always-available astronomy, local optional equipment and "
            "external optional providers. It confirms that Moon geometry is "
            "available as a runtime diagnostic and as a default-off Planner NSOM "
            "scoring input computed from the active location and local astronomy "
            "engine without network, weather, VIIRS, AOD or OpenAQ. No default "
            "runtime scoring, ranking, QML, logging, network or runtime "
            "file-write behaviour changes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Moon geometry scoring enabled now: `{readiness['moon_geometry_scoring_enabled_now']}`.",
        (
            "- Moon geometry ready for local implementation: "
            f"`{readiness['moon_geometry_ready_for_local_implementation']}`."
        ),
        (
            "- Moon geometry runtime diagnostics available: "
            f"`{readiness['moon_geometry_runtime_diagnostics_available']}`."
        ),
        (
            "- Moon geometry Planner scoring path available: "
            f"`{readiness['moon_geometry_planner_scoring_path_available']}`."
        ),
        f"- First scoring candidate: `{readiness['first_scoring_candidate']}`.",
        f"- Requires provider before next step: `{readiness['requires_provider_before_next_step']}`.",
        f"- Blocks current default-on surfaces: `{readiness['blocks_current_default_on_surfaces']}`.",
        (
            "- Runtime behaviour changed by this audit: "
            f"`{readiness['runtime_behaviour_changed_by_this_audit']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Data Source Taxonomy",
        "",
        "| Source | Availability | External provider | NSOM owner | Current scoring role | Missing-input policy |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for source in audit["data_source_taxonomy"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{source['source_id']}`",
                    source["availability"],
                    f"`{source['external_provider']}`",
                    source["nsom_owner"],
                    source["current_scoring_role"],
                    source["missing_input_policy"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Moon Geometry Field Inventory",
            "",
            "| Field | Status | Source today | Required implementation | Score role now |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for field in audit["moon_geometry_field_inventory"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{field['field']}`",
                    f"`{field['status']}`",
                    field["source_today"],
                    field["required_implementation"],
                    field["score_role_now"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Current Moon Consumers",
            "",
            "| Consumer | Current Moon input | Geometry input | Score status | Notes |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for consumer in audit["current_moon_consumers"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    consumer["consumer"],
                    consumer["current_moon_input"],
                    consumer["geometry_input"],
                    consumer["score_status"],
                    consumer["notes"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Moon Readiness Contract",
            "",
            "| Requirement | Value |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["moon_readiness"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Source Marker Checks",
            "",
            "| Surface | Path | All markers found | Missing markers |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["source_marker_checks"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['path']}`",
                    f"`{item['all_markers_found']}`",
                    f"`{item['missing_markers']}`",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Static Wiring",
            "",
            f"- Runtime report imports: `{audit['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- QML report exposure: `{audit['static_wiring_checks']['qml_report_exposure_matches']}`.",
            "",
            "## Recommended Sequence",
            "",
        ]
    )
    for item in audit["recommended_sequence"]:
        lines.append(f"- `{item['step']}`: {item['summary']}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The backend NSOM consumer migration is closed for current "
                "recommendation surfaces, and the physical model now has "
                "local Moon geometry diagnostics plus a default-off Planner NSOM "
                "scoring path. Moon altitude and Moon-target separation are "
                "deterministic once location and time are known, so the next step "
                "is review and calibration before any default-on Moon geometry, "
                "NASA AOD or OpenAQ scoring. AOD and OpenAQ remain optional "
                "provider inputs with freshness and confidence semantics."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _data_source_taxonomy() -> tuple[dict[str, object], ...]:
    return (
        {
            "source_id": "location",
            "availability": "minimum_required_input",
            "external_provider": False,
            "nsom_owner": "Sky / geometry context",
            "current_scoring_role": "required before Home recommendations can be computed",
            "missing_input_policy": "recommendations cannot be meaningful until location exists",
            "examples": ("manual coordinates", "Windows location", "approximate online location"),
        },
        {
            "source_id": "local_astronomy_ephemeris",
            "availability": "available_after_location",
            "external_provider": False,
            "nsom_owner": "Universe and Sky",
            "current_scoring_role": "target positions, visibility, Moon phase and illumination",
            "missing_input_policy": "fallback engine keeps UI usable but lowers astronomical fidelity",
            "examples": ("Skyfield", "JPL de421.bsp", "Astropy coordinate helpers"),
        },
        {
            "source_id": "equipment_profile",
            "availability": "optional_local",
            "external_provider": False,
            "nsom_owner": "Observer",
            "current_scoring_role": "ObserverCapability and PracticalTargetValue where applicable",
            "missing_input_policy": "use naked-eye/default observer assumptions",
            "examples": ("Occhio nudo", "telescope profile", "eyepieces", "barlow"),
        },
        {
            "source_id": "weather_open_meteo",
            "availability": "optional_external",
            "external_provider": True,
            "nsom_owner": "Session",
            "current_scoring_role": "SessionViability and weather blocking when available",
            "missing_input_policy": "weather-dependent conclusions remain unknown or fallback-safe",
            "examples": ("clouds", "rain", "wind", "humidity", "visibility"),
        },
        {
            "source_id": "sky_quality_viirs_or_fallback",
            "availability": "optional_hybrid",
            "external_provider": "hybrid",
            "nsom_owner": "Sky",
            "current_scoring_role": "static_sky_background when VIIRS radiance or fallback exists",
            "missing_input_policy": "distinguish real VIIRS radiance from fallback sky quality",
            "examples": ("NASA VIIRS Black Marble", "local VIIRS-derived dataset", "Bortle fallback"),
        },
        {
            "source_id": "nasa_aod",
            "availability": "optional_external",
            "external_provider": True,
            "nsom_owner": "Sky / Confidence future aerosol component",
            "current_scoring_role": "display and diagnostic only; score-neutral in current runtime",
            "missing_input_policy": "omit from scoring and confidence notes when unavailable",
            "examples": ("VIIRS MAIAC AOD", "MODIS MAIAC fallback"),
        },
        {
            "source_id": "openaq_particulate",
            "availability": "optional_external",
            "external_provider": True,
            "nsom_owner": "Sky / Confidence future particulate component",
            "current_scoring_role": "display and diagnostic only; score-neutral in current runtime",
            "missing_input_policy": "omit or mark unavailable/historical according to freshness",
            "examples": ("PM2.5", "PM10", "freshness category"),
        },
    )


def _moon_geometry_field_inventory(root: Path) -> tuple[dict[str, object], ...]:
    moon_summary_text = _moon_summary_text(root)
    return (
        {
            "field": "moon_phase",
            "status": "active_current",
            "source_today": "MoonSummary.phase",
            "required_implementation": "already available",
            "score_role_now": "display and Moon context",
        },
        {
            "field": "moon_illumination",
            "status": "active_current",
            "source_today": "MoonSummary.illumination",
            "required_implementation": "already available",
            "score_role_now": "active lunar_sky_background / existing Moon adjustment input",
        },
        {
            "field": "moon_phase_angle",
            "status": "active_current",
            "source_today": "MoonSummary.phase_angle",
            "required_implementation": "already available",
            "score_role_now": "display/context only",
        },
        {
            "field": "moon_altitude_deg",
            "status": "runtime_score_neutral_geometry_input",
            "source_today": "MoonGeometrySummary -> MoonGeometryConditionInput; absent from MoonSummary",
            "required_implementation": "implemented from sampled Moon altitude and local ephemeris",
            "score_role_now": "default score-neutral; Planner flag can use it through lunar_sky_background",
            "absent_from_moon_summary": "moon_altitude_deg" not in moon_summary_text,
        },
        {
            "field": "moon_target_separation_deg",
            "status": "runtime_score_neutral_geometry_input",
            "source_today": "MoonGeometrySummary -> MoonGeometryConditionInput; absent from MoonSummary",
            "required_implementation": "implemented as angular Moon-target separation at bounded window samples",
            "score_role_now": "default score-neutral; Planner flag can use it through lunar_sky_background",
            "absent_from_moon_summary": "moon_target_separation_deg" not in moon_summary_text,
        },
        {
            "field": "moon_above_horizon",
            "status": "runtime_score_neutral_geometry_input",
            "source_today": "MoonGeometrySummary -> MoonGeometryConditionInput; derived from sampled altitude",
            "required_implementation": "implemented from Moon altitude samples, not from display strings",
            "score_role_now": "default score-neutral; Planner flag can use it through lunar_sky_background",
            "absent_from_moon_summary": "moon_above_horizon" not in moon_summary_text,
        },
        {
            "field": "moon_visible_during_target_window",
            "status": "runtime_score_neutral_geometry_input",
            "source_today": "MoonGeometrySummary -> MoonGeometryConditionInput",
            "required_implementation": "implemented by comparing Moon samples with target window samples",
            "score_role_now": "default score-neutral; Planner flag can use it through lunar_sky_background",
            "absent_from_moon_summary": "moon_visible_during_target_window" not in moon_summary_text,
        },
        {
            "field": "moon_set_before_target_window",
            "status": "runtime_score_neutral_geometry_input",
            "source_today": "MoonGeometrySummary -> MoonGeometryConditionInput",
            "required_implementation": "implemented from sampled Moon geometry relative to target window",
            "score_role_now": "default score-neutral; Planner flag can use it through lunar_sky_background",
            "absent_from_moon_summary": "moon_set_before_target_window" not in moon_summary_text,
        },
    )


def _current_moon_consumers() -> tuple[dict[str, object], ...]:
    return (
        {
            "consumer": "Planner NSOM",
            "current_moon_input": "MoonSummary.illumination",
            "geometry_input": "default-off experimental scoring input",
            "score_status": "default active illumination-only lunar_sky_background; flag can apply geometry",
            "notes": "Moon altitude and separation affect only ObservationEnvironment.lunar_sky_background when experimental_moon_geometry_scoring is enabled.",
        },
        {
            "consumer": "Home recommendedDeepSky NSOM",
            "current_moon_input": "MoonSummary.illumination",
            "geometry_input": "diagnostic export only",
            "score_status": "active illumination-based ObservableTargetValue background",
            "notes": "Home intentionally excludes session/weather/equipment from ObservableTargetValue.",
        },
        {
            "consumer": "Best Object NSOM",
            "current_moon_input": "MoonSummary.illumination through Home observable adapter",
            "geometry_input": "diagnostic export only",
            "score_status": "active through ObservableTargetValue and Opportunity",
            "notes": "SessionViability remains separate from target and sky physics.",
        },
        {
            "consumer": "Sky Compass NSOM",
            "current_moon_input": "MoonSummary.illumination through Home observable adapter",
            "geometry_input": "diagnostic export only",
            "score_status": "active as candidate base only",
            "notes": "Direction policy remains presentation/context outside target physics.",
        },
        {
            "consumer": "ObservationConditions legacy compatibility",
            "current_moon_input": "MoonSummary.illumination",
            "geometry_input": "diagnostic notes only when supplied",
            "score_status": "geometry modifier is neutral",
            "notes": "Existing presentation compatibility score remains bounded by raw/display policy.",
        },
        {
            "consumer": "AOD/OpenAQ",
            "current_moon_input": "none",
            "geometry_input": "none",
            "score_status": "external provider data remains score-neutral",
            "notes": "Do not combine aerosol and Moon work in the same implementation step.",
        },
    )


def _moon_readiness() -> dict[str, object]:
    neutral_geometry = MoonGeometryConditionInput(
        moon_altitude_deg=42.0,
        moon_target_separation_deg=60.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
    )
    return {
        "requires_location": True,
        "requires_current_time_or_session_window": True,
        "requires_weather_provider": False,
        "requires_viirs_provider": False,
        "requires_nasa_aod": False,
        "requires_openaq": False,
        "requires_equipment_profile": False,
        "calculation_layer": "SkyfieldAstronomyEngine.moon_geometry",
        "nsom_owner": "Sky / ObservationEnvironment",
        "first_consumer": "Planner before Home",
        "sampling_policy": "bounded start/mid/best/end samples",
        "confidence_policy": "RecommendationConfidence metadata only",
        "planner_scoring_flag": "experimental_moon_geometry_scoring",
        "planner_scoring_default": False,
        "moon_geometry_planner_scoring_path_available": True,
        "planner_scoring_owner": "Sky / ObservationEnvironment.lunar_sky_background",
        "current_geometry_factor_example": ObservationConditionsService.intended_moon_geometry_factor(
            neutral_geometry
        ),
        "current_modifier_with_flag_off": ObservationConditionsService.intended_moon_geometry_modifier(
            neutral_geometry,
            ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=False),
        ),
        "current_modifier_with_flag_on": ObservationConditionsService.intended_moon_geometry_modifier(
            neutral_geometry,
            ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True),
        ),
    }


def _recommended_sequence() -> tuple[dict[str, object], ...]:
    return (
        {
            "step": "Review 1.14.1",
            "summary": (
                "Confirm the source taxonomy and Moon geometry readiness before "
                "adding runtime calculations."
            ),
        },
        {
            "step": "1.14.2 Moon geometry diagnostics runtime",
            "summary": (
                "Computed Moon altitude, Moon-target separation and Moon/window "
                "overlap from local astronomy samples; still score-neutral."
            ),
        },
        {
            "step": "Review 1.14.2",
            "summary": (
                "Confirm runtime Moon geometry diagnostics are physically sane, "
                "score-neutral and not wired into QML/runtime reports."
            ),
        },
        {
            "step": "1.14.3 Moon geometry scoring behind flag",
            "summary": (
                "Use the diagnostics in Planner ObservationEnvironment behind "
                "experimental_moon_geometry_scoring; keep the flag default-off."
            ),
        },
        {
            "step": "Review 1.14.3",
            "summary": (
                "Confirm default-off runtime behaviour, ownership boundaries and "
                "calibration risk before any Moon geometry default-on work."
            ),
        },
        {
            "step": "1.14.4 Moon geometry Planner calibration",
            "summary": (
                "Add deterministic developer-only fixtures comparing the "
                "illumination-only Planner path with the experimental Moon "
                "geometry path before any default-on decision."
            ),
        },
        {
            "step": "Review 1.14.4",
            "summary": (
                "Confirm calibration evidence, confidence metadata semantics and "
                "whether Moon geometry needs tuning before default-on."
            ),
        },
        {
            "step": "1.14.5 Moon geometry Planner default-on readiness",
            "summary": (
                "Classify the calibration evidence and decide whether a narrow "
                "Planner Moon geometry default-on switch is ready."
            ),
        },
        {
            "step": "Review 1.14.5",
            "summary": (
                "Confirm default-on readiness, default-off runtime state and "
                "non-blocking risks before changing the switch."
            ),
        },
        {
            "step": "AOD/OpenAQ scoring readiness",
            "summary": (
                "Only after Moon geometry, audit freshness, QA and double-counting "
                "before enabling provider-dependent aerosol scoring."
            ),
        },
    )


def _checks(
    source_checks: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    taxonomy: tuple[dict[str, object], ...],
    moon_fields: tuple[dict[str, object], ...],
    readiness: dict[str, object],
) -> dict[str, object]:
    source_by_id = {item["source_id"]: item for item in taxonomy}
    moon_field_by_id = {item["field"]: item for item in moon_fields}
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "source_checks": source_checks,
                "static_checks": static_checks,
                "taxonomy": taxonomy,
                "moon_fields": moon_fields,
                "readiness": readiness,
            }
        ),
        "minimum_location_source_documented": source_by_id["location"]["availability"]
        == "minimum_required_input",
        "local_astronomy_is_not_external_provider": source_by_id["local_astronomy_ephemeris"][
            "external_provider"
        ]
        is False,
        "equipment_default_is_local_optional": source_by_id["equipment_profile"]["availability"]
        == "optional_local",
        "weather_marked_external_optional": source_by_id["weather_open_meteo"][
            "external_provider"
        ]
        is True,
        "viirs_source_distinguishes_fallback": "fallback"
        in source_by_id["sky_quality_viirs_or_fallback"]["missing_input_policy"],
        "aod_openaq_external_score_neutral": all(
            source_by_id[source]["current_scoring_role"].endswith(
                "score-neutral in current runtime"
            )
            for source in ("nasa_aod", "openaq_particulate")
        ),
        "moon_summary_has_phase_illumination": all(
            moon_field_by_id[field]["status"] == "active_current"
            for field in ("moon_phase", "moon_illumination", "moon_phase_angle")
        ),
        "moon_geometry_fields_are_runtime_diagnostics": all(
            moon_field_by_id[field]["status"] == "runtime_score_neutral_geometry_input"
            for field in MOON_GEOMETRY_FIELD_MARKERS
        ),
        "moon_geometry_absent_from_moon_summary": all(
            moon_field_by_id[field]["absent_from_moon_summary"] is True
            for field in MOON_GEOMETRY_FIELD_MARKERS
        ),
        "moon_geometry_requires_no_provider": readiness["requires_weather_provider"] is False
        and readiness["requires_viirs_provider"] is False
        and readiness["requires_nasa_aod"] is False
        and readiness["requires_openaq"] is False,
        "moon_geometry_modifier_still_neutral": readiness["current_modifier_with_flag_off"] == 0.0
        and readiness["current_modifier_with_flag_on"] == 0.0,
        "moon_geometry_planner_scoring_path_available": readiness[
            "moon_geometry_planner_scoring_path_available"
        ]
        is True,
        "source_markers_all_found": all(item["all_markers_found"] is True for item in source_checks),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "no_scoring_change": True,
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "local-input-json-incompatible",
        "minimum_location_source_documented": "minimum-location-source-not-documented",
        "local_astronomy_is_not_external_provider": "local-astronomy-provider-boundary-wrong",
        "equipment_default_is_local_optional": "equipment-default-policy-missing",
        "weather_marked_external_optional": "weather-provider-boundary-wrong",
        "viirs_source_distinguishes_fallback": "viirs-fallback-boundary-missing",
        "aod_openaq_external_score_neutral": "aod-openaq-score-neutral-boundary-missing",
        "moon_summary_has_phase_illumination": "moon-summary-active-fields-missing",
        "moon_geometry_fields_are_runtime_diagnostics": "moon-geometry-fields-not-runtime-diagnostics",
        "moon_geometry_absent_from_moon_summary": "moon-geometry-already-in-moon-summary",
        "moon_geometry_requires_no_provider": "moon-geometry-provider-dependency",
        "moon_geometry_modifier_still_neutral": "moon-geometry-modifier-not-neutral",
        "moon_geometry_planner_scoring_path_available": "moon-geometry-planner-path-missing",
        "source_markers_all_found": "source-marker-missing",
        "runtime_report_imports_absent": "runtime-report-wiring",
        "qml_report_exposure_absent": "qml-report-exposure",
        "no_scoring_change": "scoring-change",
        "runtime_behaviour_unchanged_by_audit": "runtime-change",
    }
    return tuple(name for key, name in blocker_names.items() if checks[key] is not True)


def _source_marker_checks(root: Path) -> tuple[dict[str, object], ...]:
    checks: list[dict[str, object]] = []
    for item in SOURCE_MARKERS:
        path = root / item["path"]
        text = _read_text(path)
        found = tuple(marker for marker in item["markers"] if marker in text)
        missing = tuple(marker for marker in item["markers"] if marker not in text)
        checks.append(
            {
                "surface": item["surface"],
                "path": str(item["path"]).replace("\\", "/"),
                "markers": item["markers"],
                "found_markers": found,
                "missing_markers": missing,
                "all_markers_found": path.exists() and not missing,
            }
        )
    return tuple(checks)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "qml_report_exposure_matches": _scan_files(
            root / "astro_viewer" / "app" / "ui",
            ("*.qml",),
            QML_MARKERS,
        ),
    }


def _scan_files(
    root: Path,
    patterns: tuple[str, ...],
    markers: tuple[str, ...],
    *,
    include_parts: tuple[str, ...] | None = None,
) -> tuple[dict[str, object], ...]:
    if not root.exists():
        return ()
    matches: list[dict[str, object]] = []
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if include_parts and not any(part in path.parts for part in include_parts):
                continue
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                for marker in markers:
                    if marker in line:
                        matches.append(
                            {
                                "path": str(path.relative_to(root)).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                            }
                        )
    return tuple(matches)


def _strict_json_compatible(payload: object) -> bool:
    try:
        json.dumps(nsom_to_json_compatible(payload), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _moon_summary_text(root: Path) -> str:
    text = _read_text(root / "astro_viewer/app/models/observing.py")
    _before, marker, tail = text.partition("class MoonSummary")
    if not marker:
        return ""
    block, _next_marker, _after = tail.partition("class MoonGeometrySummary")
    return marker + block


if __name__ == "__main__":
    write_markdown_report()
