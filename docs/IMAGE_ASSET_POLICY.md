# NightScope Image Asset Policy

Updated: 2026-09-05 (source 1.46.11)

## Scope

NightScope packages a compact family of local `512 x 512` RGB JPEGs:

- 16 shared category illustrations for every deep-sky catalogue;
- 9 representative NASA/JPL observations for the Solar System catalogue.

The category illustrations are AI-generated artwork, explicitly labelled as
such in Italian, English and Spanish. They are **not photographs of the selected
object** or scientifically verified reconstructions. They do not depict its
actual morphology, colour, angular scale, orientation or observing appearance.
Solar System images are
static mission products and can use enhanced colour, non-visible wavelengths or
multi-frame processing. They do not represent the current phase, orientation,
solar activity or atmospheric appearance of a target.

All target images use `Image.PreserveAspectFit` in QML. The common square format
fits Home cards and both Object Detail branches without layout-specific files.

## Shared Deep-Sky Illustrations

`app/services/object_imagery.py` owns the exact mapping from canonical catalogue
types to these families:

- Galaxy and galaxy system (pairs, triplets and groups).
- Open cluster and globular cluster.
- Generic, emission, reflection, dark and planetary nebula.
- Nebula with cluster and supernova remnant.
- Asterism, Milky Way star cloud, star and optical double.
- Neutral unclassified object for unknown or unmapped types.

The same type has the same default for Messier, Caldwell and NGC, independently
of editorial coverage. The illustration set is generated through the built-in
image-generation tool using one style anchor and explicit subject constraints;
the prompt set is recorded in `docs/IMAGE_GENERATION_PROMPTS.md`. No survey
cutout or NASA photograph was used as an input to generate this family.

Artwork metadata has `kind=illustration`, an empty source URL and
`verified=False`; its label cannot be mistaken for a linked observational
source. These presentation decisions never alter the catalogue's type, target
identity, editorial prose, observability or recommendation scores.

The previous 219 CDS/2MASS, Pan-STARRS1 and SkyMapper cutouts are removed from the
source package, along with their downloader. Their original metadata and files
remain recoverable from Git history; they must not be silently reintroduced.

## Solar System Sources And Rights

The normalized Solar System assets come from original NASA Images downloads;
each seed row links the corresponding NASA Science page and carries its exact
mission credit.

| Target | PIA | Representation | Credit |
| --- | --- | --- | --- |
| Sun | `PIA26681` | SDO/AIA 171 angstrom observation; instrument footer excluded by the square crop | NASA/GSFC/Solar Dynamics Observatory |
| Moon | `PIA00405` | Galileo global colour view | NASA/JPL/USGS |
| Mercury | `PIA10189` | MESSENGER visible-infrared colour view | NASA/Johns Hopkins University Applied Physics Laboratory/Carnegie Institution of Washington |
| Venus | `PIA23791` | Mariner 10 contrast-enhanced cloud view, Figure B | NASA/JPL-Caltech |
| Mars | `PIA00407` | Viking global colour mosaic | NASA/JPL/USGS |
| Jupiter | `PIA04866` | Cassini true-colour mosaic | NASA/JPL/Space Science Institute |
| Saturn | `PIA11141` | Cassini portrait with the ring system | NASA/JPL/Space Science Institute |
| Uranus | `PIA18182` | Voyager 2 full-disk view | NASA/JPL-Caltech |
| Neptune | `PIA01492` | Voyager 2 green/orange-filter full-disk composite | NASA/JPL |

NASA states that its content generally may be used for educational or
informational purposes with acknowledgement, subject to identified third-party
rights and without implying endorsement. JPL likewise requires the displayed
credit and a check for any separately identified owner. NightScope therefore
records the source and exact credit instead of applying a blanket public-domain
claim. Current policies:

- `https://www.nasa.gov/nasa-brand-center/images-and-media/`
- `https://www.jpl.nasa.gov/jpl-image-use-policy/`

## Seed Contract

`object_images_seed.csv` contains only the nine Solar System records. Each stores:

- the official NASA Science source page;
- the mission and processing attribution shown as a clickable credit;
- the NASA/JPL media-usage declaration;
- `verified=1` only after local format and content validation.

Category defaults are resolved in code, not copied into thousands of database
rows. Schema version 26 removes known retired image records only when their
object ID, exact distributed path and legacy license match together. Existing
custom paths or licenses are preserved, as are records outside the exact 219
retired target identities (matching a catalogue prefix is not enough).
The three old fallback seed rows
are also retired; tiny legacy SVGs still used by engine/mock fixtures are not
the default image policy of the real catalogue UI.

Personal-image import and complete backup/restore are subsequent versioned
steps; see `docs/OBJECT_IMAGERY_ROADMAP.md`. This first stage does not claim that
the upload UI already exists.

## Validation And Maintenance

Install development requirements in the project venv, then run:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\check_object_images.py
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
```

The read-only image check is part of the standard source gate. It validates
the seed identities, every catalogue type, the exact category file inventory,
dimensions, RGB/JPEG format, nonblank pixels and absence of retired cutouts.
The SHA-256 manifest in `docs/IMAGE_ASSET_MANIFEST.json` ties the installed
category assets to the reviewed outputs. Regression tests enforce a compact
asset budget and reject corrupted, missing, extra, misclassified, incorrectly
formatted or unexpectedly changed resources and inconsistent manifests.

The 16 category JPEGs occupy 614,168 bytes; the unchanged nine Solar System
JPEGs occupy 293,230 bytes. Replacing the old 15,235,688-byte deep-sky set saves
14,621,520 bytes of source/bundled image data. This is an asset-size comparison,
not a measurement of a newly built executable or compressed release archive.

The Solar System tool downloads the original PIA JPEG and applies only declared,
deterministic crops plus aspect-preserving resize on a black square canvas. The
Venus crop selects the documented contrast-enhanced panel; the Sun crop excludes
the instrument timestamp. This tool updates only Solar System records, and its
`--check` mode performs no downloads or writes. No per-NGC image download is
part of initialization or catalogue maintenance.

Keep photographic source credits in the seed and generated-art provenance in
the prompt record. Do not relabel generated artwork as scientific imagery.

## Loading And Night Vision

Startup reads image associations and metadata, not all pixel data. Home and
Object Detail load their visible images asynchronously with bounded QML source
sizes and aspect-preserving display. In Red Night Vision, both pictures and
credits are hidden and image sources become empty, preserving the existing
no-bright-picture/no-image-loading contract.
