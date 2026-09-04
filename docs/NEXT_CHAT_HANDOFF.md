# NightScope - Next Chat Handoff

Updated: 2026-09-04

## Current State

- Source version: `1.46.6`.
- Current public Windows release: `v1.45.21`, from source commit
  `d06300b43db0b3df2acbcb7cde2761158704f7b5`; its GitHub release contains the
  portable Windows x64 ZIP and no Linux package.
- Current public Linux release: `v1.43.0`, from source commit
  `26dfaf49df8f9b8e73e84f406396f406170400b2`; its GitHub release contains the
  Debian 12 x86-64 tarball and adjacent checksum.
- Source `1.46.6` is not published: no `v1.46.6` tag, bundle, checksum, or
  GitHub release has been created.
- `dist` was deliberately not regenerated or modified for `1.46.6`.
- Six editorial batches are accepted: two enrich 75 NGC-only galaxies with
  complete canonical Italian content and reviewed English/Spanish overlays;
  the other four remediate declared fields for 17 baseline galaxies, 48
  baseline open clusters, 41 baseline globular clusters, and 20 baseline
  nebulae or planetary nebulae. Catalogue
  coverage remains 303 complete objects (228 baseline plus 75 NGC-only), with
  7,291 NGC-only targets remaining.
- A retrospective quality screen confirms the 50 entries added in `1.46.1`
  remain specific and useful. The older baseline has measurable formulaic debt:
  the four remediation batches clear the open-cluster, globular-cluster and
  nebula families plus the first galaxy family. The remaining warning reports
  2 connected description families across 4 objects and 5 observing-note
  families across 51 objects, all galaxies; they must be remediated in reviewed
  batches rather than hidden by bulk rewrites.
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
| 1.46.6 | current source | Replaces formulaic guidance for 20 baseline nebulae and planetary nebulae. |

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

The final local `1.46.6` coverage/security source gate passed on
Windows/Python 3.14.5:

- 1,227 tests and 10 subtests in 266.69 seconds, with 86% aggregate application
  coverage; the only tool-level warning was the expected non-failing report of
  residual historical formulaic prose;
- validated toolchain: pip 26.2.1, Ruff 0.16.5, coverage 7.16.0, PyInstaller
  6.22.2, and `pyinstaller-hooks-contrib` 2026.7;
- validated UI/astronomy runtime: PySide6/Qt/shiboken6 6.11.2, Skyfield 1.55,
  Astropy 8.0.1, astropy-IERS-data `0.2026.8.31.0.57.9`, and NumPy 2.5.2;
- validated Earthdata runtime: earthaccess 0.18.0, s3fs/fsspec 2026.7.0,
  aiobotocore 3.9.0, and maximum compatible botocore 1.43.56;
- complete documentation inventory at the coverage/security gate: 247 Python,
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
- the earlier PySide6 6.11.2 `qmllint`, isolated first-use/saved-Spanish launches,
  and native Windows splash renders from `1.45.22` remain the latest dedicated
  startup evidence; no QML source changed from `1.46.1` through `1.46.6`.

After the static website and its Pages workflow were added, all 46 developer-
tooling tests passed in 7.36 seconds and Ruff remained clean. These focused
checks validate the three language pages, local links, release URLs, canonical
and `hreflang` metadata, JSON-LD, sitemap, `robots.txt`, copied image/icon bytes,
and the 17-file operational documentation inventory. They are not a repeated
full application coverage/security gate. The first remote Pages run initially
raced repository enablement, then passed unchanged after GitHub registered the
site; the published homepage was independently checked over HTTPS.

The GitHub workflow definition and its commands were checked locally. Do not
claim a remote CI pass until GitHub has run it.

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

Sources through `1.46.6` apply the prepared editorial pipeline to 75 notable
NGC-only galaxies chosen for morphology, surface brightness, observing value,
and direct scientific evidence, then use four field-scoped remediations to
replace generic prose for 17 baseline galaxies, 48 open clusters, 41 globular
clusters, and 20 nebulae or planetary nebulae. The 228 Solar
System/Messier/Caldwell entries remain the immutable identity baseline; 303
physical objects are complete and 7,291 NGC-only targets remain queued.

The network-free audit freezes the baseline identity, verifies canonical fields,
EN/ES overlay parity, provenance, duplicate text, accepted manifests and the
remaining count. It separately reports repeated or near-identical legacy
baseline prose: identity stability does not certify historical wording. A
`baseline_remediation` manifest declares the exact changed fields, limits source
claims and duplicate screening to that scope, and may revisit a baseline ID in
a later justified correction; NGC enrichment remains complete-object work. New
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

The next source step is `1.46.7`: remediate the 51 galaxies and four galaxy
descriptions still present in the final measured baseline template families.
Review every Italian field and both translations, accept a bounded manifest,
run its static/live and visual checks plus the full source gate, then commit it
as one version. Public platform bundles can group several source batches; they
are not implied by each patch.

## Release Boundary

The stable public versions are `v1.45.21` for Windows and `v1.43.0` for Linux.
Source readiness is not publication, and validation or publication of one
platform does not approve the other. Before a future artifact, update the target
version, run the coverage/security gate, compile translations, complete QML and
visual review, build the requested platform from a clean environment, audit its
legal/runtime contents, calculate and verify checksums, create the matching
source tag, and only then publish it. Follow `docs/RELEASE_CHECKLIST.md`.

## Living References

- `docs/ARCHITECTURE.md`: detailed current runtime architecture.
- `docs/ARCHITECTURE_REVIEW_1_45.md`: evidence-backed structural assessment.
- `docs/TESTING.md`: current local and CI gate contract.
- `docs/CATALOGUE_EDITORIAL_WORKFLOW.md`: active multilingual content workflow.
- `astro_viewer/data/editorial_batches/`: baseline, batch schema and acceptance
  evidence for the `1.46.x` programme.
- `docs/RELEASE_CHECKLIST.md`: artifact and publication approval.
- `astro_viewer/CHANGELOG.md`: source-version history.
- `website/`: official static EN/IT/ES product website and SEO assets.
