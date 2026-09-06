# NightScope Testing Workflow

This document contains the current validation contract. Historical measurements
through source `1.45.6` are preserved in
`docs/archive/TESTING_HISTORY_THROUGH_1.45.6.md`; release approval remains in
`docs/RELEASE_CHECKLIST.md`.

## Public Release Metadata - 1.46.13 Windows

On 2026-09-06 GitHub confirmed the user's published `v1.46.13` release:
not draft, not prerelease, tag at `b34ec4a`, one Windows x64 ZIP, no Linux
asset. Linux remains on the public `v1.43.0` package. The tag differs from
the locally validated `be30cda` only in validation documentation. Asset size
and GitHub-reported ZIP digest are in the handoff; the archive was not
downloaded or re-audited for this documentation-only update. The following
source/build results remain dated evidence, not a new public-artifact gate.

Current README, manual and EN/IT/ES website release references are aligned,
including download links, accessible button labels, JSON-LD and sitemap dates.
The English manual footer now matches revision 1.46.13. Website assertions
compare complete version tokens, so 1.46.13 is not misclassified as 1.46.1;
they still reject every version outside the two public platform versions.
Per-language manual regressions protect release links and footer parity.
No runtime code, VERSION, dist, published asset or existing release is changed.
The final focused run passes all 49 developer-tooling tests in 8.71 s; Ruff
and the code-documentation gate also pass (259 Python / 35 QML / 17 operational
files). Existing navigation, legal, runtime-isolation and publication-boundary
assertions are retained. The initial run caught stale FAQ versions and the
checklist's missing canonical labels; documentation was corrected without
relaxing those checks. Logs: `build/release-docs-1.46.13-20260906/`.
The manual/notices inside the already published ZIP and local dist remain
unchanged; this is a repository/website-source update, not an artifact replacement.

## Local Windows Bundle - 1.46.13

The 2026-09-06 official Windows rebuild uses clean source `be30cda`, Python
3.14.5, PyInstaller 6.22.2, hooks-contrib 2026.7 and Qt/PySide6 6.11.2.
The bundle contains 5,145 files / 429,331,997 bytes. All 108 declared source
assets and five legal files match SHA-256; the embedded version is 1.46.13.
Executable SHA-256:
`40F5AB2EBD9FB1C74FDFDC5DF76D3A5AB5C8D0B8E3285207708B1C44391A4EF4`.

Qt/legal/runtime audit passes, including the newly required Dialogs and
folder-list modules. Packaged backend, normal-QML and red-QML smokes exit 0
from a disposable copy, with separate empty runtimes, empty stderr and no
runtime ERROR/CRITICAL/traceback entries. Each DB passes integrity/foreign-key
checks, schema 27, nine Solar image rows, zero personal associations and exact
parity for all 323 descriptions and 323 curiosities. No user-data upgrade
matrix is claimed. The smoke copy and all three runtimes were removed.

The additional packaged Windows image test keeps Python, Qt and production
detail/editor QML unchanged and uses a disposable test-only entry point.
UI Automation selects a synthetic JPEG through the native Windows `#32770`
dialog; the fallback opens and accepts through its QML signal. Preview,
save, M31/NGC 224 alias sharing, cancellation, red image suppression/reset and
Solar replacement pass. Restart loads the saved Moon photo after the synthetic
original is removed. Both processes exit 0, and final forced-QML stderr has
only QA progress/pass markers. The original bytes are unchanged until test
cleanup; only two managed JPEG files are stored. The temporary copy/runtime
is removed. No full manual desktop/three-language/provider matrix is claimed.

Initial QA-only iterations corrected native-control readiness, enabled Qt
stderr for the windowed executable, and removed screenshot attempts against
the hidden test window. The real source/detail lifecycle is represented by
a Loader in the final harness; initial empty-detail binding diagnostics do
not recur. These were harness changes, not application or bundle fixes.
Earlier attempt logs remain in the ignored evidence directory. Final logs:
`packaged-picker.log`, `picker.stderr.log`, `restart.stderr.log`.
The seven required embedded image/backup/credential/timezone modules are
verified, and the final pristine bundle audit passes. The documentation and
tooling recheck passes 46 tests in 9.57 s.

