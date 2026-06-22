# GeoNames Import Quality Report

Generated: 2026-06-22T10:58:55
Database: `astro_viewer/data/nightscope.db`

## Summary

| Metric | Value |
| --- | --- |
| City rows | 33775 |
| CityAlias rows | 327368 |
| Average aliases per city | 9.69 |
| Maximum aliases for one city | 218 |
| Context-like alias pollution | 0 |
| Country-code aliases | 0 |
| Country-name aliases | 0 |
| Admin-region aliases | 0 |
| Numeric-only aliases | 0 |
| Empty aliases | 0 |

Interpretation: the runtime database reflects the packaged GeoNames source files. `CityAlias` contains city names and alternate city names; country, country-code, admin-region and numeric-only administrative aliases are kept out of alias rows.

## GeoNames Import Log

| Source | Size | Imported at | Rows read | Imported | Merged | Aliases added | Missing TZ | Post-clean removed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cities15000.txt | 8345980 | 2026-06-22T10:58:00 | 33889 | 33775 | 114 | 327374 | 0 | 6 |

## Packaged GeoNames Enrichment

| File | Size | MTime |
| --- | --- | --- |
| countryInfo.txt | 31678 | 2026-06-22T10:50:34 |
| admin1CodesASCII.txt | 151572 | 2026-06-22T10:51:05 |

## Top 20 Cities By Alias Count

| City ID | City | Country | Code | Timezone | Aliases |
| --- | --- | --- | --- | --- | --- |
| 177160 | Jerusalem | Israel | IL | Asia/Jerusalem | 218 |
| 178192 | New Delhi | India | IN | Asia/Kolkata | 118 |
| 192236 | Donetsk | Ukraine | UA | Europe/Kyiv | 113 |
| 195200 | Los Angeles | United States | US | America/Los_Angeles | 102 |
| 169797 | Beijing | China | CN | Asia/Shanghai | 101 |
| 175293 | London | United Kingdom | GB | Europe/London | 101 |
| 169604 | Guangzhou | China | CN | Asia/Shanghai | 98 |
| 196903 | Cape Town | South Africa | ZA | Africa/Johannesburg | 96 |
| 168626 | Ürümqi | China | CN | Asia/Urumqi | 96 |
| 173098 | Alexandria | Egypt | EG | Africa/Cairo | 95 |
| 190497 | Mogadishu | Somalia | SO | Africa/Mogadishu | 94 |
| 172802 | Algiers | Algeria | DZ | Africa/Algiers | 92 |
| 190646 | Damascus | Syria | SY | Asia/Damascus | 91 |
| 192165 | Kyiv | Ukraine | UA | Europe/Kyiv | 90 |
| 174440 | Paris | France | FR | Europe/Paris | 90 |
| 194631 | New York City | United States | US | America/New_York | 88 |
| 193052 | New Orleans | United States | US | America/Chicago | 88 |
| 189072 | Saint Petersburg | Russia | RU | Europe/Moscow | 87 |
| 194922 | Milwaukee | United States | US | America/Chicago | 87 |
| 194077 | Agawam | United States | US | America/New_York | 87 |

## Key Search Verification

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
