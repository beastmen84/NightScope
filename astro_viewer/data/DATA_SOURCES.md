# NightScope Local Data Sources

## Cities

`cities15000.txt` is the packaged city seed and should be extracted from the official GeoNames `cities15000.zip` dump:

- tab-delimited UTF-8 text
- fields from the GeoNames `geoname` table
- `name`, `asciiname`, `alternatenames`, WGS84 latitude/longitude, country code, admin codes, population and IANA timezone

NightScope intentionally does not import `allCountries.txt`. Packaged `countryInfo.txt` and `admin1CodesASCII.txt` enrich country/admin names. When the packaged `cities15000.txt` changes, the runtime bootstrap rebuilds the city catalog from that file and records the source size/mtime in `DataImportLog`.

The importer deduplicates translated names into aliases. For example, `Addis Ababa` and `Addis Abeba` are one city record with both search terms.

GeoNames remains packaged for the visible offline city search and for
city/country/region presentation. Its timezone column is retained as source
metadata but is not used by runtime location acquisition; `timezonefinder`
resolves the timezone from the selected city's coordinates. The three packaged
GeoNames files total 8,529,230 bytes. In the current development database,
33,775 cities and 327,374 aliases occupy about 55 MB after SQLite compaction.

GeoNames publishes these dump files under Creative Commons Attribution 4.0
(`CC BY 4.0`) and provides them as-is. The official format and license notice is
`https://download.geonames.org/export/dump/readme.txt`. A public NightScope
artifact must retain the required GeoNames attribution.

## MPC Observatory Codes

`mpc_observatories_seed.csv` is the packaged offline observatory seed generated
from the official Minor Planet Center Observatory Codes API:
`https://data.minorplanetcenter.net/api/obscodes`.

Run the updater only when intentionally refreshing the release snapshot:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_mpc_observatories.py
```

Validate the checked-in snapshot without network access:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_mpc_observatories.py --check
```

The 2026-07-22 snapshot contains 2,683 fixed terrestrial sites. The generator
excludes satellite, roving, geocentric and otherwise non-surface entries. It
preserves the MPC parallax constants and derives WGS84 geodetic latitude and
ellipsoid height; longitudes are normalized to `[-180, 180)`. Runtime bootstrap
imports the seed into `MpcObservatory` and records its file signature in
`DataImportLog`. Search uses the local database only, accepts names and MPC
codes, and resolves the selected timezone offline from the derived coordinates.

MPC states that its database is freely available to the public and provides
attribution guidance at `https://docs.minorplanetcenter.net/mpc-ops-docs/faqs/`.
Public NightScope artifacts retain attribution to the International
Astronomical Union Minor Planet Center in `THIRD_PARTY_NOTICES.md`.

## Coordinate Timezones

NightScope uses `timezonefinder 8.2.5` to map WGS84 latitude/longitude directly
to an IANA timezone without a network request. The dependency packages the full
timezone-boundary dataset, including ocean zones, so timezone resolution does
not depend on the nearest GeoNames city. The Python package code is MIT licensed;
its timezone polygon data is derived from `timezone-boundary-builder` and is
distributed under ODbL 1.0. Project and license details:
`https://pypi.org/project/timezonefinder/8.2.5/`.

The PyInstaller community hook collects the dependency's data files into the
Windows bundle. NightScope keeps one lazy resolver instance. New manual and
Windows locations fall back to the system timezone only if the local polygon
lookup cannot run; a valid timezone returned by the IP provider remains
authoritative.

## Equipment Catalogs

`telescope_catalog_seed.csv`, `eyepiece_catalog_seed.csv`,
`barlow_catalog_seed.csv`, `binocular_catalog_seed.csv`,
`filter_catalog_seed.csv`, `reducer_catalog_seed.csv`,
`astronomy_camera_catalog_seed.csv`, `camera_body_catalog_seed.csv` and
`reducer_telescope_compatibility_seed.csv` are the canonical seed source for
equipment catalogs. Runtime bootstrap reads these CSVs directly; equipment
seed rows are not hardcoded in Python. Every catalogue row owns an explicit,
immutable `seed_key`; reducer-telescope associations reference those keys
directly. Brand, model and technical corrections must retain the existing key
so bootstrap updates the same database row. Rows marked
`Specs encoded in model name` should be checked against the specific regional
product revision before purchase recommendations.

