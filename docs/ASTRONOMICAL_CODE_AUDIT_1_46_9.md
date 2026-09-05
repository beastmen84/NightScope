# NightScope 1.46.9: astronomical and code audit

Audit date: 2026-09-05. Source baseline: `b567a2b`.

Historical audit, preserved as originally observed. The user subsequently
authorized functional corrections; their implementation and validation are
recorded in [1.46.10 corrections](ASTRONOMICAL_CORRECTIONS_1_46_10.md).
Statements below about open defects describe the 1.46.9 baseline, not the
corrected source. Scientific approximation/calibration limits still apply.

This audit pauses catalogue editorial work. Its scope is application logic,
astronomical calculations, numerical units, observation/imaging heuristics,
provider boundaries, persistence, orchestration and presentation. Documentation
changes are authorized; numerical/behavioural corrections are separate work.

## Verdict

The coordinate engine and basic optical geometry are coherent with the checked
reference implementations and units. The application cannot, however, be
certified as astronomically correct in every path: reproducible defects exist
in night eligibility, time handling and the treatment of incomplete inputs.
The recommendation scores and exposure/seeing advice are explicitly heuristic,
not validated physical detectability models.

Fix A5 first, then A1/A2/A3/A6 and the cross-feature twilight policy A4, before
resuming a long editorial series. A7 concerns failure-mode transparency; A8 and
N1 are lower-impact presentation/platform issues. No finding is silently fixed
by this documentation-only change.

## Evidence and limits

The full local source gate (`tools/run_checks.py --security`) passed on the
baseline: 1,251 tests and 10 subtests, including the existing scientific and
regression tests, dependency/security checks, documentation and architecture
checks, and backend/normal-QML/red-QML smoke checks. Passing these tests is not
independent proof that the scientific model is correct: the edge cases below
were found by reviewing its assumptions and running separate probes.

The test phase took 139.44 seconds in this run. This is one local measurement,
not a new test-performance optimization or a claim of reproducible timing.
The security gate retains the reviewed baseline of 0 high, 34 medium and 14 low
Bandit findings; a passing gate does not mean zero static findings.

Coverage of this review is deliberately differentiated:

| Source family | Review/evidence |
| --- | --- |
| 250 Python modules (124 production, 93 tests/support, 33 maintenance/packaging) | Complete governed inventory, parsing/static checks, protected-layer/import-cycle checks and full regression gate. |
| Astronomy and observing-time logic | Manual formula/contract review: coordinates, DE421, almanac events, polar-night states, scalar/vectorized sampling, Moon geometry, calendar, ISS and comet policies. Independent and adversarial probes below. |
| Visual equipment and imaging | Manual review of dimensional conversions, configuration eligibility, modifiers, field size, sampling, backfocus, solar eligibility, exposure/video policies and ranking boundaries; 48 independent optical fixtures. |
| NSOM and planning | Manual review of intrinsic/Sky/Observer/Session/confidence ownership, raw versus display inputs, factors/weights, candidate admission, chronology and live Compass state. |
| External conditions and location | Manual review of weather null/default/failure handling, IANA timezone resolution, VIIRS collection identity, MAIAC scaling/QA, AOD/PM precedence, freshness and units. Provider fixtures/static paths, not a live authenticated validation of every service. |
| Persistence and orchestration | Boundary review of bootstrap/migrations/backups, parameterized repository access, equipment validation, immutable snapshot contracts, request-generation/stale-result handling and secure credential selection; existing regression suites. |
| 34 QML files | Source scan for calculations and backend contract use; targeted manual checks of Moon/Compass drawing, weather and input rendering; existing normal/red runtime smoke tests. |
| 17 governed operational files | Existing packaging, security and documentation gates, configuration/source inventory; no new bundle or Linux execution. |

