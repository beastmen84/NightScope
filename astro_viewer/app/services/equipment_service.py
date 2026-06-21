from __future__ import annotations

from astro_viewer.app.models.equipment import Barlow, BeginnerPreset, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject


class EquipmentService:
    NAKED_EYE_ID = "preset:naked-eye"

    def naked_eye_telescope(self) -> Telescope:
        return Telescope(self.NAKED_EYE_ID, "Occhio nudo", 0, 0, "Occhio nudo", "nessuna")

    def beginner_presets(self) -> list[BeginnerPreset]:
        return [
            BeginnerPreset("naked-eye", "Occhio nudo", "Costellazioni e meteore", "Nessuna configurazione richiesta.", "Luna, Venere, Giove, sciami meteorici"),
            BeginnerPreset("binoculars", "Binocolo 10x50", "Ammassi aperti e Luna", "Campo ampio e uso immediato.", "M31, Pleiadi, Luna crescente"),
            BeginnerPreset("small-scope", "Telescopio piccolo", "Luna, pianeti luminosi, stelle doppie", "Rifrattore o Maksutov fino a 90 mm.", "Giove, Saturno, Albireo"),
            BeginnerPreset("medium-scope", "Telescopio medio", "Pianeti e deep sky brillante", "Strumento versatile da 130-200 mm.", "M13, M57, nebulose luminose"),
            BeginnerPreset("large-scope", "Telescopio grande", "Oggetti deboli e dettagli planetari", "Richiede seeing e acclimatazione accurati.", "Galassie, nebulose planetarie, globulari risolti"),
        ]

    def default_telescopes(self) -> list[Telescope]:
        return []

    def default_eyepieces(self) -> list[Eyepiece]:
        return [
            Eyepiece("plossl-25", "Plossl 25 mm", 25.0, 52.0),
            Eyepiece("wide-15", "Grandangolare 15 mm", 15.0, 68.0),
            Eyepiece("planetary-10", "Planetario 10 mm", 10.0, 60.0),
            Eyepiece("planetary-6", "Planetario 6 mm", 6.0, 58.0),
        ]

    def calculations(self, telescope: Telescope, eyepieces: list[Eyepiece], barlow: float) -> list[dict]:
        if not self.has_optical_telescope(telescope) or not eyepieces:
            return []
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

    def telescope_capabilities(self, telescope: Telescope) -> dict:
        if not self.has_optical_telescope(telescope):
            return {
                "name": telescope.name,
                "aperture": "n/d",
                "focalLength": "n/d",
                "practicalMagnification": "n/d",
                "lightGathering": "1x occhio",
                "limitingMagnitude": "n/d",
                "resolution": "n/d",
            }
        min_magnification = max(1, round(telescope.aperture_mm / 5))
        max_magnification = max(min_magnification, round(telescope.aperture_mm * 2))
        light_gathering = round((telescope.aperture_mm / 7.0) ** 2)
        limiting_magnitude = 2 + 5 * self._log10(max(1.0, telescope.aperture_mm))
        resolution = 116 / telescope.aperture_mm
        return {
            "name": telescope.name,
            "aperture": f"{telescope.aperture_mm} mm",
            "focalLength": f"{telescope.focal_length_mm} mm",
            "practicalMagnification": f"{min_magnification}x - {max_magnification}x",
            "lightGathering": f"{light_gathering}x occhio",
            "limitingMagnitude": f"{limiting_magnitude:.1f} stimata",
            "resolution": f"{resolution:.2f}\" stimata",
        }

    def suggest_for_object(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
        barlows: list[Barlow] | None = None,
    ) -> dict:
        """Return a practical eyepiece/Barlow suggestion for the selected setup."""

        if not self.has_optical_telescope(telescope):
            return self._naked_eye_suggestion(celestial_object)
        if not eyepieces:
            return {
                "bestEyepiece": "",
                "barlow": "No",
                "difficulty": self._difficulty_without_eyepieces(celestial_object),
                "alternative": "Aggiungi oculari al profilo",
                "setupText": "Aggiungi oculari per suggerimenti completi",
                "setupOptions": [],
                "explanation": "Telescopio presente, ma nessun oculare configurato.",
            }

        barlows = barlows or []
        combinations = self._ranked_combinations(celestial_object, telescope, eyepieces, barlows)
        if not combinations:
            return {
                "bestEyepiece": "",
                "barlow": "No",
                "difficulty": "Difficile",
                "alternative": "Nessuna combinazione utile",
                "setupText": "Aggiungi oculari adatti al profilo",
                "setupOptions": [],
                "explanation": "Le combinazioni disponibili superano i limiti pratici dello strumento.",
            }

        recommended = self._recommended_combination(combinations)
        options = self._option_set(combinations, recommended)
        difficulty = self._difficulty_for_object(celestial_object, telescope)
        setup_options = [self._combo_to_option(role, combo) for role, combo in options]
        alternative = next((option for option in setup_options if option["role"] == "Alternativa"), None)
        return {
            "bestEyepiece": recommended["eyepiece"].name,
            "barlow": recommended["barlow_label"],
            "difficulty": difficulty,
            "alternative": alternative["label"] if alternative else "n/d",
            "highMagnification": next((option["label"] for option in setup_options if option["role"] == "Alto ingrandimento"), ""),
            "wideField": next((option["label"] for option in setup_options if option["role"] == "Campo largo"), ""),
            "setupText": recommended["label"],
            "setupOptions": setup_options,
            "explanation": self._equipment_explanation(celestial_object, recommended),
        }

    def _ranked_combinations(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
    ) -> list[dict]:
        profile = self._target_profile(celestial_object, telescope)
        combinations = []
        for eyepiece in eyepieces:
            for barlow in self._barlow_options(barlows):
                multiplier = barlow.multiplier if barlow else 1.0
                magnification = (telescope.focal_length_mm / eyepiece.focal_length_mm) * multiplier
                if magnification <= 0:
                    continue
                true_field = eyepiece.apparent_field_deg / magnification
                exit_pupil = telescope.aperture_mm / magnification
                score = self._combination_score(profile, magnification, true_field, exit_pupil, multiplier)
                combinations.append(
                    {
                        "eyepiece": eyepiece,
                        "barlow": barlow,
                        "barlow_label": barlow.name if barlow else "No",
                        "multiplier": multiplier,
                        "magnification": magnification,
                        "true_field": true_field,
                        "exit_pupil": exit_pupil,
                        "score": score,
                        "label": eyepiece.name + (f" + {barlow.name}" if barlow else ""),
                    }
                )
        return sorted(combinations, key=lambda item: item["score"], reverse=True)

    @staticmethod
    def _barlow_options(barlows: list[Barlow]) -> list[Barlow | None]:
        owned = [barlow for barlow in barlows if barlow.multiplier > 1.0]
        return [None, *owned]

    def _recommended_combination(self, combinations: list[dict]) -> dict:
        best = combinations[0]
        if best["multiplier"] <= 1.0:
            return best
        best_without_barlow = next((combo for combo in combinations if combo["multiplier"] <= 1.0), None)
        if best_without_barlow and best["score"] <= best_without_barlow["score"] + 8:
            return best_without_barlow
        return best

    def _option_set(self, combinations: list[dict], recommended: dict) -> list[tuple[str, dict]]:
        options: list[tuple[str, dict]] = [("Consigliato", recommended)]
        alternative = self._first_distinct(combinations, options)
        if alternative:
            options.append(("Alternativa", alternative))
        options.append(("Alto ingrandimento", max(combinations, key=lambda item: item["magnification"])))
        options.append(("Campo largo", max(combinations, key=lambda item: item["true_field"])))
        return options

    @staticmethod
    def _first_distinct(candidates: list[dict], selected: list[tuple[str, dict]]) -> dict | None:
        selected_labels = {combo["label"] for _, combo in selected}
        for candidate in candidates:
            if candidate["label"] not in selected_labels:
                return candidate
        return None

    @staticmethod
    def _combo_to_option(role: str, combo: dict) -> dict:
        return {
            "role": role,
            "label": combo["label"],
            "magnification": f"{combo['magnification']:.0f}x",
            "trueField": f"{combo['true_field']:.2f} gradi",
            "exitPupil": f"{combo['exit_pupil']:.1f} mm",
            "barlow": combo["barlow_label"],
            "score": round(combo["score"]),
        }

    def _target_profile(self, celestial_object: CelestialObject, telescope: Telescope) -> dict:
        lower_type = celestial_object.object_type.lower()
        max_altitude = self._parse_altitude(celestial_object.max_altitude)
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        size_arcmin = self._parse_apparent_size(celestial_object.apparent_size)
        practical_max = max(30.0, telescope.aperture_mm * 2.0)
        altitude_factor = 1.0 if max_altitude >= 35 else 0.75 if max_altitude >= 20 else 0.55
        if "pianeta" in lower_type or celestial_object.id in {"mars", "jupiter", "saturn", "mercury", "venus"}:
            ideal_magnification = min(practical_max * 0.82, 190.0) * altitude_factor
            return {"mode": "high", "idealMag": max(65.0, ideal_magnification), "idealExit": 1.0, "idealField": 0.18, "barlowFriendly": True}
        if celestial_object.id == "moon" or "luna" in lower_type:
            return {"mode": "balanced", "idealMag": min(practical_max * 0.55, 120.0), "idealExit": 1.8, "idealField": 0.75, "barlowFriendly": False}
        if "globular" in lower_type or "ammasso globulare" in lower_type:
            return {"mode": "high", "idealMag": min(practical_max * 0.65, 135.0), "idealExit": 1.5, "idealField": 0.35, "barlowFriendly": False}
        if "planetary nebula" in lower_type or "nebulosa planetaria" in lower_type:
            return {"mode": "high", "idealMag": min(practical_max * 0.7, 155.0), "idealExit": 1.2, "idealField": 0.25, "barlowFriendly": True}
        if "open" in lower_type or "ammasso aperto" in lower_type:
            desired_field = max(0.9, min(3.0, (size_arcmin or 45.0) / 45.0))
            return {"mode": "wide", "idealMag": 28.0, "idealExit": 4.2, "idealField": desired_field, "barlowFriendly": False}
        if "galaxy" in lower_type or "galassia" in lower_type:
            ideal_mag = 58.0 if magnitude is None or magnitude > 8.0 else 72.0
            return {"mode": "balanced", "idealMag": min(practical_max * 0.45, ideal_mag), "idealExit": 2.2, "idealField": max(0.45, min(1.5, (size_arcmin or 20.0) / 35.0)), "barlowFriendly": False}
        if "nebula" in lower_type or "nebul" in lower_type:
            return {"mode": "wide", "idealMag": 48.0, "idealExit": 3.0, "idealField": max(0.75, min(2.5, (size_arcmin or 35.0) / 35.0)), "barlowFriendly": False}
        return {"mode": "balanced", "idealMag": 70.0, "idealExit": 2.0, "idealField": 0.6, "barlowFriendly": False}

    @staticmethod
    def _combination_score(profile: dict, magnification: float, true_field: float, exit_pupil: float, multiplier: float) -> float:
        score = 100.0
        score -= min(70.0, abs(magnification - profile["idealMag"]) / max(profile["idealMag"], 1.0) * 70.0)
        score -= min(35.0, abs(exit_pupil - profile["idealExit"]) / max(profile["idealExit"], 0.1) * 22.0)
        if profile["mode"] == "wide":
            if true_field < profile["idealField"]:
                score -= min(45.0, (profile["idealField"] - true_field) / profile["idealField"] * 55.0)
            else:
                score += min(12.0, true_field / profile["idealField"] * 4.0)
        elif true_field < profile["idealField"]:
            score -= min(20.0, (profile["idealField"] - true_field) / profile["idealField"] * 20.0)
        if exit_pupil < 0.45:
            score -= 28.0
        elif exit_pupil > 6.0:
            score -= 22.0
        if multiplier > 1.0 and not profile["barlowFriendly"]:
            score -= 18.0
            if profile["mode"] == "wide":
                score -= 16.0
        elif multiplier > 1.0:
            score -= 4.0
        return max(0.0, score)

    def _difficulty_for_object(self, celestial_object: CelestialObject, telescope: Telescope) -> str:
        lower_type = celestial_object.object_type.lower()
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        max_altitude = self._parse_altitude(celestial_object.max_altitude)
        if max_altitude < 15:
            return "Difficile"
        if "pianeta" in lower_type or celestial_object.id in {"moon", "venus", "jupiter", "saturn"}:
            return "Facile" if telescope.aperture_mm >= 80 and max_altitude >= 25 else "Media"
        if "galaxy" in lower_type or "nebula" in lower_type or "nebul" in lower_type:
            if telescope.aperture_mm < 120 or (magnitude is not None and magnitude > 9.0):
                return "Difficile"
            return "Media"
        if magnitude is not None and magnitude <= 7.5 and max_altitude >= 30:
            return "Facile"
        return "Media"

    @staticmethod
    def _equipment_explanation(celestial_object: CelestialObject, combination: dict) -> str:
        parts = [
            f"{combination['magnification']:.0f}x con pupilla {combination['exit_pupil']:.1f} mm",
            f"campo reale {combination['true_field']:.2f} gradi",
        ]
        if combination["multiplier"] > 1.0:
            parts.append("Barlow usata per aumentare l'ingrandimento utile")
        else:
            parts.append("senza Barlow per mantenere contrasto e campo")
        max_altitude = EquipmentService._parse_altitude(celestial_object.max_altitude)
        if max_altitude > 0:
            parts.append(f"altezza massima {max_altitude:.0f} gradi")
        return "; ".join(parts) + "."

    def has_optical_telescope(self, telescope: Telescope) -> bool:
        return telescope.id != self.NAKED_EYE_ID and telescope.aperture_mm > 0 and telescope.focal_length_mm > 0

    def can_use_eyepieces(self, telescope: Telescope) -> bool:
        return self.has_optical_telescope(telescope)

    def _naked_eye_suggestion(self, celestial_object: CelestialObject) -> dict:
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        lower_type = celestial_object.object_type.lower()
        naked_eye_realistic = (
            celestial_object.id in {"moon", "mercury", "venus", "mars", "jupiter", "saturn"}
            or magnitude is not None
            and magnitude <= 5.5
            and not any(fragment in lower_type for fragment in ("galaxy", "nebula", "globular"))
        )
        return {
            "bestEyepiece": "",
            "barlow": "No",
            "difficulty": "Facile" if naked_eye_realistic else "Non adatto a occhio nudo",
            "alternative": "Binocolo o telescopio consigliato" if not naked_eye_realistic else "Occhio nudo",
            "setupText": "Occhio nudo" if naked_eye_realistic else "Serve almeno un binocolo o telescopio",
            "setupOptions": [],
            "explanation": "Oggetto compatibile con osservazione a occhio nudo." if naked_eye_realistic else "Target non realistico senza strumento ottico.",
        }

    def _difficulty_without_eyepieces(self, celestial_object: CelestialObject) -> str:
        lower_type = celestial_object.object_type.lower()
        if celestial_object.id in {"moon", "venus", "jupiter", "saturn"}:
            return "Limitata"
        if "galaxy" in lower_type or "nebula" in lower_type:
            return "Difficile"
        return "Media"

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

    @staticmethod
    def _parse_apparent_size(value: str) -> float | None:
        if not value:
            return None
        cleaned = value.lower().replace("arcmin", "'").replace("′", "'").replace("x", " ")
        numbers = []
        for token in cleaned.replace(",", ".").replace("'", " ").replace('"', " ").split():
            try:
                numbers.append(float(token))
            except ValueError:
                continue
        if not numbers:
            return None
        return max(numbers)

    @staticmethod
    def _log10(value: float) -> float:
        import math

        return math.log10(value)
