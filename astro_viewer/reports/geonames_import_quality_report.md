# GeoNames Import Quality Report

Generated: 2026-06-21T20:39:14
Database: `astro_viewer/data/nightscope.db`

## Summary

| Metric | Value |
| --- | --- |
| City rows | 33785 |
| CityAlias rows | 327480 |
| Average aliases per city | 9.69 |
| Maximum aliases for one city | 218 |
| Context-like alias pollution | 0 |
| Country-code aliases | 0 |
| Country-name aliases | 0 |
| Admin-region aliases | 0 |
| Numeric-only aliases | 0 |
| Empty aliases | 0 |

Interpretation: the runtime database now reflects the corrected importer. `CityAlias` contains city names and alternate city names; country, country-code, admin-region and numeric-only administrative aliases have been removed from alias rows.

## GeoNames Import Log

| Source | Size | Imported at | Rows read | Imported | Merged | Aliases added | Missing TZ | Post-clean removed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cities15000.txt | 8344639 | 2026-06-21T20:37:40 | 33886 | 33658 | 228 | 327345 | 0 | 1 |

## Top 20 Cities By Alias Count

| City ID | City | Country | Code | Timezone | Aliases |
| --- | --- | --- | --- | --- | --- |
| 28289 | Jerusalem | Israele | IL | Asia/Jerusalem | 218 |
| 28282 | New Delhi | India | IN | Asia/Kolkata | 118 |
| 57146 | Donetsk | UA | UA | Europe/Kyiv | 113 |
| 28251 | Los Angeles | Stati Uniti | US | America/Los_Angeles | 102 |
| 28272 | Beijing | Cina | CN | Asia/Shanghai | 101 |
| 28221 | London | Regno Unito | GB | Europe/London | 101 |
| 34606 | Guangzhou | CN | CN | Asia/Shanghai | 98 |
| 28207 | Cape Town | Sudafrica | ZA | Africa/Johannesburg | 96 |
| 33629 | Ürümqi | CN | CN | Asia/Urumqi | 96 |
| 38092 | Alexandria | EG | EG | Africa/Cairo | 95 |
| 55413 | Mogadishu | SO | SO | Africa/Mogadishu | 94 |
| 28211 | Algiers | Algeria | DZ | Africa/Algiers | 92 |
| 55562 | Damascus | SY | SY | Asia/Damascus | 91 |
| 28247 | Kyiv | Ucraina | UA | Europe/Kyiv | 90 |
| 28220 | Paris | Francia | FR | Europe/Paris | 90 |
| 28250 | New York | Stati Uniti | US | America/New_York | 89 |
| 57960 | New Orleans | US | US | America/Chicago | 88 |
| 53993 | Saint Petersburg | RU | RU | Europe/Moscow | 88 |
| 58984 | Agawam | US | US | America/New_York | 87 |
| 59828 | Milwaukee | US | US | America/Chicago | 87 |

## Key Search Verification

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

## Addis Ababa Inspection

Canonical row:

| Field | Value |
| --- | --- |
| id | 28197 |
| city_name | Addis Ababa |
| country | Etiopia |
| latitude | 9.03 |
| longitude | 38.74 |
| timezone | Africa/Addis_Ababa |
| ascii_name | Addis Ababa |
| country_code | ET |
| admin_region | Addis Ababa |
| population | 3860000 |
| search_name | a di si a bei ba add addis ababa addis abaeba addis abbaba addis abeba addis abebae addisa ababa addisaaba addisz abeba adis ababa adis abeba adis abebo adisa ababa adisabeba adiseuababa adisuabeba adys ababa adys abeba antis ampempa atis apapa et etiopia finfinne neanthopolis tungga əddis əbəbə αντις αμπεμπα аддис абебæ аддис абеба адис абеба адыс абеба ադիս աբեբա ատիս ապապա אדיס אבבה اديس ابابا ادیس ابابا يەددىس يەبىبە अदिस अबाबा আদদিস আবাবা ადის აბება 아디스아바바 አዲስ አበባ アティスアヘハ 阿迪斯阿貝巴 |

Addis-related City rows found: 3

