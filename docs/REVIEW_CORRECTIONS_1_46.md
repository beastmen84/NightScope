# Corrections following the 1.45.21–1.46.13 review

Review baseline: `b435b7b`, 6 September 2026. The user authorized correcting
the findings. Source patches and local commits remain separate from public
Windows 1.46.13, Linux 1.43.0 and the existing Windows dist.

## Source 1.46.14 — runtime and maintenance

- **R1:** ordinary content-translation maintenance copies the existing `objects`
  section intact. Neither refresh mode routes reviewed prose through historical
  overrides or cleanup rules. Explicit `--draft-editorial` retains its draft-only
  meaning. Regression tests compare the entire real EN/ES object sections.
- **R2:** observing presentation checks the positive absolute useful interval,
  whose end can precede sunrise. At/after its end, the state is window-ended,
  not too-low or later. A missing `observable_now` hint also respects that
  half-open interval. Future advice must have a future instant; known high
  altitude is never described as below the threshold. Ephemerides and scoring
  are unchanged.
- **R3:** appearance loads before splash creation. All progress states and the
  bootstrap-failure dialog respect the saved red preference, without a colored
  logo or native bright window frame. Widget-only fonts request no subpixel
  antialiasing; the palette also zeros green/blue, because that Qt hint is
  best-effort on native Windows. See the [Qt font contract](https://doc.qt.io/qt-6/qfont.html#StyleStrategy-enum).
- The stale “next 1.46.10” editorial pointer is replaced with the current
  handoff/version allocation rule.

Focused validation covers production overlay updates, morning twilight and
exact useful-window boundaries, persisted appearance, and real widget pixel
checks in IT/EN/ES. Evidence is under `build/review-corrections-1.46.14/`.
The final source gate result is recorded after completion in TESTING/handoff.

## Source 1.46.15 — baseline galaxy periods

R4, first bounded step: 75 existing galaxy `best_seen` fields now name both
hemispheres in IT/EN/ES. Existing periods and observing conditions are retained;
this is a reference-frame clarification, not a fresh optimal-period calculation.
The source is the pinned 1.46.13 seed plus
[NASA's explanation of opposite seasons](https://spaceplace.nasa.gov/seasons/en/).
Both evidence URLs pass. M31, M83, C3, M82 and M91 pass all six language/theme
contact sheets (30 real QML scenes), including the complete best-seen line.
Coverage remains 323 complete / 95 NGC-only / 7,271 pending; the ledger has
10 accepted batches and 203 distinct baseline IDs with field-scoped remediation.

## Source 1.46.16 — baseline open clusters and stellar fields

R4, second bounded step: 57 existing `best_seen` records, same field-only and
three-language scope. The 54 open clusters plus M24, M40 and M73 retain their
individual identities and all other prose. Both evidence URLs pass. M45, M73,
M40, C14 and C94 pass six contact sheets / 30 QML scenes with complete seasonal
labels in both themes. Coverage is unchanged; 11 accepted batches now cover
209 distinct remediated baseline IDs.

## Source 1.46.17 — baseline globulars and nebulae

R4, third bounded step: the remaining 87 baseline deep-sky `best_seen` fields
are explicit in IT/EN/ES, bringing the corrected baseline total to 219.
C80 now pairs northern spring with southern autumn, consistent with the
[NASA observing guidance](https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-caldwell-catalog/caldwell-80/).
The three evidence URLs pass. C80, M42, C20, C105 and M76 pass all six contact
sheets / 30 QML scenes. No coordinate, magnitude, observing note, description,
curiosity or difficulty changed. The ledger has 12 accepted batches and
219 distinct remediated baseline IDs; NGC coverage remains unchanged.

## Source 1.46.18 — existing NGC records and prevention

R4's final group contains 56 previously enriched NGC galaxies. R5 also revises
NGC 1266's curiosity in IT/EN/ES: observed outflows are distinguished from the
proposed minor merger and the black hole's possible suppression of new stars,
following the [record's NASA source](https://science.nasa.gov/missions/hubble/hubble-sights-galaxy-in-transition/).
All three distinct URLs pass. NGC 1266, 1961, 613, 6951 and 3621 pass six
contact sheets / 30 QML scenes, including the curiosity and full period lines.

The new `ngc_remediation` manifest kind retains the 100-object ceiling,
declared-field/source boundaries, three-language review and visual acceptance.
It requires an earlier accepted NGC enrichment and does not increase coverage.
Historical manifests are unchanged. A repository-wide seasonal-clause check
rejects unspecified hemispheres in each language, including when an unrelated
later clause mentions northern latitude. These are screening protections, not
a substitute for scientific or language review.

The final ledger contains 13 accepted batches: three enrichment and ten
remediation, covering 219 distinct baseline IDs plus the 56 revised NGC IDs.
Coverage stays 323 complete objects, including 95 NGC-only, with 7,271 NGC-only
objects still pending. No new NGC enrichment was undertaken during corrections.

## Cross-version verification and release boundary

A parsed field comparison against `b435b7b` confirms exactly 275 changed
`best_seen` values and one changed curiosity in each language. Every other
editorial field, technical catalogue row and object identity is unchanged;
all comma/semicolon observing-condition suffixes are retained. The original
production overlay-maintenance and morning-twilight probes were rerun after
the corrections. Logs: `build/review-corrections-1.46.14/final-18-probes.log`.
The fresh final `--security` run passes: 1,515 tests and ten subtests,
86% coverage (18,219 / 21,120 lines), plus all three isolated source smokes.
The first attempt exposed one stale exact-value C23 expectation, corrected
without dropping assertions; TESTING retains that result separately from the
subsequent completely passing run. All five review findings are closed in
source within the stated scope. This does not certify every catalogue claim
or every application configuration beyond the reviewed/tested cases.

Source version and manual revision are 1.46.18. Public download links remain
Windows 1.46.13 and Linux 1.43.0; local dist and public assets are not rebuilt
or rewritten. No push, tag, GitHub Actions wait or publication is part of this
work. The preliminary non-isolated development smoke is disclosed in TESTING;
subsequent application smokes and all QML renders use disposable runtimes.
