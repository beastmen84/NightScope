"""Exercise real comet geometry, provider scheduling and unchanged fallback outputs."""

from __future__ import annotations

import time
from dataclasses import asdict, replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from astro_viewer.app.astronomy.comet_windows import (
    CometWindowEventSource, _comet_vector, _predicted_magnitude, _setup_for_magnitude,
)
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.services.cobs_observations import CobsObservationStore, CobsResult, CobsSnapshot
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.app.viewmodels.cobs_manager import CobsManager
from astro_viewer.tests.test_cobs_observations import NOW, observations, response
from astro_viewer.tests.test_comet_windows import (
    ROME, _CountingTransientSource, _Response, _repository, _skyfield_context,
)


def test_real_geometry_cobs_rescues_a_candidate_rejected_by_jpl_brightness(tmp_path):
    store = CobsObservationStore(tmp_path / "cobs.json")
    source = CometWindowEventSource(_repository(tmp_path), http_get=Mock(return_value=_Response()),
                                    observation_store=store)
    source.HORIZON = timedelta(days=2)
    prepared = source.prepare_event_data(ROME, now=NOW)
    ts, eph = _skyfield_context()
    try:
        record = prepared.records[0]
        comet = _comet_vector(record, ts, eph["sun"])
        t = ts.from_datetimes([NOW])
        current = float(_predicted_magnitude(record, np.asarray((comet-eph["sun"]).at(t).distance().au),
                                            np.asarray(eph["earth"].at(t).observe(comet).distance().au))[0])
        # Deliberately faint model: even the coarse filter rejects it. Multiple
        # independent observations imply a plausible -2.7 mag short-term offset.
        record = replace(record, absolute_magnitude=record.absolute_magnitude + 16.6 - current)
        prepared = replace(prepared, records=(record,))
        baseline = source.build_events(ROME, now=NOW, timescale=ts, ephemeris=eph, prepared_data=prepared)
        assert baseline == []
        rows, _model = observations(offset=0)
        epochs = ts.from_datetimes([row.observed_at for row in rows])
        model = _predicted_magnitude(record, np.asarray((comet-eph["sun"]).at(epochs).distance().au),
                                     np.asarray(eph["earth"].at(epochs).observe(comet).distance().au))
        rows = tuple(replace(row, magnitude=float(value - 2.7)) for row, value in zip(rows, model, strict=True))
        snapshot = CobsSnapshot(rows, NOW, "corrected")
        prepared = replace(prepared, observations=snapshot)
        events = source.build_events(ROME, now=NOW, timescale=ts, ephemeris=eph, prepared_data=prepared)
        assert len(events) == 1
        facts = {key: value for key, _label, value in events[0].event_facts}
        assert "cobs_next_magnitude" in facts
        assert "COBS" in events[0].data_source
        assert events[0].setup == _setup_for_magnitude(14.25)
        assert "3 osservatori" in facts["cobs_calibration"]
        # Age-out restores the existing prediction, not an enduring orbit fit.
        expired = source.build_events(ROME, now=NOW + timedelta(days=4), timescale=ts,
                                      ephemeris=eph, prepared_data=prepared)
        assert expired == []
    finally:
        eph.close()


@pytest.mark.parametrize("kind", ["empty", "instrumental", "stale", "discordant"])
def test_unqualified_cobs_keeps_all_original_scientific_event_fields(tmp_path, kind):
    plain = CometWindowEventSource(_repository(tmp_path), http_get=Mock(return_value=_Response()))
    prepared = plain.prepare_event_data(ROME, now=NOW)
    enhanced = CometWindowEventSource(plain._cache_repository,
                                     observation_store=CobsObservationStore(tmp_path / "cobs.json"))
    rows, _ = observations()
    if kind == "empty":
        rows = ()
    elif kind == "instrumental":
        rows = tuple(replace(row, kind="C", method="V") for row in rows)
    elif kind == "stale":
        rows = tuple(replace(row, observed_at=row.observed_at - timedelta(days=5)) for row in rows)
    else:
        rows = tuple(replace(row, magnitude=row.magnitude + i * 3) for i, row in enumerate(rows))
    augmented = replace(prepared, observations=CobsSnapshot(rows, NOW, kind))
    ts, eph = _skyfield_context()
    try:
        old = plain.build_events(ROME, now=NOW, timescale=ts, ephemeris=eph, prepared_data=prepared)
        new = enhanced.build_events(ROME, now=NOW, timescale=ts, ephemeris=eph, prepared_data=augmented)
        assert len(old) == len(new) == 1
        old_dict, new_dict = asdict(old[0]), asdict(new[0])
        new_dict["event_facts"] = tuple(fact for fact in new_dict["event_facts"] if not fact[0].startswith("cobs_"))
        new_dict["data_source"] = old_dict["data_source"]
        assert old_dict == new_dict
    finally:
        eph.close()


def test_source_captures_immutable_snapshot_and_never_fetches_cobs_on_calculation(tmp_path):
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=Mock(side_effect=AssertionError("network")))
    rows, _ = observations()
    store._snapshot = CobsSnapshot(rows, NOW, "before")
    source = CometWindowEventSource(_repository(tmp_path), http_get=Mock(return_value=_Response()),
                                    observation_store=store)
    prepared = source.prepare_event_data(ROME, now=NOW)
    store._snapshot = CobsSnapshot((), NOW, "after")
    assert len(prepared.observations.observations) == 6
    assert source.cache_token == "after"
    store._http_get.assert_not_called()


