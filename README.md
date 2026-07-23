# NightScope

<p align="center">
  <img src="astro_viewer/resources/icons/telescope.svg" width="88" alt="NightScope telescope icon">
</p>

NightScope is a Windows desktop application for planning visual astronomy
sessions. It combines local astronomical calculations, an observer location,
weather and sky-quality data, and the equipment in the active profile to answer
a practical question: **what is worth observing tonight, from here, with this
setup?**

> [!IMPORTANT]
> NightScope is still in pre-release development. The source tree is regularly
> validated; its Italian/English source visual review and source licensing are
> complete. Source version 1.39.0 includes the reviewed Spanish localization,
> the provider/runtime and Earthdata authorization fixes released in 1.34.2,
> the subsequent Italian and English editorial review, and the first
> platform-capability boundary for native Linux support, plus unified offline
> search for GeoNames cities and MPC observatories, plus a persistent Red Night
> Vision interface mode, a non-blocking startup notification for newer stable
> GitHub releases, and XDG-compliant Linux runtime paths. System location now
> uses the existing providers on Windows and GeoClue 2 on Linux; the Windows
> provider order and fallback behavior remain unchanged.
> The published Windows bundle passes automated legal,
> Qt, backend, and QML checks; its packaged visual and live-provider release
> matrices are not complete yet.

