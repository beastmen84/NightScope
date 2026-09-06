# NightScope - Next Chat Handoff

Updated: 2026-09-06

## Current State

- Source `1.46.17` adds a bounded, best-seen-only hemisphere clarification for
  87 existing objects; no enrichment or coverage increase. Its manifest
  records IT/EN/ES review and five visual samples. See the review-corrections
  document for remaining steps and final gate status.

- Source `1.46.16` adds a bounded, best-seen-only hemisphere clarification for
  57 existing objects; no enrichment or coverage increase. Its manifest
  records IT/EN/ES review and five visual samples. See the review-corrections
  document for remaining steps and final gate status.

- Source `1.46.15` adds a bounded, best-seen-only hemisphere clarification for
  75 existing objects; no enrichment or coverage increase. Its manifest
  records IT/EN/ES review and five visual samples. See the review-corrections
  document for remaining steps and final gate status.

- Source version: `1.46.17`; all three image-redesign source steps are complete.
- The user authorized the 1.45.21–1.46.13 review corrections. This first source
  step protects existing editorial overlays during maintenance, fixes ended
  useful-window status at morning twilight and themes the pre-QML splash/error
  widgets from the persisted red preference before painting. Editorial season
  clarification and NGC 1266's scientific qualifier are the next bounded steps.
  See `docs/REVIEW_CORRECTIONS_1_46.md`. Public versions and dist remain unchanged.
- Intermediate 1.46.14 validation: all runtime cases in the 1,481-test / ten
  subtest full fast run pass; two version-documentation assertions were fixed
  and all 49 tooling tests then passed. All three isolated source smokes pass.
  Native/offscreen startup progress and error widgets pass IT/EN/ES pixel
  checks. Read TESTING for the preliminary non-isolated development smoke;
  the final fresh security/coverage gate follows the editorial steps.
- Public release update: on 2026-09-06 the user published `v1.46.13` for
  Windows only. Release metadata, the public tag and the exact asset name
  were checked through GitHub. README, manual, current release records and
  EN/IT/ES website sources now distinguish Windows 1.46.13 from Linux 1.43.0.
  This documentation-only follow-up keeps VERSION and application code intact;
  it does not rebuild or replace the published ZIP or local dist. Website
  sources still use the existing GitHub Pages workflow; no hosting migration,
  push or remote-run wait is performed here.
- Documentation/site validation: 49 developer-tooling tests pass in 8.71 s,
  with Ruff clean and the 259 Python / 35 QML / 17 operational-file inventory
  unchanged. The three new cases cover per-language public links and manual
  revision parity. No full runtime suite was repeated for this non-runtime
  change. Logs: `build/release-docs-1.46.13-20260906/`. The source manual and
  notices are updated; copies already inside the published ZIP/dist are not
  rewritten. Push the documentation commit to update the GitHub Pages site.
- Step 1 is `ce83550` (1.46.11); step 2 is `8357308` (1.46.12). Step 3 has its
  separate local 1.46.13 commit: consistent atomic SQLite snapshots including
  WAL, managed-image relocation before its legacy DB, Home corrupt-thumbnail
  fallback, stricter private-image/file-picker packaging checks and lifecycle
  regressions. There is no new backup GUI: the existing DB snapshot and manual
  full-runtime copy/restore are documented in `docs/PERSONAL_IMAGES.md` and the
  IT/EN/ES manual. Keep DB and user_images together; old managed files remain
  after reset/replacement so earlier backups can recover them.
- Final full security gate: 1,452 tests plus 10 subtests in 225.57 s, 86%
  coverage (18,211 / 21,085 lines), backend/normal/red source smoke tests.
  259 Python, 35 QML, 17 operational files; 2,088 compiled finished messages
  per language; 35 QML linted with known non-fatal diagnostics. Real Home QML:
  21 personal-image states, 48 category states and three red pixel audits.
  See TESTING/VISUAL_CHECKLIST and `build/personal-imagery-1.46.13/` for evidence
  and the isolated serial shutdown-GC warning, not reproduced in the full gate.
- The user subsequently requested the Windows rebuild. Local `dist/NightScope`
  is now `1.46.13`, built from clean `be30cda` on 2026-09-06. The official
  build and Qt/legal/runtime audit pass, with all 108 declared source assets
  and five legal files matching by SHA-256. Packaged backend/normal/red QML
  smokes pass in disposable runtimes. Packaged native/fallback image workflows
  and restart without the original input also pass. No old dist data or backup
  was retained, as explicitly requested. See the Windows validation below.
- Current 1.46.12 implementation: separate PersonalObjectImages table (schema
  27), canonical-ID association, immutable JPEG/thumbnail files in user_images,
  bounded JPEG/PNG normalization through QImageReader, asynchronous cancellable
  preview manager, translated detail image editor, immediate Home/detail update,
  fallback for missing/undecodable personal images, guarded red mode and Qt
  FileDialog packaging dependencies. The original files are never changed.
  Complete security gate: 1,429 tests plus 10 subtests, 86% coverage
  (18,119 / 20,981 lines), all three source smoke tests. All 35 QML files lint;
  IT/EN/ES have 2,088 compiled finished messages each. Real QML: 36 editor
  scenes, repeated through the file-picker fallback, and six red pixel audits.
  Only the six deliberately corrupted-image decoder warnings occur per pass.
  Two existing Planner tests now freeze their clock before the target's useful
  interval, preserving assertions; no production astronomy change. Evidence:
  `build/personal-imagery-1.46.12/`, `docs/PERSONAL_IMAGES.md`, TESTING/visual docs.