| ID | City | ASCII | Country | Code | Timezone |
| --- | --- | --- | --- | --- | --- |
| 28197 | Addis Ababa | Addis Ababa | Etiopia | ET | Africa/Addis_Ababa |
| 58401 | Addison | Addison | US | US | America/Chicago |
| 58760 | Addison | Addison | US | US | America/Chicago |

Alias rows attached to canonical Addis row: 43

| Alias | Normalized | Source |
| --- | --- | --- |
| a di si a bei ba | a di si a bei ba | geonames |
| ADD | add | geonames |
| Addis Ababa | addis ababa | seed |
| Addis Abaeba | addis abaeba | geonames |
| Addis Abbaba | addis abbaba | geonames |
| Addis Abeba | addis abeba | geonames |
| Addis-Abebae | addis abebae | geonames |
| addisa ababa | addisa ababa | geonames |
| Addisaaba | addisaaba | geonames |
| Addisz-Abeba | addisz abeba | geonames |
| Adis Ababa | adis ababa | geonames |
| Adis Abeba | adis abeba | geonames |
| Adis-Abebo | adis abebo | geonames |
| adisa ababa | adisa ababa | geonames |
| Adisabeba | adisabeba | geonames |
| adiseuababa | adiseuababa | geonames |
| adisuabeba | adisuabeba | geonames |
| adys ababa | adys ababa | geonames |
| Adys-Abeba | adys abeba | geonames |
| Antis Ampempa | antis ampempa | geonames |
| Atis Apapa | atis apapa | geonames |
| Finfinne | finfinne | geonames |
| Neanthopolis | neanthopolis | geonames |
| Tungga | tungga | geonames |
| Əddis-Əbəbə | əddis əbəbə | geonames |
| Αντίς Αμπέμπα | αντις αμπεμπα | geonames |
| Аддис-Абебæ | аддис абебæ | geonames |
| Аддис-Абеба | аддис абеба | geonames |
| Адис Абеба | адис абеба | geonames |
| Адыс-Абеба | адыс абеба | geonames |
| Ադիս Աբեբա | ադիս աբեբա | geonames |
| Ատիս Ապապա | ատիս ապապա | geonames |
| אדיס אבבה | אדיס אבבה | geonames |
| أديس أبابا | اديس ابابا | geonames |
| آدیس آبابا | ادیس ابابا | geonames |
| ئەددىس -ئەبىبە | يەددىس يەبىبە | geonames |
| अदिस अबाबा | अदिस अबाबा | geonames |
| আদ্দিস আবাবা | আদদিস আবাবা | geonames |
| ადის-აბება | ადის აბება | geonames |
| 아디스아바바 | 아디스아바바 | geonames |
| አዲስ አበባ | አዲስ አበባ | geonames |
| アディスアベバ | アティスアヘハ | geonames |
| 阿迪斯阿貝巴 | 阿迪斯阿貝巴 | geonames |

## Suspicious Alias Checks

### Duplicate Aliases Across Multiple Cities

