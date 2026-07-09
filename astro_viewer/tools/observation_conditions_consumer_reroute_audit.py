from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionedTargetReadModel,
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)


REPORT_PATH = Path("docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "observation_conditions_consumer_reroute_audit",
    "OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_observation_conditions_consumer_reroute_audit_data() -> dict[str, object]:
    """Developer-only audit for read-model consumer reroute policy."""

    root = Path(__file__).parents[2]
    sky_quality = _sky_quality()
    moon = _moon("92%")
    read_models = _fixture_read_models(sky_quality=sky_quality, moon=moon)
    evaluations = _evaluations(read_models, sky_quality=sky_quality, moon=moon)
    deep_sky = tuple(item for item in evaluations if item["target_group"] == "deep_sky")
    consumer_policies = _consumer_policies(deep_sky)
    static_checks = _static_wiring_checks(root)
    checks = _checks(evaluations, consumer_policies, static_checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "home_changed": True,
            "best_object_changed": True,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "home_and_best_object_rerouted_sky_compass_pending",
            "runtime_reroute_recommended_now": True,
            "safe_to_change_runtime_in_this_step": False,
            "safe_to_keep_current_runtime_temporarily": True,
            "recommended_next_step": (
                "Review the 1.12.9 Best Object raw-target reroute, then decide "
                "whether Sky Compass should consume read-model raw targets for "
                "its observable contribution."
            ),
            "reason": (
                "The read-model boundary exposes raw target inputs and conditioned "
                "display targets separately. Home recommendedDeepSky now ranks "
                "the NSOM path from read_model.nsom_target_input while returning "
                "read_model.qml_display_target for payload compatibility. Best "
                "Object now scores raw read-model candidates and returns the "
                "selected display target. Sky Compass still requires a separate "
                "behaviour-reviewed direction reroute."
            ),
        },
        "blockers": _blockers(checks),
        "consumer_policies": consumer_policies,
        "fixture": {
            "sky_quality": sky_quality,
            "moon": moon,
            "evaluations": evaluations,
            "display_observable_order": _order(deep_sky, "display_observable_value"),
            "raw_observable_order": _order(deep_sky, "raw_observable_value"),
        },
        "checks": checks,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.12.6",
                "summary": (
                    "Confirm the read-model boundary preserves raw and display "
                    "target fields without runtime behaviour changes."
                ),
            },
            {
                "step": "1.12.7 ObservationConditions consumer reroute audit",
                "summary": (
                    "Define the consumer policy before changing Home, Best Object "
                    "or Sky Compass runtime inputs."
                ),
            },
            {
                "step": "Review 1.12.7",
                "summary": (
                    "Confirm raw-target reroute policy and choose the first "
                    "runtime consumer migration."
                ),
            },
            {
                "step": "1.12.8 Home recommendedDeepSky raw-target reroute",
                "summary": (
                    "Rank Home recommendedDeepSky NSOM candidates from the raw "
                    "read-model target while preserving display payload targets."
                ),
            },
            {
                "step": "1.12.9 Best Object raw-target reroute",
                "summary": (
                    "Score Best Object NSOM candidates from raw read-model targets "
                    "while returning the selected display target."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_observation_conditions_consumer_reroute_audit_data() if data is None else data
    readiness = audit["readiness"]
    fixture = audit["fixture"]

    lines = [
        "# ObservationConditions Consumer Reroute Audit",
        "",
        "## Executive Summary",
        "",
            (
                "This developer-only audit reviews whether NSOM consumers should use "
                "the raw target side of the ObservationConditions read model. Home "
                "recommendedDeepSky and Best Object have now been rerouted; Sky "
                "Compass remains pending. The audit itself does not change runtime "
                "behaviour, QML, scoring, logging, network access or runtime file "
                "writes."
            ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Runtime reroute recommended now: `{readiness['runtime_reroute_recommended_now']}`.",
        f"- Safe to change runtime in this step: `{readiness['safe_to_change_runtime_in_this_step']}`.",
        f"- Safe to keep current runtime temporarily: `{readiness['safe_to_keep_current_runtime_temporarily']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Consumer Policies",
        "",
        "| Consumer | Current input | Candidate input | Payload target | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for policy in audit["consumer_policies"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    policy["consumer"],
                    policy["current_runtime_input"],
                    policy["candidate_raw_input"],
                    policy["payload_target"],
                    f"`{policy['status']}`",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Raw Vs Display Observable Fixture",
            "",
            f"- Display observable order: `{fixture['display_observable_order']}`.",
            f"- Raw observable order: `{fixture['raw_observable_order']}`.",
            "",
            "| Target | Raw score | Display score | Raw observable | Display observable | Delta |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in fixture["evaluations"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["object_id"],
                    str(item["raw_score"]),
                    str(item["display_score"]),
                    f"{float(item['raw_observable_value']):.6f}",
                    f"{float(item['display_observable_value']):.6f}",
                    f"{float(item['raw_minus_display_observable']):.6f}",
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
                "The NSOM-correct direction is to score Home, Best Object and Sky "
                "Compass from raw read-model targets while preserving conditioned "
                "display targets for compatibility payloads. Home recommendedDeepSky "
                "and Best Object now follow this policy. Sky Compass should be "
                "rerouted in a separate reviewed commit because it can change "
                "direction ranking."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _fixture_read_models(
    *,
    sky_quality: SkyQuality,
    moon: MoonSummary,
) -> tuple[ObservationConditionedTargetReadModel, ...]:
    service = ObservationConditionsService()
    builder = ObservationConditionsReadModelBuilder()
    solar = (
        _target("jupiter", "Jupiter", "Pianeta", 90, magnitude="-2.1"),
        _target("moon", "Moon", "Moon", 82, magnitude="-12.0"),
    )
    deep_sky = (
        _target("galaxy", "Galaxy", "Galaxy", 88, magnitude="8.8"),
        _target("diffuse_nebula", "Diffuse Nebula", "Diffuse Nebula", 86, magnitude="7.0"),
        _target("open_cluster", "Open Cluster", "Open Cluster", 78, magnitude="5.2"),
        _target("globular_cluster", "Globular Cluster", "Globular Cluster", 82, magnitude="6.8"),
    )
    raw_by_id = {item.id: item for item in (*solar, *deep_sky)}
    conditioned_deep_sky = service.condition_deep_sky_pollution_context(
        list(deep_sky),
        sky_quality,
        ObservationConditionInputs(moon=moon, sky_quality=sky_quality),
    )
    return (
        *builder.from_display_targets(
            solar,
            source="consumer_reroute_fixture_solar",
            raw_targets_by_id=raw_by_id,
        ),
        *builder.from_conditioned_targets(
            conditioned_deep_sky,
            source="consumer_reroute_fixture_deep_sky",
            raw_targets_by_id=raw_by_id,
        ),
    )


def _evaluations(
    read_models: tuple[ObservationConditionedTargetReadModel, ...],
    *,
    sky_quality: SkyQuality,
    moon: MoonSummary,
) -> tuple[dict[str, object], ...]:
    rows = []
    for model in read_models:
        raw_observable = build_home_observable_target_value(
            model.nsom_target_input,
            sky_quality=sky_quality,
            moon=moon,
        )
        display_observable = build_home_observable_target_value(
            model.qml_display_target,
            sky_quality=sky_quality,
            moon=moon,
        )
        rows.append(
            {
                "object_id": model.object_id,
                "name": model.name,
                "target_group": "solar_system" if model.object_id in {"jupiter", "moon"} else "deep_sky",
                "source": model.source,
                "raw_score": model.raw_score,
                "display_score": model.display_score,
                "condition_flags": model.condition_flags,
                "applied_components": model.applied_components,
                "raw_observable_value": round(raw_observable.value, 6),
                "display_observable_value": round(display_observable.value, 6),
                "raw_minus_display_observable": round(
                    raw_observable.value - display_observable.value,
                    6,
                ),
                "raw_target_id": model.nsom_target_input.id,
                "display_target_id": model.qml_display_target.id,
                "raw_target_is_display_target": model.nsom_target_input is model.qml_display_target,
            }
        )
    return tuple(rows)


def _consumer_policies(deep_sky_evaluations: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    display_order = _order(deep_sky_evaluations, "display_observable_value")
    raw_order = _order(deep_sky_evaluations, "raw_observable_value")
    score_delta_present = any(float(item["raw_minus_display_observable"]) > 0.0 for item in deep_sky_evaluations)
    return (
        {
            "consumer": "Home recommendedDeepSky",
            "current_runtime_input": "read_model.nsom_target_input",
            "candidate_raw_input": "read_model.nsom_target_input",
            "payload_target": "read_model.qml_display_target",
            "status": "runtime_rerouted_to_raw_read_model_target",
            "behaviour_change_expected": display_order != raw_order or score_delta_present,
            "policy": (
                "Rank by raw ObservableTargetValue, preserve conditioned display "
                "target for QML payload shape and score compatibility."
            ),
        },
        {
            "consumer": "Best Object",
            "current_runtime_input": "read_model.nsom_target_input for scoring",
            "candidate_raw_input": "read_model.nsom_target_input for scoring",
            "payload_target": "read_model.qml_display_target when selected",
            "status": "runtime_rerouted_to_raw_read_model_target",
            "behaviour_change_expected": True,
            "policy": (
                "Score raw target physics, but return the display target for "
                "existing Home payload compatibility."
            ),
        },
        {
            "consumer": "Sky Compass",
            "current_runtime_input": "conditioned display target for direction scoring",
            "candidate_raw_input": "read_model.nsom_target_input for observable contribution",
            "payload_target": "read_model.qml_display_target",
            "status": "requires_direction_delta_review_before_reroute",
            "behaviour_change_expected": True,
            "policy": (
                "Use raw observable contribution for direction ranking while "
                "keeping display target score/name/type fields unchanged."
            ),
        },
    )


def _checks(
    evaluations: tuple[dict[str, object], ...],
    consumer_policies: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    deep_sky = tuple(item for item in evaluations if item["target_group"] == "deep_sky")
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "evaluations": evaluations,
                "consumer_policies": consumer_policies,
            }
        ),
        "raw_observable_differs_from_display_for_conditioned_targets": all(
            float(item["raw_minus_display_observable"]) > 0.0 for item in deep_sky
        ),
        "solar_system_targets_are_not_conditioned": all(
            item["raw_target_is_display_target"] is True
            and float(item["raw_minus_display_observable"]) == 0.0
            for item in evaluations
            if item["target_group"] == "solar_system"
        ),
        "home_policy_preserves_qml_display_target": _policy_field(
            consumer_policies,
            "Home recommendedDeepSky",
            "payload_target",
        )
        == "read_model.qml_display_target",
        "home_runtime_reroute_uses_raw_read_model_targets": static_checks[
            "home_runtime_reroute_uses_raw_read_model_targets"
        ]
        is True,
        "home_runtime_payload_uses_display_target": static_checks["home_runtime_payload_uses_display_target"]
        is True,
        "best_object_policy_preserves_display_return": _policy_field(
            consumer_policies,
            "Best Object",
            "payload_target",
        )
        == "read_model.qml_display_target when selected",
        "best_object_runtime_reroute_uses_raw_read_model_targets": static_checks[
            "best_object_runtime_reroute_uses_raw_read_model_targets"
        ]
        is True,
        "best_object_runtime_returns_display_target": static_checks[
            "best_object_runtime_returns_display_target"
        ]
        is True,
        "sky_compass_policy_keeps_display_payload": _policy_field(
            consumer_policies,
            "Sky Compass",
            "payload_target",
        )
        == "read_model.qml_display_target",
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "strict_json_compatible": "observation-conditions-reroute-audit-json-incompatible",
        "raw_observable_differs_from_display_for_conditioned_targets": (
            "observation-conditions-reroute-fixture-does-not-show-input-delta"
        ),
        "solar_system_targets_are_not_conditioned": "observation-conditions-reroute-solar-system-conditioned",
        "home_policy_preserves_qml_display_target": "observation-conditions-reroute-home-payload-policy-missing",
        "home_runtime_reroute_uses_raw_read_model_targets": (
            "observation-conditions-reroute-home-runtime-raw-input-missing"
        ),
        "home_runtime_payload_uses_display_target": (
            "observation-conditions-reroute-home-runtime-display-payload-missing"
        ),
        "best_object_policy_preserves_display_return": (
            "observation-conditions-reroute-best-object-display-policy-missing"
        ),
        "best_object_runtime_reroute_uses_raw_read_model_targets": (
            "observation-conditions-reroute-best-object-runtime-raw-input-missing"
        ),
        "best_object_runtime_returns_display_target": (
            "observation-conditions-reroute-best-object-display-return-missing"
        ),
        "sky_compass_policy_keeps_display_payload": "observation-conditions-reroute-sky-compass-payload-policy-missing",
        "runtime_report_imports_absent": "observation-conditions-reroute-audit-runtime-wiring",
        "qml_report_exposure_absent": "observation-conditions-reroute-audit-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "observation-conditions-reroute-audit-runtime-change",
    }
    return tuple(name for key, name in names.items() if checks[key] is not True)


def _policy_field(
    policies: tuple[dict[str, object], ...],
    consumer: str,
    field: str,
) -> object:
    return next(item[field] for item in policies if item["consumer"] == consumer)


def _order(items: tuple[dict[str, object], ...], score_key: str) -> tuple[str, ...]:
    return tuple(
        str(item["object_id"])
        for item in sorted(
            items,
            key=lambda item: (-float(item[score_key]), str(item["object_id"])),
        )
    )


def _static_wiring_checks(root: Path) -> dict[str, object]:
    controller_source = (root / "astro_viewer" / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    return {
        "home_runtime_reroute_uses_raw_read_model_targets": (
            "model.nsom_target_input for model in candidate_read_models" in controller_source
        ),
        "home_runtime_payload_uses_display_target": (
            "model.qml_display_target for model in conditioned_deep_sky_read_model" in controller_source
            and "source=\"home_recommended_deep_sky_nsom_raw_observable_order\"" in controller_source
        ),
        "best_object_runtime_reroute_uses_raw_read_model_targets": (
            "def _best_object_read_models" in controller_source
            and "model.nsom_target_input for model in candidate_read_models" in controller_source
        ),
        "best_object_runtime_returns_display_target": (
            "display_targets_by_raw_id" in controller_source
            and "model.qml_display_target" in controller_source
            and "return display_targets_by_raw_id.get(selected_raw_target.id, selected_raw_target)"
            in controller_source
        ),
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
        max_altitude="60 deg",
        direction="Sud",
        best_time="22:00",
        observing_window="21:30 - 23:30",
        notes="fixture",
        recommended_setup="fixture",
        visibility_class="Buona",
        azimuth="180 deg",
        time_above_horizon="4 h",
        score=score,
        score_label="Buono",
        difficulty="Facile",
        visible=True,
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        9,
        4.5,
        18.4,
        "Fixture VIIRS",
        "Fixture bright sky",
        "high",
        viirs_radiance=120.0,
    )


def _moon(illumination: str) -> MoonSummary:
    return MoonSummary(
        phase="fixture",
        illumination=illumination,
        rise_time="20:00",
        set_time="06:00",
        best_note="fixture",
        image="",
    )


if __name__ == "__main__":
    write_markdown_report()
