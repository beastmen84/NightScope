# NightScope Third-Party Notices

NightScope is Copyright 2026 Davide Marchi and is licensed under the Mozilla
Public License 2.0. The complete project license is in `LICENSE`.

Public NightScope source repository:
`https://github.com/beastmen84/NightScope`

The NightScope 1.33.2 Windows executable corresponds to source tag `v1.33.2`
and commit `9c17204f718223e83183367e9ccea078805b5a00`:
`https://github.com/beastmen84/NightScope/tree/v1.33.2`

This notice covers software and data redistributed with the portable Windows
application. `THIRD_PARTY_LICENSES.txt` contains the installed Python component
inventory and the corresponding license and copyright texts. Component names
and trademarks remain the property of their respective owners. Inclusion does
not imply endorsement of NightScope.

## Qt And Qt For Python

NightScope uses unmodified PySide6 Essentials and Addons 6.11.1, shiboken6,
and the Qt 6.11.1 libraries needed by Qt Core, GUI, Widgets, QML, Qt Quick,
Qt Quick Controls, Layouts, Effects, Shapes, Window, and Positioning. Addons is
used for the Qt Positioning system-location adapter. NightScope selects the
`LGPL-3.0-only` open-source licensing option for these components. The complete
GNU GPL 3.0 and LGPL 3.0 texts are reproduced in `THIRD_PARTY_LICENSES.txt`.

The Windows application is distributed as an `onedir` bundle. Qt/PySide DLLs,
plugins, QML modules, and Python extension modules remain separate files under
`_internal/PySide6`; NightScope does not cryptographically lock or verify them.
A recipient may replace those files with compatible, relinked or modified
versions and run `NightScope.exe`. Keep the original relative paths and binary
names when testing a replacement. Reverse engineering for debugging such
modifications is not prohibited by the NightScope license.

Corresponding upstream source and licensing information:

- PySide6/shiboken6 6.11.1 source:
  `https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.1-src/`
- Qt 6.11.1 source:
  `https://download.qt.io/official_releases/qt/6.11/6.11.1/`
- Qt open-source licensing:
  `https://doc.qt.io/qt-6/licensing.html`
- Third-party code used by Qt 6.11:
  `https://doc.qt.io/qt-6/licenses-used-in-qt.html`
- Qt SBOM guidance:
  `https://doc.qt.io/qt-6/sbom.html`

The release build must contain only Qt modules used by NightScope. The final
packaged-build audit must reject unexpected GPL-only Qt modules before public
distribution.

## Python And Python Packages

The frozen application embeds CPython and Python packages resolved from
`astro_viewer/requirements.txt`. Their exact installed versions, declared
licenses, copyright notices, vendored native-library notices, and license texts
are consolidated in `THIRD_PARTY_LICENSES.txt`. The archive also includes the
PyInstaller bootloader terms and exception.

Regenerate and verify the archive in the clean release environment:

```powershell
.\.venv\Scripts\python.exe tools\generate_third_party_licenses.py
.\.venv\Scripts\python.exe tools\generate_third_party_licenses.py --check
```

Because runtime dependency ranges are not yet locked, this checked-in archive
describes the validated environment, not every version that could satisfy the
requirements. The public release must use a locked environment or SBOM and
regenerate this file from that environment.

## Packaged Data

### GeoNames

`cities15000.txt`, `countryInfo.txt`, and `admin1CodesASCII.txt` are derived
from the GeoNames geographical database and are redistributed under Creative
Commons Attribution 4.0 International (`CC-BY-4.0`).

- Source: `https://download.geonames.org/export/dump/`
- License: `https://creativecommons.org/licenses/by/4.0/`
- Attribution: GeoNames, `https://www.geonames.org/`

NightScope packages an unmodified snapshot selected from the upstream export.

### Minor Planet Center Observatory Codes

`mpc_observatories_seed.csv` is a derived offline snapshot of observatory data
made publicly available by the IAU Minor Planet Center. NightScope retains the
MPC code, names, station metadata and parallax constants, derives WGS84
coordinates, and excludes non-fixed or non-terrestrial entries from location
selection.

- Source API: `https://data.minorplanetcenter.net/api/obscodes`
- API documentation: `https://docs.minorplanetcenter.net/mpc-ops-docs/apis/obscodes/`
- Attribution guidance: `https://docs.minorplanetcenter.net/mpc-ops-docs/faqs/`
- Attribution: International Astronomical Union Minor Planet Center

The packaged snapshot was retrieved on 2026-07-22. Searching it at runtime is
offline and does not send the user's query or coordinates to the MPC.

### Timezone Boundaries

The `timezonefinder` package embeds timezone-boundary data distributed under
the Open Data Commons Open Database License 1.0 (`ODbL-1.0`). Its complete
`DATA_LICENSE` text is reproduced in `THIRD_PARTY_LICENSES.txt`.

- Source project: `https://github.com/evansiroky/timezone-boundary-builder`
- Database license: `https://opendatacommons.org/licenses/odbl/1-0/`

### Astronomical Data And Images

NightScope includes the JPL DE421 ephemeris used by Skyfield. Catalogue image
sources and per-object credits are stored with the application data and shown
in the user interface. The deep-sky cutouts retain their CDS/2MASS,
Pan-STARRS1, or SkyMapper attribution and ODbL declaration. Solar System images
retain their NASA/JPL mission credits and source links.

The complete image provenance, redistribution policy, and current NASA/JPL
usage links are documented in `docs/IMAGE_ASSET_POLICY.md`.
