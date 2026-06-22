# Runtime Database City Cleanup Report

Generated: 2026-06-22T10:58:09
Database: `C:/Users/beast/PycharmProjects/NightScope/astro_viewer/data/nightscope.db`
GeoNames source: `C:/Users/beast/PycharmProjects/NightScope/astro_viewer/data/cities15000.txt`

## Rebuild Approach

- Rebuilt only `City` and `CityAlias` in the runtime database.
- Preserved the existing schema, indexes, and non-city tables.
- Imported `cities15000.txt` with the corrected GeoNames importer.
- Used packaged `countryInfo.txt` and `admin1CodesASCII.txt` to enrich country and admin names.
- Removed context-like and numeric-only administrative aliases from `CityAlias`; context remains available through columns and `search_name`.
- Updated `DataImportLog` and ran `VACUUM` after the rebuild.

## Before / After Statistics

| Metric | Before cleanup | After cleanup |
| --- | --- | --- |
| City rows | 33775 | 33775 |
| CityAlias rows | 327368 | 327368 |
| Average aliases per city | 9.69 | 9.69 |
| Maximum aliases per city | 218 | 218 |
| Context-like aliases | 0 | 0 |
| Country-code aliases | 0 | 0 |
| Country-name aliases | 0 | 0 |
| Admin-region aliases | 0 | 0 |
| Numeric-only aliases | 0 | 0 |
| Empty aliases | 0 | 0 |
| Database size bytes | 55578624 | 55869440 |

## Corrected Import Report

| Metric | Value |
| --- | --- |
| Rows read | 33889 |
| Imported | 33775 |
| Duplicates skipped/merged | 114 |
| Aliases added | 327374 |
| Missing timezone | 0 |
| Rows skipped invalid | 0 |

## Search Verification Before Cleanup

| Query | Returned city | Country | Code | Timezone | Alias count |
| --- | --- | --- | --- | --- | --- |
| Addis | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| Addis Ababa | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| Addis Abeba | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| አዲስ አበባ | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| Roma | Rome | Italy | IT | Europe/Rome | 48 |
| Rome | Rome | Italy | IT | Europe/Rome | 48 |
| Milano | Milan | Italy | IT | Europe/Rome | 35 |
| Milan | Milan | Italy | IT | Europe/Rome | 35 |
| New York | New York City | United States | US | America/New_York | 88 |
| Tokyo | Tokyo | Japan | JP | Asia/Tokyo | 40 |

## Search Verification After Cleanup

| Query | Returned city | Country | Code | Timezone | Alias count |
| --- | --- | --- | --- | --- | --- |
| Addis | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| Addis Ababa | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| Addis Abeba | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| አዲስ አበባ | Addis Ababa | Ethiopia | ET | Africa/Addis_Ababa | 43 |
| Roma | Rome | Italy | IT | Europe/Rome | 48 |
| Rome | Rome | Italy | IT | Europe/Rome | 48 |
| Milano | Milan | Italy | IT | Europe/Rome | 35 |
| Milan | Milan | Italy | IT | Europe/Rome | 35 |
| New York | New York City | United States | US | America/New_York | 88 |
| Tokyo | Tokyo | Japan | JP | Asia/Tokyo | 40 |

## Addis Reverse Lookup

| Field | Value |
| --- | --- |
| City | Addis Ababa |
| Country | Ethiopia |
| Country code | ET |
| Timezone | Africa/Addis_Ababa |
| Distance km | 0.941 |

## Assessment

- The historical runtime database reflected the legacy aggressive merge behavior.
- The rebuilt database removes polluted aliases and restores a city count consistent with the corrected importer.
- Key city searches still resolve to the expected canonical records.