- **Image redesign, step 1:** all deep-sky catalogues now use a consistent
  16-category illustration family, independent of editorial completion.
  Only the nine Solar System photographs are retained, byte-for-byte.
  Shared pure resolver, canonical types, neutral unknown-type fallback,
  explicit IT/EN/ES artwork labels and asynchronous visible-detail loading
  are implemented. Red Night Vision keeps image sources empty.
- The 16 built-in-tool illustrations were normalized with explicitly approved
  Python resizing/compression to RGB JPEG, 512 x 512, without cropping.
  Final assets are in `astro_viewer/resources/images/categories/` and total
  614,168 bytes. All 219 tracked deep-sky photos (15,235,688 bytes) and their
  obsolete downloader are removed, recoverable through Git history. The
  asset saving is 14,621,520 bytes; no compressed artifact was measured.
  Prompts and original/final SHA-256 identities are in
  `docs/IMAGE_GENERATION_PROMPTS.md` and `docs/IMAGE_ASSET_MANIFEST.json`.
  Original PNG copies remain in ignored `build/object-imagery-1.46.11/originals/`
  and are not shipped.
- Schema 26 retires only the exact old identities with matching shipped paths
  and licenses; it preserves custom paths/licenses and catalogue-prefix lookalikes.
  The distributed image seed has only nine Solar records. A permanent offline
  image gate verifies all 25 JPEGs, the category mapping, manifest hashes,
  nonblank/normalized content and absence of retired photos.
- Targeted checks pass: 59 image regressions, all 34 QML files linted (existing
  non-fatal diagnostics), 2,065 compiled finished messages per IT/EN/ES pack,
  24 real-QML detail scenes, 48 Home thumbnail states and six red pixel-channel
  audits. The full security/coverage gate passes: 1,407 tests and 10 subtests,
  86% coverage (17,838 / 20,672 lines), all three source smoke checks. A disposable
  schema-25 database with all 231 historical image rows upgrades to 26 while
  preserving a custom image, custom editorial text and all 33 other tables;
  SQLite integrity/foreign-key checks pass. See `docs/TESTING.md` for the final
  full source gate; logs and disposable QA helpers are under
  `build/object-imagery-1.46.11/`.
- **Next:** source image work is concluded; the new local 1.46.13 dist includes
  the Moon polish and all three image-management steps. The user has now
  published a Windows ZIP for this version; publication is separate from the
  remaining complete release-matrix approval. Native dialogs and workflows
  have evidence in the current Windows validation section below.
  `docs/OBJECT_IMAGERY_ROADMAP.md` records all three completed source steps.
  No editorial or astronomical formula changed in the source image steps.
  The subsequent artifact step changes only dist and validation records;
  there is no push, tag, publication or remote GitHub-run wait.
- Before the image redesign, the user-requested visual polish in `1892652`
  removed the clipped outer halo
  from the eight Moon-cycle markers. The canvas exterior is transparent;
  the dark disc, projected terminator, outline and phase calculations are
  unchanged. The unused theme glow color was removed. That source-only change
  kept `1.46.10`; the previous `ae34df5` bundle did not include it, but the
  current `be30cda` Windows rebuild does.
- The user authorized correcting the whole-project audit's findings. A1-A8/N1
  are implemented in this source step; read
  `docs/ASTRONOMICAL_CORRECTIONS_1_46_10.md` for contracts and verification.
  The original evidence remains in `docs/ASTRONOMICAL_CODE_AUDIT_1_46_9.md`
  (baseline `b567a2b`, documentation commit `e1705c4`). Editorial content and
  heuristic scoring weights remain untouched. Astronomy now uses positive
  absolute useful intervals, UTC elapsed time, conservative target-aware
  twilight, explicit unavailable ephemerides and valid-only provider rows.
- Current public Windows release: `v1.46.13`, published 2026-09-06 at
  13:27:16 UTC. The public tag points to
  `b34ec4a85783fde74bd384565aa6e3f0638e00eb`; its changes after the validated
  build source `be30cda` are documentation only. The release contains exactly
  `NightScope-v1.46.13-windows-x64.zip` (222,215,508 bytes), no Linux package
  or adjacent checksum file. GitHub reports ZIP SHA-256
  `c8fed8d0ddc7c98a70008033da8732b9c3322847f0a012db417a7360238dacf2`.
  This is server-reported metadata, not a newly downloaded/re-audited ZIP;
  do not confuse it with the local executable hash in the validation below.
- Current public Linux release: `v1.43.0`, from source commit
  `26dfaf49df8f9b8e73e84f406396f406170400b2`; its GitHub release contains the
  Debian 12 x86-64 tarball and adjacent checksum.
- Source tag/release `v1.46.13` is public. Source readiness, local bundle
  validation and the user's subsequent publication remain distinct records;
  unchecked release/visual/provider gates must not be retroactively approved.
