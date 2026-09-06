# NightScope Release Checklist

This checklist is the approval gate for public NightScope builds. A source
commit or a passing unit suite alone is not a release approval.

Current target: `v1.46.18` (local Windows test bundle validated; no public tag).
Current public Windows release: `v1.46.13`. Current public Linux release: `v1.43.0`.
The user published `v1.46.13` on 2026-09-06 for Windows only. GitHub exposes one
`NightScope-v1.46.13-windows-x64.zip` asset and tag `v1.46.13` at `b34ec4a`.
The preceding local Windows build was validated from `be30cda`; the tag adds
only validation documentation. The uploaded ZIP was not downloaded or
re-audited during this documentation update. Unchecked gates remain open:
publication alone does not provide missing evidence or approve a Linux build.
Unless explicitly scoped to Windows, gates still apply separately to each
new platform artifact. Historical Windows/Linux evidence remains dated.

## 1. Product And Legal

- [x] Select and add the project `LICENSE` file.
- [x] Create a consolidated third-party notice from runtime dependencies,
  packaged data, and image metadata.
- [x] Confirm GeoNames CC BY 4.0, MPC observatory, timezone-boundary ODbL 1.0,
  generated-art provenance, and NASA/JPL attribution is present where required.
- [ ] Create and verify the public `v1.46.18` source tag referenced by the
  portable bundles and `SOURCE_CODE.md`.
- [x] Confirm source version, changelog, source-availability notices, and
  About/build metadata agree on `1.46.18`.
- [x] Freeze the release scope; defer unrelated refactors.

## 2. Automated Validation

- [ ] Install runtime and developer requirements in a clean virtual environment.
- [x] Keep the Windows release constraints, Python patch, and committed
  third-party license inventory exactly aligned.
- [x] Run `python tools/run_checks.py --security` against source 1.46.18:
  1,515 tests / ten subtests, 86% coverage; see TESTING. No artifact approval.
- [x] Run all translation compilation and catalogue tests.
- [x] Run both normal and Red Night Vision QML smoke tests from source 1.46.18
  in disposable runtimes; backend smoke also passes.
- [x] Run `qmllint` over all packaged QML source files (35).
- [x] Run category artwork and Solar System asset checks (25 local JPEGs).
- [x] Record exact Python, dependency, test, warning, and translation counts
  in `docs/TESTING.md`; non-fatal QML diagnostics remain tracked debt.
- [ ] Produce an artifact-derived SBOM for the final release environment.

## 3. Visual Matrix

Run every row in every supported language (currently Italian, English, and
Spanish) at the supported minimum and normal desktop sizes.

Record findings and their resolution status in
[`VISUAL_CHECKLIST.md`](VISUAL_CHECKLIST.md).

- [ ] First start with no location.
- [ ] Valid location, no optional provider, Default profile in Naked eye mode.
- [ ] Valid location and a multi-instrument profile.
- [ ] Earthdata configured, authorized, verified, and returning data.
- [ ] Earthdata verified with legitimate no-data AOD/VIIRS results.
- [ ] OpenAQ verified with data and with legitimate no-data results.
- [ ] Stale weather/VIIRS cache and offline behavior.
- [ ] Home, Calendar, Weather, every Equipment catalogue, Object catalogue,
  object detail, event detail, Providers, Profiles, Location, and Observation
  log.
- [ ] Long names, long event titles, missing optional fields, and empty states.
- [ ] Sidebar fits without unnecessary scrolling at minimum supported height.
- [ ] Repeat every application page in Red Night Vision; confirm icons,
  controls, popups, focus, hover, Canvas drawings and empty states contain no
  bright white, green, cyan or blue output.
- [ ] Confirm object photographs, attributions and Home plan thumbnails are
  absent and not loaded in Red Night Vision.
- [ ] Record a pixel-channel audit for representative normal and red renders.
- [ ] Manual opens from the help button in the current language and works at
  desktop/mobile widths.

## 4. Live Provider Matrix

Use test accounts and coordinates that exercise positive and negative coverage.
Do not commit credentials or exact personal locations.

- [ ] Open-Meteo forecast and cache fallback.
- [ ] Windows precise location, denied permission, and timeout paths.
- [ ] Explicit IP fallback.
- [ ] CelesTrak refresh and visible/no-visible ISS pass results.
- [ ] JPL SBDB comet refresh and cached/offline behavior.
- [ ] Earthdata credential save, LAADS authorization, test, removal, VIIRS, and
  MAIAC AOD quality/no-data paths.
- [ ] OpenAQ key save, test, removal, measurement, distance, freshness, and
  no-data paths.