The existing dist and its local runtime state were replaced without backup,
per the user's explicit request. Evidence: `build/windows-dist-1.46.13-20260906/`.
The unchanged source gate below was not rerun. No Linux artifact, public
release, archive, tag, signing or antivirus scan is part of this rebuild.

## Personal Image Lifecycle - Source 1.46.13

On 2026-09-06 the complete security/coverage source gate passed: 1,452 tests
and 10 subtests in 225.57 s, 86% coverage (18,211 / 21,085 production lines).
Pip check/audit, Ruff, documentation (259 Python, 35 QML, 17 operational files),
import boundaries, unchanged Bandit baseline (48: 0 high, 34 medium, 14 low),
licenses and all catalogue/editorial/image checks passed. Backend and normal/red
QML smoke tests passed in isolated fresh runtimes. Dependencies are unchanged.

Twenty new lifecycle cases cover committed DELETE/WAL snapshots, uncommitted
transaction exclusion, failure/timeout preservation of the previous backup,
path redirection, immutable-file conflicts, old-backup restoration after image
replacement/reset, current-path reconstruction, personal profile/editorial
preservation, legacy migration including WAL, Home metadata and nested-bundle
privacy/plugin rules. Three additional controlled-worker cases prove that a
second preview cannot start concurrently and cancelled/red/changed-target
results cannot publish. The existing tests and assertions remain active.

Focused runs passed: 131 storage/database/tooling/path tests and 99 image/
lifecycle/tooling/Home tests. The serial 131-test process emitted one shutdown
GC ResourceWarning (145 uncollectable objects); it did not recur in the 99-test
run or full four-worker gate. No warning filter was added or relaxed.

All 35 QML files lint with exit 0 and existing non-fatal diagnostics. IT/EN/ES
compile to 2,088 finished messages each, zero unfinished. Actual Home QML passes
21 personal/missing/corrupt/replaced/reset/normal/red states across the three
languages; the six decoder/file warnings are deliberately induced fixtures.
All 48 default-category normal/red/restored states also pass without warnings.
Three Home red renders have zero off-red pixels and maxima 217/74/61, with a
black test-window clear colour so standalone rounded corners cannot inherit
Qt's default white background. Source screenshots and assertions are recorded
in [the visual checklist](VISUAL_CHECKLIST.md).

Evidence: `build/personal-imagery-1.46.13/`, including `source-gate.log`,
`storage-tooling.log`, `image-recheck.log`, `home-review.log`,
`category-home-recheck.log` and `red-home-pixels.log`. Source steps 1.46.11-13
are complete; Windows/Linux build and native-picker tests remain separate.
No dist, public release, push, tag or remote CI wait is part of these checks.

## Personal Images - Source 1.46.12

On 2026-09-05 the complete `tools/run_checks.py --security` gate passed:
1,429 tests and 10 subtests in 215.14 s, 86% application/entry-point coverage
(18,119 / 20,981 lines). Pip check/audit, Ruff, documentation (257 Python,
35 QML, 17 operational files), import boundaries, unchanged Bandit baseline
(48 findings: 0 high, 34 medium, 14 low), licenses, all catalogue/editorial
and image gates passed. Backend and normal/red QML source smoke tests passed.

The 22 new image tests cover real decoding, bounded inputs, orientation and
metadata removal, immutable storage, failures, preview cancellation, aliases,
schema-26 upgrade and persistence without originals. Existing NSOM read-model
tests also protect use without a live Qt property wrapper. Two pre-existing
equipment/catalogue integration fixtures now hold the planner clock at 20:00:
their 21:00-23:00 target must not expire depending on the time the suite runs.
All their original assertions remain; production astronomy is unchanged.

IT/EN/ES compile to 2,088 finished messages each, zero unfinished. All 35 QML
files lint with exit 0 and tracked non-fatal diagnostics. The real application
shell exercises 36 detail-editor scenes at 1040x700 across the three languages,
M31 and Moon, save/cancel/corrupt/reset and red mode. A second complete pass
opens the offscreen Qt Quick FileDialog fallback and accepts files through its
actual QML signal. Six expected corrupt-fixture decoder warnings verify fallback;
there are no unexpected QML warnings. Six red captures have zero off-red pixels,
channel maxima 217/74/61. See [Visual checks](VISUAL_CHECKLIST.md).

