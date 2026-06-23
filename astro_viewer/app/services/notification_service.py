from __future__ import annotations

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
        notifications: list[Notification] = []

        if plan:
            first_target = plan[0]
            notifications.append(
                Notification(
                    title="Prima tappa del piano",
                    message=f"{first_target.name} verso {first_target.direction}. Setup: {first_target.setup}.",
                    trigger_time=first_target.time_label,
                    priority=84,
                )
            )
        if scores.planetary_score >= 76:
            notifications.append(
                Notification(
                    title="Condizioni planetarie favorevoli",
                    message="Seeing e vento supportano pianeti con ingrandimenti medio-alti.",
                    trigger_time="Stasera",
                    priority=80,
                )
            )
        if scores.deep_sky_score >= 76:
            notifications.append(
                Notification(
                    title="Finestra deep-sky utile",
                    message="Trasparenza, Luna e cielo locale sono favorevoli agli oggetti diffusi.",
                    trigger_time="Stanotte",
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
        return sorted(notifications, key=lambda item: item.priority, reverse=True)[:5]
