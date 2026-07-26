from __future__ import annotations

from dataclasses import dataclass, field

from astro_viewer.app.models.imaging import (
    ImagingCameraKind,
    ImagingModifierKind,
)
from astro_viewer.app.models.imaging_exposure import ImagingExposureAdvice
from astro_viewer.app.models.imaging_runtime import (
    ImagingRuntimeRecommendation,
    ImagingRuntimeStatus,
)
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoCaptureAdvice,
    ImagingVideoFpsSource,
)
from astro_viewer.app.services.localization import (
    format_compact_number,
    format_number,
    join_text,
    tr,
)


@dataclass(frozen=True)
class ImagingPresentationMetric:
    code: str
    label: object
    value: object

    def to_payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "value": self.value,
        }


@dataclass(frozen=True)
class ImagingPresentationNotice:
    code: str
    text: object
    level: str = "warning"

    def to_payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "text": self.text,
            "level": self.level,
        }


@dataclass(frozen=True)
class ImagingRecommendationPresentation:
    status_code: str
    ready: bool
    subtitle: object
    state_label: object
    mode_code: str = ""
    mode_label: object = ""
    confidence_code: str = ""
    confidence_label: object = ""
    setup_text: object = ""
    modifier_label: object = ""
    mechanical_text: object = ""
    geometry_title: object = ""
    geometry_metrics: tuple[ImagingPresentationMetric, ...] = field(
        default_factory=tuple
    )
    capture_title: object = ""
    capture_metrics: tuple[ImagingPresentationMetric, ...] = field(
        default_factory=tuple
    )
    guidance: object = ""
    notices: tuple[ImagingPresentationNotice, ...] = field(
        default_factory=tuple
    )
    disclaimer: object = ""
    unavailable_title: object = ""
    unavailable_detail: object = ""
    policy_version: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "statusCode": self.status_code,
            "ready": self.ready,
            "subtitle": self.subtitle,
            "stateLabel": self.state_label,
            "modeCode": self.mode_code,
            "modeLabel": self.mode_label,
            "confidenceCode": self.confidence_code,
            "confidenceLabel": self.confidence_label,
            "setupText": self.setup_text,
            "modifierLabel": self.modifier_label,
            "mechanicalText": self.mechanical_text,
            "geometryTitle": self.geometry_title,
            "geometryMetrics": [
                metric.to_payload() for metric in self.geometry_metrics
            ],
            "captureTitle": self.capture_title,
            "captureMetrics": [
                metric.to_payload() for metric in self.capture_metrics
            ],
            "guidance": self.guidance,
            "notices": [notice.to_payload() for notice in self.notices],
            "disclaimer": self.disclaimer,
            "unavailableTitle": self.unavailable_title,
            "unavailableDetail": self.unavailable_detail,
            "policyVersion": self.policy_version,
        }