- The user subsequently requested a new local Windows `dist/NightScope` for
  manual testing. It was rebuilt as `1.46.10` from clean source `ae34df5` on
  2026-09-05. Bundle audit, source-asset hashes, and packaged backend/normal-QML/
  Red Night Vision smoke tests pass. It was pristine after build validation;
  subsequent user launches created runtime data. That previous dist and its
  local DB/settings/caches/logs were removed by the 1.46.13 rebuild, without
  preservation or a new backup. Linux was not rebuilt.
- For this rebuild the user explicitly rejected retaining the previous dist
  or creating backups, and requested deleting earlier distribution backups.
  Automatic deletion was blocked by the tool policy; after the user confirmed
  manual deletion, the old dist and
  `dist/_backups/NightScope-1.45.21-before-1.46.9-20260905-142734` were confirmed
  absent before building. No new backup was made. Do not describe that old
  backup as still available. The older 1.46.9 temporary test copy is a separate
  cleanup item recorded below; this run's new temporary copy was removed.
- Test-setup tuning was completed on `1.46.8` (`fa955d0`): setup copies a
  private database from a fresh, per-worker session template. Real bootstrap/migration/recovery
  and astronomy/controller checks remain in place; no runtime code or
  editorial data changed in that tuning commit; those checks remain in place.
- Nine editorial batches are accepted: three enrich 95 NGC-only targets
  (75 galaxies and 20 planetary nebulae); six remediate declared fields across
  197 distinct baseline objects. The new `1.46.9` batch leaves previous prose
  untouched and adds complete IT/EN/ES records for 20 planetaries. Coverage is
  323 complete objects (228 baseline plus 95 NGC-only), with 7,271 NGC-only
  targets remaining.
- A retrospective quality screen confirms the 50 entries added in `1.46.1`
  remain specific and useful. The `1.46.7` zero-debt result only measured whole
  paragraphs. A subsequent sentence-level check found 133 normalized shared
  sentence families across IT/EN/ES, affecting 85 objects. Source `1.46.8`
  corrects these and the remaining measurement-only description tails; both
  screens now report zero. This is not a blanket factual certification of
  untouched fields or a claim that no individual sentence can be improved.
- The multilingual static website lives under `website/`, and
  `.github/workflows/pages.yml` uploads only that directory. GitHub Pages is
  enabled with the `workflow` source, HTTPS is enforced, and the public homepage
  at `https://beastmen84.github.io/NightScope/` returned HTTP 200 after the first
  successful deployment.
- Historical handoff detail through `1.45.6` is preserved in
  `docs/archive/NEXT_CHAT_HANDOFF_1.45.6.md`.

## Architectural Series

| Version | Commit | Outcome |
| --- | --- | --- |
| 1.45.0 | `6e4e2e9` | Introduced the application composition root and injected resolved dependencies into the controller. |
| 1.45.1 | `771ebcd` | Extracted synchronous catalogue recommendation orchestration and immutable worker snapshots. |
| 1.45.2 | `f5285fd` | Extracted observing, weather, session, and night-time presentation logic. |
| 1.45.3 | `2328be9` | Extracted catalogue records, search/filter projections, observability, and detail construction. |
| 1.45.4 | `6000599` | Extracted equipment input, catalogue, profile-inventory, and presentation workflows. |
| 1.45.5 | `18ec214` | Removed all detected production import cycles and introduced lower-level DTO/protocol boundaries. |
| 1.45.6 | `60a964f` | Added CI, strict warning policy, incremental Bandit review, and standard architecture gates. |
| 1.45.7 | `1fec5df` | Consolidates architecture/testing documentation and closes the final structural audit. |
| 1.45.8 | `cef54b3` | Defines the code-documentation contract and documents application/model boundaries. |
| 1.45.9 | `06b514e` | Documents every domain, provider, presentation, equipment, catalogue, and localization service. |
| 1.45.10 | `35972b7` | Documents persistence, astronomy, Qt view models, and runtime composition boundaries. |
| 1.45.11 | `6719979` | Documents the responsibility and boundary contract of every QML file. |
| 1.45.12 | `8f4a9f2` | Documents maintenance, packaging, CI, configuration, schema, and manual files. |
| 1.45.13 | `0caf68f` | Documents every test/support module and enforces the complete source-documentation inventory. |
| 1.45.14 | `de25eab` | Updates the validated development and portable-packaging toolchain without changing runtime behavior. |
| 1.45.15 | `8c11175` | Updates the validated Qt and astronomy runtime baseline while preserving application contracts. |
| 1.45.16 | `a8584a8` | Updates and constrains the Earthdata transport family as one tested resolver unit. |
| 1.45.17 | `98b7b67` | Extracts concrete location adapters behind an explicit composition-root bundle while retaining compatibility imports. |
| 1.45.18 | `d18e7d9` | Extracts controller-facing location commands into a framework-independent workflow with explicit inputs and outcomes. |
| 1.45.19 | `62f6383` | Separates installed profile inventory from global equipment catalogues without changing the SQLite schema or identifiers. |
| 1.45.20 | `4cf60a1` | Pins the Windows Python/dependency closure; its remote run exposed path-dependent bytecode in the legal archive. |
| 1.45.21 | `d06300b` | Excludes code and bytecode from license notices so clean Windows environments generate an identical archive. |
| 1.45.22 | `d99e03c` | Shows localized startup progress on every launch while preserving fixed English copy for a genuinely new runtime. |
| 1.46.0 | `93fba5f` | Establishes the audited multilingual editorial pipeline without adding NGC prose. |
| 1.46.1 | `8f5d20c` | Accepts the first 50-object, source-backed, three-language NGC editorial batch. |
| 1.46.2 | `7e16c0e` | Audits historical prose debt and accepts a second, deliberately smaller 25-object multilingual batch. |
| 1.46.3 | `5f4a252` | Adds field-scoped baseline remediation and replaces generic prose for 17 reviewed galaxies. |
| 1.46.4 | `f145b4a` | Replaces formulaic guidance for 48 baseline open clusters and rewrites ten duplicated descriptions. |
| 1.46.5 | `8a2de9a` | Replaces formulaic guidance for 41 baseline globular clusters and rewrites six duplicated descriptions. |
| 1.46.6 | `2d2d1b5` | Replaces formulaic guidance for 20 baseline nebulae and planetary nebulae. |
| 1.46.7 | `d9f11d5` | Replaces the final formulaic galaxy guidance and four duplicated descriptions. |
| 1.46.8 | `fa955d0` (final tuning) | Corrects residual prose and the sentence audit; then speeds up isolated test DB setup without dropping checks. |
| 1.46.9 | `42b0cb2` | Adds 20 source-backed planetary nebulae in IT/EN/ES, with explicit visual and scientific limits. |

