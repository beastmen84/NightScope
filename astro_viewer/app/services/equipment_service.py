from __future__ import annotations

import math

from astro_viewer.app.models.equipment import Barlow, BeginnerPreset, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.recommendation_presenter import RecommendationPresenter


class EquipmentService:
    NAKED_EYE_ID = "preset:naked-eye"

    def __init__(self, presenter: RecommendationPresenter | None = None) -> None:
        self._presenter = presenter or RecommendationPresenter()

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
            return self._presenter.naked_eye(celestial_object, self.NAKED_EYE_ID)
        if not eyepieces:
            return self._presenter.missing_eyepieces(celestial_object, telescope)

        barlows = barlows or []
        candidates = self._ranked_candidates(celestial_object, telescope, eyepieces, barlows, seeing, sky_quality)
        if not candidates:
            return self._presenter.no_useful_configurations(telescope)

        recommended = self._recommended_candidate(candidates)
        return self._presenter.from_candidates(celestial_object, candidates, recommended, sky_quality)

    def suggest_for_profile(
        self,
        celestial_object: CelestialObject,
        telescopes: list[Telescope],
        eyepieces: list[Eyepiece],
        barlows: list[Barlow] | None = None,
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
        binoculars: list[Binocular] | None = None,
    ) -> dict:
        barlows = barlows or []
        binoculars = binoculars or []
        usable_telescopes = [telescope for telescope in telescopes if self.has_optical_telescope(telescope)]
        if not usable_telescopes and not binoculars:
            return self._presenter.naked_eye(celestial_object, self.NAKED_EYE_ID)

        if binoculars or (usable_telescopes and eyepieces):
            candidates = self._ranked_profile_candidates(
                celestial_object,
                usable_telescopes,
                eyepieces,
                barlows,
                binoculars,
                seeing,
                sky_quality,
            )
            if candidates:
                recommended = self._recommended_candidate(candidates)
                return self._presenter.from_candidates(
                    celestial_object,
                    candidates,
                    recommended,
                    sky_quality,
                    prefix_telescope=True,
                )

        if usable_telescopes:
            telescope = usable_telescopes[0]
            if not eyepieces:
                return self._presenter.missing_eyepieces(celestial_object, telescope)
            return self._presenter.no_useful_configurations(telescope)
        return self._presenter.naked_eye(celestial_object, self.NAKED_EYE_ID)

    def _ranked_profile_candidates(
        self,
        celestial_object: CelestialObject,
        telescopes: list[Telescope],
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
        binoculars: list[Binocular],
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> list[RecommendationCandidate]:
        from astro_viewer.app.services.observation_configuration_builder import ObservationConfigurationBuilder

        profiles: dict[str, dict] = {}

        def profile_for(telescope: Telescope) -> dict:
            if telescope.id not in profiles:
                profiles[telescope.id] = self._target_profile(celestial_object, telescope, seeing, sky_quality)
            return profiles[telescope.id]

        def focal_position_provider(candidate_telescope: Telescope, eyepiece: Eyepiece, barlow: Barlow | None) -> list[dict]:
            profile = profile_for(candidate_telescope)
            multiplier = barlow.multiplier if barlow else 1.0
            ideal_focal = candidate_telescope.focal_length_mm * multiplier / max(profile["idealMag"], 1.0)
            return self.eyepiece_focal_positions(eyepiece, ideal_focal)

        configurations = ObservationConfigurationBuilder(self).build(
            telescopes,
            eyepieces,
            barlows,
            binoculars,
            focal_position_provider,
        )
        candidates = []
        for configuration in configurations:
            if configuration.binocular:
                candidate = self._binocular_candidate(configuration, celestial_object, sky_quality)
            elif configuration.telescope:
                candidate = self._telescope_candidate(
                    configuration,
                    celestial_object,
                    profile_for(configuration.telescope),
                    sky_quality,
                )
            else:
                candidate = None
            if candidate:
                candidates.append(candidate)
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def _ranked_candidates(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> list[RecommendationCandidate]:
        from astro_viewer.app.services.observation_configuration_builder import ObservationConfigurationBuilder

        profile = self._target_profile(celestial_object, telescope, seeing, sky_quality)
        candidates = []

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
            candidate = self._telescope_candidate(configuration, celestial_object, profile, sky_quality)
            if candidate:
                candidates.append(candidate)
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def _telescope_candidate(
        self,
        configuration: ObservationConfiguration,
        celestial_object: CelestialObject,
        profile: dict,
        sky_quality: SkyQuality | None,
    ) -> RecommendationCandidate | None:
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
        score = self._configuration_score(
            TargetObservationTraits.from_object(celestial_object),
            configuration,
            profile,
            sky_quality,
            multiplier,
        )
        label = eyepiece.name + (f" + {barlow.name}" if barlow else "")
        detail_label = label
        if eyepiece.eyepiece_type == "Zoom":
            detail_label = f"{label} @ {configuration.focal_position_label}"
        return RecommendationCandidate(
            configuration=configuration,
            score=score,
            label=label,
            detail_label=detail_label,
            multiplier=multiplier,
            barlow_label=barlow.name if barlow else "No",
            telescope_name=telescope.name,
        )

    def _binocular_candidate(
        self,
        configuration: ObservationConfiguration,
        celestial_object: CelestialObject,
        sky_quality: SkyQuality | None,
    ) -> RecommendationCandidate | None:
        binocular = configuration.binocular
        if not binocular or configuration.magnification <= 0 or configuration.exit_pupil_mm <= 0:
            return None
        label = self._binocular_setup_label(binocular)
        traits = TargetObservationTraits.from_object(celestial_object)
        profile = self._binocular_target_profile(traits, sky_quality)
        return RecommendationCandidate(
            configuration=configuration,
            score=self._configuration_score(traits, configuration, profile, sky_quality),
            label=label,
            detail_label=label,
            multiplier=1.0,
            barlow_label="No",
        )

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

    def _recommended_candidate(self, candidates: list[RecommendationCandidate]) -> RecommendationCandidate:
        best = candidates[0]
        if best.equipment_type != "Telescope" or best.multiplier <= 1.0:
            return best
        best_without_barlow = next((candidate for candidate in candidates if candidate.multiplier <= 1.0), None)
        if best_without_barlow and best.score <= best_without_barlow.score + 8:
            return best_without_barlow
        return best

    def _target_profile(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> dict:
        traits = TargetObservationTraits.from_object(celestial_object)
        lower_type = traits.object_type_lower
        max_altitude = traits.max_altitude_deg
        magnitude = traits.magnitude
        size_arcmin = traits.profile_size_arcmin
        angular_size = traits.angular_size_deg
        has_observation_metadata = (
            celestial_object.recommended_observation_type.strip() in {"WideField", "General", "HighMagnification"}
            or traits.max_angular_size_deg is not None
        )
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
        if has_observation_metadata:
            if traits.is_wide_field:
                if angular_size and angular_size >= 2.5:
                    ideal_magnification = 24.0
                elif angular_size and angular_size >= 1.0:
                    ideal_magnification = 28.0
                elif angular_size and angular_size >= 0.4:
                    ideal_magnification = 36.0
                else:
                    ideal_magnification = 45.0
                desired_field = 1.2 if angular_size is None else max(0.9, min(3.2, angular_size * 1.1))
                ideal_exit = 3.8 if sky_quality and sky_quality.bortle_class >= 7 else 4.4
                return {
                    "mode": "wide",
                    "idealMag": min(ideal_magnification, practical_max * 0.45),
                    "idealExit": ideal_exit,
                    "idealField": desired_field,
                    "barlowFriendly": False,
                    "maxUsefulMag": max_useful_magnification,
                }
            if traits.is_high_magnification:
                if angular_size and angular_size < 0.05:
                    ideal_magnification = min(practical_max * 0.7, 155.0)
                    ideal_field = 0.22
                elif angular_size and angular_size < 0.12:
                    ideal_magnification = min(practical_max * 0.6, 130.0)
                    ideal_field = 0.32
                else:
                    ideal_magnification = min(practical_max * 0.5, 110.0)
                    ideal_field = 0.45
                return {
                    "mode": "high",
                    "idealMag": max(55.0, ideal_magnification * altitude_factor),
                    "idealExit": 1.2,
                    "idealField": ideal_field,
                    "barlowFriendly": True,
                    "maxUsefulMag": max_useful_magnification,
                }
            if traits.is_general:
                if angular_size and angular_size >= 0.18:
                    ideal_magnification = 55.0
                    ideal_field = max(0.55, min(1.6, angular_size * 1.4))
                    ideal_exit = 2.8
                elif angular_size and angular_size >= 0.08:
                    ideal_magnification = 58.0
                    ideal_field = max(0.45, min(1.2, angular_size * 1.5))
                    ideal_exit = 1.9
                elif angular_size and angular_size >= 0.03:
                    ideal_magnification = 78.0
                    ideal_field = 0.45
                    ideal_exit = 2.2
                else:
                    ideal_magnification = 88.0
                    ideal_field = 0.35
                    ideal_exit = 1.9
                if magnitude is not None and magnitude > 9.0 and angular_size and angular_size >= 0.03:
                    ideal_magnification = min(ideal_magnification, 65.0)
                    ideal_exit = max(ideal_exit, 2.8)
                if "globular" in lower_type or "ammasso globulare" in lower_type:
                    ideal_magnification = min(ideal_magnification + 8.0, 85.0)
                    ideal_exit = min(ideal_exit, 2.2)
                return {
                    "mode": "balanced",
                    "idealMag": min(practical_max * 0.95, ideal_magnification) * altitude_factor,
                    "idealExit": ideal_exit,
                    "idealField": ideal_field,
                    "barlowFriendly": False,
                    "maxUsefulMag": max_useful_magnification,
                }
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
    def _binocular_target_profile(traits: TargetObservationTraits, sky_quality: SkyQuality | None = None) -> dict:
        angular_size = traits.angular_size_deg
        if traits.is_planetary_or_lunar or traits.is_high_magnification:
            return {
                "mode": "high",
                "idealMag": 120.0,
                "idealExit": 1.0,
                "idealField": 0.25 if angular_size is None else max(0.18, angular_size * 5.0),
                "barlowFriendly": False,
                "maxUsefulMag": 999.0,
            }
        if traits.is_wide_field:
            if angular_size and angular_size >= 2.5:
                ideal_magnification = 8.0
            elif angular_size and angular_size >= 1.0:
                ideal_magnification = 10.0
            else:
                ideal_magnification = 12.0
            ideal_exit = 4.5 if sky_quality and sky_quality.bortle_class >= 7 else 5.0
            return {
                "mode": "wide",
                "idealMag": ideal_magnification,
                "idealExit": ideal_exit,
                "idealField": 1.4 if angular_size is None else max(1.0, angular_size * 1.15),
                "barlowFriendly": False,
                "maxUsefulMag": 999.0,
            }
        if angular_size and angular_size >= 0.15:
            ideal_magnification = 16.0
            ideal_field = max(0.8, angular_size * 2.0)
        elif angular_size and angular_size >= 0.05:
            ideal_magnification = 24.0
            ideal_field = 0.55
        else:
            ideal_magnification = 38.0
            ideal_field = 0.35
        ideal_exit = 4.2 if traits.magnitude is not None and traits.magnitude > 8.5 else 3.8
        return {
            "mode": "balanced",
            "idealMag": ideal_magnification,
            "idealExit": ideal_exit,
            "idealField": ideal_field,
            "barlowFriendly": False,
            "maxUsefulMag": 999.0,
        }

    def _configuration_score(
        self,
        traits: TargetObservationTraits,
        configuration: ObservationConfiguration,
        profile: dict,
        sky_quality: SkyQuality | None,
        multiplier: float = 1.0,
    ) -> float:
        score = 0.0
        score += self._angular_scale_score(traits, configuration, profile, 24.0)
        score += self._magnification_score(configuration.magnification, profile, 24.0)
        score += self._exit_pupil_score(configuration.exit_pupil_mm, profile, 16.0)
        score += self._light_gathering_score(traits, configuration, sky_quality, 16.0)
        score += self._seeing_compatibility_score(configuration.magnification, profile, 10.0)
        score += self._handling_score(configuration, profile, multiplier, 10.0)
        return max(0.0, min(100.0, score))

    def _angular_scale_score(
        self,
        traits: TargetObservationTraits,
        configuration: ObservationConfiguration,
        profile: dict,
        weight: float,
    ) -> float:
        true_field = configuration.true_field_of_view_deg
        if true_field is None:
            return self._binocular_scale_score(traits, configuration.magnification, profile, weight)

        angular_size = traits.angular_size_deg
        mode = profile["mode"]
        if angular_size is None or angular_size <= 0:
            return weight * 0.7
        if mode == "wide":
            minimum_field = angular_size * 0.95
            if true_field < minimum_field:
                return weight * 0.45 * max(0.0, true_field / minimum_field) ** 2
            ideal_ratio = 1.35 if angular_size >= 2.0 else 1.65
            return self._ratio_score(true_field / angular_size, ideal_ratio, weight, 0.8)
        if mode == "high":
            minimum_field = max(0.12, angular_size * 4.0)
            if true_field < minimum_field:
                return weight * 0.75 * max(0.0, true_field / minimum_field) ** 2
            return weight * min(1.0, 0.86 + true_field / max(minimum_field * 10.0, 1.0))

        minimum_field = max(0.25, angular_size * 1.2)
        if true_field < minimum_field:
            return weight * 0.65 * max(0.0, true_field / minimum_field) ** 2
        desired_field = max(profile["idealField"], angular_size * 2.0)
        if true_field >= desired_field:
            return weight
        return self._ratio_score(true_field, desired_field, weight, 1.1)

    @staticmethod
    def _binocular_scale_score(
        traits: TargetObservationTraits,
        magnification: float,
        profile: dict,
        weight: float,
    ) -> float:
        angular_size = traits.angular_size_deg
        mode = profile["mode"]
        if mode == "wide":
            if magnification <= 10.0:
                factor = 1.0
            elif magnification <= 15.0:
                factor = 0.78
            elif magnification <= 20.0:
                factor = 0.55
            else:
                factor = 0.35
            if angular_size and angular_size >= 2.5 and magnification > 12.0:
                factor *= 0.75
            return weight * factor
        if mode == "high":
            return weight * (0.04 if angular_size is None or angular_size < 0.1 else 0.18)
        if angular_size is None:
            factor = 0.5
        elif angular_size >= 0.5:
            factor = 0.75
        elif angular_size >= 0.15:
            factor = 0.65
        elif angular_size >= 0.05:
            factor = 0.45
        else:
            factor = 0.22
        return weight * factor

    def _magnification_score(self, magnification: float, profile: dict, weight: float) -> float:
        tolerance = {"wide": 0.85, "balanced": 0.7, "high": 0.55}.get(profile["mode"], 0.7)
        return self._ratio_score(magnification, profile["idealMag"], weight, tolerance)

    def _exit_pupil_score(self, exit_pupil: float, profile: dict, weight: float) -> float:
        tolerance = {"wide": 0.65, "balanced": 0.75, "high": 0.9}.get(profile["mode"], 0.75)
        score = self._ratio_score(exit_pupil, profile["idealExit"], weight, tolerance)
        if exit_pupil < 0.45:
            score *= 0.25
        elif exit_pupil > 7.0:
            score *= 0.35
        elif exit_pupil > 6.0:
            score *= 0.65
        return score

    def _light_gathering_score(
        self,
        traits: TargetObservationTraits,
        configuration: ObservationConfiguration,
        sky_quality: SkyQuality | None,
        weight: float,
    ) -> float:
        objective = self._configuration_objective_mm(configuration)
        limiting_magnitude = configuration.limiting_magnitude_estimate or (2 + 5 * self._log10(max(1.0, objective)))
        magnitude = traits.magnitude
        if magnitude is None:
            factor = 0.65
        else:
            factor = self._clamp((limiting_magnitude - magnitude + 0.8) / 4.0)
            if magnitude <= 4.0:
                factor = max(factor, 0.85)
        surface_brightness = traits.surface_brightness_proxy
        if surface_brightness and surface_brightness >= 13.5:
            aperture_factor = self._clamp((objective - 40.0) / 160.0)
            factor = factor * 0.65 + aperture_factor * 0.35
        if sky_quality and sky_quality.bortle_class >= 7 and magnitude is not None and magnitude > 8.0:
            factor *= 0.85
        return weight * self._clamp(factor)

    @staticmethod
    def _seeing_compatibility_score(magnification: float, profile: dict, weight: float) -> float:
        max_useful = profile.get("maxUsefulMag", magnification)
        if magnification <= max_useful:
            return weight
        excess_ratio = (magnification - max_useful) / max(max_useful, 1.0)
        return weight * max(0.0, 1.0 - excess_ratio * 2.2)

    @staticmethod
    def _handling_score(
        configuration: ObservationConfiguration,
        profile: dict,
        multiplier: float,
        weight: float,
    ) -> float:
        if configuration.binocular:
            magnification = configuration.magnification
            if magnification <= 10.0:
                factor = 1.0
            elif magnification <= 12.0:
                factor = 0.85
            elif magnification <= 15.0:
                factor = 0.65
            elif magnification <= 18.0:
                factor = 0.45
            else:
                factor = 0.25
            if configuration.image_stabilized:
                factor = min(1.0, factor + 0.25)
            return weight * factor

        if multiplier <= 1.0:
            return weight
        if profile["barlowFriendly"]:
            return weight * 0.82
        if profile["mode"] == "wide":
            return 0.0
        return weight * 0.25

    @staticmethod
    def _configuration_objective_mm(configuration: ObservationConfiguration) -> float:
        if configuration.telescope:
            return configuration.telescope.aperture_mm
        if configuration.binocular:
            return configuration.binocular.objective_diameter_mm
        return 7.0

    @staticmethod
    def _ratio_score(value: float, ideal: float, weight: float, tolerance_octaves: float) -> float:
        if value <= 0 or ideal <= 0:
            return 0.0
        distance = abs(math.log(value / ideal, 2))
        return weight / (1.0 + (distance / max(tolerance_octaves, 0.01)) ** 2)

    @staticmethod
    def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        return max(lower, min(upper, value))

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

    @staticmethod
    def _binocular_setup_label(binocular: Binocular) -> str:
        spec = f"{binocular.magnification}x{binocular.objective_diameter_mm}"
        display_spec = spec.replace("x", "×")
        name = binocular.name.strip().replace(spec, display_spec).replace(spec.upper(), display_spec)
        normalized_name = name.lower().replace("×", "x")
        if spec.lower() not in normalized_name:
            name = f"{name} {display_spec}"
        tokens = name.upper().replace("-", " ").split()
        if binocular.image_stabilized and "IS" not in tokens:
            name = f"{name} IS"
        return name

    def has_optical_telescope(self, telescope: Telescope) -> bool:
        return telescope.id != self.NAKED_EYE_ID and telescope.aperture_mm > 0 and telescope.focal_length_mm > 0

    def can_use_eyepieces(self, telescope: Telescope) -> bool:
        return self.has_optical_telescope(telescope)

    @staticmethod
    def _log10(value: float) -> float:
        import math

        return math.log10(value)
