# NightScope Local Data Sources

## Cities

`cities_seed.csv` is a curated offline seed designed for first-run usability and tolerant search aliases. It follows the GeoNames-style fields used by the import tool:

- city name and ASCII name
- country and country code
- latitude and longitude
- IANA timezone
- optional population
- normalized search aliases

For a full production catalog, use `tools/import_cities.py` with an exported GeoNames-derived CSV. GeoNames publishes dump formats at `https://download.geonames.org/export/dump/readme.txt`.

## Equipment Catalogs

`telescope_catalog_seed.csv`, `eyepiece_catalog_seed.csv`, and `barlow_catalog_seed.csv` are curated from public manufacturer/catalog specifications and model names. Rows marked `To verify` or `Specs encoded in model name` should be checked against the specific regional product revision before purchase recommendations.

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
