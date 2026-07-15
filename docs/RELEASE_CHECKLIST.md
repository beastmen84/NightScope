# NightScope Release Checklist

This checklist is the approval gate for the first public NightScope build. A
source commit or a passing unit suite alone is not a release approval.

## 1. Product And Legal

- [x] Select and add the project `LICENSE` file.
- [x] Create a consolidated third-party notice from runtime dependencies,
  packaged data, and image metadata.
- [x] Confirm GeoNames CC BY 4.0, timezone-boundary ODbL 1.0, survey image, and
  NASA/JPL attribution is present where required.
- [x] Record the public NightScope source URL and exact corresponding commit for
  the distributed MPL executable: tag `v1.33.2`, commit
  `9c17204f718223e83183367e9ccea078805b5a00`.
- [ ] Confirm version number, changelog, manual revision, and About/build
  metadata agree.
- [ ] Freeze the release scope; defer unrelated refactors.

## 2. Automated Validation

- [ ] Install runtime and developer requirements in a clean virtual environment.
- [ ] Run `python tools/run_checks.py --security`.
- [ ] Run all translation extraction, compilation, and catalogue tests.
- [ ] Run `qmllint` over all packaged QML files.
- [ ] Run deep-sky and Solar System asset checks.
- [ ] Record exact Python, dependency, test, warning, and translation counts.
- [ ] Produce a frozen dependency list or SBOM for the release environment.

## 3. Visual Matrix

Run every row in both Italian and English at the supported minimum and normal
desktop sizes.

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

- [ ] Start from a new empty runtime directory.
- [ ] Upgrade a copy of a representative current development database.
- [ ] Verify profiles, user-edited built-ins, custom equipment, provider state,
  cached location, and observation log survive.
- [ ] Confirm database sidecars and JSON files are written only to the intended
  runtime directory.
- [ ] Test backup and restore with the application closed.
- [ ] Confirm a read-only install location produces a clear deployment decision
  or is explicitly excluded from supported use.

## 6. Windows Artifact

- [ ] Build from a clean checkout with `packaging/build_windows.ps1`.
- [x] Confirm the source commit and build environment are recorded.
- [x] Run backend and QML smoke tests against the packaged executable.
- [x] Confirm the bundle-root legal files and Qt module audit pass.
- [ ] Verify bundled QML, translations, manual, data seeds, images, ephemeris,
  timezone polygons, and credential backend.
- [ ] Run the complete visual and provider matrices on the packaged build, not
  only from source. Test a copy and preserve a pristine release bundle.
- [x] Immediately before archiving, rerun `tools/audit_qt_bundle.py` on the
  pristine bundle and confirm that no runtime database, backup, cache, settings,
  or logs are present.
- [ ] Scan the artifact with the chosen security tooling.
- [ ] Sign the executable or document the explicit initial-release policy.
- [x] Publish a SHA-256 hash with the artifact.
- [ ] Test extraction and first launch from a normal writable user directory.

## 7. Release Approval

- [ ] No unresolved severity-1 or severity-2 defect.
- [ ] Known limitations match README and manual.
- [ ] Changelog contains only verified results.
- [x] Git worktree is clean and release tag points to the audited commit.
- [x] Final artifact identity and hash are recorded in the release notes.
