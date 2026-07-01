from __future__ import annotations

import json

import pytest

from astro_viewer.tools.nsom_observer_capability_review import (
    OBSERVER_REVIEW_CASES,
    TARGET_CLASS_SPECS,
    generate_observer_capability_review_data,
)


def test_observer_capability_review_data_is_developer_only_and_strict_json() -> None:
    data = generate_observer_capability_review_data()

    json.dumps(data, sort_keys=True, allow_nan=False)
    assert data["metadata"]["developer_only"] is True
    assert data["metadata"]["runtime_writes"] is False
    assert data["metadata"]["automatic_logging"] is False
    assert data["metadata"]["network"] is False
    assert data["metadata"]["qml_exposure"] is False
    assert data["metadata"]["planner_scoring_changed"] is False


def test_observer_review_covers_required_target_classes_and_sensitivity_cases() -> None:
    data = generate_observer_capability_review_data()
    target_classes = {case["target_class"] for case in data["cases"]}
    case_names = {case["changed_observer_dimension"] for case in data["cases"]}

    assert target_classes == {spec[0] for spec in TARGET_CLASS_SPECS}
    assert case_names == set(OBSERVER_REVIEW_CASES)
    assert data["metadata"]["case_count"] == len(TARGET_CLASS_SPECS) * len(OBSERVER_REVIEW_CASES)


def test_observer_changes_never_mutate_observable_target_value() -> None:
    data = generate_observer_capability_review_data()

    for case in data["cases"]:
        assert case["observable_target_value_unchanged"] is True
        assert case["baseline_observable_target_value"] == pytest.approx(
            case["changed_observable_target_value"]
        )


def test_observer_changes_affect_practical_target_value() -> None:
    data = generate_observer_capability_review_data()

    for case in data["cases"]:
        assert case["changed_practical_target_value"] > case["baseline_practical_target_value"]
        assert case["practical_target_value_delta"] > 0.0
        assert case["direction_makes_nsom_sense"] is True


def test_aperture_focal_length_mount_field_and_comfort_cases_are_distinguishable() -> None:
    data = generate_observer_capability_review_data()
    galaxy_cases = {
        case["changed_observer_dimension"]: case
        for case in data["cases"]
        if case["target_class"] == "galaxy"
    }

    assert set(galaxy_cases["aperture_only"]["changed_dimensions_only"]) == {"light_grasp", "resolution"}

    focal = galaxy_cases["focal_length_only"]
    assert set(focal["changed_dimensions_only"]) == {"field_of_view", "magnification_range"}
    assert focal["dimension_delta"]["field_of_view"] < 0.0
    assert focal["dimension_delta"]["magnification_range"] > 0.0

    assert set(galaxy_cases["mount_tracking_only"]["changed_dimensions_only"]) == {"tracking_or_goto"}
    assert set(galaxy_cases["field_of_view_only"]["changed_dimensions_only"]) == {"field_of_view"}
    assert set(galaxy_cases["practical_comfort_setup_only"]["changed_dimensions_only"]) == {"practical_comfort"}


def test_target_classes_are_compared_with_stable_sky_session_inputs() -> None:
    data = generate_observer_capability_review_data()
    stable_inputs = data["metadata"]["stable_sky_session_inputs"]

    assert stable_inputs["sky_quality"]["viirs_radiance"] == pytest.approx(1.0)
    assert stable_inputs["moon"]["illumination"] == "10%"
    assert stable_inputs["scores"]["planetary_score"] == pytest.approx(90)
    assert stable_inputs["scores"]["deep_sky_score"] == pytest.approx(90)

    for target_class in {case["target_class"] for case in data["cases"]}:
        observable_values = {
            case["baseline_observable_target_value"]
            for case in data["cases"]
            if case["target_class"] == target_class
        }
        assert len(observable_values) == 1


def test_review_does_not_use_legacy_score_as_expected_output() -> None:
    data = generate_observer_capability_review_data()

    assert data["metadata"]["legacy_score_used_as_expected_output"] is False
    assert all(case["legacy_score_used_as_expected_output"] is False for case in data["cases"])


def test_observer_review_confidence_remains_score_neutral() -> None:
    data = generate_observer_capability_review_data()
    confidence = data["confidence_neutrality"]

    assert confidence["low_confidence_value"] < confidence["high_confidence_value"]
    assert confidence["low_confidence_score"] == pytest.approx(confidence["high_confidence_score"])
    assert confidence["score_delta"] == pytest.approx(0.0)
    assert confidence["score_neutral"] is True


def test_current_flat_mean_is_uniform_across_target_classes_before_calibration() -> None:
    data = generate_observer_capability_review_data()
    aggregate = data["aggregate_review"]

    assert aggregate["target_specific_weighting_review"] == "recommended_before_calibration"
    assert set(aggregate["uniform_summary_delta_cases"]) == set(OBSERVER_REVIEW_CASES)
    for stats in aggregate["by_changed_observer_dimension"].values():
        assert stats["target_class_count"] == len(TARGET_CLASS_SPECS)
        assert stats["summary_delta_uniform_across_target_classes"] is True
        assert stats["summary_delta_max"] == pytest.approx(stats["summary_delta_min"])