Current Windows package:
[NightScope 1.37.0](https://github.com/beastmen84/NightScope/releases/tag/v1.37.0).
Its release notes identify the corresponding source commit and publish the
SHA-256 digest of the portable ZIP.

## What It Does

- Builds a local observing night from sunset to sunrise for the selected
  location and IANA timezone.
- Calculates Sun, Moon, planet, Messier, and Caldwell visibility with Skyfield.
- Produces a short observing plan and target-specific alternatives instead of
  exposing internal raw scores.
- Evaluates every telescope or binocular in the active profile for each target;
  a profile without either instrument uses naked-eye mode.
- Suggests practical telescope, eyepiece, Barlow, filter, and reducer context
  while keeping optical compatibility and recommendation ranking separate.
- Shows annual astronomical events, short-horizon visible ISS passes, and
  multi-night comet windows in one calendar.
- Provides live directional guidance through Sky Compass.
- Stores observation logs and user-maintained equipment locally.
- Includes offline catalogues for 110 Messier objects, 109 Caldwell objects,
  nine Solar System targets, cities, equipment, descriptions, and credited
  scientific images.
- Switches the application and its content between Italian, English, and
  Spanish at runtime.
- Provides a persistent low-luminance red interface for use at the telescope;
  astronomical photographs and plan thumbnails are suppressed in this mode.
- Checks for newer stable releases after startup and links directly to the
  official GitHub download page without downloading or installing anything.

NightScope is a decision-support tool, not a planetarium, telescope-control
system, or substitute for an astronomical atlas.

## How Recommendations Work

The recommendation path combines four distinct layers:

1. **Astronomical geometry**: darkness, altitude, useful observing interval,
   culmination, Moon separation, and Moon illumination.
2. **Local conditions**: forecast cloud cover, humidity, wind, visibility,
   estimated seeing and transparency, plus real sky-background data when
   available.
3. **Observer capability**: active-profile instruments, aperture, focal length,
   eyepieces, Barlows, and whether the target is realistic with the selected
   setup or with the naked eye.
4. **Session context**: timing, target competition, useful duration, data
   completeness, and whether the night is currently recommended, worth
   monitoring, or discouraged.

Internal quality values are implementation details. The UI presents useful
windows, limiting factors, confidence and concrete setup guidance. Missing data
is not replaced with optimistic synthetic values: for example, Bortle and SQM
remain unavailable when NightScope has no real local source.

ISS passes and comet windows deliberately bypass object scoring, Equipment,
Planner, and the NightScope observation model. They are transient calendar
events. Comet brightness is inherently uncertain and is presented as an
estimate rather than a precise promise.

Filters and focal reducers are also presentation guidance only. They do not
change target ranking. Reducer suggestions require an exact, normalized match
to the target-specific telescope and are intended for imaging context.

The full model and its boundaries are documented in
[`docs/CALCULATION_LOGIC.md`](docs/CALCULATION_LOGIC.md) and
[`docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`](docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md).

## Data And Network Use

Most catalogue, timezone, equipment, ephemeris, propagation, and recommendation
work is local. Network access is used only for current or optional external
data.

| Source | Purpose | Account | Location sent |
| --- | --- | --- | --- |
| Open-Meteo | Hourly weather forecast | No | Yes |
| System location (Windows/GeoClue) | OS location | No | Stays in the OS/app |
| GeoNames | Offline city search and labels | No | No |
| Minor Planet Center | Offline MPC observatory search | No | No; packaged snapshot |
| timezonefinder | Offline IANA timezone lookup | No | No |
| CelesTrak | ISS orbital elements | No | No |
| JPL SBDB | Comet orbital elements | No | No |
| NASA Earthdata / LAADS | VIIRS sky background and MAIAC AOD | Optional login | Yes |
| OpenAQ | Local particulate measurements | Optional API key | Yes |
| IP geolocation fallback | Approximate location after explicit user action | No | Public IP is visible to the service |

The localized **Data providers** page includes step-by-step setup guides. For
the Earthdata/LAADS flow used by NightScope, complete every profile field,
including fields marked optional, before testing the connection. First access
may also require LAADS OPeNDAP application authorization followed by a second
connection test.

CelesTrak and JPL downloads provide orbital catalogues; NightScope performs the
location-specific pass and visibility calculations locally. External results
are cached in SQLite with source-specific refresh and staleness rules.

See [`astro_viewer/data/DATA_SOURCES.md`](astro_viewer/data/DATA_SOURCES.md) for
catalogue provenance and [`docs/IMAGE_ASSET_POLICY.md`](docs/IMAGE_ASSET_POLICY.md)
for image attribution and redistribution policy.

## Privacy And Local Files

NightScope does not require a NightScope account. The portable Windows
application keeps its runtime data next to the executable:

- `nightscope.db`: location, profiles, catalogues, caches, and observation log;
- `user_preferences.json`: interface and provider state;
- `location_cache.json`: last location acquisition result; approximate IP
  fallback data is accepted for at most 24 hours and is labelled as cached;
- `logs/`: rotating diagnostic logs.

On Linux, NightScope follows the XDG base-directory contract:

- `~/.local/share/NightScope`: SQLite database and database backup;
- `~/.config/NightScope`: interface and provider preferences;
- `~/.cache/NightScope`: location and NASA AOD caches;
- `~/.local/state/NightScope/logs`: rotating diagnostic logs.

Absolute `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and
`XDG_STATE_HOME` values replace the corresponding defaults. The developer-only
`NIGHTSCOPE_RUNTIME_DIR` override keeps every runtime file together in one
isolated directory for tests and smoke checks.

Exact coordinates are therefore local application data, but they are sent to a
provider when that provider needs a location-specific result, as shown above.
Earthdata passwords and OpenAQ API keys are stored in the Windows credential
vault through `keyring`; they are not written to the SQLite database or JSON
preferences. Diagnostic logs intentionally avoid coordinates and credential
identifiers.

Back up `nightscope.db`, `user_preferences.json`, and `location_cache.json`
before replacing or moving a development build.

## Requirements

- Windows 10 or Windows 11.
- Python 3.12 or newer for source development.
- A writable checkout or extracted portable application directory.

The current application is Windows-focused. Other desktop platforms are not a
tested release target.

## Run From Source

From PowerShell in the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r astro_viewer\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe astro_viewer\main.py
```

On first start NightScope initializes its SQLite database from the packaged
schema and seed files. This can take longer than subsequent starts.

## Validation

Fast validation without coverage:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast
```

Full validation with coverage:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py
```

Include an installed-environment dependency audit:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
```

The standard runner performs dependency consistency, Ruff, bytecode
compilation, one parallel test-suite pass, a backend smoke test, and a QML smoke
test. Security mode additionally runs `pip-audit`. More focused commands and
the latest measured baseline are in [`docs/TESTING.md`](docs/TESTING.md).

## Build For Windows

```powershell
.\packaging\build_windows.ps1
```

PyInstaller writes the portable application to `dist\NightScope`. The build
includes QML, translations, the multilingual manual, catalogue seeds,
scientific images, GeoNames and MPC observatory data, timezone boundary data, and the local JPL
`de421` ephemeris.

The application writes its database, preferences, caches, and logs beside the
executable, so do not run it from a read-only directory. `dist` is intentionally
ignored by Git and must be rebuilt and independently smoke-tested for a release.
Run smoke, visual, and provider tests on a copy of the clean build: launching
NightScope creates local runtime state beside the executable. Before archiving
the untouched release copy, rerun:

```powershell
.\.venv\Scripts\python.exe tools\audit_qt_bundle.py dist\NightScope
```

The audit rejects databases, backups, preferences, caches, or logs left in the
release bundle.

## Project Layout

```text
astro_viewer/
  app/
    astronomy/       Local ephemerides, event and visibility calculations
    database/        SQLite bootstrap, repositories and migrations
    domain/          Observation, equipment and recommendation contracts
    services/        Providers, caches, localization and orchestration
    ui/              QML application and reusable controls
    viewmodels/      QML-facing read models and commands
  data/              Schemas, seeds, GeoNames, MPC sites and local ephemeris data
  resources/         Icons and credited catalogue images
  tests/             Deterministic unit, integration and presentation tests
  translations/      Runtime language packs and compiled Qt catalogues
docs/                 Architecture, model, testing and release documentation
packaging/            PyInstaller spec and Windows build script
tools/                Validation and localization maintenance tools
manuale.html          Self-contained Italian/English/Spanish user manual
```

Architecture details are in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The current release audit and
remaining release work are tracked in
[`docs/RELEASE_CANDIDATE_REVIEW.md`](docs/RELEASE_CANDIDATE_REVIEW.md) and
[`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md).

