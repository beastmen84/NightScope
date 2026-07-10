from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere
from astro_viewer.tools.nsom_aod_openaq_real_provider_probe import (
    _fetch_aod_for_probe_location,
    _location_probe_row,
    _probe_report_data,
    load_probe_credentials,
    render_markdown_report,
)


class FakeAodProvider:
    def __init__(self) -> None:
        self.calls = 0

    def aod(self, _location: ObserverLocation) -> NasaAodResult:
        self.calls += 1
        return NasaAodResult.failure("auth_error", "Autenticazione fallita.")


def test_real_provider_probe_credential_parser_redacts_values(tmp_path: Path) -> None:
    credential_file = tmp_path / "nasa_login.txt"
    credential_file.write_text(
        "\n".join(
            [
                "Earthdata",
                "nasa-user",
                "nasa-secret-password",
                "OpenAQ",
                "api: openaq-secret-token-1234567890",
            ]
        ),
        encoding="utf-8",
    )

    credentials = load_probe_credentials(credential_file)

    assert credentials.earthdata_username == "nasa-user"
    assert credentials.earthdata_password == "nasa-secret-password"
    assert credentials.openaq_api_key == "openaq-secret-token-1234567890"
    assert "nasa-secret-password" not in credentials.parse_notes
    assert "openaq-secret-token-1234567890" not in credentials.parse_notes


def test_real_provider_probe_parser_does_not_treat_openaq_username_as_earthdata(tmp_path: Path) -> None:
    credential_file = tmp_path / "nasa_login.txt"
    credential_file.write_text(
        "\n".join(
            [
                "EARTHDATA",
                "Username: earth-user",
                "Password: earth-pass",
                "OPENAQ",
                "Username: openaq-user",
                "Password: openaq-password",
                "api:",
                "openaq-secret-token-1234567890",
            ]
        ),
        encoding="utf-8",
    )

    credentials = load_probe_credentials(credential_file)

    assert credentials.earthdata_username == "earth-user"
    assert credentials.earthdata_password == "earth-pass"
    assert credentials.openaq_api_key == "openaq-secret-token-1234567890"


def test_real_provider_probe_parser_preserves_trailing_apostrophe_password(tmp_path: Path) -> None:
    credential_file = tmp_path / "nasa_login.txt"
    credential_file.write_text(
        "\n".join(
            [
                "EARTHDATA",
                "Username: earth-user",
                "Password: 7_passwordT'",
                "OPENAQ",
                "api:",
                "openaq-secret-token-1234567890",
            ]
        ),
        encoding="utf-8",
    )

    credentials = load_probe_credentials(credential_file)

    assert credentials.earthdata_password == "7_passwordT'"


def test_real_provider_probe_skips_nasa_after_auth_failure() -> None:
    provider = FakeAodProvider()
    location = ObserverLocation("Probe City", "World", 10.0, 20.0, "UTC")

    first, auth_failed = _fetch_aod_for_probe_location(provider, location, nasa_auth_failed=False)
    second, still_failed = _fetch_aod_for_probe_location(provider, location, nasa_auth_failed=auth_failed)

    assert first.status == "auth_error"
    assert second.status == "auth_skipped_after_failure"
    assert auth_failed is True
    assert still_failed is True
    assert provider.calls == 1


def test_real_provider_probe_report_is_strict_json_and_keeps_confidence_neutral() -> None:
    location = ObserverLocation("Probe City", "World", 10.0, 20.0, "UTC")
    today = datetime.now(UTC).date().isoformat()
    aod = NasaAodResult(
        available=True,
        status="ok",
        message="Dati NASA AOD disponibili.",
        product="VNP19A2.002",
        aod_550=0.44,
        uncertainty=0.04,
        qa_raw=1089,
        acquisition_date=today,
        granule_id="safe-granule-id",
        method="local_neighborhood",
        local_valid_pixel_count=4,
        retrieved_at=datetime.now(UTC).isoformat(),
    )
    atmosphere = LocalAtmosphere(
        visible=True,
        has_data=True,
        message="Dati OpenAQ disponibili.",
        pm25="35.0",
        pm10="80.0",
        clarity="Velata",
        source="OpenAQ",
        source_detail="Local station",
        freshness="oggi",
        freshness_category="current",
        source_distance_km=4.0,
    )

    row = _location_probe_row(location, aod, atmosphere)
    data = _probe_report_data(
        credentials=type(
            "Creds",
            (),
            {
                "source_path": "nasa_login.txt",
                "parse_notes": ("earthdata_username_from_unlabeled",),
            },
        )(),
        rows=(row,),
    )

    json.dumps(data, allow_nan=False)
    assert data["checks"]["flag_off_always_neutral"] is True
    assert data["checks"]["has_real_provider_success"] is True
    assert data["checks"]["has_policy_eligible_source"] is True
    assert data["checks"]["confidence_score_neutral_notes_present"] is True
    assert row["policy"]["primary_source"] == "aod"


def test_real_provider_probe_rendered_report_does_not_include_credentials() -> None:
    location = ObserverLocation("Probe City", "World", 10.0, 20.0, "UTC")
    row = _location_probe_row(location, NasaAodResult.no_credentials(), LocalAtmosphere.not_configured())
    data = _probe_report_data(
        credentials=type(
            "Creds",
            (),
            {
                "source_path": "nasa_login.txt",
                "parse_notes": ("earthdata_password_from_unlabeled", "openaq_api_key_from_label"),
            },
        )(),
        rows=(row,),
    )

    report = render_markdown_report(data)

    assert "secret" not in report.lower()
    assert "token" not in report.lower()
    assert "Credential values stored in report: `False`" in report
