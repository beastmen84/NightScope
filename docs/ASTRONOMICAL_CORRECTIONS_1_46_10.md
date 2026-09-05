# NightScope 1.46.10: astronomical audit corrections

Date: 2026-09-05. Implements the user-authorized follow-up to the
[1.46.9 audit](ASTRONOMICAL_CODE_AUDIT_1_46_9.md), documentation commit `e1705c4`.
The historical audit remains unchanged as evidence of the original defects.

## Corrected contracts

| Finding | Implementation and regression boundary |
| --- | --- |
| A1 | Stable solar-system IDs select the 8-degree altitude floor; planetary nebulae retain the DSO 15-degree floor in initial, live and Moon-geometry paths. |
| A2 | UTC elapsed sampling/interpolation, positive-window comparisons, 24-hour weather selection and comet durations. Target and plan DTOs retain offset-bearing ISO instants; ordering never round-trips through HH:MM. Legacy skipped clocks are rejected and repeated clocks can select a fold; ambiguous display minutes include a UTC offset. |
| A3 | Closing samples participate in crossing detection and the batch prefilter. A positive final segment is retained; an endpoint-only threshold touch is not. Best time remains inside the positive interval. |
| A4 | Both month and night use astronomical darkness for DSOs and Uranus/Neptune. Moon, Mercury, Venus, Mars, Jupiter and Saturn accept sunset twilight. Sun retains daytime catalogue eligibility and is not a night-plan target. |
| A5 | Missing/null/non-finite/out-of-range core weather fields reject the hour; genuine zero remains valid. Missing optional seeing inputs stay unknown. Bad fresh payloads use a valid cache or explicit unavailable state; future-dated caches are rejected. New Open-Meteo requests use Unix seconds, not ambiguous local ISO clocks. |
| A6 | Current above-horizon state is independent of `night_eligible`. Home and Planner require a positive useful interval from real-engine targets; Planner rejects zero final NSOM opportunities. Legacy display-only adapters do not override explicit negative eligibility. |
| A7 | Failed ephemeris recovery creates `UnavailableAstronomyEngine`, not a demonstration sky. Positions, lunar estimates and events are empty/unavailable. Controller provenance and a global QML header survive no-location/detection/selection transitions. |
| A8 | The actual QML clipping path projects a spherical terminator. Quarter phases illuminate half the disk; waxing-right/waning-left is a fixed schematic convention, not local orientation/libration. |
| N1 | Update discovery scans bounded release-list pages for an uploaded official Windows/Linux x64 artifact matching its tag. Drafts, prereleases, checksums, empty assets, other architectures and external URLs are not package evidence. |

Additional bounded corrections: OpenAQ latitude/longitude zero survive alias
fallback; the comet Moon-separation veto is neutral when the Moon is below the
local horizon. The fixed lunar magnitude is now labeled as a full-Moon reference
in Object Detail; no phase-dependent photometric model was invented.

## Implementation limits

- These are planning policies, not detection probabilities. The Moon and bright
  planets can be seen in twilight; this does not mean every target admitted by
  a geometric threshold will be detectable with every setup. Month sampling
  remains hourly, night sampling 15/30 minutes, and grazing monthly windows can
  be missed. Polar daylight/unavailable states remain distinct.
- One connected sampled useful interval is retained. In continuous polar-night
  containers the longest astronomical-dark interval is selected. Crossings are
  linearly interpolated, not exact continuous extrema.
- Moon diagnostics retain a bounded shared 30-minute batch grid; narrow windows
  without a sample report unknown geometry. Adding each catalogue object's
  boundaries to the global matrix would cause avoidable quadratic work.
- Core weather requires cloud, precipitation probability, wind, humidity and
  temperature. Optional cloud-layer/gust/visibility/dew-point inputs must be
  present for the basic seeing estimate. Unknown does not mean perfect seeing;
  the existing low-confidence neutral estimate is retained when unavailable.
- Legacy clock-only adapters remain supported. Real Skyfield targets and new
  provider rows use absolute timestamps. The update scan is bounded to 300
  releases; current supported artifacts are Windows x64 ZIP and Debian-12/Linux
  x64 tarball. This is not certification for arbitrary Linux distributions.
- No NSOM weights, optical/imaging formulas, catalogue identities, editorial
  text, schema, dependencies, user runtime files or portable distribution changed.
  Scientific calibration, authenticated-provider validation, terrain/refraction
  and observatory-grade astrometry remain separate projects, not bugs declared
  solved by a green regression suite.

