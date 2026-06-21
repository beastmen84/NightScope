# GeoNames Import Quality Report

Generated: 2026-06-21T20:01:12
Database: `astro_viewer/data/nightscope.db`

## Summary

| Metric | Value |
| --- | --- |
| City rows | 27704 |
| CityAlias rows | 391666 |
| Average aliases per city | 14.14 |
| Maximum aliases for one city | 539 |
| Cities with >100 aliases | 99 |
| Cities with >250 aliases | 10 |
| Context-like alias rows | 82916 |

Interpretation: the overall alias volume is plausible for GeoNames alternate names, but context-like aliases should be treated as search pollution because country names, country codes, and admin regions are not city aliases.

Implementation note: this verification found a clear importer bug. The importer in this worktree has been updated so future GeoNames imports keep country, country code, and admin region in `City.search_name` only, not in `CityAlias`. The measured runtime database still contains the old context-like alias rows until it is cleaned or rebuilt.

## Last GeoNames Import Logs

| Source | Size | Imported at | Rows read | Imported | Merged | Aliases added | Missing TZ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cities15000.txt | 8344639 | 2026-06-21T18:38:18 | 33886 | 28029 | 5857 | 383949 | 0 |

## Top 20 Cities By Alias Count

| City ID | City | Country | Code | Timezone | Aliases |
| --- | --- | --- | --- | --- | --- |
| 64 | Paris | Francia | FR | Europe/Paris | 539 |
| 133 | Jerusalem | Israele | IL | Asia/Jerusalem | 407 |
| 9917 | Créteil | FR | FR | Europe/Paris | 355 |
| 14 | Madrid | Spagna | ES | Europe/Madrid | 326 |
| 9141 | Sants | ES | ES | Europe/Madrid | 318 |
| 71 | Brussels | Belgio | BE | Europe/Brussels | 266 |
| 119 | Hong Kong | Hong Kong | HK | Asia/Hong_Kong | 264 |
| 24979 | Gretna | US | US | America/Chicago | 258 |
| 9633 | Villeurbanne | FR | FR | Europe/Paris | 251 |
| 11702 | Yāfā | IL | IL | Asia/Jerusalem | 251 |
| 25865 | Malden | US | US | America/New_York | 242 |
| 26175 | Hillside | US | US | America/New_York | 241 |
| 26494 | Artesia | US | US | America/Los_Angeles | 230 |
| 65 | London | Regno Unito | GB | Europe/London | 224 |
| 10072 | Wembley | GB | GB | Europe/London | 222 |
| 9810 | Marseille | FR | FR | Europe/Paris | 199 |
| 4021 | Vancouver | CA | CA | America/Vancouver | 196 |
| 9680 | Suresnes | FR | FR | Europe/Paris | 193 |
| 25521 | Alexandria | US | US | America/New_York | 187 |
| 21580 | Saint Petersburg | RU | RU | Europe/Moscow | 187 |

## Key Search Verification

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

## Addis Ababa Inspection

Canonical row:

| Field | Value |
| --- | --- |
| id | 40 |
| city_name | Addis Ababa |
| country | Etiopia |
| latitude | 9.03 |
| longitude | 38.74 |
| timezone | Africa/Addis_Ababa |
| ascii_name | Addis Ababa |
| country_code | ET |
| admin_region | Addis Ababa |
| population | 3860000 |
| search_name | 44 a di si a bei ba ababa abeba add addis addis ababa addis abaeba addis abbaba addis abeba addis abebae addisa ababa addisaaba addisz abeba adis ababa adis abeba adis abebo adisa ababa adisabeba adiseuababa adisuabeba adys ababa adys abeba antis ampempa atis apapa et ethiopia etiopia finfinne neanthopolis tungga əddis əbəbə αντις αμπεμπα аддис абебæ аддис абеба адис абеба адыс абеба ադիս աբեբա ատիս ապապա אדיס אבבה اديس ابابا ادیس ابابا يەددىس يەبىبە अदिस अबाबा আদদিস আবাবা ადის აბება 아디스아바바 አዲስ አበባ アティスアヘハ 阿迪斯阿貝巴 |

Distinct City rows matching Addis Ababa/Addis Abeba canonical/search fields: 1 (`[40]`)
Alias rows attached to canonical Addis row: 50

Aliases attached to Addis Ababa:

