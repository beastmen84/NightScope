from __future__ import annotations

from copy import deepcopy
from inspect import signature
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.sky_compass_nsom_ranking import (
    NSOM_SKY_COMPASS_ENABLED,
    SkyCompassNsomDirectionService,
)
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tools.sky_compass_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)
from astro_viewer.tools.sky_compass_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
    generate_policy_readiness_data,
)


DEFAULT_ON_READINESS_AUDIT_PATH = Path("docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "sky_compass_nsom_comparison_report",
    "sky_compass_nsom_policy_readiness",
    "sky_compass_nsom_default_on_readiness_audit",
    "SKY_COMPASS_NSOM_COMPARISON_REPORT",
    "SKY_COMPASS_NSOM_POLICY_READINESS",
    "SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT",
)

QML_MARKERS = (
    "NSOM_SKY_COMPASS_ENABLED",
    "SkyCompassNsomDirectionService",
    "sky_compass_nsom_ranking",
    "sky_compass_nsom_default_on_readiness_audit",
    "SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT",
)


def generate_default_on_readiness_audit_data() -> dict[str, object]:
    comparison = generate_report_data()
    policy = generate_policy_readiness_data()
    runtime = _runtime_policy_evidence()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    safety = _runtime_safety(comparison, policy, runtime, static_checks)
    checks = _readiness_checks(policy, runtime, static_checks, safety)
    blockers = _default_on_blockers(checks)
    ready = blockers == ()

    audit_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "sky_compass_changed_by_this_audit": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "default_off_policy_report": str(POLICY_READINESS_PATH).replace("\\", "/"),
            "audit_report_path": str(DEFAULT_ON_READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "ready_for_sky_compass_nsom_default_on_switch"
                if ready
                else "not_ready_for_sky_compass_nsom_default_on_switch"
            ),
            "ready_for_default_on_switch": ready,
            "default_flag": f"NSOM_SKY_COMPASS_ENABLED = {NSOM_SKY_COMPASS_ENABLED}",
            "default_flag_currently_enabled": NSOM_SKY_COMPASS_ENABLED is True,
            "requires_separate_flag_change": NSOM_SKY_COMPASS_ENABLED is False,
            "runtime_behaviour_changed_by_this_audit": False,
            "explicit_legacy_rollback": "AppController(use_nsom_sky_compass=False)",
            "explicit_nsom_path": "AppController(use_nsom_sky_compass=True)",
            "recommended_switch_change": (
                "already enabled"
                if NSOM_SKY_COMPASS_ENABLED
                else "set NSOM_SKY_COMPASS_ENABLED = True"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "checks": checks,
        "runtime_policy_evidence": runtime,
        "display_score_semantics": _display_score_semantics(runtime),
        "fallback_policy": _fallback_policy(runtime),
        "rollback_policy": _rollback_policy(runtime),
        "non_blocking_risks": _non_blocking_risks(),
        "runtime_safety": safety,
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_default_on_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    runtime = audit["runtime_policy_evidence"]
    display = audit["display_score_semantics"]
    fallback = audit["fallback_policy"]
    rollback = audit["rollback_policy"]
    safety = audit["runtime_safety"]

    lines = [
        "# Sky Compass NSOM Default-On Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the existing default-off Sky "
            "Compass NSOM direction path is ready for a separate default-on switch. "
            "It does not enable the flag, change QML, wire report tooling into "
            "runtime, log automatically, call the network or write runtime files."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
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

    lines.extend(
        [
            "",
            "## Runtime Policy Evidence",
            "",
            "| Policy | Evidence |",
            "| --- | --- |",
            (
                "| Flag off | "
                f"Direction `{runtime['flag_off_legacy']['direction']}`, equals legacy "
                f"`{runtime['flag_off_legacy']['equals_legacy']}`. |"
            ),
            (
                "| Flag on | "
                f"Legacy top `{runtime['flag_on_nsom']['legacy_direction']}`, NSOM top "
                f"`{runtime['flag_on_nsom']['nsom_direction']}`. |"
            ),
            (
                "| Rollback | "
                f"`{rollback['constructor_rollback']}` preserves legacy "
                f"`{rollback['legacy_path_preserved']}`. |"
            ),
            (
                "| Fallback | "
                f"Missing sky quality fallback `{fallback['missing_sky_quality_fallback_present']}`, "
                f"service failure fallback `{fallback['service_failure_fallback_present']}`. |"
            ),
            (
                "| Payload | "
                f"Payload keys unchanged `{runtime['payload']['payload_keys_unchanged']}`, "
                f"target keys unchanged `{runtime['payload']['target_keys_unchanged']}`, "
                f"NSOM fields exposed `{runtime['payload']['nsom_fields_exposed']}`. |"
            ),
            (
                "| Ownership | "
                f"Observable base `{runtime['ownership']['uses_observable_target_value']}`, "
                f"PracticalTargetValue used `{runtime['ownership']['uses_practical_target_value']}`, "
                f"confidence parameter `{runtime['ownership']['accepts_confidence_parameter']}`. |"
            ),
            (
                "| Mutation | "
                f"Runtime objects mutated `{runtime['mutation']['runtime_objects_mutated']}`. |"
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## Displayed Score Semantics",
            "",
            f"- Status: `{display['status']}`.",
            f"- Keep legacy/base displayed score: `{display['keep_legacy_base_score_for_payload_compatibility']}`.",
            f"- Score monotonic with NSOM direction decision: `{display['score_monotonic_with_nsom_direction']}`.",
            f"- Blocks default-on switch: `{display['blocks_default_on_switch']}`.",
            f"- Decision: {display['decision']}",
            f"- Future UI work: {display['future_ui_work']}",
            "",
            "## Fallback And Rollback",
            "",
            f"- Missing sky quality fallback: `{fallback['missing_sky_quality_fallback_present']}`.",
            f"- Service failure fallback: `{fallback['service_failure_fallback_present']}`.",
            f"- Fallback target: {fallback['runtime_fallback']}",
            f"- Blocks default-on switch: `{fallback['blocks_default_on_switch']}`.",
            f"- Constructor rollback: `{rollback['constructor_rollback']}`.",
            f"- Legacy path preserved: `{rollback['legacy_path_preserved']}`.",
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
            (
                "Review this audit. If accepted, implement a separate switch-only "
                "commit that sets `NSOM_SKY_COMPASS_ENABLED = True`, preserves "
                "`AppController(use_nsom_sky_compass=False)` as rollback and keeps "
                "the `skyCompass` QML payload shape unchanged."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = DEFAULT_ON_READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _runtime_policy_evidence() -> dict[str, object]:
    targets = tuple(_targets())
    before = deepcopy(targets)
    sky_quality = _sky_quality(9, radiance=120.0)
    moon = _moon(20)

    legacy_service = SkyCompassService()
    legacy_payload = legacy_service.compass(list(targets), [], None, has_location=True)
    nsom_payload = SkyCompassNsomDirectionService().compass(
        list(targets),
        [],
        None,
        sky_quality=sky_quality,
        moon=moon,
        has_location=True,
    )

    flag_off = _controller(use_nsom_sky_compass=False, sky_quality=sky_quality)
    flag_on = _controller(use_nsom_sky_compass=True, sky_quality=sky_quality)
    missing_quality = _controller(use_nsom_sky_compass=True, sky_quality=None)
    failing = _controller(
        use_nsom_sky_compass=True,
        sky_quality=sky_quality,
        nsom_service=_FailingSkyCompassNsomService(),
    )

    flag_off_payload = flag_off._select_sky_compass_payload(list(targets), has_location=True, caution_text="")
    flag_on_payload = flag_on._select_sky_compass_payload(list(targets), has_location=True, caution_text="")
    missing_quality_payload = missing_quality._select_sky_compass_payload(
        list(targets),
        has_location=True,
        caution_text="",
    )
    failing_payload = failing._select_sky_compass_payload(list(targets), has_location=True, caution_text="")

    service_source = (Path(__file__).parents[1] / "app" / "services" / "sky_compass_nsom_ranking.py").read_text(
        encoding="utf-8"
    )
    compass_parameters = tuple(signature(SkyCompassNsomDirectionService.compass).parameters)

    return {
        "flag_off_legacy": {
            "direction": flag_off_payload["direction"],
            "equals_legacy": flag_off_payload == legacy_payload,
        },
        "flag_on_nsom": {
            "legacy_direction": legacy_payload["direction"],
            "nsom_direction": flag_on_payload["direction"],
            "matches_direct_service": flag_on_payload == nsom_payload,
            "direction_changes_in_high_light_pollution": flag_on_payload["direction"] != legacy_payload["direction"],
        },
        "fallback": {
            "missing_sky_quality_equals_legacy": missing_quality_payload == legacy_payload,
            "service_failure_equals_legacy": failing_payload == legacy_payload,
        },
        "payload": {
            "legacy_keys": tuple(sorted(legacy_payload)),
            "nsom_keys": tuple(sorted(nsom_payload)),
            "payload_keys_unchanged": set(legacy_payload) == set(nsom_payload),
            "target_keys_unchanged": _target_payload_keys(legacy_payload) == _target_payload_keys(nsom_payload),
            "nsom_fields_exposed": _payload_has_nsom_fields(nsom_payload),
            "display_scores": tuple(item["score"] for item in nsom_payload["targets"]),
            "primary_target_ids": tuple(item["id"] for item in nsom_payload["primaryTargets"]),
        },
        "ownership": {
            "uses_observable_target_value": "build_home_observable_target_value" in service_source,
            "uses_practical_target_value": "PracticalTargetValue" in service_source,
            "uses_observer_capability": "ObserverCapability" in service_source,
            "uses_session_viability": "SessionViability" in service_source,
            "uses_recommendation_confidence": "RecommendationConfidence" in service_source,
            "accepts_weather_parameter": "weather" in compass_parameters,
            "accepts_telescope_parameter": "telescope" in compass_parameters,
            "accepts_confidence_parameter": "confidence" in compass_parameters,
            "confidence_score_effect": 0.0,
        },
        "mutation": {
            "runtime_objects_mutated": targets != before,
        },
    }


def _readiness_checks(
    policy: dict[str, object],
    runtime: dict[str, object],
    static_checks: dict[str, object],
    safety: dict[str, object],
) -> dict[str, object]:
    return {
        "default_off_policy_ready": policy["readiness"]["ready_for_default_off_path"] is True,
        "default_flag_currently_off": NSOM_SKY_COMPASS_ENABLED is False,
        "default_on_requires_separate_flag_change": NSOM_SKY_COMPASS_ENABLED is False,
        "legacy_rollback_available": runtime["flag_off_legacy"]["equals_legacy"] is True,
        "flag_on_uses_nsom_path": runtime["flag_on_nsom"]["matches_direct_service"] is True,
        "high_light_pollution_direction_changes_as_expected": runtime["flag_on_nsom"][
            "direction_changes_in_high_light_pollution"
        ]
        is True,
        "payload_shape_unchanged": runtime["payload"]["payload_keys_unchanged"] is True
        and runtime["payload"]["target_keys_unchanged"] is True,
        "no_nsom_fields_in_payload": runtime["payload"]["nsom_fields_exposed"] is False,
        "fallback_policy_present": runtime["fallback"]["missing_sky_quality_equals_legacy"] is True
        and runtime["fallback"]["service_failure_equals_legacy"] is True,
        "candidate_base_is_observable": runtime["ownership"]["uses_observable_target_value"] is True,
        "practical_target_value_not_used": runtime["ownership"]["uses_practical_target_value"] is False,
        "observer_capability_not_used": runtime["ownership"]["uses_observer_capability"] is False,
        "session_viability_not_used": runtime["ownership"]["uses_session_viability"] is False,
        "confidence_score_neutral": runtime["ownership"]["uses_recommendation_confidence"] is False
        and runtime["ownership"]["accepts_confidence_parameter"] is False
        and runtime["ownership"]["confidence_score_effect"] == 0.0,
        "weather_and_equipment_not_in_direction_score": runtime["ownership"]["accepts_weather_parameter"] is False
        and runtime["ownership"]["accepts_telescope_parameter"] is False,
        "runtime_objects_not_mutated": runtime["mutation"]["runtime_objects_mutated"] is False,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_safety_all_clear": all(value is True for value in safety.values()),
    }


def _runtime_safety(
    comparison: dict[str, object],
    policy: dict[str, object],
    runtime: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    return {
        "current_flag_default_off": NSOM_SKY_COMPASS_ENABLED is False,
        "default_off_policy_ready": policy["readiness"]["ready_for_default_off_path"] is True,
        "comparison_tooling_developer_only": comparison["metadata"]["developer_only"] is True,
        "comparison_tooling_has_no_runtime_writes": comparison["metadata"]["runtime_writes"] is False,
        "comparison_tooling_has_no_automatic_logging": comparison["metadata"]["automatic_logging"] is False,
        "comparison_tooling_has_no_network": comparison["metadata"]["network"] is False,
        "comparison_tooling_has_no_qml_exposure": comparison["metadata"]["qml_exposure"] is False,
        "sky_compass_runtime_unchanged_by_this_audit": True,
        "home_runtime_unchanged": True,
        "best_object_runtime_unchanged": True,
        "planner_runtime_unchanged": True,
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "runtime_objects_not_mutated": runtime["mutation"]["runtime_objects_mutated"] is False,
    }


def _default_on_blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "default_off_policy_ready": "sky-compass-default-off-policy-not-ready",
        "default_flag_currently_off": "sky-compass-flag-not-default-off-before-switch",
        "default_on_requires_separate_flag_change": "sky-compass-default-on-not-separate-switch",
        "legacy_rollback_available": "sky-compass-legacy-rollback-missing",
        "flag_on_uses_nsom_path": "sky-compass-flag-on-not-nsom",
        "high_light_pollution_direction_changes_as_expected": "sky-compass-nsom-behaviour-not-observable",
        "payload_shape_unchanged": "sky-compass-payload-shape-change",
        "no_nsom_fields_in_payload": "sky-compass-nsom-fields-in-payload",
        "fallback_policy_present": "sky-compass-fallback-policy-missing",
        "candidate_base_is_observable": "sky-compass-candidate-base-not-observable",
        "practical_target_value_not_used": "sky-compass-practical-value-leak",
        "observer_capability_not_used": "sky-compass-observer-capability-leak",
        "session_viability_not_used": "sky-compass-session-viability-leak",
        "confidence_score_neutral": "sky-compass-confidence-score-effect",
        "weather_and_equipment_not_in_direction_score": "sky-compass-weather-equipment-leak",
        "runtime_objects_not_mutated": "sky-compass-runtime-object-mutation",
        "runtime_report_imports_absent": "sky-compass-runtime-report-wiring",
        "qml_exposure_absent": "sky-compass-qml-exposure",
        "runtime_safety_all_clear": "sky-compass-runtime-safety",
    }
    return tuple(name for key, name in names.items() if checks[key] is not True)


def _display_score_semantics(runtime: dict[str, object]) -> dict[str, object]:
    legacy_top = runtime["flag_on_nsom"]["legacy_direction"]
    nsom_top = runtime["flag_on_nsom"]["nsom_direction"]
    return {
        "status": "accepted_non_blocking_for_default_on",
        "keep_legacy_base_score_for_payload_compatibility": True,
        "score_monotonic_with_nsom_direction": legacy_top == nsom_top,
        "blocks_default_on_switch": False,
        "decision": (
            "The `score` field remains the existing target display/base score so the "
            "QML contract stays compatible. It is not a Sky Compass NSOM rationale."
        ),
        "future_ui_work": (
            "If the UI later needs score rationale, add separate explanation fields "
            "in a dedicated design step rather than changing this default-on switch."
        ),
    }


def _fallback_policy(runtime: dict[str, object]) -> dict[str, object]:
    return {
        "status": "accepted_for_default_on",
        "missing_sky_quality_fallback_present": runtime["fallback"]["missing_sky_quality_equals_legacy"] is True,
        "service_failure_fallback_present": runtime["fallback"]["service_failure_equals_legacy"] is True,
        "runtime_fallback": "legacy SkyCompassService.compass(...)",
        "blocks_default_on_switch": False,
        "reason": (
            "Sky Compass remains usable when NSOM ObservableTargetValue cannot be "
            "built from local sky-quality context."
        ),
    }


def _rollback_policy(runtime: dict[str, object]) -> dict[str, object]:
    return {
        "constructor_rollback": "AppController(use_nsom_sky_compass=False)",
        "legacy_path_preserved": runtime["flag_off_legacy"]["equals_legacy"] is True,
        "blocks_default_on_switch": False,
    }


def _non_blocking_risks() -> tuple[str, ...]:
    return (
        "Default-on will intentionally change direction choice in some bright-sky/high-light-pollution scenarios.",
        "The displayed target `score` remains legacy/base compatibility data and is not an NSOM direction rationale.",
        "Sky Compass still has no visible NSOM explanation UI; adding one should be a separate UX/design step.",
        "Missing sky quality keeps the legacy fallback, so default-on coverage is partial until sky quality is available.",
        "Equipment-aware compass semantics remain deferred because `PracticalTargetValue` is intentionally not used.",
    )


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "qml_matches": _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
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
    use_nsom_sky_compass: bool,
    sky_quality: SkyQuality | None,
    nsom_service: object | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._use_nsom_sky_compass = use_nsom_sky_compass
    controller._sky_quality = sky_quality
    controller._moon = _moon(20)
    controller._sky_compass_service = SkyCompassService()
    controller._sky_compass_nsom_direction_service = nsom_service or SkyCompassNsomDirectionService()
    controller._night_plan = []
    controller._best_object = None
    return controller


class _FailingSkyCompassNsomService:
    def compass(self, *_args: object, **_kwargs: object) -> dict:
        raise RuntimeError("fixture")


def _targets() -> tuple[CelestialObject, ...]:
    return (
        _target("jupiter", "Jupiter", "Pianeta", "Est", 86, magnitude="-2.1", difficulty="Facile"),
        _target("moon", "Moon", "Moon", "Ovest", 82, magnitude="-12.0", difficulty="Facile"),
        _target("galaxy", "Galaxy", "Galaxy", "Sud", 90, magnitude="8.2"),
        _target("diffuse_nebula", "Diffuse Nebula", "Nebula", "Sud", 88, magnitude="7.0"),
        _target(
            "open_cluster",
            "Open Cluster",
            "Open Cluster",
            "Nord-Est",
            78,
            magnitude="5.2",
            difficulty="Facile",
        ),
        _target("globular_cluster", "Globular Cluster", "Globular Cluster", "Nord-Est", 84, magnitude="6.8"),
    )


def _target(
    object_id: str,
    name: str,
    object_type: str,
    direction: str,
    score: int,
    *,
    magnitude: str = "8.0",
    difficulty: str = "Media",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction=direction,
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Sky Compass default-on readiness fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="SkyCompassDefaultOnReadinessFixture",
        description="Sky Compass default-on readiness fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )


def _target_payload_keys(payload: dict[str, object]) -> set[str]:
    keys: set[str] = set()
    for key in ("targets", "primaryTargets"):
        for item in payload[key]:
            keys.update(item)
    return keys


def _payload_has_nsom_fields(payload: dict[str, object]) -> bool:
    text = str(payload).lower()
    return any(marker in text for marker in ("nsom", "observable", "practical", "confidence"))


def _order_label(order: object) -> str:
    return " > ".join(str(item) for item in order)


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "The default-off Sky Compass NSOM path has explicit rollback, legacy "
            "fallback, unchanged payload shape, documented non-blocking risks and "
            "no QML/report runtime wiring. Default-on can be a separate flag-only "
            "switch after review."
        )
    return "One or more Sky Compass default-on readiness checks still blocks the switch."


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
