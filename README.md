# NightScope

NightScope è un'app desktop Windows per astronomia osservativa. Combina calcoli astronomici locali, profili di equipaggiamento, meteo orario, stima del cielo locale e suggerimenti pratici per pianificare una sessione visuale.

L'obiettivo non è sostituire atlanti o software planetari completi, ma rispondere rapidamente alla domanda: cosa vale la pena osservare stanotte, da questa località, con questo setup?

## Funzionalità principali

- Dashboard Home con qualità osservativa, Luna, meteo osservativo, punteggi planetari, cielo profondo e Sky Compass.
- Sky Compass come prima guida pratica della Home: indica dove iniziare, spiega perché quella zona è consigliata e mostra target principali e alternative; non è un planetario.
- Piano osservativo consigliato: selezione per qualità dei target e visualizzazione in ordine cronologico; altri pianeti visibili e oggetti di cielo profondo restano filtrati per profilo attivo.
- Dettaglio oggetto con finestra osservativa, descrizione, configurazione consigliata, motivazioni e ciclo lunare.
- Calcoli Skyfield reali per Sole, Luna, pianeti, fasi lunari, eventi e coordinate alt/az.
- Pagina `Oggetti celesti` per esplorare il catalogo locale con ricerca, filtri,
  colonna `Utile (≥15°)`, visibilità mensile e apertura del dettaglio oggetto.
- Catalogo offline generico con oggetti Messier e Sistema Solare, pronto per futuri cataloghi Caldwell/NGC/IC.
- Meteo Open-Meteo con cache SQLite, retry controllato sui timeout e fallback controllato.
- Sezione Meteo `Trasparenza atmosferica` con AOD NASA MAIAC opzionale da Earthdata, display-only e separata da OpenAQ.
- Sezione Meteo `Atmosfera locale` con dati OpenAQ opzionali e display-only per PM2.5, PM10, limpidezza, fonte e freschezza della misura.
- Stima seeing/trasparenza da nuvolosità, vento, raffiche, umidità, visibilità e dew point.
- Stima qualità cielo con Bortle/SQM locale e supporto opzionale ai dati NASA VIIRS Black Marble tramite Earthdata.
- Località configurabile da posizione Windows, fallback online approssimato, ricerca città GeoNames offline o coordinate manuali.
- Pagina `Provider dati` per configurare accessi opzionali a servizi esterni, inclusi Earthdata NASA e OpenAQ.
- Profili di equipaggiamento con cataloghi separati per telescopi, oculari e Barlow.
- Recommendation Engine v2 con setup pratici, posizioni reali per oculari zoom e presentazione separata tra visibilità e osservazione consigliata.
- Database SQLite embedded inizializzato da seed CSV locali.
- Build Windows tramite PyInstaller.

## Stato

Versione corrente: `1.5.5`.

