from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_nsom_comparison import EquipmentNsomComparisonService


REPORT_PATH = Path("docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md")


@dataclass(frozen=True)
class EquipmentScenario:
    scenario_id: str
    label: str
    target_profile: str
    equipment_profile: str
    sky_profile: str
    seeing_profile: str
    expectation: str
    target: CelestialObject
    telescopes: tuple[Telescope, ...]
    eyepieces: tuple[Eyepiece, ...]
    barlows: tuple[Barlow, ...]
    binoculars: tuple[Binocular, ...]
    sky_quality: SkyQuality
    seeing: SeeingTransparency | None
    moon: MoonSummary | None
    confidence: RecommendationConfidence


def generate_report_data() -> dict[str, object]:
    scenarios = tuple(_evaluate_scenario(scenario) for scenario in _scenarios())
    rows = tuple(row for scenario in scenarios for row in scenario["candidates"])
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "equipment_recommendations_changed": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
            "candidate_row_count": len(rows),
        },
        "scenarios": scenarios,
        "summary": _summary(scenarios, rows),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_report_data() if data is None else data
    metadata = report_data["metadata"]
    summary = report_data["summary"]

    lines = [
        "# Equipment NSOM Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report compares current EquipmentService setup "
            "ranking with NSOM ObserverCapability/Q_target projections. It does "
            "not change equipment recommendations, Planner, Home, Best Object, "
            "Sky Compass, Detail/Object, QML, logging, network behaviour or "
            "runtime file writes."
        ),
        "Roadmap label: Equipment/ObserverCapability NSOM comparison.",
        (
            f"The matrix covers {metadata['scenario_count']} deterministic scenarios "
            f"and {metadata['candidate_row_count']} candidate rows."
        ),
        "",
        "## Methodology",
        "",
        "- Uses `EquipmentNsomComparisonService` with fixed in-memory fixtures only.",
        "- Legacy formula is the real EquipmentService component sum.",
        "- NSOM ObserverCapability is projected from each candidate configuration.",
        "- Q_target is target-class specific and affects PracticalTargetValue only.",
        "- Sky quality and seeing are identified as ownership-mixing in legacy Equipment scoring.",
        "- RecommendationConfidence remains metadata and never modifies score.",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Target | Equipment | Sky | Seeing | Expected behaviour |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in report_data["scenarios"]:
        axes = scenario["axes"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    str(axes["target_profile"]),
                    str(axes["equipment_profile"]),
                    str(axes["sky_profile"]),
                    str(axes["seeing_profile"]),
                    str(scenario["expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Candidate Ranking Comparison",
            "",
            "| Scenario | Legacy Equipment Top | NSOM Q_target Top | NSOM Practical Top | Candidate Count |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for scenario in report_data["scenarios"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    _top_label(scenario["rankings"]["legacy_equipment_score"]),
                    _top_label(scenario["rankings"]["nsom_q_target"]),
                    _top_label(scenario["rankings"]["nsom_practical_target_value"]),
                    str(len(scenario["candidates"])),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Candidate Details",
            "",
            "| Scenario | Candidate | Legacy Score | Q_target | Practical | Legacy Main Component | Legacy Ownership Mixing |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        for row in scenario["candidates"][:8]:
            legacy = row["legacy"]
            nsom = row["nsom"]
            main_component = max(legacy["components"].items(), key=lambda item: float(item[1]))
            ownership = legacy["ownership_mixing"]
            mixed = [
                name
                for name, info in ownership.items()
                if info.get("mixed_into_equipment_score") is True
            ]
            lines.append(
                "| "
                + " | ".join(
                    (
                        str(scenario["scenario_id"]),
                        str(row["label"]),
                        f"{float(legacy['score']):.2f}",
                        f"{float(nsom['observer_capability']['q_target']):.3f}",
                        f"{float(nsom['practical_target_value']['value']):.2f}",
                        f"{main_component[0]}={float(main_component[1]):.2f}",
                        ", ".join(mixed),
                    )
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Main Findings",
            "",
        ]
    )
    for item in summary["findings"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "",
            "1. Review whether Equipment should get a default-off NSOM path or remain a practical setup helper.",
            "2. Decide how seeing/transparency should flow into ObserverCapability versus ObservationEnvironment.",
            "3. Keep EquipmentService runtime ranking unchanged until that policy is explicit.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(scenario: EquipmentScenario) -> dict[str, object]:
    comparison = EquipmentNsomComparisonService().compare(
        scenario.target,
        sky_quality=scenario.sky_quality,
        telescopes=scenario.telescopes,
        eyepieces=scenario.eyepieces,
        barlows=scenario.barlows,
        binoculars=scenario.binoculars,
        seeing=scenario.seeing,
        moon=scenario.moon,
        confidence=scenario.confidence,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "label": scenario.label,
        "axes": {
            "target_profile": scenario.target_profile,
            "equipment_profile": scenario.equipment_profile,
            "sky_profile": scenario.sky_profile,
            "seeing_profile": scenario.seeing_profile,
        },
        "expectation": scenario.expectation,
        "target": comparison["target"],
        "legacy_formula": comparison["legacy_formula"],
        "rankings": comparison["rankings"],
        "candidates": comparison["candidates"],
    }


def _summary(
    scenarios: tuple[dict[str, object], ...],
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    q_values = [float(row["nsom"]["observer_capability"]["q_target"]) for row in rows]
    legacy_scores = [float(row["legacy"]["score"]) for row in rows]
    findings = [
        "Legacy EquipmentService exposes a useful component sum, but mixes target traits, sky quality, seeing and setup handling in one score.",
        "NSOM Q_target is configuration-derived and target-class-specific; it stays outside ObservableTargetValue.",
        "RecommendationConfidence is present only as metadata and has zero score effect.",
        "Equipment remains an active backend area; this report is evidence for a future policy/default-off path, not a runtime switch.",
    ]
    return {
        "scenario_count": len(scenarios),
        "candidate_row_count": len(rows),
        "average_legacy_score": sum(legacy_scores) / len(legacy_scores) if legacy_scores else 0.0,
        "average_q_target": sum(q_values) / len(q_values) if q_values else 0.0,
        "findings": tuple(findings),
    }


def _scenarios() -> tuple[EquipmentScenario, ...]:
    confidence = RecommendationConfidence(
        weather_confidence=0.9,
        viirs_confidence=0.9,
        moon_geometry_confidence=0.9,
        provider_fallback_confidence=0.1,
        notes=("fixture:equipment_comparison",),
    )
    return (
        EquipmentScenario(
            "E01_planet_mixed_equipment",
            "Planet across mixed equipment",
            "planet",
            "small_and_large_telescopes",
            "dark_sky",
            "good_seeing",
            "Planet Q_target should reward resolution, magnification and tracking.",
            _target("jupiter", "Jupiter", "Pianeta", 92, observation_type="HighMagnification", size=0.013),
            (_small_scope(), _large_scope()),
            _eyepieces(),
            (_barlow(),),
            (),
            _sky_quality(3),
            _seeing(86),
            _moon(20),
            confidence,
        ),
        EquipmentScenario(
            "E02_open_cluster_wide_field",
            "Open cluster wide-field handling",
            "open_cluster",
            "binocular_and_small_scope",
            "dark_sky",
            "average_seeing",
            "Open clusters should value field of view and practical comfort.",
            _target("m45", "Pleiades", "Ammasso aperto", 88, observation_type="WideField", size=1.8),
            (_small_scope(),),
            _eyepieces(),
            (),
            (_binocular(),),
            _sky_quality(3),
            _seeing(62),
            _moon(15),
            confidence,
        ),
        EquipmentScenario(
            "E03_galaxy_high_light_pollution",
            "Galaxy under high light pollution",
            "galaxy",
            "medium_telescope",
            "high_light_pollution",
            "good_seeing",
            "Legacy Equipment scoring still reacts to sky quality inside setup score.",
            _target("m51", "M51", "Galassia", 86, observation_type="General", size=0.18, magnitude="8.4"),
            (_medium_scope(),),
            _eyepieces(),
            (),
            (),
            _sky_quality(9, radiance=120.0),
            _seeing(82),
            _moon(25),
            confidence,
        ),
        EquipmentScenario(
            "E04_planet_poor_seeing",
            "Planet with poor seeing",
            "planet",
            "mak_zoom",
            "dark_sky",
            "poor_seeing",
            "Seeing should be visible as legacy Equipment context, not confidence.",
            _target("saturn", "Saturn", "Pianeta", 90, observation_type="HighMagnification", size=0.006),
            (_mak_scope(),),
            (_zoom(),),
            (),
            (),
            _sky_quality(3),
            _seeing(30),
            _moon(20),
            confidence,
        ),
        EquipmentScenario(
            "E05_confidence_metadata",
            "Low-confidence metadata check",
            "galaxy",
            "medium_telescope",
            "dark_sky",
            "good_seeing",
            "Confidence changes report trust only and never changes Equipment or Q_target scores.",
            _target("m81", "M81", "Galassia", 84, observation_type="General", size=0.22, magnitude="6.9"),
            (_medium_scope(),),
            _eyepieces(),
            (),
            (),
            _sky_quality(3),
            _seeing(82),
            _moon(20),
            RecommendationConfidence(
                weather_confidence=0.2,
                viirs_confidence=0.1,
                moon_geometry_confidence=0.2,
                provider_fallback_confidence=0.8,
                notes=("fixture:low_confidence",),
            ),
        ),
    )


def _top_label(rows: object) -> str:
    if not rows:
        return "n/d"
    first = rows[0]
    return str(first["label"])


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    *,
    observation_type: str,
    size: float,
    magnitude: str = "5.0",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="n/d",
        max_altitude="55 deg",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00-01:00",
        notes="Fixture target.",
        recommended_setup="Fixture setup",
        visibility_class="Buona",
        azimuth="180",
        time_above_horizon="4 h",
        visible=True,
        current_altitude="45 deg",
        score=score,
        difficulty="Media",
        apparent_size=f"{size} deg",
        max_angular_size_deg=size,
        recommended_observation_type=observation_type,
    )


def _small_scope() -> Telescope:
    return Telescope("small-70", "Small 70/500", 70, 500, "Refractor", "manual altaz")


def _medium_scope() -> Telescope:
    return Telescope("newton-130", "Newton 130/650", 130, 650, "Reflector", "manual dob")


def _large_scope() -> Telescope:
    return Telescope("large-220", "Large GoTo 220/1800", 220, 1800, "SCT", "GoTo EQ")


def _mak_scope() -> Telescope:
    return Telescope("mak-127", "Mak 127/1500", 127, 1500, "Maksutov", "tracking eq")


def _eyepieces() -> tuple[Eyepiece, ...]:
    return (
        Eyepiece("wide-32", "Wide 32 mm", 32.0, 68.0),
        Eyepiece("plossl-25", "Plossl 25 mm", 25.0, 52.0),
        Eyepiece("planetary-10", "Planetary 10 mm", 10.0, 60.0),
        Eyepiece("planetary-6", "Planetary 6 mm", 6.0, 58.0),
    )


def _zoom() -> Eyepiece:
    return Eyepiece(
        "zoom-8-24",
        "Zoom 8-24 mm",
        16.0,
        60.0,
        eyepiece_type="Zoom",
        min_focal_length_mm=8.0,
        max_focal_length_mm=24.0,
        zoom_click_positions_mm=(24.0, 20.0, 16.0, 12.0, 8.0),
    )


def _barlow() -> Barlow:
    return Barlow("barlow-2x", "2x Barlow", 2.0)


def _binocular() -> Binocular:
    return Binocular("bino-10x50", "Nikon 10x50", 10, 50)


def _sky_quality(bortle: int, *, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.4 if bortle <= 4 else 4.3,
        sky_brightness=21.4 if bortle <= 4 else 18.8,
        source="deterministic_fixture",
        description="Equipment NSOM comparison sky fixture.",
        confidence="high",
        viirs_radiance=radiance,
        viirs_observation_count=8 if radiance is not None else None,
    )


def _seeing(score: int) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good" if score >= 70 else "Poor",
        transparency="Good",
        seeing_score=score,
        transparency_score=80,
        explanation="Equipment NSOM comparison seeing fixture.",
        source="deterministic_fixture",
        confidence="high",
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="05:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=80.0,
    )


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
