from __future__ import annotations

import csv
import math
import sqlite3
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


GEONAMES_COLUMNS = (
    "geonameid",
    "name",
    "asciiname",
    "alternatenames",
    "latitude",
    "longitude",
    "feature_class",
    "feature_code",
    "country_code",
    "cc2",
    "admin1_code",
    "admin2_code",
    "admin3_code",
    "admin4_code",
    "population",
    "elevation",
    "dem",
    "timezone",
    "modification_date",
)


@dataclass(frozen=True)
class GeoNamesCity:
    geonameid: str
    city_name: str
    ascii_name: str
    country: str
    country_code: str
    admin_region: str
    latitude: float
    longitude: float
    timezone: str
    population: int | None
    aliases: set[str]

    @property
    def search_name(self) -> str:
        return build_search_name(self.city_name, self.ascii_name, self.country, self.country_code, self.admin_region, self.aliases)


@dataclass
class GeoNamesImportReport:
    total_rows_read: int = 0
    total_imported: int = 0
    duplicates_skipped: int = 0
    duplicates_merged: int = 0
    aliases_added: int = 0
    cities_missing_timezone: int = 0
    rows_skipped_non_city: int = 0
    rows_skipped_invalid: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def import_geonames_cities(
    connection: sqlite3.Connection,
    source_path: Path,
    country_info_path: Path | None = None,
    admin1_codes_path: Path | None = None,
    proximity_km: float = 5.0,
    progress_callback: Callable[[int], None] | None = None,
    progress_interval: int = 500,
) -> GeoNamesImportReport:
    report = GeoNamesImportReport()
    country_names = _load_country_names(country_info_path)
    admin_names = _load_admin1_names(admin1_codes_path)

    for raw_row in _iter_source_rows(source_path):
        report.total_rows_read += 1
        if progress_callback and report.total_rows_read % progress_interval == 0:
            progress_callback(report.total_rows_read)
        city = _city_from_row(raw_row, country_names, admin_names)
        if city is None:
            if _is_non_city_row(raw_row):
                report.rows_skipped_non_city += 1
            else:
                report.rows_skipped_invalid += 1
            continue
        if not city.timezone:
            report.cities_missing_timezone += 1
            continue

        duplicate = _find_duplicate_city(connection, city, proximity_km)
        if duplicate:
            added = _merge_city_aliases(connection, duplicate, city)
            report.duplicates_skipped += 1
            report.duplicates_merged += 1
            report.aliases_added += added
            continue

        city_id = _insert_city(connection, city)
        report.total_imported += 1
        report.aliases_added += _insert_aliases(connection, city_id, city.aliases, "geonames")

    if progress_callback:
        progress_callback(report.total_rows_read)
    return report


def build_search_name(
    city_name: str,
    ascii_name: str,
    country: str,
    country_code: str,
    admin_region: str,
    aliases: set[str] | list[str] | str,
) -> str:
    if isinstance(aliases, str):
        alias_values = _split_aliases(aliases)
    else:
        alias_values = set(aliases)
    values = {city_name, ascii_name, country, country_code, admin_region, *alias_values}
    normalized = sorted({_normalize_search(value) for value in values if value and _normalize_search(value)})
    return " ".join(normalized)


def aliases_to_text(aliases: set[str]) -> str:
    return "|".join(sorted(alias.strip() for alias in aliases if alias.strip()))


def _iter_source_rows(source_path: Path):
    with source_path.open("r", encoding="utf-8", newline="") as file:
        sample = file.read(4096)
        file.seek(0)
        if "\t" in sample:
            for values in csv.reader(file, delimiter="\t"):
                if not values or values[0].startswith("#"):
                    continue
                padded = values + [""] * (len(GEONAMES_COLUMNS) - len(values))
                yield dict(zip(GEONAMES_COLUMNS, padded))
        else:
            yield from csv.DictReader(file)