This is a whole-project, risk-based audit, not a formal proof or a claim of
equal line-by-line depth in every controller, CRUD form and maintenance script.
The independent astronomy probe shares DE421 with the application: it checks
the coordinate pipeline, not the independent accuracy of the JPL kernel itself.
Generated seeds/translations/assets, virtual environments and build outputs are
outside the handwritten-source inventory; their existing validation gates still
ran. No new object-by-object editorial review was performed.

The generated Windows distribution, GitHub Actions, public releases, external
provider accounts and catalogue editorial content are not changed by this audit.
Local diagnostic scripts are under
`build/astronomy-audit-1.46.9-20260905/` (ignored, not release evidence). Their
observed results are recorded here. `source-gate.log` is only the PowerShell
transcript wrapper; it did not capture the native subprocess output and must
not be presented as a complete test log.

## Independent numerical checks

- Compared the application observer/apparent/AltAz pipeline with Astropy
  `get_body(...).transform_to(AltAz(..., pressure=0))`, using the same local
  DE421 kernel, zero site height and no IERS downloads.
- Sites: Rome (41.9, 12.5), Sydney (-33.9, 151.2), Tromso (69.65, 18.96).
  Instants: 00:00/12:00 UTC on 2026-03-20, 06-21, 09-05 and 12-21.
  Targets: Sun, Moon, seven planets and three fixed ICRS directions, including
  a near-polar direction. Total: **288 comparisons**.
- Maximum full-direction separation was **2.6084 arcseconds**. This supports
  the position/angle-unit implementation at the application's display precision;
  it does not establish sub-arcsecond astrometry, refraction accuracy, valid
  threshold selection or correct useful-window admission.
- **48 optical configurations / 240 identities** passed: apertures 50/100/200/
  400 mm, focal lengths 250/500/1000/2000 mm, modifiers 1/2/3x, 10 mm eyepiece
  with 60-degree AFOV and a 20x10 mm sensor with 5-micrometre pixels. Checked
  magnification times exit pupil = aperture, TFOV times magnification = AFOV,
  focal ratio times aperture = effective focal length, arcseconds/pixel unit
  conversion, and the inverse of the full-angle sensor FOV formula.