| Alias | Normalized | Source |
| --- | --- | --- |
| 44 | 44 | geonames |
| a di si a bei ba | a di si a bei ba | geonames |
| ababa | ababa | dedupe |
| abeba | abeba | dedupe |
| ADD | add | geonames |
| addis | addis | dedupe |
| Addis Ababa | addis ababa | dedupe |
| Addis Abaeba | addis abaeba | geonames |
| Addis Abbaba | addis abbaba | geonames |
| Addis Abeba | addis abeba | dedupe |
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
| ET | et | dedupe |
| ethiopia | ethiopia | dedupe |
| Etiopia | etiopia | dedupe |
| finfinne | finfinne | dedupe |
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

Conclusion for Addis: PASS - Addis Ababa/Addis Abeba map to one City row.

## Suspicious Alias Pollution

### Duplicate Aliases Across Multiple Cities

| Normalized alias | Cities | Rows | Sample cities |
| --- | --- | --- | --- |
| in | 3156 | 3156 | Saint-Germain-en-Laye (FR, Europe/Paris); St Helens (GB, Europe/London); Abhayāpuri (IN, Asia/Kolkata); Abohar (IN, Asia/Kolkata); Abrama (IN, Asia/Kolkata); Achalpur (IN, Asia/Kolkata); Achampet (IN, Asia/Kolkata); Achhnera (IN, Asia/Kolkata) |
| us | 2488 | 2488 | Aberdeen (US, America/New_York); Aberdeen (US, America/Chicago); Aberdeen (US, America/Los_Angeles); Abilene (US, America/Chicago); Abington (US, America/New_York); Abington (US, America/New_York); Acton (US, America/New_York); Acworth (US, America/New_York) |
| br | 2196 | 2196 | Abadia de Goiás (BR, America/Sao_Paulo); Abaetetuba (BR, America/Belem); Abaeté (BR, America/Sao_Paulo); Abaré (BR, America/Bahia); Abelardo Luz (BR, America/Sao_Paulo); Acaraú (BR, America/Fortaleza); Acará (BR, America/Belem); Acopiara (BR, America/Fortaleza) |
| cn | 1942 | 1942 | Acheng (CN, Asia/Shanghai); Ahu (CN, Asia/Shanghai); Aihui (CN, Asia/Shanghai); Alamaiti (CN, Asia/Urumqi); Anbu (CN, Asia/Shanghai); Anda (CN, Asia/Shanghai); Anfu (CN, Asia/Shanghai); Anfu (CN, Asia/Shanghai) |
| 07 | 1021 | 1021 | les Escaldes (AD, Europe/Andorra); Umm Al Quwain City (AE, Asia/Dubai); Andkhoy (AF, Asia/Kabul); Maymana (AF, Asia/Kabul); Artik (AM, Asia/Yerevan); Gyumri (AM, Asia/Yerevan); Humbe (AO, Africa/Luanda); Ondjiva (AO, Africa/Luanda) |
| 05 | 992 | 992 | Ras Al Khaimah (AE, Asia/Dubai); Bāmyān (AF, Asia/Kabul); Bāzār-e Yakāwlang (AF, Asia/Kabul); Abovyan (AM, Asia/Yerevan); Charentsavan (AM, Asia/Yerevan); Hrazdan (AM, Asia/Yerevan); Camabatela (AO, Africa/Luanda); Cazombo (AO, Africa/Luanda) |
| 02 | 980 | 980 | Ajman (AE, Asia/Dubai); Al Ḩamīdīyah (AE, Asia/Dubai); Ghormach (AF, Asia/Kabul); Ararat (AM, Asia/Yerevan); Artashat (AM, Asia/Yerevan); Masis (AM, Asia/Yerevan); Andulo (AO, Africa/Luanda); Camacupa (AO, Africa/Luanda) |
| ru | 980 | 980 | Wattrelos (FR, Europe/Paris); Jerusalem (IL, Asia/Jerusalem); Chorzów (PL, Europe/Warsaw); Abakan (RU, Asia/Krasnoyarsk); Abaza (RU, Asia/Krasnoyarsk); Abdulino (RU, Asia/Yekaterinburg); Abinsk (RU, Europe/Moscow); Achinsk (RU, Asia/Krasnoyarsk) |
| de | 964 | 964 | Beveren (BE, Europe/Brussels); Chaudfontaine (BE, Europe/Brussels); Grimbergen (BE, Europe/Brussels); Coquitlam (CA, America/Vancouver); Edmonton (CA, America/Edmonton); Montréal (CA, America/Toronto); Concepción (CL, America/Santiago); Aachen (DE, Europe/Berlin) |
| jp | 954 | 954 | Abashiri (JP, Asia/Tokyo); Ageo (JP, Asia/Tokyo); Agui (JP, Asia/Tokyo); Aihara (JP, Asia/Tokyo); Aioi (JP, Asia/Tokyo); Aira (JP, Asia/Tokyo); Aizu-Wakamatsu (JP, Asia/Tokyo); Aizu-misato Machi (JP, Asia/Tokyo) |
| 04 | 952 | 952 | Dibba Al-Fujairah (AE, Asia/Dubai); Fujairah (AE, Asia/Dubai); Reef Al Fujairah City (AE, Asia/Dubai); Ţarīf Kalbā (AE, Asia/Dubai); Saint John’s (AG, America/Antigua); Gavar (AM, Asia/Yerevan); Sevan (AM, Asia/Yerevan); Comodoro Rivadavia (AR, America/Argentina/Catamarca) |
| 13 | 864 | 864 | Istālif (AF, Asia/Kabul); Kabul (AF, Asia/Kabul); Paghmān (AF, Asia/Kabul); Camucuio (AO, Africa/Luanda); Mossamedes (AO, Africa/Luanda); Tômbua (AO, Africa/Luanda); Virei (AO, Africa/Luanda); Mendoza (AR, America/Argentina/Mendoza) |
| 01 | 825 | 825 | Abu Dhabi (AE, Asia/Dubai); Al Ain City (AE, Asia/Dubai); Al Shamkhah City (AE, Asia/Dubai); Ar Ruways (AE, Asia/Dubai); Bani Yas City (AE, Asia/Dubai); Khalifah A City (AE, Asia/Dubai); Mohammed Bin Zayed City (AE, Asia/Dubai); Musaffah (AE, Asia/Dubai) |
| 16 | 819 | 819 | Cuímba (AO, Africa/Luanda); Mbanza Kongo (AO, Africa/Luanda); N'zeto (AO, Africa/Luanda); Soyo (AO, Africa/Luanda); Tombôco (AO, Africa/Luanda); Allen (AR, America/Argentina/Salta); Catriel (AR, America/Argentina/Salta); Cinco Saltos (AR, America/Argentina/Salta) |
| 06 | 797 | 797 | Adh Dhayd (AE, Asia/Dubai); Al Sajaah (AE, Asia/Dubai); Khawr Fakkān (AE, Asia/Dubai); Sharjah (AE, Asia/Dubai); Ţarīf Kalbā (AE, Asia/Dubai); Farah (AF, Asia/Kabul); Vanadzor (AM, Asia/Yerevan); Calulo (AO, Africa/Luanda) |
| 15 | 773 | 773 | Maquela do Zombo (AO, Africa/Luanda); Negage (AO, Africa/Luanda); Sanza Pombo (AO, Africa/Luanda); Songo (AO, Africa/Luanda); Uíge (AO, Africa/Luanda); Centenario (AR, America/Argentina/Salta); Cutral-Có (AR, America/Argentina/Salta); Neuquén (AR, America/Argentina/Salta) |
| 08 | 772 | 772 | les Escaldes (AD, Europe/Andorra); Ghazni (AF, Asia/Kabul); Goris (AM, Asia/Yerevan); Kapan (AM, Asia/Yerevan); Alto Hama (AO, Africa/Luanda); Catchiungo (AO, Africa/Luanda); Caála (AO, Africa/Luanda); Huambo (AO, Africa/Luanda) |
| 09 | 740 | 740 | Shahrak (AF, Asia/Kabul); Dilijan (AM, Asia/Yerevan); Ijevan (AM, Asia/Yerevan); Caluquembe (AO, Africa/Luanda); Lubango (AO, Africa/Luanda); Matala (AO, Africa/Luanda); Quipungo (AO, Africa/Luanda); Formosa (AR, America/Argentina/Cordoba) |
| 03 | 699 | 699 | Al Mizhar First (AE, Asia/Dubai); Al Qusais 1 (AE, Asia/Dubai); Ar Rāshidīyah (AE, Asia/Dubai); Dayrah (AE, Asia/Dubai); Dubai (AE, Asia/Dubai); Dubai (AE, Asia/Dubai); Dubai Silicon Oasis (AE, Asia/Dubai); Jebel Ali (AE, Asia/Dubai) |
| 11 | 644 | 644 | Eslam Qaleh (AF, Asia/Kabul); Herāt (AF, Asia/Kabul); Karukh (AF, Asia/Kabul); Kushk (AF, Asia/Kabul); Shīnḏanḏ (AF, Asia/Kabul); Avan (AM, Asia/Yerevan); Davtashen (AM, Asia/Yerevan); Erebuni (AM, Asia/Yerevan) |
| 25 | 630 | 630 | İsmayıllı (AZ, Asia/Baku); Gatumba (BI, Africa/Bujumbura); Alto Alegre (BR, America/Boa_Vista); Boa Vista (BR, America/Boa_Vista); Cantá (BR, America/Boa_Vista); Caracaraí (BR, America/Boa_Vista); Mucajaí (BR, America/Boa_Vista); Pacaraima (BR, America/Boa_Vista) |
| ca | 607 | 607 | Abbotsford (CA, America/Vancouver); Agincourt North (CA, America/Toronto); Ahuntsic-Cartierville (CA, America/Toronto); Airdrie (CA, America/Edmonton); Ajax (CA, America/Toronto); Alliston (CA, America/Toronto); Alma (CA, America/Toronto); Amos (CA, America/Toronto) |
| 10 | 598 | 598 | Gereshk (AF, Asia/Kabul); Khān Neshīn (AF, Asia/Kabul); Lashkar Gāh (AF, Asia/Kabul); Libertador General San Martín (AR, America/Argentina/Jujuy); Palpalá (AR, America/Argentina/Jujuy); San Pedro de Jujuy (AR, America/Argentina/Jujuy); San Salvador de Jujuy (AR, America/Argentina/Jujuy); Gourcy (BF, Africa/Ouagadougou) |
| gb | 560 | 560 | Aberdare (GB, Europe/London); Aberdeen (GB, Europe/London); Aberystwyth (GB, Europe/London); Abingdon (GB, Europe/London); Accrington (GB, Europe/London); Adwick le Street (GB, Europe/London); Aldridge (GB, Europe/London); Alfreton (GB, Europe/London) |
| 14 | 553 | 553 | Cazombo (AO, Africa/Luanda); Luau (AO, Africa/Luanda); Luena (AO, Africa/Luanda); Lumbala (AO, Africa/Luanda); Apóstoles (AR, America/Argentina/Cordoba); Aristóbulo del Valle (AR, America/Argentina/Cordoba); Colonia Wanda (AR, America/Argentina/Cordoba); El Soberbio (AR, America/Argentina/Cordoba) |
| mx | 549 | 549 | Abasolo (MX, America/Mexico_City); Acaponeta (MX, America/Mazatlan); Acapulco de Juárez (MX, America/Mexico_City); Acatlán de Osorio (MX, America/Mexico_City); Acayucan (MX, America/Mexico_City); Actopan (MX, America/Mexico_City); Acámbaro (MX, America/Mexico_City); Agua Dulce (MX, America/Mexico_City) |
| 12 | 521 | 521 | Bailundo (AO, Africa/Luanda); Cacuso (AO, Africa/Luanda); Cambundi (AO, Africa/Luanda); Cambundi (AO, Africa/Luanda); Cambundi Catembo (AO, Africa/Luanda); Cangandala (AO, Africa/Luanda); Kunda dya Baze (AO, Africa/Luanda); Luquembo (AO, Africa/Luanda) |
| 33 | 520 | 520 | Sang-e Chārak (AF, Asia/Kabul); Sar-e Pul (AF, Asia/Kabul); Mingachevir (AZ, Asia/Baku); Anfu (CN, Asia/Shanghai); Anju (CN, Asia/Shanghai); Anlan (CN, Asia/Shanghai); Anping (CN, Asia/Shanghai); Anwen (CN, Asia/Shanghai) |
| it | 478 | 478 | Abano Terme (IT, Europe/Rome); Abbiategrasso (IT, Europe/Rome); Aci Castello (IT, Europe/Rome); Acilia-Castel Fusano-Ostia Antica (IT, Europe/Rome); Acireale (IT, Europe/Rome); Acquaviva delle Fonti (IT, Europe/Rome); Acqui Terme (IT, Europe/Rome); Agrigento (IT, Europe/Rome) |
| eng | 468 | 468 | Abingdon (GB, Europe/London); Accrington (GB, Europe/London); Adwick le Street (GB, Europe/London); Aldridge (GB, Europe/London); Alfreton (GB, Europe/London); Alton (GB, Europe/London); Altrincham (GB, Europe/London); Ampthill (GB, Europe/London) |
| 27 | 462 | 462 | Kyurdarmir (AZ, Asia/Baku); Adamantina (BR, America/Sao_Paulo); Aguaí (BR, America/Sao_Paulo); Agudos (BR, America/Sao_Paulo); Altinópolis (BR, America/Sao_Paulo); Alumínio (BR, America/Sao_Paulo); Americana (BR, America/Sao_Paulo); Amparo (BR, America/Sao_Paulo) |
| 19 | 452 | 452 | Khāsh (AF, Asia/Kabul); Zaranj (AF, Asia/Kabul); Barra do Dande (AO, Africa/Luanda); Bula Atumba (AO, Africa/Luanda); Cage Mazumbo (AO, Africa/Luanda); Calumbo (AO, Africa/Luanda); Canacassala (AO, Africa/Luanda); Caxito (AO, Africa/Luanda) |
| es | 447 | 447 | A Coruña (ES, Europe/Madrid); A Estrada (ES, Europe/Madrid); Adeje (ES, Atlantic/Canary); Adra (ES, Europe/Madrid); Alameda de Osuna (ES, Europe/Madrid); Albacete (ES, Europe/Madrid); Alcalá de Guadaira (ES, Europe/Madrid); Alcalá de Henares (ES, Europe/Madrid) |
| id | 425 | 425 | Abepura (ID, Asia/Jayapura); Agats (ID, Asia/Jayapura); Amahai (ID, Asia/Jayapura); Ambarawa (ID, Asia/Jakarta); Ambon (ID, Asia/Jayapura); Amlapura (ID, Asia/Makassar); Amuntai (ID, Asia/Makassar); Arjawinangun (ID, Asia/Jakarta) |
| ph | 413 | 413 | Abuyog (PH, Asia/Manila); Aglipay (PH, Asia/Manila); Agoo (PH, Asia/Manila); Al-Barka (PH, Asia/Manila); Alabel (PH, Asia/Manila); Alaminos (PH, Asia/Manila); Aliaga (PH, Asia/Manila); Alicia (PH, Asia/Manila) |
| 23 | 410 | 410 | Kandahār (AF, Asia/Kabul); Río Grande (AR, America/Argentina/Ushuaia); Ushuaia (AR, America/Argentina/Ushuaia); Hacıqabul (AZ, Asia/Baku); Agudo (BR, America/Sao_Paulo); Alegrete (BR, America/Sao_Paulo); Alvorada (BR, America/Sao_Paulo); Arroio Grande (BR, America/Sao_Paulo) |
| 36 | 409 | 409 | Gardez (AF, Asia/Kabul); Neftçala (AZ, Asia/Baku); Chiquinquirá (CO, America/Bogota); Duitama (CO, America/Bogota); Moniquirá (CO, America/Bogota); Puerto Boyacá (CO, America/Bogota); Sogamoso (CO, America/Bogota); Tunja (CO, America/Bogota) |
| tr | 398 | 398 | Adana (TR, Europe/Istanbul); Adapazarı (TR, Europe/Istanbul); Adilcevaz (TR, Europe/Istanbul); Adıyaman (TR, Europe/Istanbul); Afyonkarahisar (TR, Europe/Istanbul); Afşin (TR, Europe/Istanbul); Ahlat (TR, Europe/Istanbul); Akdağmadeni (TR, Europe/Istanbul) |
| 21 | 392 | 392 | Arroyo Seco (AR, America/Argentina/Cordoba); Carcarañá (AR, America/Argentina/Cordoba); Casilda (AR, America/Argentina/Cordoba); Cañada de Gómez (AR, America/Argentina/Cordoba); Coronda (AR, America/Argentina/Cordoba); Esperanza (AR, America/Argentina/Cordoba); Firmat (AR, America/Argentina/Cordoba); Gobernador Gálvez (AR, America/Argentina/Cordoba) |
| 24 | 390 | 390 | Khanabad (AF, Asia/Kabul); Kunduz (AF, Asia/Kabul); Qarāwul (AF, Asia/Kabul); Aguilares (AR, America/Argentina/Tucuman); Alderetes (AR, America/Argentina/Tucuman); Bella Vista (AR, America/Argentina/Tucuman); Famaillá (AR, America/Argentina/Tucuman); Monteros (AR, America/Argentina/Tucuman) |

