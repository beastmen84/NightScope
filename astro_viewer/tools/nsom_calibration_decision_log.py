from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.tools.nsom_planner_comparison_report import generate_report_data

DECISION_LOG_PATH = Path("docs/NSOM_CALIBRATION_DECISION_LOG.md")
DECISION_STATUSES = (
    "accepted",
    "deferred",
    "needs_calibration",
    "needs_policy_decision",
)


@dataclass(frozen=True)
class CalibrationDecision:
    decision_id: str
    decision_status: str
    decision_reason: str
    affected_nsom_layer: str
    affected_target_class: str
    intentional_nsom_behaviour: bool
    possible_calibration_issue: bool
    blocks_default_on_work: bool
    blocked_session_policy_decision_placeholder: bool
    rank_delta_review_notes: str
    requires_tuning: bool
    match: Callable[[dict[str, object]], bool]

    def to_payload(self, linked_rows: tuple[str, ...]) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "decision_status": self.decision_status,
            "decision_reason": self.decision_reason,
            "affected_nsom_layer": self.affected_nsom_layer,
            "affected_target_class": self.affected_target_class,
            "intentional_nsom_behaviour": self.intentional_nsom_behaviour,
            "possible_calibration_issue": self.possible_calibration_issue,
            "blocks_default_on_work": self.blocks_default_on_work,
            "blocked_session_policy_decision_placeholder": (
                self.blocked_session_policy_decision_placeholder
            ),
            "rank_delta_review_notes": self.rank_delta_review_notes,
            "requires_tuning": self.requires_tuning,
            "linked_rows": linked_rows,
        }


