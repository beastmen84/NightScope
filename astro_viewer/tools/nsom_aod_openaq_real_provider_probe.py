from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialState
from astro_viewer.app.services.nasa_aod_provider import NasaAodProvider
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionFeatureFlags,
    ObservationConditionInputs,
    ObservationConditionsService,
    ParticulateConditionInput,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere
from astro_viewer.app.services.openaq_atmosphere_service import OpenAQLocalAtmosphereService


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md")
DEFAULT_CREDENTIAL_PATH = Path("nasa_login.txt")

BASELINE_LOCATIONS: tuple[ObserverLocation, ...] = (
    ObserverLocation("Bologna", "Italy", 44.4938, 11.3387, "Europe/Rome"),
    ObserverLocation("San Pedro de Atacama", "Chile", -22.9087, -68.1997, "America/Santiago"),
    ObserverLocation("New Delhi", "India", 28.6139, 77.2090, "Asia/Kolkata"),
    ObserverLocation("Mauna Kea", "USA", 19.8206, -155.4681, "Pacific/Honolulu"),
    ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa"),
)

EXPANDED_LOCATIONS: tuple[ObserverLocation, ...] = (
    *BASELINE_LOCATIONS,
    ObserverLocation("Cairo", "Egypt", 30.0444, 31.2357, "Africa/Cairo"),
    ObserverLocation("Marrakech", "Morocco", 31.6295, -7.9811, "Africa/Casablanca"),
    ObserverLocation("Mexico City", "Mexico", 19.4326, -99.1332, "America/Mexico_City"),
    ObserverLocation("Los Angeles", "USA", 34.0522, -118.2437, "America/Los_Angeles"),
    ObserverLocation("Beijing", "China", 39.9042, 116.4074, "Asia/Shanghai"),
    ObserverLocation("Tokyo", "Japan", 35.6762, 139.6503, "Asia/Tokyo"),
    ObserverLocation("Singapore", "Singapore", 1.3521, 103.8198, "Asia/Singapore"),
    ObserverLocation("Sydney", "Australia", -33.8688, 151.2093, "Australia/Sydney"),
    ObserverLocation("Cape Town", "South Africa", -33.9249, 18.4241, "Africa/Johannesburg"),
    ObserverLocation("Reykjavik", "Iceland", 64.1466, -21.9426, "Atlantic/Reykjavik"),
)

LOCATION_SETS: dict[str, tuple[ObserverLocation, ...]] = {
    "baseline": BASELINE_LOCATIONS,
    "expanded": EXPANDED_LOCATIONS,
}
DEFAULT_LOCATION_SET = "expanded"
DEFAULT_LOCATIONS = EXPANDED_LOCATIONS


@dataclass(frozen=True)
class ProviderProbeCredentials:
    earthdata_username: str = ""
    earthdata_password: str = ""
    openaq_api_key: str = ""
    source_path: str = ""
    parse_notes: tuple[str, ...] = ()

    @property
    def has_earthdata(self) -> bool:
        return bool(self.earthdata_username and self.earthdata_password)

    @property
    def has_openaq(self) -> bool:
        return bool(self.openaq_api_key)


class DirectEarthdataCredentials:
    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def state(self) -> EarthdataCredentialState:
        return EarthdataCredentialState(
            username=self._username,
            configured=bool(self._username and self._password),
            secure_store_available=True,
            connection_verified=bool(self._username and self._password),
            message="Credenziali Earthdata caricate per probe developer-only.",
        )

    def password(self) -> str | None:
        return self._password or None