| Normalized alias | Cities | Rows | Sample cities |
| --- | --- | --- | --- |
| santa cruz | 21 | 21 | Santa Cruz de la Sierra (BO, America/La_Paz); Reriutaba (BR, America/Fortaleza); Santa Cruz (BR, America/Fortaleza); Santa Cruz Cabrália (BR, America/Bahia); Santa Cruz do Capibaribe (BR, America/Recife); Santa Cruz do Sul (BR, America/Sao_Paulo); Santa Cruz (CL, America/Santiago); Santa Cruz de Tenerife (ES, Atlantic/Canary) |
| victoria | 17 | 17 | Victoria (AR, America/Argentina/Cordoba); Vitória (BR, America/Sao_Paulo); Vitória de Santo Antão (BR, America/Recife); Victoria (CA, America/Vancouver); Victoria (CL, America/Santiago); Limbe (CM, Africa/Douala); Las Tunas (CU, America/Havana); Hong Kong (HK, Asia/Hong_Kong) |
| san pedro | 16 | 16 | San Pedro (AR, America/Argentina/Buenos_Aires); San Pedro (AR, America/Argentina/Cordoba); São Pedro do Sul (BR, America/Sao_Paulo); San Pedro (BZ, America/Belize); San-Pédro (CI, Africa/Abidjan); San Pedro (CR, America/Costa_Rica); San Pedro Alcántara (ES, Europe/Madrid); San Pedro Sacatepéquez (GT, America/Guatemala) |
| santa rosa | 15 | 15 | Santa Rosa (AR, America/Argentina/Salta); Iturama (BR, America/Sao_Paulo); Santa Rosa (BR, America/Sao_Paulo); Santa Rosa de Viterbo (BR, America/Sao_Paulo); Santa Rosa (CO, America/Bogota); Santa Rosa de Cabal (CO, America/Bogota); Santa Rosa de Osos (CO, America/Bogota); Santa Rosa (EC, America/Guayaquil) |
| santiago | 15 | 15 | Santiago (BR, America/Sao_Paulo); Santiago (CL, America/Santiago); Santiago de Cuba (CU, America/Havana); Santiago de los Caballeros (DO, America/Santo_Domingo); Santiago de Compostela (ES, Europe/Madrid); Santiago Atitlán (GT, America/Guatemala); Santiago Sacatepéquez (GT, America/Guatemala); Santiago (MX, America/Monterrey) |
| aebura | 14 | 14 | Yverdon-les-Bains (CH, Europe/Zurich); Olomouc (CZ, Europe/Prague); Aïn Temouchent (DZ, Africa/Algiers); Alcalá la Real (ES, Europe/Madrid); Talavera de la Reina (ES, Europe/Madrid); Ávila (ES, Europe/Madrid); Évreux (FR, Europe/Paris); Edinburgh (GB, Europe/London) |
| san antonio | 12 | 12 | Soyo (AO, Africa/Luanda); Santo Antônio do Sudoeste (BR, America/Sao_Paulo); San Antonio (CL, America/Santiago); San Antonio de los Baños (CU, America/Havana); Sant Antoni de Portmany (ES, Europe/Madrid); Villa de San Antonio (HN, America/Tegucigalpa); San Antonio (PE, America/Lima); San Antonio (PH, Asia/Manila) |
| san fernando | 11 | 11 | San Fernando (ES, Europe/Madrid); San Fernando (MX, America/Monterrey); San Fernando (PE, America/Lima); San Fernando (PH, Asia/Manila); San Fernando (PH, Asia/Manila); San Fernando (PH, Asia/Manila); San Fernando (TT, America/Port_of_Spain); Florissant (US, America/Chicago) |
| san juan | 11 | 11 | San Juan (AR, America/Argentina/San_Juan); San Juan Nepomuceno (CO, America/Bogota); San Juan de Urabá (CO, America/Bogota); San Juan (CR, America/Costa_Rica); San Juan de la Maguana (DO, America/Santo_Domingo); Poio (ES, Europe/Madrid); San Juan (PE, America/Lima); San Juan (PH, Asia/Manila) |
| san luis | 11 | 11 | San Luis (AR, America/Argentina/San_Luis); São Luís (BR, America/Fortaleza); San Luis (CU, America/Havana); San Luis Jilotepeque (GT, America/Guatemala); San Luis (HN, America/Tegucigalpa); Huamantla (MX, America/Mexico_City); San Luis Potosí (MX, America/Monterrey); San Luis Río Colorado (MX, America/Hermosillo) |
| santa maria | 11 | 11 | Santa Maria (BR, America/Sao_Paulo); Santa Maria (BR, America/Sao_Paulo); Santa Maria da Vitória (BR, America/Bahia); Santa Maria do Pará (BR, America/Belem); Oleiros (ES, Europe/Madrid); Teo (ES, Europe/Madrid); Santa María de Jesús (GT, America/Guatemala); Oaxaca (MX, America/Mexico_City) |
| middletown | 10 | 10 | Athens (US, America/New_York); Fairmont (US, America/New_York); Long Island City (US, America/New_York); Middletown (US, America/New_York); Middletown (US, America/New_York); Middletown (US, America/New_York); Middletown (US, America/New_York); Middletown (US, America/New_York) |
| richmond | 10 | 10 | Richmond (AU, Australia/Melbourne); Richmond (CA, America/Vancouver); Richmond (GB, Europe/London); Richmond (NZ, Pacific/Auckland); Port Richmond (US, America/New_York); Richmond (US, America/Indiana/Indianapolis); Richmond (US, America/New_York); Richmond (US, America/New_York) |
| rosario | 10 | 10 | Rosario (AR, America/Argentina/Cordoba); Ibatiba (BR, America/Sao_Paulo); Rosário (BR, America/Fortaleza); Rosário do Sul (BR, America/Sao_Paulo); Villa del Rosario (CO, America/Bogota); El Rosario (HN, America/Tegucigalpa); El Rosario (MX, America/Mazatlan); Rosarito (MX, America/Tijuana) |
| san miguel | 10 | 10 | San Miguel (AR, America/Argentina/Buenos_Aires); San Miguel (CR, America/Costa_Rica); San Miguel Coatlinchán (MX, America/Mexico_City); San Miguel el Alto (MX, America/Mexico_City); San Miguelito (PA, America/Panama); San Miguel (PE, America/Lima); San Miguel (PH, Asia/Manila); San Miguel (PH, Asia/Manila) |
| santa barbara | 10 | 10 | Bituruna (BR, America/Sao_Paulo); Santa Bárbara (BR, America/Sao_Paulo); Santa Bárbara (BR, America/Bahia); Timbiquí (CO, America/Bogota); Poptún (GT, America/Guatemala); Santa Bárbara (GT, America/Guatemala); Santa Bárbara (HN, America/Tegucigalpa); Santa Barbara (PH, Asia/Manila) |
| franklin | 9 | 9 | Columbus (US, America/New_York); Denville (US, America/New_York); El Paso (US, America/Denver); Franklin (US, America/Chicago); Franklin (US, America/Indiana/Indianapolis); Franklin (US, America/New_York); Franklin (US, America/Chicago); Kent (US, America/New_York) |
| la union | 9 | 9 | La Unión (AR, America/Argentina/Buenos_Aires); La Unión (CL, America/Santiago); La Unión (CO, America/Bogota); La Unión (CO, America/Bogota); La Unión (CO, America/Bogota); La Unión (ES, Europe/Madrid); San Marcos (GT, America/Guatemala); La Unión (PE, America/Lima) |
| san francisco | 9 | 9 | San Francisco (AR, America/Argentina/Cordoba); San Francisco (CR, America/Costa_Rica); San Francisco El Alto (GT, America/Guatemala); Xonacatlán (MX, America/Mexico_City); Aurora (PH, Asia/Manila); San Francisco (PH, Asia/Manila); San Francisco (PH, Asia/Manila); San Francisco (SV, America/El_Salvador) |
| san jose | 9 | 9 | San Jose (CR, America/Costa_Rica); San José (CR, America/Costa_Rica); Puerto San José (GT, America/Guatemala); San Jose (PH, Asia/Manila); San Jose (PH, Asia/Manila); San Jose (PH, Asia/Manila); San Jose (US, America/Los_Angeles); San José de Mayo (UY, America/Montevideo) |
| san pablo | 9 | 9 | San Pablo (CO, America/Bogota); San Pablo (CR, America/Costa_Rica); San Pablo Jocopilas (GT, America/Guatemala); San Pablo Autopan (MX, America/Mexico_City); San Pablo de las Salinas (MX, America/Mexico_City); San Pablo (PH, Asia/Manila); Saint Paul (US, America/Chicago); San Pablo (US, America/Los_Angeles) |
| santa rita | 9 | 9 | Itumbiara (BR, America/Sao_Paulo); Nova Santa Rita (BR, America/Sao_Paulo); Santa Rita (BR, America/Fortaleza); Santa Rita (BR, America/Fortaleza); Santa Rita de Cássia (BR, America/Bahia); Santa Rita do Passa Quatro (BR, America/Sao_Paulo); Santa Rita (HN, America/Tegucigalpa); Santa Rita (IT, Europe/Rome) |
| springfield | 9 | 9 | Agawam (US, America/New_York); Springfield (US, America/Chicago); Springfield (US, America/Chicago); Springfield (US, America/New_York); Springfield (US, America/New_York); Springfield (US, America/Chicago); Springfield (US, America/New_York); Springfield (US, America/Los_Angeles) |
| alexandria | 8 | 8 | Alexandria (EG, Africa/Cairo); Mashhad (IR, Asia/Tehran); Alessandria (IT, Europe/Rome); Alexandria (RO, Europe/Bucharest); Oleksandriya (UA, Europe/Kyiv); Alexandria (US, America/Chicago); Alexandria (US, America/New_York); Hlanganani (ZA, Africa/Johannesburg) |
| belem | 8 | 8 | Belem (BR, America/Sao_Paulo); Belém (BR, America/Fortaleza); Belém (BR, America/Belem); Belém de São Francisco (BR, America/Recife); Itatira (BR, America/Fortaleza); Belem (GW, Africa/Bissau); Bethlehem (PS, Asia/Hebron); Belém (PT, Europe/Lisbon) |
| georgetown | 8 | 8 | Georgetown (CA, America/Toronto); Saint George's (GD, America/Grenada); Georgetown (GY, America/Guyana); George Town (KY, America/Cayman); George Town (MY, Asia/Kuala_Lumpur); Georgetown (US, America/New_York); Georgetown (US, America/Chicago); Leesburg (US, America/New_York) |
| la paz | 8 | 8 | La Paz (AR, America/Argentina/Cordoba); La Paz (BO, America/La_Paz); La Paz (ES, Europe/Madrid); La Paz (HN, America/Tegucigalpa); La Paz (MX, America/Mazatlan); La Paz Centro (NI, America/Managua); La Paz (PH, Asia/Manila); La Paz (UY, America/Montevideo) |
| newtown | 8 | 8 | Cambridge (US, America/New_York); Elmhurst (US, America/New_York); Elmira (US, America/New_York); Great Kills (US, America/New_York); Hartford (US, America/New_York); Macon (US, America/New_York); Tallahassee (US, America/New_York); Wilmington (US, America/Los_Angeles) |
| sakai | 8 | 8 | Sakai (JP, Asia/Tokyo); Sakai (JP, Asia/Tokyo); Sakai (JP, Asia/Tokyo); Sakai (JP, Asia/Tokyo); Sakai-nakajima (JP, Asia/Tokyo); Sakaiminato (JP, Asia/Tokyo); Sakaki (JP, Asia/Tokyo); Saki (UA, Europe/Simferopol) |
| san cristobal | 8 | 8 | San Cristobal (CU, America/Havana); San Cristóbal (DO, America/Santo_Domingo); San Cristobal (ES, Europe/Madrid); San Cristóbal Verapaz (GT, America/Guatemala); Carlos A. Carrillo (MX, America/Mexico_City); Ecatepec de Morelos (MX, America/Mexico_City); San Cristóbal de las Casas (MX, America/Merida); San Cristóbal (VE, America/Caracas) |
| san lorenzo | 8 | 8 | San Lorenzo (AR, America/Argentina/Cordoba); San Lorenzo (CO, America/Bogota); San Lorenzo de Esmeraldas (EC, America/Guayaquil); San Lorenzo de El Escorial (ES, Europe/Madrid); San Lorenzo (HN, America/Tegucigalpa); San Lorenzo (IT, Europe/Rome); San Lorenzo (PY, America/Asuncion); San Lorenzo (US, America/Los_Angeles) |
| san rafael | 8 | 8 | San Rafael (AR, America/Argentina/Mendoza); San Rafael (CR, America/Costa_Rica); San Rafael Arriba (CR, America/Costa_Rica); San Rafael (MX, America/Mexico_City); San Rafael del Sur (NI, America/Managua); San Rafael (US, America/Los_Angeles); San Rafael (VE, America/Caracas); San Rafael de Onoto (VE, America/Caracas) |
| santa ana | 8 | 8 | Santa Ana Chiautempan (MX, America/Mexico_City); Santa Ana (PE, America/Lima); Santa Ana (PH, Asia/Manila); Taguig (PH, Asia/Manila); Santa Ana (SV, America/El_Salvador); Santa Ana (US, America/Los_Angeles); Santa Ana (VE, America/Caracas); Santa Ana (VE, America/Caracas) |
| santo antonio | 8 | 8 | Soyo (AO, Africa/Luanda); Santo Antônio (BR, America/Fortaleza); Santo Antônio do Içá (BR, America/Manaus); Santo Antônio do Leverger (BR, America/Cuiaba); Santo Antônio do Sudoeste (BR, America/Sao_Paulo); Santo Antônio do Tauá (BR, America/Belem); Santo António (CN, Asia/Macau); Santo António (PT, Atlantic/Madeira) |
| springfild | 8 | 8 | Agawam (US, America/New_York); Springfield (US, America/Chicago); Springfield (US, America/Chicago); Springfield (US, America/New_York); Springfield (US, America/New_York); Springfield (US, America/Chicago); Springfield (US, America/New_York); Springfield (US, America/Los_Angeles) |
| washington | 8 | 8 | Washington (GB, Europe/London); Macomb (US, America/Chicago); Piqua (US, America/New_York); Reisterstown (US, America/New_York); South River (US, America/New_York); Washington (US, America/New_York); Washington (US, America/Chicago); Washington (US, America/Denver) |
| спрингфилд | 8 | 8 | Agawam (US, America/New_York); Springfield (US, America/Chicago); Springfield (US, America/Chicago); Springfield (US, America/New_York); Springfield (US, America/New_York); Springfield (US, America/Chicago); Springfield (US, America/New_York); Springfield (US, America/Los_Angeles) |
| aurora | 7 | 7 | Aurora (BR, America/Fortaleza); Aurora (CA, America/Toronto); Aurora (IT, Europe/Rome); Aurora (PH, Asia/Manila); Aurora (US, America/Chicago); Aurora (US, America/New_York); Aurora (US, America/Denver) |
| bela vista | 7 | 7 | Catchiungo (AO, Africa/Luanda); Bella Vista (AR, America/Argentina/Tucuman); Bela Vista (BR, America/Campo_Grande); Bela Vista (BR, America/Sao_Paulo); Bela Vista de Goiás (BR, America/Sao_Paulo); Utinga (BR, America/Bahia); Bella Vista (US, America/Chicago) |
| belen | 7 | 7 | Belém (BR, America/Fortaleza); Belém (BR, America/Belem); Belén de Umbría (CO, America/Bogota); Belén Gualcho (HN, America/Tegucigalpa); Belen (PE, America/Lima); Bethlehem (PS, Asia/Hebron); Belen (TR, Europe/Istanbul) |