def generate_decision_log_data(
    report_data: dict[str, object] | None = None,
) -> dict[str, object]:
    comparison = generate_report_data() if report_data is None else report_data
    review_rows_source = tuple(
        row
        for group in comparison["scenario_groups"]
        for row in group["scenarios"]
        if row["calibration_review"]["status"] != "expected"
    )
    policy_rows = tuple(
        row
        for group in comparison["scenario_groups"]
        for row in group["scenarios"]
        if row["opportunity_policy_type"] != "actionable_ranked_recommendation"
    )
    rows = tuple({str(row["scenario_id"]): row for row in (*review_rows_source, *policy_rows)}.values())
    decisions = _decision_entries()
    row_decisions = {
        str(row["scenario_id"]): tuple(
            decision.decision_id
            for decision in decisions
            if decision.match(row)
        )
        for row in rows
    }
    decision_payloads = tuple(
        decision.to_payload(
            tuple(
                scenario_id
                for scenario_id, decision_ids in row_decisions.items()
                if decision.decision_id in decision_ids
            )
        )
        for decision in decisions
    )
    warning_rows = tuple(
        str(row["scenario_id"])
        for row in review_rows_source
        if row["calibration_review"]["status"] == "warning"
    )
    review_rows = tuple(
        str(row["scenario_id"])
        for row in review_rows_source
        if row["calibration_review"]["status"] == "review"
    )
    policy_row_ids = tuple(str(row["scenario_id"]) for row in policy_rows)
    log_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "nsom_planner_scoring_enabled": NSOM_PLANNER_SCORING_ENABLED,
            "source_report": "docs/NSOM_PLANNER_COMPARISON_REPORT.md",
            "decision_statuses": DECISION_STATUSES,
        },
        "summary": _summary(
            decisions=decision_payloads,
            row_decisions=row_decisions,
            warning_rows=warning_rows,
            review_rows=review_rows,
            policy_rows=policy_row_ids,
            confidence_control=comparison["confidence_control"],
        ),
        "decisions": decision_payloads,
        "row_decisions": row_decisions,
        "warning_rows": warning_rows,
        "review_rows": review_rows,
        "policy_rows": policy_row_ids,
        "confidence_control": comparison["confidence_control"],
    }
    return nsom_to_json_compatible(log_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    log_data = generate_decision_log_data() if data is None else data
    summary = log_data["summary"]
    confidence = log_data["confidence_control"]
    lines = [
        "# NSOM Calibration Decision Log",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only decision log records how current NSOM Planner "
            "calibration review rows are accepted, deferred, escalated to targeted "
            "calibration, or held for policy decisions. It does not tune weights, "
            "enable NSOM Planner, or change runtime Planner behaviour."
        ),
        "",
        "## Decision Status Counts",
        "",
        "| Status | Count |",
        "| --- | ---: |",
    ]
    for status, count in summary["decision_status_counts"].items():
        lines.append(f"| `{status}` | {count} |")

    lines.extend(
        [
            "",
            "## Default-On Blockers",
            "",
        ]
    )
    for decision_id in summary["default_on_blockers"]:
        lines.append(f"- `{decision_id}`")

    lines.extend(
        [
            "",
            "## Decision Entries",
            "",
            "| Decision | Status | Layer | Target | Blocks Default-On | Reason |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for decision in log_data["decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['decision_status']}`",
                    str(decision["affected_nsom_layer"]),
                    str(decision["affected_target_class"]),
                    "yes" if decision["blocks_default_on_work"] else "no",
                    str(decision["decision_reason"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Warning And Review Row Links",
            "",
            "| Scenario | Decisions |",
            "| --- | --- |",
        ]
    )
    for scenario_id, decision_ids in log_data["row_decisions"].items():
        lines.append(
            f"| `{scenario_id}` | "
            + ", ".join(f"`{decision_id}`" for decision_id in decision_ids)
            + " |"
        )

    lines.extend(
        [
            "",
            "## Resolved Opportunity Policies",
            "",
            (
                "`blocked-session-hard-block-policy`, "
                "`invisible-target-non-actionable-policy` and "
                "`missing-window-policy` are resolved as developer-only policy "
                "metadata. G09 and G20 remain non-actionable; G19 remains "
                "actionable with uncertain timing through the conservative 0.5 "
                "observing-window fallback."
            ),
            "",
            "## Confidence Control",
            "",
            (
                f"Low confidence score `{float(confidence['low_confidence_score']):.4f}` "
                f"and high confidence score `{float(confidence['high_confidence_score']):.4f}` "
                f"produce score delta `{float(confidence['score_delta']):.4f}`."
            ),
            "",
            "## Recommended Next Step",
            "",
            (
                "Target only the entries marked `needs_calibration` with isolated "
                "formula changes before reconsidering default-on NSOM Planner work."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = DECISION_LOG_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _summary(
    *,
    decisions: tuple[dict[str, object], ...],
    row_decisions: dict[str, tuple[str, ...]],
    warning_rows: tuple[str, ...],
    review_rows: tuple[str, ...],
    policy_rows: tuple[str, ...],
    confidence_control: dict[str, object],
) -> dict[str, object]:
    status_counts = {status: 0 for status in DECISION_STATUSES}
    for decision in decisions:
        status_counts[str(decision["decision_status"])] += 1
    return {
        "decision_status_counts": status_counts,
        "warning_rows_covered": all(row_decisions[row] for row in warning_rows),
        "review_rows_linked": all(row_decisions[row] for row in review_rows),
        "policy_rows_linked": all(row_decisions[row] for row in policy_rows),
        "unlinked_rows": tuple(
            scenario_id
            for scenario_id, decision_ids in row_decisions.items()
            if not decision_ids
        ),
        "unresolved_policy_decisions": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["decision_status"] == "needs_policy_decision"
        ),
        "default_on_blockers": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["blocks_default_on_work"]
        ),
        "remaining_policy_blockers": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["decision_status"] == "needs_policy_decision"
            and decision["blocks_default_on_work"]
        ),
        "tuning_requirement_decisions": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["requires_tuning"]
        ),
        "accepted_without_tuning": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["decision_status"] == "accepted"
            and not decision["requires_tuning"]
        ),
        "confidence_score_delta": confidence_control["score_delta"],
    }


def _decision_entries() -> tuple[CalibrationDecision, ...]:
    return (
        CalibrationDecision(
            decision_id="blocked-session-hard-block-policy",
            decision_status="accepted",
            decision_reason=(
                "G09 keeps the current hard-block score behaviour. "
                "ObservationOpportunity remains 0.0, stable order is deterministic "
                "tie order, and non_actionable_preserved_order is diagnostic-only."
            ),
            affected_nsom_layer="SessionViability/ObservationOpportunity",
            affected_target_class="all",
            intentional_nsom_behaviour=True,
            possible_calibration_issue=False,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="Rank deltas inside the all-zero blocked tie are not recommendation deltas.",
            requires_tuning=False,
            match=lambda row: _group_id(row) == "G09",
        ),
        CalibrationDecision(
            decision_id="invisible-target-non-actionable-policy",
            decision_status="accepted",
            decision_reason=(
                "G20 invisible targets remain non-actionable when geometric "
                "visibility is 0.0; stable all-zero order is deterministic tie order "
                "and never recommendation ranking."
            ),
            affected_nsom_layer="ObservationEnvironment/ObservationOpportunity",
            affected_target_class="all",
            intentional_nsom_behaviour=True,
            possible_calibration_issue=False,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="Rank deltas inside invisible-target ties are diagnostic only.",
            requires_tuning=False,
            match=lambda row: _group_id(row) == "G20",
        ),
        CalibrationDecision(
            decision_id="small-equipment-planet-q-target",
            decision_status="accepted",
            decision_reason=(
                "G10/G11 planets now use a planet-observable Q_target floor for "
                "small but usable equipment, preserving the distinction between "
                "planet observable and planet optimal detail without changing "
                "sky, session or confidence layers."
            ),
            affected_nsom_layer="ObserverCapability/PracticalTargetValue",
            affected_target_class="planet",
            intentional_nsom_behaviour=False,
            possible_calibration_issue=False,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes=(
                "Rank delta is reduced from warning to review; the preserved "
                "ObservableTargetValue confirms the change is limited to Q_target."
            ),
            requires_tuning=False,
            match=lambda row: _scenario_id(row) in {"G10:planet", "G11:planet"},
        ),
        CalibrationDecision(
            decision_id="globular-large-telescope-promotion",
            decision_status="accepted",
            decision_reason=(
                "Large-telescope deep-sky conditions intentionally favour globular "
                "clusters through light grasp and resolution in Q_target."
            ),
            affected_nsom_layer="ObserverCapability/PracticalTargetValue",
            affected_target_class="globular_cluster",
            intentional_nsom_behaviour=True,
            possible_calibration_issue=False,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="Large negative rank delta is accepted model behaviour.",
            requires_tuning=False,
            match=lambda row: _target_type(row) == "globular_cluster"
            and _equipment(row) == "large_telescope"
            and int(row["rank_delta"]) <= -3,
        ),
        CalibrationDecision(
            decision_id="open-cluster-recurring-demotion",
            decision_status="needs_calibration",
            decision_reason=(
                "Open clusters recur as large positive rank deltas across baseline, "
                "session, geometry and large-telescope groups. Review intrinsic "
                "cluster value and Q_target field-of-view/comfort weighting together."
            ),
            affected_nsom_layer="Universe/ObserverCapability/PracticalTargetValue",
            affected_target_class="open_cluster",
            intentional_nsom_behaviour=False,
            possible_calibration_issue=True,
            blocks_default_on_work=True,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="Recurring open-cluster demotion is a targeted calibration blocker.",
            requires_tuning=True,
            match=lambda row: _target_type(row) == "open_cluster"
            and abs(int(row["rank_delta"])) >= 3
            and _group_id(row) != "G20",
        ),
        CalibrationDecision(
            decision_id="medium-equipment-q-target-review-band",
            decision_status="deferred",
            decision_reason=(
                "Many review rows are driven by Q_target being below the current "
                "review threshold rather than by a directional rule failure. Keep "
                "them linked but do not turn them into broad tuning work."
            ),
            affected_nsom_layer="ObserverCapability/PracticalTargetValue",
            affected_target_class="all",
            intentional_nsom_behaviour=True,
            possible_calibration_issue=False,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="Q_target review-band rows need context, not global scaling.",
            requires_tuning=False,
            match=lambda row: "Q_target" in row["calibration_review"][
                "suggested_human_review_reason"
            ],
        ),
        CalibrationDecision(
            decision_id="missing-window-policy",
            decision_status="accepted",
            decision_reason=(
                "G19 visible targets keep the conservative 0.5 observing-window "
                "fallback and are marked actionable_with_uncertain_timing rather "
                "than fully normal."
            ),
            affected_nsom_layer="ObservationOpportunity",
            affected_target_class="all",
            intentional_nsom_behaviour=True,
            possible_calibration_issue=False,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="Rank deltas are reviewed with explicit uncertain timing metadata.",
            requires_tuning=False,
            match=lambda row: _group_id(row) == "G19",
        ),
        CalibrationDecision(
            decision_id="moon-planet-favouring-category-factor",
            decision_status="deferred",
            decision_reason=(
                "G14 Moon warning is caused by the generic protected-target threshold "
                "interacting with category/session factors, not by sky-background "
                "damage. Keep it visible for the Moon-specific pass."
            ),
            affected_nsom_layer="Sky/ObservableTargetValue",
            affected_target_class="moon",
            intentional_nsom_behaviour=True,
            possible_calibration_issue=True,
            blocks_default_on_work=False,
            blocked_session_policy_decision_placeholder=False,
            rank_delta_review_notes="No rank delta escalation; defer to Moon-specific calibration review.",
            requires_tuning=False,
            match=lambda row: _scenario_id(row) == "G14:moon",
        ),
    )


def _scenario_id(row: dict[str, object]) -> str:
    return str(row["scenario_id"])


def _group_id(row: dict[str, object]) -> str:
    return _scenario_id(row).split(":", 1)[0]


def _target_type(row: dict[str, object]) -> str:
    return str(row["target_type"])


def _equipment(row: dict[str, object]) -> str:
    return str(row["axes"]["equipment_profile"])


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
