from __future__ import annotations

import inspect
import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
import astro_viewer.app.services.observation_conditions_service as observation_conditions_module
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.viewmodels.app_controller import AppController


REPORT_PATH = Path("docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "observation_conditions_read_model_audit",
    "OBSERVATION_CONDITIONS_READ_MODEL_AUDIT",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_observation_conditions_read_model_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    service = ObservationConditionsService()
    raw_target = _target("m31", "M31", "Galaxy", 88, magnitude="8.8")
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    moon = _moon("92%")

    pollution = service.apply_deep_sky_pollution_to_target(raw_target, sky_quality)
    moon_conditioned = service.apply_moon_adjustment(raw_target, moon)
    combined = service.condition_target(
        raw_target,
        ObservationConditionInputs(moon=moon, sky_quality=sky_quality),
        apply_moon=True,
        apply_pollution=True,
    )
    reapplied_pollution = service.apply_deep_sky_pollution_to_target(pollution.target, sky_quality)
    read_model = ObservationConditionsReadModelBuilder().from_conditioned_target(
        combined,
        source="observation_conditions_read_model_audit",
    )

    raw_observable = build_home_observable_target_value(raw_target, sky_quality=sky_quality, moon=moon)
    pollution_observable = build_home_observable_target_value(
        pollution.target,
        sky_quality=sky_quality,
        moon=moon,
    )
    combined_observable = build_home_observable_target_value(
        combined.target,
        sky_quality=sky_quality,
        moon=moon,
    )

    static_checks = _static_wiring_checks(root)
    controller_checks = _controller_static_checks()
    service_checks = _service_static_checks()
    phenomenon_fixture = _phenomenon_fixture(
        raw_target=raw_target,
        pollution=pollution,
        moon_conditioned=moon_conditioned,
        combined=combined,
        reapplied_pollution=reapplied_pollution,
        raw_observable_value=raw_observable.value,
        pollution_observable_value=pollution_observable.value,
        combined_observable_value=combined_observable.value,
    )
    read_model_fixture = _read_model_fixture(read_model)
    checks = _checks(
        static_checks,
        controller_checks,
        service_checks,
        phenomenon_fixture,
        read_model_fixture,
    )
    blockers = _blockers(checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "read_model_boundary_introduced_consumer_reroute_pending"
                if checks["read_model_boundary_present"]
                else "read_model_boundary_required_before_cleanup"
            ),
            "runtime_migration_recommended_now": False,
            "safe_to_remove_service": False,
            "safe_to_keep_current_runtime_temporarily": True,
            "recommended_next_step": (
                "Review the 1.12.6 boundary, then decide whether NSOM Home, Best "
                "Object and Sky Compass consumers can read raw read-model targets "
                "without changing presentation payloads unexpectedly."
                if checks["read_model_boundary_present"]
                else (
                    "Review this audit, then introduce an ObservationConditions "
                    "read-model boundary that separates raw target score, "
                    "condition-adjusted display score and NSOM ObservableTargetValue "
                    "inputs."
                )
            ),
            "reason": (
                "ObservationConditionsService is active runtime code. It returns "
                "replacement CelestialObject instances for Moon and light-pollution "
                "presentation compatibility, and those conditioned objects can become "
                "inputs to default-on NSOM Home/Best Object/Sky Compass observable "
                "calculations. The 1.12.6 boundary now preserves raw and display "
                "targets separately, but runtime consumer rerouting remains a "
                "separate behaviour-changing review."
                if checks["read_model_boundary_present"]
                else (
                    "calculations. That is a read-model boundary problem, not dead "
                    "code."
                )
            ),
        },
        "blockers": blockers,
        "ownership": {
            "current_owner": "ObservationConditionsService",
            "owns_today": (
                "Moon-adjusted display score copies",
                "light-pollution display/context copies",
                "AOD/PM/Moon-geometry score-neutral diagnostics",
                "double-counting condition flags",
            ),
            "should_not_own": (
                "ObserverCapability",
                "PracticalTargetValue",
                "SessionViability",
                "RecommendationConfidence aggregation",
                "Planner chronology",
                "visible QML field design",
            ),
            "target_state": (
                "A read model with raw_target, condition_breakdown, display_score, "
                "display_notes, condition_flags and NSOM-safe raw ObservableTargetValue input."
            ),
        },
        "runtime_consumers": _runtime_consumers(),
        "controller_static_checks": controller_checks,
        "service_static_checks": service_checks,
        "phenomenon_fixture": phenomenon_fixture,
        "read_model_fixture": read_model_fixture,
        "checks": checks,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.12.5",
                "summary": (
                    "Confirm the ObservationConditions audit correctly identifies "
                    "active consumers and read-model risks."
                ),
            },
            {
                "step": "1.12.6 ObservationConditions read-model boundary",
                "summary": (
                    "Introduce explicit raw/display/conditioned fields without "
                    "changing visible ranking or QML payload shape."
                ),
            },
            {
                "step": "Review 1.12.6",
                "summary": (
                    "Verify NSOM consumers read raw target inputs while legacy "
                    "display compatibility reads display fields."
                ),
            },
            {
                "step": "1.12.7 ObservationConditions consumer reroute audit",
                "summary": (
                    "Define raw-target consumer policy before changing Home, Best "
                    "Object or Sky Compass runtime inputs."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_observation_conditions_read_model_audit_data() if data is None else data
    readiness = audit["readiness"]
    fixture = audit["phenomenon_fixture"]
    read_model = audit["read_model_fixture"]

    lines = [
        "# ObservationConditions NSOM Read-Model Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews the active ObservationConditions "
            "runtime boundary after Sky Map and Notifications were removed as dead "
            "legacy. It does not change runtime behaviour, QML, scoring, logging, "
            "network access or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Runtime migration recommended now: `{readiness['runtime_migration_recommended_now']}`.",
        f"- Safe to remove service: `{readiness['safe_to_remove_service']}`.",
        f"- Safe to keep current runtime temporarily: `{readiness['safe_to_keep_current_runtime_temporarily']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Blockers",
        "",
    ]
    if audit["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["blockers"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Ownership",
            "",
            f"- Current owner: `{audit['ownership']['current_owner']}`.",
            f"- Owns today: `{audit['ownership']['owns_today']}`.",
            f"- Should not own: `{audit['ownership']['should_not_own']}`.",
            f"- Target state: {audit['ownership']['target_state']}",
            "",
            "## Runtime Consumers",
            "",
            "| Consumer | Uses conditioned object | Uses NSOM observable | Current risk |",
            "| --- | --- | --- | --- |",
        ]
    )
    for consumer in audit["runtime_consumers"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    consumer["consumer"],
                    f"`{consumer['uses_conditioned_object']}`",
                    f"`{consumer['uses_nsom_observable']}`",
                    consumer["current_risk"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Phenomenon Fixture",
            "",
            f"- Raw score: `{fixture['raw_score']}`.",
            f"- Pollution-conditioned score: `{fixture['pollution_conditioned_score']}`.",
            f"- Moon-conditioned score: `{fixture['moon_conditioned_score']}`.",
            f"- Combined-conditioned score: `{fixture['combined_conditioned_score']}`.",
            f"- Raw ObservableTargetValue: `{fixture['raw_observable_value']}`.",
            f"- Pollution-conditioned ObservableTargetValue: `{fixture['pollution_conditioned_observable_value']}`.",
            f"- Combined-conditioned ObservableTargetValue: `{fixture['combined_conditioned_observable_value']}`.",
            f"- NSOM conditioned-score input risk: `{fixture['nsom_conditioned_score_input_risk']}`.",
            f"- Original target mutated: `{fixture['original_target_mutated']}`.",
            f"- Pollution reapply guarded: `{fixture['pollution_reapply_guarded']}`.",
            "",
            "## Read-Model Boundary",
            "",
            f"- Object id: `{read_model['object_id']}`.",
            f"- Raw score: `{read_model['raw_score']}`.",
            f"- Display score: `{read_model['display_score']}`.",
            f"- Applied components: `{read_model['applied_components']}`.",
            f"- Condition flags: `{read_model['condition_flags']}`.",
            f"- Raw target preserved for NSOM input: `{read_model['raw_target_preserved']}`.",
            f"- QML display target preserved: `{read_model['display_target_preserved']}`.",
            f"- NSOM input uses raw target: `{read_model['nsom_input_uses_raw_target']}`.",
            f"- Strict JSON compatible: `{read_model['strict_json_compatible']}`.",
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
                "ObservationConditions is not dead legacy. The 1.12.6 read-model "
                "boundary now preserves raw and display targets separately, while "
                "runtime consumer rerouting remains a separate behaviour-reviewed "
                "step before condition-adjusted CelestialObject scores can be "
                "fully removed from NSOM intrinsic input paths."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _checks(
    static_checks: dict[str, object],
    controller_checks: dict[str, object],
    service_checks: dict[str, object],
    fixture: dict[str, object],
    read_model_fixture: dict[str, object],
) -> dict[str, object]:
    return {
        "service_is_active_runtime_code": controller_checks["conditions_service_instantiated"] is True,
        "conditioned_caches_present": controller_checks["conditioned_caches_present"] is True,
        "pollution_context_writes_deep_sky_cache": controller_checks["pollution_context_writes_deep_sky_cache"] is True,
        "home_nsom_can_consume_conditioned_candidates": controller_checks[
            "home_nsom_ranking_gets_deep_sky_candidates"
        ]
        is True,
        "best_object_can_consume_pollution_conditioned_deep_sky": controller_checks[
            "best_object_planning_uses_deep_sky_cache"
        ]
        is True,
        "sky_compass_uses_conditioned_cache": controller_checks["sky_compass_uses_conditioned_cache"] is True,
        "service_uses_replacement_not_mutation": fixture["original_target_mutated"] is False,
        "service_preserves_original_target_reference": fixture["original_target_preserved"] is True,
        "double_count_guard_present_for_pollution": fixture["pollution_reapply_guarded"] is True,
        "nsom_conditioned_score_input_risk_visible": fixture["nsom_conditioned_score_input_risk"] is True,
        "read_model_boundary_present": (
            controller_checks["read_model_caches_present"] is True
            and controller_checks["read_model_builder_present"] is True
            and service_checks["conditioned_pollution_context_available"] is True
            and read_model_fixture["raw_target_preserved"] is True
            and read_model_fixture["nsom_input_uses_raw_target"] is True
        ),
        "read_model_strict_json_compatible": read_model_fixture["strict_json_compatible"] is True,
        "read_model_display_score_separate_from_raw_score": (
            read_model_fixture["raw_score"] != read_model_fixture["display_score"]
        ),
        "aod_pm_score_neutral_today": service_checks["aod_pm_modifiers_neutral"] is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    if checks["nsom_conditioned_score_input_risk_visible"]:
        blockers.append("observation-conditions-conditioned-score-as-nsom-intrinsic")
    if checks["pollution_context_writes_deep_sky_cache"]:
        blockers.append("observation-conditions-deep-sky-cache-is-condition-adjusted")
    if not checks["read_model_boundary_present"]:
        blockers.append("observation-conditions-read-model-boundary-missing")
    if checks["read_model_strict_json_compatible"] is not True:
        blockers.append("observation-conditions-read-model-json-incompatible")
    if checks["read_model_display_score_separate_from_raw_score"] is not True:
        blockers.append("observation-conditions-read-model-score-boundary-missing")
    safety_names = {
        "service_is_active_runtime_code": "observation-conditions-service-not-detected",
        "service_uses_replacement_not_mutation": "observation-conditions-mutates-targets",
        "service_preserves_original_target_reference": "observation-conditions-original-target-lost",
        "double_count_guard_present_for_pollution": "observation-conditions-pollution-reapply-unguarded",
        "aod_pm_score_neutral_today": "observation-conditions-aod-pm-score-effect",
        "runtime_report_imports_absent": "observation-conditions-audit-runtime-wiring",
        "qml_report_exposure_absent": "observation-conditions-audit-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "observation-conditions-audit-runtime-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _runtime_consumers() -> tuple[dict[str, object], ...]:
    return (
        {
            "consumer": "Home recommendedDeepSky",
            "uses_conditioned_object": True,
            "uses_nsom_observable": True,
            "current_risk": (
                "Default-on Home NSOM ranks ObservableTargetValue from the current "
                "deep-sky candidate objects; those objects may already carry "
                "condition-adjusted display scores."
            ),
        },
        {
            "consumer": "Best Object",
            "uses_conditioned_object": True,
            "uses_nsom_observable": True,
            "current_risk": (
                "Best Object receives planning objects from the controller deep-sky "
                "cache, so condition-adjusted score can become intrinsic target input."
            ),
        },
        {
            "consumer": "Sky Compass",
            "uses_conditioned_object": True,
            "uses_nsom_observable": True,
            "current_risk": (
                "Sky Compass intentionally uses the conditioned cache for display "
                "compatibility, but NSOM direction policy also computes observable "
                "values from those targets."
            ),
        },
        {
            "consumer": "Detail/Object selectedObject",
            "uses_conditioned_object": True,
            "uses_nsom_observable": False,
            "current_risk": (
                "Visible Detail keeps a moon-adjusted compatibility display score; "
                "future visible NSOM detail fields need a separate raw/read-model input."
            ),
        },
        {
            "consumer": "Planner",
            "uses_conditioned_object": False,
            "uses_nsom_observable": False,
            "current_risk": (
                "Planner has its own NSOM path and should not consume conditioned "
                "Home display objects as target physics."
            ),
        },
    )


def _controller_static_checks() -> dict[str, object]:
    source = inspect.getsource(AppController)
    recalculate_source = inspect.getsource(AppController._recalculate_observing_outputs)
    recommended_source = inspect.getsource(AppController._recommended_deep_sky_candidates)
    compass_source = inspect.getsource(AppController._sky_compass_candidates)
    return {
        "conditions_service_instantiated": "self._conditions_service = ObservationConditionsService()" in source,
        "conditioned_caches_present": "_conditioned_deep_sky" in source and "_conditioned_home_objects" in source,
        "read_model_builder_present": "ObservationConditionsReadModelBuilder()" in source,
        "read_model_caches_present": (
            "_conditioned_deep_sky_read_model" in source
            and "_conditioned_home_read_model" in source
            and "_deep_sky_pollution_read_model" in source
        ),
        "pollution_context_writes_deep_sky_cache": "self._deep_sky = self._apply_deep_sky_pollution_context(self._deep_sky)" in source,
        "home_nsom_ranking_gets_deep_sky_candidates": (
            "rank_by_observable_target_value" in recommended_source
            and "objects" in recommended_source
        ),
        "best_object_planning_uses_deep_sky_cache": "self._visible_planets + self._deep_sky" in recalculate_source,
        "sky_compass_uses_conditioned_cache": "_conditioned_deep_sky_candidates()" in compass_source,
        "selected_object_uses_moon_adjusted_copy": "_moon_adjusted_object(self._selected_object)" in source,
    }


def _service_static_checks() -> dict[str, object]:
    source = inspect.getsource(ObservationConditionsService)
    module_source = inspect.getsource(observation_conditions_module)
    return {
        "returns_conditioned_target": "return ConditionedTarget(" in source,
        "conditioned_pollution_context_available": "def condition_deep_sky_pollution_context" in source,
        "uses_dataclass_replace_for_adjusted_copy": "replace(" in source,
        "tracks_condition_flags": "condition_flags" in source,
        "aod_pm_modifiers_neutral": (
            "experimental_aerosol_scoring: bool = False" in module_source
            and "aod_modifier = 0.0" in source
            and "pm25_modifier = 0.0" in source
            and "aerosol_scoring:flag_off" in source
        ),
        "experimental_flags_default_off": "experimental_aerosol_scoring: bool = False" in module_source,
    }


def _read_model_fixture(read_model) -> dict[str, object]:
    payload = read_model.to_dict()
    return {
        "object_id": read_model.object_id,
        "raw_score": read_model.raw_score,
        "display_score": read_model.display_score,
        "applied_components": read_model.applied_components,
        "condition_flags": read_model.condition_flags,
        "raw_target_preserved": read_model.raw_target is read_model.nsom_target_input,
        "display_target_preserved": read_model.display_target is read_model.qml_display_target,
        "nsom_input_uses_raw_target": read_model.nsom_target_input.score == read_model.raw_score,
        "display_uses_conditioned_target": read_model.qml_display_target.score == read_model.display_score,
        "strict_json_compatible": _strict_json_compatible(payload),
        "payload": payload,
    }


def _phenomenon_fixture(
    *,
    raw_target: CelestialObject,
    pollution,
    moon_conditioned,
    combined,
    reapplied_pollution,
    raw_observable_value: float,
    pollution_observable_value: float,
    combined_observable_value: float,
) -> dict[str, object]:
    return {
        "target_id": raw_target.id,
        "raw_score": raw_target.score,
        "pollution_conditioned_score": pollution.target.score,
        "moon_conditioned_score": moon_conditioned.target.score,
        "combined_conditioned_score": combined.target.score,
        "pollution_penalty": pollution.breakdown.pollution_penalty,
        "moon_penalty": moon_conditioned.breakdown.moon_penalty,
        "combined_components": combined.breakdown.applied_components,
        "condition_flags": pollution.target.condition_flags,
        "already_adjusted_flags_on_reapply": reapplied_pollution.breakdown.already_adjusted_flags,
        "raw_observable_value": round(raw_observable_value, 6),
        "pollution_conditioned_observable_value": round(pollution_observable_value, 6),
        "combined_conditioned_observable_value": round(combined_observable_value, 6),
        "nsom_conditioned_score_input_risk": pollution_observable_value < raw_observable_value,
        "original_target_mutated": raw_target.score != 88 or bool(raw_target.condition_flags),
        "original_target_preserved": pollution.original_target == raw_target,
        "pollution_reapply_guarded": reapplied_pollution.breakdown.pollution_penalty == 0.0
        and "light_pollution" in reapplied_pollution.breakdown.already_adjusted_flags,
    }


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


def _strict_json_compatible(payload: object) -> bool:
    try:
        json.dumps(payload, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


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


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    *,
    magnitude: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="ObservationConditions read-model audit fixture",
        recommended_setup="Dobson 200 + 25 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="4 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty="Media",
    )


def _sky_quality(*, bortle: int, radiance: float) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=4.8,
        sky_brightness=18.4,
        source="ObservationConditionsReadModelAuditFixture",
        description="ObservationConditions read-model audit fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: str) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=illumination,
        rise_time="19:00",
        set_time="05:00",
        best_note="Fixture",
        image="",
    )


if __name__ == "__main__":
    write_markdown_report()
