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
  table reference avoids extracting all charts/prose on normal cached reads.
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

Local radiant/Moon/night-window optimisation and extraction of additional peaks
from narrative sections are not implemented. Visibility remains to be checked.
Future years without a downloaded matching edition retain the explicitly
indicative built-in recurrence. The immutable annual overlay affects only meteor
events in Home/Calendar; ephemerides, optics, NSOM, equipment and planner scoring
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
The two real editions are additionally checked in an isolated runtime; evidence
is under `build/imo-20260919/`. See `TESTING.md` for final gate results.