### Context-like Aliases

| Alias type | Rows | Cities |
| --- | --- | --- |
| country_code | 27695 | 27695 |
| country | 27589 | 27589 |
| admin_region | 27632 | 27632 |

### Empty Aliases

Empty alias rows: 0

### Short Aliases

| Normalized alias | Rows | Cities | Sample |
| --- | --- | --- | --- |
| w | 54 | 54 | W |
| c | 49 | 49 | C |
| e | 40 | 40 | E |
| n | 31 | 31 | N |
| l | 30 | 30 | L |
| i | 22 | 22 | I |
| a | 19 | 19 | a |
| 3 | 13 | 13 | 3 |
| 1 | 12 | 12 | 1 |
| 2 | 11 | 11 | 2 |
| f | 11 | 11 | F |
| s | 11 | 11 | S |
| m | 10 | 10 | M |
| 7 | 9 | 9 | 7 |
| b | 9 | 9 | B |
| k | 9 | 9 | K |
| 5 | 8 | 8 | 5 |
| h | 8 | 8 | H |
| d | 7 | 7 | D |
| 4 | 5 | 5 | 4 |
| 6 | 5 | 5 | 6 |
| / | 4 | 4 | / |
| 8 | 3 | 3 | 8 |
| u | 3 | 3 | U |
| ، | 3 | 3 | ، |
| و | 3 | 3 | و |
| x | 2 | 2 | x |
| 9 | 1 | 1 | 9 |
| o | 1 | 1 | O |
| t | 1 | 1 | t |