La serie `1.1` è chiusa a `1.1.15` come ultimo stato stabile prima del ciclo 1.2.
La serie `1.3` introduce il layer `ObservationConditionsService` e separa il
ranking specifico del Planner in `PlannerScoringService`, preservando i
comportamenti osservativi esistenti. AOD NASA e particolato OpenAQ possono
essere rappresentati come diagnostica neutra del layer condizioni, ma non
alimentano ancora punteggi o raccomandazioni.
Lo step `1.3.8e` completa l'hardening dell'export diagnostico NSOM interno:
snapshot coerenti per i target Planner, semantica distinta per dati VIIRS reali,
dataset locali derivati e fallback, serializzazione JSON stretta, refresh dello
snapshot dopo completamento OpenAQ/AOD e nessuna esposizione QML, scrittura file,
logging automatico, segnale o ricomputazione di Planner/Home/Equipment/Sky
Compass.
La serie `1.4` avvia l'implementazione reale del core NSOM come codice interno:
DTO immutabili per Universe/Sky/Observer/Session/Opportunity/Confidence,
adattatori dai runtime object correnti e compatibilità JSON stretta. In `1.4.0`
questo layer non sostituisce ancora ranking Planner, Home, Best Object, Sky
Compass o Recommendation Engine: la sostituzione dei percorsi legacy parte dai
commit successivi.
Lo step `1.4.0b` indurisce il core senza avviare la sostituzione Planner:
`ObservationOpportunity` usa `SessionViability` come unica sorgente di verità,
gli adapter rifiutano input sessione conflittuali e la serializzazione JSON
stretta resta garantita anche con valori runtime non finiti.
Lo step `1.4.1` introduce il primo consumer reale: un path Planner NSOM
sperimentale, interno e spento di default. Quando il flag resta disattivato il
Planner continua a usare `PlannerScoringService`; quando viene attivato, i
candidati Planner vengono trasformati in `ObservationOpportunity` e ordinati sul
valore NSOM, mantenendo `RecommendationConfidence` come metadato parallelo che
non modifica il punteggio.
Lo step `1.4.2` pulisce la ownership dell'adapter Planner NSOM: il path
sperimentale non deriva piu' Luna, inquinamento luminoso o osservabilita' da
`PlannerScoringService.condition_breakdown`, ma costruisce
`ObservationEnvironment` da input runtime gia' disponibili al Planner. La
capacita' osservatore usa anche i dati del telescopio corrente per produrre un
`PracticalTargetValue` diverso senza modificare `ObservableTargetValue`; il flag
Planner NSOM resta interno e disattivato di default.
Lo step `1.4.3` aggiunge fixture e helper interni di confronto tra ranking
Planner legacy e ranking Planner NSOM sperimentale. Il confronto restituisce
dizionari compatibili JSON con punteggi, delta di punteggio/rank e componenti
NSOM principali, senza scrivere file, fare logging automatico, esporre QML o
abilitare il path NSOM di default.
Lo step `1.4.4` aggiunge fixture comportamentali in cui NSOM puo' divergere
intenzionalmente dal ranking Planner legacy: protezione di pianeti/Luna dai
penalty di fondo cielo, maggiore sensibilita' di galassie e nebulose diffuse,
separazione tra valore target e sessione, influenza dell'equipaggiamento sul
solo `PracticalTargetValue` e neutralita' del `RecommendationConfidence`.
Lo step `1.4.5` aggiunge spiegazioni developer-facing per il path Planner NSOM
sperimentale: ogni `ObservationOpportunity` puo' esportare target, punteggio
finale, componenti NSOM, fattori limitanti/positivi e metadati di confidence in
forma compatibile JSON. La confidence resta una spiegazione di trust separata e
non diventa un fattore di score; il flag Planner NSOM resta interno e spento di
default, senza esposizione QML, scrittura file o logging automatico.
Lo step `1.4.6` usa comparison ed explanation per una inspection di calibrazione
developer-only: scenari nominati per cielo brillante, sessione buona/scarsa,
telescopi piccoli/grandi, condizioni favorevoli a pianeti o deep-sky e target
Luna producono output JSON con ranking NSOM, riferimento legacy, componenti,
fattori e aspettativa comportamentale. L'ispezione non abilita il Planner NSOM,
non scrive file, non logga automaticamente e non espone nulla a QML.
Lo step `1.4.7` aggiunge il report developer-facing
`docs/NSOM_PLANNER_COMPARISON_REPORT.md` e il relativo tooling deterministico:
120 scenari confrontano scoring Planner legacy e scoring Planner NSOM
sperimentale con spiegazioni, rank delta, componenti disponibili e componenti
legacy marcati come non disponibili quando non esposti. Il report non modifica
i pesi NSOM, non abilita il flag Planner NSOM e non viene collegato al runtime.
Lo step `1.4.8` aggiunge il report developer-facing
`docs/NSOM_MATHEMATICAL_TRACE_REPORT.md`: per ogni scenario deterministico
esistente mostra la pipeline matematica NSOM completa, da
`IntrinsicTargetQuality` fino al ranking Planner finale, con input, formule,
calcoli intermedi, fattori positivi/limitanti e confronto legacy limitato ai
campi realmente disponibili. `RecommendationConfidence` resta fuori dalla
pipeline matematica come metadato diagnostico; il tooling non abilita Planner
NSOM, non modifica scoring, non scrive file a runtime, non logga
automaticamente e non espone QML.
Lo step `1.4.8b` indurisce il report matematico NSOM per evitare letture
fuorvianti durante la calibrazione: i gruppi con tutti gli score NSOM a zero
sono marcati come tie non azionabili, il rank stabile non viene piu' indicato
come fattore positivo, le formule di dettaglio per fondo Luna, fondo cielo,
trasparenza, geometria e capacita' osservatore sono mostrate o marcate come
adapter-derived/unavailable, e le fixture deterministiche coprono
`observing_window_quality` a `1.0`, `0.5` e `0.0`. Le statistiche di dominanza
sono descritte come frequenze di apparizione, non come prova di peso o
sensibilita'. Il tooling resta developer-only e non cambia Planner, UI, QML o
scoring runtime.
Lo step `1.4.9` aggiunge evidenza prima della calibrazione: test di formula
parity confrontano le sub-formule del report con i valori prodotti dal servizio
NSOM Planner, inclusi Moon background, sky background, trasparenza,
geometria/horizon, observing window e SessionViability. Fixture di sensitivity
isolate verificano direzione e ownership per ObserverCapability, sky
background, Moon background, SessionViability, observing window, horizon e
confidence. Il report traccia expected/reported per le formule ricostruibili e
mantiene adapter-derived/unavailable dove gli input non sono sufficienti. Non
cambia scoring, ranking, Planner runtime, UI o QML.
Lo step `1.5.0` aggiunge una review developer-only di `ObserverCapability`
prima di qualsiasi tuning: fixture controllate isolano aperture-only,
focal-length-only, mount/tracking-only, field-of-view-only e practical
comfort/setup-only su pianeta, Luna, galassia, nebulosa diffusa, ammasso aperto
e globulare. La review conferma che `ObservableTargetValue` resta invariato e
che il flat mean corrente produce delta di summary uniformi tra classi target;
per questo la pesatura target-specific resta un punto da decidere prima della
calibrazione. Nessun peso viene modificato e il Planner NSOM resta spento di
default.
Lo step `1.5.1` introduce la proiezione sperimentale interna `Q_target`:
`ObserverCapability` resta un profilo multidimensionale, ma il Planner NSOM
default-off può proiettarlo con pesi espliciti per classe target quando serve
un singolo moltiplicatore di `PracticalTargetValue`. I profili coprono pianeta,
Luna, galassia, nebulosa diffusa, ammasso aperto e globulare; il report mostra
profilo completo, flat summary, `Q_target`, pesi usati e delta rispetto al flat
mean. Nessun peso finale viene calibrato, il Planner legacy resta invariato e
il flag NSOM Planner resta spento.
Lo step `1.5.2` aggiunge soglie developer-only per review di calibrazione:
rank delta grandi, degrado inatteso di pianeti/Luna, protezione inattesa dei
target deep-sky sotto cielo brillante, dominanza osservatore, gruppi all-zero e
casi missing/invisible window sono classificati come `expected`, `review` o
`warning`. Il report confronta anche la policy blocked-session corrente
hard-block con una lettura alternativa non azionabile basata su
`PracticalTargetValue`. Le soglie non calibrano pesi, non cambiano Planner
runtime e non abilitano NSOM Planner di default.
Lo step `1.5.3` aggiunge il decision log developer-only
`docs/NSOM_CALIBRATION_DECISION_LOG.md`: ogni warning/review della matrice di
calibrazione viene collegato a una decisione `accepted`, `deferred`,
`needs_calibration` o `needs_policy_decision`, con layer NSOM, classe target,
motivazione, intenzionalita' e impatto sul default-on. Il log marca G09/G20 e
missing-window come policy aperte, G10/G11 pianeti e demotion ricorrenti degli
ammassi aperti come calibrazione mirata futura, e accetta la promozione dei
globular cluster con grande telescopio. Non modifica score, pesi o runtime.
Lo step `1.5.4` risolve le policy non-actionable che bloccavano il default-on:
G09 resta hard-block con `ObservationOpportunity = 0.0`, G20 resta target
invisibile non azionabile, e G19 conserva il fallback conservativo
`observing_window_quality = 0.5` ma viene marcato
`actionable_with_uncertain_timing`. L'ordine preservato per i casi non
azionabili e' `non_actionable_preserved_order`, diagnostico-only, non usato per
ranking runtime e non esposto a QML. I blocker restanti sono solo calibrazioni
mirate.
Lo step `1.5.5` risolve il blocker mirato `small-equipment-planet-q-target`:
la proiezione sperimentale `Q_target` applica un floor solo per pianeti con
equipaggiamento piccolo ma ancora osservabile, distinguendo "planet observable"
da "planet optimal detail". La calibrazione resta nel layer
`ObserverCapability`/`PracticalTargetValue`: non cambia `ObservableTargetValue`,
`EffectiveObservability`, `SessionViability`, `RecommendationConfidence`,
Planner legacy, QML o il flag Planner NSOM default-off. I report developer-only
e il decision log sono aggiornati; il blocker default-on residuo e'
`open-cluster-recurring-demotion`.

