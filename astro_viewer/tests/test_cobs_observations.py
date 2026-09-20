"""Protect COBS trust boundaries, offline caches and short-term brightness policies."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import numpy as np
import pytest
import requests

from astro_viewer.app.services.cobs_observations import (
    CACHE_TTL, MAX_PAGE_BYTES, CobsObservationStore, CobsSnapshot, CometObservation,
    designation_key, parse_observations,
)
from astro_viewer.app.services.comet_brightness import assess_brightness


NOW = datetime(2026, 9, 20, 0, tzinfo=UTC)


def api_row(**changes):
    row = {"type": "V", "obs_date": "2026-09-19 20:00:00", "magnitude": "10.2",
           "comet": {"name": "C/2024 T5", "component": None},
           "observer": {"icq_name": "TEST1"}, "obs_method": {"key": "S"},
           "conditions": None, "comet_visibility": None, "magnitude_error": None}
    return row | changes


def page(rows=None, *, number=1, pages=1, total=None):
    rows = [api_row()] if rows is None else rows
    return {"signature": {"version": "1.5"}, "objects": rows,
            "info": {"page": number, "pages": pages,
                     "recordsTotal": len(rows) if total is None else total}}


def response(payload=None, *, status=200, content=None):
    result = Mock()
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    result.status_code = status
    result.iter_content.return_value = [content if content is not None else json.dumps(payload or page()).encode()]
    return result


def observations(*, kind="V", method="S", offset=-1.2):
    rows, models = [], []
    for day in (1, 2):
        for observer in range(3):
            model = 12.0 + day * 0.2
            rows.append(CometObservation("C/2024T5", NOW - timedelta(days=day, hours=observer),
                                         model + offset, f"TEST{observer}", kind, method))
            models.append(model)
    return tuple(rows), np.asarray(models)


@pytest.mark.parametrize(("name", "expected"), [
    ("  C/2024 T5 (ATLAS)", "C/2024T5"), ("220P/McNaught", "220P"),
    ("C/2024T5", "C/2024T5"), ("P/2026 A1", "P/2026A1"),
    ("73P-B", ""), ("73P/B", ""), ("73P-B (fragment)", ""),
    ("C/2024 T5-A", ""), ("ATLAS", ""), ("2024T5", ""),
])
def test_designations_never_match_names_or_fragments(name, expected):
    assert designation_key(name) == expected


@pytest.mark.parametrize("changes", [
    {"conditions": ":"}, {"comet_visibility": ">"}, {"comet_visibility": "["},
    {"issues": True}, {"has_issue": True}, {"issue": "reported"},
    {"magnitude": "nan"}, {"magnitude": "inf"}, {"magnitude": None},
    {"magnitude": "<10"}, {"magnitude": 40}, {"magnitude_error": -1},
    {"magnitude": True}, {"magnitude_error": False},
    {"magnitude_error": "nan"}, {"obs_date": "2026-10-01 00:00:00"},
    {"obs_date": "2026-08-01 00:00:00"}, {"obs_date": "bad"},
    {"comet": {"name": "C/2024 T5", "component": "A"}}, {"comet": None},
    {"type": "?"},
])
def test_invalid_or_unsafe_measurements_are_not_observations(changes):
    assert parse_observations([api_row(**changes)], NOW) == ()


def test_parser_deduplicates_and_keeps_visual_distinct_from_instrumental_v():
    visual = api_row()
    instrumental = api_row(type="C", obs_method={"key": "V"})
    rows = parse_observations([visual, visual, instrumental], NOW)
    assert len(rows) == 2
    assert {row.kind for row in rows} == {"V", "C"}
    assert all(row.error is None for row in rows)


def test_remote_codes_are_not_markup_or_unbounded_ui_text():
    rows = parse_observations([api_row(observer={"icq_name": "<img src='x'>"},
                                      obs_method={"key": "x" * 10000})], NOW)
    assert len(rows) == 1 and rows[0].observer == rows[0].method == ""


def test_daily_cache_is_reused_across_restart_and_global_context(tmp_path):
    http = Mock(return_value=response())
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=http)
    result = store.refresh(NOW)
    original = store.path.read_bytes()
    mtime = store.path.stat().st_mtime_ns
    assert len(result.snapshot.observations) == 1
    assert store.refresh(NOW + timedelta(hours=1)).snapshot == result.snapshot
    restarted = CobsObservationStore(store.path, http_get=Mock(side_effect=AssertionError("network")))
    assert restarted.refresh(NOW + timedelta(hours=2)).snapshot == result.snapshot
    assert store.path.read_bytes() == original
    assert store.path.stat().st_mtime_ns == mtime
    http.assert_called_once()
    params = http.call_args.kwargs["params"]
    assert params["exclude_issue"] == params["exclude_faint"] == "true"
    assert not {"lat", "long", "user", "uid"} & params.keys()
    assert json.loads(original)["license"].endswith("/by-nc-sa/4.0/")


def test_all_pages_required_and_fresh_empty_response_is_cached(tmp_path):
    http = Mock(side_effect=[response(page(pages=2, total=2)),
                            response(page([api_row(magnitude="10.3")], number=2, pages=2, total=2))])
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=http)
    assert len(store.refresh(NOW).snapshot.observations) == 2
    assert http.call_count == 2
    http.return_value = response(page([], pages=0))
    http.side_effect = None
    assert store.refresh(NOW + CACHE_TTL).snapshot.observations == ()
    assert store.snapshot.fetched_at == NOW + CACHE_TTL


@pytest.mark.parametrize("bad_response", [
    response(status=429), response(status=500), response(status=302),
    response(content=b"<html>maintenance</html>"), response(content=b"{}"),
    response(page() | {"signature": {"version": "2.0"}}),
    response(page(total=3)), response(page(pages=9)),
    response(page([api_row(magnitude="nan")])),
])
def test_failed_refresh_preserves_data_and_backs_off_across_restart(tmp_path, bad_response):
    http = Mock(side_effect=[response(), bad_response])
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=http)
    before = store.refresh(NOW).snapshot
    result = store.refresh(NOW + CACHE_TTL)
    assert result.error == "unavailable"
    assert result.snapshot == before
    restarted = CobsObservationStore(store.path, http_get=Mock(side_effect=AssertionError("network")))
    assert restarted.refresh(NOW + CACHE_TTL + timedelta(hours=1)).snapshot == before


def test_timeout_empty_cache_backoff_survives_restart(tmp_path):
    http = Mock(side_effect=requests.Timeout("offline"))
    path = tmp_path / "cobs.json"
    assert CobsObservationStore(path, http_get=http).refresh(NOW).error == "unavailable"
    CobsObservationStore(path, http_get=http).refresh(NOW + timedelta(hours=2))
    http.assert_called_once()


def test_large_payload_and_incomplete_second_page_are_not_published(tmp_path):
    http = Mock(side_effect=[response(page(pages=2, total=2)), response(status=500)])
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=http)
    assert store.refresh(NOW).snapshot == CobsSnapshot()
    http.side_effect = None
    http.return_value = response(content=b" " * (MAX_PAGE_BYTES + 1))
    assert store.refresh(NOW + CACHE_TTL).error == "unavailable"


def test_atomic_write_failure_keeps_previous_file_and_usable_memory(tmp_path):
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=Mock(return_value=response()))
    store.refresh(NOW)
    before = store.path.read_bytes()
    with patch("pathlib.Path.replace", side_effect=OSError("read only")):
        result = store.refresh(NOW + CACHE_TTL)
    assert result.error == "cache_write"
    assert result.snapshot.fetched_at == NOW + CACHE_TTL
    assert store.path.read_bytes() == before
    assert not list(tmp_path.glob(".cobs-*.tmp"))


def test_snapshot_use_time_excludes_future_and_old_observations():
    rows, _ = observations()
    snapshot = CobsSnapshot(rows, NOW, "fixture")
    assert snapshot.for_comet("C/2024 T5 (ATLAS)", NOW) == rows
    assert snapshot.for_comet("C/2024 T5-A", NOW) == ()
    assert snapshot.for_comet("C/2024 T5", NOW - timedelta(days=5)) == ()
    assert snapshot.for_comet("C/2024 T5", NOW + timedelta(days=20)) == ()


def test_calibration_corrects_distance_law_residual_not_raw_magnitude_average():
    rows, model = observations()
    result = assess_brightness(rows, model, NOW)
    calibration = result.calibration
    assert calibration is not None
    assert calibration.offset == pytest.approx(-1.2)
    assert calibration.margin == 0.35
    assert calibration.observers == 3 and calibration.count == 6
    dates = [NOW, NOW + timedelta(days=1), NOW + timedelta(days=4)]
    corrected = calibration.adjust(np.array([11.0, 12.0, 13.0]), dates)
    assert corrected == pytest.approx([9.8, 10.8, 13.0])
    assert calibration.faint_limit(corrected, dates) == pytest.approx([10.15, 11.15, 13.0])


@pytest.mark.parametrize(("kind", "method", "accepted"), [
    ("V", "S", True), ("V", "M", True), ("V", "B", True), ("C", "Z", True),
    ("C", "V", False), ("C", "R", False), ("C", "C", False), ("V", "V", False),
    ("V", "?", False),
])
def test_method_family_is_never_inferred_from_filter_name(kind, method, accepted):
    rows, model = observations(kind=kind, method=method)
    assert bool(assess_brightness(rows, model, NOW).calibration) is accepted


@pytest.mark.parametrize("mutation", ["one_observer", "one_day", "old", "future", "uncertain", "no_observer", "unstable", "large_offset"])
def test_weak_or_unstable_series_do_not_change_predictions(mutation):
    rows, model = observations()
    if mutation == "one_observer":
        rows = tuple(replace(row, observer="TEST") for row in rows)
    elif mutation == "one_day":
        rows = tuple(replace(row, observed_at=NOW - timedelta(hours=3)) for row in rows)
    elif mutation == "old":
        rows = tuple(replace(row, observed_at=row.observed_at - timedelta(days=5)) for row in rows)
    elif mutation == "future":
        rows = tuple(replace(row, observed_at=row.observed_at + timedelta(days=5)) for row in rows)
    elif mutation == "uncertain":
        rows = tuple(replace(row, error=0.8) for row in rows)
    elif mutation == "no_observer":
        rows = tuple(replace(row, observer="") for row in rows)
    elif mutation == "unstable":
        rows = tuple(replace(row, magnitude=row.magnitude + i) for i, row in enumerate(rows))
    elif mutation == "large_offset":
        rows = tuple(replace(row, magnitude=row.magnitude - 4) for row in rows)
    assert assess_brightness(rows, model, NOW).calibration is None


def test_observer_burst_cannot_dominate_fit_or_manufacture_independence():
    rows, model = observations()
    duplicated = tuple(replace(rows[0], magnitude=rows[0].magnitude + 0.2) for _ in range(100))
    result = assess_brightness(rows + duplicated, np.concatenate((model, np.repeat(model[0], 100))), NOW)
    assert result.calibration.offset == pytest.approx(-1.2)
    assert result.calibration.count == 6
    assert assess_brightness(duplicated, np.repeat(model[0], 100), NOW).calibration is None


def test_conflicting_visual_equivalent_series_is_not_silently_averaged():
    visual, vm = observations(offset=-1.2)
    ccd, cm = observations(kind="C", method="Z", offset=0.5)
    result = assess_brightness(visual + ccd, np.concatenate((vm, cm)), NOW)
    assert result.calibration is None and result.reason == "conflicting"


def test_synthetic_known_truth_and_expiration_for_hundred_distance_laws():
    rng = np.random.default_rng(8841)
    template, _ = observations()
    for _ in range(100):
        model = rng.uniform(6, 16, size=6)
        offset = rng.uniform(-2, 2)
        rows = tuple(replace(row, magnitude=float(value + offset))
                     for row, value in zip(template, model, strict=True))
        calibration = assess_brightness(rows, model, NOW).calibration
        assert calibration.offset == pytest.approx(offset)
        assert calibration.adjust(np.array([12.0]), [NOW])[0] == pytest.approx(12 + offset)
        assert calibration.adjust(np.array([12.0]), [NOW + timedelta(days=90)])[0] == 12


def test_mismatched_model_epoch_count_is_an_error():
    rows, model = observations()
    with pytest.raises(ValueError):
        assess_brightness(rows, model[:1], NOW)


@pytest.mark.parametrize("bad_content", ["[]", "broken", '{"schema": 99}', '{"schema": 1, "pages": []}'])
def test_bad_disk_cache_refreshes_instead_of_becoming_a_permanent_failure(tmp_path, bad_content):
    path = tmp_path / "cobs.json"
    path.write_text(bad_content, encoding="utf-8")
    http = Mock(return_value=response())
    result = CobsObservationStore(path, http_get=http).refresh(NOW)
    assert result.snapshot.fetched_at == NOW and not result.error


def test_future_cache_and_invalid_retry_date_do_not_lock_provider(tmp_path):
    http = Mock(return_value=response())
    path = tmp_path / "cobs.json"
    CobsObservationStore(path, http_get=http).refresh(NOW)
    payload = json.loads(path.read_text())
    payload["fetched_at"] = (NOW + timedelta(days=5)).isoformat()
    payload["next_check"] = (NOW + timedelta(days=6)).isoformat()
    path.write_text(json.dumps(payload))
    assert CobsObservationStore(path, http_get=http).refresh(NOW).snapshot.fetched_at == NOW
    assert http.call_count == 2


def test_changed_pagination_is_not_published(tmp_path):
    http = Mock(side_effect=[response(page(pages=2, total=2)),
                            response(page(number=2, pages=2, total=3))])
    result = CobsObservationStore(tmp_path / "cobs.json", http_get=http).refresh(NOW)
    assert result.error == "unavailable" and result.snapshot.fetched_at is None


def test_download_time_budget_is_checked_during_streaming(tmp_path):
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=Mock(return_value=response()))
    with patch("astro_viewer.app.services.cobs_observations.time.monotonic", side_effect=[0, 1, 60]):
        result = store.refresh(NOW)
    assert result.error == "unavailable" and result.snapshot.observations == ()
