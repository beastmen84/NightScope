from __future__ import annotations

from astro_viewer.app.models.equipment import Barlow, BeginnerPreset, Eyepiece, Telescope
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality


class EquipmentService:
    NAKED_EYE_ID = "preset:naked-eye"

    def naked_eye_telescope(self) -> Telescope:
        return Telescope(self.NAKED_EYE_ID, "Occhio nudo", 0, 0, "Occhio nudo", "nessuna")

    def beginner_presets(self) -> list[BeginnerPreset]:
        return [
            BeginnerPreset("naked-eye", "Occhio nudo", "Costellazioni e meteore", "Nessuna configurazione richiesta.", "Luna, Venere, Giove, sciami meteorici"),
            BeginnerPreset("binoculars", "Binocolo 10x50", "Ammassi aperti e Luna", "Campo ampio e uso immediato.", "M31, Pleiadi, Luna crescente"),
            BeginnerPreset("small-scope", "Telescopio piccolo", "Luna, pianeti luminosi, stelle doppie", "Rifrattore o Maksutov fino a 90 mm.", "Giove, Saturno, Albireo"),
            BeginnerPreset("medium-scope", "Telescopio medio", "Pianeti e cielo profondo brillante", "Strumento versatile da 130-200 mm.", "M13, M57, nebulose luminose"),
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
            for focal_position in self.eyepiece_focal_positions(eyepiece):
                values = self.telescope_configuration_values(
                    telescope,
                    eyepiece,
                    focal_position["focal"],
                    barlow_multiplier=barlow,
                )
                rows.append(
                    {
                        "eyepiece": eyepiece.name if eyepiece.eyepiece_type != "Zoom" else f"{eyepiece.name} @ {focal_position['position']}",
                        "magnification": f"{values['magnification']:.0f}x",
                        "trueField": f"{values['true_field_of_view_deg']:.2f} gradi",
                        "exitPupil": f"{values['exit_pupil_mm']:.1f} mm",
                        "barlow": f"{barlow:g}x",
                    }
                )
        return rows

    def barlow_options(self, barlows: list[Barlow]) -> list[Barlow | None]:
        return self._barlow_options(barlows)

    def eyepiece_focal_positions(self, eyepiece: Eyepiece, ideal_focal_mm: float | None = None) -> list[dict]:
        return self._eyepiece_focal_positions(
            eyepiece,
            eyepiece.focal_length_mm if ideal_focal_mm is None else ideal_focal_mm,
        )

    def telescope_configuration_values(
        self,
        telescope: Telescope,
        eyepiece: Eyepiece,
        focal_mm: float,
        barlow: Barlow | None = None,
        barlow_multiplier: float | None = None,
    ) -> dict[str, float]:
        multiplier = barlow_multiplier if barlow_multiplier is not None else (barlow.multiplier if barlow else 1.0)
        magnification = (telescope.focal_length_mm / focal_mm) * multiplier
        true_field = eyepiece.apparent_field_deg / magnification
        exit_pupil = telescope.aperture_mm / magnification
        limiting_magnitude = 2 + 5 * self._log10(max(1.0, telescope.aperture_mm))
        resolution = 116 / telescope.aperture_mm
        return {
            "magnification": magnification,
            "true_field_of_view_deg": true_field,
            "exit_pupil_mm": exit_pupil,
            "limiting_magnitude_estimate": limiting_magnitude,
            "resolution_estimate": resolution,
        }

    def telescope_capabilities(self, telescope: Telescope) -> dict:
        return self.profile_capabilities(telescope, [], [])

    def profile_capabilities(self, telescope: Telescope, eyepieces: list[Eyepiece], barlows: list[Barlow]) -> dict:
        if not self.has_optical_telescope(telescope):
            return {
                "name": telescope.name,
                "aperture": "n/d",
                "focalLength": "n/d",
                "practicalMagnification": "n/d",
                "availableMagnificationMin": "n/d",
                "availableMagnificationMax": "n/d",
                "exitPupilMin": "n/d",
                "exitPupilMax": "n/d",
                "trueFieldMin": "n/d",
                "trueFieldMax": "n/d",
                "lightGathering": "1x occhio",
                "limitingMagnitude": "n/d",
                "resolution": "n/d",
                "availableConfigurations": [],
                "availableConfigurationsText": "Aggiungi attrezzatura al profilo",
            }
        min_magnification = max(1, round(telescope.aperture_mm / 5))
        max_magnification = max(min_magnification, round(telescope.aperture_mm * 2))
        light_gathering = round((telescope.aperture_mm / 7.0) ** 2)
        limiting_magnitude = 2 + 5 * self._log10(max(1.0, telescope.aperture_mm))
        resolution = 116 / telescope.aperture_mm
        configurations = self._available_configurations(telescope, eyepieces, barlows)
        magnifications = [item["magnificationValue"] for item in configurations]
        exit_pupils = [item["exitPupilValue"] for item in configurations]
        true_fields = [item["trueFieldValue"] for item in configurations]
        return {
            "name": telescope.name,
            "aperture": f"{telescope.aperture_mm} mm",
            "focalLength": f"{telescope.focal_length_mm} mm",
            "practicalMagnification": f"{min_magnification}x - {max_magnification}x",
            "availableMagnificationMin": f"{min(magnifications):.0f}x" if magnifications else "n/d",
            "availableMagnificationMax": f"{max(magnifications):.0f}x" if magnifications else "n/d",
            "exitPupilMin": f"{min(exit_pupils):.1f} mm" if exit_pupils else "n/d",
            "exitPupilMax": f"{max(exit_pupils):.1f} mm" if exit_pupils else "n/d",
            "trueFieldMin": f"{min(true_fields):.2f} gradi" if true_fields else "n/d",
            "trueFieldMax": f"{max(true_fields):.2f} gradi" if true_fields else "n/d",
            "lightGathering": f"{light_gathering}x occhio",
            "limitingMagnitude": f"{limiting_magnitude:.1f} stimata",
            "resolution": f"{resolution:.2f}\" stimata",
            "availableConfigurations": configurations,
            "availableConfigurationsText": ", ".join(item["magnification"] for item in configurations[:12]) if configurations else "Aggiungi oculari al profilo",
        }

    def suggest_for_object(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
        barlows: list[Barlow] | None = None,
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> dict:
        """Return a practical eyepiece/Barlow suggestion for the selected setup."""

        if not self.has_optical_telescope(telescope):
            return self._naked_eye_suggestion(celestial_object)
        if not eyepieces:
            return {
                "bestEyepiece": "",
                "suggestedPosition": "",
                "barlow": "No",
                "difficulty": self._difficulty_without_eyepieces(celestial_object),
                "alternative": "Aggiungi oculari al profilo",
                "setupText": "Aggiungi oculari per suggerimenti completi",
                "setupOptions": [],
                "explanation": "Telescopio presente, ma nessun oculare configurato.",
                "telescopeId": telescope.id,
                "telescopeName": telescope.name,
                "selectionScore": 12.0,
            }

        barlows = barlows or []
        combinations = self._ranked_combinations(celestial_object, telescope, eyepieces, barlows, seeing, sky_quality)
        if not combinations:
            return {
                "bestEyepiece": "",
                "suggestedPosition": "",
                "barlow": "No",
                "difficulty": "Difficile",
                "alternative": "Nessuna combinazione utile",
                "setupText": "Aggiungi oculari adatti al profilo",
                "setupOptions": [],
                "explanation": "Le combinazioni disponibili superano i limiti pratici dello strumento.",
                "telescopeId": telescope.id,
                "telescopeName": telescope.name,
                "selectionScore": 8.0,
            }

        recommended = self._recommended_combination(combinations)
        options = self._option_set(combinations, recommended)
        difficulty = self._difficulty_for_object(celestial_object, telescope, sky_quality)
        setup_options = [self._combo_to_option(role, combo) for role, combo in options]
        alternative = next((option for option in setup_options if option["role"] == "Alternativa"), None)
        return {
            "bestEyepiece": recommended["eyepiece"].name,
            "suggestedPosition": recommended["focal_position"],
            "barlow": recommended["barlow_label"],
            "difficulty": difficulty,
            "alternative": alternative["detailLabel"] if alternative else "n/d",
            "highMagnification": next((option["detailLabel"] for option in setup_options if option["role"] == "Alto ingrandimento"), ""),
            "wideField": next((option["detailLabel"] for option in setup_options if option["role"] == "Campo largo"), ""),
            "setupText": recommended["detail_label"],
            "setupOptions": setup_options,
            "explanation": self._equipment_explanation(celestial_object, recommended),
            "telescopeId": telescope.id,
            "telescopeName": telescope.name,
            "selectionScore": recommended["score"],
        }

    def suggest_for_profile(
        self,
        celestial_object: CelestialObject,
        telescopes: list[Telescope],
        eyepieces: list[Eyepiece],
        barlows: list[Barlow] | None = None,
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> dict:
        usable_telescopes = [telescope for telescope in telescopes if self.has_optical_telescope(telescope)]
        if not usable_telescopes:
            return self._naked_eye_suggestion(celestial_object)

        suggestions = [
            self.suggest_for_object(celestial_object, telescope, eyepieces, barlows or [], seeing, sky_quality)
            for telescope in usable_telescopes
        ]
        best = max(suggestions, key=lambda item: item.get("selectionScore", 0.0))
        setup_text = best.get("setupText", "").strip()
        if setup_text and not setup_text.startswith(("Aggiungi", "Serve almeno")):
            best = {**best, "setupText": f"{best['telescopeName']} + {setup_text}"}
        return best

    def _ranked_combinations(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> list[dict]:
        from astro_viewer.app.services.observation_configuration_builder import ObservationConfigurationBuilder

        profile = self._target_profile(celestial_object, telescope, seeing, sky_quality)
        combinations = []

        def focal_position_provider(candidate_telescope: Telescope, eyepiece: Eyepiece, barlow: Barlow | None) -> list[dict]:
            multiplier = barlow.multiplier if barlow else 1.0
            ideal_focal = candidate_telescope.focal_length_mm * multiplier / max(profile["idealMag"], 1.0)
            return self.eyepiece_focal_positions(eyepiece, ideal_focal)

        configurations = ObservationConfigurationBuilder(self).build_telescope_configurations(
            [telescope],
            eyepieces,
            barlows,
            focal_position_provider,
        )
        for configuration in configurations:
            combination = self._configuration_to_combination(configuration, celestial_object, profile, sky_quality)
            if combination:
                combinations.append(combination)
        return sorted(combinations, key=lambda item: item["score"], reverse=True)

    def _configuration_to_combination(
        self,
        configuration: ObservationConfiguration,
        celestial_object: CelestialObject,
        profile: dict,
        sky_quality: SkyQuality | None,
    ) -> dict | None:
        if not configuration.telescope or not configuration.eyepiece:
            return None
        if configuration.true_field_of_view_deg is None or configuration.focal_position_mm is None:
            return None
        magnification = configuration.magnification
        if magnification <= 0:
            return None
        telescope = configuration.telescope
        eyepiece = configuration.eyepiece
        barlow = configuration.barlow
        multiplier = barlow.multiplier if barlow else 1.0
        true_field = configuration.true_field_of_view_deg
        exit_pupil = configuration.exit_pupil_mm
        score = self._combination_score(profile, magnification, true_field, exit_pupil, multiplier)
        score += self._telescope_suitability_score(celestial_object, telescope, sky_quality)
        label = eyepiece.name + (f" + {barlow.name}" if barlow else "")
        detail_label = label
        if eyepiece.eyepiece_type == "Zoom":
            detail_label = f"{label} @ {configuration.focal_position_label}"
        return {
            "eyepiece": eyepiece,
            "barlow": barlow,
            "barlow_label": barlow.name if barlow else "No",
            "multiplier": multiplier,
            "focal_position": configuration.focal_position_label,
            "focal_mm": configuration.focal_position_mm,
            "magnification": magnification,
            "true_field": true_field,
            "exit_pupil": exit_pupil,
            "score": score,
            "label": label,
            "detail_label": detail_label,
            "telescope_name": telescope.name,
        }

    @staticmethod
    def _barlow_options(barlows: list[Barlow]) -> list[Barlow | None]:
        owned = [barlow for barlow in barlows if barlow.multiplier > 1.0]
        return [None, *owned]

    def _available_configurations(self, telescope: Telescope, eyepieces: list[Eyepiece], barlows: list[Barlow]) -> list[dict]:
        if not eyepieces:
            return []
        configurations = []
        seen = set()
        for eyepiece in eyepieces:
            for barlow in self.barlow_options(barlows):
                multiplier = barlow.multiplier if barlow else 1.0
                for focal_position in self.eyepiece_focal_positions(eyepiece):
                    values = self.telescope_configuration_values(telescope, eyepiece, focal_position["focal"], barlow)
                    magnification = round(values["magnification"])
                    key = (eyepiece.id, focal_position["position"], multiplier, magnification)
                    if key in seen:
                        continue
                    seen.add(key)
                    configurations.append(
                        {
                            "label": eyepiece.name + (f" @ {focal_position['position']}" if eyepiece.eyepiece_type == "Zoom" else ""),
                            "magnification": f"{magnification}x",
                            "magnificationValue": float(magnification),
                            "trueFieldValue": eyepiece.apparent_field_deg / max(magnification, 1),
                            "exitPupilValue": telescope.aperture_mm / max(magnification, 1),
                            "barlow": barlow.name if barlow else "No",
                        }
                    )
        return sorted(configurations, key=lambda item: int(item["magnification"].replace("x", "")))

    @staticmethod
    def _eyepiece_focal_positions(eyepiece: Eyepiece, ideal_focal_mm: float) -> list[dict]:
        if eyepiece.eyepiece_type != "Zoom":
            return [{"focal": eyepiece.focal_length_mm, "position": f"{eyepiece.focal_length_mm:g} mm"}]
        minimum = eyepiece.min_focal_length_mm or min(eyepiece.focal_length_mm, eyepiece.max_focal_length_mm or eyepiece.focal_length_mm)
        maximum = eyepiece.max_focal_length_mm or max(eyepiece.focal_length_mm, minimum)
        low = min(minimum, maximum)
        high = max(minimum, maximum)
        clamped = max(low, min(high, ideal_focal_mm))
        candidates = [clamped, low, high, (low + high) / 2]
        positions = []
        seen = set()
        for value in candidates:
            rounded = round(value, 1)
            key = round(rounded, 1)
            if key in seen:
                continue
            seen.add(key)
            positions.append({"focal": rounded, "position": f"{rounded:g} mm"})
        return positions

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
        selected_labels = {combo["detail_label"] for _, combo in selected}
        for candidate in candidates:
            if candidate["detail_label"] not in selected_labels:
                return candidate
        return None

    @staticmethod
    def _combo_to_option(role: str, combo: dict) -> dict:
        return {
            "role": role,
            "label": combo["label"],
            "detailLabel": combo["detail_label"],
            "suggestedPosition": combo["focal_position"],
            "magnification": f"{combo['magnification']:.0f}x",
            "trueField": f"{combo['true_field']:.2f} gradi",
            "exitPupil": f"{combo['exit_pupil']:.1f} mm",
            "barlow": combo["barlow_label"],
            "score": max(0, min(100, round(combo["score"]))),
            "telescopeName": combo.get("telescope_name", ""),
        }

    def _target_profile(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> dict:
        lower_type = celestial_object.object_type.lower()
        max_altitude = self._parse_altitude(celestial_object.max_altitude)
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        size_arcmin = self._parse_apparent_size(celestial_object.apparent_size)
        max_useful_magnification = self._seeing_limited_magnification(telescope, seeing)
        practical_max = max(30.0, max_useful_magnification)
        altitude_factor = 1.0 if max_altitude >= 35 else 0.75 if max_altitude >= 20 else 0.55
        if "pianeta" in lower_type or celestial_object.id in {"mars", "jupiter", "saturn", "mercury", "venus"}:
            ideal_magnification = min(practical_max * 0.82, 190.0) * altitude_factor
            return {
                "mode": "high",
                "idealMag": max(55.0, ideal_magnification),
                "idealExit": 1.0,
                "idealField": 0.18,
                "barlowFriendly": True,
                "maxUsefulMag": max_useful_magnification,
            }
        if celestial_object.id == "moon" or "luna" in lower_type:
            return {"mode": "balanced", "idealMag": min(practical_max * 0.55, 120.0), "idealExit": 1.8, "idealField": 0.75, "barlowFriendly": False, "maxUsefulMag": max_useful_magnification}
        if "globular" in lower_type or "ammasso globulare" in lower_type:
            return {"mode": "high", "idealMag": min(practical_max * 0.65, 135.0), "idealExit": 1.5, "idealField": 0.35, "barlowFriendly": False, "maxUsefulMag": max_useful_magnification}
        if "planetary nebula" in lower_type or "nebulosa planetaria" in lower_type:
            return {"mode": "high", "idealMag": min(practical_max * 0.7, 155.0), "idealExit": 1.2, "idealField": 0.25, "barlowFriendly": True, "maxUsefulMag": max_useful_magnification}
        if "open" in lower_type or "ammasso aperto" in lower_type:
            desired_field = max(0.9, min(3.0, (size_arcmin or 45.0) / 45.0))
            return {"mode": "wide", "idealMag": 28.0, "idealExit": 4.2, "idealField": desired_field, "barlowFriendly": False, "maxUsefulMag": max_useful_magnification}
        if "galaxy" in lower_type or "galassia" in lower_type:
            ideal_mag = 58.0 if magnitude is None or magnitude > 8.0 else 72.0
            exit_pupil = 2.8 if sky_quality and sky_quality.bortle_class >= 7 else 2.2
            return {"mode": "balanced", "idealMag": min(practical_max * 0.45, ideal_mag), "idealExit": exit_pupil, "idealField": max(0.45, min(1.5, (size_arcmin or 20.0) / 35.0)), "barlowFriendly": False, "maxUsefulMag": max_useful_magnification}
        if "nebula" in lower_type or "nebul" in lower_type:
            exit_pupil = 3.8 if sky_quality and sky_quality.bortle_class >= 7 else 3.0
            return {"mode": "wide", "idealMag": 48.0, "idealExit": exit_pupil, "idealField": max(0.75, min(2.5, (size_arcmin or 35.0) / 35.0)), "barlowFriendly": False, "maxUsefulMag": max_useful_magnification}
        return {"mode": "balanced", "idealMag": 70.0, "idealExit": 2.0, "idealField": 0.6, "barlowFriendly": False, "maxUsefulMag": max_useful_magnification}

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
        if magnification > profile.get("maxUsefulMag", magnification):
            score -= min(45.0, (magnification - profile["maxUsefulMag"]) / max(profile["maxUsefulMag"], 1.0) * 70.0)
        return max(0.0, score)

    def _difficulty_for_object(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        sky_quality: SkyQuality | None = None,
    ) -> str:
        lower_type = celestial_object.object_type.lower()
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        max_altitude = self._parse_altitude(celestial_object.max_altitude)
        if max_altitude < 15:
            return "Difficile"
        if "pianeta" in lower_type or celestial_object.id in {"moon", "venus", "jupiter", "saturn"}:
            return "Facile" if telescope.aperture_mm >= 80 and max_altitude >= 25 else "Media"
        if "galaxy" in lower_type or "nebula" in lower_type or "nebul" in lower_type:
            if sky_quality and sky_quality.bortle_class >= 8:
                return "Difficile"
            surface_brightness = self._surface_brightness_proxy(celestial_object)
            if sky_quality and sky_quality.bortle_class >= 7 and surface_brightness and surface_brightness >= 13.5:
                return "Difficile"
            if telescope.aperture_mm < 120 or (magnitude is not None and magnitude > 9.0):
                return "Difficile"
            return "Media"
        if magnitude is not None and magnitude <= 7.5 and max_altitude >= 30:
            return "Facile"
        return "Media"

    @staticmethod
    def _seeing_limited_magnification(telescope: Telescope, seeing: SeeingTransparency | None) -> float:
        theoretical = max(30.0, telescope.aperture_mm * 2.0)
        if not seeing:
            return theoretical
        score = seeing.seeing_score
        if score >= 82:
            return min(theoretical, 260.0)
        if score >= 65:
            return min(theoretical, 185.0, telescope.aperture_mm * 1.45)
        if score >= 42:
            return min(theoretical, 125.0, telescope.aperture_mm * 0.95)
        return min(theoretical, 85.0, telescope.aperture_mm * 0.6)

    def _telescope_suitability_score(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        sky_quality: SkyQuality | None = None,
    ) -> float:
        lower_type = celestial_object.object_type.lower()
        aperture = telescope.aperture_mm
        if "pianeta" in lower_type or celestial_object.id in {"mars", "jupiter", "saturn", "mercury", "venus", "moon"}:
            return min(18.0, aperture / 12.0)
        if "galaxy" in lower_type or "nebula" in lower_type or "nebul" in lower_type:
            bonus = min(24.0, aperture / 9.0)
            if sky_quality and sky_quality.bortle_class >= 7:
                bonus *= 0.7
            return bonus
        if "globular" in lower_type:
            return min(22.0, aperture / 9.5)
        if "open" in lower_type or "cluster" in lower_type:
            return min(12.0, aperture / 18.0)
        return min(14.0, aperture / 16.0)

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
            "suggestedPosition": "",
            "barlow": "No",
            "difficulty": "Facile" if naked_eye_realistic else "Non adatto a occhio nudo",
            "alternative": "Binocolo o telescopio consigliato" if not naked_eye_realistic else "Occhio nudo",
            "setupText": "Occhio nudo" if naked_eye_realistic else "Serve almeno un binocolo o telescopio",
            "setupOptions": [],
            "explanation": "Oggetto compatibile con osservazione a occhio nudo." if naked_eye_realistic else "Target non realistico senza strumento ottico.",
            "telescopeId": self.NAKED_EYE_ID,
            "telescopeName": "Occhio nudo",
            "selectionScore": 20.0 if naked_eye_realistic else 0.0,
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

    def _surface_brightness_proxy(self, celestial_object: CelestialObject) -> float | None:
        magnitude = self._parse_magnitude(celestial_object.magnitude)
        size_arcmin = self._parse_apparent_size(celestial_object.apparent_size)
        if magnitude is None or not size_arcmin or size_arcmin <= 0:
            return None
        area_arcmin2 = max(1.0, 3.14159 * (size_arcmin / 2.0) ** 2)
        return magnitude + 2.5 * self._log10(area_arcmin2)

    @staticmethod
    def _log10(value: float) -> float:
        import math

        return math.log10(value)
