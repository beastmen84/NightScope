from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible


REPORT_PATH = Path("docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md")

QML_NOTIFICATION_MARKERS = (
    "controller.notifications",
    "appController.notifications",
    "notificationsModel",
    "notificationModel",
)

APP_CONTROLLER_NOTIFICATION_MARKERS = (
    "from astro_viewer.app.services.notification_service import NotificationService",
    "self._notification_service = NotificationService()",
    "def notifications(",
    "self._notifications",
    "self._notification_service.notifications(",
)

SERVICE_NOTIFICATION_MARKERS = (
    "class NotificationService",
    "def notifications(",
)

MODEL_NOTIFICATION_MARKERS = (
    "class Notification",
)

RUNTIME_REPORT_MARKERS = (
    "notifications_dead_legacy_audit",
    "NOTIFICATIONS_DEAD_LEGACY_AUDIT",
)


def generate_notifications_dead_legacy_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    qml_matches = _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_NOTIFICATION_MARKERS)
    controller_matches = _scan_files(
        root / "astro_viewer" / "app" / "viewmodels",
        ("app_controller.py",),
        APP_CONTROLLER_NOTIFICATION_MARKERS,
    )
    service_file = root / "astro_viewer" / "app" / "services" / "notification_service.py"
    service_matches = _scan_files(
        service_file.parent,
        ("notification_service.py",),
        SERVICE_NOTIFICATION_MARKERS,
    )
    model_matches = _scan_files(
        root / "astro_viewer" / "app" / "models",
        ("sky.py",),
        MODEL_NOTIFICATION_MARKERS,
    )
    runtime_present = bool(controller_matches or service_file.exists() or model_matches)
    classification = (
        "removed_dead_legacy"
        if not qml_matches and not runtime_present
        else "dead_legacy_pending_removal"
        if not qml_matches
        else "active_or_visible"
    )
    static_checks = _static_wiring_checks(root)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "notification_surface": {
            "surface": "Notifications",
            "classification": classification,
            "qml_consumed": bool(qml_matches),
            "qml_consumer_matches": qml_matches,
            "controller_runtime_present": bool(controller_matches),
            "controller_matches": controller_matches,
            "service_file_present": service_file.exists(),
            "service_matches": service_matches,
            "model_dto_present": bool(model_matches),
            "model_matches": model_matches,
            "evidence": _evidence(classification),
            "recommended_handling": _recommended_handling(classification),
            "blocks_current_nsom_surfaces": False,
            "not_a_nsom_migration_target": classification != "active_or_visible",
        },
        "checks": {
            "qml_consumers_absent": qml_matches == (),
            "runtime_path_present": runtime_present,
            "dead_legacy_pending_removal": classification == "dead_legacy_pending_removal",
            "removed_dead_legacy": classification == "removed_dead_legacy",
            "not_a_nsom_migration_target": classification != "active_or_visible",
            "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
            "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
            "runtime_behaviour_unchanged_by_audit": True,
        },
        "static_checks": static_checks,
        "recommended_sequence": _recommended_sequence(classification),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_notifications_dead_legacy_audit_data() if data is None else data
    surface = audit["notification_surface"]

    lines = [
        "# Notifications Dead Legacy Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the legacy Notifications "
            "backend still has a current QML/Home consumer. It does not change "
            "runtime behaviour, QML, scoring, logging, network access or runtime "
            "file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Classification: `{surface['classification']}`.",
        f"- QML consumed: `{surface['qml_consumed']}`.",
        f"- Controller runtime present: `{surface['controller_runtime_present']}`.",
        f"- Service file present: `{surface['service_file_present']}`.",
        f"- Model DTO present: `{surface['model_dto_present']}`.",
        f"- Not an NSOM migration target: `{surface['not_a_nsom_migration_target']}`.",
        f"- Recommended handling: {surface['recommended_handling']}",
        "",
        "## Evidence",
        "",
    ]
    for item in surface["evidence"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Static Matches",
            "",
            "| Area | Matches |",
            "| --- | --- |",
            f"| QML consumers | `{surface['qml_consumer_matches']}` |",
            f"| AppController runtime | `{surface['controller_matches']}` |",
            f"| NotificationService | `{surface['service_matches']}` |",
            f"| Notification DTO | `{surface['model_matches']}` |",
            "",
            "## Safety Checks",
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
                "Notifications should be treated like the removed Sky Map path: "
                "dead legacy when no QML/Home consumer exists, not as a backend "
                "NSOM migration surface."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evidence(classification: str) -> tuple[str, ...]:
    if classification == "removed_dead_legacy":
        return (
            "No QML files consume `controller.notifications` or equivalent notification models.",
            "AppController no longer exposes or computes a notifications property.",
            "`NotificationService` and the `Notification` DTO are absent.",
        )
    if classification == "dead_legacy_pending_removal":
        return (
            "No QML files consume `controller.notifications` or equivalent notification models.",
            "AppController still exposes/computes notifications.",
            "`NotificationService` and the `Notification` DTO are still present.",
        )
    return (
        "A QML or runtime consumer still references notifications.",
        "Do not remove until the visible consumer contract is reviewed.",
    )


def _recommended_handling(classification: str) -> str:
    if classification == "removed_dead_legacy":
        return "Keep removed; do not rebuild unless a visible product requirement reintroduces notifications."
    if classification == "dead_legacy_pending_removal":
        return "Remove NotificationService, AppController.notifications, runtime recomputation and DTO/test leftovers."
    return "Review visible notification requirements before any migration or removal."


def _recommended_sequence(classification: str) -> tuple[dict[str, object], ...]:
    if classification == "removed_dead_legacy":
        return (
            {
                "step": "Review notification removal",
                "summary": "Confirm the dead Notifications backend/property/service path is absent.",
            },
            {
                "step": "1.12.5 ObservationConditions read-model audit",
                "summary": "Audit the active ObservationConditions read-model boundary after dead legacy cleanup.",
            },
            {
                "step": "1.12.6 ObservationConditions read-model boundary",
                "summary": "Separate raw target input from condition-adjusted display compatibility fields.",
            },
        )
    return (
        {
            "step": "1.12.3 Notifications dead legacy audit",
            "summary": "Classify Notifications as dead legacy because no QML/Home consumer remains.",
        },
        {
            "step": "1.12.4 Remove dead Notifications backend path",
            "summary": "Remove AppController notifications, NotificationService and leftover DTO/tests.",
        },
        {
            "step": "1.12.5 ObservationConditions read-model audit",
            "summary": "Audit the active ObservationConditions read-model boundary after dead legacy cleanup.",
        },
    )


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            RUNTIME_REPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "qml_report_exposure_matches": _scan_files(
            root / "astro_viewer" / "app" / "ui",
            ("*.qml",),
            RUNTIME_REPORT_MARKERS,
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


if __name__ == "__main__":
    write_markdown_report()
