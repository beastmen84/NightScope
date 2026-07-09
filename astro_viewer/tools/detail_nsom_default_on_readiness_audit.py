from __future__ import annotations

from copy import deepcopy
from inspect import signature
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.detail_nsom_runtime import (
    DETAIL_SOURCE_CATALOGUE,
    DETAIL_SOURCE_OBSERVING,
    NSOM_DETAIL_OBJECT_ENABLED,
    DetailObjectNsomRuntimeService,
)
from astro_viewer.app.services.observation_conditions_service import ObservationConditionsService
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tools.detail_nsom_readiness_audit import (
    READINESS_AUDIT_PATH as DEFAULT_OFF_READINESS_AUDIT_PATH,
    generate_readiness_audit_data,
)


DEFAULT_ON_READINESS_AUDIT_PATH = Path("docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "detail_nsom_default_on_readiness_audit",
    "DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT",
)

QML_MARKERS = (
    "detailObjectNsom",
    "selectedObjectNsom",
    "NSOM_DETAIL_OBJECT_ENABLED",
    "DetailObjectNsomRuntimeService",
    "_selected_object_nsom_payload",
    "DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT",
)


def generate_default_on_readiness_audit_data() -> dict[str, object]:
    default_off_audit = generate_readiness_audit_data()
    runtime = _runtime_policy_evidence()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    safety = _runtime_safety(default_off_audit, runtime, static_checks)
    checks = _readiness_checks(default_off_audit, runtime, static_checks, safety)
    blockers = _default_on_blockers(checks)
    ready = blockers == ()

    audit_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "selected_object_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "sky_compass_changed": False,
            "source_report": str(DEFAULT_OFF_READINESS_AUDIT_PATH).replace("\\", "/"),
            "audit_report_path": str(DEFAULT_ON_READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "detail_object_nsom_default_on_enabled"
                if ready and NSOM_DETAIL_OBJECT_ENABLED
                else "ready_for_detail_object_nsom_default_on_switch"
                if ready
                else "not_ready_for_detail_object_nsom_default_on_switch"
            ),
            "ready_for_default_on_switch": ready,
            "default_flag": f"NSOM_DETAIL_OBJECT_ENABLED = {NSOM_DETAIL_OBJECT_ENABLED}",
            "default_flag_currently_enabled": NSOM_DETAIL_OBJECT_ENABLED is True,
            "default_flag_enabled_by_this_commit": NSOM_DETAIL_OBJECT_ENABLED is True,
            "requires_separate_flag_change": NSOM_DETAIL_OBJECT_ENABLED is False,
            "runtime_behaviour_changed_by_this_audit": False,
            "explicit_legacy_rollback": "removed: AppController(use_nsom_detail_object=False)",
            "explicit_nsom_path": "default AppController()",
            "recommended_switch_change": (
                "already enabled"
                if NSOM_DETAIL_OBJECT_ENABLED
                else "set NSOM_DETAIL_OBJECT_ENABLED = True"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "checks": checks,
        "runtime_policy_evidence": runtime,
        "display_score_semantics": _display_score_semantics(runtime),
        "missing_input_policy": _missing_input_policy(runtime),
        "rollback_policy": _rollback_policy(runtime),
        "non_blocking_risks": _non_blocking_risks(),
        "runtime_safety": safety,
        "static_wiring_checks": static_checks,
        "default_off_readiness_summary": {
            "verdict": default_off_audit["readiness"]["verdict"],
            "runtime_path_exists": default_off_audit["readiness"]["runtime_path_exists"],
            "blockers": default_off_audit["blockers"],
        },
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_default_on_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    runtime = audit["runtime_policy_evidence"]
    display = audit["display_score_semantics"]
    missing = audit["missing_input_policy"]
    rollback = audit["rollback_policy"]
    safety = audit["runtime_safety"]

    lines = [
        "# Detail/Object NSOM Default-On Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the Detail/Object NSOM "
            "default-on switch is safe to keep. It reports the current "
            "`NSOM_DETAIL_OBJECT_ENABLED` flag, removed rollback path and payload policy "
            "without changing `selectedObject`, QML, Home, Best Object, Planner, "
            "Sky Compass, logging, network access or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
        f"- Default flag enabled by this commit: `{readiness['default_flag_enabled_by_this_commit']}`.",
        f"- Requires separate flag change: `{readiness['requires_separate_flag_change']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Explicit legacy rollback: `{readiness['explicit_legacy_rollback']}`.",
        f"- Explicit NSOM path: `{readiness['explicit_nsom_path']}`.",
        f"- Recommended switch change: `{readiness['recommended_switch_change']}`.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-On Blockers",
        "",
    ]
    if audit["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["blockers"])
    else:
        lines.append("- none")

    observing = runtime["observing_source"]
    catalogue = runtime["catalogue_source"]
    lines.extend(
        [
            "",
            "## Runtime Policy Evidence",
            "",
            "| Policy | Evidence |",
            "| --- | --- |",
            (
                "| Runtime default | "
                f"Observing payload exists `{observing['internal_payload_present']}`, "
                f"catalogue payload exists `{catalogue['internal_payload_present']}`. |"
            ),
            (
                "| Observing source | "
                f"Policy `{observing['legacy_display_policy']}`, internal payload exists "
                f"`{observing['internal_payload_present']}`, selected payload unchanged "
                f"`{observing['selected_object_unchanged']}`. |"
            ),
            (
                "| Catalogue source | "
                f"Policy `{catalogue['legacy_display_policy']}`, internal payload exists "
                f"`{catalogue['internal_payload_present']}`, selected payload unchanged "
                f"`{catalogue['selected_object_unchanged']}`. |"
            ),
            (
                "| Session | "
                f"Blocked session value `{runtime['session']['blocked_value']}`, "
                f"observable unchanged `{runtime['session']['observable_unchanged']}`, "
                f"practical unchanged `{runtime['session']['practical_unchanged']}`. |"
            ),
            (
                "| Confidence | "
                f"Low/high values `{runtime['confidence']['low_value']}` / "
                f"`{runtime['confidence']['high_value']}`, score effect "
                f"`{runtime['confidence']['score_effect']}`. |"
            ),
            (
                "| Mutation | "
                f"Runtime object mutated `{runtime['mutation']['runtime_object_mutated']}`. |"
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## Display Score Semantics",
            "",
            f"- Status: `{display['status']}`.",
            f"- Keep legacy/base displayed score: `{display['keep_legacy_displayed_score_for_payload_compatibility']}`.",
            f"- Score monotonic with NSOM payload: `{display['score_monotonic_with_nsom_payload']}`.",
            f"- Blocks default-on switch: `{display['blocks_default_on_switch']}`.",
            f"- Decision: {display['decision']}",
            f"- Future UI work: {display['future_ui_work']}",
            "",
            "## Missing Input Policy",
            "",
            f"- Status: `{missing['status']}`.",
            f"- Missing sky quality returns empty payload: `{missing['missing_sky_quality_returns_empty_payload']}`.",
            f"- Missing weather returns empty payload: `{missing['missing_weather_returns_empty_payload']}`.",
            f"- Blocks default-on switch: `{missing['blocks_default_on_switch']}`.",
            f"- Reason: {missing['reason']}",
            "",
            "## Rollback Policy",
            "",
            f"- Constructor rollback: `{rollback['constructor_rollback']}`.",
            f"- Legacy path preserved: `{rollback['legacy_path_preserved']}`.",
            f"- NSOM path explicit: `{rollback['nsom_path_explicit']}`.",
            f"- Blocks default-on switch: `{rollback['blocks_default_on_switch']}`.",
            "",
            "## Runtime Safety",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in safety.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Non-Blocking Risks",
            "",
        ]
    )
    for risk in audit["non_blocking_risks"]:
        lines.append(f"- {risk}")

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            "Review the rollback cleanup and keep visible Detail/Object NSOM UI as a separate design step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = DEFAULT_ON_READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _runtime_policy_evidence() -> dict[str, object]:
    observing_on = _controller(source=DETAIL_SOURCE_OBSERVING, moon=_moon(95))
    observing_before = AppController.selectedObject.fget(observing_on)
    observing_payload = observing_on._selected_object_nsom_payload()
    observing_after = AppController.selectedObject.fget(observing_on)

    catalogue_on = _controller(source=DETAIL_SOURCE_CATALOGUE, moon=_moon(95))
    catalogue_before = AppController.selectedObject.fget(catalogue_on)
    catalogue_payload = catalogue_on._selected_object_nsom_payload()
    catalogue_after = AppController.selectedObject.fget(catalogue_on)

    missing_sky = _controller(source=DETAIL_SOURCE_OBSERVING)
    missing_sky._sky_quality = None
    missing_weather = _controller(source=DETAIL_SOURCE_OBSERVING)
    missing_weather._weather_summary = None

    service = DetailObjectNsomRuntimeService()
    target = _target("galaxy", "Galaxy", 88)
    before_target = deepcopy(target)
    service.payload(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
    ).to_dict()

    good = service.payload(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
    ).to_dict()
    blocked = service.payload(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(10, cloud_cover=96, precipitation_probability=85),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
    ).to_dict()
    low = service.payload(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    ).to_dict()
    high = service.payload(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    ).to_dict()

    return {
        "observing_source": {
            "internal_payload_present": observing_payload != {},
            "schema_version": observing_payload.get("schemaVersion"),
            "legacy_display_policy": observing_payload["selectedObjectPolicy"]["legacyDisplayPolicy"],
            "selected_object_formula": observing_payload["selectedObjectPolicy"]["selectedObjectFormula"],
            "selected_object_unchanged": observing_after == observing_before,
            "selected_object_keys_unchanged": set(observing_after) == set(observing_before),
            "nsom_fields_in_selected_object": _nsom_fields_in_selected_object(observing_after),
            "selected_score": observing_after["score"],
            "observable_value": observing_payload["observableTargetValue"]["value"],
            "practical_value": observing_payload["practicalTargetValue"]["value"],
        },
        "catalogue_source": {
            "internal_payload_present": catalogue_payload != {},
            "schema_version": catalogue_payload.get("schemaVersion"),
            "legacy_display_policy": catalogue_payload["selectedObjectPolicy"]["legacyDisplayPolicy"],
            "selected_object_formula": catalogue_payload["selectedObjectPolicy"]["selectedObjectFormula"],
            "selected_object_unchanged": catalogue_after == catalogue_before,
            "selected_object_keys_unchanged": set(catalogue_after) == set(catalogue_before),
            "nsom_fields_in_selected_object": _nsom_fields_in_selected_object(catalogue_after),
            "selected_score": catalogue_after["score"],
            "observable_value": catalogue_payload["observableTargetValue"]["value"],
            "practical_value": catalogue_payload["practicalTargetValue"]["value"],
        },
        "missing_inputs": {
            "missing_sky_quality_returns_empty_payload": missing_sky._selected_object_nsom_payload() == {},
            "missing_weather_returns_empty_payload": missing_weather._selected_object_nsom_payload() == {},
        },
        "session": {
            "blocked_state": blocked["sessionViability"]["state"],
            "blocked_value": blocked["sessionViability"]["value"],
            "score_factor": blocked["sessionViability"]["scoreFactor"],
            "observable_unchanged": blocked["observableTargetValue"]["value"] == good["observableTargetValue"]["value"],
            "practical_unchanged": blocked["practicalTargetValue"]["value"] == good["practicalTargetValue"]["value"],
        },
        "confidence": {
            "low_value": low["recommendationConfidence"]["value"],
            "high_value": high["recommendationConfidence"]["value"],
            "score_factor": low["recommendationConfidence"]["scoreFactor"],
            "score_effect": low["recommendationConfidence"]["scoreEffect"],
            "observable_unchanged": low["observableTargetValue"]["value"] == high["observableTargetValue"]["value"],
            "practical_unchanged": low["practicalTargetValue"]["value"] == high["practicalTargetValue"]["value"],
        },
        "mutation": {
            "runtime_object_mutated": target != before_target,
        },
        "constructor": {
            "rollback_parameter_present": "use_nsom_detail_object"
            in signature(AppController.__init__).parameters,
            "default_kwarg_is_flag": False,
            "runtime_rollback_removed": "use_nsom_detail_object"
            not in signature(AppController.__init__).parameters,
        },
    }


def _display_score_semantics(runtime: dict[str, object]) -> dict[str, object]:
    observing = runtime["observing_source"]
    catalogue = runtime["catalogue_source"]
    return {
        "status": "accepted",
        "keep_legacy_displayed_score_for_payload_compatibility": True,
        "score_monotonic_with_nsom_payload": False,
        "observing_selected_score": observing["selected_score"],
        "observing_observable_value": observing["observable_value"],
        "catalogue_selected_score": catalogue["selected_score"],
        "catalogue_observable_value": catalogue["observable_value"],
        "blocks_default_on_switch": False,
        "decision": (
            "`selectedObject.score` remains legacy/base compatibility data even if "
            "the internal Detail/Object NSOM path is enabled by default."
        ),
        "future_ui_work": (
            "Visible NSOM rationale or score labels require a separate Detail page UX step."
        ),
    }


def _missing_input_policy(runtime: dict[str, object]) -> dict[str, object]:
    missing = runtime["missing_inputs"]
    ok = (
        missing["missing_sky_quality_returns_empty_payload"] is True
        and missing["missing_weather_returns_empty_payload"] is True
    )
    return {
        "status": "accepted" if ok else "needs_review",
        "missing_sky_quality_returns_empty_payload": missing["missing_sky_quality_returns_empty_payload"],
        "missing_weather_returns_empty_payload": missing["missing_weather_returns_empty_payload"],
        "blocks_default_on_switch": not ok,
        "reason": (
            "The internal payload is absent until required runtime inputs exist; "
            "`selectedObject` continues to provide the legacy-compatible view."
        ),
    }


def _rollback_policy(runtime: dict[str, object]) -> dict[str, object]:
    constructor = runtime["constructor"]
    return {
        "constructor_rollback": "removed: AppController(use_nsom_detail_object=False)",
        "legacy_path_preserved": False,
        "rollback_parameter_present": constructor["rollback_parameter_present"],
        "default_kwarg_is_flag": constructor["default_kwarg_is_flag"],
        "runtime_rollback_removed": constructor["runtime_rollback_removed"],
        "nsom_path_explicit": "default AppController()",
        "blocks_default_on_switch": False,
    }


def _runtime_safety(
    default_off_audit: dict[str, object],
    runtime: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    return {
        "developer_only_audit": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "selected_object_payload_preserved": (
            runtime["observing_source"]["selected_object_unchanged"] is True
            and runtime["catalogue_source"]["selected_object_unchanged"] is True
        ),
        "nsom_fields_absent_from_selected_object": (
            runtime["observing_source"]["nsom_fields_in_selected_object"] == ()
            and runtime["catalogue_source"]["nsom_fields_in_selected_object"] == ()
        ),
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
        "default_off_readiness_has_no_blockers": default_off_audit["blockers"] == [],
    }


def _readiness_checks(
    default_off_audit: dict[str, object],
    runtime: dict[str, object],
    static_checks: dict[str, object],
    safety: dict[str, object],
) -> dict[str, object]:
    return {
        "default_flag_enabled": NSOM_DETAIL_OBJECT_ENABLED is True,
        "default_off_runtime_path_exists": default_off_audit["readiness"]["runtime_path_exists"] is True,
        "default_off_readiness_has_no_blockers": default_off_audit["blockers"] == [],
        "constructor_rollback_removed": runtime["constructor"]["runtime_rollback_removed"] is True,
        "default_builds_internal_payload": (
            runtime["observing_source"]["internal_payload_present"] is True
            and runtime["catalogue_source"]["internal_payload_present"] is True
        ),
        "selected_object_payload_preserved": safety["selected_object_payload_preserved"] is True,
        "no_nsom_fields_in_selected_object": safety["nsom_fields_absent_from_selected_object"] is True,
        "session_metadata_only": (
            runtime["session"]["score_factor"] is False
            and runtime["session"]["observable_unchanged"] is True
            and runtime["session"]["practical_unchanged"] is True
        ),
        "confidence_score_neutral": (
            runtime["confidence"]["score_factor"] is False
            and runtime["confidence"]["score_effect"] == 0.0
            and runtime["confidence"]["observable_unchanged"] is True
            and runtime["confidence"]["practical_unchanged"] is True
        ),
        "missing_inputs_safe": (
            runtime["missing_inputs"]["missing_sky_quality_returns_empty_payload"] is True
            and runtime["missing_inputs"]["missing_weather_returns_empty_payload"] is True
        ),
        "runtime_objects_not_mutated": runtime["mutation"]["runtime_object_mutated"] is False,
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
    }


def _default_on_blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "default_flag_enabled": "detail-default-flag-not-enabled",
        "default_off_runtime_path_exists": "detail-runtime-path-missing",
        "default_off_readiness_has_no_blockers": "detail-default-off-readiness-blocker",
        "constructor_rollback_removed": "detail-rollback-still-present",
        "default_builds_internal_payload": "detail-default-payload-missing",
        "selected_object_payload_preserved": "detail-selected-object-payload-change",
        "no_nsom_fields_in_selected_object": "detail-selected-object-nsom-field-exposure",
        "session_metadata_only": "detail-session-score-effect",
        "confidence_score_neutral": "detail-confidence-score-effect",
        "missing_inputs_safe": "detail-missing-input-policy",
        "runtime_objects_not_mutated": "detail-runtime-object-mutation",
        "qml_exposure_absent": "detail-qml-exposure",
        "runtime_report_imports_absent": "detail-report-runtime-wiring",
    }
    return tuple(name for key, name in names.items() if checks[key] is not True)


def _non_blocking_risks() -> tuple[str, ...]:
    return (
        "`selectedObject.score` remains legacy/base compatibility data and may not be monotonic with NSOM values.",
        "Visible Detail page NSOM explanations still require a separate UX/design step.",
        "Missing sky quality or weather leaves the internal NSOM payload empty while legacy Detail remains available.",
    )


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "The Detail/Object NSOM default-on switch is active with runtime rollback removed, "
            "preserves `selectedObject`, keeps session/confidence metadata-only "
            "and has no QML or report runtime wiring."
        )
    return "One or more default-on readiness checks need review before changing the flag."


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    return {
        "qml_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
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


def _controller(
    *,
    source: str,
    weather: WeatherSummary | None = None,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._detail_object_nsom_runtime_service = DetailObjectNsomRuntimeService()
    controller._selected_object = _target("galaxy", "Galaxy", 88)
    controller._selected_object_source = source
    controller._weather_summary = weather or _weather(90)
    controller._sky_quality = sky_quality or _sky_quality(3)
    controller._moon = moon if moon is not None else _moon(15)
    controller._current_telescope = lambda: _telescope()
    controller._conditions_service = ObservationConditionsService()
    controller._object_descriptions = {}
    controller._is_catalogue_detail_object = lambda _item: False
    controller._home_time_label = lambda item: item.best_time
    controller._home_window_label = lambda item: item.observing_window
    controller._observing_status = lambda _item: ("", "")
    controller._observing_reasons = lambda _item: []
    controller._setup_reason = lambda _item: ""
    return controller


def _nsom_fields_in_selected_object(payload: dict[str, object]) -> tuple[str, ...]:
    forbidden = (
        "detailObjectNsom",
        "observableTargetValue",
        "practicalTargetValue",
        "sessionViability",
        "recommendationConfidence",
        "observationOpportunity",
        "nsom",
    )
    return tuple(key for key in forbidden if key in payload)


def _target(
    object_id: str,
    object_type: str,
    score: int,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.replace("_", " ").title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:30",
        observing_window="21:00 - 02:00",
        notes="Deterministic Detail NSOM default-on readiness fixture.",
        recommended_setup="Telescopio",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="4 h",
        visible=True,
        score=score,
        score_label="Buono",
        difficulty="Media",
        recommended_setup_type="Telescope",
        apparent_size="20 arcmin",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Buono",
        score_value=score,
        explanation="Deterministic Detail NSOM default-on readiness weather fixture.",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=8,
        humidity=55,
        temperature_c=12.0,
        alert="",
    )


def _sky_quality(bortle: int) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.2,
        sky_brightness=21.2,
        source="deterministic_fixture",
        description="Deterministic Detail NSOM default-on readiness sky fixture.",
        confidence="high",
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=90.0,
    )


def _telescope() -> Telescope:
    return Telescope(
        id="medium-goto",
        name="Medium GoTo",
        aperture_mm=130,
        focal_length_mm=900,
        optical_type="Reflector",
        mount="GoTo EQ",
    )
