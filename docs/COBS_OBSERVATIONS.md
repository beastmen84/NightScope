# COBS comet observations

Included in source 1.47.0 and its Windows build preparation, 2026-09-20.
The user's confirmed intended use is noncommercial. Public Windows 1.46.21
does not include this integration. Artifact validation is recorded separately
in `TESTING.md`; a local build is not publication.

## Sources and rights

- API: https://cobs.si/api/obs_list.api
- Contract: https://cobs.si/help/cobs_api/observation_list_api/
- Policy: https://cobs.si/help/data_policy/
- Licence: https://creativecommons.org/licenses/by-nc-sa/4.0/

Free, no account/key. The API currently reports version 1.5 (the documentation
heading still says 1.4). Unknown versions fail closed. Credit belongs to COBS
and contributing observers. Data and distributed derived adaptations remain
CC BY-NC-SA 4.0, with attribution, licence and modification notices. Code stays
MPL 2.0; runtime downloads are not an exception to the data licence. No dataset
is bundled. Cached API records retain observer credits; the UI links to source
and licence and identifies NightScope analysis. No additional COBS permission
or endorsement has been obtained or claimed.

## Runtime contract

`CobsObservationStore` is created without disk/network work. `CobsManager`
starts two seconds after the first frame and performs loading/downloads on a
dedicated worker. It queries the last 14 UTC days globally, not per location,
comet or equipment profile. No location/credentials are transmitted. Completed
responses, including valid empty results, are reused for 24 hours across
restarts. Failure backoff also survives restart where the cache is writable.

Pagination is verified completely before publication: at most eight pages of
2,500 records, 6 MiB per page, a 45-second checked download budget plus bounded
connect/read timeouts. No redirects or automatic immediate retries. A failing
or partial response preserves previous observations; the UI marks fallback
data. Atomic writes never overwrite a valid cache with a partial download.
Dates of observations, not download dates, determine scientific eligibility.
The local cache is `cobs_observations.json` beside the runtime database, not
the seed or orbital database.

The comet worker consumes an immutable snapshot; no COBS I/O is added to
Skyfield calculations. Source revision tokens invalidate only the changed
transient source. Tokens are captured before preparation, so a provider update
racing with a calculation schedules a follow-up instead of blessing old data.
Controller requests are coalesced during an existing worker. The comet results
are refreshed hourly when COBS is integrated; the download remains daily.

## Scientific use, not merely a display overlay

The existing JPL orbit and total-brightness law remain:

`m = M1 + 5 log10(geocentric distance/AU) + K1 log10(heliocentric distance/AU)`.

At each original observation's UTC epoch, NightScope computes that baseline
and forms **observed minus predicted** residuals. It does not average raw
magnitudes taken at different distances, fit an orbit, refit K1 or infer a
90-day light curve from current photometry.

Usable records exclude nondetection/limit flags, poor-condition flags, reported
issues (API filter, plus known flags checked locally), malformed/nonfinite
magnitudes, future dates and fragments. Matching uses explicit normalized
designations, never the discovery name alone. Ordinary Johnson V, R, other
filters and unfiltered/nuclear photometry cannot calibrate visual visibility.
The API's observation **type V** is distinct from instrumental **method V**.

The following thresholds are conservative **NightScope policies**, not accuracy
claims or standards supplied by COBS:

- Fit observations from the last seven days; the last one must be less than
  72 hours old. The correction is applied only from its latest measurement
  through that measurement plus 72 hours, never beyond it.
- Visual type V / methods S, B or M: at least three observer/UTC-day samples,
  at least two independent observer codes and at least two UTC dates.
- Instrumental type C / visual-equivalent method Z: a separate fallback
  series, requiring at least six observer/day samples and three observers
  across at least two dates. It is not mixed with visual observations.
- Collapse repeated observer/day estimates, then balance observers using
  medians. A burst of frames cannot manufacture independent confirmation.
- Reject reported uncertainty above 0.5 mag, inter-bin residual ranges above
  1.0 mag, daily-median changes above 0.6 mag, offsets larger than 3 mag, or
  conflicting qualified visual/Z fits differing by more than 0.75 mag.
  A well-supported unstable visual series cannot be bypassed by choosing Z.
- Keep a practical faint-side margin of at least 0.35 mag, enlarged to cover
  accepted residual deviations and reported errors. It is not a statistical
  confidence interval and does not shrink with sample count.

An accepted offset changes the **coarse candidate filter**, sampled brightness,
useful-night admission, brightest-12 comet selection and the generic instrument
advice for the first useful night. Night admission and instrument advice use
the faint-side margin; displayed brightness and selection ordering use the
central estimate. Geometry thresholds/positions, lunar quantities and optical
formulas do not change. The familiar period can contain both corrected
near-term nights and later JPL-only nights; the detail states the expiry and,
when applicable, the corrected estimate for the next window.

Missing, expired, discordant or incompatible observations leave original
scientific results intact, with an explicit fallback explanation. A fresh
download is not a guarantee of fresh or reliable measurements.

## Limits and scope

This is empirical short-term guidance, not certified accuracy. Missing
uncertainty is not interpreted as zero error. Independent observers can share
systematic biases; integrated magnitude is not coma surface brightness and
does not guarantee detection. An outburst/rapid change or strong disagreement
causes fallback, not a confident extrapolation. Nights just after correction
expiry use JPL again and can differ discontinuously; the validity label makes
that model boundary explicit rather than disguising it as an observed trend.

Only comets already supported by the JPL candidate query can be recovered by
COBS: M1/K1 and orbital elements must exist, the perihelion selection must
include them, and fragments remain excluded. COBS is not yet an independent
discovery/alert catalogue. It does not add moving comets to the fixed-object
NSOM catalogue/night planner or tailor apertures/exposure times to individual
photographic measurements. Those would require a distinct moving-target and
photometric-detectability workflow, not a change in the meaning of existing
scores. Calendar highlights retain their event-level policy; the upstream
comet candidate set can change intentionally.

UI: a half-width provider card beside IMO, source/licence and cache status;
compact translated comet-detail facts for observation dates/counts, calibration
or fallback reason, expiry and methods. The latest available visual (or, if
absent, CCD visual-equivalent) measurement is explicitly dated and identified
as a single observation, not a prediction. Comet facts wrap and stack at narrow
widths, as meteor facts already do. IT/EN/ES resources are compiled. There
is no automatic source upload, publication, distribution rebuild or release.