## Resulting Architecture

`astro_viewer.main` resolves runtime paths and builds
`AppControllerDependencies`. `AppController` remains the Qt boundary and owns
signals, slots, asynchronous scheduling, stale-result rejection, and publication
of runtime state. Framework-independent application workflows and presentation
services now prepare recommendation, catalogue, observing/weather, and equipment
read models. The composition root also builds the concrete location-adapter
bundle; `LocationService` owns provider selection, fallback and result
normalization. `LocationCommandWorkflow` owns search, selection, validation,
startup fallback and recent-location policy while the controller retains Qt
lifecycle and publication. `EquipmentProfileRepository` owns profile lifecycle
and assignments independently from global catalogue CRUD; the legacy repository
surface remains compatible and forced removals still share one SQLite
transaction. Repositories own SQLite transactions and models carry typed data.

The Windows source job uses Python 3.14.5 plus an exact 62-component constraints
file that is mechanically matched to `THIRD_PARTY_LICENSES.txt`. Linux testing
and the separate Python 3.14 dependency audit remain floating compatibility
signals rather than release-record environments.

License collection accepts arbitrary notice filenames only below the standard
`.dist-info/licenses` directory and excludes Python source, bytecode and cache
directories. The regenerated archive is identical between the project venv and
a clean Windows environment despite their different absolute paths.

The normal GUI path now installs the saved language and presents one startup
splash before database bootstrap, service composition and QML loading. A new
runtime with neither database nor preferences retains the English first-use
copy; existing users see routine progress in Italian, English or Spanish. The
splash closes after the first QML frame, records completion without replacing
other preferences, and logs phase timings. Headless smoke paths are unchanged.

The production graph is acyclic. The architecture gate also prevents models,
database, astronomy, and service modules from importing the controller or the
application composition layer. Compatibility wrappers remain where existing
tests or integrations construct the controller directly.

The detailed assessment is in `docs/ARCHITECTURE_REVIEW_1_45.md`. The concise
verdict is that the codebase is robust, well tested, and materially better
organized than `1.44.0`, but not uniformly modular: `AppController`, the NASA
provider, equipment repository/bootstrap, the Skyfield engine, and the largest
QML pages remain concentrated maintenance areas.

## Validation

The subsequent lunar-marker polish, still source `1.46.10`, passed the full
coverage/security gate: 1,348 tests and 10 subtests in 182.32 s for pytest,
86% coverage (17,799 / 20,633 lines), all static/data/security checks and
backend/normal-QML/red-QML smokes. All 34 QML files pass `qmllint` with existing
non-fatal diagnostics. The phase regression now covers 24 angle/size cases
without relaxing its geometry assertions. Real Canvas pixel checks and visual
review confirm transparent exteriors and opaque discs at three sizes across
normal/red/normal, with an identical restored normal frame. Evidence is in
`build/moon-polish-1.46.10/`; `docs/TESTING.md` records the precise scope.
The dist from `ae34df5` was not changed or rebuilt, and no GitHub run was awaited.

The original corrected `1.46.10` complete coverage/security source gate passed on
2026-09-05: 1,332 tests and 10 subtests in 223.57 s for pytest, 86% application
coverage (17,799 / 20,633 lines). All static, architecture, reviewed-security,
dependency, license and catalogue gates pass; backend and normal/red QML smoke
tests pass with disposable runtimes. Inventory is 251 Python / 34 QML /
17 operational files; the existing Bandit baseline remains 0 high / 34 medium /
14 low and `pip-audit` reports no known dependency vulnerabilities. The
correction report records the regression boundaries, independent numerical
probes, UI verification and remaining approximation limits. No bundled runtime
was changed, and no remote GitHub run was awaited.
All 34 QML files pass `qmllint` with non-fatal diagnostics retained. All three
Qt packs contain 2,064 compiled finished messages. Targeted normal/red lunar
renders and six IT/EN/ES degraded-ephemeris Home/Calendar scenes were reviewed;
this is not a new complete release visual/provider matrix.

