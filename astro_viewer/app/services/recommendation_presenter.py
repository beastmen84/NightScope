from __future__ import annotations

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits


class RecommendationPresenter:
    def from_candidates(
        self,
        celestial_object: CelestialObject,
        candidates: list[RecommendationCandidate],
        recommended: RecommendationCandidate,
        sky_quality: SkyQuality | None = None,
        prefix_telescope: bool = False,
    ) -> dict:
        options = self._option_set(candidates, recommended)
        setup_options = [self._candidate_to_option(role, candidate) for role, candidate in options]
        alternative = next((option for option in setup_options if option["role"] == "Alternativa"), None)
        setup_text = recommended.detail_label
        telescope = recommended.telescope
        binocular = recommended.binocular
        if prefix_telescope and recommended.equipment_type == "Telescope" and telescope:
            setup_text = f"{recommended.telescope_name} + {setup_text}"
        if recommended.equipment_type == "Binocular":
            difficulty = self._difficulty_for_binocular(recommended)
            explanation = self._binocular_explanation(celestial_object, recommended)
            best_eyepiece = "Non richiesto"
            telescope_id = binocular.id if binocular else ""
            telescope_name = "Binocolo"
        else:
            difficulty = self._difficulty_for_object(celestial_object, telescope, sky_quality) if telescope else "Media"
            explanation = self._equipment_explanation(celestial_object, recommended)
            best_eyepiece = recommended.eyepiece.name if recommended.eyepiece else ""
            telescope_id = telescope.id if telescope else ""
            telescope_name = telescope.name if telescope else ""
        return {
            "bestEyepiece": best_eyepiece,
            "suggestedPosition": recommended.focal_position,
            "barlow": recommended.barlow_label,
            "difficulty": difficulty,
            "alternative": alternative["detailLabel"] if alternative else "n/d",
            "highMagnification": next((option["detailLabel"] for option in setup_options if option["role"] == "Alto ingrandimento"), ""),
            "wideField": next((option["detailLabel"] for option in setup_options if option["role"] == "Campo largo"), ""),
            "setupText": setup_text,
            "setupOptions": setup_options,
            "explanation": explanation,
            "telescopeId": telescope_id,
            "telescopeName": telescope_name,
            "equipmentType": recommended.equipment_type,
            "setupType": recommended.setup_type,
            "selectionScore": recommended.score,
        }

    def missing_eyepieces(self, celestial_object: CelestialObject, telescope: Telescope) -> dict:
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
            "equipmentType": "Telescope",
            "setupType": "telescope",
            "selectionScore": 12.0,
        }

    @staticmethod
    def no_useful_configurations(telescope: Telescope) -> dict:
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
            "equipmentType": "Telescope",
            "setupType": "telescope",
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
            "telescopeId": naked_eye_id,
            "telescopeName": "Occhio nudo",
            "equipmentType": "NakedEye",
            "setupType": "naked_eye",
            "selectionScore": 20.0 if naked_eye_realistic else 0.0,
        }

    def _option_set(
        self,
        candidates: list[RecommendationCandidate],
        recommended: RecommendationCandidate,
    ) -> list[tuple[str, RecommendationCandidate]]:
        options: list[tuple[str, RecommendationCandidate]] = [("Consigliato", recommended)]
        alternative = self._first_distinct(candidates, options)
        if alternative:
            options.append(("Alternativa", alternative))
        self._append_distinct_option(options, "Alto ingrandimento", max(candidates, key=lambda item: item.magnification))
        self._append_distinct_option(options, "Campo largo", max(candidates, key=lambda item: item.true_field or 0.0))
        return options

    @classmethod
    def _append_distinct_option(
        cls,
        options: list[tuple[str, RecommendationCandidate]],
        role: str,
        candidate: RecommendationCandidate,
    ) -> None:
        selected_keys = {cls._candidate_key(selected) for _, selected in options}
        if cls._candidate_key(candidate) not in selected_keys:
            options.append((role, candidate))

    @staticmethod
    def _first_distinct(
        candidates: list[RecommendationCandidate],
        selected: list[tuple[str, RecommendationCandidate]],
    ) -> RecommendationCandidate | None:
        selected_keys = {RecommendationPresenter._candidate_key(candidate) for _, candidate in selected}
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
    def _candidate_to_option(role: str, candidate: RecommendationCandidate) -> dict:
        true_field = candidate.true_field
        exit_pupil = candidate.exit_pupil
        return {
            "role": role,
            "label": candidate.label,
            "detailLabel": candidate.detail_label,
            "suggestedPosition": candidate.focal_position,
            "magnification": f"{candidate.magnification:.0f}x",
            "trueField": f"{true_field:.2f} gradi" if true_field is not None else "n/d",
            "exitPupil": f"{exit_pupil:.1f} mm" if exit_pupil is not None else "n/d",
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
            return "Difficile"
        if "pianeta" in lower_type or celestial_object.id in {"moon", "venus", "jupiter", "saturn"}:
            return "Facile" if telescope.aperture_mm >= 80 and max_altitude >= 25 else "Media"
        if "galaxy" in lower_type or "nebula" in lower_type or "nebul" in lower_type:
            if sky_quality and sky_quality.bortle_class >= 8:
                return "Difficile"
            surface_brightness = traits.surface_brightness_proxy
            if sky_quality and sky_quality.bortle_class >= 7 and surface_brightness and surface_brightness >= 13.5:
                return "Difficile"
            if telescope.aperture_mm < 120 or (magnitude is not None and magnitude > 9.0):
                return "Difficile"
            return "Media"
        if magnitude is not None and magnitude <= 7.5 and max_altitude >= 30:
            return "Facile"
        return "Media"

    @staticmethod
    def _difficulty_for_binocular(candidate: RecommendationCandidate) -> str:
        score = candidate.score
        if score >= 75.0:
            return "Facile"
        if score >= 45.0:
            return "Media"
        return "Difficile"

    def _binocular_explanation(self, celestial_object: CelestialObject, candidate: RecommendationCandidate) -> str:
        observation_type = TargetObservationTraits.from_object(celestial_object).recommended_observation_type
        magnification = candidate.magnification
        exit_pupil = candidate.exit_pupil
        if observation_type == "HighMagnification" or candidate.score < 35.0:
            return (
                "Il binocolo permette di individuare l'oggetto, ma non è ideale per i dettagli: "
                "servirebbe maggiore ingrandimento. "
                f"Configurazione disponibile: {magnification:.0f}x con pupilla {exit_pupil:.1f} mm."
            )
        if observation_type == "WideField":
            stabilization = " Binocolo stabilizzato: immagine più ferma." if candidate.binocular and candidate.binocular.image_stabilized else ""
            return (
                "Oggetto esteso: il binocolo offre una visione più naturale a largo campo. "
                f"{magnification:.0f}x con pupilla {exit_pupil:.1f} mm; "
                "il campo reale non è stimato perché il catalogo binocoli non include il FOV."
                + stabilization
            )
        return (
            "Configurazione utilizzabile a basso ingrandimento: "
            f"{magnification:.0f}x con pupilla {exit_pupil:.1f} mm; "
            "un telescopio può mostrare più dettaglio se disponibile."
        )

    @staticmethod
    def _equipment_explanation(celestial_object: CelestialObject, candidate: RecommendationCandidate) -> str:
        parts = [
            f"{candidate.magnification:.0f}x con pupilla {candidate.exit_pupil:.1f} mm",
            f"campo reale {candidate.true_field:.2f} gradi",
        ]
        if candidate.multiplier > 1.0:
            parts.append("Barlow usata per aumentare l'ingrandimento utile")
        else:
            parts.append("senza Barlow per mantenere contrasto e campo")
        max_altitude = TargetObservationTraits.from_object(celestial_object).max_altitude_deg
        if max_altitude > 0:
            parts.append(f"altezza massima {max_altitude:.0f} gradi")
        return "; ".join(parts) + "."

    def _difficulty_without_eyepieces(self, celestial_object: CelestialObject) -> str:
        lower_type = TargetObservationTraits.from_object(celestial_object).object_type_lower
        if celestial_object.id in {"moon", "venus", "jupiter", "saturn"}:
            return "Limitata"
        if "galaxy" in lower_type or "nebula" in lower_type:
            return "Difficile"
        return "Media"
