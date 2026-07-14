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
`filter_catalog_seed.csv`, `reducer_catalog_seed.csv` and
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
designation. The current dataset contains 110 Messier and 109 Caldwell targets.

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

The split is intentional: a future secondary designation can point to an
existing physical target without creating a second object, a second astronomy
calculation or an inflated catalogue count. Existing `messier-Mxx` IDs remain
stable for backward compatibility with images, descriptions and persisted
references.

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

`object_images_seed.csv` contains an explicit row for all 228 selectable targets.
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
separate observing notes for all 228 selectable targets: Sun, Moon, the seven
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
for the same 228 selectable targets. Every row contains an object-specific
historical or scientific fact, a visible source label and an HTTPS source URL.
The primary
references are NASA's Hubble Messier and Caldwell catalogues and NASA Solar
System fact pages; objects without a dedicated NASA catalogue page use a
linked Wikipedia article as a secondary factual reference. All 227 distinct
URLs were checked successfully on 2026-07-12. The seed deliberately remains
separate from observing notes and does not participate in NSOM, Equipment or
ranking calculations.

`ObjectDescription` and `ObjectCuriosity` rows supplied by these seeds are
managed content (`is_builtin = 1`) and receive editorial corrections during
bootstrap. Description imports performed with `import_object_content.py` are
marked as user content (`is_builtin = 0`) and are preserved by later seed
refreshes.

The source check is repeatable without modifying data:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_curiosity_sources.py --workers 8
```