### Historical 1.46.9 And Earlier Validation

The final local `1.46.9` coverage/security source gate passed on 2026-09-05 on
Windows/Python 3.14.5:

- 1,251 tests and 10 subtests in 310.46 seconds, with 86% aggregate application
  coverage; the editorial audit passed without warnings and reports zero
  historical paragraph families and zero shared narrative sentence families
  across IT/EN/ES;
- validated toolchain: pip 26.2.1, Ruff 0.16.5, coverage 7.16.0, PyInstaller
  6.22.2, and `pyinstaller-hooks-contrib` 2026.7;
- validated UI/astronomy runtime: PySide6/Qt/shiboken6 6.11.2, Skyfield 1.55,
  Astropy 8.0.1, astropy-IERS-data `0.2026.8.31.0.57.9`, and NumPy 2.5.2;
- validated Earthdata runtime: earthaccess 0.18.0, s3fs/fsspec 2026.7.0,
  aiobotocore 3.9.0, and maximum compatible botocore 1.43.56;
- complete documentation inventory at the coverage/security gate: 250 Python,
  34 QML, and 17 operational files;
- Ruff, compilation, license archive, MPC/OpenNGC snapshot checks, and the
  network-free editorial baseline/manifest/translation/provenance audit;
- 0 import cycles and 0 protected-layer violations;
- Bandit baseline unchanged: 0 high, 34 medium, 14 low reviewed findings;
- `pip check`; the in-gate `pip-audit` found no known vulnerabilities;
- backend, normal QML, and Red Night Vision smoke tests;
- separate `1.46.2` batch evidence: 50 distinct source URLs reached successfully
  and 36 Object Detail scenes reviewed across six objects, IT/EN/ES and
  normal/red;
- separate `1.46.3` remediation evidence: 17 direct NASA URLs reached
  successfully and 84 final Object Detail scenes reviewed across seven objects,
  IT/EN/ES, normal/red, and both observing-note and lower-card positions;
- separate `1.46.4` remediation evidence: 48 distinct URLs reached successfully
  and 108 final Object Detail scenes reviewed across nine objects, IT/EN/ES,
  normal/red, and both observing-note and lower-card positions;
- separate `1.46.5` remediation evidence: 41 direct NASA URLs reached
  successfully and 96 final Object Detail scenes reviewed across eight objects,
  IT/EN/ES, normal/red, and both observing-note and lower-card positions;
- separate `1.46.6` remediation evidence: 20 distinct object-specific URLs
  reached successfully and 84 final Object Detail scenes reviewed across seven
  objects, IT/EN/ES, normal/red, and both observing-note and lower-card positions;
- separate `1.46.7` remediation evidence: 50 distinct NASA Hubble URLs reached
  successfully for 51 objects and 120 final Object Detail scenes reviewed
  across ten objects, IT/EN/ES, normal/red, and both observing-note and
  lower-card positions;
- separate `1.46.8` correction evidence: 101 distinct manifest URLs reached
  successfully and 72 final Object Detail scenes reviewed across twelve
  objects, IT/EN/ES, normal/red, at the lower description/curiosity position;
  all revised text remained complete and Red Night Vision monochromatic;
- the earlier PySide6 6.11.2 `qmllint`, isolated first-use/saved-Spanish launches,
  and native Windows splash renders from `1.45.22` remain the latest dedicated
  startup evidence; no QML source changed from `1.46.1` through `1.46.9`;
- separate `1.46.9` enrichment evidence: 26 distinct manifest URLs and 72
  final upper/lower Object Detail scenes passed review. Four added test cases
  protect the new batch identity and IT/EN/ES scientific distinctions; three
  database counters were updated from 303 to 323 without weakening their
  content or runtime assertions. Current covered lines: 17,540 / 20,396.

After the static website and its Pages workflow were added, all 46 developer-
tooling tests passed in 7.36 seconds and Ruff remained clean. These focused
checks validate the three language pages, local links, release URLs, canonical
and `hreflang` metadata, JSON-LD, sitemap, `robots.txt`, copied image/icon bytes,
and the 17-file operational documentation inventory. They are not a repeated
full application coverage/security gate. The first remote Pages run initially
raced repository enablement, then passed unchanged after GitHub registered the
site; the published homepage was independently checked over HTTPS.

The GitHub workflow definition and its commands were checked locally. Do not
claim a remote CI pass until GitHub has run it. The user explicitly does not
want local work to wait for GitHub runs; they will report a remote failure.

### Test-Setup Tuning Evidence

