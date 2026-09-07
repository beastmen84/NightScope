# Home Performance Review And Windows Bundle - 1.46.21

Date: 2026-09-07. Reviewed commits: `efce203`, `18d53b7`, `66c4b5a`
against `8e86509`. No blocking regression found; no application, QML, version,
calculation or test assertion was changed during this review.

## Review And Repeated Checks

- The compact projection supplies every field consumed by the unchanged Home
  service. Full details/public alternatives retain their rich contract, image
  selection and missing-file fallback. Filtering, deduplication and sort rules
  are unchanged; no catalogue limit was introduced.
- Timing preparation uses the existing single observing worker. Publication
  retains generation/context checks; identity matching invalidates replaced
  targets/nights, including equal-looking DST boundaries. One snapshot is held,
  with no cached final payload, personal-image metadata or rendered translation.
- Coalescing is limited to consecutive desktop Home notifications. Direct
  controller notifications remain synchronous, later/reentrant updates are
  retained, and shutdown stops the owned timer.
- A fresh full `tools/run_checks.py --security` passes: 1,728 tests and ten
  subtests in 210.68 s, 87% coverage (18,972 / 21,896 executable lines).
  Backend/normal/red source smokes pass in 9.6/10.2/9.9 s. Static, dependency,
  license, editorial, imagery and layer gates pass. pip-audit reports no known
  vulnerabilities; Bandit remains at 48 findings, zero high. Inventory remains
  271 Python, 36 QML and 17 operational files.
- Two additional serial full-catalogue QML matrices both pass with zero QML
  warnings: IT/EN/ES, normal/red, Home/catalogue/profiles, real month selection,
  profile changes, equipment snapshots and 7,594 exact monthly visibility values.
  They add 36 page captures and eight transitions. Two Home screenshots from
  the second run were inspected (Italian normal and Spanish red). Known fixture
  location-message and offscreen red-icon limits remain; no native rendering
  approval follows from these screenshots.

Evidence: `build/home-performance-1.46.21/review-source-gate.log`,
`review-qml-all-1.log`, `review-qml-all-2.log` and `review-*-qml-final-all/`.
The test-only wrapper changes output destinations, not application code,
scenario timing, assertions or warning handling. Earlier evidence is retained.

## Open Follow-Ups

No finding above blocks a local Windows rebuild, but these limits remain:

1. Complete payload conversion and QML filtering/model updates still execute
   on the GUI thread. The repeated month/profile probes record maximum heartbeat
   gaps of 0.727/1.398 s and 0.665/1.257 s respectively. These are diagnostic
   timings on this PC, not a guarantee for the reporting user's hardware.
2. Cold synchronous fallback and presentation-only target replacement still
   prepare timings locally. Further changes need separate parity and lifecycle
   validation; this review does not claim a completely nonblocking Home.
3. The earlier incubation/context-destruction warning pair did not recur in
   either new run. It is not declared fixed. Native rapid-navigation and
   lower-resource-PC checks remain useful; standalone qmllint's previously
   documented startup failure was not reclassified as a pass.

The user authorized the Windows artifact rebuild after this review. Bundle
validation and preservation are recorded separately from source approval and
public publication; Linux, push, tag, ZIP publication and release are out of scope.

## Local Windows Artifact Identity And Preservation

The official `packaging/build_windows.ps1` was invoked from clean `66c4b5a`.
The build and pristine Qt/legal/runtime audit pass. The later tracked changes
are validation documentation only, not application or packaged-source changes.
Environment: Windows 11, Python 3.14.5, PyInstaller 6.22.2, hooks-contrib 2026.7,
PySide6/Qt 6.11.2. Embedded VERSION is 1.46.21.

- Bundle: `dist/NightScope`, 5,146 files, 429,395,620 bytes.
- Executable SHA-256:
  `c93006954f669e434acf51f1093823dc913d6a55681701ea1e088dd1d433b57f`.
- All 109 declared assets and five legal files match source SHA-256. All 131
  embedded application modules and the main entrypoint match compiled source,
  including the three required observing/Home performance modules. Windows
  credentials/timezone backends and native QtPositioning binding/DLL are present.
- Before replacement, the entire 1.46.18 directory was copied to
  `build/windows-dist-1.46.21-20260907/previous-dist-1.46.18`:
  5,150 files / 554,296,957 bytes, all verified by SHA-256 against the original.
  It includes the portable database, existing DB backup, preferences, location
  cache and logs. The preserved copy remains hash-identical after the build;
  seven pre-existing development runtime files also remain unchanged.
- The new bundle is intentionally pristine. Previous portable settings/data
  are preserved in that backup, not imported into the distributable directory.
  The backup contains private runtime data and must not be shipped as a release.

Build evidence and helpers are in `build/windows-dist-1.46.21-20260907/`.
Optional assetdownloader, pycparser-table, importlib_resources.trees, zlib.dll
and snappy.dll diagnostics remain in `build.log`; no application or dependency
was changed to hide them. The EXE hash above is not a ZIP digest, signature,
antivirus result, public release or Linux-artifact validation.

## Packaged Executable Validation

Backend, normal-QML and Red Night Vision QML smokes all exit 0 from an unchanged
disposable copy, using three separate fresh `NIGHTSCOPE_RUNTIME_DIR` directories.
Serial elapsed times are 29.55/24.11/22.68 s, including first-use database
initialization; they are not an observing-performance comparison. Every test
prints its explicit success marker, has empty stderr and no runtime warnings,
errors or tracebacks. All three databases pass integrity and foreign-key checks,
schema 27, nine Solar image records, zero personal images and exact field parity
for all 323 descriptions and 323 curiosities against the current source.

The copied bundle passes its own pristine audit after the smokes, demonstrating
that runtime writes stayed outside it. Only the validated temporary copy and
its three synthetic runtimes were removed. The final audit of `dist/NightScope`
also passes; the previous portable backup is retained. Logs: `packaged-smokes.log`,
`fresh-*.stdout.log`, `fresh-*.stderr.log`, `fresh-*.runtime.log`,
`final-bundle-audit.log`, `source-parity.log` and `final-preservation.log`.

This approves the scoped local Windows build, not a full native visual/provider,
photo-picker, existing-user upgrade or low-resource hardware matrix. No ZIP,
signature, antivirus scan, tag, push, remote CI check or publication was performed;
Linux artifacts and public downloads are untouched.

Post-build documentation/tooling checks pass: 49 tests in 10.43 s, the unchanged
271 Python / 36 QML / 17 operational inventory, and `git diff --check`.
