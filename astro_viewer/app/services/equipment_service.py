from __future__ import annotations

from astro_viewer.app.models.equipment import BeginnerPreset, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject


class EquipmentService:
    def beginner_presets(self) -> list[BeginnerPreset]:
        return [
            BeginnerPreset("naked-eye", "Occhio nudo", "Costellazioni e meteore", "Nessuna configurazione richiesta.", "Luna, Venere, Giove, sciami meteorici"),
            BeginnerPreset("binoculars", "Binocolo 10x50", "Ammassi aperti e Luna", "Campo ampio e uso immediato.", "M31, Pleiadi, Luna crescente"),
            BeginnerPreset("small-scope", "Telescopio piccolo", "Luna, pianeti luminosi, stelle doppie", "Rifrattore o Maksutov fino a 90 mm.", "Giove, Saturno, Albireo"),
            BeginnerPreset("medium-scope", "Telescopio medio", "Pianeti e deep sky brillante", "Strumento versatile da 130-200 mm.", "M13, M57, nebulose luminose"),
            BeginnerPreset("large-scope", "Telescopio grande", "Oggetti deboli e dettagli planetari", "Richiede seeing e acclimatazione accurati.", "Galassie, nebulose planetarie, globulari risolti"),
        ]

    def default_telescopes(self) -> list[Telescope]:
        return [
            Telescope("refractor-80", "Rifrattore 80/600", 80, 600, "rifrattore", "altazimutale"),
            Telescope("newton-150", "Newton 150/750", 150, 750, "Newton", "equatoriale"),
            Telescope("sct-203", "Schmidt-Cassegrain 203/2032", 203, 2032, "Schmidt-Cassegrain", "GoTo"),
            Telescope("mak-127", "Maksutov 127/1500", 127, 1500, "Maksutov", "altazimutale GoTo"),
        ]

    def default_eyepieces(self) -> list[Eyepiece]:
        return [
            Eyepiece("plossl-25", "Plossl 25 mm", 25.0, 52.0),
            Eyepiece("wide-15", "Grandangolare 15 mm", 15.0, 68.0),
            Eyepiece("planetary-10", "Planetario 10 mm", 10.0, 60.0),
            Eyepiece("planetary-6", "Planetario 6 mm", 6.0, 58.0),
        ]

    def calculations(self, telescope: Telescope, eyepieces: list[Eyepiece], barlow: float) -> list[dict]:
        rows = []
        for eyepiece in eyepieces:
            magnification = (telescope.focal_length_mm / eyepiece.focal_length_mm) * barlow
            true_field = eyepiece.apparent_field_deg / magnification
            exit_pupil = telescope.aperture_mm / magnification
            rows.append(
                {
                    "eyepiece": eyepiece.name,
                    "magnification": f"{magnification:.0f}x",
                    "trueField": f"{true_field:.2f} gradi",
                    "exitPupil": f"{exit_pupil:.1f} mm",
                    "barlow": f"{barlow:g}x",
                }
            )
        return rows

    def suggest_for_object(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
    ) -> dict:
        """Return a practical eyepiece/Barlow suggestion for the selected setup."""

        lower_type = celestial_object.object_type.lower()
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        max_altitude = self._parse_altitude(celestial_object.max_altitude)

        if "pianeta" in lower_type or celestial_object.id in {"mars", "jupiter", "saturn"}:
            preferred = self._eyepiece_near(eyepieces, 10.0)
            barlow = "Barlow 2x" if telescope.aperture_mm >= 100 and max_altitude >= 25 else "No"
            difficulty = "Facile" if max_altitude >= 30 else "Media"
            alternative = self._eyepiece_near(eyepieces, 6.0).name
        elif "galaxy" in lower_type or "galassia" in lower_type:
            preferred = self._eyepiece_near(eyepieces, 25.0)
            barlow = "No"
            difficulty = "Media" if magnitude is not None and magnitude <= 9.0 and max_altitude >= 30 else "Difficile"
            alternative = self._eyepiece_near(eyepieces, 15.0).name
        elif "globular" in lower_type or "ammasso globulare" in lower_type:
            preferred = self._eyepiece_near(eyepieces, 25.0)
            barlow = "No"
            difficulty = "Facile" if magnitude is not None and magnitude <= 7.0 and max_altitude >= 35 else "Media"
            alternative = self._eyepiece_near(eyepieces, 10.0).name
        elif "open" in lower_type or "ammasso aperto" in lower_type:
            preferred = self._eyepiece_near(eyepieces, 25.0)
            barlow = "No"
            difficulty = "Facile"
            alternative = "Binocolo 10x50"
        else:
            preferred = self._eyepiece_near(eyepieces, 15.0)
            barlow = "No"
            difficulty = "Media" if max_altitude >= 25 else "Difficile"
            alternative = self._eyepiece_near(eyepieces, 25.0).name

        return {
            "bestEyepiece": preferred.name,
            "barlow": barlow,
            "difficulty": difficulty,
            "alternative": alternative,
            "setupText": f"{preferred.name}" + (f" + {barlow}" if barlow != "No" else ""),
        }

    @staticmethod
    def _eyepiece_near(eyepieces: list[Eyepiece], focal_length_mm: float) -> Eyepiece:
        return min(eyepieces, key=lambda eyepiece: abs(eyepiece.focal_length_mm - focal_length_mm))

    @staticmethod
    def _parse_magnitude(value: str) -> float | None:
        try:
            return float(value.split("/")[0].strip().replace(",", "."))
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse_altitude(value: str) -> float:
        try:
            return float(value.split()[0].replace(",", "."))
        except (ValueError, IndexError):
            return 0.0