The controlled local comparison against unchanged `0aecdb1` measured 310.62 s
before and 216.43 s after, both with four workers, the default scheduler and
coverage: 94.19 s / 30.3% less pytest time. The earlier editorial gate's
423.37 s is not the controlled baseline. All 1,237 original JUnit identities
were retained and passed, with ten new fixture regressions and ten unchanged
subtests. Coverage retained every formerly covered line and gained 13 bootstrap
lines: 17,539 / 20,396 executable lines; excluded lines are unchanged.

`astro_viewer/tests/database_fixture.py` is test-only and explicit: each test
owns its copy, GeoNames is really imported from that test's files, and no
template survives the session. Bootstrap/migration/recovery calls under test
still use real initialization. All 15 functional test modules are AST-identical
apart from setup calls/imports; controller, Skyfield, NSOM, tolerances and full
case loops are unchanged. `--fresh-test-databases` disables pooled setup for
diagnostics and passed five focused scenarios. The standard runner now reports
slow test phases without narrowing selection or disabling coverage. See
`docs/TESTING.md` for the fixture contract and measured scope.

### Local Windows Bundle For User Testing - 1.46.13

The official `packaging/build_windows.ps1` completed from clean `be30cda` on
2026-09-06, using Python 3.14.5, PyInstaller 6.22.2 and hooks-contrib 2026.7.
The pristine bundle contains 5,145 files / 429,331,997 bytes, embedded version
`1.46.13`. All 108 declared source assets and five legal files match SHA-256;
Qt Quick Dialogs and folder-list plugins are present. Executable SHA-256:
`40F5AB2EBD9FB1C74FDFDC5DF76D3A5AB5C8D0B8E3285207708B1C44391A4EF4`.

The packaged backend, normal-QML and Red Night Vision smoke tests exit 0 with
empty stderr and no runtime ERROR/CRITICAL/traceback entries. Each fresh DB
passes integrity/foreign-key checks, schema 27, exactly nine Solar image rows,
zero personal associations and field-by-field parity for all 323 descriptions
and 323 curiosities. All three temporary runtimes and their test copy were
removed. No user data was imported or used for an upgrade check.

The packaged desktop image test uses the same executable, Python archive,
Qt libraries and production detail/editor components, with a test-only QML
entry point in a separate disposable copy. Windows UI Automation selects a
synthetic JPEG through the actual native `#32770` dialog. The Qt fallback is
opened and accepted through its QML signal. Assertions pass for preview,
save, M31/NGC 224 alias sharing, cancellation, red source suppression and
reset, and a personal Solar image. A second launch decodes the saved Moon
image after the synthetic original is removed. Both processes exit 0, final
QML output contains only expected QA markers, originals are unchanged before
test cleanup, and the whole temporary runtime/copy is removed. This is not
a complete manual visual/provider or three-language desktop matrix.

The seven expected embedded image/backup/credential/timezone modules are
verified in the executable. Final pristine bundle audit passes; the focused
documentation/tooling recheck passes 46 tests in 9.57 s. Initial test-only
automation adjustments and failed screenshot attempts are recorded in the
ignored evidence directory; no application or packaged source was changed.

The old 1.46.10 dist, including its runtime DB/DB backup, preferences, caches
and logs, was replaced without preservation, as requested; no new distribution
backup was made. Evidence and QA helpers are under
`build/windows-dist-1.46.13-20260906/`. The unchanged application source gate
was not repeated. No version bump, Linux build, archive/checksum publication,
tag, signing/security scan, push or GitHub release is implied by this rebuild.

### Historical Windows Bundle For User Testing - 1.46.10

The official `packaging/build_windows.ps1` completed from clean `ae34df5` with
Python 3.14.5, PyInstaller 6.22.2 and hooks-contrib 2026.7. The pristine bundle
contains 5,277 files / 440,458,423 bytes, embedded version `1.46.10`. All 310
declared source assets and five legal files match by SHA-256. Qt/runtime/legal
audit passes before and after the packaged tests. Executable SHA-256:
`06C796709DCBF98847857BF338DFEF7AE92D2D54BDC66129E07EBF826EA8AC7F`.

The packaged backend, normal QML and Red Night Vision QML checks all exit 0,
with empty stderr and no runtime ERROR/CRITICAL/traceback entries. Their fresh
databases pass SQLite integrity/foreign-key checks and every canonical seed
field for all 323 descriptions and 323 curiosities. The new temporary test
copy and all three runtimes were removed; no previous-user-data preservation
or upgrade test was requested or performed. Logs and local helpers live under
`build/windows-dist-1.46.10-20260905/`. The source gate was not repeated for
unchanged application code. No version bump, Linux artifact, archive/tag,
signing/security scan, push or public release was created by this rebuild.

The earlier temporary test directory
`C:\Users\beast\AppData\Local\Temp\nightscope-dist-1.46.9-b245a5f625434bb48914ac35de9c0ef9`
was still present when rebuilding; the user was informed that it can be removed
separately. Do not confuse it with the deleted previous-distribution backup.

### Historical Windows Bundle - 1.46.9

The evidence below describes the preceding build, not the current dist. The
old dist and retained backup were subsequently removed at the user's request.

