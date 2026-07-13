# NightScope Local Data Sources

## Cities

`cities15000.txt` is the packaged city seed and should be extracted from the official GeoNames `cities15000.zip` dump:

- tab-delimited UTF-8 text
- fields from the GeoNames `geoname` table
- `name`, `asciiname`, `alternatenames`, WGS84 latitude/longitude, country code, admin codes, population and IANA timezone

NightScope intentionally does not import `allCountries.txt`. Packaged `countryInfo.txt` and `admin1CodesASCII.txt` enrich country/admin names. When the packaged `cities15000.txt` changes, the runtime bootstrap rebuilds the city catalog from that file and records the source size/mtime in `DataImportLog`.

The importer deduplicates translated names into aliases. For example, `Addis Ababa` and `Addis Abeba` are one city record with both search terms.

GeoNames publishes dump formats at `https://download.geonames.org/export/dump/readme.txt`.

## Equipment Catalogs

`telescope_catalog_seed.csv`, `eyepiece_catalog_seed.csv`,
`barlow_catalog_seed.csv`, `binocular_catalog_seed.csv`,
`filter_catalog_seed.csv`, `reducer_catalog_seed.csv` and
`reducer_telescope_compatibility_seed.csv` are the canonical seed source for
equipment catalogs. Runtime bootstrap reads these CSVs directly; equipment
seed rows are not hardcoded in Python. Rows marked
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
- Celestron visual color, neutral-density and polarizing guidance:
  `https://www.celestron.com/blogs/knowledgebase/what-are-the-different-types-of-eyepiece-filters-colored-neutral-density-and-polarizing`
  and
  `https://www.celestron.com/products/variable-polarizing-filter-1-25`
- Optolong visual-filter families:
  `https://www.optolong.com/cms/column/index/id/30.html`
- Starizona SCT reducers: `https://starizona.com/collections/starizona-optics`
- William Optics reducer/flattener compatibility:
  `https://support.williamoptics.com/guides/flattener-back-focus-adjustment`
- Sky-Watcher matched ED reducers:
  `https://www.skywatcher.com/series/imaging-accessories/`

The packaged filter set contains 48 unique visual night-observation products;
eyepiece solar filters are intentionally excluded. Barrel size is not modeled:
the same product is not duplicated for `1.25\"` and `2\"`. Color filters use
explicit classes such as `COLOR_RED` and `COLOR_LIGHT_BLUE`; an unrecognized
legacy color can remain `COLOR_UNSPECIFIED` for migration compatibility but is
not a selectable recommendation class.

Target filter preferences in `catalogue_objects_seed.csv` use primary UHC,
OIII or H-beta classes only where the object-specific visual guidance supports
them. The main cross-checks are Lumicon's visual-use guide
(`https://www.lumiconinc.com/uses`), Astronomik's UHC guidance
(`https://www.astronomik.com/en/Visual-Filters/UHC/`) and NASA's Caldwell object
notes where available. Solar-System preferences keep attenuation/contrast as
the primary recommendation and any color filter as a separate optional level.
The runtime matches these classes only against filters in the active profile;
it does not use them in setup selection, ObserverCapability, score or NSOM.

Reducer compatibility is model-specific and stored separately from the
reduction factor. Sixteen exact links for dedicated reducers use normalized
`TelescopeModel` IDs; universal or system-level reducers intentionally have no
fabricated model association. The `visual_compatible` and
`imaging_compatible` flags describe intended use, but reducers still do not
alter recommendations or apply any score.

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

`light_pollution_seed.csv` is a small local lookup dataset for provider plumbing and common cities. It is not a replacement for a real World Atlas or VIIRS raster import.

Prepared external providers:

- `light_pollution_world_atlas.csv`: optional preprocessed World Atlas / SQM sample grid. Expected columns are `latitude`, `longitude`, `radius_km`, and either `sky_brightness`/`sqm_mag_arcsec2` or `bortle_class`. Optional columns: `limiting_magnitude`, `source`, `confidence`.
- `light_pollution_viirs_samples.csv`: optional preprocessed VIIRS / Black Marble sample grid with the same normalized columns after external preprocessing.
- `light_pollution_seed.csv`: packaged NightScope local baseline used only when richer local datasets are absent.
- Offline estimate fallback: used only when no local record matches the active location.

When Earthdata credentials are configured, authorized and connection-verified, the app can query NASA LAADS OPeNDAP for a small NetCDF-4 subset (`.dap.nc4`) of the VIIRS Black Marble `VNP46A3` monthly product around the active location. The runtime query fetches only the local pixel window needed for the current location, reads `AllAngle_Composite_Snow_Free`, `AllAngle_Composite_Snow_Free_Num`, and `AllAngle_Composite_Snow_Free_Quality`, then caches the resulting local sky-quality estimate in `SkyQualityEstimate`.

If Earthdata is not configured, the network is unavailable, NASA does not expose the matching product tile, or the returned subset cannot be parsed, NightScope keeps using the local CSV/cache fallback chain. Full raster products still require external preprocessing before packaging. NASA Black Marble information: `https://blackmarble.gsfc.nasa.gov/`

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