Logs/helpers: `build/personal-imagery-1.46.12/`, especially
`source-gate-final.log`, `qml-editor-review.log`, `filedialog-review.log` and
`red-pixel-audit.log`. No dist, push, tag, publication or remote CI wait.
Native desktop and packaged-plugin tests remain artifact gates; backup/restore
hardening is the next source step, 1.46.13.

## Environment

Create a virtual environment and install runtime and developer dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r astro_viewer\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

On Linux, replace the executable with `.venv/bin/python`. The standard runner
always uses four pytest workers. Do not substitute `-n auto`: PySide and
Skyfield make each worker comparatively expensive, especially on high-core
Windows hosts.

The `1.46.13` Windows/Python 3.14.5 environment retains pip 26.2.1,
Ruff 0.16.5, coverage 7.16.0, PyInstaller 6.22.2,
`pyinstaller-hooks-contrib` 2026.7, PySide6/Qt/shiboken6 6.11.2, Skyfield 1.55,
Astropy 8.0.1, astropy-IERS-data `0.2026.8.31.0.57.9`, NumPy 2.5.2,
earthaccess 0.18.0, s3fs/fsspec 2026.7.0, aiobotocore 3.9.0, and botocore
1.43.56. The five Earthdata requirements are intentionally constrained and
must be upgraded as one resolver unit.

## Standard Source Gates

Fast complete gate without coverage:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast
```

Fast gate plus installed-environment vulnerability audit:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast --security
```

Full source/release gate with coverage and dependency audit:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
```

The runner performs these checks in order:

1. `pip check`.
2. Ruff over application, tests, developer tools, and packaging Python modules.
3. Complete Python, QML, and operational-file documentation inventory.
4. Production import-cycle and protected-layer validation.
5. Bandit comparison with the reviewed source-context baseline.
6. Quiet bytecode compilation, including packaging Python modules.
7. Third-party license archive validation.
8. Offline MPC observatory snapshot validation.
9. Offline OpenNGC snapshot and derived-seed validation.
10. Network-free catalogue editorial baseline, translation, provenance, and
    accepted-batch validation.
11. Network-free Solar System/category image inventory and format validation.
12. Optional `pip-audit`.
13. One complete pytest pass, with or without runtime-code coverage.
14. Backend smoke test in a disposable runtime.
15. Normal-mode QML smoke test in a disposable runtime.
16. Red Night Vision QML smoke test in a disposable runtime.

The source gate does not build, update, or approve `dist`.

## Architecture And Security Policies

`tools/check_code_documentation.py` discovers governed Python and QML sources
recursively and validates the operational source families defined in
`docs/CODE_DOCUMENTATION_POLICY.md`. It enforces responsibility docstrings and
purpose/contract headers; review still owns their semantic accuracy.

`tools/check_import_cycles.py` rejects strongly connected components and
self-imports in production Python modules. It also prevents models, database,
astronomy, and service modules from importing either the Qt view-model layer or
the application composition layer. These rules protect the outer dependency
boundaries without pretending that the current codebase is a pure clean-
architecture implementation.

`tools/check_bandit.py` scans the application, entry point, and developer tools.
The baseline records rule, severity, confidence, portable path, triggering
source line, and a hash of Bandit's code context after line numbers are removed.
A new finding, removed finding, changed context, or reclassification fails.
High-severity findings are never accepted.

Inspect a proposed baseline without writing it:

```powershell
.\.venv\Scripts\python.exe tools\check_bandit.py --render-baseline
```

Use `--write-baseline` only after reviewing every difference and its rationale.

Pytest promotes unexpected warnings to errors. `pytest.ini` contains only two
repository-wide exceptions: the exact Skyfield `dtype` and `shape` deprecation
signatures caused by NumPy 2.5, constrained by message, category, and module.
The `dtype` exception remains reproducible with Skyfield 1.55 and NumPy 2.5.2.
Remove both filters only when the corresponding upstream behavior is fixed and
rerun the complete astronomy suite.

## Continuous Integration

`.github/workflows/source-validation.yml` reuses the local fast gate on:

- Windows with Python 3.14.5 and
  `packaging/windows-release-constraints.txt`;
- Linux with Python 3.12.

A separate Linux/Python 3.14 job runs `pip check` and `pip-audit` over the
latest resolvable dependency closure. Runtime requirements continue to express
supported ranges, while the Windows constraints file pins the 62 runtime/build
components recorded in `THIRD_PARTY_LICENSES.txt`. A tooling test enforces exact
name/version equality and requires the workflow's Windows Python patch to match
the archive. License collection excludes Python source, bytecode and cache
directories; arbitrary notice filenames are accepted only below the standard
`.dist-info/licenses` directory. The workflow has read-only repository
permission, uses the official checkout and Python setup actions, caches pip
downloads, and does not run packaging commands.

Local validation proves the workflow contract and commands; it does not prove a
remote GitHub run. Record remote results separately when CI has actually run.

## Focused Development Checks

Run the smallest relevant test file while changing one service:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_location_service.py
```

