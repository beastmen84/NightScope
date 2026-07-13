from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping, Sequence


class ObservationLogValidationError(ValueError):
    pass


class ObservationLogService:
    """Validates observation records and builds the QML read model."""

    def normalize(
        self,
        *,
        date_text: str,
        time_text: str,
        object_name: str,
        location: str,
        telescope: str,
        eyepiece: str,
        rating: int,
        notes: str,
        now: datetime,
    ) -> dict:
        try:
            observed_at = datetime.strptime(
                f"{date_text.strip()} {time_text.strip()}",
                "%Y-%m-%d %H:%M",
            )
        except ValueError as error:
            raise ObservationLogValidationError(
                "Inserisci data e ora nei formati AAAA-MM-GG e HH:MM."
            ) from error

        local_now = now.replace(tzinfo=None, second=0, microsecond=0)
        if observed_at > local_now + timedelta(minutes=1):
            raise ObservationLogValidationError(
                "Il Log Osservazioni accetta soltanto osservazioni già effettuate."
            )

        clean_object_name = object_name.strip()
        if not clean_object_name:
            raise ObservationLogValidationError("Indica l'oggetto osservato.")
        if not 1 <= rating <= 5:
            raise ObservationLogValidationError("La valutazione deve essere compresa tra 1 e 5.")

        return {
            "date": observed_at.isoformat(timespec="minutes"),
            "object_name": clean_object_name,
            "location": location.strip(),
            "telescope": telescope.strip(),
            "eyepiece": eyepiece.strip(),
            "rating": rating,
            "notes": notes.strip(),
        }

    def build_entries(self, rows: Sequence[Mapping]) -> list[dict]:
        return [self._build_entry(row) for row in rows]

    def build_summary(self, rows: Sequence[Mapping]) -> dict:
        ratings = [int(row.get("rating") or 0) for row in rows if int(row.get("rating") or 0) > 0]
        object_names = {
            str(row.get("object_name") or "").strip().casefold()
            for row in rows
            if str(row.get("object_name") or "").strip()
        }
        latest_label = self._date_label(rows[0].get("date")) if rows else "-"
        return {
            "total": len(rows),
            "uniqueObjects": len(object_names),
            "averageRating": round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
            "latestLabel": latest_label,
        }

    def _build_entry(self, row: Mapping) -> dict:
        observed_at = self._parse_date(row.get("date"))
        date_value = observed_at.strftime("%Y-%m-%d") if observed_at else ""
        time_value = observed_at.strftime("%H:%M") if observed_at else ""
        telescope = str(row.get("telescope") or "").strip()
        eyepiece = str(row.get("eyepiece") or "").strip()
        setup_parts = [part for part in (telescope, eyepiece) if part]
        rating = max(0, min(5, int(row.get("rating") or 0)))
        notes = str(row.get("notes") or "").strip()
        location = str(row.get("location") or "").strip()
        object_name = str(row.get("object_name") or "").strip()
        return {
            "id": int(row["id"]),
            "date": str(row.get("date") or ""),
            "dateValue": date_value,
            "timeValue": time_value,
            "dateLabel": self._date_label(row.get("date")),
            "objectName": object_name,
            "location": location,
            "locationLabel": location or "Non specificata",
            "telescope": telescope,
            "eyepiece": eyepiece,
            "setupLabel": " / ".join(setup_parts) if setup_parts else "Non specificato",
            "rating": rating,
            "ratingLabel": f"{rating}/5" if rating else "-",
            "notes": notes,
            "notesLabel": notes or "Nessuna nota",
            "searchText": " ".join(
                (object_name, location, telescope, eyepiece, notes)
            ).casefold(),
        }

    def _date_label(self, value: object) -> str:
        parsed = self._parse_date(value)
        if not parsed:
            return str(value or "-")
        if parsed.hour == 0 and parsed.minute == 0 and "T" not in str(value):
            return parsed.strftime("%d/%m/%Y")
        return parsed.strftime("%d/%m/%Y %H:%M")

    @staticmethod
    def _parse_date(value: object) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
