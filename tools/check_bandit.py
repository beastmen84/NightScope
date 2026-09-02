"""Compare Bandit findings with the reviewed baseline and reject security regressions."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess  # nosec B404 - fixed local Bandit command, never user input
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).with_name("bandit_baseline.json")
BASELINE_SCHEMA_VERSION = 1
BANDIT_TARGETS = (
    "astro_viewer/app",
    "astro_viewer/main.py",
    "tools",
)
BASELINE_REVIEW = (
    {
        "test_ids": ["B110"],
        "rationale": (
            "The destructor only suppresses cleanup failures after explicit close() "
            "has already been attempted; runtime work does not depend on finalization."
        ),
    },
    {
        "test_ids": ["B314", "B405"],
        "rationale": (
            "The maintenance command parses only repository-owned Qt TS files selected "
            "from the fixed translations directory, never remote or user-supplied XML."
        ),
    },
    {
        "test_ids": ["B404", "B603", "B607"],
        "rationale": (
            "Location and packaging helpers use argument lists with shell disabled; "
            "executables and developer-tool arguments come from controlled code paths."
        ),
    },
    {
        "test_ids": ["B608"],
        "rationale": (
            "SQLite values remain parameterized. Dynamic identifiers come from fixed "
            "internal table/column maps and placeholder strings derived only from value "
            "counts, not from user-provided SQL fragments."
        ),
    },
)


@dataclass(frozen=True, order=True)
class Finding:
    test_id: str
    severity: str
    confidence: str
    path: str
    source: str
    code_hash: str


def normalize_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def normalize_reported_code(value: str) -> str:
    lines = []
    for line in value.replace("\r\n", "\n").splitlines():
        lines.append(re.sub(r"^\s*\d+\s", "", line).rstrip())
    return "\n".join(lines).strip()


def finding_from_result(result: dict[str, Any], repo_root: Path) -> Finding:
    relative_path = normalize_relative_path(str(result["filename"]))
    source_path = repo_root / Path(relative_path)
    line_number = int(result["line_number"])
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    if line_number < 1 or line_number > len(source_lines):
        raise ValueError(
            f"Bandit returned invalid line {line_number} for {relative_path}."
        )
    normalized_code = normalize_reported_code(str(result["code"]))
    return Finding(
        test_id=str(result["test_id"]),
        severity=str(result["issue_severity"]),
        confidence=str(result["issue_confidence"]),
        path=relative_path,
        source=source_lines[line_number - 1].strip(),
        code_hash=hashlib.sha256(normalized_code.encode("utf-8")).hexdigest(),
    )


def findings_from_report(report: dict[str, Any], repo_root: Path) -> list[Finding]:
    results = report.get("results")
    if not isinstance(results, list):
        raise ValueError("Bandit JSON report has no results list.")
    return sorted(finding_from_result(result, repo_root) for result in results)


def load_baseline(path: Path = BASELINE_PATH) -> list[Finding]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != BASELINE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported Bandit baseline schema in {path}: "
            f"{payload.get('schema_version')!r}."
        )
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        raise ValueError(f"Bandit baseline {path} has no findings list.")
    return sorted(Finding(**item) for item in raw_findings)


def finding_differences(
    expected: list[Finding], current: list[Finding]
) -> tuple[list[Finding], list[Finding]]:
    expected_counts = Counter(expected)
    current_counts = Counter(current)
    added = sorted((current_counts - expected_counts).elements())
    removed = sorted((expected_counts - current_counts).elements())
    return added, removed


def run_bandit(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    command = (
        sys.executable,
        "-m",
        "bandit",
        "-q",
        "-r",
        *BANDIT_TARGETS,
        "-f",
        "json",
    )
    completed = subprocess.run(  # nosec B603 - argv is a fixed local command
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode not in {0, 1}:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"Bandit failed with exit code {completed.returncode}: {details}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Bandit did not produce a valid JSON report.") from error


def baseline_payload(findings: list[Finding]) -> dict[str, Any]:
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "reviewed_on": "2026-09-02",
        "policy": (
            "Exact reviewed findings only. New, removed, reclassified, or changed "
            "source lines fail the gate; high-severity findings are never accepted."
        ),
        "review": list(BASELINE_REVIEW),
        "findings": [asdict(finding) for finding in sorted(findings)],
    }


def write_baseline(path: Path, findings: list[Finding]) -> None:
    path.write_text(
        json.dumps(baseline_payload(findings), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _summary(findings: list[Finding]) -> str:
    severities = Counter(finding.severity for finding in findings)
    return (
        f"{len(findings)} finding(s): "
        f"{severities['HIGH']} high, {severities['MEDIUM']} medium, "
        f"{severities['LOW']} low"
    )


def _render_findings(label: str, findings: list[Finding]) -> None:
    if not findings:
        return
    print(f"{label} ({len(findings)}):")
    for finding in findings:
        print(
            f"  {finding.test_id} {finding.severity}/{finding.confidence} "
            f"{finding.path}: {finding.source} [{finding.code_hash[:12]}]"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run Bandit and reject every change from the reviewed source-line "
            "baseline."
        )
    )
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        "--write-baseline",
        action="store_true",
        help="Explicitly replace the reviewed baseline with the current findings.",
    )
    output_mode.add_argument(
        "--render-baseline",
        action="store_true",
        help="Print the current baseline JSON without changing the repository.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH,
        help="Baseline path (defaults to tools/bandit_baseline.json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        current = findings_from_report(run_bandit(), REPO_ROOT)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Bandit gate could not run: {error}", file=sys.stderr)
        return 2

    high_findings = [finding for finding in current if finding.severity == "HIGH"]
    if high_findings:
        _render_findings("High-severity findings are forbidden", high_findings)
        return 1

    if args.write_baseline:
        write_baseline(args.baseline, current)
        print(f"Wrote reviewed Bandit baseline to {args.baseline}: {_summary(current)}.")
        return 0
    if args.render_baseline:
        print(json.dumps(baseline_payload(current), indent=2, ensure_ascii=False))
        return 0

    try:
        expected = load_baseline(args.baseline)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Bandit baseline could not be loaded: {error}", file=sys.stderr)
        return 2
    added, removed = finding_differences(expected, current)
    if added or removed:
        print("Bandit findings differ from the reviewed baseline.")
        _render_findings("New or changed findings", added)
        _render_findings("Removed or changed baseline entries", removed)
        return 1

    print(f"Bandit baseline unchanged: {_summary(current)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
