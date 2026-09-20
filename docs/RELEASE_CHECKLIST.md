# NightScope Release Checklist

Current target: `v1.47.0` (local Windows build; not published).
Current public Windows release: `v1.46.21`. Current public Linux release: `v1.43.0`.

Updated 2026-09-20. This is the checklist for the new target, not inherited
approval from an older artifact. A source commit or unit suite alone does not
approve publication. The historical 1.46.21 release used tag `f6b45e9` and the
single-extension `NightScope-v1.46.21-windows-x64.zip`; its evidence remains in
`TESTING.md` and `REVIEW_HOME_PERFORMANCE_1_46_21.md`.

## 1. Product, Documentation And Legal

- [x] Freeze scope: startup/recommendation fixes, practical windows, IMO,
  local meteor windows, COBS and reviewed layout work. No new provider/refactor.
- [x] Align VERSION, changelog, manual IT/EN/ES, README, source/legal notices
  and architecture with 1.47.0 while preserving historical records.
- [x] Explain COBS noncommercial CC BY-NC-SA 4.0 data separately from MPL code;
  preserve attribution, observer credits and modification notices. Do not bundle
  or mirror IMO publications or a COBS dataset.
- [x] Keep website download links/structured release metadata on the published
  platform versions; identify 1.47.0 only as source/local preparation.
- [ ] Publish and verify the matching audited source tag, then update
  SOURCE_CODE.md with its exact public identity before public distribution.
- [ ] Complete the desktop/mobile browser review of the revised manual.

## 2. Automated Source Validation

- [x] Run the complete 1.47.0 `tools/run_checks.py --security` gate with coverage,
  catalogue/editorial, imagery, dependency and license checks: 2,303 tests / ten
  subtests, 87% coverage; evidence in TESTING.
- [x] Compile and validate all three translation catalogues (2,224 messages each).
- [x] Run isolated backend, normal QML and Red Night Vision source smokes.
- [x] Recheck all 36 QML files: the native qmllint executable now exits 0.
  The 1.47.0 rerun recorded 849 warnings / 710 informational messages;
  context/property diagnostics are not a zero-warning approval.
- [ ] Install dependencies in a fresh environment and repeat the release gate.
  The configured, pinned development environment is not a fresh-install test.
- [ ] Produce an artifact-derived SBOM for the final release environment.

## 3. Windows Artifact And Data Safety

- [x] Build from clean `15cc17a` using `packaging/build_windows.ps1`.
- [x] Audit the pristine bundle: legal files, Qt modules, native Positioning,
  dialog/folder plugins, seeds, translations, manual, ephemeris and timezone data.
- [x] Compare embedded application code/assets and VERSION against source.
- [x] Pass backend, normal QML and red QML smokes from a disposable copy,
  with separate NIGHTSCOPE_RUNTIME_DIR paths and database integrity/FK checks.
- [x] Upgrade a consistent copy of the current development DB; its one Default
  profile and 28 tables are preserved, city/alias semantics and current editorial
  seeds verified. Four original runtime files retain their SHA-256 hashes.
- [ ] Repeat with a populated personal archive: custom equipment, assignments,
  edited built-ins, image references and observation log. The sparse copy above
  is not evidence for every populated-user scenario.
- [x] Confirm runtime files stay outside the pristine deliverable. Disposable
  copy cleanup was blocked by execution policy; private path recorded in TESTING.
- [ ] Test closed-app backup/restore and document any retained private QA copy.
- [x] Portable Windows use requires a writable extracted directory; a read-only
  install path is not the documented deployment.
- [ ] Repeat native photo selection, save/alias/cancel/red/reset and restart
  without the original image on the new artifact.
- [x] Record artifact file count, size, EXE SHA-256 and exact source/environment.
- [ ] Immediately before archiving, repeat the pristine audit; exclude databases,
  backups, caches, logs, preferences, credentials and personal images.
- [ ] Scan the artifact with the chosen security tooling.
- [x] Current policy: unsigned portable executable, no installer or automatic updater.
  Do not claim Authenticode signing or bypass operating-system warnings.
- [ ] Create the final ZIP, verify its SHA-256 and test extraction/first launch.
  An EXE hash is not the ZIP checksum.

## 4. Native Visual And Provider Matrix

Repeat on the packaged application in IT/EN/ES, normal/red modes and supported
minimum/normal desktop sizes. Scoped earlier matrices in TESTING remain useful
evidence but do not silently check off this complete manual matrix.

- [ ] No location; valid location without optional providers; naked-eye and
  multi-instrument profiles; long text, missing fields and empty states.
- [ ] Home, Calendar, Weather, all equipment pages, Catalogue, both detail pages,
  Providers, Profiles, Location and Observation log; sidebar fit and help/manual.
- [ ] Red-mode icons, controls, popups, focus/hover, Canvas and photographs;
  representative pixel-channel audit.
- [ ] Open-Meteo fresh/stale/offline; Windows location allowed/denied/timeout;
  explicit approximate IP fallback; CelesTrak visible/no-visible passes.
- [ ] JPL and COBS valid/empty/stale/offline; correction versus JPL fallback
  explained without implying measured accuracy from an insufficient sample.
- [ ] IMO download/import/year rollover/failure; preserve the old edition until
  the new one validates; local meteor windows with partial/no weather.
- [ ] Earthdata credentials/authorization/removal, positive and legitimate
  no-data VIIRS/AOD; OpenAQ key lifecycle and valid/no-data/freshness paths.
- [ ] Ensure inspected logs contain no credential secrets or personal coordinates.
  Use test credentials only; never commit them.

## 5. Publication Boundary

- [ ] Resolve any newly found blocking issue and review known limitations.
- [ ] Complete the remaining artifact/manual gates, or explicitly record
  release-owner acceptance of each uncompleted gate.
- [ ] Ensure the tag identifies the audited source, the final archive/hash are
  recorded and source-availability notices match; only then publish.
- [ ] Update website public download links/metadata only after the actual
  Windows release asset exists. Do not imply publication from a local build.

No push, tag, GitHub publication or Linux build is part of this preparation.
Linux 1.43.0 stays public; a future Linux artifact needs its own Debian 12 build,
native-component/source/license inventory, Debian/Ubuntu Wayland/XCB smokes,
archive/hash/extraction checks and explicit approval.
