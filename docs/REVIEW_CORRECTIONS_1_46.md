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

## Remaining editorial steps

R4 explicitly qualifies existing seasonal guidance without changing catalogue
coordinates or silently inventing new visibility periods. R5 restores the
probable, rather than certain, merger interpretation for NGC 1266 in all three
languages, following the [record's NASA source](https://science.nasa.gov/missions/hubble/hubble-sights-galaxy-in-transition/).
Each bounded field-scoped batch retains its own version, manifest, review and
commit; accepted historical manifests are not rewritten.