Run the complete deterministic suite directly:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n 4 astro_viewer\tests
```

Use a serial run only to investigate ordering, process, or worker behavior:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests
```

## Seeded Database Setup And Timing

`astro_viewer/tests/database_fixture.py` removes repeated catalogue seeding
from opted-in test setup. The session fixture in `tests/conftest.py` owns a
lazy template per pytest worker, built by the real `initialize_database` from
the current repository schema and seeds. Each test receives a separate file
in its own temporary directory, copied only after initialization has committed
and closed its connections. No database, connection, or mutable test state is
shared, and templates are removed when the session ends. There is no persistent
cache that could hide changes to editorial CSVs between runs.

Call `prepare_database(path, schema)` only when a fully seeded database is
setup, not the operation under test. It refuses existing destinations; pooled
setup also rejects alternate schemas. Keep direct `initialize_database` calls
for bootstrap, migration, recovery, changed-schema/seed, and startup-preflight
scenarios. These tests still execute real initialization.
Plain unittest runs fall back to real initialization without needing pytest.
GeoNames files are still imported by the real importer into each test's copy
from that test's directory; paths, file signatures, cities and aliases are not
borrowed from another test.

Dedicated regression tests compare the complete schema and every table against
a cold bootstrap, with and without GeoNames, plus SQLite integrity/foreign-key
checks and startup preflight. Only import-log surrogate IDs, import timestamps,
and the physical database size measured at import time are normalized: imports
occur in a different order, while source identity and provenance are retained.
Additional checks cover independent mutations, one template build per factory,
fresh session lifetime/cleanup, failed builds, destination protection, and the
standalone fallback. Real controller, Skyfield, NSOM and whole-catalogue/camera
checks remain unchanged; no assertions, numerical tolerances or case loops were
removed to obtain the speedup.

To investigate fixture equivalence, disable reuse explicitly:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n 4 astro_viewer\tests --fresh-test-databases
```

The standard runner keeps four workers and its existing scheduler, full test
selection, warnings policy and coverage scope. It now prints the 20 slowest
test phases taking at least one second. For more timing detail in a focused
run, add `--durations=35 --durations-min=0.1`. Timing reports do not skip tests
or impose flaky wall-clock assertions.

## Specialized Data And UI Checks

Validate and compile every language pack:

```powershell
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py
```

Validate repository images:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\check_object_images.py
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
```

