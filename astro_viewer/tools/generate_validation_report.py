from __future__ import annotations

import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.messier_repository import MessierRepository


BODY_NAMES = {"Sole", "Luna", "Giove", "Saturno", "Venere"}
VALIDATION_LOCATIONS = [
    ObserverLocation("Addis Ababa", "Etiopia", 9.03, 38.74, "Africa/Addis_Ababa"),
    ObserverLocation("Roma", "Italia", 41.9028, 12.4964, "Europe/Rome"),
    ObserverLocation("Milano", "Italia", 45.4642, 9.19, "Europe/Rome"),
    ObserverLocation("Cape Town", "Sudafrica", -33.9249, 18.4241, "Africa/Johannesburg"),
    ObserverLocation("Oslo", "Norvegia", 59.9139, 10.7522, "Europe/Oslo"),
]


@dataclass(frozen=True)
class ValidationResult:
    location: str
    body: str
    altitude_ok: bool
    azimuth_ok: bool
    event_order_ok: bool
    notes: str

    @property
    def passed(self) -> bool:
        return self.altitude_ok and self.azimuth_ok and self.event_order_ok


def validate_astronomy(base_dir: Path, database_path: Path | None = None) -> list[ValidationResult]:
    database_path = database_path or base_dir.parent / "nightscope.db"
    initialize_database(database_path, base_dir / "data" / "schema.sql")
    engine = SkyfieldAstronomyEngine(base_dir / "data", MessierRepository(database_path))

    try:
        results: list[ValidationResult] = []
        for location in VALIDATION_LOCATIONS:
            objects = {item.name: item for item in engine.solar_system_objects(location) if item.name in BODY_NAMES}
            for config in engine.BODY_CONFIGS:
                if config.name not in BODY_NAMES:
                    continue
                item = objects[config.name]
                altitude = _parse_degrees(item.current_altitude)
                azimuth = _parse_degrees(item.current_azimuth)
                order_ok = _event_order_ok(engine, config, location)
                notes = f"alt={altitude:.1f}, az={azimuth:.1f}, rise={item.rise_time}, transit={item.culmination_time}, set={item.set_time}"
                results.append(
                    ValidationResult(
                        location=f"{location.city}, {location.country}",
                        body=config.name,
                        altitude_ok=-90.0 <= altitude <= 90.0,
                        azimuth_ok=0.0 <= azimuth <= 360.0,
                        event_order_ok=order_ok,
                        notes=notes,
                    )
                )
        return results
    finally:
        engine.close()


def write_report(base_dir: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        results = validate_astronomy(base_dir, Path(temp_dir) / "nightscope.db")
    passed_count = len([item for item in results if item.passed])
    lines = [
        "# NightScope Astronomy Validation Report",
        "",
        f"Generated: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"Checks passed: {passed_count}/{len(results)}",
        "",
        "| Location | Body | Altitude | Azimuth | Events | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            "| {location} | {body} | {altitude} | {azimuth} | {events} | {notes} |".format(
                location=result.location,
                body=result.body,
                altitude=_label(result.altitude_ok),
                azimuth=_label(result.azimuth_ok),
                events=_label(result.event_order_ok),
                notes=result.notes,
            )
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_degrees(value: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        raise ValueError(f"Cannot parse angle from {value!r}")
    return float(match.group(0))


def _event_order_ok(engine: SkyfieldAstronomyEngine, config, location: ObserverLocation) -> bool:
    zone = engine._zone(location)
    now = datetime.now(zone)
    start = datetime.combine(now.date(), time(0, 0), tzinfo=zone)
    end = start + timedelta(hours=48)
    observer = engine._observer(location)
    body = engine._ephemeris[config.body_key]
    rises = engine._event_datetimes(engine_module_almanac_find("rise"), observer, body, start, end, zone)
    transits = engine._transit_datetimes(observer, body, start, end, zone)
    settings = engine._event_datetimes(engine_module_almanac_find("set"), observer, body, start, end, zone)
    if not rises or not transits or not settings:
        return True
    for rise_dt in rises:
        transit_dt = next((candidate for candidate in transits if candidate >= rise_dt), None)
        setting_dt = next((candidate for candidate in settings if transit_dt and candidate >= transit_dt), None)
        if transit_dt and setting_dt and rise_dt <= transit_dt <= setting_dt:
            return True
    return False


def engine_module_almanac_find(kind: str):
    from skyfield import almanac

    return almanac.find_risings if kind == "rise" else almanac.find_settings


def _label(value: bool) -> str:
    return "OK" if value else "FAIL"


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    output_path = base_dir / "reports" / "astronomy_validation_report.md"
    write_report(base_dir, output_path)
    print(f"Report written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