The equipment seeds were audited against manufacturer catalog pages on 2026-06-22. Historical placeholder rows marked `Catalog seed entry` and unresolved `To verify` rows were removed from the packaged seed files.

The visual-filter and focal-reducer additions were checked on 2026-07-13
against current manufacturer catalog pages and manuals. Primary references:

- Astronomik visual filters: `https://www.astronomik.com/en/Visual-Filters/`
- Baader visual filters and Alan Gee telecompressors:
  `https://www.baader-planetarium.com/en/downloads/dl/file/id/1908/baader-planetarium-price-list-04-2026.pdf`
- Lumicon narrow-band filters: `https://www.lumiconinc.com/uses`
- Explore Scientific filters and 0.7x reducer:
  `https://explorescientific.com/`
- Celestron filters and focal reducers:
  `https://www.celestron.com/collections/astronomy-filters` and
  `https://www.celestron.com/blogs/knowledgebase/understanding-focal-reducers`
- Celestron reducer/corrector and EdgeHD reducer product guidance:
  `https://www.celestron.com/products/reducer-corrector` and
  `https://www.celestron.com/products/reducer-lens-7x-edgehd-1100`
- Celestron visual color, neutral-density and polarizing guidance:
  `https://www.celestron.com/blogs/knowledgebase/what-are-the-different-types-of-eyepiece-filters-colored-neutral-density-and-polarizing`
  and
  `https://www.celestron.com/products/variable-polarizing-filter-1-25`
- Optolong visual-filter families:
  `https://www.optolong.com/cms/column/index/id/30.html`
- Starizona SCT reducers and imaging guidance:
  `https://starizona.com/collections/starizona-optics` and
  `https://starizona.com/blogs/tutorials/imaging-with-a-sct`
- William Optics reducer/flattener compatibility:
  `https://support.williamoptics.com/guides/flattener-back-focus-adjustment`
- Sky-Watcher matched ED reducers:
  `https://www.skywatcher.com/series/imaging-accessories/`

The camera catalogues were assembled and reviewed against official manufacturer
specifications on 2026-07-25. The astronomy-camera seed contains 37
representative cooled and uncooled, color and monochrome models from ZWO,
QHYCCD, Player One Astronomy, Atik and SVBONY. The camera-body seed contains 40
mirrorless and DSLR models from Canon, Nikon, Sony, Fujifilm, Panasonic,
OM System, Pentax and Sigma. Every row keeps its exact official product,
manual or specification URL; primary manufacturer collections include:

- ZWO, QHYCCD, Player One Astronomy, Atik and SVBONY:
  `https://www.zwoastro.com/`, `https://www.qhyccd.com/`,
  `https://player-one-astronomy.com/`, `https://www.atik-cameras.com/` and
  `https://www.svbony.com/`
- Canon, Nikon and Sony:
  `https://www.usa.canon.com/cameras/eos`,
  `https://www.nikonusa.com/c/cameras` and
  `https://electronics.sony.com/imaging/interchangeable-lens-cameras/`
- Fujifilm, Panasonic, OM System, Pentax and Sigma:
  `https://www.fujifilm-x.com/global/products/cameras/`,
  `https://shop.panasonic.com/pages/cameras-camcorders`,
  `https://explore.omsystem.com/`,
  `https://us.ricoh-imaging.com/product-category/cameras/` and
  `https://www.sigma-global.com/en/cameras/`

