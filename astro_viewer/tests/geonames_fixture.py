from __future__ import annotations

from pathlib import Path


def write_small_geonames_fixture(data_dir: Path, extra_rows: int = 120) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        _geonames_row(
            "344979",
            "Addis Ababa",
            "Addis Ababa",
            "Addis Abeba,Finfinne",
            "9.03",
            "38.74",
            "ET",
            "AA",
            "3041002",
            "Africa/Addis_Ababa",
        ),
        _geonames_row("3169070", "Rome", "Rome", "Roma", "41.8919", "12.5113", "IT", "07", "2318895", "Europe/Rome"),
        _geonames_row("3173435", "Milan", "Milan", "Milano", "45.4643", "9.1895", "IT", "09", "1371498", "Europe/Rome"),
    ]
    for index in range(extra_rows):
        rows.append(
            _geonames_row(
                str(900000 + index),
                f"Fixture City {index:03d}",
                f"Fixture City {index:03d}",
                "",
                f"{30.0 + index / 1000:.4f}",
                f"{-90.0 - index / 1000:.4f}",
                "US",
                "NY",
                str(15000 + index),
                "America/New_York",
            )
        )
    (data_dir / "cities15000.txt").write_text("\n".join(rows), encoding="utf-8")
    (data_dir / "countryInfo.txt").write_text(
        "\n".join(
            [
                "ET\tETH\t231\tET\tEtiopia",
                "IT\tITA\t380\tIT\tItalia",
                "US\tUSA\t840\tUS\tUnited States",
            ]
        ),
        encoding="utf-8",
    )


def _geonames_row(
    geoname_id: str,
    name: str,
    ascii_name: str,
    alternate_names: str,
    latitude: str,
    longitude: str,
    country_code: str,
    admin1_code: str,
    population: str,
    timezone: str,
) -> str:
    columns = [
        geoname_id,
        name,
        ascii_name,
        alternate_names,
        latitude,
        longitude,
        "P",
        "PPLC",
        country_code,
        "",
        admin1_code,
        "",
        "",
        "",
        population,
        "",
        "",
        timezone,
        "2026-01-01",
    ]
    return "\t".join(columns)