### Short Aliases

| Normalized alias | Rows | Cities | Sample |
| --- | --- | --- | --- |
| i | 2 | 2 | I |
| o | 1 | 1 | O |
| ч | 1 | 1 | Ч |
| ဂ | 1 | 1 | ဂ |
| ቦ | 1 | 1 | ቦ |
| ፖ | 1 | 1 | ፖ |
| つ | 1 | 1 | つ |
| ツ | 1 | 1 | ツ |
| ホ | 1 | 1 | ホ |
| 上 | 1 | 1 | 上 |
| 光 | 1 | 1 | 光 |
| 北 | 1 | 1 | 北 |
| 原 | 1 | 1 | 原 |
| 呉 | 1 | 1 | 呉 |
| 堺 | 1 | 1 | 堺 |
| 境 | 1 | 1 | 境 |
| 寶 | 1 | 1 | 寶 |
| 扇 | 1 | 1 | 扇 |
| 旭 | 1 | 1 | 旭 |
| 柏 | 1 | 1 | 柏 |
| 森 | 1 | 1 | 森 |
| 沪 | 1 | 1 | 沪 |
| 津 | 1 | 1 | 津 |
| 湊 | 1 | 1 | 湊 |
| 燕 | 1 | 1 | 燕 |
| 萩 | 1 | 1 | 萩 |
| 蕨 | 1 | 1 | 蕨 |
| 関 | 1 | 1 | 関 |
| 鵤 | 1 | 1 | 鵤 |

## Findings

- The runtime database was rebuilt with the corrected importer and now reports 228 merged GeoNames records.
- Context-like alias pollution is 0 under the protected-name check used by the cleanup tool.
- Numeric-only aliases are 0.
- Addis, Addis Ababa, Addis Abeba and the Ethiopic query all resolve to the same canonical city.
- Roma/Rome and Milano/Milan still resolve to the curated Italian canonical rows.
