# NightScope

NightScope e una applicazione desktop Windows per astronomia osservativa, costruita con Python, PySide6, Qt Quick/QML, SQLite embedded, Skyfield, Astropy e Open-Meteo.

## Stato RC1

- UI QML dark theme con Home, dettaglio oggetto, calendario, meteo, location e strumenti.
- Database SQLite locale con citta, Messier, cataloghi strumenti, cache meteo, profili e storico osservazioni.
- Seed locali estesi per citta, cataloghi telescopi/oculari/Barlow, contenuti osservativi e lookup iniziale inquinamento luminoso.
- Calcoli Skyfield reali per Sole, Luna e pianeti principali usando `data/skyfield/de421.bsp`.
- Catalogo Messier offline importato da `data/messier_seed.csv`.
- Meteo Open-Meteo con cache SQLite, timeout breve e fallback offline.
- Score osservativo, Planetary Score, Deep Sky Score, seeing, transparency e Bortle stimato.
- Night Planner, Sky Map minimale e notifiche generate localmente.
- Logging con rotazione in `logs/nightscope.log`.
- Validazione astronomica automatica e packaging Windows PyInstaller.

## Avvio sviluppo

```powershell
.\.venv\Scripts\python.exe astro_viewer\main.py
```

## Verifica

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s astro_viewer\tests
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\python.exe astro_viewer\tools\generate_validation_report.py
```

Il report astronomico viene scritto in `astro_viewer/reports/astronomy_validation_report.md`.

## Build Windows

```powershell
.\packaging\build_windows.ps1
```

La build usa `packaging/NightScope.spec` e include:

- QML e componenti UI;
- `resources/` con icone e immagini locali;
- `data/nightscope.db`;
- `data/schema.sql`;
- `data/messier_seed.csv`;
- `data/cities15000.txt`;
- `data/countryInfo.txt` e `data/admin1CodesASCII.txt`;
- seed CSV per telescopi, oculari, Barlow, inquinamento luminoso e contenuti oggetti;
- `data/skyfield/de421.bsp`;
- icona `resources/icons/nightscope.ico`.

Output previsto: `dist/NightScope/NightScope.exe`.

## Struttura

```text
astro_viewer/
  main.py
  app/
    astronomy/
    database/
    models/
    services/
    viewmodels/
    ui/
  data/
  resources/
  tests/
  tools/
  reports/
packaging/
```

## Servizi principali

- `SkyfieldAstronomyEngine`: ephemeris, alt/az, sorgere, tramonto, culminazione, fase lunare ed eventi.
- `OpenMeteoWeatherService`: forecast 24h, cache locale e fallback controllato.
- `LocationService`: citta SQLite, coordinate manuali, posizione Windows e fallback online approssimato solo su consenso.
- `ObservingScoreService`: qualita osservativa e miglior oggetto della notte.
- `LightPollutionService`: provider architecture con lookup dataset locale, placeholder World Atlas/VIIRS e stima offline fallback.
- `SeeingTransparencyService`: provider architecture con stima base da cloud low/mid/high, vento, raffiche, umidita, visibilita e dew point; placeholder Meteoblue senza API key nel codice.
- `NightPlannerService`: sequenza osservativa ottimizzata.
- `EquipmentService`: calcoli strumenti, oculari, Barlow e difficolta.

## Dataset locali

I seed locali sono in `data/`:

- `cities15000.txt`: catalogo citta GeoNames incluso nel package.
- `countryInfo.txt` e `admin1CodesASCII.txt`: arricchimento GeoNames per nomi paese e regioni.
- `telescope_catalog_seed.csv`: catalogo canonico dei modelli telescopio.
- `eyepiece_catalog_seed.csv`: catalogo canonico degli oculari, inclusi oculari zoom e range focali.
- `barlow_catalog_seed.csv`: catalogo canonico di Barlow/focal extender.
- `light_pollution_seed.csv`: lookup locale iniziale per Bortle, sky brightness, limiting magnitude, source e confidence.
- `object_images_seed.csv` e `object_descriptions_seed.csv`: asset locali verificati e note osservative per pianeti, Luna e principali Messier.

Le fonti e i limiti sono documentati in `data/DATA_SOURCES.md`. I dati tecnici marcati `To verify` o derivati dal nome modello vanno confermati sulla variante regionale prima di usarli per raccomandazioni d'acquisto.

## Import dati

Gli import CLI non richiedono API key e usano upsert/deduplicazione per evitare duplicati:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\import_cities.py C:\path\to\cities15000.txt --country-info C:\path\to\countryInfo.txt --admin1-codes C:\path\to\admin1CodesASCII.txt
.\.venv\Scripts\python.exe astro_viewer\tools\import_telescope_catalog.py astro_viewer\data\telescope_catalog_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_eyepiece_catalog.py astro_viewer\data\eyepiece_catalog_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_eyepiece_catalog.py astro_viewer\data\barlow_catalog_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_light_pollution.py astro_viewer\data\light_pollution_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_object_content.py astro_viewer\data\object_descriptions_seed.csv
```