### Numeric-only Aliases

| Normalized alias | Rows | Cities | Sample |
| --- | --- | --- | --- |
| 07 | 1021 | 1021 | 07 |
| 05 | 992 | 992 | 05 |
| 02 | 980 | 980 | 02 |
| 04 | 952 | 952 | 04 |
| 13 | 864 | 864 | 13 |
| 01 | 825 | 825 | 01 |
| 16 | 819 | 819 | 16 |
| 06 | 797 | 797 | 06 |
| 15 | 773 | 773 | 15 |
| 08 | 772 | 772 | 08 |
| 09 | 740 | 740 | 09 |
| 03 | 699 | 699 | 03 |
| 11 | 644 | 644 | 11 |
| 25 | 630 | 630 | 25 |
| 10 | 598 | 598 | 10 |
| 14 | 553 | 553 | 14 |
| 12 | 521 | 521 | 12 |
| 33 | 520 | 520 | 33 |
| 27 | 462 | 462 | 27 |
| 19 | 452 | 452 | 19 |
| 23 | 410 | 410 | 23 |
| 36 | 409 | 409 | 36 |
| 21 | 392 | 392 | 21 |
| 24 | 390 | 390 | 24 |
| 30 | 389 | 389 | 30 |
| 18 | 388 | 388 | 18 |
| 29 | 372 | 372 | 29 |
| 17 | 341 | 341 | 17 |
| 35 | 336 | 336 | 35 |
| 26 | 332 | 332 | 26 |

## Findings

- 383k generated/imported aliases is broadly reasonable for a 33,886-row GeoNames `cities15000.txt` import: the observed average is 14.14 aliases per city, and high-count cities such as Paris and Jerusalem are expected to have many multilingual alternate names.
- Key searches for Addis, Addis Ababa, Addis Abeba, Ethiopic Addis, Roma/Rome, Milano/Milan, New York, and Tokyo resolve to concrete city records.
- Addis Ababa and Addis Abeba are not separate City rows in the current database.
- Suspicious alias pollution is present: country codes, country names, and admin regions are stored in `CityAlias`. This inflates duplicate aliases and can make generic searches such as country codes match many unrelated cities.
- The importer has been fixed for future imports; the existing runtime database needs a cleanup/rebuild step to remove already-imported context-like aliases.

## Recommended Cleanup

1. Keep GeoNames alternate names, canonical city names, ASCII names, and known translation aliases in `CityAlias`.
2. Keep the importer behavior that stores `country`, `country_code`, and `admin_region` only in `City.search_name` or dedicated columns for filtering, not in `CityAlias`.
3. Rebuild `CityAlias` from a clean source or run a targeted cleanup migration removing context-like aliases from existing rows.
4. After cleanup, re-run this report and verify that key searches still pass.