Only stable fields needed by a later imaging engine are modeled: physical
sensor size, pixel pitch or derived pixel pitch, resolution, bit depth, sensor
and shutter type, cooling, frame rate, live view, Bulb support, lens mount and
source URL. The camera-body video tuple records the highest-resolution native
mode and the frame rate available at that same resolution, rather than an
unrelated lower-resolution peak rate. Gain-dependent values such as quantum
efficiency, read noise and full-well capacity remain intentionally deferred
until the imaging engine defines a comparable operating mode. Schema 21 stores
astronomy-camera and camera-body assignments as profile inventory through
dedicated association tables. Those links still have no visual recommendation
consumer and do not alter any observing score, setup choice or ranking.

Telescope mount values are normalized to stable codes covering optical-tube
only, manual/GoTo/PushTo alt-azimuth, manual/tracking equatorial, GoTo fork and
manual/GoTo/PushTo Dobsonian configurations. Legacy seed labels are mapped to
those codes during bootstrap; the historical generic `manuale` value maps to
an explicit unspecified-manual compatibility code. The visual
tracking-capability projection keeps its previous values; the finer taxonomy
is reserved for later imaging logic.

The packaged filter set contains 48 unique visual night-observation products;
eyepiece solar filters are intentionally excluded. Barrel size is not modeled:
the same product is not duplicated for `1.25\"` and `2\"`. Color filters use
explicit classes such as `COLOR_RED` and `COLOR_LIGHT_BLUE`.

Target filter preferences in `catalogue_objects_seed.csv` use primary UHC,
OIII or H-beta classes only where the object-specific visual guidance supports
them. The main cross-checks are Lumicon's visual-use guide
(`https://www.lumiconinc.com/uses`), Astronomik's UHC guidance
(`https://www.astronomik.com/en/Visual-Filters/UHC/`) and NASA's Caldwell object
notes where available. Solar-System preferences keep attenuation/contrast as
the primary recommendation and any color filter as a separate optional level.
The Celestron guidance also limits the yellow-filter suggestion for Uranus and
Neptune to apertures of about `11\"`, represented as `280 mm`. The runtime first
checks the target-specific telescope and its aperture against the complete
filter catalogue, then selects only compatible products assigned to the active
profile. It does not use filters in setup selection, ObserverCapability, score
or NSOM.

Reducer compatibility is model-specific and stored separately from the
reduction factor. Sixteen exact links for dedicated reducers use normalized
`TelescopeModel` IDs; universal or system-level reducers intentionally have no
fabricated model association. The `visual_compatible` and
`imaging_compatible` flags describe intended use. User-created reducers use the
same normalized relation and may select more than one exact telescope model;
the free-text compatibility description is not used for matching.

`catalogue_objects_seed.csv` marks 53 extended targets with
`imaging_reducer_recommended`. The initial selection follows the 53 existing
`WideField` classifications as a conservative photographic opportunity flag.
The manufacturer references above support the general field-enlargement use
case, not a per-target product endorsement, and the flag does not claim that
every optical train will frame the target. Runtime recommendation therefore
still requires the target-specific telescope and an exact imaging-compatible
reducer link. The result is presentation metadata only and does not alter
setup, capability, score or NSOM.

No API keys or vendor-specific private data are included.

## Celestial Object Catalogues

`catalogue_objects_seed.csv` is the canonical source for physical deep-sky
targets. `catalogue_designations_seed.csv` associates each physical `object_id`
with one or more catalogue designations and marks exactly one primary
designation. The current dataset contains 7,585 physical targets: 110 Messier,
109 Caldwell and 7,366 NGC-only objects.

The Caldwell rows use the Astronomical League's Caldwell Program Object List,
whose positions are J2000.0. The imported fields are designation, NGC/IC or
common identifier, constellation, type, right ascension, declination,
magnitude and apparent size. The 109 rows are checked against the catalogue's
official distribution of 46 star clusters, 35 galaxies and 28 nebulae:
`https://www.astroleague.org/caldwell-program-object-list/`.

