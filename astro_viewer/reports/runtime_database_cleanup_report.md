# Runtime Database City Cleanup Report

Generated: 2026-06-21T20:37:51
Database: `C:/Users/beast/PycharmProjects/NightScope/astro_viewer/data/nightscope.db`
GeoNames source: `C:/Users/beast/PycharmProjects/NightScope/astro_viewer/data/cities15000.txt`

## Rebuild Approach

- Rebuilt only `City` and `CityAlias` in the runtime database.
- Preserved the existing schema, indexes, and non-city tables.
- Seeded curated city rows first to preserve canonical names such as Roma and Milano.
- Imported `cities15000.txt` with the corrected GeoNames importer.
- Removed context-like and numeric-only administrative aliases from `CityAlias`; context remains available through columns and `search_name`.
- Updated `DataImportLog` and ran `VACUUM` after the rebuild.

## Before / After Statistics

| Metric | Before cleanup | After cleanup |
| --- | --- | --- |
| City rows | 27704 | 33785 |
| CityAlias rows | 391666 | 327480 |
| Average aliases per city | 14.14 | 9.69 |
| Maximum aliases per city | 539 | 218 |
| Context-like aliases | 82860 | 0 |
| Country-code aliases | 27695 | 0 |
| Country-name aliases | 27588 | 0 |
| Admin-region aliases | 27577 | 0 |
| Numeric-only aliases | 24074 | 0 |
| Empty aliases | 0 | 0 |
| Database size bytes | 61366272 | 53465088 |

## Corrected Import Report

| Metric | Value |
| --- | --- |
| Rows read | 33886 |
| Imported | 33658 |
| Duplicates skipped/merged | 228 |
| Aliases added | 327345 |
| Missing timezone | 0 |
| Rows skipped invalid | 0 |

## Search Verification Before Cleanup

| Query | Returned city | Country | Code | Timezone | Alias count |
| --- | --- | --- | --- | --- | --- |
| Addis | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 50 |
| Addis Ababa | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 50 |
| Addis Abeba | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 50 |
| አዲስ አበባ | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 50 |
| Roma | Roma | Italia | IT | Europe/Rome | 52 |
| Rome | Roma | Italia | IT | Europe/Rome | 52 |
| Milano | Milano | Italia | IT | Europe/Rome | 39 |
| Milan | Milano | Italia | IT | Europe/Rome | 39 |
| New York | New York | Stati Uniti | US | America/New_York | 151 |
| Tokyo | Tokyo | Giappone | JP | Asia/Tokyo | 106 |

## Search Verification After Cleanup

| Query | Returned city | Country | Code | Timezone | Alias count |
| --- | --- | --- | --- | --- | --- |
| Addis | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 43 |
| Addis Ababa | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 43 |
| Addis Abeba | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 43 |
| አዲስ አበባ | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa | 43 |
| Roma | Roma | Italia | IT | Europe/Rome | 48 |
| Rome | Roma | Italia | IT | Europe/Rome | 48 |
| Milano | Milano | Italia | IT | Europe/Rome | 35 |
| Milan | Milano | Italia | IT | Europe/Rome | 35 |
| New York | New York | Stati Uniti | US | America/New_York | 89 |
| Tokyo | Tokyo | Giappone | JP | Asia/Tokyo | 40 |

## Addis Reverse Lookup

| Field | Value |
| --- | --- |
| City | Addis Ababa |
| Country | Etiopia |
| Country code | ET |
| Timezone | Africa/Addis_Ababa |
| Distance km | 0.000 |

## Assessment

- The historical runtime database reflected the legacy aggressive merge behavior.
- The rebuilt database removes polluted aliases and restores a city count consistent with the corrected importer.
- Key city searches still resolve to the expected canonical records.