The requested rebuild used the official `packaging/build_windows.ps1` and the
configured Python 3.14.5 virtual environment. The result contains 5,277 files
and 440,456,369 bytes, with embedded version `1.46.9`; all 310 declared source
assets and five legal files match the source by SHA-256. Qt Positioning,
the Windows credential backend, timezone data and DE421 are present.
Executable SHA-256:
`90A702F9635CE5DE3A21571DBD223D6EE8FCAE4662CF7C6023668F5894E7F3F0`.

Packaged backend, normal-QML and Red Night Vision tests passed from an isolated
copy with separate runtime directories. An additional backend run upgraded a
copy of the previous `1.45.21` database. Both fresh and upgraded databases pass
SQLite integrity/foreign-key checks and contain all 323 descriptions and 323
curiosities matching the current seeds field by field. The previous database's
one profile and empty equipment/observation/preference tables are preserved;
language and startup settings are unchanged. The saved system-location cache
refreshes as expected because automatic detection was already enabled; the
original backup is untouched. This is not a populated-equipment upgrade matrix.

Build logs, local verification helpers and the temporary-directory cleanup
note are under `build/windows-dist-1.46.9-20260905/`. The execution policy
blocked removal of the disposable test copy; its exact path is recorded in
`VALIDATION.md` there. No new source gate was necessary for this
unchanged-code rebuild; the preceding same-commit gate remains the source
evidence. This validates a local Windows test bundle, not the complete manual,
provider, signing, archive or public-release checklist.

## Next Architectural Step

`1.45.19` completed the first persistence split. Profile CRUD and every
equipment-assignment family now live in `EquipmentProfileRepository`, while
`EquipmentCatalogRepository` owns global catalogue CRUD and inherits the old
profile surface only for compatibility. Both repositories use the existing
tables and stable IDs. A populated-database test verifies profile inventory
survives bootstrap unchanged, and a forced-failure test proves catalogue delete
plus assignment cleanup still roll back atomically.

The next persistence change should not be automatic. Choose either one coherent
catalogue family from the remaining repository or one migration/seed family
from `database.bootstrap`, only after mapping its transaction boundary. The
Skyfield event/calculation seams remain the next non-persistence priority.

## Active Product Work: Catalogue Editorial Content

Sources through `1.46.9` apply the prepared editorial pipeline to 75 notable
NGC-only galaxies and 20 planetary nebulae chosen for morphology, observing
value and direct evidence; six field-scoped remediations corrected 197
distinct baseline objects. The 228 Solar System/Messier/Caldwell entries
remain the immutable identity baseline; 323 physical objects are complete
and 7,271 NGC-only targets remain queued.

The network-free audit freezes the baseline identity, verifies canonical fields,
EN/ES overlay parity, provenance, duplicate text, accepted manifests and the
remaining count. Its historical paragraph screen and its new IT/EN/ES
sentence-level screen both report zero; identity stability still does not
certify every individual sentence. Long shared narrative sentences are now
repository-wide errors even without `--batch`; short advice is excluded and
explicit accepted language/field/object-pair waivers are supported. A
`baseline_remediation` manifest declares the exact changed fields, limits source
claims and candidate paragraph screening to that scope, and may revisit a
baseline ID in a later justified correction; the sentence screen remains
global. NGC enrichment remains complete-object work. New
manifests live under `astro_viewer/data/editorial_batches`; live source checks
and near-duplicate screening can be bounded to the batch currently under review.
Automatic object translation is opt-in through `--draft-editorial` and never
constitutes review.

Runtime and schema localization did not need redesign. Italian remains canonical
in the description/curiosity CSVs and EN/ES remain structured overlays. When a
future NGC record is complete, its `short_description` replaces the historic
catalogue placeholder and its `observing_notes` replace placeholder runtime
notes, so no fifth prose field is introduced.

Use `docs/CATALOGUE_EDITORIAL_WORKFLOW.md` as the acceptance contract. Important
boundaries:

- work in reviewed batches with one source version and commit per batch;
- never fabricate a fun fact from catalogue type alone;
- retain per-object source label, HTTPS URL, verification state, and stable
  `object_id`;
- review all three languages editorially rather than accepting raw automatic
  translation;
- keep editorial fields out of NSOM, equipment selection, visibility, and
  recommendation scores;
- do not regenerate `dist` until explicitly requested.

The accepted `batch_1_46_2.json` manifest adds 25 deliberately varied galaxies
with exact designations, direct NED evidence, and an object-specific
institutional or primary source for every curiosity. Its 50 distinct URLs
passed the live audit on 2026-09-04. Six representative objects were rendered
in all three languages and both normal and Red Night Vision modes: 36 scenes
showed complete final text and attribution without clipping or overlap.
`render_editorial_samples.py` keeps that matrix repeatable with an isolated
runtime and output outside the repository. The earlier 50-object evidence
remains recorded in `batch_1_46_1.json`.

The accepted `batch_1_46_3.json` manifest records rewritten observing notes for
17 Messier/Caldwell galaxies and rewritten descriptions for C17, C53, C65, and
C77. All three languages were reviewed against 17 direct NASA Hubble catalogue
pages. Seven representative objects produced 84 final scenes across both
detail-page positions, all three languages, and both visual modes. Curiosities,
best-seen fields, NGC coverage, schema, and recommendation behaviour are
unchanged.

