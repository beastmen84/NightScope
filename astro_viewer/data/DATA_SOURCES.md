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

`telescope_catalog_seed.csv`, `eyepiece_catalog_seed.csv`, and `barlow_catalog_seed.csv` are the canonical seed source for equipment catalogs. Runtime bootstrap reads these CSVs directly; equipment seed rows are not hardcoded in Python. Rows marked `Specs encoded in model name` should be checked against the specific regional product revision before purchase recommendations.

The equipment seeds were audited against manufacturer catalog pages on 2026-06-22. Historical placeholder rows marked `Catalog seed entry` and unresolved `To verify` rows were removed from the packaged seed files.

No API keys or vendor-specific private data are included.

## Light Pollution

`light_pollution_seed.csv` is a small local lookup dataset for provider plumbing and common cities. It is not a replacement for a real World Atlas or VIIRS raster import.

Prepared external providers:

- `light_pollution_world_atlas.csv`: optional preprocessed World Atlas / SQM sample grid. Expected columns are `latitude`, `longitude`, `radius_km`, and either `sky_brightness`/`sqm_mag_arcsec2` or `bortle_class`. Optional columns: `limiting_magnitude`, `source`, `confidence`.
- `light_pollution_viirs_samples.csv`: optional preprocessed VIIRS / Black Marble sample grid with the same normalized columns after external preprocessing.
- `light_pollution_seed.csv`: packaged NightScope local baseline used only when richer local datasets are absent.
- Offline estimate fallback: used only when no local record matches the active location.

When Earthdata credentials are configured, authorized and connection-verified, the app can query NASA LAADS OPeNDAP for a small NetCDF-4 subset (`.dap.nc4`) of the VIIRS Black Marble `VNP46A3` monthly product around the active location. The runtime query fetches only the local pixel window needed for the current location, reads `AllAngle_Composite_Snow_Free`, `AllAngle_Composite_Snow_Free_Num`, and `AllAngle_Composite_Snow_Free_Quality`, then caches the resulting local sky-quality estimate in `SkyQualityEstimate`.

If Earthdata is not configured, the network is unavailable, NASA does not expose the matching product tile, or the returned subset cannot be parsed, NightScope keeps using the local CSV/cache fallback chain. Full raster products still require external preprocessing before packaging. NASA Black Marble information: `https://blackmarble.gsfc.nasa.gov/`

## Object Images And Descriptions

`object_images_seed.csv` uses local NightScope-generated SVG assets or local placeholders unless a source URL and license are explicitly provided. This avoids shipping unverified image assets.

`object_descriptions_seed.csv` contains NightScope-style narrative descriptions and separate observing notes for the Moon, planets, and all 110 Messier entries. Rows are kept deliberately similar in length to avoid detail-page layout imbalance. Messier descriptions are derived from the local Messier catalog attributes and checked against NASA's Hubble Messier Catalog overview (`https://science.nasa.gov/mission/hubble/science/explore-the-night-sky/hubble-messier-catalog/`); Solar System descriptions are checked against NASA planetary overview pages such as Uranus (`https://science.nasa.gov/uranus/`).
