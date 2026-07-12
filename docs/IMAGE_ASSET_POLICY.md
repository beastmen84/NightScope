# NightScope Image Asset Policy

Updated: 2026-07-12

## Scope

NightScope packages one local `512 x 512` RGB JPEG for each of the 219 Messier
and Caldwell targets. The files are deterministic scientific survey cutouts,
not illustrations, AI-generated reconstructions or screenshots copied from
third-party editorial pages. Solar System SVG assets remain local NightScope
artwork.

All catalogue images use `Image.PreserveAspectFit` in QML. A single square
format therefore fits the existing Home cards and both Object Detail branches
without cropping or layout-specific variants.

## Sources And Rights

The cutouts are generated with the CDS `hips2fits` service from these public
HiPS datasets:

- `CDS/P/2MASS/color`: 200 targets. Survey credit: 2MASS,
  UMass/IPAC-Caltech. The CDS HiPS metadata declares `ODbL-1.0`.
- `CDS/P/PanSTARRS/DR1/color-i-r-g`: 15 northern planetary nebulae and
  supernova remnants that are poorly represented in near-infrared. Survey
  credit: Pan-STARRS1. The CDS HiPS metadata declares `ODbL-1.0`.
- `CDS/P/Skymapper/DR4/color`: 4 southern planetary nebulae. Survey credit:
  SkyMapper Southern Survey DR4. The CDS HiPS metadata declares `ODbL-1.0`.

The 2MASS public-data terms require acknowledgement and identify DSS as the
restricted exception; NightScope does not use DSS imagery. Pan-STARRS and
SkyMapper are public survey releases, while the redistributed colour HiPS
products and cutouts retain the CDS attribution and ODbL declaration shown in
their metadata.

Every `object_images_seed.csv` row stores:

- the exact `hips2fits` request URL, including survey, coordinates and field;
- the survey and CDS attribution shown as a clickable credit in Object Detail;
- the applicable survey/HiPS license declaration;
- `verified=1` only after local format and content validation.

The three local fallback SVG rows are not presented as target photographs and
remain available only for defensive compatibility.

## Reproducible Sync

Install development requirements in the project venv, then run:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --workers 8
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --check
```

The sync validates dimensions, RGB/JPEG format and nonblank pixel variance,
writes each image atomically, and updates the CSV only after every target has
succeeded. Existing files are reused when their recorded source URL is
unchanged. Compact Caldwell planetary nebulae use precise J2000 positions
resolved through CDS Sesame/SIMBAD because the display coordinates in the
catalogue are intentionally rounded and can exceed a narrow image field.

Do not add or replace an asset unless its redistribution terms and required
credit are recorded in the seed. A visually attractive image without clear
rights is not an acceptable catalogue asset.