def load_probe_credentials(path: Path = DEFAULT_CREDENTIAL_PATH) -> ProviderProbeCredentials:
    """Load local provider secrets without exposing values in returned metadata."""

    if not path.exists():
        return ProviderProbeCredentials(
            source_path=str(path),
            parse_notes=("credential_file_missing",),
        )

    raw_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    parsed: dict[str, str] = {}
    unlabeled: list[tuple[str, str]] = []
    notes: list[str] = []
    section = ""
    pending_key: str | None = None

    for raw_line in raw_lines:
        line = _strip_wrapping_quotes(raw_line.strip())
        if not line or line.startswith("#"):
            continue
        heading = _section_for_heading(line)
        if heading:
            section = heading
            pending_key = None
            notes.append(f"section_{section}")
            continue
        key, value = _known_labeled_value(line, section)
        if key is not None:
            if value:
                if key not in parsed:
                    parsed[key] = value
                    notes.append(f"{key}_from_label")
                else:
                    notes.append(f"{key}_duplicate_ignored")
                pending_key = None
            else:
                pending_key = key
                notes.append(f"{key}_pending_value")
            continue
        if pending_key is not None:
            if pending_key not in parsed:
                parsed[pending_key] = line
                notes.append(f"{pending_key}_from_following_line")
            else:
                notes.append(f"{pending_key}_pending_duplicate_ignored")
            pending_key = None
            continue
        unlabeled.append((section, line))

    earthdata_unlabeled = [value for item_section, value in unlabeled if item_section in {"", "earthdata"}]
    openaq_unlabeled = [value for item_section, value in unlabeled if item_section in {"", "openaq"}]

    if "earthdata_username" not in parsed and earthdata_unlabeled:
        parsed["earthdata_username"] = earthdata_unlabeled.pop(0)
        notes.append("earthdata_username_from_unlabeled")
    if "earthdata_password" not in parsed and earthdata_unlabeled:
        parsed["earthdata_password"] = earthdata_unlabeled.pop(0)
        notes.append("earthdata_password_from_unlabeled")
    if "openaq_api_key" not in parsed:
        candidate_index = _openaq_candidate_index(openaq_unlabeled)
        if candidate_index is not None:
            parsed["openaq_api_key"] = openaq_unlabeled.pop(candidate_index)
            notes.append("openaq_api_key_from_unlabeled")

    if "earthdata_username" not in parsed:
        notes.append("earthdata_username_missing")
    if "earthdata_password" not in parsed:
        notes.append("earthdata_password_missing")
    if "openaq_api_key" not in parsed:
        notes.append("openaq_api_key_missing")

    return ProviderProbeCredentials(
        earthdata_username=parsed.get("earthdata_username", ""),
        earthdata_password=parsed.get("earthdata_password", ""),
        openaq_api_key=parsed.get("openaq_api_key", ""),
        source_path=str(path),
        parse_notes=tuple(notes),
    )


def run_real_provider_probe(
    *,
    credential_path: Path = DEFAULT_CREDENTIAL_PATH,
    locations: Iterable[ObserverLocation] = DEFAULT_LOCATIONS,
    location_set: str = DEFAULT_LOCATION_SET,
) -> dict[str, object]:
    credentials = load_probe_credentials(credential_path)
    nasa_provider = (
        NasaAodProvider(
            DirectEarthdataCredentials(credentials.earthdata_username, credentials.earthdata_password),
            cache_path=None,
        )
        if credentials.has_earthdata
        else None
    )
    openaq_service = OpenAQLocalAtmosphereService()

    rows = []
    nasa_auth_failed = False
    for location in locations:
        aod_result, nasa_auth_failed = _fetch_aod_for_probe_location(
            nasa_provider,
            location,
            nasa_auth_failed=nasa_auth_failed,
        )
        if credentials.has_openaq:
            atmosphere = openaq_service.atmosphere(credentials.openaq_api_key, location)
        else:
            atmosphere = LocalAtmosphere.not_configured()
        rows.append(_location_probe_row(location, aod_result, atmosphere))

    return _probe_report_data(credentials, tuple(rows), location_set=location_set)


def _fetch_aod_for_probe_location(
    nasa_provider: NasaAodProvider | None,
    location: ObserverLocation,
    *,
    nasa_auth_failed: bool,
) -> tuple[NasaAodResult, bool]:
    if nasa_provider is None:
        return NasaAodResult.no_credentials(), nasa_auth_failed
    if nasa_auth_failed:
        return (
            NasaAodResult.failure(
                "auth_skipped_after_failure",
                "NASA AOD non ritentato dopo un errore di autenticazione nel probe.",
            ),
            True,
        )
    result = nasa_provider.aod(location)
    return result, result.status == "auth_error"