NASA's Hubble Caldwell overview independently confirms that the catalogue has
109 entries and intentionally excludes Messier objects. Therefore Caldwell
uses distinct `caldwell-C1` through `caldwell-C109` target IDs rather than
inventing overlaps with Messier:
`https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-caldwell-catalog/`.

The repository-only
`sources/openngc-36cb178a0f69dba8bfc03a99c10512831edf1c6b-ngc.csv.gz`
snapshot is a reproducibly compressed copy of OpenNGC's `NGC.csv` at commit
`36cb178a0f69dba8bfc03a99c10512831edf1c6b`. Its uncompressed SHA-256 is
`e4acd595ed13888f888273fc5cb47c7934430a13348a294abdc8879b1d66fef7`.
The offline generator preserves 7,839 usable canonical NGC designations,
excludes the one entry marked non-existent, and resolves them to 7,571 physical
targets. Of these, 205 reuse existing Messier/Caldwell identities and 7,366
create new NGC-only objects. Duplicate codes and compound objects can therefore
attach multiple NGC designations to one `object_id`.

Cross-catalogue identities are read from the explicit NGC references in the
curated object descriptions, so numerals in common names such as `47 Tucanae`
cannot become catalogue codes. An OpenNGC duplicate attached to a curated
target also assigns that identity to its physical source unless the source has
a different explicit curated identity. This keeps NGC 6882/6885 together as
Caldwell C37 while preserving the intentional Caldwell C49/NGC 2239 and
Caldwell C50/NGC 2244 distinction. Existing databases merge the obsolete
NGC-only identity into C37 and retain its user preference unless C37 already
has an explicit preference.

The split is intentional: a secondary designation points to an existing
physical target without creating a second object, a second astronomy
calculation or an inflated physical count. Existing `messier-Mxx` and
`caldwell-Cxx` IDs remain stable for backward compatibility with images,
descriptions and persisted references. NGC-only targets default to disabled
for automatic suggestions and use the explicit `Work in progress` editorial
placeholder; existing curated targets keep their default even when they also
have an NGC designation.

OpenNGC is redistributed under Creative Commons Attribution-ShareAlike 4.0
International. The complete license is in the repository and bundles as
`OPENNGC_LICENSE.txt`; exact provenance is also recorded in
`sources/README.md` and `THIRD_PARTY_NOTICES.md`.

Portable bundles contain the derived runtime catalogue seeds plus the required
OpenNGC license and attribution. They intentionally do not contain the
repository-only compressed source snapshot or its source-maintenance README.

Regenerate or verify the derived seeds without network access:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_ngc_catalogue.py
.\.venv\Scripts\python.exe astro_viewer\tools\update_ngc_catalogue.py --check
```

## Light Pollution

NightScope does not package synthetic city baselines or coordinate-based Bortle
estimates. The former `light_pollution_seed.csv` was retired in `1.32.5` because
its small hand-authored sample could not represent real local sky quality.

Prepared external providers:

- `light_pollution_world_atlas.csv`: optional preprocessed World Atlas / SQM sample grid. Expected columns are `latitude`, `longitude`, `radius_km`, and either `sky_brightness`/`sqm_mag_arcsec2` or `bortle_class`. Optional columns: `limiting_magnitude`, `source`, `confidence`.
- `light_pollution_viirs_samples.csv`: optional preprocessed VIIRS / Black Marble sample grid with the same normalized columns after external preprocessing.

When Earthdata credentials are configured, authorized and connection-verified, the app can query NASA LAADS OPeNDAP for a small NetCDF-4 subset (`.dap.nc4`) of the VIIRS Black Marble `VNP46A3` monthly product around the active location. The runtime query fetches only the local pixel window needed for the current location, reads `AllAngle_Composite_Snow_Free`, `AllAngle_Composite_Snow_Free_Num`, and `AllAngle_Composite_Snow_Free_Quality`, then caches the resulting local sky-quality estimate in `SkyQualityEstimate`.

If Earthdata is not configured and neither a cached VIIRS result nor a real
preprocessed local dataset covers the active coordinates, sky quality is
unavailable. The UI reports Bortle, SQM and naked-eye limiting magnitude as
`n/d`; the backend does not synthesize a light-pollution penalty. Full raster
products still require external preprocessing before packaging. NASA Black
Marble information: `https://blackmarble.gsfc.nasa.gov/`