## Verification

Focused regressions are in `astro_viewer/tests/test_audit_corrections.py` and
the existing weather, night-window, Moon, planner, update and composition suites.
They include both Europe/Rome DST changes, the synthetic 05:45-06:00 positive
pre-dawn window, the real Rome 2026-09-05 daytime-only Mercury case, Edinburgh
June twilight visibility, genuine clear/calm weather, invalid provider inputs,
positive versus zero opportunities and engine-failure location transitions.

The Moon geometry test executes the production QML drawing function in Qt's
JavaScript engine, computes its polygon area for eight phases and checks a
straight quarter terminator (absolute area-fraction tolerance 0.0002). Separate
offscreen QML renders exercise the same production function in normal/red modes.
Local diagnostic artifacts are under `build/astronomy-fixes-1.46.10/` (ignored).

The prior audit's independent probes were rerun on this corrected source:
288 Skyfield/Astropy positions at Rome, Sydney and Tromso across four dates,
with maximum angular difference 2.6084 arcseconds; all 240 optical identities
across 48 configurations pass. Both astrometry pipelines use the same DE421
kernel: this checks the coordinate transformation, not JPL's kernel accuracy.
The Edinburgh June probe now admits the Moon, Venus and Jupiter in sunset
twilight despite zero astronomical-dark samples.

The complete `tools/run_checks.py --security` source gate passed on
Windows/Python 3.14.5: 1,332 tests and 10 subtests, no failures/skips, 223.57 s
for pytest, 86% application coverage (17,799 / 20,633 executable lines).
The final run includes 81 additional cases compared with the audited baseline.
Documentation inventory covers 251 Python, 34 QML and 17 operational files.
Ruff, compilation, import/layer boundaries, licenses and catalogue snapshots
pass. Bandit remains at its reviewed 0-high/34-medium/14-low baseline;
`pip check` is clean and `pip-audit` finds no known vulnerabilities.
Backend, normal QML and Red Night Vision QML smoke tests pass in isolated
runtimes. The full log is `build/astronomy-fixes-1.46.10/source-gate.log`.
Timing is a local measurement, not a new test-performance claim.

Intermediate focused/complete runs exposed fixture expectations tied to the
corrected behavior: an uninitialized fake engine needed an explicit darkness seam,
the Python inventory grew by one, the old Mercury/Mars monthly exclusions
assumed the all-body darkness policy, and a catalogue-toggle scenario needed
valid seeing inputs to isolate its actual assertion. Moon scalar/batch
equivalence and numerical tolerances are retained; the M13 lunar-separation
reference changes from 116.56 to 116.92 degrees because it now describes the
dark useful interval. Uranus remains excluded in that conservative monthly
fixture. No failing scientific assertion was deleted to obtain a green gate.

All three Qt catalogues were re-extracted and compiled after the final source
changes: 2,064 finished messages each, no new/unfinished/empty messages after
the two reviewed additions and removal of the obsolete fallback warning.
The large TS diff mostly refreshes generated Python source-location references;
editorial JSON overlays are unchanged. `qmllint` over all 34 QML files exits 0;
non-fatal context/unqualified-access diagnostics remain recorded in the local
`qmllint.log`, not represented as zero warnings.
After the final documentation/translation refresh, the focused tooling and
translation suite also passes: 75 tests in 10.09 s.

The actual application shell was rendered at 1040 x 700 in six disposable
IT/EN/ES scenes (normal Home and red Calendar), with the ephemeris constructor
deliberately failing. The new banner remains complete and translated across
page/language/theme changes. Its text and the eight-phase normal/red Moon
renders pass visual review. This is targeted UI evidence, not completion of
the entire release visual/provider matrix.

No GitHub Actions wait, push, new bundle, tag, checksum/archive or publication
is part of this correction step. Public Windows remains 1.45.21; public Linux
remains 1.43.0, verified against the official release assets on this date.

Method references: [Python datetime arithmetic](https://docs.python.org/3/library/datetime.html),
[USNO twilight definitions](https://aa.usno.navy.mil/faq/RST_defs),
[Open-Meteo timestamp and weather contract](https://open-meteo.com/en/docs),
[Qt Canvas paths/clipping](https://doc.qt.io/qt-6/qml-qtquick-context2d.html),
[GitHub release and asset API](https://docs.github.com/en/rest/releases/releases).
