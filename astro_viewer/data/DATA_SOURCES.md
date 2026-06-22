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

- World Atlas style local raster/CSV lookup
- NASA/VIIRS Black Marble style local tiles/CSV lookup
- Offline estimate fallback

NASA Black Marble information: `https://blackmarble.gsfc.nasa.gov/`

## Object Images And Descriptions

`object_images_seed.csv` uses local NightScope-generated SVG assets or local placeholders unless a source URL and license are explicitly provided. This avoids shipping unverified image assets.

`object_descriptions_seed.csv` contains concise observing notes for the Moon, planets, and the first 31 Messier entries. Remaining Messier objects still use the base Messier catalog text until richer content is imported.