The accepted `batch_1_46_4.json` manifest records rewritten observing notes for
48 Messier/Caldwell open clusters and ten rewritten descriptions. Its 48
distinct object-specific URLs passed the live audit. Nine representative
objects produced 108 final scenes across both detail-page positions, all three
languages, and both visual modes; all text remained complete and Red Night
Vision stayed monochromatic.

The accepted `batch_1_46_5.json` manifest records rewritten observing notes for
41 Messier/Caldwell globular clusters and rewritten descriptions for C42, C47,
C66, C81, C93, and C107. Forty-one direct NASA Hubble catalogue URLs passed the
live audit. Eight representative objects produced 96 final scenes across both
detail-page positions, all three languages, and both visual modes; all text
remained complete and Red Night Vision stayed monochromatic.

The accepted `batch_1_46_6.json` manifest records rewritten observing notes for
20 Messier/Caldwell emission, reflection, and planetary nebulae. Twenty
distinct object-specific URLs passed the live audit. Seven representative
objects produced 84 final scenes across both detail-page positions, all three
languages, and both visual modes; all text remained complete and Red Night
Vision stayed monochromatic.

The accepted `batch_1_46_7.json` manifest records rewritten observing notes for
51 Messier/Caldwell galaxies and rewritten descriptions for C21, C48, C57, and
C60. Fifty distinct NASA Hubble URLs passed the live audit. Ten representative
objects produced 120 final scenes across both detail-page positions, all three
languages, and both visual modes; all text remained complete and Red Night
Vision stayed monochromatic. Its zero-template result applied to whole
paragraphs, not to shared sentences inside otherwise different descriptions.

The `batch_1_46_8.json` manifest revisits 94 historical objects: 92 descriptions
and the curiosities of C8, C21, C48, C56, and C80. It removes residual templates,
corrects NGC 246's faint shell and NGC 4945's edge-on appearance, and preserves
M84's elliptical/lenticular classification differences with NASA and ESA
evidence. NGC 559's two-billion-year claim is replaced by a cited photometric
study estimating 224 million years. The other curiosity corrections cover
stellar-stream terminology, flocculent arms, the central triple system of
NGC 246, and Omega Centauri's tentative stripped-dwarf origin. Observing
notes, best-seen fields, difficulty ratings, catalogue metadata, identities,
and recommendation behaviour remain unchanged.
All 101 distinct manifest URLs passed the live audit. Twelve representative
objects produced 72 reviewed final description/curiosity scenes in IT/EN/ES
and normal/red modes, without clipping, overlap, or loss of red monochromy.
The field-level diff check confirms the same 97 edited fields per language
and no changes to unrelated translation sections. The focused catalogue,
translation, and developer-tooling suite passed 91 tests in 19.95 seconds.

The accepted `batch_1_46_9.json` adds 20 NGC-only planetary nebulae. Its
26 distinct URLs passed the live check on 2026-09-05. Six samples cover 72
Object Detail scenes: IT/EN/ES, normal/red, notes at the top and lower
description/curiosity cards. Key review distinctions include one physical
NGC 2371/2372, foreground NGC 2438 rather than M46 membership, infrared rings
in NGC 1514 rather than eyepiece features, and locally formed HeH+ in NGC 7027
rather than molecules surviving from the Big Bang. Companion hypotheses and
motion-derived ages retain qualifiers. Advice is conservative inference, not
a field-observation claim. No older prose, images, catalogue metadata or
runtime/scoring code changed. The focused catalogue/translation suite passed
49 tests in 14.15 seconds, including new identity and three-language
qualifier regressions; the existing Spanish terminology gate remains intact.

After the user's review of the correctness changes, the next editorial source
step can be `1.46.11`: continue NGC-only enrichment with
a new bounded manifest and the same source, three-language, static/live,
visual and full-gate requirements. Do not wait for GitHub Actions; the user
will report failures. Public platform bundles can group several source
batches; they are not implied by each patch.

## Release Boundary

The stable public versions are `v1.46.13` for Windows and `v1.43.0` for Linux.
Source readiness is not publication, and validation or publication of one
platform does not approve the other. Before a future artifact, update the target
version, run the coverage/security gate, compile translations, complete QML and
visual review, build the requested platform from a clean environment, audit its
legal/runtime contents, calculate and verify checksums, create the matching
source tag, and only then publish it. Follow `docs/RELEASE_CHECKLIST.md`.

## Living References

- `docs/ARCHITECTURE.md`: detailed current runtime architecture.
- `docs/ARCHITECTURE_REVIEW_1_45.md`: evidence-backed structural assessment.
- `docs/ASTRONOMICAL_CORRECTIONS_1_46_10.md`: corrected scientific contracts,
  regression evidence and remaining model limits.
- `docs/TESTING.md`: current local and CI gate contract.
- `docs/CATALOGUE_EDITORIAL_WORKFLOW.md`: active multilingual content workflow.
- `astro_viewer/data/editorial_batches/`: baseline, batch schema and acceptance
  evidence for the `1.46.x` programme.
- `docs/RELEASE_CHECKLIST.md`: artifact and publication approval.
- `astro_viewer/CHANGELOG.md`: source-version history.
- `website/`: official static EN/IT/ES product website and SEO assets.