Method references: [Astropy get_body](https://docs.astropy.org/en/stable/api/astropy.coordinates.get_body.html)
and [Skyfield positions](https://rhodesmill.org/skyfield/positions.html).

## Confirmed findings

### A1. Planetary nebulae use the planetary live-altitude threshold

Priority: medium. Owner: `astronomy/skyfield_engine.py`,
`_geometry_altitude_threshold()` and its live/Moon-geometry callers.

The substring test for `planet` also matches `Planetary Nebula` and
`Nebulosa planetaria`. Both receive 8 degrees, while other deep-sky objects
receive 15 degrees. Initial catalogue geometry does use 15 degrees, so live
refresh and Moon-window geometry do not preserve the initial DSO contract.

An isolated call reproduces 8 degrees for both planetary-nebula labels and
15 degrees for `Emission Nebula` and `Galaxy`. This is an actual classification
error, not a disagreement over which observational threshold is preferable.

Correction should use the shared target taxonomy or explicit solar-system IDs,
and test both English and Italian nebula labels across initial and live paths.

### A2. Local-clock sampling is not a monotonic astronomical timeline at DST

Priority: medium. Owners: `SkyfieldAstronomyEngine._datetime_samples()`,
`ObservingNightWindow`, clock-based planner duration/order calculations.

Sampling adds timedeltas to an IANA-localized datetime, then converts each sample
to UTC. Across the Europe/Rome spring transition on 2026-03-29, a nominal
five-hour wall-clock span is four elapsed hours: the 30-minute grid contains
two duplicate UTC instants and one backwards 30-minute step. On 2026-10-25,
the corresponding span is six elapsed hours and has one 90-minute UTC gap.

`HH:MM` alone also cannot distinguish the repeated autumn hour: reconstructing
02:30 selects `fold=0`. Subtraction of datetimes sharing the same `ZoneInfo`
returns wall-clock rather than elapsed time. This affects transition nights,
not the ordinary daily operation of a fixed-offset night.

Correction should sample/order/subtract in UTC, retain absolute timestamps
through planning, and localize only presentation. Regression cases must cover
both transitions and positive windows crossing a repeated/skipped hour.

This follows Python's documented aware-datetime arithmetic, not a defect in
the timezone database. See [datetime arithmetic](https://docs.python.org/3/library/datetime.html).

### A3. Excluding the terminal sample can discard a real pre-dawn window

Priority: medium. Owners: `SkyfieldAstronomyEngine._sample_summary()` and
the visibility prefilter in `_catalogue_details_batch()`.

The closing sample is excluded to avoid claiming a zero-duration useful window
at sunrise. However, it is also excluded when deciding whether any window
exists. For a two-sample 05:30-06:00 interval with altitude increasing from
10 to 20 degrees, the 15-degree crossing is at 05:45. The helper reports no
window and a maximum of 10 degrees, losing a positive 15-minute interval.

The existing threshold-interpolation helper independently returns that 05:45
crossing. This probe demonstrates the algorithmic error; its linear altitudes
are a synthetic boundary case, not claimed ephemeris measurements.

Correction should separate positive-duration interval detection from the
selection of a best observing instant. Preserve the legitimate exclusion of
zero-length windows, while interpolating a crossing before the final sample.

### A4. Monthly and nightly visibility impose different twilight policies

Priority: medium, policy inconsistency. Owners:
`SkyfieldAstronomyEngine.catalogue_month_visibility()`, `_month_dark_samples()`,
`observing_night_window()` and the NSOM environment contract.

The monthly filter admits non-Sun objects only at Sun altitude below -18 degrees,
including the Moon and planets. Nightly planning instead starts at sunset,
about -0.833 degrees, and the NSOM environment has no solar-altitude factor.

Real DE421 probe, Edinburgh (55.95, -3.19), June 2026: there are no astronomical-
darkness samples, and the monthly filter returns false for Moon/Venus/Jupiter.
Yet the same observer has these above the 15-degree threshold after sunset:

| Object | Local instant (Europe/London) | Object altitude | Sun altitude |
| --- | --- | --- | --- |
| Moon | 2026-06-20 22:15 +01:00 | 20.193 deg | -1.985 deg |
| Venus | 2026-06-06 22:00 +01:00 | 17.915 deg | -1.516 deg |
| Jupiter | 2026-06-01 22:00 +01:00 | 20.039 deg | -2.121 deg |

These are bright civil-twilight targets, not examples of astronomical darkness.
Conversely a DSO's sunset-to-sunrise altitude window is not evidence of a dark
sky. Define a shared, target-aware solar-altitude policy and make the monthly
filter's label match what it actually tests. Do not simply apply -18 degrees to
all nightly targets. Definitions: [USNO twilight](https://aa.usno.navy.mil/faq/RST_defs)
and [Skyfield almanac](https://rhodesmill.org/skyfield/almanac.html).

### A5. Partial weather data can become excellent observing conditions

Priority: high. Owners: `services/weather_service.py`, `_parse_payload()`,
`_hourly_value()`, `_safe_int()` and `_safe_float()`; downstream weather/seeing.

A payload containing an hourly timestamp but absent or null cloud, rain, wind
and humidity fields produces zero for those values. Both isolated probes return
weather **100/100**, seeing **100/100** and transparency **100/100**. Seeing's
low-confidence flag does not undo the fabricated good-condition inputs.
An entirely absent forecast is handled differently and correctly remains
unavailable; this defect concerns partial rows/arrays, not every provider outage.

A non-finite wind value also escapes normalization: NaN raises `ValueError`
at rounding and infinity raises `OverflowError`. Payload parsing occurs after
the request/JSON exception block, so that block does not apply the service's
normal cached-data fallback to these parse failures.

Correction must distinguish missing measurements from genuine zero, validate
parallel-array shape/ranges/finiteness, and define eligibility for partially
known hours. Keep the last valid forecast or explicit unknown state. Test missing
keys, null/short arrays and non-finite values alongside valid clear-sky zeros.
Units used by the request match [Open-Meteo's defaults](https://open-meteo.com/en/docs);
no wrong km/h-to-m/s conversion was found.

### A6. A daytime-only planet can enter the night plan with a zero opportunity

Priority: medium. Owners: `SkyfieldAstronomyEngine._body_details()`,
`application/catalogue_recommendations.home_visible_objects_for_window()` and
`NightPlannerService.plan()`.

For solar-system bodies, `visible` means above the horizon now OR above the
night threshold. `_sample_summary()` returns a best timestamp even when the
whole night is below threshold, and Home admission accepts that timestamp.
The planner filters the old raw score before NSOM ranking, but does not reject
a zero final opportunity.

Real DE421 probe at Rome, reference 2026-09-05 12:00 UTC: Mercury is currently
52.6 degrees high, but its displayed nightly maximum is 4 degrees, below the
8-degree policy. It has no useful observing window, yet `visible=True`, raw
score 48, best time 19:37 and Home admission true. With a one-target pool,
benign synthetic weather and a 200/1000 mm telescope, the real planner returns
Mercury at **19:37 with score 0**. Venus/Mars serve as ordinary positive controls.
This is a focused pipeline probe, not a claim that Mercury always appears among
four recommendations when a large eligible catalogue competes with it.

Separate current-horizon state from useful-night eligibility. Require a
positive-duration useful interval and reject zero opportunities before selection.
Do not hide the problem with a display-score clamp or by deleting current
daytime position information.

### A7. Demonstration fallback is not a durable data-quality state

Priority: medium, failure path. Owners: `application/dependencies.py`,
`MockAstronomyEngine`, `AppController` service-status handling and Home banner.

Ephemeris recovery failure substitutes deterministic mock planets, Moon and
events, not the last valid local calculation. A probe confirms identical planet
data for Rome and Sydney. The composition root does create a warning and Home
renders it; this is not an entirely silent fallback at the composition boundary.

However, the warning lives in the generic `_service_status` string. The
no-location and startup-location-pending paths overwrite it with normal location
instructions. Subsequent `_refresh_all()` preserves the current string for a
mock engine, not necessarily the original ephemeris warning. This is a traced
control-flow finding; no failed real ephemeris was induced in the user's runtime.

Use a persistent engine/data-quality state exposed on all relevant pages, and
disable real observing recommendations/events when only demonstration data exists.
Test recovery failure followed by no location, location detection and selection.

### A8. Moon phase artwork is not quantitatively faithful at quarter phase

Priority: low, visual accuracy. Owner: `ObjectDetailPage.qml`, `drawMoonPhase()`.

The artwork translates one circular shadow over another circle. At 90/270
degrees its geometric illuminated area is about **60.90%**, not approximately
50%, and the quarter-phase terminator is curved rather than straight. Gradients
are decorative; this area calculation concerns the clipping geometry, not pixel
photometry. The numerical lunar illumination comes from Skyfield and is separate.

If the illustration is intended to be scientifically quantitative, draw the
projected spherical terminator instead. Document whether orientation is a fixed
schematic convention or an observer-dependent position angle; the current icon
does not model local orientation or libration. This audit adds a developer
comment, not a visual correction.

### N1. Update discovery does not check platform asset availability

Priority: low/medium, non-astronomical. Owner: `services/update_manager.py`,
`find_newer_release()`.

The updater compares the latest repository release version, without inspecting
its assets or the running platform. An offline Windows-only `v1.45.21` response
still offers that release to a mocked Linux `1.43.0` installation. This matters
while the project publishes different latest Windows/Linux packages. The URL is
properly constrained to the official HTTPS release path; no automatic binary
download/execution occurs here.

Future correction should select the newest release containing a compatible
platform artifact, retaining separate source/release/package status. This audit
does not change the published platform versions or contact GitHub to release.

## Scientific approximations and calibration limits

These are not all implementation bugs; they define what the output can claim.

- **Observer/horizon:** WGS84 zero height, no terrain mask or local obstructions,
  no pressure/temperature refraction for plain AltAz. Rise/set uses conventional
  horizon definitions, so it need not coincide with a displayed altitude of zero.
  The old calculation guide incorrectly listed observer elevation as an input;
  that documentation is corrected. Fixed catalogue coordinates omit proper
  motion/parallax; the independent fixed-target comparisons share that assumption.
- **Sampling:** nightly maxima and threshold crossings are sampled/interpolated,
  not continuous extrema or exact observing start/stop times. A single selected
  connected window can omit another useful interval. Month visibility and annual
  events have separate sample grids. Static meteor-shower templates are approximate
  annual guidance, not predictions of the current year's ZHR/outbursts.
- **Brightness/NSOM:** intrinsic magnitude points saturate at magnitude 10.5, so
  fainter targets of the same class are not distinguished by that component.
  Extended-object concentration, extinction and physical detectability require
  calibration beyond the present type/magnitude policy. Sun magnitude -26.7 and
  Moon magnitude -12.7 are fixed references; **-12.7 is not the Moon's current-
  phase brightness**. A future UI/model change should label that reference or
  compute a phase-dependent value. The squared-major-diameter surface-brightness
  proxy is not a measured mag/arcsec^2 quantity.
- **Optics/imaging:** TFOV = AFOV / magnification, Dawes resolution and aperture-
  only limiting magnitude are estimates with omitted field-stop/eye/seeing effects.
  Nominal reducer factors and backfocus checks do not certify mechanical assembly.
  Video f-ratio/pixel-pitch rules and still-exposure/mount caps are empirical;
  they do not solve wavelength/PSF sampling, detector SNR or local field rotation.
  Solar imaging eligibility requires declared protection; a software flag cannot
  certify actual filter integrity, mounting or safe observing practice.
- **Seeing/atmosphere:** surface wind, gusts, cloud and humidity are proxies,
  not a vertical turbulence forecast. NSOM's multiplicative factors are bounded
  ranking attenuation, not measured transmission or detection probabilities.
  Keep atmosphere-only transparency separate from the legacy display index that
  already includes a light-pollution adjustment. Confidence is not an extra score
  multiplier. AOD/PM are alternative aerosol inputs, not additive measurements
  of the same quantity; PM concentration is not an optical-depth measurement.
- **VIIRS:** the configured product is VNP46A3 collection 002, whose radiance
  format differs from collection 001. Do not incorrectly diagnose a mandatory
  0.1 scale-factor omission by reading the older packed-integer specification.
  No authenticated live granule was fetched in this audit.
  [NASA product/version description](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A3/).
  The audit's inference for NightScope is that satellite upward radiance cannot
  by itself establish local zenith brightness: the radiance-to-Bortle-to-SQM/NELM
  mapping needs empirical validation. Pixel-quality confidence does not validate
  those derived ground-sky estimates.
- **MAIAC:** the reviewed readers apply the product scale/fill metadata and
  inspect cloud, adjacency and AOD-quality bits. The masks correspond to the
  documented MAIAC definitions; synthetic/provider tests cannot certify all live
  retrievals or their local representativeness. [MAIAC guide, collection 6.1](https://lpdaac.usgs.gov/documents/1500/MCD19_User_Guide_V61.pdf).
- **ISS:** OMM elements use SGP4, with epoch-age and search-horizon gates plus
  satellite sunlight and observer-darkness checks. This is appropriately distinct
  from heliocentric two-body propagation, but manoeuvres/element age limit timing
  and position accuracy. No live pass was validated against an observation.
  [Skyfield satellite guidance](https://rhodesmill.org/skyfield/earth-satellites.html).
- **Comets:** SBDB perihelion TDB-to-TT conversion and the total-magnitude law
  `M1 + 5 log10(delta_AU) + K1 log10(r_AU)` are consistent with the referenced
  conventions; there must be no extra factor 2.5 on K1. Two-body osculating
  propagation ignores perturbations/non-gravitational forces and the brightness
  law cannot forecast outbursts. The coarse window's Moon veto uses illumination
  and separation but does not check whether the Moon is above the horizon; this
  should be reconciled with the main Moon-geometry policy. Terminal valid samples
  are extended by one sample step, so durations are estimates, not solved threshold
  crossings. [JPL SBDB timescales](https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html)
  and [Horizons magnitude law](https://ssd.jpl.nasa.gov/horizons/manual.html).

## Architecture and remaining verification boundaries

The current separation of raw astronomical inputs, display adjustments and NSOM
read models is important and should be preserved. Shared dependency construction,
stable object IDs, explicit equipment capability checks and isolated runtime
smokes are substantive strengths. The controller, astronomy engine and bootstrap/
equipment persistence modules remain concentration points; passing import-layer
checks does not make their stateful paths trivial or fully typed.

No global type-checking proof, concurrency stress test, security penetration test,
Linux bundle validation, authenticated provider campaign or observatory-grade
validation was performed. Remaining hardening targets include partial provider
units/coordinates, finite/range validation at legacy display-text parsers, robust
UTC timestamps across every DTO, persistent degraded-data provenance, and
calibration of heuristic scoring against representative observing cases. In
particular, an OpenAQ latitude/longitude of zero can be lost in the coordinate
fallback's `value or alternative` expression when no explicit distance exists;
that is a bounded input-normalization issue, not evidence of a universal location
error. Existing regression coverage alone cannot close these questions.

## Documentation delivered and correction plan

Added focused in-code contracts for observer coordinates/night states, sampled
windows, optical units/estimates, NSOM interpretation, surface-brightness proxy,
forecast parsing, seeing, VIIRS provenance, comet timescale/brightness, imaging
exposure/video limits and schematic Moon artwork. The calculation guide and
current handoff link this report. Formulas, thresholds, catalogue contents,
translation strings, schema and source version remain unchanged.

Suggested bounded correction sequence:

1. A5: unknown/invalid weather must not become clear-sky evidence; keep genuine
   zero values valid and preserve the last valid/explicitly unavailable state.
2. A1/A3/A6: shared target classes and positive useful-window eligibility through
   initial geometry, live refresh, Home and planner; regression tests for the
   reproduced nebula, terminal crossing and Mercury cases.
3. A2: UTC time arithmetic and timestamp-rich contracts across both DST changes,
   weather/planner ordering and event durations.
4. A4/A7: explicit target-aware twilight and persistent unavailable/demo provenance.
5. A8/N1 and calibration/UI limits: quantitative Moon illustration, phase-dependent
   magnitude/reference labeling and platform-aware update discovery; then consider
   empirical calibration without retroactively presenting heuristics as physics.

Each behavioural correction needs its own before/after regression evidence and
explicit authorization; the audit's numerical probes are not failing tests added
to the normal suite. Resume editorial work only after agreeing which correctness
items to close first.

## Post-edit verification

- Parsed the complete 250-module Python inventory and compared each of the
  **15 modified Python modules** with `b567a2b`, stripping only actual module/
  class/function docstrings. All executable ASTs are identical. QML diff review
  confirms the only UI edit is a three-line comment.
- Ruff, documentation inventory, import-cycle/protected-layer checks and the
  unchanged Bandit baseline passed after the documentation edits.
- Reran **153 focused tests**, all passed in **18.56 seconds**: astronomy
  validation, coordinates, observing-night bounds/weather, comet windows,
  imaging trains/recommendations/exposure/video, NSOM model/environment,
  planner scoring and weather hardening.
- The full 1,251-test/10-subtest security source gate was the pre-edit baseline
  run. It was not unnecessarily repeated for a patch whose executable ASTs,
  thresholds, dependencies, fixtures and translated strings are unchanged.
- No version bump, catalogue edits, runtime-data changes, distribution rebuild,
  tag, release or remote CI wait is part of this audit.