NightScope usa `cities15000.txt` da GeoNames come sorgente citta inclusa nel package. Non importa `allCountries.txt`. Se il file viene sostituito con una versione piu recente, l'avvio rileva size/mtime diversi e ricostruisce il catalogo citta dal dump. Il report import include:

- total rows read;
- total imported;
- duplicates skipped/merged;
- aliases generated;
- duplicates merged;
- cities missing timezone;
- DB size.

Le traduzioni non diventano righe separate: `Addis Ababa` e `Addis Abeba` restano un solo record con alias ricercabili.

## Regole strumenti

La sezione `Strumenti` e divisa in tre pagine:

- `Profili`: setup osservativi usati da planner, Home e raccomandazioni.
- `Telescopi`: catalogo globale dei modelli disponibili.
- `Oculari e Barlow`: catalogo globale degli accessori ottici.

I profili referenziano gli elementi dei cataloghi tramite ID; i cataloghi non vengono duplicati come "attrezzatura posseduta". La pagina `Profili` consente di assegnare o rimuovere equipaggiamento con dialog QML dark-theme, filtrando tra telescopi, oculari, zoom e Barlow.

- Se non esiste un telescopio assegnato al profilo attivo, NightScope usa `Occhio nudo`.
- In modalita `Occhio nudo`, oculari e Barlow non vengono usati e i suggerimenti non inventano setup.
- Le raccomandazioni usano solo telescopi, oculari e Barlow assegnati al profilo attivo.
- Se un profilo contiene un telescopio ma non oculari, i suggerimenti restano limitati e l'app invita ad aggiungere oculari.
- Gli oculari zoom sono singoli record catalogo con focale minima/massima, non una serie di oculari fissi separati.
- Se si elimina un elemento catalogo usato da uno o piu profili, l'app chiede conferma e puo rimuovere prima i riferimenti dai profili.

## Troubleshooting

### Windows location non disponibile

Se Windows Location e disattivata, non autorizzata, non supportata dal dispositivo, va in timeout o restituisce coordinate vuote, NightScope mantiene la posizione corrente e mostra:

```text
Windows location is not available. Please choose a city or enter coordinates manually.
```

Usare la ricerca citta offline o inserire latitudine/longitudine manualmente nella pagina Location.

### Meteo non disponibile

Se Open-Meteo non risponde, restituisce JSON non valido, rate limiting o timeout, NightScope usa la cache locale se presente. In assenza di cache mostra:

```text
Weather service temporarily unavailable.
```

I dati astronomici restano utilizzabili, ma lo score meteo viene degradato.

### Database mancante o corrotto

All'avvio NightScope verifica `data/nightscope.db` con `PRAGMA integrity_check`. Se il database e corrotto, viene spostato in un file `*.corrupt-YYYYMMDDHHMMSS.bak` e ricreato da `schema.sql` e dai seed locali. Un backup aggiornato viene mantenuto come `nightscope.db.backup`.

### Ephemeris mancante o corrotta

Se `data/skyfield/de421.bsp` manca o non e leggibile, Skyfield tenta il recupero tramite il loader. Se il recupero fallisce, l'app mostra uno stato controllato e usa dati astronomici fallback invece di terminare con un traceback.

### Log

I log applicativi sono in:

```text
logs/nightscope.log
```

La rotazione mantiene tre file storici da circa 1 MB.
