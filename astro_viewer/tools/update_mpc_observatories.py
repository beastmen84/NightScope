"""Regenerate or verify the pinned MPC observatory seed with structural safeguards."""

from __future__ import annotations

import argparse
import csv
import json
import math
import unicodedata
from pathlib import Path

import requests


API_URL = "https://data.minorplanetcenter.net/api/obscodes"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "astro_viewer" / "data" / "mpc_observatories_seed.csv"
FIELDNAMES = (
    "mpc_code",
    "name",
    "short_name",
    "latitude",
    "longitude",
    "elevation_m",
    "rho_cos_phi",
    "rho_sin_phi",
    "observations_type",
    "first_date",
    "last_date",
    "web_link",
    "old_names",
    "source_updated_at",
    "search_name",
)
NON_FIXED_TYPES = {"roving", "satellite"}
WGS84_SEMI_MAJOR_AXIS_M = 6_378_137.0
WGS84_FLATTENING = 1 / 298.257_223_563


def update_snapshot(output_path: Path = DEFAULT_OUTPUT) -> list[dict[str, str]]:
    response = requests.get(API_URL, json={}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("MPC observatory response is not an object.")
    rows = snapshot_rows(payload)
    _validate_rows(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def snapshot_rows(payload: dict[str, object]) -> list[dict[str, str]]:
    rows = []
    for source_key, raw_value in payload.items():
        if not isinstance(raw_value, dict):
            continue
        row = _snapshot_row(str(source_key), raw_value)
        if row is not None:
            rows.append(row)
    return sorted(rows, key=lambda item: item["mpc_code"])


def geodetic_coordinates(
    rho_cos_phi: float,
    rho_sin_phi: float,
) -> tuple[float, float]:
    """Convert MPC parallax constants to WGS84 latitude and ellipsoid height."""
    semi_major = WGS84_SEMI_MAJOR_AXIS_M
    flattening = WGS84_FLATTENING
    semi_minor = semi_major * (1 - flattening)
    eccentricity_sq = flattening * (2 - flattening)
    second_eccentricity_sq = (
        (semi_major * semi_major - semi_minor * semi_minor)
        / (semi_minor * semi_minor)
    )
    horizontal = rho_cos_phi * semi_major
    vertical = rho_sin_phi * semi_major
    theta = math.atan2(vertical * semi_major, horizontal * semi_minor)
    latitude = math.atan2(
        vertical
        + second_eccentricity_sq * semi_minor * math.sin(theta) ** 3,
        horizontal
        - eccentricity_sq * semi_major * math.cos(theta) ** 3,
    )
    prime_vertical_radius = semi_major / math.sqrt(
        1 - eccentricity_sq * math.sin(latitude) ** 2
    )
    elevation = horizontal / math.cos(latitude) - prime_vertical_radius
    return math.degrees(latitude), elevation


def validate_snapshot(path: Path = DEFAULT_OUTPUT) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != FIELDNAMES:
            raise ValueError("MPC observatory snapshot columns are not current.")
        rows = list(reader)
    _validate_rows(rows)
    return rows


def _snapshot_row(source_key: str, raw: dict[str, object]) -> dict[str, str] | None:
    code = str(raw.get("obscode") or source_key).strip().upper()
    observations_type = str(raw.get("observations_type") or "").strip().lower()
    if observations_type in NON_FIXED_TYPES:
        return None
    try:
        longitude = float(raw["longitude"])
        rho_cos_phi = float(raw["rhocosphi"])
        rho_sin_phi = float(raw["rhosinphi"])
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in (longitude, rho_cos_phi, rho_sin_phi)):
        return None
    if math.hypot(rho_cos_phi, rho_sin_phi) < 0.5:
        return None
    latitude, elevation = geodetic_coordinates(rho_cos_phi, rho_sin_phi)
    longitude = ((longitude + 180.0) % 360.0) - 180.0
    name = _text(raw.get("name_utf8")) or _text(raw.get("name"))
    if not code or not name or not -90 <= latitude <= 90:
        return None
    old_names_value = raw.get("old_names")
    old_names = (
        [_text(value) for value in old_names_value if _text(value)]
        if isinstance(old_names_value, list)
        else []
    )
    short_name = _text(raw.get("short_name"))
    search_name = _normalize_search(
        " ".join((code, name, short_name, *old_names))
    )
    return {
        "mpc_code": code,
        "name": name,
        "short_name": short_name,
        "latitude": f"{latitude:.8f}",
        "longitude": f"{longitude:.8f}",
        "elevation_m": f"{elevation:.3f}",
        "rho_cos_phi": f"{rho_cos_phi:.8f}",
        "rho_sin_phi": f"{rho_sin_phi:.8f}",
        "observations_type": observations_type,
        "first_date": _text(raw.get("firstdate")),
        "last_date": _text(raw.get("lastdate")),
        "web_link": _text(raw.get("web_link")),
        "old_names": "|".join(old_names),
        "source_updated_at": _text(raw.get("updated_at")),
        "search_name": search_name,
    }


def _validate_rows(rows: list[dict[str, str]]) -> None:
    if len(rows) < 2_500:
        raise ValueError(f"MPC observatory snapshot is unexpectedly small: {len(rows)} rows.")
    codes = [row["mpc_code"] for row in rows]
    if len(codes) != len(set(codes)):
        raise ValueError("MPC observatory snapshot contains duplicate codes.")
    if codes != sorted(codes):
        raise ValueError("MPC observatory snapshot is not sorted by code.")
    if "R50" not in set(codes):
        raise ValueError("MPC observatory snapshot does not contain R50.")
    for row in rows:
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError(f"Invalid coordinates for MPC {row['mpc_code']}.")


def _normalize_search(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(ascii_value.replace("-", " ").replace("_", " ").split())


def _text(value: object) -> str:
    return str(value or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update or validate NightScope's offline MPC observatory snapshot."
    )
    parser.add_argument("--check", action="store_true", help="validate the packaged snapshot without network access")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = validate_snapshot(args.output) if args.check else update_snapshot(args.output)
    mode = "validated" if args.check else "updated"
    print(json.dumps({"status": mode, "rows": len(rows), "path": str(args.output)}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
