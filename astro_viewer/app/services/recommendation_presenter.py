from __future__ import annotations

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.target_observation_traits import (
    TargetObservationTraits,
    is_supernova_remnant_type,
)
from astro_viewer.app.services.localization import format_number, tr


DIFFICULTY_EASY = tr("Facile")
DIFFICULTY_MEDIUM = tr("Media")
DIFFICULTY_HARD = tr("Difficile")
DIFFICULTY_LIMITED = tr("Limitata")

ROLE_LABELS = {
    "recommended": tr("Consigliato"),
    "alternative": tr("Alternativa"),
    "high_magnification": tr("Alto ingrandimento"),
    "wide_field": tr("Campo largo"),
}

PLANET_BINOCULAR_DIFFICULTY = {
    "moon": DIFFICULTY_EASY,
    "mercury": DIFFICULTY_HARD,
    "venus": DIFFICULTY_EASY,
    "mars": DIFFICULTY_MEDIUM,
    "jupiter": DIFFICULTY_EASY,
    "saturn": DIFFICULTY_MEDIUM,
    "uranus": DIFFICULTY_HARD,
    "neptune": DIFFICULTY_HARD,
}


class RecommendationPresenter:
    def from_candidates(
        self,
        celestial_object: CelestialObject,
        candidates: list[RecommendationCandidate],
        recommended: RecommendationCandidate,
        sky_quality: SkyQuality | None = None,
        prefix_telescope: bool = False,
        seeing_limited: bool = False,
    ) -> dict:
        options = self._option_set(
            celestial_object,
            candidates,
            recommended,
        )
        setup_options = self._setup_options(options)
        alternative = next(
            (option for option in setup_options if option["roleCode"] == "alternative"),
            None,
        )
        setup_text = recommended.detail_label
        telescope = recommended.telescope
        binocular = recommended.binocular
        if prefix_telescope and recommended.equipment_type == "Telescope" and telescope:
            setup_text = tr(
                "{telescope} + {setup}",
                telescope=recommended.telescope_name,
                setup=setup_text,
            )
        if recommended.equipment_type == "Binocular":
            difficulty = self._difficulty_for_binocular(celestial_object, recommended)
            explanation = self._binocular_explanation(celestial_object, recommended)
            best_eyepiece = tr("Non richiesto")
            telescope_id = binocular.id if binocular else ""
            telescope_name = tr("Binocolo")
        else:
            difficulty = (
                self._difficulty_for_object(celestial_object, telescope, sky_quality)
                if telescope
                else DIFFICULTY_MEDIUM
            )
            explanation = self._equipment_explanation(celestial_object, recommended)
            if seeing_limited:
                explanation = (
                    f"{explanation} "
                    f"{tr('Usa alti ingrandimenti solo se il seeing lo permette.')}"
                )
            best_eyepiece = recommended.eyepiece.name if recommended.eyepiece else ""
            telescope_id = telescope.id if telescope else ""
            telescope_name = telescope.name if telescope else ""
        return {
            "bestEyepiece": best_eyepiece,
            "suggestedPosition": recommended.focal_position,
            "barlow": recommended.barlow_label,
            "difficulty": difficulty,
            "alternative": alternative["displayLabel"] if alternative else tr("n/d"),
            "highMagnification": next((option["displayLabel"] for option in setup_options if option["roleCode"] == "high_magnification"), ""),
            "wideField": next((option["displayLabel"] for option in setup_options if option["roleCode"] == "wide_field"), ""),
            "setupText": setup_text,
            "setupOptions": setup_options,
            "explanation": explanation,
            "telescopeId": telescope_id,
            "telescopeName": telescope_name,
            "equipmentType": recommended.equipment_type,
            "setupType": recommended.setup_type,
            "recommendationState": (
                "seeing_limited" if seeing_limited else "ready"
            ),
            "requiresOpticalInstrument": False,
            "selectionScore": recommended.score,
        }

    def missing_eyepieces(self, celestial_object: CelestialObject, telescope: Telescope) -> dict:
        return {
            "bestEyepiece": "",
            "suggestedPosition": "",
            "barlow": tr("No"),
            "difficulty": self._difficulty_without_eyepieces(celestial_object),
            "alternative": tr("Aggiungi oculari al profilo"),
            "setupText": tr("Aggiungi oculari per suggerimenti completi"),
            "setupOptions": [],
            "explanation": tr("Telescopio presente, ma nessun oculare configurato."),
            "telescopeId": telescope.id,
            "telescopeName": telescope.name,
            "equipmentType": "Telescope",
            "setupType": "telescope",
            "recommendationState": "missing_eyepieces",
            "requiresOpticalInstrument": False,
            "selectionScore": 12.0,
        }

    def smart_eaa_route(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        naked_eye_id: str,
    ) -> dict:
        """Keep visual scoring neutral while routing the user to smart EAA."""

        payload = self.naked_eye(celestial_object, naked_eye_id)
        payload.update(
            {
                "bestEyepiece": "",
                "suggestedPosition": "",
                "barlow": tr("Non applicabile"),
                "alternative": tr(
                    "Per il visuale ottico usa un telescopio con oculari"
                ),
                "setupText": tr(
                    "{telescope}: usa il piano EAA/fotografico",
                    telescope=telescope.name,
                ),
                "setupOptions": [],
                "explanation": tr(
                    "Questo telescopio smart usa il sensore integrato: "
                    "ingrandimento, pupilla d'uscita, oculari e Barlow non "
                    "sono applicabili. Consulta il piano fotografico EAA."
                ),
                "telescopeName": telescope.name,
                "recommendationState": "smart_eaa_only",
                "smartTelescopeId": telescope.id,
            }
        )
        return payload

    @staticmethod
    def no_useful_configurations(telescope: Telescope) -> dict:
        return {
            "bestEyepiece": "",
            "suggestedPosition": "",
            "barlow": tr("No"),
            "difficulty": DIFFICULTY_HARD,
            "alternative": tr("Nessuna combinazione utile"),
            "setupText": tr("Aggiungi oculari adatti al profilo"),
            "setupOptions": [],
            "explanation": tr(
                "Le combinazioni disponibili superano i limiti pratici dello strumento."
            ),
            "telescopeId": telescope.id,
            "telescopeName": telescope.name,
            "equipmentType": "Telescope",
            "setupType": "telescope",
            "recommendationState": "no_useful_configurations",
            "requiresOpticalInstrument": False,
            "selectionScore": 8.0,
        }

    def naked_eye(self, celestial_object: CelestialObject, naked_eye_id: str) -> dict:
        traits = TargetObservationTraits.from_object(celestial_object)
        magnitude = traits.magnitude
        lower_type = traits.object_type_lower
        naked_eye_realistic = (
            celestial_object.id in {"moon", "mercury", "venus", "mars", "jupiter", "saturn"}
            or magnitude is not None
            and magnitude <= 5.5
            and not is_supernova_remnant_type(lower_type)
            and not any(fragment in lower_type for fragment in ("galaxy", "nebula", "globular"))
        )
        naked_eye_difficulty = {
            "moon": DIFFICULTY_EASY,
            "mercury": DIFFICULTY_HARD,
            "venus": DIFFICULTY_EASY,
            "mars": DIFFICULTY_MEDIUM,
            "jupiter": DIFFICULTY_EASY,
            "saturn": DIFFICULTY_MEDIUM,
        }.get(celestial_object.id, DIFFICULTY_EASY)
        return {
            "bestEyepiece": "",
            "suggestedPosition": "",
            "barlow": tr("No"),
            "difficulty": naked_eye_difficulty if naked_eye_realistic else tr("Non adatto a occhio nudo"),
            "alternative": tr("Binocolo o telescopio consigliato") if not naked_eye_realistic else tr("Occhio nudo"),
            "setupText": tr("Occhio nudo") if naked_eye_realistic else tr("Serve almeno un binocolo o telescopio"),
            "setupOptions": [],
            "explanation": tr("Oggetto compatibile con osservazione a occhio nudo.") if naked_eye_realistic else tr("Oggetto non realistico senza strumento ottico."),
            "telescopeId": naked_eye_id,
            "telescopeName": tr("Occhio nudo"),
            "equipmentType": "NakedEye",
            "setupType": "naked_eye",
            "recommendationState": (
                "naked_eye" if naked_eye_realistic else "requires_optical_instrument"
            ),
            "requiresOpticalInstrument": not naked_eye_realistic,
            "selectionScore": 20.0 if naked_eye_realistic else 0.0,
        }

    def _option_set(
        self,
        celestial_object: CelestialObject,
        candidates: list[RecommendationCandidate],
        recommended: RecommendationCandidate,
    ) -> list[tuple[str, str, RecommendationCandidate]]:
        options: list[tuple[str, str, RecommendationCandidate]] = [
            ("recommended", ROLE_LABELS["recommended"], recommended)
        ]
        alternative = self._first_distinct(candidates, options)
        if alternative:
            options.append(("alternative", ROLE_LABELS["alternative"], alternative))
        self._append_distinct_option(
            options,
            "high_magnification",
            self._high_magnification_candidate(
                celestial_object,
                candidates,
            ),
        )
        self._append_distinct_option(
            options,
            "wide_field",
            max(candidates, key=lambda item: item.true_field or 0.0),
        )
        return options

    @staticmethod
    def _high_magnification_candidate(
        celestial_object: CelestialObject,
        candidates: list[RecommendationCandidate],
    ) -> RecommendationCandidate:
        traits = TargetObservationTraits.from_object(celestial_object)
        faint_extended_target = (
            traits.surface_brightness_proxy is not None
            and traits.surface_brightness_proxy >= 13.5
            and (
                is_supernova_remnant_type(traits.object_type_lower)
                or any(
                    fragment in traits.object_type_lower
                    for fragment in (
                        "galaxy",
                        "galassia",
                        "nebula",
                        "nebul",
                    )
                )
            )
        )
        practical: list[RecommendationCandidate] = []
        for candidate in candidates:
            telescope = candidate.telescope
            if telescope is not None and (
                candidate.magnification > telescope.aperture_mm * 2.0
                or candidate.exit_pupil < 0.45
            ):
                continue
            if faint_extended_target:
                if candidate.barlow is not None or candidate.exit_pupil < 1.0:
                    continue
                target_size = traits.angular_size_deg
                if (
                    target_size is not None
                    and (
                        candidate.true_field is None
                        or candidate.true_field < target_size * 1.05
                    )
                ):
                    continue
            practical.append(candidate)
        return max(
            practical or candidates,
            key=lambda item: item.magnification,
        )

    @classmethod
    def _append_distinct_option(
        cls,
        options: list[tuple[str, str, RecommendationCandidate]],
        role_code: str,
        candidate: RecommendationCandidate,
    ) -> None:
        selected_keys = {cls._candidate_key(selected) for _, _, selected in options}
        if cls._candidate_key(candidate) not in selected_keys:
            options.append((role_code, ROLE_LABELS[role_code], candidate))

    @staticmethod
    def _first_distinct(
        candidates: list[RecommendationCandidate],
        selected: list[tuple[str, str, RecommendationCandidate]],
    ) -> RecommendationCandidate | None:
        selected_keys = {
            RecommendationPresenter._candidate_key(candidate)
            for _, _, candidate in selected
        }
        for candidate in candidates:
            if RecommendationPresenter._candidate_key(candidate) not in selected_keys:
                return candidate
        return None

    @staticmethod
    def _candidate_key(candidate: RecommendationCandidate) -> tuple[str, str, str, str]:
        return (
            candidate.equipment_type,
            candidate.telescope_name,
            candidate.detail_label,
            candidate.barlow_label,
        )

    @staticmethod
    def _setup_options(options: list[tuple[str, str, RecommendationCandidate]]) -> list[dict]:
        ambiguous_labels = RecommendationPresenter._ambiguous_telescope_labels(
            [candidate for _, _, candidate in options]
        )
        return [
            RecommendationPresenter._candidate_to_option(
                role_code,
                role,
                candidate,
                include_telescope=candidate.detail_label in ambiguous_labels,
            )
            for role_code, role, candidate in options
        ]

    @staticmethod
    def _ambiguous_telescope_labels(candidates: list[RecommendationCandidate]) -> set[str]:
        telescopes_by_label: dict[str, set[str]] = {}
        for candidate in candidates:
            if candidate.equipment_type != "Telescope" or not candidate.telescope_name:
                continue
            telescopes_by_label.setdefault(candidate.detail_label, set()).add(candidate.telescope_name)
        return {
            label
            for label, telescope_names in telescopes_by_label.items()
            if len(telescope_names) > 1
        }

    @staticmethod
    def _candidate_to_option(
        role_code: str,
        role: str,
        candidate: RecommendationCandidate,
        include_telescope: bool = False,
    ) -> dict:
        true_field = candidate.true_field
        exit_pupil = candidate.exit_pupil
        display_label = candidate.detail_label
        if include_telescope and candidate.equipment_type == "Telescope" and candidate.telescope_name:
            display_label = tr(
                "{telescope} + {setup}",
                telescope=candidate.telescope_name,
                setup=candidate.detail_label,
            )
        return {
            "roleCode": role_code,
            "role": role,
            "label": candidate.label,
            "detailLabel": candidate.detail_label,
            "displayLabel": display_label,
            "suggestedPosition": candidate.focal_position,
            "magnification": tr(
                "{value}x",
                value=format_number(candidate.magnification),
            ),
            "trueField": (
                tr("{value}°", value=format_number(true_field, decimals=2))
                if true_field is not None
                else tr("n/d")
            ),
            "exitPupil": (
                tr("{value} mm", value=format_number(exit_pupil, decimals=1))
                if exit_pupil is not None
                else tr("n/d")
            ),
            "exitPupilAvailable": exit_pupil is not None,
            "barlow": candidate.barlow_label,
            "score": max(0, min(100, round(candidate.score))),
            "telescopeName": candidate.telescope_name,
            "equipmentType": candidate.equipment_type,
        }

    def _difficulty_for_object(
        self,
        celestial_object: CelestialObject,
        telescope: Telescope,
        sky_quality: SkyQuality | None = None,
    ) -> str:
        traits = TargetObservationTraits.from_object(celestial_object)
        lower_type = traits.object_type_lower
        magnitude = traits.magnitude
        max_altitude = traits.max_altitude_deg
        if max_altitude < 15:
            return DIFFICULTY_HARD
        if traits.is_planetary_or_lunar:
            return self._planet_telescope_difficulty(
                celestial_object.id,
                telescope.aperture_mm,
                max_altitude,
            )
        if (
            "galaxy" in lower_type
            or "nebula" in lower_type
            or "nebul" in lower_type
            or is_supernova_remnant_type(lower_type)
        ):
            if sky_quality and sky_quality.bortle_class >= 8:
                return DIFFICULTY_HARD
            surface_brightness = traits.surface_brightness_proxy
            if sky_quality and sky_quality.bortle_class >= 7 and surface_brightness and surface_brightness >= 13.5:
                return DIFFICULTY_HARD
            if telescope.aperture_mm < 120 or (magnitude is not None and magnitude > 9.0):
                return DIFFICULTY_HARD
            return DIFFICULTY_MEDIUM
        if magnitude is not None and magnitude <= 7.5 and max_altitude >= 30:
            return DIFFICULTY_EASY
        return DIFFICULTY_MEDIUM

    @staticmethod
    def _planet_telescope_difficulty(
        object_id: str,
        aperture_mm: int,
        max_altitude: float,
    ) -> str:
        if object_id == "mercury":
            difficulty = DIFFICULTY_HARD if aperture_mm < 130 else DIFFICULTY_MEDIUM
        elif object_id == "mars":
            difficulty = DIFFICULTY_MEDIUM if aperture_mm < 130 else DIFFICULTY_EASY
        elif object_id == "uranus":
            difficulty = DIFFICULTY_EASY if aperture_mm >= 200 else DIFFICULTY_MEDIUM
        elif object_id == "neptune":
            difficulty = DIFFICULTY_HARD if aperture_mm < 130 else DIFFICULTY_MEDIUM
        else:
            difficulty = DIFFICULTY_EASY if aperture_mm >= 80 else DIFFICULTY_MEDIUM
        if max_altitude < 25:
            return {
                DIFFICULTY_EASY: DIFFICULTY_MEDIUM,
                DIFFICULTY_MEDIUM: DIFFICULTY_HARD,
            }.get(difficulty, difficulty)
        return difficulty

    @staticmethod
    def _difficulty_for_binocular(
        celestial_object: CelestialObject,
        candidate: RecommendationCandidate,
    ) -> str:
        score = candidate.score
        difficulty = PLANET_BINOCULAR_DIFFICULTY.get(celestial_object.id)
        if difficulty is None:
            if score >= 75.0:
                return DIFFICULTY_EASY
            if score >= 45.0:
                return DIFFICULTY_MEDIUM
            return DIFFICULTY_HARD
        if score < 45.0:
            return DIFFICULTY_HARD
        if score < 75.0 and difficulty == DIFFICULTY_EASY:
            return DIFFICULTY_MEDIUM
        return difficulty

    def _binocular_explanation(self, celestial_object: CelestialObject, candidate: RecommendationCandidate) -> str:
        observation_type = TargetObservationTraits.from_object(celestial_object).recommended_observation_type
        magnification = candidate.magnification
        exit_pupil = candidate.exit_pupil
        if observation_type == "HighMagnification" or candidate.score < 35.0:
            return tr(
                "Il binocolo permette di individuare l'oggetto, ma non è ideale per i dettagli: "
                "servirebbe maggiore ingrandimento. "
                "Configurazione disponibile: {magnification}x con pupilla {exit_pupil} mm.",
                magnification=format_number(magnification),
                exit_pupil=format_number(exit_pupil, decimals=1),
            )
        if observation_type == "WideField":
            stabilization = (
                tr(" Binocolo stabilizzato: immagine più ferma.")
                if candidate.binocular and candidate.binocular.image_stabilized
                else ""
            )
            return tr(
                "Oggetto esteso: il binocolo offre una visione più naturale a largo campo. "
                "{magnification}x con pupilla {exit_pupil} mm; "
                "il campo reale non è stimato perché il catalogo binocoli non include il FOV."
                "{stabilization}",
                magnification=format_number(magnification),
                exit_pupil=format_number(exit_pupil, decimals=1),
                stabilization=stabilization,
            )
        return tr(
            "Configurazione utilizzabile a basso ingrandimento: "
            "{magnification}x con pupilla {exit_pupil} mm; "
            "un telescopio può mostrare più dettaglio se disponibile.",
            magnification=format_number(magnification),
            exit_pupil=format_number(exit_pupil, decimals=1),
        )

    @staticmethod
    def _equipment_explanation(celestial_object: CelestialObject, candidate: RecommendationCandidate) -> str:
        barlow_clause = (
            tr("Barlow usata per aumentare l'ingrandimento utile")
            if candidate.multiplier > 1.0
            else tr("senza Barlow per mantenere contrasto e campo")
        )
        max_altitude = TargetObservationTraits.from_object(celestial_object).max_altitude_deg
        altitude_clause = (
            tr(
                "; altezza massima {altitude}°",
                altitude=format_number(max_altitude),
            )
            if max_altitude > 0
            else ""
        )
        return tr(
            "{magnification}x con pupilla {exit_pupil} mm; "
            "campo reale {true_field}°; {barlow}{altitude}.",
            magnification=format_number(candidate.magnification),
            exit_pupil=format_number(candidate.exit_pupil, decimals=1),
            true_field=format_number(candidate.true_field, decimals=2),
            barlow=barlow_clause,
            altitude=altitude_clause,
        )

    def _difficulty_without_eyepieces(self, celestial_object: CelestialObject) -> str:
        lower_type = TargetObservationTraits.from_object(celestial_object).object_type_lower
        if celestial_object.id in {"moon", "venus", "jupiter", "saturn"}:
            return DIFFICULTY_LIMITED
        if celestial_object.id in {"mercury", "uranus", "neptune"}:
            return DIFFICULTY_HARD
        if "galaxy" in lower_type or "nebula" in lower_type or is_supernova_remnant_type(lower_type):
            return DIFFICULTY_HARD
        return DIFFICULTY_MEDIUM
