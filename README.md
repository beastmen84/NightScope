# NightScope

NightScope è un'app desktop Windows per astronomia osservativa. Combina calcoli astronomici locali, profili di equipaggiamento, meteo orario, stima del cielo locale e suggerimenti pratici per pianificare una sessione visuale.

L'obiettivo non è sostituire atlanti o software planetari completi, ma rispondere rapidamente alla domanda: cosa vale la pena osservare stanotte, da questa località, con questo setup?

## Funzionalità principali

- Dashboard Home con qualità osservativa, Luna, meteo osservativo, punteggi planetari e cielo profondo.
- Piano osservativo consigliato, altri pianeti visibili e oggetti di cielo profondo filtrati per profilo attivo.
- Dettaglio oggetto con finestra osservativa, descrizione, configurazione consigliata, motivazioni e ciclo lunare.
- Calcoli Skyfield reali per Sole, Luna, pianeti, fasi lunari, eventi e coordinate alt/az.
- Pagina `Oggetti celesti` per esplorare il catalogo locale con ricerca, filtri,
  colonna `Utile (≥15°)`, visibilità mensile e apertura del dettaglio oggetto.
- Catalogo offline generico con oggetti Messier e Sistema Solare, pronto per futuri cataloghi Caldwell/NGC/IC.
- Meteo Open-Meteo con cache SQLite, timeout breve e fallback controllato.
- Stima seeing/trasparenza da nuvolosità, vento, raffiche, umidità, visibilità e dew point.
- Stima qualità cielo con Bortle/SQM locale e supporto opzionale ai dati NASA VIIRS Black Marble tramite Earthdata.
- Località configurabile da posizione Windows, fallback online approssimato, ricerca città GeoNames offline o coordinate manuali.
- Pagina `Provider dati` per configurare accessi opzionali a servizi esterni, a partire da Earthdata NASA.
- Profili di equipaggiamento con cataloghi separati per telescopi, oculari e Barlow.
- Recommendation Engine v2 con setup pratici, posizioni reali per oculari zoom e presentazione separata tra visibilità e osservazione consigliata.
- Database SQLite embedded inizializzato da seed CSV locali.
- Build Windows tramite PyInstaller.

## Stato

Versione stabile di riferimento: `1.1.3`.

La UI e il flusso principale sono considerati stabili per l'uso osservativo visuale. Le aree più sperimentali restano:

- dati VIIRS NASA, perché dipendono da connessione, credenziali Earthdata e disponibilità LAADS;
- qualità dei cataloghi strumenti, da verificare sempre per varianti regionali e modelli commerciali specifici;
- descrizioni e note osservative, che possono essere arricchite nel tempo.

Il numero versione applicativo è tracciato nel file root `VERSION`.

## Requisiti

- Windows 10/11.
- Python 3.12+ consigliato per sviluppo.
- Virtualenv locale in `.venv`.

Installazione dipendenze:

```powershell
.\.venv\Scripts\python.exe -m pip install -r astro_viewer\requirements.txt
```

## Avvio in sviluppo

```powershell
.\.venv\Scripts\python.exe astro_viewer\main.py
```

Smoke test rapido:

```powershell
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
```

Suite test:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall astro_viewer
```

## Validazione

Esegui tutti i controlli standard con:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py
```

Modalità rapida senza coverage:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast
```

## Build Windows

```powershell
.\packaging\build_windows.ps1
```

La build usa `packaging/NightScope.spec` e include:

- UI QML e componenti;
- `resources/` con icone e immagini locali;
- `data/schema.sql`;
- seed CSV per Messier, immagini, descrizioni, telescopi, oculari, Barlow e inquinamento luminoso;
- dump GeoNames `cities15000.txt`, `countryInfo.txt`, `admin1CodesASCII.txt`;
- ephemeris `data/skyfield/de421.bsp`;
- `manuale.html`;
- `VERSION`.

Output previsto:

```text
dist/NightScope/NightScope.exe
```

## Struttura repo

```text
astro_viewer/
  main.py
  app/
    astronomy/
    database/
    models/
    services/
    ui/
    viewmodels/
  data/
  resources/
  tests/
  tools/
packaging/
VERSION
manuale.html
README.md
```

## Database e dati

Il database runtime è `nightscope.db`, accanto all'applicazione. Non viene distribuito nel pacchetto: al primo avvio viene creato da `data/schema.sql` e dai seed locali. In sviluppo viene creato nella root del repository.

- città e alias GeoNames importati;
- cataloghi strumenti importati;
- oggetti Messier, immagini e descrizioni importati;
- un solo profilo predefinito `Occhio nudo`;
- cache meteo, storico osservazioni, cache VIIRS e assegnazioni profilo vuote;
- nessuna tabella legacy `Owned*`.

All'avvio NightScope verifica l'integrità con `PRAGMA integrity_check`, applica migrazioni idempotenti e usa `PRAGMA user_version` per registrare la versione schema applicata. Se il DB è corrotto, viene messo in quarantena e ricreato da `schema.sql` e dai seed locali. Se trova un vecchio `data/nightscope.db`, lo copia nella nuova posizione runtime per preservare i dati utente durante l'aggiornamento.

I sidecar runtime `user_preferences.json` e `location_cache.json` vivono nella stessa cartella di `nightscope.db`. Copiando la cartella NightScope completa si preservano profili, osservazioni, cache e preferenze. La password Earthdata resta nel vault di sistema e va reinserita sul nuovo computer.

## Dataset locali

I seed locali vivono in `astro_viewer/data/`:

- `cities15000.txt`: dump GeoNames incluso nel package.
- `countryInfo.txt`, `admin1CodesASCII.txt`: arricchimento paesi e regioni GeoNames.
- `messier_seed.csv`: catalogo Messier.
- `telescope_catalog_seed.csv`: catalogo telescopi.
- `eyepiece_catalog_seed.csv`: catalogo oculari, inclusi zoom.
- `barlow_catalog_seed.csv`: catalogo Barlow/focal extender.
- `light_pollution_seed.csv`: fallback locale per qualità cielo.
- `object_images_seed.csv`, `object_descriptions_seed.csv`: asset e contenuti osservativi.

Le fonti e i limiti sono documentati in `astro_viewer/data/DATA_SOURCES.md`.

## Import e manutenzione dati

Gli import CLI usano upsert/deduplicazione:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\import_cities.py astro_viewer\data\cities15000.txt --country-info astro_viewer\data\countryInfo.txt --admin1-codes astro_viewer\data\admin1CodesASCII.txt
.\.venv\Scripts\python.exe astro_viewer\tools\import_telescope_catalog.py astro_viewer\data\telescope_catalog_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_eyepiece_catalog.py astro_viewer\data\eyepiece_catalog_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_eyepiece_catalog.py astro_viewer\data\barlow_catalog_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_light_pollution.py astro_viewer\data\light_pollution_seed.csv
.\.venv\Scripts\python.exe astro_viewer\tools\import_object_content.py astro_viewer\data\object_descriptions_seed.csv
```

I report generati dagli strumenti sono output locali e non vengono versionati. Se necessari, gli script li ricreano in `astro_viewer/reports/`.

## Note operative

- `dist/`, `build/`, `logs/`, cache Python e report generati non sono parte del repository.
- `nasa_login.txt` non deve essere committato.
- Le credenziali Earthdata vengono salvate tramite vault di sistema quando disponibile; non vengono salvate nel database. Su un altro computer vanno reinserite.
- PyInstaller è il percorso di build supportato.

## Manuale utente

Il manuale sintetico per l'utente finale è in [manuale.html](manuale.html).