Validate fixed MPC and OpenNGC inputs without network access:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_mpc_observatories.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\update_ngc_catalogue.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py
```

The editorial audit reports the immutable 228-object pre-programme identity,
the 95 accepted NGC-only additions, complete IT/EN/ES coverage, three accepted
enrichment manifests, six baseline-remediation manifests covering 197 objects,
and the remaining 7,271-object NGC-only backlog. The historical paragraph
screen and the new repository-wide IT/EN/ES sentence screen both report zero
findings. The latter catches long shared sentences hidden inside otherwise
distinct descriptions, notes, and curiosities; short recurring advice is
excluded. Regression tests cover normalization, within-object repetition,
scoped waivers, and all three narrative fields in both translation overlays
without `--batch`. Pass `--batch` to screen one candidate batch
for near-duplicate prose; run
`audit_curiosity_sources.py --batch ...` separately because live URL state is
review evidence rather than a deterministic source gate.

Run `pyside6-qmllint` over every QML file below `astro_viewer/app/ui`. Existing
`unqualified access` diagnostics for context properties and nested components
are non-fatal technical debt, but any non-zero tool exit remains a failure.

## Latest Measured Gate

### Category Imagery (Source 1.46.11)

The final exact-identity migration candidate passed the full coverage/security
gate on 2026-09-05: 1,407 tests and 10 subtests in 225.44 seconds for pytest,
86% application coverage (17,838 / 20,672 executable lines), and successful
isolated backend, normal-QML and Red Night Vision smoke tests. The new pure
image resolver has 100% line coverage. Static/documentation/import/license/
catalogue checks pass; the inventory is 253 Python, 34 QML and 17 operational
files. Bandit remains 48 reviewed findings (0 high, 34 medium, 14 low), and
the installed-environment dependency audit found no known vulnerabilities.
This is a local validation timing, not a new test-performance comparison.

The initial full run found one old schema assertion still expecting 25;
only that expectation was updated to 26, retaining the smart-equipment
capability assertions. A subsequent review added an exact historical-ID
allowlist: its new prefix-lookalike regression failed before the correction
and passed after it. All 59 dedicated image tests then passed in 12.55 seconds,
followed by the final complete gate above. No test selection, warning policy,
numerical tolerance, astronomy formula or editorial content was relaxed.

All 34 QML files pass lint with existing non-fatal diagnostics. IT/EN/ES each
contain 2,065 compiled finished Qt messages and zero unfinished messages.
The image gate checks all 25 local JPEGs (907,398 bytes), including the exact
16-category inventory and its SHA-256 manifest. The nine Solar photographs
and the complete IT/EN/ES editorial sources match the previous commit.

Targeted live-QML checks cover 24 detail scenes across three languages,
catalogue/observing branches, 1040x700/1240x820, normal/red/restored modes,
M31, C33, NGC 1 and the Moon. They assert image readiness and identity, exact
translated illustration labels, retained NASA credit, and empty sources in
hidden/red branches; no QML warnings were emitted. Representative captures
were visually inspected. All six red captures have no pixel with green or
blue exceeding red (channel maxima 217/74/61). The real Home row separately
passes 48 thumbnail states: every category in normal/red/normal mode, including
no source/loading in red and successful restoration, with no QML warnings.
This is targeted offscreen validation, not a full desktop/GPU/provider matrix.

A disposable schema-25 database containing all 231 historical image rows,
with a custom-image override and custom editorial prose, upgrades to schema 26:
221 retired records are removed, nine Solar records and the custom image
remain, all 33 other tables are row-equivalent, and SQLite integrity/foreign-key
checks pass. Regression coverage additionally verifies repeat initialization
and preservation of IDs that only resemble old catalogue identities. This is
source migration testing, not an upgrade of the user's real runtime database.

Logs, captures and local-only QA helpers are in
`build/object-imagery-1.46.11/`; the final full log is
`full-source-gate-exact-identities.log`. A final developer-tooling/translation
pass after the documentation updates passed 75 tests in 10.54 seconds.
Generated originals remain outside
application resources. No dist rebuild, remote CI wait, tag, push or public
release is implied; personal-image import and backup/restore are later steps.

### Lunar-Marker Polish (Source 1.46.10)

The subsequent source-only transparency polish passed the complete coverage/
security gate on 2026-09-05: 1,348 tests and 10 subtests in 182.32 seconds for
pytest, 86% application coverage (17,799 / 20,633 lines), and all three isolated
backend/normal-QML/red-QML smoke tests. Static, architecture, security,
dependency, license and catalogue gates pass; the inventories are unchanged.
All 34 QML files also pass `qmllint` with existing non-fatal diagnostics.

The original eight spherical-phase assertions and tolerances remain, now
checked at 44, 88 and 206 pixels, with additional clear-canvas/disc-boundary
checks that failed against the old oversized halo. These 24 focused cases
pass in 2.60 seconds. A separate real-Canvas pixel review at 44, 88 and 210
pixels covers all eight phases in normal/red/normal: alpha is zero outside
the antialiased outline and fully opaque inside the disc. Switching back
restores the exact original frame. Local captures/helpers and gate logs are
under `build/moon-polish-1.46.10/`. This is targeted artwork validation, not
a full page/provider matrix. Version, astronomy, translations and editorial
data are unchanged; the `ae34df5` portable bundle below has not been rebuilt
and does not include this polish. No remote GitHub run was awaited.

### Astronomy-Corrections Baseline

The `1.46.10` coverage/security source gate passed on 2026-09-05 with 1,332
tests and 10 subtests in 223.57 seconds (pytest phase), 86% application coverage
(17,799 / 20,633 executable lines), and successful backend, normal-QML and
Red Night Vision smoke tests in disposable runtimes. Ruff, documentation
(251 Python / 34 QML / 17 operational), import boundaries, reviewed Bandit
baseline (0 high / 34 medium / 14 low), dependency, license and all catalogue
gates pass. No known installed dependency vulnerability was found.
This is local Windows/Python 3.14.5 evidence, not a new timing optimization,
remote CI pass or portable-bundle approval. Detailed evidence is recorded in
[`ASTRONOMICAL_CORRECTIONS_1_46_10.md`](ASTRONOMICAL_CORRECTIONS_1_46_10.md).
New regressions exercise absolute observing intervals, both DST changes,
provider missing-value semantics, target-aware twilight, ephemeris failure,
platform-specific updates and the actual QML lunar clipping geometry. The
editorial seeds, NSOM weights and test-setup reuse policy remain unchanged.
All 34 QML files also passed `qmllint` (exit 0, existing non-fatal diagnostics
retained); IT/EN/ES contain 2,064 compiled, finished Qt messages each. The
targeted visual review covers the eight lunar phases in normal/red and six
real-shell degraded-ephemeris scenes across the three languages, Home/Calendar,
normal/red at minimum size. It is not a complete release visual matrix.

### Historical 1.46.9 And Earlier Evidence

The `1.46.9` coverage/security source gate passed on 2026-09-05 on
Windows/Python 3.14.5 with 1,251 tests and 10 subtests in 310.46 seconds,
86% aggregate application coverage (17,540 / 20,396 executable lines), complete
documentation coverage for 250 Python, 34 QML, and 17 operational files, an acyclic production
graph, zero protected-layer
violations, a reviewed Bandit baseline (0 high, 34 medium, 14 low), clean
dependency/license/MPC/OpenNGC/editorial checks, and successful backend, normal
QML, and Red Night Vision QML smoke tests. The editorial check passed without
warnings and reports zero historical paragraph families and zero shared
narrative sentence families across IT/EN/ES. The in-gate installed-environment
`pip-audit` found no known vulnerabilities. At that baseline the most recent
separate PySide6 6.11.2 `qmllint` pass was `1.45.22`; the newer `1.46.10` check
is recorded above. Non-fatal diagnostics remain tracked technical debt.

The earlier `1.46.8` same-session before/after comparison used the same SDK,
four workers, default scheduler, full test selection and application/entry-point coverage.
The unchanged source baseline was `0aecdb1`; reported durations below are the
pytest phase, not the entire source gate:

| Measurement | Tests / subtests | Pytest elapsed | Covered / executable lines |
| --- | --- | --- | --- |
| Before setup tuning | 1,237 / 10 | 310.62 s | 17,526 / 20,396 |
| After setup tuning | 1,247 / 10 | 216.43 s | 17,539 / 20,396 |

This run saved 94.19 seconds (30.3%). JUnit comparison retained every original
test identity with no skipped, failed or errored tests; the ten additions
protect fixture behavior. JSON coverage comparison lost no previously covered
line and gained 13 bootstrap/preflight lines, with unchanged executable and
excluded-line sets. AST comparison of all 15 changed functional test modules,
normalizing only setup-call names and imports, found no other changes. The
developer-tooling module additionally checks duration reporting/full selection
and the expanded documentation inventory.

The diagnostic `--fresh-test-databases` path separately passed five focused
city, catalogue-migration, profile-persistence and VIIRS scenarios in 9.13 s.
The city-alias scenario also passed as a direct unittest invocation without
pytest. A final focused pass over developer tooling and the three import-order
cleanup modules passed 70 tests in 7.31 s after documentation updates.
The earlier editorial gate's 423.37 s remains historical evidence, not the
controlled pre-tuning timing. These measurements are local Windows results,
not guaranteed timings on other machines or evidence of a remote CI run.

The separate `1.46.9` batch evidence includes 26 successful live source URL
checks, a clean static/similarity audit, and 72 final Object Detail scenes:
six planetary nebulae in IT/EN/ES, normal/red, at upper observing-note and lower
description/curiosity positions. Text, source links and red monochromy passed
visual review. The focused catalogue/translation suite passed 49 tests in
14.15 seconds; existing Spanish terminology checks were preserved and the new
prose aligned to them. Field-level comparison against `fa955d0` retained all
303 previous description/curiosity records and overlays unchanged, adding
20 complete objects (80 narrative fields per language). All other translation
sections, catalogue measurements/designations/flags and image seeds are unchanged.
The initial full run exposed three database tests still expecting 303 records;
only those counters were updated to 323. The separate prefix-diversity check
also prompted a new opening for NGC 2440's Italian curiosity. All three
database checks then passed in 3.79 seconds with their original uniqueness,
minimum-length, prefix and similarity thresholds; the complete gate was rerun
successfully afterwards. That 310.46-second run is not a replacement for
the controlled 1.46.8 optimization comparison or a new performance claim.
A final developer-tooling pass after the documentation/version updates
passed 46 tests in 15.49 seconds; the final batch similarity audit also passed.

The separate `1.46.2` batch evidence includes a successful live audit of 50
distinct manifest URLs and 36 reviewed Object Detail renders: six objects in
IT/EN/ES, each in normal and Red Night Vision mode. The sample spans bright-star
proximity, compact faint, southern edge-on, extended edge-on, cluster-context,
and merger-remnant cases.

The separate `1.46.3` remediation evidence includes a successful live audit of
17 direct object-specific NASA URLs and 84 reviewed Object Detail scenes: seven
objects in IT/EN/ES, normal and Red Night Vision mode, at both the top position
that exposes observing notes and the lower description/curiosity position.
All final text remained complete and free of clipping or overlap.

The separate `1.46.4` remediation evidence includes a successful live audit of
48 distinct object-specific URLs and 108 reviewed Object Detail scenes: nine
open clusters in IT/EN/ES, normal and Red Night Vision mode, at both the top
position that exposes observing notes and the lower description/curiosity
position. All final text remained complete and free of clipping or overlap.

The separate `1.46.5` remediation evidence includes a successful live audit of
41 direct object-specific NASA URLs and 96 reviewed Object Detail scenes: eight
globular clusters in IT/EN/ES, normal and Red Night Vision mode, at both the top
position that exposes observing notes and the lower description/curiosity
position. All final text remained complete and free of clipping or overlap.

The separate `1.46.6` remediation evidence includes a successful live audit of
20 distinct object-specific URLs and 84 reviewed Object Detail scenes: seven
nebulae in IT/EN/ES, normal and Red Night Vision mode, at both the top position
that exposes observing notes and the lower description/curiosity position. All
final text remained complete and free of clipping or overlap.

The separate `1.46.7` remediation evidence includes a successful live audit of
50 distinct NASA Hubble URLs supporting 51 galaxies and 120 reviewed Object
Detail scenes: ten representative galaxies in IT/EN/ES, normal and Red Night
Vision mode, at both the top position that exposes observing notes and the lower
description/curiosity position. All final text remained complete and free of
clipping or overlap, and Red Night Vision remained monochromatic.

The separate `1.46.8` correction evidence includes a successful live audit of
101 distinct manifest URLs and 72 reviewed Object Detail scenes: twelve
representative objects in IT/EN/ES, normal and Red Night Vision mode, at the
lower description/curiosity position. All revised text remained complete and
free of clipping or overlap, and Red Night Vision remained monochromatic.
The field-level diff check confirmed exactly 92 descriptions and five
curiosities across 94 stable baseline identities, with the same 97 edited
fields in each overlay and no changes to unrelated translation sections.
The focused catalogue, translation, and developer-tooling run passed all 91
tests in 19.95 seconds.

No remote CI result, distribution build, source tag, checksum, or release is
implied by that local source measurement.

## Local Windows Distribution - 1.46.10

On 2026-09-05 the requested Windows rebuild completed from clean `ae34df5`
with the official script and the unchanged Python 3.14.5/PyInstaller 6.22.2/
hooks-contrib 2026.7 environment. The user explicitly requested no backup or
preservation of the old dist and manually removed it plus the prior retained
distribution backup after automatic deletion was blocked. No new backup was
created. The new `dist/NightScope` contains 5,277 files / 440,458,423 bytes,
embedded version `1.46.10`, and executable SHA-256:
`06C796709DCBF98847857BF338DFEF7AE92D2D54BDC66129E07EBF826EA8AC7F`.

All 310 declared source assets and five legal files match by SHA-256. The
Qt/legal/runtime-state audit passes before and after packaged tests. Backend,
normal-QML and Red Night Vision smoke tests pass from a disposable copy with
isolated fresh runtimes: exit 0, empty stderr, no runtime errors. All three
databases pass integrity/foreign-key checks and exact source-field parity for
323 descriptions and 323 curiosities. This is fresh-install testing, not a
new upgrade/preservation validation. The current disposable copy and runtimes
were removed, leaving the final bundle pristine. PyInstaller's optional-module/
DLL warnings remain non-blocking for these checked paths, not a guarantee for
every external provider. Logs/helpers: `build/windows-dist-1.46.10-20260905/`.

The earlier 1.46.9 temporary test copy was still present and was separately
reported to the user for cleanup. Source code and dependencies are unchanged;
the full source gate was not repeated. Linux, visual/provider matrices,
archive/checksum publication, signing/scanning, tags and releases are outside
this local rebuild.
The post-build documentation update was followed by 46 passing developer-
tooling tests in 8.69 s; no production code or existing test changed.

## Historical Windows Distribution - 1.46.9

This is dated evidence. Its dist and retained backup were removed at the
user's request before the 1.46.10 rebuild above.

On 2026-09-05 the user separately requested a local Windows rebuild for manual
testing. `packaging/build_windows.ps1` completed from clean source commit
`42b0cb2` with the configured Python 3.14.5/PyInstaller 6.22.2 environment.
The existing complete `1.45.21` distribution was copied to
`dist/_backups/NightScope-1.45.21-before-1.46.9-20260905-142734`; file count/size
matched and all five runtime-file SHA-256 hashes were verified before rebuild.

The pristine `dist/NightScope` contains 5,277 files and 440,456,369 bytes, with
embedded version `1.46.9`. The Qt/legal/runtime-state audit passed. All 310
declared source assets and five legal files match by SHA-256, including QML,
IT/EN/ES translations, the manual, editorial/catalogue seeds, images and DE421.
Timezone polygon data, Qt Positioning and the embedded Windows credential
backend are present. Executable SHA-256:
`90A702F9635CE5DE3A21571DBD223D6EE8FCAE4662CF7C6023668F5894E7F3F0`.

Backend, normal-QML and Red Night Vision smoke tests exited 0 from a disposable
copy with isolated runtime directories. A fourth packaged backend test upgraded
a copy of the previous database; all four runs had empty stderr and no runtime
ERROR/CRITICAL/traceback entries. Read-only SQLite checks confirmed integrity,
foreign keys, and exact seed parity for all 323 descriptions and 323 curiosities
in both fresh and upgraded databases. The previous one-profile state and empty
equipment/observation/preference tables were preserved, as were language and
startup settings. A first overly strict comparison also treated the refreshed
saved-location cache as immutable; inspection confirmed that already-enabled
automatic Windows location detection correctly refreshed coordinates, accuracy
and timestamp. The final check permits only these expected cache fields and
still compares the remaining settings and location metadata exactly. No
production code or existing tests were changed. This sample does not certify
upgrade behavior for populated custom equipment or observing logs.

Evidence and local-only verification helpers are in
`build/windows-dist-1.46.9-20260905/`. The complete source gate above was not
repeated for this unchanged-code artifact build. Manual visual/provider checks,
archive/checksum publication, signing/security scanning and the full release
checklist remain separate. No Linux artifact, version bump, tag or public
release was created.

## Change Policy

For a narrow service change, run Ruff, the architecture/security tools, and the
relevant focused tests first. For shared controller, persistence, astronomy,
provider, QML, localization, or packaging changes, run the complete source gate
before commit. A release artifact additionally requires every manual, provider,
upgrade, legal, visual, and artifact check in `docs/RELEASE_CHECKLIST.md`.