## Known Limitations

- Local terrain, buildings, trees, horizon masks, and atmospheric extinction
  near the horizon are not modeled.
- Weather, AOD, particulate, and VIIRS availability depends on provider
  coverage, freshness, authorization, and quality gates.
- Comet magnitudes can differ materially from orbital-catalogue estimates.
- Reducer recommendations do not model a complete camera and back-focus train.
- There is no installer, automatic updater, or artifact signature. The current
  portable release publishes its SHA-256 digest.
- The final manual and application visual matrix still requires a human pass on
  the release build.

Never observe the Sun through unfiltered optics. Use only a certified,
full-aperture solar filter mounted securely in front of the instrument. Do not
use eyepiece solar filters.

## Licensing And Attribution

NightScope includes data and images from sources with their own terms and
attribution requirements. In particular, GeoNames data is distributed under
CC BY 4.0, timezone boundary data used by `timezonefinder` is derived from
`timezone-boundary-builder` under ODbL 1.0, and every catalogue image retains
its source and credit metadata. The offline observatory snapshot retains
attribution to the International Astronomical Union Minor Planet Center.

NightScope is Copyright 2026 Davide Marchi and is licensed under the
[Mozilla Public License 2.0](LICENSE). The MPL applies to NightScope source
files; third-party components and packaged data retain their own licenses.

The consolidated notices, exact validated dependency inventory, Qt/PySide
LGPL information, source links, and data attributions are in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt). A public Windows build
must regenerate that inventory, pass the bundle-license audit, and identify its
exact corresponding public source commit.

## Development Status

NightScope is developed as a pre-release application. User-facing changes and
fixes are recorded in [`astro_viewer/CHANGELOG.md`](astro_viewer/CHANGELOG.md);
the README intentionally describes the current product instead of duplicating
the changelog.