def test_transient_revision_changes_rebuild_only_that_source_even_during_a_race():
    stable = _CountingTransientSource("iss", timedelta(hours=6))
    changing = _CountingTransientSource("comet", timedelta(hours=6))
    changing.cache_token = "initial"
    engine = SkyfieldAstronomyEngine.__new__(SkyfieldAstronomyEngine)
    engine._transient_event_sources = (stable, changing)
    engine._transient_event_results = {}
    engine._timescale = engine._ephemeris = object()
    engine._now = lambda _location: NOW
    prepared = engine.prepare_transient_events(ROME)
    # Update occurs after preparation but before result publication.
    changing.cache_token = "new"
    engine.upcoming_transient_events(ROME, prepared)
    next_prepared = engine.prepare_transient_events(ROME)
    assert [source.name for source, _ in next_prepared.entries] == ["comet"]
    engine.upcoming_transient_events(ROME, next_prepared)
    assert stable.build_calls == 1 and changing.build_calls == 2
    assert engine.prepare_transient_events(ROME).entries == ()


def test_calibration_failure_is_not_a_reason_to_drop_an_existing_comet():
    rows, _ = observations()
    source = CometWindowEventSource(None)
    snapshot = CobsSnapshot(rows, NOW, "fixture")
    timescale = Mock()
    timescale.from_datetimes.side_effect = RuntimeError("calibration unavailable")
    result = source._brightness_assessment(SimpleNamespace(designation="C/2024 T5"),
                                           None, snapshot, NOW, timescale, {})
    assert result.calibration is None and result.observations == rows


def test_manager_does_no_constructor_io_and_coalesces_async_requests(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    store = CobsObservationStore(tmp_path / "cobs.json", http_get=Mock(return_value=response()))
    manager = CobsManager(store, clock=lambda: NOW)
    signals = []
    manager.observationsChanged.connect(lambda: signals.append(manager.info["count"]))
    assert not store._loaded and not store.path.exists()
    manager.start()
    manager.check()
    deadline = time.monotonic() + 5
    while manager.info["busy"] and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert not manager.info["busy"]
    assert manager.info["state"] == "ready" and signals == [1]
    store._http_get.assert_called_once()
    manager.check()
    store._http_get.assert_called_once()
    manager.stop()
    before = manager.info
    manager._accept(CobsResult(CobsSnapshot(), NOW))
    assert manager.info == before


def test_manager_thread_start_failure_is_nonfatal(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    manager = CobsManager(CobsObservationStore(tmp_path / "cobs.json"), clock=lambda: NOW)
    with patch("astro_viewer.app.viewmodels.cobs_manager.Thread.start", side_effect=RuntimeError):
        manager.start()
    assert app and manager.info["state"] == "unavailable" and not manager.info["busy"]
    manager.stop()


def test_controller_retains_a_refresh_request_while_worker_runs():
    controller = SimpleNamespace(_cobs_refresh_pending=False, _start_transient_event_refresh=Mock(return_value=False))
    AppController._cobs_observations_changed(controller)
    assert controller._cobs_refresh_pending
    controller._start_transient_event_refresh.assert_called_once()


@pytest.mark.parametrize(("model", "offset", "admitted"), [(14.0, 1.0, False), (15.0, -1.0, True), (14.9, -0.5, False)])
def test_night_admission_uses_correction_and_faint_side_margin(model, offset, admitted):
    from astro_viewer.app.services.comet_brightness import BrightnessCalibration
    from astro_viewer.tests.test_recommendation_guidance_audit import comet_context
    comet, context = comet_context([30, 35, 30])
    now = context["datetimes"][0]
    fit = BrightnessCalibration(offset, .35, now - timedelta(hours=2), now + timedelta(days=2), "visual", 3, 2)
    source = CometWindowEventSource(None)
    with patch("astro_viewer.app.astronomy.comet_windows._predicted_magnitude", return_value=np.full(3, model)):
        corrected = source._night_windows(comet, None, context=context, calibration=fit)
        original = source._night_windows(comet, None, context=context)
    assert bool(corrected) is admitted
    assert bool(original) is (model <= 14.5)
    if corrected:
        window = corrected[0]
        assert window.predicted_magnitude == pytest.approx(model + offset)
        assert window.magnitude_margin == .35
        assert window.start == context["datetimes"][0] and window.end == context["datetimes"][-1]
        assert window.maximum_altitude_deg == 35


def test_instrument_advice_uses_corrected_faint_bound_not_an_optimistic_threshold():
    from astro_viewer.app.astronomy.comet_windows import _NightWindow
    first = _NightWindow(NOW.date(), NOW, NOW+timedelta(hours=2), NOW+timedelta(hours=1), 6.3, 45, 60, 80, .2)
    source = CometWindowEventSource(None)
    record = SimpleNamespace(spk_id="test", designation="Test")
    prepared = SimpleNamespace(cache_record=SimpleNamespace(fetched_at=NOW.isoformat()), freshness="fresh")
    original = source._event(record, [first], prepared)
    conservative = source._event(record, [replace(first, magnitude_margin=.35)], prepared)
    assert original.setup == _setup_for_magnitude(6.3)
    assert conservative.setup == _setup_for_magnitude(6.65)
    assert conservative.setup != original.setup


def test_unknown_bad_photometry_is_shown_as_measurement_not_promoted_to_prediction():
    from astro_viewer.app.services.comet_observation_presentation import observation_facts
    from astro_viewer.app.services.comet_brightness import BrightnessAssessment
    rows, _ = observations()
    facts = dict((code, str(value)) for code, _label, value in observation_facts(
        BrightnessAssessment(rows, reason="insufficient"), CobsSnapshot(rows, NOW, "x"),
        SimpleNamespace(start=NOW)))
    assert "Singola misura" in facts["cobs_last_estimate"]
    assert "insufficienti" in facts["cobs_calibration"]
    assert "cobs_next_magnitude" not in facts
