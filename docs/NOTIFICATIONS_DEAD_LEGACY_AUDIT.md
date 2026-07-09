# Notifications Dead Legacy Audit

## Executive Summary

This developer-only audit checks whether the legacy Notifications backend still has a current QML/Home consumer. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Classification: `dead_legacy_pending_removal`.
- QML consumed: `False`.
- Controller runtime present: `True`.
- Service file present: `True`.
- Model DTO present: `True`.
- Not an NSOM migration target: `True`.
- Recommended handling: Remove NotificationService, AppController.notifications, runtime recomputation and DTO/test leftovers.

## Evidence

- No QML files consume `controller.notifications` or equivalent notification models.
- AppController still exposes/computes notifications.
- `NotificationService` and the `Notification` DTO are still present.

## Static Matches

| Area | Matches |
| --- | --- |
| QML consumers | `[]` |
| AppController runtime | `[{'path': 'app_controller.py', 'line': 71, 'marker': 'from astro_viewer.app.services.notification_service import NotificationService'}, {'path': 'app_controller.py', 'line': 255, 'marker': 'self._notification_service = NotificationService()'}, {'path': 'app_controller.py', 'line': 292, 'marker': 'self._notifications'}, {'path': 'app_controller.py', 'line': 684, 'marker': 'def notifications('}, {'path': 'app_controller.py', 'line': 685, 'marker': 'self._notifications'}, {'path': 'app_controller.py', 'line': 1745, 'marker': 'self._notifications'}, {'path': 'app_controller.py', 'line': 1963, 'marker': 'self._notifications'}, {'path': 'app_controller.py', 'line': 1963, 'marker': 'self._notification_service.notifications('}, {'path': 'app_controller.py', 'line': 2820, 'marker': 'self._notifications'}, {'path': 'app_controller.py', 'line': 2825, 'marker': 'self._notifications'}]` |
| NotificationService | `[{'path': 'notification_service.py', 'line': 7, 'marker': 'class NotificationService'}, {'path': 'notification_service.py', 'line': 10, 'marker': 'def notifications('}]` |
| Notification DTO | `[{'path': 'sky.py', 'line': 113, 'marker': 'class Notification'}]` |

## Safety Checks

| Check | Result |
| --- | --- |
| `qml_consumers_absent` | `True` |
| `runtime_path_present` | `True` |
| `dead_legacy_pending_removal` | `True` |
| `removed_dead_legacy` | `False` |
| `not_a_nsom_migration_target` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Recommended Sequence

- `1.12.3 Notifications dead legacy audit`: Classify Notifications as dead legacy because no QML/Home consumer remains.
- `1.12.4 Remove dead Notifications backend path`: Remove AppController notifications, NotificationService and leftover DTO/tests.
- `Next backend area decision`: Continue with ObservationConditions read-model cleanup or Equipment presenter contract work.

## Conclusion

Notifications should be treated like the removed Sky Map path: dead legacy when no QML/Home consumer exists, not as a backend NSOM migration surface.