def _city_from_row(raw_row: dict, country_names: dict[str, str], admin_names: dict[str, str]) -> GeoNamesCity | None:
    if _is_non_city_row(raw_row):
        return None
    name = (raw_row.get("name") or raw_row.get("city_name") or "").strip()
    ascii_name = (raw_row.get("asciiname") or raw_row.get("ascii_name") or name).strip()
    country_code = (raw_row.get("country_code") or "").strip().upper()
    country = (raw_row.get("country") or country_names.get(country_code) or country_code).strip()
    admin_code = (raw_row.get("admin1_code") or "").strip()
    admin_region = (raw_row.get("admin_region") or admin_names.get(f"{country_code}.{admin_code}") or admin_code).strip()
    timezone = (raw_row.get("timezone") or "").strip()
    try:
        latitude = float(raw_row.get("latitude") or "")
        longitude = float(raw_row.get("longitude") or "")
    except ValueError:
        return None
    if not name or not country_code or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    population = _optional_int(raw_row.get("population"))
    aliases = _split_aliases(raw_row.get("alternatenames") or raw_row.get("aliases") or "")
    aliases.update({name, ascii_name})
    aliases = _clean_city_aliases(
        aliases,
        {country, country_code, admin_region, admin_code},
        protected_aliases={name, ascii_name},
    )
    return GeoNamesCity(
        geonameid=str(raw_row.get("geonameid") or ""),
        city_name=name,
        ascii_name=ascii_name,
        country=country,
        country_code=country_code,
        admin_region=admin_region,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        population=population,
        aliases=aliases,
    )


def _is_non_city_row(raw_row: dict) -> bool:
    feature_class = (raw_row.get("feature_class") or "").strip()
    feature_code = (raw_row.get("feature_code") or "").strip()
    if feature_class:
        return feature_class != "P"
    if feature_code:
        return not feature_code.startswith("PPL")
    return False


def _find_duplicate_city(connection: sqlite3.Connection, city: GeoNamesCity, proximity_km: float) -> sqlite3.Row | None:
    delta = max(proximity_km / 111.0, 0.01)
    connection.row_factory = sqlite3.Row
    candidates = connection.execute(
        """
        SELECT id, city_name, ascii_name, country, country_code, admin_region,
               latitude, longitude, timezone, population, aliases, search_name
        FROM City
        WHERE country_code = ?
          AND timezone = ?
          AND ABS(latitude - ?) <= ?
          AND ABS(longitude - ?) <= ?
        """,
        (city.country_code, city.timezone, city.latitude, delta, city.longitude, delta),
    ).fetchall()
    city_aliases = {_normalize_search(alias) for alias in city.aliases if _normalize_search(alias)}
    for candidate in candidates:
        if _distance_km(city.latitude, city.longitude, candidate["latitude"], candidate["longitude"]) > proximity_km:
            continue
        candidate_aliases = _candidate_aliases(connection, candidate)
        if city_aliases & candidate_aliases:
            return candidate
        if _normalize_search(city.ascii_name) == _normalize_search(candidate["ascii_name"] or ""):
            return candidate
    return None


def _candidate_aliases(connection: sqlite3.Connection, candidate: sqlite3.Row) -> set[str]:
    aliases = {
        candidate["city_name"] or "",
        candidate["ascii_name"] or "",
        *(candidate["aliases"] or "").split("|"),
    }
    rows = connection.execute(
        "SELECT normalized_alias FROM CityAlias WHERE city_id = ?",
        (candidate["id"],),
    ).fetchall()
    aliases.update(row["normalized_alias"] for row in rows)
    return {_normalize_search(alias) for alias in aliases if alias and _normalize_search(alias)}


