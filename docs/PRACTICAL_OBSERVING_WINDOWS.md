# Practical observing windows (unreleased source)

Date: 2026-09-19. Baseline: `35bd872`. VERSION remains 1.46.21.
This work changes observing guidance and Calendar presentation, not the
published Windows bundle. No release, push, website change or dist rebuild.

## Presentation contracts

- Home and its sidebar show **good weather windows**, alongside a separately
  labelled forecast peak. Good runs can exceed three hours; bad or missing
  hourly forecasts split them. At least two consecutive hourly samples must
  satisfy cloud cover <=35%, precipitation probability <=20%, wind <=20 km/h
  and the existing humidity-aware hourly weather score >=70. These are
  presentation thresholds, distinct from the usable-weather planner policy
  documented in the follow-up audit below. NSOM/session admission is unchanged.
  Forecasts are not guarantees, and good weather is not a claim of astronomical
  darkness, favourable Moon position or target visibility.
- The Home header shows the existing **astronomical darkness** interval
  (Sun below -18 degrees). Sunset/sunrise are not added. The astronomy worker
  publishes the cached result in its snapshot; the Qt getter never calculates
  ephemerides. Location/timezone changes, night rollover, missing location,
  polar daylight and failed calculations do not retain an obsolete interval.
- Target details show a **preferred altitude window**, not a one-minute
  deadline. It is the connected interval around the sampled altitude maximum,
  above both 30 degrees and maximum minus 10 degrees, lasting at least 30
  minutes. It reuses the existing night-clipped samples and interpolated
  crossings. Low/brief targets have no preferred plateau; their ordinary
  useful window and technical maximum remain. It is not a weather forecast.
- Comet cards show the favourable observing-night period, not the final
  highest-altitude sample as an absolute best date. The original `peak_at`
  remains technical metadata. The magnitude envelope covers the selected
  nights, not only the highest-altitude night. The 90-day calculation horizon
  is displayed, with an explicit warning when the last group reaches its end. No claim is
  made about the following months or uninterrupted day-and-night visibility.

## Planetary periods

The exact existing events are retained, including their dates, separations,
local visibility at the event instant and equipment advice. A separate
projection supplies favourable observing nights:

- Pair conjunctions: up to 30 days either side of the exact minimum, separation
  <= min(6 degrees, max(1 degree, minimum separation + 2 degrees)).
- Oppositions: up to 90 days either side, apparent diameter at least 95% of
  the sampled maximum nearby (distance <= minimum distance / 0.95).
- Compact groups: at least three planets, **every pair** within 6 degrees.
  A chain A-B-C with distant endpoints is not accepted.
- Broad parades: at least four of Mercury, Venus, Mars, Jupiter and Saturn
  simultaneously usable, not necessarily close together or in one optical
  field. This does not claim a perfect spatial alignment.

All members must be >=15 degrees altitude for two consecutive hourly samples
(one elapsed hour). Bright planets use Sun <=-6 degrees; any group containing
Uranus/Neptune requires <=-18 degrees. The grid is a coarse, conservative
guide: short opportunities can be missed and weather/terrain are not modelled.
Existing shorter event-night windows remain available and distinct.

Consecutive useful nights are grouped; interruptions are preserved. Dates are
observing nights identified by local noon-to-noon bounds, not continuous
visibility. Look-back searches retain recent exact events while their practical
season is still useful. Calendar date filters include a season that starts
before its exact event. Maximal multi-planet sets suppress contained subgroups
on the same night; this is not an exhaustive list of every possible combination.

The numerical grid is batched, omits daytime planetary calculations and has a
single-entry cache keyed by coordinates, timezone and analysis dates. No new
threads or network services are introduced. If the optional planetary projection
fails, exact future events remain available. Reported dates at an analysis
boundary explicitly remain estimates and may extend beyond the search.

## Scientific references and policy limits

