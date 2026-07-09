from __future__ import annotations

import inspect
import json
from dataclasses import replace
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.observation_conditions_read_model import ObservationConditionsReadModelBuilder
from astro_viewer.app.services.sky_compass_nsom_ranking import SkyCompassNsomDirectionService
from astro_viewer.app.viewmodels.app_controller import AppController


REPORT_PATH = Path("docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md")

REPORT_IMPORT_MARKERS = (
    "sky_compass_read_model_reroute_policy",
    "SKY_COMPASS_READ_MODEL_REROUTE_POLICY",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_sky_compass_read_model_reroute_policy_data() -> dict[str, object]:
    """Developer-only policy for the final ObservationConditions consumer reroute."""

    root = Path(__file__).parents[2]
    sky_quality = _sky_quality()
    moon = _moon()
    fixture = _fixture_evidence(sky_quality=sky_quality, moon=moon)
    static_checks = _static_checks(root)
    decisions = _policy_decisions()
    checks = _checks(fixture, decisions, static_checks)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_policy": False,
            "sky_compass_runtime_changed": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "sky_compass_read_model_policy_defined_runtime_pending",
            "runtime_reroute_ready_for_next_step": True,
            "runtime_changed_by_this_step": False,
            "recommended_next_step": (
                "Review this policy, then implement a Sky Compass read-model "
                "adapter that uses raw target physics for ObservableTargetValue "
                "and display/live targets for geometry and payload compatibility."
            ),
            "reason": (
                "Sky Compass is a direction/presentation surface. Replacing the "
                "candidate with the raw target would avoid display-score reuse, "
                "but it could also drop display/live direction, visibility and "
                "current-position data. The safe policy is a split adapter."
            ),
        },
        "policy_decisions": decisions,
        "fixture": fixture,
        "checks": checks,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.12.9",
                "summary": "Confirm Best Object raw-target scoring and display target return.",
            },
            {
                "step": "1.12.10 Sky Compass read-model reroute policy",
                "summary": "Define raw target physics vs display/live geometry ownership before runtime changes.",
            },
            {
                "step": "1.12.11 Sky Compass read-model reroute",
                "summary": "Implement the policy if review accepts the split adapter.",
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    policy = generate_sky_compass_read_model_reroute_policy_data() if data is None else data
    readiness = policy["readiness"]
    fixture = policy["fixture"]

    lines = [
        "# Sky Compass Read-Model Reroute Policy",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only policy defines how Sky Compass should consume the "
            "ObservationConditions read model in a later runtime step. It does not "
            "change Sky Compass runtime behaviour, QML, logging, network access or "
            "runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Runtime reroute ready for next step: `{readiness['runtime_reroute_ready_for_next_step']}`.",
        f"- Runtime changed by this step: `{readiness['runtime_changed_by_this_step']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Policy Decisions",
        "",
        "| Boundary | Source | Runtime role | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for decision in policy["policy_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    decision["boundary"],
                    decision["source"],
                    decision["runtime_role"],
                    decision["reason"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Fixture Evidence",
            "",
            f"- Raw observable value: `{fixture['raw_observable_value']}`.",
            f"- Display observable value: `{fixture['display_observable_value']}`.",
            f"- Raw minus display observable: `{fixture['raw_minus_display_observable']}`.",
            f"- Raw direction: `{fixture['raw_target']['direction']}`.",
            f"- Display direction: `{fixture['display_target']['direction']}`.",
            f"- Live direction: `{fixture['live_display_target']['direction']}`.",
            f"- Policy observable source: `{fixture['policy_projection']['observable_source']}`.",
            f"- Policy geometry source: `{fixture['policy_projection']['geometry_source']}`.",
            f"- Policy payload source: `{fixture['policy_projection']['payload_source']}`.",
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in policy["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Static Wiring",
            "",
            f"- Runtime report imports: `{policy['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- QML report exposure: `{policy['static_wiring_checks']['qml_report_exposure_matches']}`.",
            f"- Current runtime uses conditioned/display candidates: `{policy['static_wiring_checks']['sky_compass_uses_conditioned_display_candidates_now']}`.",
            f"- Live refresh updates current candidate geometry: `{policy['static_wiring_checks']['live_refresh_updates_current_candidate_geometry']}`.",
            f"- Current NSOM service computes observable from candidate object: `{policy['static_wiring_checks']['nsom_service_uses_candidate_object_for_observable_now']}`.",
            "",
            "## Recommended Sequence",
            "",
        ]
    )
    for item in policy["recommended_sequence"]:
        lines.append(f"- `{item['step']}`: {item['summary']}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "Sky Compass should not be rerouted by passing only raw targets to "
                "the existing service. The next runtime step should introduce a "
                "small adapter that joins raw NSOM target input with display/live "
                "geometry and payload data by target id."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_decisions() -> tuple[dict[str, object], ...]:
    return (
        {
            "boundary": "ObservableTargetValue target physics",
            "source": "read_model.nsom_target_input",
            "runtime_role": "NSOM score contribution",
            "reason": "Avoid reusing condition-adjusted display score as intrinsic target value.",
        },
        {
            "boundary": "Direction grouping",
            "source": "current display/live target",
            "runtime_role": "Sky Compass direction and zone grouping",
            "reason": "Direction can change during live refresh and belongs to current geometry, not raw catalogue value.",
        },
        {
            "boundary": "Visibility and horizon geometry",
            "source": "current display/live target",
            "runtime_role": "Candidate eligibility and horizon context",
            "reason": "Live position refresh can update visible state and altitude without recomputing raw target data.",
        },
        {
            "boundary": "QML payload",
            "source": "read_model.qml_display_target or current live display target",
            "runtime_role": "Existing target card fields",
            "reason": "Payload keys, display score and labels must remain compatible.",
        },
        {
            "boundary": "Night Plan and Best Object boosts",
            "source": "target id context",
            "runtime_role": "Presentation/context boost",
            "reason": "Plan and Best Object membership are not target physics and should stay outside ObservableTargetValue.",
        },
        {
            "boundary": "Missing read-model fallback",
            "source": "current display/live target",
            "runtime_role": "Compatibility fallback",
            "reason": "Plan-only or live-refreshed candidates may lack a read-model row and must remain renderable.",
        },
    )


def _fixture_evidence(
    *,
    sky_quality: SkyQuality,
    moon: MoonSummary,
) -> dict[str, object]:
    raw = _target(
        "galaxy",
        "Galaxy",
        "Galaxy",
        score=88,
        direction="Sud",
        max_altitude="45 gradi",
    )
    display = replace(
        raw,
        score=32,
        condition_flags=("light_pollution",),
        direction="Sud",
        max_altitude="42 gradi",
    )
    live_display = replace(
        display,
        direction="Sud-Ovest",
        max_altitude="37 gradi",
        azimuth="220 gradi",
    )
    read_model = ObservationConditionsReadModelBuilder().from_display_targets(
        [display],
        source="sky_compass_read_model_policy_fixture",
        raw_targets_by_id={raw.id: raw},
    )[0]
    raw_observable = build_home_observable_target_value(read_model.nsom_target_input, sky_quality=sky_quality, moon=moon)
    display_observable = build_home_observable_target_value(read_model.qml_display_target, sky_quality=sky_quality, moon=moon)
    return {
        "raw_target": _target_summary(raw),
        "display_target": _target_summary(display),
        "live_display_target": _target_summary(live_display),
        "read_model": read_model.to_dict(),
        "raw_observable_value": round(raw_observable.value, 6),
        "display_observable_value": round(display_observable.value, 6),
        "raw_minus_display_observable": round(raw_observable.value - display_observable.value, 6),
        "policy_projection": {
            "observable_source": "read_model.nsom_target_input",
            "geometry_source": "current_display_or_live_target",
            "payload_source": "read_model.qml_display_target_or_live_display_target",
            "join_key": "target.id",
            "runtime_changed_by_policy": False,
        },
    }


def _checks(
    fixture: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    boundaries = {str(item["boundary"]): item for item in decisions}
    return {
        "strict_json_compatible": _strict_json_compatible({"fixture": fixture, "decisions": decisions}),
        "raw_observable_differs_from_display": float(fixture["raw_minus_display_observable"]) > 0.0,
        "observable_target_physics_uses_raw": (
            boundaries["ObservableTargetValue target physics"]["source"] == "read_model.nsom_target_input"
        ),
        "direction_grouping_uses_live_display_geometry": (
            boundaries["Direction grouping"]["source"] == "current display/live target"
        ),
        "visibility_horizon_uses_live_display_geometry": (
            boundaries["Visibility and horizon geometry"]["source"] == "current display/live target"
        ),
        "payload_uses_display_target": (
            boundaries["QML payload"]["source"] == "read_model.qml_display_target or current live display target"
        ),
        "context_boosts_remain_presentation": (
            boundaries["Night Plan and Best Object boosts"]["runtime_role"] == "Presentation/context boost"
        ),
        "missing_read_model_fallback_defined": "Missing read-model fallback" in boundaries,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_policy": True,
    }


def _static_checks(root: Path) -> dict[str, object]:
    controller_source = inspect.getsource(AppController)
    sky_compass_candidates = inspect.getsource(AppController._sky_compass_candidates)
    live_refresh = inspect.getsource(AppController._refresh_sky_compass_live)
    nsom_service_source = inspect.getsource(SkyCompassNsomDirectionService)
    return {
        "sky_compass_uses_conditioned_display_candidates_now": "_conditioned_deep_sky_candidates()" in sky_compass_candidates,
        "live_refresh_updates_current_candidate_geometry": (
            "refresh_current_positions" in live_refresh and "_sky_compass_candidate_snapshot" in live_refresh
        ),
        "nsom_service_uses_candidate_object_for_observable_now": (
            "build_home_observable_target_value(item" in nsom_service_source
        ),
        "controller_has_no_sky_compass_read_model_adapter_yet": "def _sky_compass_read_models" not in controller_source,
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
            text = path.read_text(encoding="utf-8")
            found = tuple(marker for marker in markers if marker in text)
            if found:
                matches.append(
                    {
                        "path": str(path.relative_to(root.parents[1])).replace("\\", "/"),
                        "markers": found,
                    }
                )
    return tuple(matches)


def _strict_json_compatible(value: object) -> bool:
    json.dumps(nsom_to_json_compatible(value), sort_keys=True, allow_nan=False)
    return True


def _target_summary(item: CelestialObject) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "object_type": item.object_type,
        "score": item.score,
        "direction": item.direction,
        "max_altitude": item.max_altitude,
        "azimuth": item.azimuth,
        "visible": item.visible,
        "condition_flags": item.condition_flags,
    }


def _target(
    object_id: str,
    name: str,
    object_type: str,
    *,
    score: int,
    direction: str,
    max_altitude: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude=max_altitude,
        direction=direction,
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty="Media",
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=9,
        limiting_magnitude=4.2,
        sky_brightness=18.0,
        source="Fixture",
        description="Fixture",
        viirs_radiance=120.0,
    )


def _moon() -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination="80%",
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )
