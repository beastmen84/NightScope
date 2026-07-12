# NightScope Image Asset Policy

Updated: 2026-07-12

## Scope

NightScope packages one local `512 x 512` RGB JPEG for every selectable target:

- 219 deterministic scientific survey cutouts for Messier and Caldwell;
- 9 representative NASA/JPL observations for the Solar System catalogue.

The assets are not AI-generated reconstructions, screenshots copied from
editorial pages or substitutes for live ephemerides. Solar System images are
static mission products and can use enhanced colour, non-visible wavelengths or
multi-frame processing. They do not represent the current phase, orientation,
solar activity or atmospheric appearance of a target.

All target images use `Image.PreserveAspectFit` in QML. The common square format
fits Home cards and both Object Detail branches without layout-specific files.

## Deep-Sky Sources And Rights

Deep-sky cutouts are generated with the CDS `hips2fits` service from these
public HiPS datasets:

- `CDS/P/2MASS/color`: 200 targets. Survey credit: 2MASS,
  UMass/IPAC-Caltech. The CDS HiPS metadata declares `ODbL-1.0`.
- `CDS/P/PanSTARRS/DR1/color-i-r-g`: 15 northern planetary nebulae and
  supernova remnants that are poorly represented in near-infrared. Survey
  credit: Pan-STARRS1. The CDS HiPS metadata declares `ODbL-1.0`.
- `CDS/P/Skymapper/DR4/color`: 4 southern planetary nebulae. Survey credit:
  SkyMapper Southern Survey DR4. The CDS HiPS metadata declares `ODbL-1.0`.

The 2MASS public-data terms require acknowledgement and identify DSS as the
restricted exception; NightScope does not use DSS imagery. Pan-STARRS and
SkyMapper are public survey releases, while redistributed colour HiPS products
and cutouts retain the CDS attribution and ODbL declaration in their metadata.

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

Every `object_images_seed.csv` target row stores:

- the exact scientific cutout request or official NASA Science source page;
- the survey, mission and processing attribution shown as a clickable credit;
- the applicable dataset license or NASA/JPL media-usage declaration;
- `verified=1` only after local format and content validation.

The three local fallback SVG rows are generic object-type illustrations, are
not presented as target photographs and remain only for defensive compatibility.

## Reproducible Sync

Install development requirements in the project venv, then run:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --workers 8
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
```

Both tools validate dimensions, RGB/JPEG format and nonblank pixel variance,
write each image atomically and update the CSV only after all requested assets
succeed. Existing files are reused while their recorded source URL is unchanged.

The Solar System tool downloads the original PIA JPEG and applies only declared,
deterministic crops plus aspect-preserving resize on a black square canvas. The
Venus crop selects the documented contrast-enhanced panel; the Sun crop excludes
the instrument timestamp. Compact Caldwell planetary nebulae use precise J2000
positions resolved through CDS Sesame/SIMBAD because display coordinates are
intentionally rounded and can exceed a narrow image field.

Do not add or replace an asset unless its redistribution terms and required
credit are recorded in the seed. A visually attractive image without clear
rights is not an acceptable NightScope asset.