- [USNO rise/set and twilight definitions](https://aa.usno.navy.mil/faq/RST_defs):
  astronomical twilight uses -18 degrees, not the sunset/sunrise boundary.
- [USNO glossary](https://aa.usno.navy.mil/faq/asa_glossary): an angular closest
  approach and a conjunction are distinct technical concepts; NightScope
  retains its existing pair-event convention.
- [NASA planetary alignments and parades](https://science.nasa.gov/solar-system/skywatching/planetary-alignments-and-planet-parades/):
  multiple planets can be interesting over a period rather than one instant.
- [NASA Saturn opposition observing guidance](https://www.nasa.gov/blogs/watch-the-skies/2023/08/24/saturn-shines-this-week-3-ways-to-view-the-planets-opposition/):
  useful observations extend around the exact opposition date.

The 30-degree/10-degree altitude plateau, 95% size criterion, angular limits,
hourly sampling and weather thresholds are explicit NightScope guidance
policies, **not** universal astronomical standards or physical detectability
models. The old ranking, geometry, precision and planner thresholds are not
replaced by these policies.

## Verification

Evidence is under `build/observing-windows-20260919/` (ignored local diagnostics).

- Focused regressions cover evening-to-dawn weather with a later peak, gaps,
  invalid/bad samples, autumn clock folds, short/low altitude plateaus, local
  darkness snapshot/failure handling, changed timezone, no-night cases,
  grouping versus angular chains, maximal-set deduplication, parades, faint
  planets, distance-derived opposition periods, conjunction limits, active
  past events, early-starting seasons and comet analysis limits.
- Real ephemeris tests compare the batch planetary grid with scalar geometry
  and cover polar daylight. Existing astronomy, observing-refresh and
  recommendation regression suites remain part of the full source gate.
- `baseline-parity.log`: direct comparison with Git baseline at Addis Ababa,
  Rome (autumn DST night) and Tromso (polar summer). All previous solar-system
  fields match exactly, excluding the new display-only field. All **252**
  original annual events retain every existing field exactly; new periods and
  additional events are deliberate additions.
- `catalogue-parity.log`: read-only SQLite access, all **7,585** catalogue
  objects enabled, Addis Ababa/Rome/Cape Town. Ordered results contain
  **4,729 / 5,229 / 4,767** targets respectively: every old field and ranking
  matches exactly. Also 36 independently calculated scalar details match.
- Initial full run: 2,016 passed, with two expected-contract failures
  (new source inventory and renamed detail label). Both were corrected;
  targeted reruns pass. Final full gate: 2,020 tests and ten subtests pass;
  87% overall coverage, 97% of the new planetary module, no known dependency
  vulnerabilities and all three isolated smokes. Final context, unavailable-data
  and gap-filter refinements have a further 126-check targeted rerun. Results
  and logs are recorded in TESTING and handoff.
- IT/EN/ES catalogues contain 2,118 completed messages per language; all new
  translations have reviewed entries and compiled QM files. Lazy joins retain
  translation/date metadata across runtime language changes.

The annual-calendar parity probe also measured 2.81-3.11 s before and
3.96-4.77 s after on this PC (single runs, concurrent validation activity).
This is roughly 1.1-1.7 s of additional annual analysis, **not** a whole-app
startup benchmark or a speed improvement. Numerical arrays are cached; the
normal desktop runs this work in the existing astronomy worker, not in QML
getters. Existing startup/network limits are not claimed to be resolved here.

## Follow-up guidance audit: existing data only

Baseline `80cdb32`, 2026-09-19. This second pass intentionally changes which
times/targets enter the plan and which comet nights pass the duration policy;
it is not a claim of identical guidance. Astronomical positions, ephemerides,
optical formulas, NSOM arithmetic and equipment scoring are not changed.

- The planner intersects each target's useful astronomical interval with
  usable hourly forecast bins before choosing up to four targets. It keeps
  the original time when usable; otherwise chooses the closest usable time.
  Usable means the existing weather policy: clouds <=65%, precipitation
  probability <=35%, wind <=28 km/h and hourly weather score >=45. These are
  not the stricter **good-window** thresholds. Bad, invalid and missing hours
  are not bridged. Each row covers at most one elapsed hour, clipped by the
  following row, the night, the target window and the current time. Duplicate
  conflicts are conservative; UTC comparison preserves explicit DST folds,
  while offset-free ambiguous/nonexistent hours are rejected.
- A production refresh always snapshots the hourly forecast as an immutable
  tuple and includes it in the catalogue runtime signature. An empty forecast
  cannot substantiate a plan. `None` retains compatibility only for older
  service adapters without an hourly contract. Both synchronous and detached
  catalogue/observing paths pass the same inputs. Existing nightly weather
  blocking remains; this is not a new global scheduler, slew/exposure budget,
  hourly NSOM model or rescore of target-specific lunar geometry at the moved
  instant. The plan labels direction as **now**, because it is current azimuth,
  not the azimuth forecast for the scheduled time.
- Comet windows stop at the last passing sample, not 30 minutes after it.
  At least 60 minutes must be spanned by valid samples (three points at the
  existing half-hour cadence). This conservative grid can miss short/grazing
  opportunities; it no longer awards an unverified extra half-hour. All useful
  groups are retained, with gaps and one aggregate event per comet. Existing
  magnitude/geometry thresholds and the 12-comet display cap remain. As before,
  the longest useful sampled interval represents each observing night.
- Comet details show the next local sampled interval, plus an explicit local
  reference time for solar elongation and lunar data from that first night.
  Maximum altitude is still labelled as the maximum over the analysis period;
  `peak_at` remains technical metadata. The magnitude range is rounded outward
  from the model values at nightly altitude peaks across **all** retained nights.
  The arbitrary extra +/-1 magnitude padding is removed: this is a model range,
  not a confidence interval or a guarantee of visual detectability. Equipment
  text refers to the first night. Actual comet brightness remains uncertain.
- Missing seeing inputs carry explicit availability metadata. QML/Home display
  `n/d`, not the internal neutral 50/100 fallback as a real forecast. A partial
  deep-sky diagnosis does not display a complete numeric score. The fallback
  remains unchanged inside NSOM/optical calculations. Available seeing is
  explicitly an empirical estimate, not measured turbulence or an arcsecond
  forecast; users are advised to check the image at the eyepiece.
- The compact Moon card describes **potential** interference from illumination,
  conditional on altitude/time and angular distance to the target. It does not
  calculate a new Moon-free period or imply interference all night. Existing
  per-target lunar geometry remains in recommendations. At narrow widths the
  decorative icon is omitted so rise/set times retain space. Meteor-shower
  maxima are explicitly indicative: dates and observing-clock templates are
  still recurring approximations, not an annual IMO prediction.
- IT/EN/ES translations are manually reviewed and compiled. Event detail avoids
  repeating the same comet period in three different blocks. No provider,
  dependency, network request, database schema or startup calculation is added.

### Subsequent data-source policy

Only genuinely free sources compatible with NightScope's distribution may be
considered. Free trials, payment-dependent tiers and Meteoblue are excluded.
Free access alone does not establish permission to redistribute a dataset:
licence, attribution, quotas and non-commercial restrictions must be checked
before enabling a provider. Annual meteor data, observed comet brightness and
specialised atmospheric estimates remain subsequent work, not implemented here.
Any future integration must use cached/offline fallback data and avoid adding
network waits to startup. The existing Meteoblue-named compatibility placeholder
only calls the local basic estimator; it is not a Meteoblue API integration.

Evidence for this follow-up is under `build/recommendation-guidance-20260919/`.
Current validation results are recorded in `TESTING.md` and the handoff.
