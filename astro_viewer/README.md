# NightScope

Applicazione desktop Windows per astronomia osservativa, costruita con Python, PySide6, Qt Quick/QML, SQLite embedded, Skyfield, Astropy-ready boundaries e Open-Meteo.

## Avvio

```powershell
.\.venv\Scripts\python.exe astro_viewer\main.py
```

## Verifica rapida

```powershell
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m unittest discover -s astro_viewer\tests
```

## Stato Fase 2

- UI QML funzionante con dark theme, card moderne e navigazione tra pagine.
- Database SQLite locale in `data/nightscope.db` con `City`, `MessierObject`, `WeatherCache` e `ObservationHistory`.
- Catalogo Messier offline in `data/messier_seed.csv`, importato nel database al bootstrap.
- Ephemeris Skyfield locale in `data/skyfield/de421.bsp` per funzionamento astronomico offline.
- Calcoli reali Skyfield per Sole, Luna, Mercurio, Venere, Marte, Giove, Saturno, Urano e Nettuno.
- Visibilita Messier calcolata da RA/Dec del database con `skyfield.api.Star`.
- Meteo reale Open-Meteo per le prossime 24 ore, con cache SQLite e fallback in assenza rete.
- Indice di qualita osservativa 0-100 basato su nuvole, precipitazioni, vento, umidita e fase lunare.
- Selezione automatica del miglior oggetto della notte.
- Calcoli strumentali per ingrandimento, campo reale e pupilla d'uscita.
- Suggerimenti per oculare, Barlow e difficolta osservativa.
- Storico osservazioni salvato in SQLite dalla pagina dettaglio.
- Cataloghi locali per telescopi, oculari e Barlow.
- Profili attrezzatura con cambio rapido del setup attivo.
- Stima locale di Sky Quality con scala Bortle, magnitudine limite e brillanza cielo.
- Score separati per Planetary e Deep Sky.
- Stima seeing e trasparenza da forecast meteo.
- Night Planner automatico con sequenza osservativa.
- Sky map minimale per Nord, Sud, Est e Ovest.
- Notifiche intelligenti generate dal planner.

## Servizi principali

- `SkyfieldAstronomyEngine`: confina ephemeris, sorgere/tramonto, transiti, alt/az, fase lunare, opposizioni/congiunzioni ed eclissi lunari.
- `OpenMeteoWeatherService`: usa `/v1/forecast` con `forecast_hours=24` e variabili orarie Open-Meteo.
- `LocationService`: supporta citta SQLite, coordinate manuali e tentativo WinRT per posizione Windows.
- `ObservingScoreService`: calcola score osservativo e miglior oggetto della notte.
- `EquipmentService`: calcola combinazioni telescopio/oculare e suggerimenti osservativi.
- `LightPollutionService`: stima Bortle offline e cache `SkyQualityEstimate`; boundary isolato per futuri dataset VIIRS/World Atlas.
- `SeeingTransparencyService`: stima seeing e transparency da vento, nuvole, umidita e visibilita.
- `AdvancedObservingService`: calcola `Planetary Score` e `Deep Sky Score`.
- `NightPlannerService`: ordina gli oggetti visibili in una sequenza osservativa.
- `SkyMapService`: raggruppa target visibili per direzione cardinale.
- `NotificationService`: genera promemoria osservativi.

## Note dati

Il catalogo Messier seed e derivato dalla tabella pubblica della pagina Wikipedia "Messier object" e viene salvato localmente per uso offline. I parametri Open-Meteo e le routine Skyfield seguono la documentazione ufficiale corrente.

Per l'inquinamento luminoso sono state valutate fonti pubbliche come VIIRS/DNB e il World Atlas of Artificial Night Sky Brightness. In questa fase l'app usa una stima locale conservativa per garantire uso offline; il servizio e gia separato per sostituire la stima con lookup raster/API senza toccare UI o ViewModel.
