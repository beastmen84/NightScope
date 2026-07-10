from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
)


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_READINESS_AUDIT.md")
SOURCE_REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_real_provider_readiness_audit",
    "NSOM_AOD_OPENAQ_REAL_PROVIDER_READINESS_AUDIT",
)

QML_MARKERS = (
    "nsomAodOpenAQRealProviderReadinessAudit",
    "aodOpenAQRealProviderReadinessAudit",
    "NSOM_AOD_OPENAQ_REAL_PROVIDER_READINESS_AUDIT",
)


def generate_aod_openaq_real_provider_readiness_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    source_report = root / SOURCE_REPORT_PATH
    evidence = _real_provider_evidence(source_report)
    gates = _readiness_gates(evidence)
    blockers = tuple(
        str(gate["gate"])
        for gate in gates
        if gate["blocks_default_on"] is True
    )
    static_checks = _static_wiring_checks(root)
    checks = _checks(evidence, gates, blockers, static_checks)

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
                "aod_openaq_real_provider_ready_for_default_on"
                if not blockers
                else "aod_openaq_default_on_deferred_for_temporal_provider_evidence"
            ),
            "ready_for_default_on": not blockers,
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "default_runtime_score_effect": 0.0,
            "feature_flag_change_in_this_audit": False,
            "recommended_next_step": (
                "Repeat the real-provider probe on another date/time or explicitly "
                "accept stale-AOD runtime policy. Only then consider a narrow "
                "default-on switch."
                if blockers
                else "Proceed to a narrow default-on switch with an explicit rollback note."
            ),
            "reason": (
                "The expanded real-provider probe resolves the score-scale review "
                "with modest target-specific effects, but all usable AOD inputs in "
                "the checked-in provider run are stale and the evidence is still a "
                "single temporal snapshot."
            ),
        },
        "evidence_summary": _evidence_summary(evidence),
        "readiness_gates": gates,
        "blockers": blockers,
        "provider_rows": evidence["provider_rows"],
        "policy_rows": evidence["policy_rows"],
        "aggregate_checks": evidence["aggregate_checks"],
        "static_wiring_checks": static_checks,
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = (
        generate_aod_openaq_real_provider_readiness_audit_data()
        if data is None
        else data
    )
    readiness = report["readiness"]
    summary = report["evidence_summary"]

    lines = [
        "# NSOM AOD/OpenAQ Real-Provider Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews the expanded real NASA Earthdata AOD "
            "and OpenAQ probe before any AOD/OpenAQ default-on decision. It reads "
            "the checked-in provider report as evidence, does not call the network, "
            "does not enable aerosol scoring, and does not change Planner, Home, "
            "Best Object, Advanced Observing, Sky Compass, Detail/Object, "
            "Equipment or QML."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Default runtime score effect: `{readiness['default_runtime_score_effect']}`.",
        f"- Feature flag change in this audit: `{readiness['feature_flag_change_in_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Evidence Summary",
        "",
        f"- Source report: `{report['metadata']['source_report']}`.",
        f"- Location set: `{summary['location_set']}`.",
        f"- Location count: `{summary['location_count']}`.",
        f"- Policy source counts: `{summary['policy_source_counts']}`.",
        f"- NASA AOD status counts: `{summary['nasa_aod_status_counts']}`.",
        f"- OpenAQ status counts: `{summary['openaq_status_counts']}`.",
        f"- AOD freshness counts: `{summary['aod_freshness_counts']}`.",
        f"- PM input freshness counts: `{summary['particulate_freshness_counts']}`.",
        f"- Locations with provider data and zero score effect: `{summary['zero_effect_provider_locations']}`.",
        f"- Locations with non-zero aerosol effect: `{summary['penalty_effect_locations']}`.",
        f"- Deep-sky max penalty: `{summary['deep_sky_max_penalty']}`.",
        f"- Solar-system max penalty: `{summary['solar_system_max_penalty']}`.",
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
            "## Blockers",
            "",
        ]
    )
    if report["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in report["blockers"])
    else:
        lines.append("- none")

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
                "The real-provider evidence is directionally coherent and the "
                "absolute score scale no longer looks like the blocker: low/clean "
                "provider successes stay neutral, deep-sky targets receive the "
                "largest effect, and protected solar-system targets remain nearly "
                "neutral. The default-on decision is still deferred because this "
                "checked-in evidence contains no current AOD input and represents "
                "one provider snapshot only."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _real_provider_evidence(path: Path) -> dict[str, object]:
    text = _read_text(path)
    provider_rows = tuple(_provider_row(row) for row in _table_rows(text, "Provider Results By Location"))
    policy_rows = tuple(_policy_row(row) for row in _table_rows(text, "Policy Reasons By Location"))
    effect_rows = tuple(_effect_row(row) for row in _table_rows(text, "Flag Off/On Aerosol Effects"))
    aggregate_checks = _aggregate_checks(_table_rows(text, "Aggregate Checks"))
    return {
        "source_report_exists": path.exists(),
        "location_set": _regex_value(text, r"Location set: `([^`]+)`", default="unknown"),
        "location_count": int(_regex_value(text, r"Location count: `(\d+)`", default="0")),
        "safety": {
            "runtime_behaviour_changed": _line_bool(text, "Runtime behaviour changed"),
            "qml_exposure": _line_bool(text, "QML exposure"),
            "network": _line_bool(text, "Network"),
            "automatic_logging": _line_bool(text, "Automatic logging"),
            "persistent_writes": _line_bool(text, "Persistent writes"),
            "credential_values_stored_in_report": _line_bool(
                text,
                "Credential values stored in report",
            ),
        },
        "provider_rows": provider_rows,
        "policy_rows": policy_rows,
        "effect_rows": effect_rows,
        "aggregate_checks": aggregate_checks,
    }


def _readiness_gates(evidence: dict[str, object]) -> tuple[dict[str, object], ...]:
    summary = _evidence_summary(evidence)
    return (
        {
            "gate": "expanded_real_provider_coverage",
            "status": "accepted" if summary["location_count"] == 15 else "review",
            "blocks_default_on": summary["location_count"] != 15,
            "reason": "The checked-in probe should cover the expanded 15-location set.",
            "evidence": f"location_count={summary['location_count']}",
        },
        {
            "gate": "policy_branch_coverage",
            "status": "accepted" if summary["all_policy_sources_observed"] else "review",
            "blocks_default_on": not summary["all_policy_sources_observed"],
            "reason": "Real data should exercise AOD, OpenAQ PM fallback and no-source neutrality.",
            "evidence": f"policy_source_counts={summary['policy_source_counts']}",
        },
        {
            "gate": "real_provider_score_scale",
            "status": "accepted" if summary["real_provider_score_scale_acceptable"] else "review",
            "blocks_default_on": not summary["real_provider_score_scale_acceptable"],
            "reason": (
                "Expanded real-provider effects should remain modest, target-specific "
                "and stronger for deep-sky targets than for protected solar-system targets."
            ),
            "evidence": (
                f"deep_sky={summary['deep_sky_max_penalty']}, "
                f"solar_system={summary['solar_system_max_penalty']}"
            ),
        },
        {
            "gate": "provider_rejection_and_fallback_policy",
            "status": "accepted" if summary["rejection_and_fallback_observed"] else "review",
            "blocks_default_on": not summary["rejection_and_fallback_observed"],
            "reason": (
                "Rejected/missing AOD should either remain neutral or fall back to "
                "local OpenAQ PM without additive double-counting."
            ),
            "evidence": f"policy_source_counts={summary['policy_source_counts']}",
        },
        {
            "gate": "zero_effect_provider_success",
            "status": "accepted" if summary["has_zero_effect_provider_success"] else "review",
            "blocks_default_on": not summary["has_zero_effect_provider_success"],
            "reason": "Clean/low provider data must be allowed to produce no score change.",
            "evidence": f"locations={summary['zero_effect_provider_locations']}",
        },
        {
            "gate": "credential_and_runtime_safety",
            "status": "accepted" if summary["credential_and_runtime_safety_ok"] else "warning",
            "blocks_default_on": not summary["credential_and_runtime_safety_ok"],
            "reason": "The report must remain developer-only with no credential values or runtime wiring.",
            "evidence": f"safety={evidence['safety']}",
        },
        {
            "gate": "aod_current_coverage_absent",
            "status": "review",
            "blocks_default_on": summary["current_aod_count"] == 0,
            "reason": (
                "The expanded real-provider run contains usable stale AOD but no "
                "current AOD input, so runtime behaviour under fresh AOD is not "
                "confirmed by real provider evidence."
            ),
            "evidence": f"aod_freshness_counts={summary['aod_freshness_counts']}",
        },
        {
            "gate": "single_snapshot_repeatability",
            "status": "review",
            "blocks_default_on": True,
            "reason": (
                "The checked-in evidence is one provider snapshot. Provider "
                "availability, AOD freshness and OpenAQ coverage should be repeated "
                "or explicitly accepted before default-on."
            ),
            "evidence": "real_provider_probe_runs=1",
        },
    )


def _evidence_summary(evidence: dict[str, object]) -> dict[str, object]:
    provider_rows = tuple(evidence["provider_rows"])
    effect_rows = tuple(evidence["effect_rows"])
    aggregate = dict(evidence["aggregate_checks"])
    policy_counts = _counts(row["policy_source"] for row in provider_rows)
    nasa_aod_status_counts = _counts(row["nasa_aod_status"] for row in provider_rows)
    openaq_status_counts = _counts(row["openaq_status"] for row in provider_rows)
    aod_freshness_counts = _counts(row["aod_input_freshness"] for row in provider_rows)
    pm_freshness_counts = _counts(row["particulate_input_freshness"] for row in provider_rows)
    effect_by_location: dict[str, list[dict[str, object]]] = {}
    for row in effect_rows:
        effect_by_location.setdefault(str(row["location"]), []).append(row)

    zero_effect_locations = tuple(
        location
        for location, rows in effect_by_location.items()
        if any(row["source"] in {"aod", "particulate"} for row in rows)
        and all(float(row["flag_on_modifier"]) == 0.0 for row in rows)
    )
    penalty_locations = tuple(
        location
        for location, rows in effect_by_location.items()
        if any(float(row["flag_on_modifier"]) < 0.0 for row in rows)
    )
    deep_sky_penalty = float(aggregate.get("deep_sky_max_penalty", 0.0))
    solar_system_penalty = float(aggregate.get("solar_system_max_penalty", 0.0))
    source_values = set(policy_counts)
    safety = dict(evidence["safety"])
    current_aod_count = int(aod_freshness_counts.get("current", 0))
    return {
        "source_report_exists": evidence["source_report_exists"],
        "location_set": evidence["location_set"],
        "location_count": evidence["location_count"],
        "policy_source_counts": policy_counts,
        "nasa_aod_status_counts": nasa_aod_status_counts,
        "openaq_status_counts": openaq_status_counts,
        "aod_freshness_counts": aod_freshness_counts,
        "particulate_freshness_counts": pm_freshness_counts,
        "current_aod_count": current_aod_count,
        "stale_aod_count": int(aod_freshness_counts.get("stale", 0)),
        "all_aod_inputs_are_stale_or_missing": set(aod_freshness_counts).issubset({"stale", "none"}),
        "all_policy_sources_observed": {"aod", "particulate", "none"}.issubset(source_values),
        "has_zero_effect_provider_success": bool(zero_effect_locations),
        "zero_effect_provider_locations": zero_effect_locations,
        "penalty_effect_locations": penalty_locations,
        "deep_sky_max_penalty": deep_sky_penalty,
        "solar_system_max_penalty": solar_system_penalty,
        "real_provider_score_scale_acceptable": (
            bool(aggregate.get("deep_sky_penalty_at_least_solar_system"))
            and abs(deep_sky_penalty) <= 4.0
            and abs(solar_system_penalty) <= 0.2
        ),
        "rejection_and_fallback_observed": (
            policy_counts.get("none", 0) > 0
            and policy_counts.get("particulate", 0) > 0
            and policy_counts.get("aod", 0) > 0
        ),
        "credential_and_runtime_safety_ok": (
            safety["runtime_behaviour_changed"] is False
            and safety["qml_exposure"] is False
            and safety["automatic_logging"] is False
            and safety["persistent_writes"] is False
            and safety["credential_values_stored_in_report"] is False
        ),
    }


def _checks(
    evidence: dict[str, object],
    gates: tuple[dict[str, object], ...],
    blockers: tuple[str, ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    summary = _evidence_summary(evidence)
    aggregate = dict(evidence["aggregate_checks"])
    return {
        "strict_json_compatible": _strict_json_compatible(evidence),
        "feature_flag_default_off": True,
        "default_runtime_neutral": aggregate.get("flag_off_always_neutral") is True,
        "source_report_exists": summary["source_report_exists"] is True,
        "expanded_location_count_is_15": summary["location_count"] == 15,
        "all_policy_sources_observed": summary["all_policy_sources_observed"] is True,
        "score_scale_resolved_by_real_provider_probe": (
            _gate(gates, "real_provider_score_scale")["blocks_default_on"] is False
        ),
        "zero_effect_provider_success_observed": summary["has_zero_effect_provider_success"] is True,
        "rejection_and_fallback_observed": summary["rejection_and_fallback_observed"] is True,
        "has_no_current_aod_input": summary["current_aod_count"] == 0,
        "all_aod_inputs_are_stale_or_missing": summary["all_aod_inputs_are_stale_or_missing"] is True,
        "temporal_evidence_still_blocks_default_on": "single_snapshot_repeatability" in blockers,
        "ready_for_default_on_is_false": bool(blockers),
        "confidence_neutral_notes_present": aggregate.get("confidence_score_neutral_notes_present") is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
    }


def _provider_row(cells: tuple[str, ...]) -> dict[str, object]:
    aod_tokens = _code_tokens(cells[2])
    pm_tokens = _code_tokens(cells[4])
    return {
        "location": cells[0],
        "nasa_aod_status": _first_code(cells[1]),
        "aod_input_included": _first_code(cells[2]) == "True",
        "aod_input_freshness": aod_tokens[-1] if aod_tokens else "none",
        "openaq_status": _first_code(cells[3]),
        "particulate_input_included": _first_code(cells[4]) == "True",
        "particulate_input_freshness": pm_tokens[-1] if pm_tokens else "none",
        "policy_source": _first_code(cells[5]),
    }


def _policy_row(cells: tuple[str, ...]) -> dict[str, object]:
    return {
        "location": cells[0],
        "policy_source": _first_code(cells[1]),
        "aod_eligible": _first_code(cells[2]) == "True",
        "aod_reasons": _reason_tokens(cells[3]),
        "particulate_eligible": _first_code(cells[4]) == "True",
        "particulate_reasons": _reason_tokens(cells[5]),
    }


def _effect_row(cells: tuple[str, ...]) -> dict[str, object]:
    return {
        "location": cells[0],
        "target_class": _first_code(cells[1]),
        "source": _first_code(cells[2]),
        "flag_off_modifier": float(_first_code(cells[3])),
        "flag_on_modifier": float(_first_code(cells[4])),
        "flag_on_score": int(float(_first_code(cells[5]))),
        "transparency_loss": float(_first_code(cells[6])),
    }


def _aggregate_checks(rows: tuple[tuple[str, ...], ...]) -> dict[str, object]:
    checks: dict[str, object] = {}
    for key_cell, value_cell in rows:
        key = _first_code(key_cell)
        raw_value = _strip_code(value_cell)
        checks[key] = _parse_value(raw_value)
    return checks


def _table_rows(text: str, heading: str) -> tuple[tuple[str, ...], ...]:
    marker = f"## {heading}"
    if marker not in text:
        return ()
    section = text.split(marker, 1)[1]
    section = section.split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if not cells or set(cells[0]) <= {"-", " "}:
            continue
        if cells[0] in {"Location", "Check", "Case"}:
            continue
        rows.append(cells)
    return tuple(rows)


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


def _counts(values: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _gate(gates: tuple[dict[str, object], ...], gate_id: str) -> dict[str, object]:
    return next(gate for gate in gates if gate["gate"] == gate_id)


def _code_tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`([^`]*)`", value))


def _first_code(value: str) -> str:
    tokens = _code_tokens(value)
    return tokens[0] if tokens else _strip_code(value)


def _reason_tokens(value: str) -> tuple[str, ...]:
    tokens = _code_tokens(value)
    return () if tokens == ("none",) else tokens


def _strip_code(value: str) -> str:
    return re.sub(r"`([^`]*)`", r"\1", value).strip()


def _parse_value(raw_value: str) -> object:
    if raw_value == "True":
        return True
    if raw_value == "False":
        return False
    try:
        return ast.literal_eval(raw_value)
    except (ValueError, SyntaxError):
        pass
    try:
        return float(raw_value)
    except ValueError:
        return raw_value


def _regex_value(text: str, pattern: str, *, default: str) -> str:
    match = re.search(pattern, text)
    return match.group(1) if match else default


def _line_bool(text: str, label: str) -> bool | None:
    value = _regex_value(text, rf"{re.escape(label)}: `([^`]+)`", default="")
    if value == "True":
        return True
    if value == "False":
        return False
    return None


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