def render_markdown_report(data: dict[str, object]) -> str:
    lines = [
        "# NSOM AOD/OpenAQ Real Provider Probe",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only probe uses real NASA Earthdata AOD and OpenAQ "
            "responses for a mixed-location set. It compares the default "
            "aerosol flag-off behaviour with the explicit experimental flag-on "
            "score effect. It is not wired into runtime, QML or automatic tests."
        ),
        "",
        "## Safety",
        "",
        f"- Runtime behaviour changed: `{data['metadata']['runtime_behaviour_changed_by_this_probe']}`.",
        f"- QML exposure: `{data['metadata']['qml_exposure']}`.",
        f"- Network: `{data['metadata']['network']}`.",
        f"- Automatic logging: `{data['metadata']['automatic_logging']}`.",
        f"- Persistent writes: `{data['metadata']['persistent_writes']}`.",
        f"- Credential values stored in report: `{data['metadata']['credential_values_stored_in_report']}`.",
        "",
        "## Verdict",
        "",
        f"- Verdict: `{data['readiness']['verdict']}`.",
        f"- Ready for default-on: `{data['readiness']['ready_for_default_on']}`.",
        f"- Recommended next step: {data['readiness']['recommended_next_step']}",
        f"- Location set: `{data['metadata']['location_set']}`.",
        f"- Location count: `{data['location_count']}`.",
        "",
        "## Provider Results By Location",
        "",
        "| Location | NASA AOD | AOD input | OpenAQ | PM input | Policy source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in data["locations"]:
        lines.append(
            "| "
            f"{row['location_label']} | "
            f"`{row['aod']['status']}` {row['aod']['value_label']} | "
            f"`{row['aod_input_included']}` `{row['aod_input_freshness']}` | "
            f"`{row['openaq']['status']}` {row['openaq']['value_label']} | "
            f"`{row['particulate_input_included']}` `{row['particulate_input_freshness']}` | "
            f"`{row['policy']['primary_source']}` |"
        )

    lines.extend(
        [
            "",
            "## Policy Reasons By Location",
            "",
            "| Location | Policy source | AOD eligible | AOD reasons | PM eligible | PM reasons |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in data["locations"]:
        policy = row["policy"]
        lines.append(
            "| "
            f"{row['location_label']} | `{policy['primary_source']}` | "
            f"`{policy['aod_eligible']}` | {_reason_label(policy['aod_reasons'])} | "
            f"`{policy['particulate_eligible']}` | {_reason_label(policy['particulate_reasons'])} |"
        )

    lines.extend(
        [
            "",
            "## Flag Off/On Aerosol Effects",
            "",
            "| Location | Target | Source | Flag off | Flag on modifier | Flag on score | Transparency loss |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in data["locations"]:
        for target in row["targets"]:
            lines.append(
                "| "
                f"{row['location_label']} | `{target['target_class']}` | "
                f"`{target['flag_on_primary_source']}` | `{target['flag_off_modifier']}` | "
                f"`{target['flag_on_modifier']}` | `{target['flag_on_adjusted_score']}` | "
                f"`{target['flag_on_transparency_loss']}` |"
            )

    lines.extend(
        [
            "",
            "## Aggregate Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in data["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Notes For Review",
            "",
            (
                "- A location can have provider data but still no score effect if "
                "freshness or provider-quality policy rejects the input."
            ),
            (
                "- NASA AOD remains primary when policy-eligible. OpenAQ PM remains "
                "fallback/context only and is not additive with AOD."
            ),
            (
                "- The default runtime stays score-neutral because "
                "`ObservationConditionFeatureFlags.experimental_aerosol_scoring` "
                "is still `False`."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(
    path: Path = REPORT_PATH,
    *,
    credential_path: Path = DEFAULT_CREDENTIAL_PATH,
    location_set: str = DEFAULT_LOCATION_SET,
) -> Path:
    data = run_real_provider_probe(
        credential_path=credential_path,
        locations=_locations_for_set(location_set),
        location_set=location_set,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(data), encoding="utf-8")
    return path


def _probe_report_data(
    credentials: ProviderProbeCredentials,
    rows: tuple[dict[str, object], ...],
    *,
    location_set: str = DEFAULT_LOCATION_SET,
) -> dict[str, object]:
    checks = _checks(rows)
    data = {
        "metadata": {
            "developer_only": True,
            "network": True,
            "runtime_behaviour_changed_by_this_probe": False,
            "qml_exposure": False,
            "automatic_logging": False,
            "persistent_writes": False,
            "provider_temp_downloads": True,
            "credential_values_stored_in_report": False,
            "credential_source_path": credentials.source_path,
            "credential_parse_notes": credentials.parse_notes,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "location_set": location_set,
            "version": _read_text(Path("VERSION")).strip(),
            "generated_at_utc": datetime.now(UTC).isoformat(),
        },
        "readiness": {
            "verdict": _verdict(checks),
            "ready_for_default_on": False,
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "recommended_next_step": (
                "Review real-provider results, then decide whether AOD/OpenAQ "
                "can move to a narrow default-on switch or needs more field observations."
            ),
        },
        "location_count": len(rows),
        "locations": rows,
        "checks": checks,
    }
    json.dumps(nsom_to_json_compatible(data), allow_nan=False)
    return nsom_to_json_compatible(data)


def _location_probe_row(
    location: ObserverLocation,
    aod_result: NasaAodResult,
    atmosphere: LocalAtmosphere,
) -> dict[str, object]:
    service = ObservationConditionsService()
    flags_off = ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)
    flags_on = ObservationConditionFeatureFlags(experimental_aerosol_scoring=True)
    aod_input = _aod_condition_input(aod_result)
    particulate_input = _particulate_condition_input(atmosphere)
    policy = service._aerosol_provider_policy(aod_input, particulate_input, flags_on)
    target_rows = []
    for target in _targets():
        off_breakdown = service.experimental_aerosol_scoring_breakdown(
            target,
            aod_input,
            particulate_input,
            flags_off,
        )
        on_breakdown = service.experimental_aerosol_scoring_breakdown(
            target,
            aod_input,
            particulate_input,
            flags_on,
        )
        on_conditioned = service.condition_target(
            target,
            ObservationConditionInputs(
                aod=aod_input,
                particulate=particulate_input,
                feature_flags=flags_on,
            ),
        )
        target_rows.append(
            {
                "target_id": target.id,
                "target_name": target.name,
                "target_class": on_breakdown.target_class,
                "base_score": target.score,
                "flag_off_modifier": off_breakdown.score_modifier,
                "flag_on_primary_source": on_breakdown.primary_source,
                "flag_on_modifier": on_breakdown.score_modifier,
                "flag_on_adjusted_score": on_conditioned.breakdown.adjusted_score,
                "flag_on_transparency_loss": on_breakdown.transparency_loss,
                "flag_on_atmospheric_transparency_factor": on_breakdown.atmospheric_transparency_factor,
                "flag_on_notes": on_breakdown.notes,
            }
        )
    return {
        "location": asdict(location),
        "location_label": f"{location.city}, {location.country}",
        "aod": _aod_result_summary(aod_result),
        "openaq": _openaq_result_summary(atmosphere),
        "aod_input_included": aod_input is not None,
        "aod_input_freshness": aod_input.freshness_category if aod_input is not None else "none",
        "particulate_input_included": particulate_input is not None,
        "particulate_input_freshness": particulate_input.freshness_category if particulate_input is not None else "none",
        "policy": {
            "primary_source": policy.primary_source,
            "aod_eligible": policy.aod.eligible_for_future_scoring,
            "aod_reasons": policy.aod.reasons,
            "particulate_eligible": policy.particulate.eligible_for_future_fallback,
            "particulate_reasons": policy.particulate.reasons,
            "double_counting_rules": policy.double_counting_rules,
            "confidence_notes": policy.confidence_notes,
        },
        "targets": tuple(target_rows),
    }


def _aod_condition_input(result: NasaAodResult) -> AodConditionInput | None:
    if not result.available or result.aod_550 is None:
        return None
    age_days = _aod_age_days(result)
    freshness_category = _aod_freshness_category(age_days)
    if freshness_category == "historical":
        return None
    return AodConditionInput(
        available=True,
        freshness_category=freshness_category,
        aod_550=result.aod_550,
        source=result.provider,
        product=result.product,
        status=result.status,
        age_days=age_days,
        uncertainty=result.uncertainty,
        qa_raw=result.qa_raw,
        method=result.method,
        local_valid_pixel_count=result.local_valid_pixel_count,
    )


def _particulate_condition_input(atmosphere: LocalAtmosphere) -> ParticulateConditionInput | None:
    if not atmosphere.has_data:
        return None
    return ParticulateConditionInput(
        available=True,
        freshness_category=atmosphere.freshness_category,
        pm25=_numeric_value(atmosphere.pm25),
        pm10=_numeric_value(atmosphere.pm10),
        source=atmosphere.source if atmosphere.source != "—" else "",
        status="ok",
        age_days=_freshness_age_days(atmosphere.freshness),
        distance_km=atmosphere.source_distance_km,
    )


def _aod_result_summary(result: NasaAodResult) -> dict[str, object]:
    age_days = _aod_age_days(result)
    return {
        "available": result.available,
        "status": result.status,
        "product": result.product,
        "aod_550": result.aod_550,
        "uncertainty": result.uncertainty,
        "qa_raw_present": result.qa_raw is not None,
        "acquisition_date": result.acquisition_date,
        "age_days": age_days,
        "freshness_category": _aod_freshness_category(age_days),
        "method": result.method,
        "local_valid_pixel_count": result.local_valid_pixel_count,
        "cache_hit": result.cache_hit,
        "value_label": f"AOD {result.aod_550:.3f}" if result.aod_550 is not None else "",
    }


def _openaq_result_summary(atmosphere: LocalAtmosphere) -> dict[str, object]:
    return {
        "visible": atmosphere.visible,
        "has_data": atmosphere.has_data,
        "status": "ok" if atmosphere.has_data else atmosphere.freshness_category,
        "pm25": _numeric_value(atmosphere.pm25),
        "pm10": _numeric_value(atmosphere.pm10),
        "freshness_category": atmosphere.freshness_category,
        "freshness": atmosphere.freshness,
        "source": atmosphere.source,
        "source_distance_km": atmosphere.source_distance_km,
        "value_label": _pm_value_label(atmosphere),
    }


def _checks(rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    target_rows = [target for row in rows for target in row["targets"]]
    deep_sky = [
        float(target["flag_on_modifier"])
        for target in target_rows
        if target["target_class"] in {"galaxy", "diffuse_nebula", "open_cluster", "globular_cluster"}
    ]
    solar_system = [
        float(target["flag_on_modifier"])
        for target in target_rows
        if target["target_class"] in {"planet", "moon"}
    ]
    policy_sources = {row["policy"]["primary_source"] for row in rows}
    return {
        "location_count_is_5_to_15": 5 <= len(rows) <= 15,
        "strict_json_compatible": _strict_json_ok(rows),
        "flag_off_always_neutral": all(float(target["flag_off_modifier"]) == 0.0 for target in target_rows),
        "has_real_provider_success": any(row["aod"]["available"] or row["openaq"]["has_data"] for row in rows),
        "has_policy_eligible_source": any(row["policy"]["primary_source"] in {"aod", "particulate"} for row in rows),
        "policy_sources_observed": tuple(sorted(str(source) for source in policy_sources)),
        "deep_sky_max_penalty": min(deep_sky) if deep_sky else 0.0,
        "solar_system_max_penalty": min(solar_system) if solar_system else 0.0,
        "deep_sky_penalty_at_least_solar_system": (
            abs(min(deep_sky)) >= abs(min(solar_system))
            if deep_sky and solar_system
            else True
        ),
        "confidence_score_neutral_notes_present": all(
            "provider_quality_does_not_change_target_specific_score" in row["policy"]["confidence_notes"]
            for row in rows
        ),
    }


def _locations_for_set(location_set: str) -> tuple[ObserverLocation, ...]:
    try:
        return LOCATION_SETS[location_set]
    except KeyError as exc:
        raise ValueError(f"Unknown location set: {location_set}") from exc


def _reason_label(reasons: object) -> str:
    if not reasons:
        return "`none`"
    if isinstance(reasons, (list, tuple)):
        return ", ".join(f"`{reason}`" for reason in reasons) or "`none`"
    return f"`{reasons}`"


def _verdict(checks: dict[str, object]) -> str:
    if not checks["has_real_provider_success"]:
        return "real_provider_probe_no_provider_data"
    if not checks["has_policy_eligible_source"]:
        return "real_provider_probe_provider_data_not_policy_eligible"
    if not checks["deep_sky_penalty_at_least_solar_system"]:
        return "real_provider_probe_needs_aerosol_scale_review"
    return "real_provider_probe_ready_for_human_review"


def _known_labeled_value(line: str, section: str = "") -> tuple[str | None, str]:
    for separator in ("=", ":"):
        if separator not in line:
            continue
        left, right = line.split(separator, 1)
        key = _credential_key(left, section)
        value = _strip_wrapping_quotes(right.strip())
        if key is not None:
            return key, value
    return None, line


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _credential_key(value: str, section: str = "") -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if normalized in {
        "earthdata_username",
        "earthdata_user",
        "earthdata_login",
        "nasa_username",
        "nasa_user",
        "nasa_login",
        "username",
        "user",
        "login",
    }:
        if section == "openaq":
            return None
        return "earthdata_username"
    if normalized in {
        "earthdata_password",
        "earthdata_pass",
        "nasa_password",
        "nasa_pass",
        "password",
        "pass",
        "pwd",
    }:
        if section == "openaq":
            return None
        return "earthdata_password"
    if normalized in {
        "openaq_api_key",
        "openaq_key",
        "openaq",
        "api_key",
        "api",
        "token",
        "key",
    }:
        return "openaq_api_key"
    return None


def _looks_like_heading(line: str) -> bool:
    return _section_for_heading(line) in {"earthdata", "openaq"} or _normalized_heading(line) in {
        "credentials",
        "credenziali",
    }


def _section_for_heading(line: str) -> str:
    normalized = _normalized_heading(line)
    if normalized in {"nasa", "earthdata", "nasa_earthdata"}:
        return "earthdata"
    if normalized in {"openaq", "open_aq"}:
        return "openaq"
    return ""


def _normalized_heading(line: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", line.strip().lower()).strip("_")


def _openaq_candidate_index(values: list[str]) -> int | None:
    if not values:
        return None
    for index, value in enumerate(values):
        compact = value.strip()
        if len(compact) >= 24 and " " not in compact:
            return index
    return len(values) - 1


def _aod_age_days(result: NasaAodResult) -> float | None:
    if not result.acquisition_date:
        return None
    try:
        acquisition_date = datetime.fromisoformat(result.acquisition_date).date()
    except ValueError:
        return None
    return float(max(0, (datetime.now(UTC).date() - acquisition_date).days))


def _aod_freshness_category(age_days: float | None) -> str:
    if age_days is None:
        return "unavailable"
    if age_days < 3:
        return "current"
    if age_days <= 7:
        return "stale"
    return "historical"


def _numeric_value(value: str) -> float | None:
    match = re.search(r"-?\d+(?:[.,]\d+)?", value or "")
    if not match:
        return None
    try:
        parsed = float(match.group(0).replace(",", "."))
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _freshness_age_days(label: str) -> float | None:
    normalized = (label or "").strip().lower()
    if not normalized:
        return None
    if "oggi" in normalized or "today" in normalized:
        return 0.0
    if "ieri" in normalized or "yesterday" in normalized:
        return 1.0
    match = re.search(r"(\d+)\s+(?:giorni|days)", normalized)
    if match:
        return float(match.group(1))
    return None


def _pm_value_label(atmosphere: LocalAtmosphere) -> str:
    values = []
    if atmosphere.pm25 != "—":
        values.append(f"PM2.5 {atmosphere.pm25}")
    if atmosphere.pm10 != "—":
        values.append(f"PM10 {atmosphere.pm10}")
    return ", ".join(values)


def _targets() -> tuple[CelestialObject, ...]:
    return (
        _make_target("m31", "M31", "Galaxy"),
        _make_target("m42", "M42", "Diffuse Nebula"),
        _make_target("m45", "M45", "Open Cluster"),
        _make_target("m13", "M13", "Globular Cluster"),
        _make_target("mars", "Mars", "Pianeta"),
        _make_target("moon", "Moon", "Satellite naturale"),
    )


def _make_target(object_id: str, name: str, object_type: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="7.8",
        distance="",
        max_altitude="48 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Probe target.",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=82,
        score_label=ObservingScoreService.score_label(82),
        difficulty="Media",
        apparent_size="20 arcmin",
        max_angular_size_deg=0.33,
    )


def _strict_json_ok(value: object) -> bool:
    try:
        json.dumps(nsom_to_json_compatible(value), allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the developer-only real provider AOD/OpenAQ probe.")
    parser.add_argument("--credentials", default=str(DEFAULT_CREDENTIAL_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--location-set", choices=tuple(LOCATION_SETS), default=DEFAULT_LOCATION_SET)
    args = parser.parse_args()
    path = write_markdown_report(
        Path(args.output),
        credential_path=Path(args.credentials),
        location_set=args.location_set,
    )
    print(path)


if __name__ == "__main__":
    main()
