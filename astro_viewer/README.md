# NightScope

NightScope e una applicazione desktop Windows per astronomia osservativa, costruita con Python, PySide6, Qt Quick/QML, SQLite embedded, Skyfield, Astropy e Open-Meteo.

## Stato RC1

- UI QML dark theme con Home, dettaglio oggetto, calendario, meteo, location e strumenti.
- Database SQLite locale con citta, Messier, cataloghi strumenti, cache meteo, profili e storico osservazioni.
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
- `LocationService`: citta SQLite, coordinate manuali e posizione Windows.
- `ObservingScoreService`: qualita osservativa e miglior oggetto della notte.
- `LightPollutionService`: stima Bortle offline con boundary per fonti future.
- `SeeingTransparencyService`: stima seeing e transparency dal forecast.
- `NightPlannerService`: sequenza osservativa ottimizzata.
- `EquipmentService`: calcoli strumenti, oculari, Barlow e difficolta.

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
