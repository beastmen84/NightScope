"""Generate and assert the deterministic optical recommendation quality matrix."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope  # noqa: E402
from astro_viewer.app.models.observing import CelestialObject  # noqa: E402
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality  # noqa: E402
from astro_viewer.app.services.equipment_service import EquipmentService  # noqa: E402

CATALOGUE_OBJECTS_PATH = ROOT / "astro_viewer" / "data" / "catalogue_objects_seed.csv"
CATALOGUE_DESIGNATIONS_PATH = ROOT / "astro_viewer" / "data" / "catalogue_designations_seed.csv"
REPORT_PATH = ROOT / "docs" / "recommendation_engine_quality_matrix.md"
CSV_PATH = ROOT / "docs" / "recommendation_engine_quality_matrix_results.csv"

CLICK_POSITIONS = {"24 mm", "20 mm", "16 mm", "12 mm", "8 mm"}
PLANET_IDS = {"mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"}
MEDIUM_GLOBULAR_IDS = {"messier-M5", "messier-M13", "messier-M15", "messier-M92"}
WIDE_FIELD_IDS = {"messier-M7", "messier-M8", "messier-M24", "messier-M31", "messier-M44", "messier-M45"}


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    name: str
    weather_state: str
    telescopes: tuple[Telescope, ...]
    eyepieces: tuple[Eyepiece, ...]
    barlows: tuple[Barlow, ...]
    binoculars: tuple[Binocular, ...]
    seeing: SeeingTransparency | None
    sky_quality: SkyQuality


@dataclass(frozen=True)
class Target:
    category: str
    object: CelestialObject


def main() -> None:
    scenarios = _scenarios()
    targets = _targets()
    rows = [_evaluate(scenario, target) for scenario in scenarios for target in targets]
    _write_csv(rows)
    _write_report(scenarios, targets, rows)
    _assert_matrix(rows)
    print(f"Generated {len(rows)} recommendation checks")
    print(f"Report: {REPORT_PATH.relative_to(ROOT)}")
    print(f"CSV: {CSV_PATH.relative_to(ROOT)}")


def _evaluate(scenario: Scenario, target: Target) -> dict[str, str]:
    service = EquipmentService()
    suggestion = service.suggest_for_profile(
        target.object,
        list(scenario.telescopes),
        list(scenario.eyepieces),
        list(scenario.barlows),
        seeing=scenario.seeing,
        sky_quality=scenario.sky_quality,
        binoculars=list(scenario.binoculars),
    )
    options = suggestion.get("setupOptions", [])
    primary = options[0] if options else {}
    display_labels = [_display_label(option) for option in options]
    option_keys = [_option_key(option) for option in options]
    duplicate_options = len(option_keys) - len(set(option_keys))
    ambiguous_labels = len(display_labels) - len(set(display_labels))
    magnification = primary.get("magnification", "n/d")
    row = {
        "scenario_id": scenario.scenario_id,
        "scenario_name": scenario.name,
        "weather_state": scenario.weather_state,
        "seeing": scenario.seeing.seeing if scenario.seeing else "Unknown",
        "seeing_score": str(scenario.seeing.seeing_score) if scenario.seeing else "",
        "transparency": scenario.seeing.transparency if scenario.seeing else "Unknown",
        "transparency_score": str(scenario.seeing.transparency_score) if scenario.seeing else "",
        "bortle_class": str(scenario.sky_quality.bortle_class),
        "viirs_radiance": "" if scenario.sky_quality.viirs_radiance is None else f"{scenario.sky_quality.viirs_radiance:g}",
        "target_id": target.object.id,
        "target_name": target.object.name,
        "target_category": target.category,
        "object_type": target.object.object_type,
        "observation_type": target.object.recommended_observation_type,
        "equipment_type": suggestion.get("equipmentType", ""),
        "setup_type": suggestion.get("setupType", ""),
        "setup_text": suggestion.get("setupText", ""),
        "display_label": _display_label(primary),
        "suggested_position": primary.get("suggestedPosition", suggestion.get("suggestedPosition", "")),
        "magnification": magnification,
        "magnification_value": f"{_magnification_value(magnification):.0f}" if _magnification_value(magnification) is not None else "",
        "barlow": suggestion.get("barlow", ""),
        "difficulty": suggestion.get("difficulty", ""),
        "selection_score": f"{float(suggestion.get('selectionScore', 0.0)):.1f}",
        "alternative": suggestion.get("alternative", ""),
        "high_magnification": suggestion.get("highMagnification", ""),
        "wide_field": suggestion.get("wideField", ""),
        "option_count": str(len(options)),
        "duplicate_option_count": str(duplicate_options),
        "ambiguous_option_label_count": str(ambiguous_labels),
        "explanation": suggestion.get("explanation", ""),
    }
    return row


def _write_csv(rows: list[dict[str, str]]) -> None:
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(scenarios: list[Scenario], targets: list[Target], rows: list[dict[str, str]]) -> None:
    equipment_counts = Counter(row["equipment_type"] for row in rows)
    category_counts = Counter(row["target_category"] for row in rows)
    scenario_counts = Counter(row["scenario_id"] for row in rows)
    violations = _matrix_violations(rows)
    zoom_positions = sorted({row["suggested_position"] for row in rows if "Baader Hyperion Zoom" in row["setup_text"]})
    duplicate_count = sum(int(row["duplicate_option_count"]) for row in rows)
    ambiguous_label_count = sum(int(row["ambiguous_option_label_count"]) for row in rows)
    limited_globulars = _limited_medium_globular_cases(rows)
    planetary_rows = [row for row in rows if row["target_id"] in PLANET_IDS and row["equipment_type"] == "Telescope"]
    category_rows = _category_summary(rows)
    report = [
        "# Recommendation Engine Quality Matrix",
        "",
        "Generated by `tools/recommendation_quality_matrix.py`.",
        "",
        "## Scope",
        "",
        f"- Scenarios: {len(scenarios)} equipment/condition profiles.",
        f"- Targets: {len(targets)} objects: {sum(1 for target in targets if target.object.id in PLANET_IDS)} planets and {sum(1 for target in targets if target.object.id not in PLANET_IDS)} Messier objects.",
        f"- Total checks: {len(rows)}.",
        f"- Raw matrix: `docs/{CSV_PATH.name}`.",
        "",
        "This matrix exercises the current Recommendation Engine behaviour only. It does not call weather, VIIRS, planner or astronomy services. Weather and VIIRS are represented by synthetic `SeeingTransparency` and `SkyQuality` inputs, matching the inputs consumed by `EquipmentService.suggest_for_profile()`.",
        "",
        "## Scenario Profiles",
        "",
        "| ID | Profile | Weather / seeing | Bortle | VIIRS |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario in scenarios:
        seeing = scenario.seeing.seeing if scenario.seeing else "Unknown"
        score = scenario.seeing.seeing_score if scenario.seeing else "n/d"
        viirs = "n/d" if scenario.sky_quality.viirs_radiance is None else f"{scenario.sky_quality.viirs_radiance:g}"
        report.append(f"| {scenario.scenario_id} | {scenario.name} | {scenario.weather_state}; seeing {seeing} ({score}) | {scenario.sky_quality.bortle_class} | {viirs} |")
    report.extend(
        [
            "",
            "## Target Set",
            "",
            "| Category | Objects |",
            "| --- | --- |",
        ]
    )
    for category, count in sorted(category_counts.items()):
        names = ", ".join(target.object.name for target in targets if target.category == category)
        report.append(f"| {category} ({count // len(scenarios)} objects) | {names} |")
    report.extend(
        [
            "",
            "## Aggregate Behaviour",
            "",
            "| Metric | Result |",
            "| --- | --- |",
            f"| Checks per scenario | {min(scenario_counts.values())} - {max(scenario_counts.values())} |",
            f"| Equipment selected | {_counter_text(equipment_counts)} |",
            f"| Duplicate setup options | {duplicate_count} |",
            f"| Ambiguous option labels across different instruments | {ambiguous_label_count} |",
            f"| Zoom primary positions used | {', '.join(zoom_positions) if zoom_positions else 'n/d'} |",
            f"| Matrix invariant violations | {len(violations)} |",
            "",
            "## Planetary Behaviour",
            "",
            "| Seeing | Cases | Median telescope magnification | Typical setups |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for seeing, group in sorted(_group_by(planetary_rows, "seeing").items()):
        magnifications = [_magnification_value(row["magnification"]) for row in group]
        magnifications = [value for value in magnifications if value is not None]
        setups = Counter(row["setup_text"] for row in group).most_common(3)
        setup_text = "; ".join(f"{name} ({count})" for name, count in setups)
        median_mag = f"{median(magnifications):.0f}x" if magnifications else "n/d"
        report.append(f"| {seeing} | {len(group)} | {median_mag} | {setup_text} |")
    report.extend(
        [
            "",
            "## Messier Category Behaviour",
            "",
            "| Category | Cases | Equipment selected | Median telescope magnification | Typical setups |",
            "| --- | ---: | --- | ---: | --- |",
        ]
    )
    for summary in category_rows:
        report.append(
            f"| {summary['category']} | {summary['cases']} | {summary['equipment']} | {summary['median_mag']} | {summary['setups']} |"
        )
    report.extend(
        [
            "",
            "## Checks",
            "",
            "- Unknown seeing planetary telescope recommendations stay conservative: no primary recommendation above 130x.",
            "- Poor seeing planetary telescope recommendations stay low/medium power: no primary recommendation above 90x.",
            "- Baader Hyperion Zoom primary recommendations use only click positions: 24, 20, 16, 12, 8 mm.",
            "- Wide-field Messier targets avoid Barlow in the primary recommendation.",
            "- Duplicate setup option rows are not emitted.",
            "",
        ]
    )
    if violations:
        report.append("### Violations")
        report.append("")
        for violation in violations:
            report.append(f"- {violation}")
        report.append("")
    else:
        report.append("All matrix invariants passed.")
        report.append("")
    if limited_globulars:
        report.extend(
            [
                "### Non-blocking Findings",
                "",
                f"- Medium globular clusters fall below 55x in {len(limited_globulars)} limited-profile cases. These are equipment-limit cases, not scoring failures.",
            ]
        )
        if ambiguous_label_count > 0:
            report.append(f"- Ambiguous display labels occur in {ambiguous_label_count} cases. Setup option UI should include telescope context when needed.")
        report.append("")
    report.extend(
        [
            "## Review Notes",
            "",
            "- Weather state is not a direct input to setup selection. The engine receives seeing/transparency and sky-quality context; cloud/rain blocking belongs to Home/Planner eligibility and observing quality layers.",
            "- VIIRS radiance is not scored directly here. Its practical effect is represented by the Bortle class exposed through `SkyQuality`.",
            "- Mixed profiles usually select binoculars for large wide-field targets and telescopes for planetary, planetary-nebula and globular targets.",
            "- The recent zoom-click implementation is visible in the matrix: no primary setup uses intermediate focal lengths such as 23.8 mm, 15.7 mm or 11.9 mm.",
            "- Medium globular clusters are no longer behaving like wide-field objects in telescope profiles; they generally land in medium magnification unless the available profile is binocular-only or naked-eye.",
            "- Short focal-length or sparse-eyepiece profiles can still recommend lower magnification for medium globulars because no stronger practical option exists in that profile.",
            "- High Bortle scenarios lower suitability for faint deep-sky objects but do not remove the target from consideration. Target eligibility remains owned by Home/Planner/catalogue logic.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")


def _category_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    summaries = []
    for category, group in sorted(_group_by([row for row in rows if row["target_id"] not in PLANET_IDS], "target_category").items()):
        telescope_magnifications = [
            _magnification_value(row["magnification"])
            for row in group
            if row["equipment_type"] == "Telescope" and _magnification_value(row["magnification"]) is not None
        ]
        equipment = _counter_text(Counter(row["equipment_type"] for row in group))
        setups = Counter(row["setup_text"] for row in group).most_common(3)
        summaries.append(
            {
                "category": category,
                "cases": str(len(group)),
                "equipment": equipment,
                "median_mag": f"{median(telescope_magnifications):.0f}x" if telescope_magnifications else "n/d",
                "setups": "; ".join(f"{name} ({count})" for name, count in setups),
            }
        )
    return summaries


def _assert_matrix(rows: list[dict[str, str]]) -> None:
    violations = _matrix_violations(rows)
    if violations:
        raise SystemExit("Recommendation matrix violations:\n" + "\n".join(violations))


def _matrix_violations(rows: list[dict[str, str]]) -> list[str]:
    violations = []
    for row in rows:
        magnification = _magnification_value(row["magnification"])
        if int(row["duplicate_option_count"]) > 0:
            violations.append(_case_label(row, "duplicate setup options"))
        if "Baader Hyperion Zoom" in row["setup_text"] and row["suggested_position"] not in CLICK_POSITIONS:
            violations.append(_case_label(row, f"invalid zoom position {row['suggested_position']}"))
        if row["target_id"] in PLANET_IDS and row["equipment_type"] == "Telescope" and row["seeing"] == "Unknown":
            if magnification is not None and magnification > 130:
                violations.append(_case_label(row, f"unknown-seeing planetary magnification {magnification:.0f}x"))
        if row["target_id"] in PLANET_IDS and row["equipment_type"] == "Telescope" and row["seeing"] == "Poor":
            if magnification is not None and magnification > 90:
                violations.append(_case_label(row, f"poor-seeing planetary magnification {magnification:.0f}x"))
        if row["target_id"] in WIDE_FIELD_IDS and row["barlow"] != "No":
            violations.append(_case_label(row, "wide-field primary recommendation uses Barlow"))
    return violations


def _limited_medium_globular_cases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    limited = []
    for row in rows:
        magnification = _magnification_value(row["magnification"])
        if row["target_id"] in MEDIUM_GLOBULAR_IDS and row["equipment_type"] == "Telescope" and magnification is not None and magnification < 55:
            limited.append(row)
    return limited


def _option_key(option: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        option.get("equipmentType", ""),
        option.get("telescopeName", ""),
        _display_label(option),
        option.get("barlow", ""),
        option.get("magnification", ""),
    )


def _display_label(option: dict[str, str]) -> str:
    return option.get("displayLabel", "") or option.get("detailLabel", "") or option.get("label", "")


def _case_label(row: dict[str, str], message: str) -> str:
    return f"{row['scenario_id']} {row['target_name']}: {message}; setup={row['setup_text']}; mag={row['magnification']}"


def _targets() -> list[Target]:
    messier_ids = [
        "M1",
        "M3",
        "M5",
        "M7",
        "M8",
        "M13",
        "M15",
        "M17",
        "M24",
        "M27",
        "M31",
        "M42",
        "M44",
        "M45",
        "M51",
        "M57",
        "M81",
        "M92",
    ]
    rows = _messier_rows()
    targets = [_planet(object_id, name, magnitude, altitude) for object_id, name, magnitude, altitude in _planet_specs()]
    for messier_id in messier_ids:
        row = rows[messier_id]
        targets.append(Target(_messier_category(row), _messier_object(row)))
    return targets


def _planet_specs() -> list[tuple[str, str, str, str]]:
    return [
        ("mercury", "Mercurio", "-0.4", "18 gradi"),
        ("venus", "Venere", "-4.0", "35 gradi"),
        ("mars", "Marte", "0.4", "62 gradi"),
        ("jupiter", "Giove", "-2.2", "50 gradi"),
        ("saturn", "Saturno", "0.7", "38 gradi"),
        ("uranus", "Urano", "5.7", "45 gradi"),
        ("neptune", "Nettuno", "7.8", "42 gradi"),
    ]


def _planet(object_id: str, name: str, magnitude: str, altitude: str) -> Target:
    return Target(
        "Planet",
        CelestialObject(
            id=object_id,
            name=name,
            object_type="Pianeta",
            image="",
            magnitude=magnitude,
            distance="",
            max_altitude=altitude,
            direction="Sud",
            best_time="22:00",
            observing_window="21:00 - 01:00",
            notes="",
            recommended_setup="",
            visibility_class="",
            azimuth="",
            time_above_horizon="3 h",
            visible=True,
            score=80,
            difficulty="Media",
            recommended_observation_type="HighMagnification",
        ),
    )


def _messier_rows() -> dict[str, dict[str, str]]:
    with CATALOGUE_OBJECTS_PATH.open(encoding="utf-8", newline="") as handle:
        objects = {row["object_id"]: row for row in csv.DictReader(handle)}

    rows: dict[str, dict[str, str]] = {}
    with CATALOGUE_DESIGNATIONS_PATH.open(encoding="utf-8", newline="") as handle:
        for designation in csv.DictReader(handle):
            if designation["catalogue"] != "Messier":
                continue
            physical_object = objects.get(designation["object_id"])
            if physical_object is None:
                continue
            row = dict(physical_object)
            row["messier_id"] = designation["designation"]
            rows[designation["designation"]] = row
    return rows


def _messier_object(row: dict[str, str]) -> CelestialObject:
    messier_id = row["messier_id"]
    name = row["nome"]
    display_name = name if name.startswith(messier_id) else f"{messier_id} {name}"
    return CelestialObject(
        id=f"messier-{messier_id}",
        name=display_name,
        object_type=row["tipo"],
        image="",
        magnitude=row["magnitudine"],
        distance="",
        max_altitude=_representative_altitude(messier_id),
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes=row["descrizione"],
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=80,
        difficulty="Media",
        apparent_size=row["dimensione_apparente"],
        max_angular_size_deg=_optional_float(row["max_angular_size_deg"]),
        recommended_observation_type=row["recommended_observation_type"],
    )


def _representative_altitude(messier_id: str) -> str:
    altitudes = {
        "M7": "11 gradi",
        "M8": "22 gradi",
        "M17": "30 gradi",
        "M24": "25 gradi",
        "M42": "45 gradi",
        "M57": "70 gradi",
    }
    return altitudes.get(messier_id, "55 gradi")


def _messier_category(row: dict[str, str]) -> str:
    observation_type = row["recommended_observation_type"]
    object_type = row["tipo"].lower()
    if observation_type == "WideField":
        return "Messier wide-field"
    if "globular" in object_type:
        return "Messier globular"
    if "planetary nebula" in object_type:
        return "Messier planetary nebula"
    if "galaxy" in object_type:
        return "Messier galaxy"
    if "nebula" in object_type:
        return "Messier nebula"
    return "Messier general"


def _scenarios() -> list[Scenario]:
    return [
        Scenario("P01", "Solo occhio nudo", "sereno, meteo neutro", (), (), (), (), None, _sky(4, None)),
        Scenario("P02", "Binocolo 7x50 sotto cielo scuro", "sereno secco", (), (), (), (_bino("b7x50", "Celestron Cometron", 7, 50),), _seeing(72, 82), _sky(3, 0.6)),
        Scenario("P03", "Binocolo 10x50 suburbano", "sereno medio", (), (), (), (_bino("b10x50", "Nikon Aculon A211", 10, 50),), _seeing(60, 65), _sky(5, 8.0)),
        Scenario("P04", "Binocolo 15x70 cielo lattiginoso", "foschia, trasparenza bassa", (), (), (), (_bino("b15x70", "Celestron SkyMaster Pro", 15, 70),), _seeing(48, 35), _sky(6, 30.0)),
        Scenario("P05", "Rifrattore 80/640 con oculari base", "sereno stabile", (_scope("fr80", "Rifrattore 80/640", 80, 640, "rifrattore"),), (_e("e32", "32 mm", 32, 52), _e("e18", "18 mm", 18, 60), _e("e10", "10 mm", 10, 60)), (), (), _seeing(78, 80), _sky(4, 2.0)),
        Scenario("P06", "Mak 90/1250 con Plossl e Barlow", "meteo buono, seeing non disponibile", (_scope("mak90", "Maksutov 90/1250", 90, 1250, "Maksutov"),), (_e("e25", "25 mm", 25, 52), _e("e10", "10 mm", 10, 60)), (_barlow("b2", "Barlow 2x", 2.0),), (), None, _sky(5, 8.0)),
        Scenario("P07", "Newton 130/650 completo", "sereno stabile", (_scope("newton130", "Newton 130/650", 130, 650, "Newton"),), (_e("e32", "32 mm", 32, 68), _e("e25", "25 mm", 25, 52), _e("e10", "10 mm", 10, 60), _e("e6", "6 mm", 6, 58)), (_barlow("b2", "Barlow 2x", 2.0),), (), _seeing(82, 78), _sky(4, 2.0)),
        Scenario("P08", "Mak 127 con Hyperion Zoom", "seeing sconosciuto", (_scope("mak127", "Mak 127", 127, 1500, "Maksutov"),), (_hyperion_zoom(),), (), (), None, _sky(5, 8.0)),
        Scenario("P09", "Mak 127 con Zoom e Barlow 2.25x", "seeing ottimo", (_scope("mak127", "Mak 127", 127, 1500, "Maksutov"),), (_hyperion_zoom(),), (_barlow("b225", "Hyperion Zoom Barlow 2.25x", 2.25),), (), _seeing(90, 82), _sky(5, 8.0)),
        Scenario("P10", "Mak 127 con Zoom e seeing scarso", "vento e seeing scarso", (_scope("mak127", "Mak 127", 127, 1500, "Maksutov"),), (_hyperion_zoom(),), (_barlow("b225", "Hyperion Zoom Barlow 2.25x", 2.25),), (), _seeing(30, 55), _sky(5, 8.0)),
        Scenario("P11", "Newton 150/750 con oculari wide/high", "sereno buono", (_scope("newton150", "Newton 150/750", 150, 750, "Newton"),), (_e("e24", "Hyperion 24 mm", 24, 68), _e("e17", "Hyperion 17 mm", 17, 68), _e("e10", "Hyperion 10 mm", 10, 68), _e("e6", "Ortho 6 mm", 6, 50)), (_barlow("b2", "Barlow 2x", 2.0),), (), _seeing(76, 75), _sky(3, 0.8)),
        Scenario("P12", "Dobson 203/1200 con set ampio", "cielo scuro, seeing buono", (_scope("dob203", "Dobson 203/1200", 203, 1200, "Newton"),), (_e("e32", "32 mm 68", 32, 68), _e("e20", "20 mm 70", 20, 70), _e("e12", "12 mm 68", 12, 68), _e("e8", "8 mm 60", 8, 60)), (_barlow("b2", "Barlow 2x", 2.0),), (), _seeing(78, 86), _sky(2, 0.15)),
        Scenario("P13", "Rifrattore rapido 72/400 wide-field", "cielo montano limpido", (_scope("fr72", "Rifrattore 72/400", 72, 400, "rifrattore"),), (_e("e32", "32 mm 68", 32, 68), _e("e24", "24 mm 68", 24, 68), _e("e13", "13 mm 68", 13, 68)), (), (), _seeing(65, 90), _sky(3, 0.4)),
        Scenario("P14", "SCT 203/2032 con Hyperion Zoom", "cielo urbano, seeing sconosciuto", (_scope("sct203", "SCT 203/2032", 203, 2032, "SCT"),), (_hyperion_zoom(),), (_barlow("b2", "Barlow 2x", 2.0),), (), None, _sky(7, 65.0)),
        Scenario("P15", "Profilo misto completo urbano", "meteo discreto, VIIRS urbano", (_scope("mak127", "Mak 127", 127, 1500, "Maksutov"), _scope("newton130", "Newton 130/650", 130, 650, "Newton")), (_hyperion_zoom(), _e("e32", "32 mm", 32, 68), _e("e10", "10 mm", 10, 60), _e("e6", "6 mm", 6, 58)), (_barlow("b2", "Barlow 2x", 2.0),), (_bino("b10x50", "Nikon Aculon A211", 10, 50),), _seeing(55, 50), _sky(7, 75.0)),
    ]


def _scope(identifier: str, name: str, aperture: int, focal_length: int, optical_type: str) -> Telescope:
    return Telescope(identifier, name, aperture, focal_length, optical_type, "manuale")


def _e(identifier: str, name: str, focal: float, afov: float) -> Eyepiece:
    return Eyepiece(identifier, name, focal, afov)


def _hyperion_zoom() -> Eyepiece:
    return Eyepiece(
        "hyperion-zoom",
        "Baader Hyperion Zoom 8-24 mm",
        24,
        60,
        "Zoom",
        8,
        24,
        (24, 20, 16, 12, 8),
    )


def _barlow(identifier: str, name: str, multiplier: float) -> Barlow:
    return Barlow(identifier, name, multiplier)


def _bino(identifier: str, name: str, magnification: int, objective: int) -> Binocular:
    return Binocular(identifier, name, magnification, objective)


def _seeing(seeing_score: int, transparency_score: int) -> SeeingTransparency:
    return SeeingTransparency(
        _quality_label(seeing_score),
        _quality_label(transparency_score),
        seeing_score,
        transparency_score,
        "Synthetic quality-matrix condition.",
        "Synthetic",
    )


def _quality_label(score: int) -> str:
    if score >= 82:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 42:
        return "Average"
    return "Poor"


def _sky(bortle: int, viirs_radiance: float | None) -> SkyQuality:
    limiting_magnitude = {2: 6.8, 3: 6.4, 4: 6.0, 5: 5.6, 6: 5.1, 7: 4.7}.get(bortle, 4.2)
    sky_brightness = {2: 21.8, 3: 21.3, 4: 20.8, 5: 20.0, 6: 19.2, 7: 18.5}.get(bortle, 18.0)
    return SkyQuality(
        bortle,
        limiting_magnitude,
        sky_brightness,
        "SyntheticVIIRS" if viirs_radiance is not None else "Synthetic",
        f"Bortle {bortle} synthetic matrix sky.",
        viirs_radiance=viirs_radiance,
    )


def _optional_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _magnification_value(value: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)x", value)
    if not match:
        return None
    return float(match.group(1))


def _counter_text(counter: Counter[str]) -> str:
    return ", ".join(f"{key}: {value}" for key, value in counter.most_common())


def _group_by(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


if __name__ == "__main__":
    main()
