# Automatic IMO calendar

This unreleased integration adds the International Meteor Organization as a
no-account provider. It does not change the public 1.46.21 Windows distribution.

## Download and ownership

- The normal desktop launch starts the worker 1.5 seconds after the first
  frame. No network request, PDF import or parsing occurs during the splash.
  Backend/QML smoke modes do not start automatic downloads.
- The year is the PC's current civil year, not the selected catalogue month.
  The worker first validates `imo_calendar/calendar-YYYY.pdf` in the runtime
  cache. A valid local calendar suppresses subsequent downloads, including
  restarts and the Retry action. In-session checks detect year changes.
- The downloader tries IMO's historic annual URL, then discovers a matching
  PDF link on the official home page. Only HTTPS `imo.net` / `www.imo.net`
  targets are allowed; redirects are rejected. Requests have connect/read and
  response-size limits. An HTML maintenance page with HTTP 200 is not a PDF.
- PDF header/trailer, page count, title year, Working List year, all ten
  supported shower rows, dates, intervals and coordinates must validate.
  Unknown layouts and incomplete tables fail closed. The introductory page's
  table reference avoids extracting all charts/prose on normal cached reads;
  the adjacent radiant-drift table is also read when its reference is present.
- Installation uses a temporary file, flush/fsync and atomic replacement.
  Only after success are older `calendar-YYYY.pdf` files in this provider's
  cache removed. Unrelated files, newer-year files and symlinks are preserved.
  Failed downloads, imports or writes retain the previous calendar. Old-year
  predictions are never relabelled as current-year data.
- Failed automatic attempts have a persisted 24-hour retry deadline. Restarting
  neither hammers the provider nor resets this deadline. Manual Retry bypasses
  the failure cooldown, but never re-downloads a valid current calendar.
- The provider card shows state, stored year, filename, save date and the ten
  supported major showers. An optional Import PDF action validates and copies
  the original current-year publication without changing the selected source
  file. This is useful during upstream outages; automatic rollover remains.

Windows uses the portable runtime cache; Linux uses the existing XDG cache
root. `NIGHTSCOPE_RUNTIME_DIR` isolates tests. Runtime PDFs and retry metadata
are excluded from Git and rejected by the distribution runtime-state audit.

## Scientific scope

Only the ten major showers already present in NightScope are imported from
the annual Working List (Table 5): QUA, LYR, ETA, SDA, PER, DRA, ORI, LEO, GEM
and URS. This is not an import of every meteor shower or every modelled outburst.
The event presentation uses the edition-specific maximum date, activity period
and reference ZHR, including qualifiers such as `80+`. Dates are labelled UT.
The internal sorting anchor is not an exact predicted peak and is not displayed
as an observing time. ZHR describes ideal reference conditions, not a predicted
local count. Activity dates are not presented as local observing windows.

Local windows now combine astronomical darkness, radiant altitude and lunar
geometry, with a separate forecast assessment. They can be computed months in
advance from the downloaded edition and installed Skyfield ephemerides. The
maximum remains an annual UT date; no exact peak, local meteor rate or outburst
is inferred. Extraction of additional peaks from narrative sections is still
outside this integration. The generic internal usefulness score stays 78, but
the meteor priority badge now says IMO calendar, not Relevant: local geometry
and source provenance are different information.

For example, the supplied 2026 calendar replaces the built-in October 8
Draconids recurrence with October 9 UT, activity October 6-10 and reference
ZHR 5. These are edition-specific facts, not five guaranteed visible meteors
per hour. The separate local interval does not change the predicted maximum.

### Local window policy

- Analyse the maximum UT date and its two neighbouring UT dates, clipped to
  the annual activity bounds. This is not a best-night or meteor-flux model
  for the entire season. The primary interval is selected by geometry, not by
  assuming that each night has the peak ZHR.
