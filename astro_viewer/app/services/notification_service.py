from __future__ import annotations

from datetime import datetime, timedelta

from astro_viewer.app.models.observing import AstronomicalEvent, CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, NightPlanItem, Notification


class NotificationService:
    """Creates lightweight scheduled observation hints for the UI."""

    def notifications(
        self,
        best_object: CelestialObject | None,
        plan: list[NightPlanItem],
        events: list[AstronomicalEvent],
        scores: AdvancedObservingScores,
        moon: MoonSummary,
    ) -> list[Notification]:
        now = datetime.now()
        notifications: list[Notification] = []

        if best_object:
            notifications.append(
                Notification(
                    title=f"{best_object.name} al meglio",
                    message=f"Tra poco {best_object.name} sara vicino alla finestra migliore: {best_object.observing_window}.",
                    trigger_time=(now + timedelta(minutes=30)).strftime("%H:%M"),
                    priority=90,
                )
            )
        if plan:
            notifications.append(
                Notification(
                    title="Piano osservativo pronto",
                    message=f"Prima tappa consigliata: {plan[0].time_label} - {plan[0].name}.",
                    trigger_time=plan[0].time_label,
                    priority=84,
                )
            )
        if scores.deep_sky_score >= 76:
            notifications.append(
                Notification(
                    title="Cielo profondo sopra la media",
                    message="Le condizioni per il cielo profondo saranno migliori del normale.",
                    trigger_time=(now + timedelta(hours=1)).strftime("%H:%M"),
                    priority=78,
                )
            )
        if moon.phase == "Piena":
            notifications.append(
                Notification(
                    title="Luna piena",
                    message="Questa sera la Luna penalizza gli oggetti cielo profondo deboli.",
                    trigger_time="20:00",
                    priority=65,
                )
            )
        for event in events[:2]:
            notifications.append(
                Notification(
                    title=event.title,
                    message=f"{event.event_type}: {event.note}",
                    trigger_time=event.best_time,
                    priority=event.usefulness,
                )
            )
        return sorted(notifications, key=lambda item: item.priority, reverse=True)[:5]
