"""Score visual equipment configurations and build recommendation candidates."""

from __future__ import annotations

import math
from collections.abc import Callable

from astro_viewer.app.models.equipment import Barlow, BeginnerPreset, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.equipment_configuration import (
    EquipmentConfigurationService,
    FocalPosition,
)
from astro_viewer.app.services.observation_configuration_builder import (
    ObservationConfigurationBuilder,
)
from astro_viewer.app.services.recommendation_presenter import RecommendationPresenter
from astro_viewer.app.services.localization import (
    format_compact_number,
    format_number,
    join_text,
    tr,
)
from astro_viewer.app.services.equipment_setup_score_read_model import (
    EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS,
    EquipmentSetupScoreReadModel,
    EquipmentSetupScoreReadModelBuilder,
)


class EquipmentService(EquipmentConfigurationService):

    def __init__(self, presenter: RecommendationPresenter | None = None) -> None:
        self._presenter = presenter or RecommendationPresenter()
        self._setup_score_read_model_builder = EquipmentSetupScoreReadModelBuilder()

    def naked_eye_telescope(self) -> Telescope:
        return Telescope(
            self.NAKED_EYE_ID,
            tr("Occhio nudo"),
            0,
            0,
            tr("Occhio nudo"),
            tr("nessuna"),
        )

    def beginner_presets(self) -> list[BeginnerPreset]:
        return [
            BeginnerPreset("naked-eye", tr("Occhio nudo"), tr("Costellazioni e meteore"), tr("Nessuna configurazione richiesta."), tr("Luna, Venere, Giove, sciami meteorici")),
            BeginnerPreset("binoculars", tr("Binocolo 10x50"), tr("Ammassi aperti e Luna"), tr("Campo ampio e uso immediato."), tr("M31, Pleiadi, Luna crescente")),
            BeginnerPreset("small-scope", tr("Telescopio piccolo"), tr("Luna, pianeti luminosi, stelle doppie"), tr("Rifrattore o Maksutov fino a 90 mm."), tr("Giove, Saturno, Albireo")),
            BeginnerPreset("medium-scope", tr("Telescopio medio"), tr("Pianeti e cielo profondo brillante"), tr("Strumento versatile da 130-200 mm."), tr("M13, M57, nebulose luminose")),
            BeginnerPreset("large-scope", tr("Telescopio grande"), tr("Oggetti deboli e dettagli planetari"), tr("Richiede seeing e acclimatazione accurati."), tr("Galassie, nebulose planetarie, globulari risolti")),
        ]

    def default_telescopes(self) -> list[Telescope]:
        return []

    def default_eyepieces(self) -> list[Eyepiece]:
        return [
            Eyepiece("plossl-25", "Plossl 25 mm", 25.0, 52.0),
            Eyepiece("wide-15", tr("Grandangolare 15 mm"), 15.0, 68.0),
            Eyepiece("planetary-10", tr("Planetario 10 mm"), 10.0, 60.0),
            Eyepiece("planetary-6", tr("Planetario 6 mm"), 6.0, 58.0),
        ]

    def calculations(self, telescope: Telescope, eyepieces: list[Eyepiece], barlow: float) -> list[dict]:
        if not self.can_use_eyepieces(telescope) or not eyepieces:
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
                        "eyepiece": (
                            eyepiece.name
                            if eyepiece.eyepiece_type != "Zoom"
                            else join_text(
                                [eyepiece.name, focal_position["position"]], " @ "
                            )
                        ),
                        "magnification": tr(
                            "{value}x",
                            value=format_number(values["magnification"]),
                        ),
                        "trueField": tr(
                            "{value}°",
                            value=format_number(
                                values["true_field_of_view_deg"], decimals=2
                            ),
                        ),
                        "exitPupil": tr(
                            "{value} mm",
                            value=format_number(values["exit_pupil_mm"], decimals=1),
                        ),
                        "barlow": tr(
                            "{value}x", value=format_compact_number(barlow)
                        ),
                    }
                )
        return rows

    def telescope_capabilities(self, telescope: Telescope) -> dict:
        return self.profile_capabilities(telescope, [], [])

    def profile_capabilities(self, telescope: Telescope, eyepieces: list[Eyepiece], barlows: list[Barlow]) -> dict:
        if not self.has_optical_telescope(telescope):
            return {
                "name": telescope.name,
                "aperture": tr("n/d"),
                "focalLength": tr("n/d"),
                "practicalMagnification": tr("n/d"),
                "availableMagnificationMin": tr("n/d"),
                "availableMagnificationMax": tr("n/d"),
                "exitPupilMin": tr("n/d"),
                "exitPupilMax": tr("n/d"),
                "trueFieldMin": tr("n/d"),
                "trueFieldMax": tr("n/d"),
                "lightGathering": tr("1x occhio"),
                "limitingMagnitude": tr("n/d"),
                "resolution": tr("n/d"),
                "availableConfigurations": [],
                "availableConfigurationsText": tr("Aggiungi attrezzatura al profilo"),
            }
        if not self.can_use_eyepieces(telescope):
            return {
                "name": telescope.name,
                "aperture": tr(
                    "{value} mm",
                    value=format_number(telescope.aperture_mm),
                ),
                "focalLength": tr(
                    "{value} mm",
                    value=format_number(telescope.focal_length_mm),
                ),
                "practicalMagnification": tr("Non applicabile"),
                "availableMagnificationMin": tr("n/d"),
                "availableMagnificationMax": tr("n/d"),
                "exitPupilMin": tr("n/d"),
                "exitPupilMax": tr("n/d"),
                "trueFieldMin": tr("n/d"),
                "trueFieldMax": tr("n/d"),
                "lightGathering": tr("Canale fotografico integrato"),
                "limitingMagnitude": tr("n/d"),
                "resolution": tr("n/d"),
                "availableConfigurations": [],
                "availableConfigurationsText": tr(
                    "Telescopio smart: usa il piano EAA/fotografico integrato."
                ),
            }
        min_magnification = max(1, round(telescope.aperture_mm / 5))
        max_magnification = max(min_magnification, round(telescope.aperture_mm * 2))
        light_gathering = round((telescope.aperture_mm / 7.0) ** 2)
        limiting_magnitude = 2 + 5 * self._log10(max(1.0, telescope.aperture_mm))
        resolution = 116 / telescope.aperture_mm
        configurations = self._profile_capability_configurations(telescope, eyepieces, barlows)
        magnifications = [item["magnificationValue"] for item in configurations]
        exit_pupils = [item["exitPupilValue"] for item in configurations]
        true_fields = [item["trueFieldValue"] for item in configurations]
        return {
            "name": telescope.name,
            "aperture": tr("{value} mm", value=format_number(telescope.aperture_mm)),
            "focalLength": tr("{value} mm", value=format_number(telescope.focal_length_mm)),
            "practicalMagnification": tr(
                "{minimum}x - {maximum}x",
                minimum=format_number(min_magnification),
                maximum=format_number(max_magnification),
            ),
            "availableMagnificationMin": tr("{value}x", value=format_number(min(magnifications))) if magnifications else tr("n/d"),
            "availableMagnificationMax": tr("{value}x", value=format_number(max(magnifications))) if magnifications else tr("n/d"),
            "exitPupilMin": tr("{value} mm", value=format_number(min(exit_pupils), decimals=1)) if exit_pupils else tr("n/d"),
            "exitPupilMax": tr("{value} mm", value=format_number(max(exit_pupils), decimals=1)) if exit_pupils else tr("n/d"),
            "trueFieldMin": tr("{value}°", value=format_number(min(true_fields), decimals=2)) if true_fields else tr("n/d"),
            "trueFieldMax": tr("{value}°", value=format_number(max(true_fields), decimals=2)) if true_fields else tr("n/d"),
            "lightGathering": tr("{value}x occhio", value=light_gathering),
            "limitingMagnitude": tr("{value} stimata", value=format_number(limiting_magnitude, decimals=1)),
            "resolution": tr("{value}\" stimata", value=format_number(resolution, decimals=2)),
            "availableConfigurations": configurations,
            "availableConfigurationsText": join_text(
                [item["magnification"] for item in configurations[:12]], ", "
            ) if configurations else tr("Aggiungi oculari al profilo"),
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
        if not self.can_use_eyepieces(telescope):
            return self._presenter.smart_eaa_route(
                celestial_object,
                telescope,
                self.NAKED_EYE_ID,
            )
        if not eyepieces:
            return self._presenter.missing_eyepieces(celestial_object, telescope)

        barlows = barlows or []
        candidates = self._ranked_candidates(celestial_object, telescope, eyepieces, barlows, seeing, sky_quality)
        if not candidates:
            return self._presenter.no_useful_configurations(telescope)

        recommended = self._recommended_candidate(candidates)
        return self._presenter.from_candidates(
            celestial_object,
            candidates,
            recommended,
            sky_quality,
            seeing_limited=self._candidate_exceeds_seeing_limit(
                celestial_object,
                recommended,
                seeing,
                sky_quality,
            ),
        )

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
        usable_telescopes = [
            telescope
            for telescope in telescopes
            if self.can_use_eyepieces(telescope)
        ]
        smart_telescopes = [
            telescope
            for telescope in telescopes
            if telescope.is_smart_integrated
        ]
        if not usable_telescopes and not binoculars:
            if smart_telescopes:
                return self._presenter.smart_eaa_route(
                    celestial_object,
                    smart_telescopes[0],
                    self.NAKED_EYE_ID,
                )
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
                    seeing_limited=self._candidate_exceeds_seeing_limit(
                        celestial_object,
                        recommended,
                        seeing,
                        sky_quality,
                    ),
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
        profiles: dict[str, dict] = {}

        def profile_for(telescope: Telescope) -> dict:
            if telescope.id not in profiles:
                profiles[telescope.id] = self._target_profile(celestial_object, telescope, seeing, sky_quality)
            return profiles[telescope.id]

        def focal_position_provider(
            candidate_telescope: Telescope,
            eyepiece: Eyepiece,
            barlow: Barlow | None,
        ) -> list[FocalPosition]:
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
        practical_candidates = self._seeing_practical_candidates(
            candidates,
            profile_for,
            enforce_limit=self._seeing_limit_is_selection_constraint(
                celestial_object
            ),
        )
        return sorted(
            practical_candidates,
            key=lambda item: item.score,
            reverse=True,
        )

    def _ranked_candidates(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        eyepieces: list[Eyepiece],
        barlows: list[Barlow],
        seeing: SeeingTransparency | None = None,
        sky_quality: SkyQuality | None = None,
    ) -> list[RecommendationCandidate]:
        profile = self._target_profile(celestial_object, telescope, seeing, sky_quality)
        candidates = []

        def focal_position_provider(
            candidate_telescope: Telescope,
            eyepiece: Eyepiece,
            barlow: Barlow | None,
        ) -> list[FocalPosition]:
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
        practical_candidates = self._seeing_practical_candidates(
            candidates,
            lambda _telescope: profile,
            enforce_limit=self._seeing_limit_is_selection_constraint(
                celestial_object
            ),
        )
        return sorted(
            practical_candidates,
            key=lambda item: item.score,
            reverse=True,
        )

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
            barlow_label=barlow.name if barlow else tr("No"),
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
            barlow_label=tr("No"),
        )

    def _profile_capability_configurations(self, telescope: Telescope, eyepieces: list[Eyepiece], barlows: list[Barlow]) -> list[dict]:
        if not eyepieces:
            return []

        configurations = []
        seen = set()

        builder_configurations = ObservationConfigurationBuilder(self).build_telescope_configurations(
            [telescope],
            eyepieces,
            barlows,
        )
        for configuration in builder_configurations:
            eyepiece = configuration.eyepiece
            if not eyepiece:
                continue
            barlow = configuration.barlow
            multiplier = barlow.multiplier if barlow else 1.0
            magnification = round(configuration.magnification)
            key = (eyepiece.id, configuration.focal_position_label, multiplier, magnification)
            if key in seen:
                continue
            seen.add(key)
            configurations.append(
                {
                    "label": (
                        join_text(
                            [eyepiece.name, configuration.focal_position_label],
                            " @ ",
                        )
                        if eyepiece.eyepiece_type == "Zoom"
                        else eyepiece.name
                    ),
                    "magnification": tr("{value}x", value=format_number(magnification)),
                    "magnificationValue": float(magnification),
                    "trueFieldValue": eyepiece.apparent_field_deg / max(magnification, 1),
                    "exitPupilValue": telescope.aperture_mm / max(magnification, 1),
                    "barlow": barlow.name if barlow else tr("No"),
                }
            )
        return sorted(configurations, key=lambda item: item["magnificationValue"])

    @staticmethod
    def _seeing_practical_candidates(
        candidates: list[RecommendationCandidate],
        profile_for: Callable[[Telescope], dict],
        *,
        enforce_limit: bool,
    ) -> list[RecommendationCandidate]:
        if not enforce_limit:
            return candidates
        telescope_groups: dict[str, list[RecommendationCandidate]] = {}
        accepted_configuration_ids = {
            candidate.configuration.configuration_id
            for candidate in candidates
            if candidate.telescope is None
        }
        for candidate in candidates:
            telescope = candidate.telescope
            if telescope is not None:
                telescope_groups.setdefault(telescope.id, []).append(candidate)

        for group in telescope_groups.values():
            telescope = group[0].telescope
            if telescope is None:
                continue
            profile = profile_for(telescope)
            max_useful = float(profile["maxUsefulMag"])
            within_limit = [
                candidate
                for candidate in group
                if candidate.magnification <= max_useful
            ]
            if within_limit:
                accepted = within_limit
            else:
                minimum_magnification = min(
                    candidate.magnification
                    for candidate in group
                )
                accepted = [
                    candidate
                    for candidate in group
                    if math.isclose(
                        candidate.magnification,
                        minimum_magnification,
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    )
                ]
            accepted_configuration_ids.update(
                candidate.configuration.configuration_id
                for candidate in accepted
            )

        return [
            candidate
            for candidate in candidates
            if candidate.configuration.configuration_id
            in accepted_configuration_ids
        ]

    def _candidate_exceeds_seeing_limit(
        self,
        celestial_object: CelestialObject,
        candidate: RecommendationCandidate,
        seeing: SeeingTransparency | None,
        sky_quality: SkyQuality | None,
    ) -> bool:
        telescope = candidate.telescope
        if (
            telescope is None
            or not self._seeing_limit_is_selection_constraint(
                celestial_object
            )
        ):
            return False
        profile = self._target_profile(
            celestial_object,
            telescope,
            seeing,
            sky_quality,
        )
        return candidate.magnification > float(profile["maxUsefulMag"])

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
        profile = self._unclamped_target_profile(
            celestial_object,
            telescope,
            seeing,
            sky_quality,
        )
        if not self._seeing_limit_is_selection_constraint(celestial_object):
            return profile
        max_useful = max(1.0, float(profile["maxUsefulMag"]))
        return {
            **profile,
            "idealMag": min(float(profile["idealMag"]), max_useful),
        }

    @staticmethod
    def _seeing_limit_is_selection_constraint(
        celestial_object: CelestialObject,
    ) -> bool:
        traits = TargetObservationTraits.from_object(celestial_object)
        return (
            traits.is_planetary_or_lunar
            or traits.is_high_magnification
        )

    def _unclamped_target_profile(
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
            planetary_max = max_useful_magnification
            if not seeing:
                planetary_max = self._unknown_seeing_planetary_cap(telescope)
            ideal_magnification = min(max(30.0, planetary_max) * 0.82, 190.0) * altitude_factor
            return {
                "mode": "high",
                "idealMag": max(55.0, ideal_magnification),
                "idealExit": 1.0,
                "idealField": 0.18,
                "barlowFriendly": True,
                "maxUsefulMag": planetary_max,
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
                    if angular_size and 0.18 <= angular_size <= 0.45:
                        ideal_magnification = max(ideal_magnification, 84.0)
                        ideal_exit = min(ideal_exit, 1.8)
                    else:
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
        return self._configuration_score_read_model(
            traits,
            configuration,
            profile,
            sky_quality,
            multiplier,
        ).score

    def _configuration_score_read_model(
        self,
        traits: TargetObservationTraits,
        configuration: ObservationConfiguration,
        profile: dict,
        sky_quality: SkyQuality | None,
        multiplier: float = 1.0,
    ) -> EquipmentSetupScoreReadModel:
        weights = EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS
        return self._setup_score_read_model_builder.from_component_values(
            {
                "angular_scale": self._angular_scale_score(
                    traits,
                    configuration,
                    profile,
                    weights["angular_scale"],
                ),
                "magnification": self._magnification_score(
                    configuration.magnification,
                    profile,
                    weights["magnification"],
                ),
                "exit_pupil": self._exit_pupil_score(
                    configuration.exit_pupil_mm,
                    profile,
                    weights["exit_pupil"],
                ),
                "light_gathering": self._light_gathering_score(
                    traits,
                    configuration,
                    sky_quality,
                    weights["light_gathering"],
                ),
                "seeing_compatibility": self._seeing_compatibility_score(
                    configuration.magnification,
                    profile,
                    weights["seeing_compatibility"],
                ),
                "handling": self._handling_score(
                    configuration,
                    profile,
                    multiplier,
                    weights["handling"],
                ),
            }
        )

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
    def _unknown_seeing_planetary_cap(telescope: Telescope) -> float:
        theoretical = max(30.0, telescope.aperture_mm * 2.0)
        return min(theoretical, 125.0)

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
