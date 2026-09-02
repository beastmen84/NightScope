"""Protect deterministic Bandit normalization, baseline review, and regression failure."""

from __future__ import annotations

from pathlib import Path

from tools.check_bandit import (
    Finding,
    baseline_payload,
    finding_differences,
    finding_from_result,
    normalize_reported_code,
)


def _finding(*, source: str = "query = f\"SELECT {column}\"") -> Finding:
    return Finding(
        test_id="B608",
        severity="MEDIUM",
        confidence="MEDIUM",
        path="astro_viewer/app/database/example.py",
        source=source,
        code_hash=(
            "737de8090807bff7397ffaa466c4b586d0efd7894f048c5ca9d27ea131086958"
        ),
    )


def test_finding_fingerprint_is_path_portable_and_line_number_independent(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "astro_viewer" / "app" / "database" / "example.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(
        "padding = True\nquery = f\"SELECT {column}\"\n",
        encoding="utf-8",
    )
    result = {
        "test_id": "B608",
        "issue_severity": "MEDIUM",
        "issue_confidence": "MEDIUM",
        "filename": ".\\astro_viewer\\app\\database\\example.py",
        "line_number": 2,
        "code": '1 padding = True\n2 query = f"SELECT {column}"\n',
    }

    assert finding_from_result(result, tmp_path) == _finding()


def test_reported_code_hash_ignores_only_bandit_line_number_prefixes() -> None:
    original = '1 padding = True\n2 query = f"SELECT {column}"\n'
    shifted = '40 padding = True\n41 query = f"SELECT {column}"\n'
    changed = '40 padding = True\n41 query = f"DELETE FROM {column}"\n'

    assert normalize_reported_code(original) == normalize_reported_code(shifted)
    assert normalize_reported_code(original) != normalize_reported_code(changed)


def test_finding_differences_are_multiset_sensitive() -> None:
    expected = [_finding(), _finding()]

    added, removed = finding_differences(expected, [_finding()])

    assert added == []
    assert removed == [_finding()]


def test_changed_source_or_severity_requires_a_new_review() -> None:
    changed_source = _finding(source="query = f\"DELETE FROM {table}\"")
    changed_severity = Finding(
        test_id="B608",
        severity="HIGH",
        confidence="MEDIUM",
        path="astro_viewer/app/database/example.py",
        source=_finding().source,
        code_hash=_finding().code_hash,
    )

    added, removed = finding_differences([_finding()], [changed_source])
    assert added == [changed_source]
    assert removed == [_finding()]

    added, removed = finding_differences([_finding()], [changed_severity])
    assert added == [changed_severity]
    assert removed == [_finding()]


def test_baseline_documents_the_strict_review_policy() -> None:
    payload = baseline_payload([_finding()])

    assert payload["schema_version"] == 1
    assert "high-severity findings are never accepted" in payload["policy"]
    assert {test_id for item in payload["review"] for test_id in item["test_ids"]} == {
        "B110",
        "B314",
        "B404",
        "B405",
        "B603",
        "B607",
        "B608",
    }
    assert payload["findings"] == [
        {
            "test_id": "B608",
            "severity": "MEDIUM",
            "confidence": "MEDIUM",
            "path": "astro_viewer/app/database/example.py",
            "source": "query = f\"SELECT {column}\"",
            "code_hash": (
                "737de8090807bff7397ffaa466c4b586d0efd7894f048c5ca9d27ea131086958"
            ),
        }
    ]
