# NightScope 1.46.21 - Home Presentation Performance

Date: 2026-09-07. Scope: source only; the local Windows bundle remains
1.46.18. No data migration, package build, push, tag or publication.

## Implementation And Preserved Behavior

1. A lean Home projection replaces full detail DTOs. Each target is prepared
   once and shared by plan and alternatives. Image resolution is shared with
   full details; personal files and fallback are checked again on every read.
2. A controller-owned zero-interval, single-shot timer coalesces consecutive
   Home notifications in asynchronous desktop mode. Other signals and direct
   synchronous-controller notification semantics are unchanged. Pending Home
   notifications stop with the performance workers.
3. The existing observing worker prepares Home clock labels and sorting before
   atomic publication. One immutable timing snapshot may be reused only for
   the same ordered target instances and the same night instance. Replacements,
   even equal-looking DST boundaries, invalidate it. No image, final rendered
   payload or profile is cached. Cancellation and stale-context checks apply
   to this preparation too; no additional worker or repository access is added.

All targets remain available. Four plan slots, canonical deduplication,
chronological/natural ordering, naked-eye compatibility and image defaults
use the existing rules. Scientific calculations, scoring, thresholds, Qt
layouts, periodic refresh/backup cadence and user runtime data are unchanged.
Direct synchronous use and presentation-only target replacements have a
correct synchronous fallback; this is not a claim that every getter is
universally nonblocking.

## Paired Measurements

Probes use the original `8e86509` Home methods, the same process, fixed
Rome 2026-09-07 observing/weather context, a Newton 150/750 profile and a
disposable copy of the existing audit database. Network access is disabled;
OpenBLAS uses one thread. Default and fully enabled catalogue runs are serial,
not concurrent with coverage tests. Timing excludes JSON serialization and
the separately recorded cProfile pass.

The first lean-projection step, before detached timing preparation:

| Catalogue | Targets / alternatives | Old getter | Lean getter |
| --- | --- | --- | --- |
| Default | 131 / 127 | 0.108-0.114 s | 0.018-0.023 s |
| All enabled | 4,462 / 4,458 | 3.766-4.286 s | 0.575-0.681 s |

Every final Home field matches, as do all full detail DTOs and the public
`homeVisibleAlternatives` contract. Final payload size remains 59,165 and
1,866,785 UTF-8 JSON bytes: no target truncation or loss of displayed fields.
The full-catalogue SHA-256 is
`911fcae8c5b37ba4a1e4ade73d0419bf9e25ce3a1fcd5b384f5014bc9522f5a2`.

Before the third step, real QML month/profile scenarios still recorded
1.67/2.73 s maximum Qt heartbeat gaps, versus 13.88/28.77 s with the old Home
adapter. This prompted detached timing preparation rather than treating
the getter speedup as proof of a completely responsive UI.

After detached preparation, the final full-catalogue paired run measures
3.044-3.457 s for the old getter, 0.503-0.537 s for the explicit cold fallback,
and 0.098-0.123 s with matching timings already prepared. These are getter
times, not end-to-end refresh or frame timings; preparation still consumes CPU
in the worker. Full detail and public alternative parity passes again.

The final extended QML rerun measures maximum month/profile heartbeat gaps
of 1.188/1.181 s, versus 13.883/28.770 s for the original Home adapter. Request
handlers return in 0.026/0.0004 s. Total elapsed scenarios are 16.41/3.05 s;
astronomical work and rendering are included and this is not a CPU reduction
claim. The first cold fixture read was 1.04 s; subsequent prepared reads were
mostly 0.11-0.13 s, with cold presentation replacements up to 0.48 s.

The final default-catalogue comparison is 0.083-0.099 s old,
0.016-0.021 s cold and 0.004-0.006 s prepared, with identical payloads.
The default QML month/profile gaps are 0.312/0.170 s; total elapsed scenarios
2.99/0.62 s, with 18 language/theme/page scenes and no QML warnings.

Evidence is under `build/home-performance-1.46.21/`: `verify_home.py`,
`verify_home_ui.py`, `verify_home_rows.py`, the initial `all/` and `default/`,
`qml-current-all/`, `qml-legacy-all/`, and the separate `final-*` /
`qml-final-*` results. These disposable probe outputs are ignored; the
regression tests and this methodology are tracked.

## Validation

The first step passed 105 focused tests and paired full/default catalogue
checks before commit `efce203`. Notification lifecycle tests passed before
commit `18d53b7`. With detached preparation, 109 focused Home/worker tests
pass, including input identity, immutable mappings, real background-thread
preparation, atomic publication and rejection of superseded work.

Additional coverage compares every Home field across six session states,
loading, four equipment configurations, duplicated/missing entries,
midnight, DST, polar night/day, legacy clocks, IT/EN/ES changes and personal
image removal/restoration. Initial new-test fixture assumptions (naked-eye
count, absent versus null night, profile-name storage and a lazily created
generation attribute) were corrected; no production behavior assertion or
security baseline was weakened.

The full-catalogue final matrix covers IT/EN/ES and both themes, Home/catalogue/
profiles, the real month control, previous-plan retention, equipment snapshots
and 7,594 exact monthly visibility values. The additional rows probe checks
all 4,458 alternatives, the three type filters and Sky Compass scoping across
12 language/theme/width combinations (1440 and 1040 pixels). It scrolls to
the true final row and clicks it to open the complete detail DTO. All these
final probes pass without QML warnings.

One earlier final-matrix attempt emitted two QML incubation/context-destruction
warnings during rapid automated navigation and failed its warning assertion.
The same scenario was rerun without changing application/QML source, retaining
the strict assertion and adding diagnostic logging; it passed. The separate
12-combination row/navigation test also passed. The initial warning is not
claimed fixed or silently suppressed; native/rapid-navigation QA remains
appropriate. The first rows-probe attempt searched QObject ownership rather
than the ListView visual tree; it was corrected to inspect visual children and
use the actual positionViewAtEnd method, without changing the application.

The complete `tools/run_checks.py --security` gate passes on 2026-09-07:
1,728 tests plus ten subtests in 181.12 s, 87% coverage (18,971 / 21,896
executable lines). Isolated backend/normal/red QML smokes pass in
9.6/9.0/8.2 s. Ruff, compileall, documentation and import/layer boundaries,
installed dependencies, license inventory, MPC/NGC/editorial and imagery
audits pass. pip-audit finds no known vulnerabilities; the Bandit baseline
remains 48 findings (zero high, 34 medium, 14 low). Inventory: 271 Python,
36 QML and 17 operational files. Log: `final-source-gate.log` in the evidence
directory. No application source changes followed this passing gate.

The two final QML matrices cover
36 page scenes and eight transition captures; the separate row/detail probe
adds 25 captures. Four table/detail samples were visually inspected, including
compact English and red Spanish. Historical 1.46.20 gate results remain
historical; this report does not reuse them as validation of the new source.
QML sources were not edited. The previously documented standalone qmllint
startup failure was not revisited; runtime validation above is not a new
qmllint pass or native artifact approval.

## Remaining Limits

The final complete payload must still cross the Python/QML boundary, and
QML filtering/model updates run on the UI thread. A cold synchronous fallback
can still prepare timings there. The ListView was already virtualized and
is unchanged. Native desktop behavior on the reporting user's slower PC
has not been measured; offscreen checks do not certify every rendering path.
