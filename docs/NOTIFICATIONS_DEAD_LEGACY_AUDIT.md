# Notifications Dead Legacy Audit

## Executive Summary

This developer-only audit checks whether the legacy Notifications backend still has a current QML/Home consumer. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Classification: `removed_dead_legacy`.
- QML consumed: `False`.
- Controller runtime present: `False`.
- Service file present: `False`.
- Model DTO present: `False`.
- Not an NSOM migration target: `True`.
- Recommended handling: Keep removed; do not rebuild unless a visible product requirement reintroduces notifications.

## Evidence

- No QML files consume `controller.notifications` or equivalent notification models.
- AppController no longer exposes or computes a notifications property.
- `NotificationService` and the `Notification` DTO are absent.

## Static Matches

| Area | Matches |
| --- | --- |
| QML consumers | `[]` |
| AppController runtime | `[]` |
| NotificationService | `[]` |
| Notification DTO | `[]` |

## Safety Checks

| Check | Result |
| --- | --- |
| `qml_consumers_absent` | `True` |
| `runtime_path_present` | `False` |
| `dead_legacy_pending_removal` | `False` |
| `removed_dead_legacy` | `True` |
| `not_a_nsom_migration_target` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Recommended Sequence

- `Review notification removal`: Confirm the dead Notifications backend/property/service path is absent.
- `1.12.5 ObservationConditions read-model audit`: Audit the active ObservationConditions read-model boundary after dead legacy cleanup.
- `1.12.6 ObservationConditions read-model boundary`: Separate raw target input from condition-adjusted display compatibility fields.

## Conclusion

Notifications should be treated like the removed Sky Map path: dead legacy when no QML/Home consumer exists, not as a backend NSOM migration surface.