- [ ] Confirm logs contain no credential secrets, usernames, API keys, or exact
  coordinates.

## 5. Data And Upgrade Safety

- [x] Source image-lifecycle fixtures: schema upgrade, WAL-consistent snapshot,
  old-backup restore after photo replacement/reset, personal profile/prose
  preservation, relocated file URLs and failed writes; see `docs/TESTING.md`.
- [x] Windows 1.46.18 packaged backend/normal/red smokes start with separate
  empty runtimes; this does not approve an existing-user upgrade.
- [ ] Upgrade a copy of a representative current development database.
- [ ] Verify profiles, user-edited built-ins, custom equipment, provider state,
  cached location, and observation log survive.
- [ ] Confirm database sidecars and JSON files are written only to the intended
  runtime directory.
- [ ] Test backup and restore with the application closed.
- [ ] Confirm a read-only install location produces a clear deployment decision
  or is explicitly excluded from supported use.

## 6. Windows Artifact

The local Windows dist was rebuilt on 2026-09-06 from clean `971292d`, version
`1.46.18`; it includes the review's runtime/editorial corrections after the
three image steps. Translation-maintenance tooling remains source-only.
Artifact identity and scoped validation are in `docs/TESTING.md` and the handoff.
The checks below approve only their stated scope, not publication or the
remaining complete visual/provider matrix. The user removed the previous dist
without backup; the disposable test copy and three fresh runtimes were removed.

- [x] Build from a clean checkout with `packaging/build_windows.ps1`.
- [x] Confirm the source commit and build environment are recorded.
- [x] Run backend and QML smoke tests against the packaged executable.
- [x] Confirm the bundle-root legal files and Qt module audit pass.
- [x] Confirm Qt Quick Dialogs and folder-list plugins are present, with no
  user_images directory at any depth.
- [ ] Repeat native photo selection, fallback open/accept, save/alias/cancel/
  red/reset and restart-without-original on 1.46.18. The passing 1.46.13
  packaged workflow remains historical evidence, not a repeated current gate.
- [x] Verify bundled QML, translations, manual, data seeds, images, ephemeris,
  timezone polygons, and credential backend.
- [x] Rebuild with the current review corrections and repeat artifact validation
  before publishing a bundle from the updated source.
- [ ] Run the complete visual and provider matrices on the packaged build, not
  only from source. Test a copy and preserve a pristine release bundle.
- [ ] Immediately before archiving, rerun `tools/audit_qt_bundle.py` on the
  pristine bundle and confirm that no runtime database, backup, cache, settings,
  or logs are present.
- [ ] Scan the artifact with the chosen security tooling.
- [ ] Sign the executable or document the explicit initial-release policy.
- [ ] Publish a SHA-256 hash with the artifact.
- [ ] Test extraction and first launch from a normal writable user directory.

## 7. Linux Artifact

- [ ] Build through the declared Debian 12 x86-64/glibc 2.36 container with
  `packaging/build_linux_debian12.sh`.
- [ ] Generate the environment-specific Python license archive.
- [ ] Inventory every copied native ELF file with binary/source versions,
  bundle SHA-256, notice path and exact Debian Sources or CPython source URL.
- [ ] Bundle every source-component copyright notice and Debian common-license
  text referenced by the generated inventory.
- [ ] Verify every unique exact-version source URL returns HTTP success.
- [ ] Reject unmanifested/stale native files, changed hashes, missing notices,
  missing common licenses, unsupported Qt plugins and GPL-only Qt modules.
- [ ] Run backend and normal/red QML smoke tests in Debian 12 and Debian 13;
  run Wayland normal/red and XCB QML smoke tests on the Ubuntu host.
- [ ] Confirm GIO modules remain isolated so newer-host GVFS plugins are not
  loaded against the bundled Debian 12 GLib.
- [ ] Create the deterministic
  `NightScope-v1.46.13-debian-12-x64.tar.gz` and adjacent SHA-256 file.
- [ ] Verify checksum, extraction, audit and smoke tests from the final archive.
- [ ] Publish the tarball and checksum together with the matching Windows ZIP
  in the public `v1.46.13` GitHub release when both platforms are approved.
  Update discovery checks actual compatible assets; publication can remain
  platform-specific and must not imply validation of the other platform.

## 8. Release Approval

- [x] No unresolved severity-1 or severity-2 defect.
- [x] Known limitations match README and manual.
- [x] Changelog contains only verified results.
- [ ] Git worktree is clean and release tag points to the audited commit.
- [ ] Final artifact identity and hash are recorded in the release notes.
