from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.notifications_dead_legacy_audit import (
    REPORT_PATH,
    generate_notifications_dead_legacy_audit_data,
    render_markdown_report,
)


def test_notifications_dead_legacy_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_notifications_dead_legacy_audit_data()
    second = generate_notifications_dead_legacy_audit_data()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_behaviour_changed_by_this_audit": False,
        "report_path": "docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md",
    }


def test_notifications_dead_legacy_backend_path_has_been_removed() -> None:
    data = generate_notifications_dead_legacy_audit_data()
    surface = data["notification_surface"]

    assert surface["surface"] == "Notifications"
    assert surface["classification"] == "removed_dead_legacy"
    assert surface["qml_consumed"] is False
    assert surface["qml_consumer_matches"] == []
    assert surface["controller_runtime_present"] is False
    assert surface["service_file_present"] is False
    assert surface["model_dto_present"] is False
    assert surface["not_a_nsom_migration_target"] is True
    assert data["checks"]["qml_consumers_absent"] is True
    assert data["checks"]["dead_legacy_pending_removal"] is False
    assert data["checks"]["removed_dead_legacy"] is True


def test_notifications_dead_legacy_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_notifications_dead_legacy_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_checks"]["runtime_report_import_matches"] == []
    assert data["static_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_notifications_dead_legacy_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Notifications Dead Legacy Audit" in text
    assert "removed_dead_legacy" in text
    assert "not as a backend NSOM migration surface" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
