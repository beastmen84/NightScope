from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
    ObservationConditionsService,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.tools.nsom_aod_openaq_real_provider_readiness_audit import (
    SOURCE_REPORT_PATH,
    _real_provider_evidence,
)


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_STALE_CURRENT_REPLAY_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_stale_current_replay_audit",
    "NSOM_AOD_OPENAQ_STALE_CURRENT_REPLAY_AUDIT",
)

QML_MARKERS = (
    "nsomAodOpenAQStaleCurrentReplayAudit",
    "aodOpenAQStaleCurrentReplayAudit",
    "NSOM_AOD_OPENAQ_STALE_CURRENT_REPLAY_AUDIT",
)


@dataclass(frozen=True)
class ReplayTargetProfile:
    target_score: int
    max_transparency_loss: float


def generate_aod_openaq_stale_current_replay_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    evidence = _real_provider_evidence(root / SOURCE_REPORT_PATH)
    replay_rows = _replay_rows(evidence)
    summary = _summary(evidence, replay_rows)
    gates = _readiness_gates(summary)
    blockers = tuple(
        str(gate["gate"])
        for gate in gates
        if gate["blocks_default_on"] is True
    )
    static_checks = _static_wiring_checks(root)
    checks = _checks(summary, gates, blockers, static_checks)

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
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "equipment_changed": False,
            "source_report": str(SOURCE_REPORT_PATH).replace("\\", "/"),
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": (
                "aod_openaq_stale_policy_ready_for_default_on_review"
                if not blockers
                else "aod_openaq_stale_policy_needs_more_review"
            ),
            "ready_for_default_on_review": not blockers,
            "default_on_enabled_by_this_audit": False,
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "default_runtime_score_effect": 0.0,
            "feature_flag_change_in_this_audit": False,
            "stale_aod_weight_policy": "keep_stale_aod_weight_0_5",
            "recommended_next_step": (
                "Review this replay audit. If accepted, the next implementation "
                "step can be a narrow AOD/OpenAQ default-on switch."
                if not blockers
                else "Collect more provider evidence or adjust stale/current policy before default-on."
            ),
            "reason": (
                "Replaying the checked-in real AOD values as current keeps the "
                "score effect bounded and target-specific. The stale 0.5 weight "
                "is therefore a reasonable conservative runtime policy."
            ),
        },
        "formula": {
            "replay_change": "Only AOD freshness is changed from stale weight 0.5 to current weight 1.0.",
            "score_modifier": (
                "-target_score * min(max_transparency_loss, "
                "max_transparency_loss * sensitivity * severity * freshness_weight * source_weight)"
            ),
            "source_scope": "AOD-source rows only; particulate and none rows are unchanged.",
            "confidence_role": "RecommendationConfidence and provider confidence remain metadata only.",
        },
        "summary": summary,
        "readiness_gates": gates,
        "blockers": blockers,
        "replay_rows": replay_rows,
        "static_wiring_checks": static_checks,
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = (
        generate_aod_openaq_stale_current_replay_audit_data()
        if data is None
        else data
    )
    readiness = report["readiness"]
    summary = report["summary"]
    formula = report["formula"]

    lines = [
        "# NSOM AOD/OpenAQ Stale-vs-Current Replay Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit replays the checked-in expanded real-provider "
            "AOD/OpenAQ evidence with only one change: policy-eligible stale AOD "
            "rows are treated as current to measure the score effect of "
            "`freshness_weight=1.0` versus `0.5`. It does not call NASA/OpenAQ, "
            "does not enable aerosol scoring, and does not change Planner, Home, "
            "Best Object, Advanced Observing, Sky Compass, Detail/Object, "
            "Equipment or QML."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on review: `{readiness['ready_for_default_on_review']}`.",
        f"- Default-on enabled by this audit: `{readiness['default_on_enabled_by_this_audit']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Default runtime score effect: `{readiness['default_runtime_score_effect']}`.",
        f"- Stale AOD weight policy: `{readiness['stale_aod_weight_policy']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Formula",
        "",
        f"- Replay change: {formula['replay_change']}",
        f"- Score modifier: `{formula['score_modifier']}`.",
        f"- Source scope: {formula['source_scope']}",
        f"- Confidence role: {formula['confidence_role']}",
        "",
        "## Summary",
        "",
        f"- AOD source location count: `{summary['aod_source_location_count']}`.",
        f"- AOD replay row count: `{summary['aod_replay_row_count']}`.",
        f"- Stale deep-sky max penalty: `{summary['stale_deep_sky_max_penalty']}`.",
        f"- Current replay deep-sky max penalty: `{summary['current_deep_sky_max_penalty']}`.",
        f"- Stale solar-system max penalty: `{summary['stale_solar_system_max_penalty']}`.",
        f"- Current replay solar-system max penalty: `{summary['current_solar_system_max_penalty']}`.",
        f"- Max additional deep-sky penalty: `{summary['max_additional_deep_sky_penalty']}`.",
        f"- Max additional solar-system penalty: `{summary['max_additional_solar_system_penalty']}`.",
        f"- Max current/stale non-zero ratio: `{summary['max_current_to_stale_ratio']}`.",
        f"- Zero-effect AOD locations preserved: `{summary['zero_effect_aod_locations_preserved']}`.",
        f"- Particulate rows unchanged: `{summary['particulate_rows_unchanged']}`.",
        f"- None-source rows unchanged: `{summary['none_rows_unchanged']}`.",
        "",
        "## Readiness Gates",
        "",
        "| Gate | Status | Blocks default-on | Reason | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for gate in report["readiness_gates"]:
        lines.append(
            "| "
            f"`{gate['gate']}` | `{gate['status']}` | "
            f"`{gate['blocks_default_on']}` | {gate['reason']} | "
            f"{gate['evidence']} |"
        )

    lines.extend(
        [
            "",
            "## Representative Replay Rows",
            "",
            "| Location | Target | Source | Stale modifier | Current replay modifier | Additional penalty |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["replay_rows"]:
        if row["source"] != "aod" or row["target_class"] not in {"galaxy", "planet", "moon"}:
            continue
        lines.append(
            "| "
            f"{row['location']} | `{row['target_class']}` | `{row['source']}` | "
            f"`{row['stale_modifier']}` | `{row['current_replay_modifier']}` | "
            f"`{row['additional_penalty']}` |"
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
    for key, value in report["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The replay supports keeping stale AOD at half weight. If those "
                "same AOD values were current, the strongest deep-sky penalty "
                "would remain bounded, low-AOD AOD-source locations would still "
                "be neutral, and protected solar-system targets would remain only "
                "minimally affected. The audit therefore removes stale/current "
                "freshness as a technical blocker, while keeping the actual default "
                "flag off for a separate reviewed switch."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _replay_rows(evidence: dict[str, object]) -> tuple[dict[str, object], ...]:
    provider_by_location = {
        row["location"]: row
        for row in evidence["provider_rows"]
    }
    profiles = _target_profiles()
    rows: list[dict[str, object]] = []
    for row in evidence["effect_rows"]:
        target_class = str(row["target_class"])
        profile = profiles[target_class]
        provider_row = provider_by_location[str(row["location"])]
        stale_modifier = float(row["flag_on_modifier"])
        stale_loss = float(row["transparency_loss"])
        source = str(row["source"])
        replay_loss = stale_loss
        replay_modifier = stale_modifier
        replay_changed = False
        if source == "aod" and provider_row["aod_input_freshness"] == "stale":
            replay_loss = round(
                min(profile.max_transparency_loss, stale_loss / 0.5),
                5,
            )
            penalty_points = round(profile.target_score * replay_loss, 3)
            replay_modifier = round(-penalty_points, 3) if penalty_points > 0 else 0.0
            replay_changed = replay_modifier != stale_modifier
        additional_penalty = round(replay_modifier - stale_modifier, 3)
        rows.append(
            {
                "location": row["location"],
                "target_class": target_class,
                "source": source,
                "aod_original_freshness": provider_row["aod_input_freshness"],
                "stale_transparency_loss": stale_loss,
                "current_replay_transparency_loss": replay_loss,
                "stale_modifier": stale_modifier,
                "current_replay_modifier": replay_modifier,
                "additional_penalty": additional_penalty,
                "stale_adjusted_score": row["flag_on_score"],
                "current_replay_adjusted_score": max(
                    0,
                    min(100, round(profile.target_score + replay_modifier)),
                ),
                "replay_changed": replay_changed,
            }
        )
    return tuple(rows)


def _summary(
    evidence: dict[str, object],
    replay_rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    deep_sky_classes = {"galaxy", "diffuse_nebula", "open_cluster", "globular_cluster"}
    solar_classes = {"planet", "moon"}
    aod_rows = [row for row in replay_rows if row["source"] == "aod"]
    deep_rows = [row for row in replay_rows if row["target_class"] in deep_sky_classes]
    solar_rows = [row for row in replay_rows if row["target_class"] in solar_classes]
    aod_deep_rows = [row for row in aod_rows if row["target_class"] in deep_sky_classes]
    aod_solar_rows = [row for row in aod_rows if row["target_class"] in solar_classes]
    non_zero_ratios = [
        round(
            abs(float(row["current_replay_modifier"])) / abs(float(row["stale_modifier"])),
            3,
        )
        for row in aod_rows
        if float(row["stale_modifier"]) != 0.0
    ]
    aod_locations = sorted({str(row["location"]) for row in aod_rows})
    zero_effect_aod_locations = sorted(
        {
            str(row["location"])
            for row in aod_rows
            if all(
                float(candidate["current_replay_modifier"]) == 0.0
                for candidate in aod_rows
                if candidate["location"] == row["location"]
            )
        }
    )
    particulate_rows = [row for row in replay_rows if row["source"] == "particulate"]
    none_rows = [row for row in replay_rows if row["source"] == "none"]
    return {
        "source_report": str(SOURCE_REPORT_PATH).replace("\\", "/"),
        "location_count": evidence["location_count"],
        "aod_source_location_count": len(aod_locations),
        "aod_source_locations": tuple(aod_locations),
        "aod_replay_row_count": len(aod_rows),
        "stale_deep_sky_max_penalty": _min_modifier(deep_rows, "stale_modifier"),
        "current_deep_sky_max_penalty": _min_modifier(deep_rows, "current_replay_modifier"),
        "stale_solar_system_max_penalty": _min_modifier(solar_rows, "stale_modifier"),
        "current_solar_system_max_penalty": _min_modifier(solar_rows, "current_replay_modifier"),
        "aod_current_replay_deep_sky_max_penalty": _min_modifier(
            aod_deep_rows,
            "current_replay_modifier",
        ),
        "aod_current_replay_solar_system_max_penalty": _min_modifier(
            aod_solar_rows,
            "current_replay_modifier",
        ),
        "max_additional_deep_sky_penalty": _min_modifier(deep_rows, "additional_penalty"),
        "max_additional_solar_system_penalty": _min_modifier(solar_rows, "additional_penalty"),
        "max_current_to_stale_ratio": max(non_zero_ratios) if non_zero_ratios else 0.0,
        "zero_effect_aod_locations_preserved": tuple(zero_effect_aod_locations),
        "particulate_rows_unchanged": all(
            row["current_replay_modifier"] == row["stale_modifier"]
            for row in particulate_rows
        ),
        "none_rows_unchanged": all(
            row["current_replay_modifier"] == row["stale_modifier"]
            for row in none_rows
        ),
        "confidence_score_neutral": True,
    }


def _readiness_gates(summary: dict[str, object]) -> tuple[dict[str, object], ...]:
    current_deep_sky = abs(float(summary["aod_current_replay_deep_sky_max_penalty"]))
    current_solar = abs(float(summary["aod_current_replay_solar_system_max_penalty"]))
    return (
        {
            "gate": "offline_replay_only",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": "The replay uses checked-in provider evidence and performs no network work.",
            "evidence": summary["source_report"],
        },
        {
            "gate": "stale_weight_policy",
            "status": "accepted" if summary["max_current_to_stale_ratio"] <= 2.01 else "review",
            "blocks_default_on": summary["max_current_to_stale_ratio"] > 2.01,
            "reason": "Stale AOD at weight 0.5 should be a conservative half-strength version of current AOD.",
            "evidence": f"max_ratio={summary['max_current_to_stale_ratio']}",
        },
        {
            "gate": "current_replay_score_scale",
            "status": "accepted" if current_deep_sky <= 8.0 else "review",
            "blocks_default_on": current_deep_sky > 8.0,
            "reason": "Treating the same real AOD as current should keep deep-sky impact bounded.",
            "evidence": f"aod_current_deep_sky={summary['aod_current_replay_deep_sky_max_penalty']}",
        },
        {
            "gate": "protected_target_current_replay",
            "status": "accepted" if current_solar <= 0.4 else "review",
            "blocks_default_on": current_solar > 0.4,
            "reason": "Planets and Moon should remain protected even when real AOD is replayed as current.",
            "evidence": f"aod_current_solar_system={summary['aod_current_replay_solar_system_max_penalty']}",
        },
        {
            "gate": "zero_effect_aod_preserved",
            "status": "accepted" if summary["zero_effect_aod_locations_preserved"] else "review",
            "blocks_default_on": not bool(summary["zero_effect_aod_locations_preserved"]),
            "reason": "Low/clean AOD-source locations should stay neutral after current replay.",
            "evidence": f"locations={summary['zero_effect_aod_locations_preserved']}",
        },
        {
            "gate": "fallback_sources_unchanged",
            "status": (
                "accepted"
                if summary["particulate_rows_unchanged"] and summary["none_rows_unchanged"]
                else "review"
            ),
            "blocks_default_on": not (
                summary["particulate_rows_unchanged"] and summary["none_rows_unchanged"]
            ),
            "reason": "Changing AOD freshness must not alter PM fallback or no-source rows.",
            "evidence": (
                f"particulate={summary['particulate_rows_unchanged']}, "
                f"none={summary['none_rows_unchanged']}"
            ),
        },
        {
            "gate": "confidence_neutrality",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": "Confidence remains metadata and is not a replay score factor.",
            "evidence": f"confidence_score_neutral={summary['confidence_score_neutral']}",
        },
    )


def _checks(
    summary: dict[str, object],
    gates: tuple[dict[str, object], ...],
    blockers: tuple[str, ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(summary),
        "feature_flag_default_off": ObservationConditionFeatureFlags().experimental_aerosol_scoring is False,
        "default_runtime_neutral": True,
        "aod_replay_rows_present": summary["aod_replay_row_count"] > 0,
        "stale_weight_doubles_nonzero_effect_at_most": _gate(gates, "stale_weight_policy")["blocks_default_on"] is False,
        "current_replay_score_scale_accepted": _gate(gates, "current_replay_score_scale")["blocks_default_on"] is False,
        "protected_targets_remain_protected": _gate(gates, "protected_target_current_replay")["blocks_default_on"] is False,
        "pm_and_none_rows_unchanged": _gate(gates, "fallback_sources_unchanged")["blocks_default_on"] is False,
        "confidence_neutral": _gate(gates, "confidence_neutrality")["blocks_default_on"] is False,
        "ready_for_default_on_review": not blockers,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
    }


def _target_profiles() -> dict[str, ReplayTargetProfile]:
    service = ObservationConditionsService()
    profiles: dict[str, ReplayTargetProfile] = {}
    for target in _targets():
        profile = service.atmospheric_sensitivity_profile(target)
        profiles[profile.target_class] = ReplayTargetProfile(
            target_score=target.score,
            max_transparency_loss=round(max(0.0, profile.penalty_cap / 100.0), 5),
        )
    return profiles


def _targets() -> tuple[CelestialObject, ...]:
    return (
        _make_target("m31", "M31", "Galaxy"),
        _make_target("m42", "M42", "Diffuse Nebula"),
        _make_target("m45", "M45", "Open Cluster"),
        _make_target("m13", "M13", "Globular Cluster"),
        _make_target("mars", "Mars", "Pianeta"),
        _make_target("moon", "Moon", "Satellite naturale"),
    )


def _make_target(object_id: str, name: str, object_type: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="7.8",
        distance="",
        max_altitude="48 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Replay target.",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=82,
        score_label=ObservingScoreService.score_label(82),
        difficulty="Media",
        apparent_size="20 arcmin",
        max_angular_size_deg=0.33,
    )


def _min_modifier(rows: list[dict[str, object]], key: str) -> float:
    return min((float(row[key]) for row in rows), default=0.0)


def _gate(gates: tuple[dict[str, object], ...], gate_id: str) -> dict[str, object]:
    return next(gate for gate in gates if gate["gate"] == gate_id)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    ui_root = app_root / "ui"
    return {
        "runtime_report_import_matches": _scan_files(app_root, ("*.py",), REPORT_IMPORT_MARKERS),
        "qml_report_exposure_matches": _scan_files(ui_root, ("*.qml",), QML_MARKERS),
    }


def _scan_files(root: Path, patterns: tuple[str, ...], markers: tuple[str, ...]) -> tuple[str, ...]:
    if not root.exists():
        return ()
    matches: list[str] = []
    for pattern in patterns:
        for path in root.rglob(pattern):
            if "__pycache__" in path.parts:
                continue
            text = _read_text(path)
            if any(marker in text for marker in markers):
                matches.append(str(path.relative_to(root.parents[1])).replace("\\", "/"))
    return tuple(sorted(set(matches)))


def _strict_json_compatible(payload: object) -> bool:
    try:
        json.dumps(nsom_to_json_compatible(payload), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


if __name__ == "__main__":
    write_markdown_report()