def _insert_city(connection: sqlite3.Connection, city: GeoNamesCity) -> int:
    aliases = aliases_to_text(city.aliases)
    cursor = connection.execute(
        """
        INSERT INTO City (
            city_name, ascii_name, country, country_code, admin_region,
            latitude, longitude, timezone, population, aliases, search_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            city.city_name,
            city.ascii_name,
            city.country,
            city.country_code,
            city.admin_region,
            city.latitude,
            city.longitude,
            city.timezone,
            city.population,
            aliases,
            city.search_name,
        ),
    )
    return int(cursor.lastrowid)


def _merge_city_aliases(connection: sqlite3.Connection, duplicate: sqlite3.Row, city: GeoNamesCity) -> int:
    existing_aliases = set((duplicate["aliases"] or "").split("|"))
    merged_aliases = {alias for alias in existing_aliases if alias}
    merged_aliases.update(city.aliases)
    merged_aliases = _clean_city_aliases(
        merged_aliases,
        {
            duplicate["country"] or "",
            duplicate["country_code"] or "",
            duplicate["admin_region"] or "",
            city.country,
            city.country_code,
            city.admin_region,
        },
        protected_aliases={
            duplicate["city_name"] or "",
            duplicate["ascii_name"] or "",
            city.city_name,
            city.ascii_name,
        },
    )
    population = max(duplicate["population"] or 0, city.population or 0) or None
    search_name = build_search_name(
        duplicate["city_name"],
        duplicate["ascii_name"] or city.ascii_name,
        duplicate["country"] or city.country,
        duplicate["country_code"] or city.country_code,
        duplicate["admin_region"] or city.admin_region,
        merged_aliases,
    )
    connection.execute(
        """
        UPDATE City
        SET aliases = ?,
            search_name = ?,
            population = ?,
            ascii_name = COALESCE(NULLIF(ascii_name, ''), ?),
            admin_region = COALESCE(NULLIF(admin_region, ''), ?)
        WHERE id = ?
        """,
        (
            aliases_to_text(merged_aliases),
            search_name,
            population,
            city.ascii_name,
            city.admin_region,
            duplicate["id"],
        ),
    )
    return _insert_aliases(connection, duplicate["id"], merged_aliases, "geonames")


def _insert_aliases(connection: sqlite3.Connection, city_id: int, aliases: set[str], source: str) -> int:
    added = 0
    for alias in sorted(alias.strip() for alias in aliases if alias.strip()):
        normalized = _normalize_search(alias)
        if not _is_valid_city_alias(normalized):
            continue
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO CityAlias (city_id, alias, normalized_alias, source)
            VALUES (?, ?, ?, ?)
            """,
            (city_id, alias, normalized, source),
        )
        added += cursor.rowcount
    return added


def _load_country_names(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    result: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.reader(file, delimiter="\t"):
            if not row or row[0].startswith("#") or len(row) < 5:
                continue
            result[row[0].upper()] = row[4]
    return result


def _load_admin1_names(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    result: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.reader(file, delimiter="\t"):
            if len(row) >= 2:
                result[row[0]] = row[1]
    return result


def _split_aliases(value: str) -> set[str]:
    aliases: set[str] = set()
    for chunk in value.replace("|", ",").split(","):
        alias = chunk.strip()
        if alias:
            aliases.add(alias)
    return aliases


def _clean_city_aliases(
    aliases: set[str],
    context_values: set[str],
    protected_aliases: set[str] | None = None,
) -> set[str]:
    context_aliases = {_normalize_search(value) for value in context_values if value and _normalize_search(value)}
    protected = {
        _normalize_search(value)
        for value in (protected_aliases or set())
        if value and _normalize_search(value)
    }
    return {
        alias
        for alias in aliases
        if _is_valid_city_alias(_normalize_search(alias))
        and (_normalize_search(alias) not in context_aliases or _normalize_search(alias) in protected)
    }


def _is_valid_city_alias(normalized_alias: str) -> bool:
    return bool(normalized_alias) and not normalized_alias.isdigit()


def _optional_int(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def _normalize_search(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(ascii_value.replace("-", " ").replace("_", " ").replace(",", " ").split())


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))