- Sample at five-minute intervals. Require Sun altitude at or below -18 degrees
  and radiant altitude at least 15 degrees for a usable interval. A favourable
  interval additionally requires radiant altitude at least 30 degrees and Moon
  centre at or below -0.83 degrees, or illumination at most 25 percent. These
  are explicit NightScope planning heuristics, not universal IMO thresholds.
- Keep continuous intervals of at least 30 minutes. End at the final valid
  sample, never one step beyond it. Do not bridge gaps or unfavourable samples.
  Select a favourable interval first, then longest duration, greatest sampled
  radiant altitude and earliest start. Also show other comparable intervals
  and the wider usable interval when available. Polar/no-darkness/low-radiant
  cases are explicit; missing calculations remain unassessed.
- Table 6 radiant drift is optional. PDF text coordinates preserve empty cells;
  require a labelled, unambiguous column, valid dates/coordinates, continuity
  and agreement with the Working List. Interpolate RA on the shortest arc and
  never extrapolate. Otherwise use the maximum's approximate radiant and state
  that limitation. The 2026 Draconids have only one Table 6 point, so no invented
  drift is applied. This is not a precision model of radiant dispersion.
- Rotate the J2000 radiant direction with Skyfield's local horizon matrix;
  lunar and solar positions use topocentric apparent ephemerides. Published
  intervals include local dates and the location's IANA timezone. UTC elapsed
  time handles midnight/year/DST boundaries; ongoing windows are clipped and
  their lunar/radiant facts recomputed from cached samples.
- Weather never changes the astronomical interval or its badge. When matching
  local forecasts exist, intersect their actual hourly coverage with the
  primary interval using the planner's existing usable-weather admission rules.
  Missing/ambiguous/conflicting hours are conservative. Partial coverage,
  unusable weather and future unavailable forecasts have distinct messages.
  No guaranteed meteor count or claim of ideal sky conditions is made.
- One coalescing worker computes immutable annual/local results off Qt's UI
  thread and shares the engine's calculation lock. Cache identity includes
  edition data, location and current UTC date. Late results from another
  location/year are discarded; shutdown cancels pending work. No new network
  request, provider, startup splash stage or calculation in a QML getter.

Future years without a downloaded matching edition retain the explicitly
indicative built-in recurrence. The immutable annual overlay affects only meteor
events in Home/Calendar; other ephemerides, optics, NSOM, equipment and planner scoring
are untouched. Non-meteor events retain their original objects and fields.

## Source and licensing boundary

Official source: <https://www.imo.net/> and the annual calendar linked there.
The September 2026 restoration page currently links `ShCal27s.pdf`; the historic
2026 URL currently returns HTML. The user-supplied `ShCal26-0.pdf` is the 2026
IMO edition and was inspected for compatibility. Neither publication is bundled
in NightScope or checked into this repository. Each installation obtains its
own local copy directly from IMO or imports a user-selected original.

The publications remain copyright IMO. Public access is not represented as an
open redistribution licence; no permission to republish the PDF, illustrations
or narrative text is assumed. There is no NightScope mirror or server-side
dataset. The app displays limited numerical facts with explicit IMO attribution.
Any future redistribution of source publications requires a separate rights
review. No login, paid service, trial or other provider is introduced.

PDF text extraction uses `pypdf` and `fonttools` (BSD-3-Clause), lazily in the
worker. Their licences are in the generated third-party archive. Qt PDF was
used only for local visual inspection, not added to application dependencies or
the native bundle.

## Validation

Offline regression fixtures are synthetic PDFs, not copied IMO publications.
Checks cover reuse after restart, rollover, HTTP-200 HTML, wrong years, corrupt
files, partial tables, failed disk writes, exact cleanup scope, offline retries,
manual import, GUI-thread responsiveness, duplicate requests and late results.
The two real editions are additionally checked in an isolated runtime; initial
provider evidence is under `build/imo-20260919/`. Local-window science/parity,
worker, forecast/DST and visual checks are under `build/meteor-windows-20260920/`.
See `TESTING.md` for final gate and Windows artifact results.