class ImagingRecommendationPresenter:
    """Maps the typed photographic runtime result to a localized UI DTO."""

    _NOTICE_LIMIT = 3

    def present(
        self,
        recommendation: ImagingRuntimeRecommendation,
    ) -> ImagingRecommendationPresentation:
        if not recommendation.ready or recommendation.candidate is None:
            return self._unavailable(recommendation)

        candidate = recommendation.candidate
        mode_code = candidate.capture_mode.value
        advice = recommendation.advice
        confidence_code = (
            advice.confidence.value
            if advice is not None
            else ""
        )

        if recommendation.exposure_advice is not None:
            capture_title = tr("Piano di posa")
            capture_metrics = self._still_metrics(
                recommendation.exposure_advice
            )
            guidance = tr(
                "Acquisisci molte pose e sommale; regola gain o ISO con prove "
                "sul campo senza superare il limite prudenziale indicato."
            )
            disclaimer = tr(
                "I tempi sono intervalli di pianificazione, non una "
                "calibrazione della camera."
            )
            warning_codes = recommendation.exposure_advice.warning_codes
        else:
            capture_title = tr("Piano video")
            capture_metrics = self._video_metrics(
                recommendation.video_advice
            )
            guidance = tr(
                "Registra più clip separate e seleziona i frame migliori "
                "durante lo stacking."
            )
            disclaimer = self._video_disclaimer(
                recommendation.video_advice
            )
            warning_codes = (
                recommendation.video_advice.warning_codes
                if recommendation.video_advice is not None
                else ()
            )

        notices = self._notices(recommendation, warning_codes)
        return ImagingRecommendationPresentation(
            status_code=recommendation.status.value,
            ready=True,
            subtitle=tr(
                "Migliore combinazione disponibile nel profilo attivo"
            ),
            state_label=tr(
                "Scelta tra {count} configurazioni",
                count=format_number(recommendation.candidate_count),
            ),
            mode_code=mode_code,
            mode_label=(
                tr("Foto a lunga posa")
                if mode_code == "still"
                else tr("Video planetario")
            ),
            confidence_code=confidence_code,
            confidence_label=self._confidence_label(confidence_code),
            setup_text=self._setup_text(recommendation),
            modifier_label=self._modifier_label(recommendation),
            mechanical_text=self._mechanical_text(recommendation),
            geometry_title=tr("Inquadratura e campionamento"),
            geometry_metrics=self._geometry_metrics(recommendation),
            capture_title=capture_title,
            capture_metrics=capture_metrics,
            guidance=guidance,
            notices=notices,
            disclaimer=disclaimer,
            policy_version=recommendation.policy_version,
        )

    @staticmethod
    def _setup_text(
        recommendation: ImagingRuntimeRecommendation,
    ) -> object:
        configuration = recommendation.candidate.configuration
        parts: list[object] = [configuration.telescope.name]
        if configuration.reducer is not None:
            parts.append(configuration.reducer.name)
        elif configuration.barlow is not None:
            parts.append(configuration.barlow.name)
        parts.append(configuration.camera.name)
        return join_text(parts, " + ")

    @staticmethod
    def _modifier_label(
        recommendation: ImagingRuntimeRecommendation,
    ) -> object:
        configuration = recommendation.candidate.configuration
        if configuration.modifier_kind is ImagingModifierKind.FOCAL_REDUCER:
            return tr(
                "Riduttore di focale {factor}×",
                factor=format_compact_number(
                    configuration.focal_length_factor,
                    max_decimals=2,
                ),
            )
        if configuration.modifier_kind is ImagingModifierKind.BARLOW:
            return tr(
                "Barlow {factor}×",
                factor=format_compact_number(
                    configuration.focal_length_factor,
                    max_decimals=2,
                ),
            )
        return tr("Fuoco diretto")

    @staticmethod
    def _mechanical_text(
        recommendation: ImagingRuntimeRecommendation,
    ) -> object:
        configuration = recommendation.candidate.configuration
        required = configuration.required_backfocus_mm
        remaining = configuration.additional_backfocus_spacing_mm
        if required is None:
            return ""
        if remaining is None:
            return tr(
                "Backfocus richiesto dal riduttore: {required} mm",
                required=format_compact_number(
                    required,
                    max_decimals=1,
                ),
            )
        if remaining >= 0:
            return tr(
                "Backfocus richiesto: {required} mm · spaziatura ottica "
                "residua stimata: {remaining} mm",
                required=format_compact_number(
                    required,
                    max_decimals=1,
                ),
                remaining=format_compact_number(
                    remaining,
                    max_decimals=1,
                ),
            )
        return tr(
            "Il backfocus della camera supera di {overrun} mm la distanza "
            "richiesta dal riduttore.",
            overrun=format_compact_number(
                abs(remaining),
                max_decimals=1,
            ),
        )

    @staticmethod
    def _geometry_metrics(
        recommendation: ImagingRuntimeRecommendation,
    ) -> tuple[ImagingPresentationMetric, ...]:
        candidate = recommendation.candidate
        configuration = candidate.configuration
        body_video_geometry_unknown = (
            candidate.capture_mode.value == "video"
            and configuration.camera.kind
            is ImagingCameraKind.CAMERA_BODY
        )
        field_label = (
            tr("Campo video")
            if candidate.capture_mode.value == "video"
            else tr("Campo del sensore")
        )
        field_value = (
            tr("Non verificato")
            if body_video_geometry_unknown
            else tr(
                "{width}° × {height}°",
                width=format_compact_number(
                    configuration.field_width_deg,
                    max_decimals=2,
                ),
                height=format_compact_number(
                    configuration.field_height_deg,
                    max_decimals=2,
                ),
            )
        )
        sampling_label = (
            tr("Campionamento video")
            if candidate.capture_mode.value == "video"
            else tr("Campionamento")
        )
        sampling_value = (
            tr("Non verificato")
            if body_video_geometry_unknown
            else tr(
                "{value}″/px",
                value=format_compact_number(
                    configuration.pixel_scale_arcsec_per_pixel,
                    max_decimals=2,
                ),
            )
        )
        return (
            ImagingPresentationMetric(
                "field_of_view",
                field_label,
                field_value,
            ),
            ImagingPresentationMetric(
                "pixel_scale",
                sampling_label,
                sampling_value,
            ),
            ImagingPresentationMetric(
                "effective_focal_length",
                tr("Focale effettiva"),
                tr(
                    "{value} mm",
                    value=format_compact_number(
                        configuration.effective_focal_length_mm,
                        max_decimals=1,
                    ),
                ),
            ),
            ImagingPresentationMetric(
                "effective_focal_ratio",
                tr("Rapporto focale"),
                tr(
                    "f/{value}",
                    value=format_compact_number(
                        configuration.effective_focal_ratio,
                        max_decimals=1,
                    ),
                ),
            ),
        )

    @staticmethod
    def _still_metrics(
        advice: ImagingExposureAdvice,
    ) -> tuple[ImagingPresentationMetric, ...]:
        return (
            ImagingPresentationMetric(
                "sub_exposure",
                tr("Posa singola"),
                _seconds_range(
                    advice.sub_exposure_min_seconds,
                    advice.sub_exposure_max_seconds,
                ),
            ),
            ImagingPresentationMetric(
                "total_integration",
                tr("Integrazione totale"),
                _minutes_range(
                    advice.total_integration_min_minutes,
                    advice.total_integration_max_minutes,
                ),
            ),
            ImagingPresentationMetric(
                "frame_count",
                tr("Numero di pose indicativo"),
                _count_range(
                    advice.estimated_frame_count_min,
                    advice.estimated_frame_count_max,
                ),
            ),
            ImagingPresentationMetric(
                "tracking_limit",
                tr("Limite prudenziale per posa"),
                tr(
                    "{value} s",
                    value=format_compact_number(
                        advice.tracking_limit_seconds,
                        max_decimals=1,
                    ),
                ),
            ),
        )

    @staticmethod
    def _video_metrics(
        advice: ImagingVideoCaptureAdvice | None,
    ) -> tuple[ImagingPresentationMetric, ...]:
        if advice is None:
            return ()
        return (
            ImagingPresentationMetric(
                "clip_duration",
                tr("Durata della singola clip"),
                _seconds_range(
                    advice.clip_duration_min_seconds,
                    advice.clip_duration_max_seconds,
                    prefer_minutes=True,
                ),
            ),
            ImagingPresentationMetric(
                "planned_fps",
                tr("Frame rate pianificato"),
                _fps_range(
                    advice.planned_fps_min,
                    advice.planned_fps_max,
                ),
            ),
            ImagingPresentationMetric(
                "frame_count",
                tr("Frame indicativi"),
                _count_range(
                    advice.estimated_frame_count_min,
                    advice.estimated_frame_count_max,
                ),
            ),
            ImagingPresentationMetric(
                "fps_source",
                tr("Riferimento del frame rate"),
                {
                    ImagingVideoFpsSource.ACHIEVABLE: tr(
                        "Valore misurato"
                    ),
                    ImagingVideoFpsSource.CATALOG_MAXIMUM: tr(
                        "Massimo di catalogo"
                    ),
                    ImagingVideoFpsSource.TARGET_GOAL: tr(
                        "Obiettivo per il target"
                    ),
                }[advice.fps_source],
            ),
        )

    @staticmethod
    def _video_disclaimer(
        advice: ImagingVideoCaptureAdvice | None,
    ) -> object:
        if (
            advice is not None
            and advice.fps_source is ImagingVideoFpsSource.CATALOG_MAXIMUM
        ):
            return tr(
                "Il frame rate deriva dal massimo di catalogo a piena "
                "risoluzione: durata e FPS non sono prestazioni garantite."
            )
        if (
            advice is not None
            and advice.fps_source is ImagingVideoFpsSource.TARGET_GOAL
        ):
            return tr(
                "Il frame rate è un obiettivo per il target: durata e FPS "
                "non sono prestazioni garantite."
            )
        return tr(
            "Durata e FPS sono intervalli di pianificazione, non una "
            "calibrazione di acquisizione."
        )

    def _notices(
        self,
        recommendation: ImagingRuntimeRecommendation,
        warning_codes: tuple[str, ...],
    ) -> tuple[ImagingPresentationNotice, ...]:
        notices: list[ImagingPresentationNotice] = []
        framing_notice = self._framing_notice(recommendation)
        if framing_notice is not None:
            notices.append(framing_notice)

        messages = self._warning_messages()
        warning_set = set(warning_codes)
        for code in self._warning_priority():
            if code not in warning_set or code not in messages:
                continue
            notices.append(ImagingPresentationNotice(code, messages[code]))
            if len(notices) >= self._NOTICE_LIMIT:
                break
        return tuple(notices[: self._NOTICE_LIMIT])

    @staticmethod
    def _framing_notice(
        recommendation: ImagingRuntimeRecommendation,
    ) -> ImagingPresentationNotice | None:
        candidate = recommendation.candidate
        if (
            candidate.capture_mode.value == "video"
            and candidate.camera.kind is ImagingCameraKind.CAMERA_BODY
        ):
            return ImagingPresentationNotice(
                "camera_body_video_geometry_unverified",
                tr(
                    "Il ritaglio e il ricampionamento video del corpo macchina "
                    "non sono verificati: campo e campionamento possono "
                    "differire dal sensore fotografico."
                ),
            )
        target = candidate.target
        if (
            target.angular_size_major_deg is None
            or target.angular_size_minor_deg is None
        ):
            return None
        field_major = max(
            candidate.configuration.field_width_deg,
            candidate.configuration.field_height_deg,
        )
        field_minor = min(
            candidate.configuration.field_width_deg,
            candidate.configuration.field_height_deg,
        )
        target_major = max(
            target.angular_size_major_deg,
            target.angular_size_minor_deg,
        )
        target_minor = min(
            target.angular_size_major_deg,
            target.angular_size_minor_deg,
        )
        if target_major > field_major or target_minor > field_minor:
            return ImagingPresentationNotice(
                "target_exceeds_sensor_field",
                tr(
                    "Il target non entra interamente nel campo del sensore: "
                    "inquadra una regione oppure pianifica un mosaico."
                ),
            )
        if (
            target_major > field_major * 0.85
            or target_minor > field_minor * 0.85
        ):
            return ImagingPresentationNotice(
                "target_near_sensor_edge",
                tr(
                    "L'inquadratura è stretta: lascia margine per "
                    "orientamento, allineamento e ritaglio."
                ),
                level="info",
            )
        return None

    @staticmethod
    def _warning_priority() -> tuple[str, ...]:
        return (
            "target_below_horizon",
            "low_target_altitude",
            "poor_seeing_limits_planetary_detail",
            "variable_seeing_capture_multiple_clips",
            "atmospheric_dispersion_risk",
            "field_rotation_limits_sub_exposure",
            "field_rotation_limits_long_video",
            "manual_tracking_limits_sub_exposure",
            "manual_tracking_may_fragment_video",
            "bulb_mode_unavailable",
            "faint_planet_requires_exposure_gain_tradeoff",
            "planet_rotation_limits_single_clip",
            "uncooled_camera_thermal_noise",
            "strong_moonlight",
            "moonlight_present",
            "comet_motion_limits_sub_exposure",
            "mount_type_unverified",
            "camera_body_video_may_be_compressed",
            "frame_rate_below_target_goal",
        )

    @staticmethod
    def _warning_messages() -> dict[str, object]:
        return {
            "target_below_horizon": tr(
                "Il target è sotto l'orizzonte: pianifica la ripresa nella "
                "sua finestra di visibilità."
            ),
            "low_target_altitude": tr(
                "Il target è basso sull'orizzonte; attendi un'altezza "
                "maggiore per ridurre turbolenza e dispersione."
            ),
            "poor_seeing_limits_planetary_detail": tr(
                "Il seeing corrente limita il dettaglio planetario."
            ),
            "variable_seeing_capture_multiple_clips": tr(
                "Il seeing è variabile: acquisisci più clip e confronta i "
                "risultati."
            ),
            "atmospheric_dispersion_risk": tr(
                "A questa altezza la dispersione atmosferica può ridurre il "
                "dettaglio."
            ),
            "field_rotation_limits_sub_exposure": tr(
                "La montatura altazimutale limita la posa singola per "
                "contenere la rotazione di campo."
            ),
            "field_rotation_limits_long_video": tr(
                "La montatura altazimutale limita le clip più lunghe per la "
                "rotazione di campo."
            ),
            "manual_tracking_limits_sub_exposure": tr(
                "L'inseguimento manuale richiede pose singole molto brevi."
            ),
            "manual_tracking_may_fragment_video": tr(
                "L'inseguimento manuale può richiedere clip più brevi e "
                "ripetute."
            ),
            "bulb_mode_unavailable": tr(
                "Il corpo macchina non dichiara la modalità Bulb; verifica "
                "il tempo massimo disponibile."
            ),
            "faint_planet_requires_exposure_gain_tradeoff": tr(
                "Il pianeta è debole: bilancia tempo di esposizione del "
                "singolo frame e gain senza inseguire soltanto gli FPS."
            ),
            "planet_rotation_limits_single_clip": tr(
                "La rotazione del pianeta limita la durata utile di una "
                "singola clip senza derotazione."
            ),
            "uncooled_camera_thermal_noise": tr(
                "La camera non raffreddata può richiedere più frame e una "
                "gestione accurata del rumore termico."
            ),
            "strong_moonlight": tr(
                "La luce lunare è forte e può aumentare l'integrazione "
                "necessaria."
            ),
            "moonlight_present": tr(
                "La Luna è presente nella finestra del target; controlla "
                "gradienti e contrasto."
            ),
            "comet_motion_limits_sub_exposure": tr(
                "Il moto della cometa può richiedere pose più brevi o "
                "stacking allineato sul nucleo."
            ),
            "mount_type_unverified": tr(
                "Il tipo di montatura non è verificato; usa il limite di "
                "posa come valore prudenziale."
            ),
            "camera_body_video_may_be_compressed": tr(
                "Il video del corpo macchina può applicare compressione o "
                "ridimensionamento."
            ),
            "frame_rate_below_target_goal": tr(
                "Il frame rate disponibile è inferiore all'obiettivo tipico "
                "per questo target."
            ),
        }

    @staticmethod
    def _confidence_label(code: str) -> object:
        return {
            "low": tr("Affidabilità bassa"),
            "medium": tr("Affidabilità media"),
            "high": tr("Affidabilità alta"),
        }.get(code, tr("Affidabilità non disponibile"))

    @staticmethod
    def _unavailable(
        recommendation: ImagingRuntimeRecommendation,
    ) -> ImagingRecommendationPresentation:
        title, detail, state_label = {
            ImagingRuntimeStatus.NO_ACTIVE_PROFILE: (
                tr("Nessun profilo Equipment attivo"),
                tr(
                    "Attiva un profilo per costruire una raccomandazione "
                    "fotografica."
                ),
                tr("Profilo richiesto"),
            ),
            ImagingRuntimeStatus.NO_TELESCOPES: (
                tr("Nessun telescopio nel profilo"),
                tr(
                    "Aggiungi almeno un telescopio al profilo attivo per "
                    "costruire il treno fotografico."
                ),
                tr("Inventario incompleto"),
            ),
            ImagingRuntimeStatus.NO_CAMERAS: (
                tr("Nessuna camera nel profilo"),
                tr(
                    "Aggiungi una camera astronomica o un corpo macchina al "
                    "profilo attivo."
                ),
                tr("Inventario incompleto"),
            ),
            ImagingRuntimeStatus.NO_VALID_CONFIGURATIONS: (
                tr("Nessun treno fotografico valido"),
                tr(
                    "Verifica telescopio, camera e compatibilità dei "
                    "riduttori assegnati."
                ),
                tr("Configurazione non valida"),
            ),
            ImagingRuntimeStatus.ADVICE_UNAVAILABLE: (
                tr("Parametri di acquisizione non disponibili"),
                tr(
                    "La combinazione è stata valutata, ma i dati non bastano "
                    "per un piano di acquisizione affidabile."
                ),
                tr("Piano non disponibile"),
            ),
        }.get(
            recommendation.status,
            ImagingRecommendationPresenter._unsupported_copy(
                recommendation.unavailable_reason_code
            ),
        )
        return ImagingRecommendationPresentation(
            status_code=recommendation.status.value,
            ready=False,
            subtitle=tr("Configurazione fotografica del profilo attivo"),
            state_label=state_label,
            unavailable_title=title,
            unavailable_detail=detail,
            policy_version=recommendation.policy_version,
        )

    @staticmethod
    def _unsupported_copy(reason_code: str) -> tuple[object, object, object]:
        if reason_code == "certified_full_aperture_solar_filter_required":
            return (
                tr("Filtro solare certificato richiesto"),
                tr(
                    "Il Sole viene raccomandato solo con un filtro solare "
                    "certificato a tutta apertura, fissato davanti "
                    "all'obiettivo del telescopio selezionato."
                ),
                tr("Sicurezza solare"),
            )
        return (
            tr("Piano fotografico non disponibile"),
            tr(
                "Questo target non dispone ancora di una policy fotografica "
                "affidabile."
            ),
            tr("Target non supportato"),
        )


