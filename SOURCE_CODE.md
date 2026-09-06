# Source Code Availability

This file accompanies the NightScope 1.46.15 development source. Its intended
release tag is `v1.46.15`, not yet created or published. The planned source URL
`https://github.com/beastmen84/NightScope/tree/v1.46.15` must be verified before
distributing a corresponding binary. The current branch contains the source
and build scripts; no new portable package is claimed here.

The public portable Windows release remains NightScope 1.46.13.
The published Linux package remains version 1.43.0 and carries its own
version-specific source and native-component notices.

## NightScope

NightScope is distributed under the Mozilla Public License 2.0. The complete
corresponding source for the public Windows release is identified by `v1.46.13`:

- Repository: `https://github.com/beastmen84/NightScope`
- Release source: `https://github.com/beastmen84/NightScope/tree/v1.46.13`
- Source archive:
  `https://github.com/beastmen84/NightScope/archive/refs/tags/v1.46.13.tar.gz`

The source tag includes the PyInstaller specifications and scripts used to
produce the portable bundles. The project license is reproduced in `LICENSE`.
The public `v1.46.13` tag points to `b34ec4a85783fde74bd384565aa6e3f0638e00eb`.
Its changes after the validated Windows build source `be30cda` are validation
documentation only; application code and packaged resources are unchanged.

## Qt And Qt For Python

NightScope 1.46.13 uses unmodified PySide6/shiboken6 6.11.2 and Qt 6.11.2 under
the LGPL-3.0-only option. Complete corresponding upstream source is available
without charge from:

- PySide6/shiboken6:
  `https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/`
- Qt:
  `https://download.qt.io/official_releases/qt/6.11/6.11.2/`

Qt/PySide libraries remain separate dynamically loaded files in the portable
bundle. Replacement and relinking instructions are in
`THIRD_PARTY_NOTICES.md`; the complete LGPL and GPL texts are in
`THIRD_PARTY_LICENSES.txt`.

## Linux Native Components

Linux bundles include `LINUX_NATIVE_COMPONENTS.tsv`. Each row identifies a
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
