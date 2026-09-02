# Source Code Availability

This file is prepared for the NightScope 1.45.8 portable release bundles.

## NightScope

NightScope is distributed under the Mozilla Public License 2.0. The complete
corresponding source for these bundles is identified by the `v1.45.8` tag:

- Repository: `https://github.com/beastmen84/NightScope`
- Release source: `https://github.com/beastmen84/NightScope/tree/v1.45.8`
- Source archive:
  `https://github.com/beastmen84/NightScope/archive/refs/tags/v1.45.8.tar.gz`

The source tag includes the PyInstaller specifications and scripts used to
produce the portable bundles. The project license is reproduced in `LICENSE`.
The bundles must not be published until the tag and both source links above are
publicly reachable.

## Qt And Qt For Python

NightScope 1.45.8 uses unmodified PySide6/shiboken6 6.11.1 and Qt 6.11.1 under
the LGPL-3.0-only option. Complete corresponding upstream source is available
without charge from:

- PySide6/shiboken6:
  `https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.1-src/`
- Qt:
  `https://download.qt.io/official_releases/qt/6.11/6.11.1/`

Qt/PySide libraries remain separate dynamically loaded files in the portable
bundle. Replacement and relinking instructions are in
`THIRD_PARTY_NOTICES.md`; the complete LGPL and GPL texts are in
`THIRD_PARTY_LICENSES.txt`.

## Linux Native Components

The Linux bundle includes `LINUX_NATIVE_COMPONENTS.tsv`. Each row identifies a
bundled ELF file, its SHA-256 digest, the exact Debian or Ubuntu binary and
source package versions, its bundled copyright notice, and the exact Debian
Sources or Launchpad source-package page. Components supplied by the
python.org build image instead identify the exact CPython source archive. The
corresponding notices and all Debian/Ubuntu common-license texts they reference
are under `legal/linux-native`.

On a Debian or Ubuntu system with source repositories enabled, install
`dpkg-dev` and retrieve the same source package with:

```bash
sudo apt install dpkg-dev
apt-get source SOURCE_PACKAGE=SOURCE_VERSION
```

Use the exact source package name and version recorded in
`LINUX_NATIVE_COMPONENTS.tsv`.