def _seconds_range(
    minimum: float,
    maximum: float,
    *,
    prefer_minutes: bool = False,
) -> object:
    if prefer_minutes and minimum >= 60 and maximum >= 60:
        return tr(
            "{minimum}–{maximum} min",
            minimum=format_compact_number(
                minimum / 60.0,
                max_decimals=1,
            ),
            maximum=format_compact_number(
                maximum / 60.0,
                max_decimals=1,
            ),
        )
    return tr(
        "{minimum}–{maximum} s",
        minimum=format_compact_number(minimum, max_decimals=1),
        maximum=format_compact_number(maximum, max_decimals=1),
    )


def _minutes_range(minimum: int, maximum: int) -> object:
    if minimum >= 120 and maximum >= 120:
        return tr(
            "{minimum}–{maximum} h",
            minimum=format_compact_number(
                minimum / 60.0,
                max_decimals=1,
            ),
            maximum=format_compact_number(
                maximum / 60.0,
                max_decimals=1,
            ),
        )
    return tr(
        "{minimum}–{maximum} min",
        minimum=format_number(minimum),
        maximum=format_number(maximum),
    )


def _count_range(minimum: int, maximum: int) -> object:
    return tr(
        "{minimum}–{maximum}",
        minimum=format_number(minimum),
        maximum=format_number(maximum),
    )


def _fps_range(minimum: float, maximum: float) -> object:
    if minimum == maximum:
        return tr(
            "{value} FPS",
            value=format_compact_number(minimum, max_decimals=1),
        )
    return tr(
        "{minimum}–{maximum} FPS",
        minimum=format_compact_number(minimum, max_decimals=1),
        maximum=format_compact_number(maximum, max_decimals=1),
    )