## Object Images, Descriptions And Curiosities

`object_images_seed.csv` contains an explicit row for the 228 curated targets.
The 219 Messier/Caldwell targets have dedicated local `512 x 512` JPEG cutouts
from the 2MASS, Pan-STARRS1 or SkyMapper scientific surveys, generated through
CDS `hips2fits`. The nine Solar System targets use normalized NASA/JPL
Photojournal PIA images with the exact mission credit and source page. These are
static representative observations, not live phase, orientation or appearance
data. Source URLs, attribution and usage declarations are kept per row and shown
in Object Detail. The full selection and redistribution rules are documented in
`docs/IMAGE_ASSET_POLICY.md`. The three typed local SVG fallbacks remain
defensive compatibility assets and are not used by current target rows.

`object_descriptions_seed.csv` contains NightScope-style descriptions and
separate observing notes for the same 228 curated targets: Sun, Moon, the seven
displayed planets, all 110 Messier entries and all 109 Caldwell entries. The
Sun entry requires a certified full-aperture front-mounted solar filter and
explicitly excludes eyepiece solar filters. Caldwell observing copy is derived
conservatively from the verified catalogue type, coordinates, magnitude and
apparent size; it does not mix in the separate editorial content. Messier
descriptions are derived from the local Messier catalog
attributes and checked against NASA's Hubble Messier Catalog overview
(`https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-messier-catalog/`);
Solar System descriptions are checked against NASA planetary overview pages
such as Uranus (`https://science.nasa.gov/uranus/`) and the NASA Sun facts page
(`https://science.nasa.gov/sun/facts/`).

`object_curiosities_seed.csv` is a separate, source-backed presentation layer
for the same 228 curated targets. Every row contains an object-specific
historical or scientific fact, a visible source label and an HTTPS source URL.
The primary
references are NASA's Hubble Messier and Caldwell catalogues and NASA Solar
System fact pages; objects without a dedicated NASA catalogue page use a
linked Wikipedia article as a secondary factual reference. All 227 distinct
URLs were checked successfully on 2026-07-12. The seed deliberately remains
separate from observing notes and does not participate in NSOM, Equipment or
ranking calculations.

NGC-only targets do not fabricate entries in these three editorial/image
seeds. Their catalogue detail uses a type-specific compatibility image and the
localized `Work in progress` placeholder until individual source-backed content
is added. Once an object has a complete editorial record, presentation derives
the catalogue description and notes from the canonical `short_description` and
`observing_notes`; new prose is not duplicated into the historic catalogue
`descrizione` field.

The required provenance, three-language review, batching, and acceptance gates
for that work are defined in
[`docs/CATALOGUE_EDITORIAL_WORKFLOW.md`](../../docs/CATALOGUE_EDITORIAL_WORKFLOW.md).

`ObjectDescription` and `ObjectCuriosity` rows supplied by these seeds are
managed content (`is_builtin = 1`) and receive editorial corrections during
bootstrap. Description imports performed with `import_object_content.py` are
marked as user content (`is_builtin = 0`) and are preserved by later seed
refreshes.

The source check is repeatable without modifying data:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_curiosity_sources.py --workers 8
```

Source `1.46.0` also freezes the 228-object baseline identity and adds a
network-free audit for canonical fields, EN/ES overlay parity, HTTPS provenance,
accepted batch manifests, duplicate text, and remaining NGC coverage:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py
```

Use the `--batch` option on both audit tools while accepting one bounded
`1.46.x` batch; this limits live URL checks to the evidence being reviewed and
enables near-duplicate screening against the existing corpus.