La UI e il flusso principale sono considerati stabili per l'uso osservativo visuale. Le aree più sperimentali restano:

- dati VIIRS NASA, perché dipendono da connessione, credenziali Earthdata e disponibilità LAADS;
- dati NASA AOD sperimentali nella sezione Meteo `Trasparenza atmosferica`: sono informativi, dipendono da disponibilità MAIAC/cloud mask e non alimentano ancora punteggi o raccomandazioni;
- OpenAQ, opzionale e usato solo per mostrare dati locali PM2.5/PM10 nella pagina Meteo; la freschezza della misura decide se il dato può essere presentato come attuale;
- qualità dei cataloghi strumenti, da verificare sempre per varianti regionali e modelli commerciali specifici;
- descrizioni e note osservative, che possono essere arricchite nel tempo.

Il numero versione applicativo è tracciato nel file root `VERSION`.

La direzione matematica di lungo periodo per scoring, pianificazione e logica
osservativa è fissata in
[NSOM 1.0 - NightScope Observation Model](docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md).
Le future modifiche a scoring e Planner dovrebbero essere verificate contro
quel modello prima dell'implementazione.

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
- Dopo un test Earthdata riuscito, la pagina Meteo può mostrare anche `Trasparenza atmosferica` da NASA MAIAC AOD. Il dato resta display-only, viene mantenuto come risultato processato compatto con TTL locale e non modifica Recommendation Engine, Planner, Sky Compass, seeing, trasparenza meteo o punteggi.
- La API key OpenAQ viene salvata tramite vault di sistema quando disponibile; dopo un test connessione riuscito NightScope ricorda un'impronta sicura della key verificata e la pagina Meteo la usa solo per la sezione informativa `Atmosfera locale`, mai per Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi. Misure OpenAQ storiche non vengono presentate come condizioni atmosferiche attuali.
- PyInstaller è il percorso di build supportato.

## Manuale utente

Il manuale sintetico per l'utente finale è in [manuale.html](manuale.html).
