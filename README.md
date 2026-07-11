# NightScope

NightScope è un'app desktop Windows per astronomia osservativa. Combina calcoli astronomici locali, profili di equipaggiamento, meteo orario, stima del cielo locale e suggerimenti pratici per pianificare una sessione visuale.

L'obiettivo non è sostituire atlanti o software planetari completi, ma rispondere rapidamente alla domanda: cosa vale la pena osservare stanotte, da questa località, con questo setup?

## Funzionalità principali

- Dashboard Home con qualità osservativa, Luna, meteo osservativo, punteggi planetari, cielo profondo e Sky Compass.
- Sky Compass come guida live della Home: ogni minuto valuta gli oggetti realmente osservabili adesso, combina qualità e concentrazione per direzione e mantiene piano/Best Object come contesto, non come bonus dominante.
- Piano osservativo consigliato: quattro opportunità NSOM selezionate per qualità e poi ordinate cronologicamente, usando per ogni target lo strumento realmente scelto dal profilo multi-equipaggiamento.
- Home inferiore state-aware: separa sequenza consigliata, finestra da
  monitorare e sessione sconsigliata; mostra setup compatti e una tabella unica
  degli altri oggetti senza esporre score grezzi.
- Dettaglio oggetto con finestra osservativa, descrizione, configurazione consigliata, motivazioni e ciclo lunare.
- Calcoli Skyfield reali per Sole, Luna, pianeti, fasi lunari, eventi e coordinate alt/az.
- Pagina `Oggetti celesti` per esplorare il catalogo locale con ricerca, filtri,
  colonna `Utile (≥15°)`, visibilità mensile e apertura del dettaglio oggetto.
- Catalogo offline generico con oggetti Messier e Sistema Solare, pronto per futuri cataloghi Caldwell/NGC/IC.
- Meteo Open-Meteo con cache SQLite, retry controllato sui timeout e fallback controllato.
- Sezione Meteo `Aerosol atmosferico` con AOD NASA MAIAC opzionale da Earthdata,
  freschezza misura e fonte satellite, separata da OpenAQ.
- Sezione Meteo `Particolato locale` con dati OpenAQ opzionali per PM2.5,
  PM10, aria locale, fonte e freschezza della misura.
- Stima seeing/trasparenza da nuvolosità, vento, raffiche, umidità, visibilità e dew point.
- Stima qualità cielo con Bortle/SQM locale e supporto opzionale ai dati NASA VIIRS Black Marble tramite Earthdata.
- Località configurabile da posizione Windows, fallback online approssimato, ricerca città GeoNames offline o coordinate manuali.
- Pagina `Provider dati` per configurare accessi opzionali a servizi esterni, inclusi Earthdata NASA e OpenAQ.
- Profili di equipaggiamento con cataloghi separati per telescopi, oculari e Barlow.
- Recommendation Engine v2 con setup pratici, posizioni reali per oculari zoom e presentazione separata tra visibilità e osservazione consigliata.
- Database SQLite embedded inizializzato da seed CSV locali.
- Build Windows tramite PyInstaller.

## Stato

Versione corrente sorgente: `1.18.7`.

Distribuzione Windows corrente: `1.18.6`.

Il backend NSOM e' chiuso per lo scope corrente. Le superfici principali usano
ora i rispettivi percorsi NSOM o boundary NSOM espliciti:

- Planner: ranking `ObservationOpportunity`.
- Home `recommendedDeepSky`: tutti i target utili della notte, ordinati per
  `ObservableTargetValue`; `homeVisibleAlternatives` unifica pianeti e cielo
  profondo escludendo le quattro tappe del piano.
- Home inferiore: `homeNightPlanOverview` proietta stato sessione, riepilogo
  multi-equipment, piano compatto e righe alternative lette direttamente dalla
  QML della Home.
- Best Object: selezione Home-specific basata su concetti NSOM.
- Advanced Observing: snapshot backend NSOM parallelo.
- Sky Compass: direzione live basata su `ObservableTargetValue`, altitudine
  corrente e densita' dei target osservabili ora.
- Detail/Object: payload interno NSOM separato.
- ObservationConditions: AOD/OpenAQ default-on quando i dati provider sono gia'
  disponibili e passano i gate di qualita'.
- Equipment: resta setup-local con boundary ObserverCapability espliciti, senza
  replacement path NSOM separato.

`docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md` e' il riepilogo corrente dello stato
backend NSOM. `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md` documenta la
rimozione dei report/tool/test storici di migrazione eseguita in `1.15.2`.

La UI/QML visibile resta compatibility-first fuori dalle superfici riviste. In
`1.16.0` la pagina Meteo ha ricevuto un primo passaggio semantico sui dati
condizioni AOD/OpenAQ, senza nuovi pannelli NSOM e senza spiegazioni visibili del
ranking. I punteggi display legacy/base restano campi di compatibilita' dove
servono alla presentazione. Eventuali spiegazioni NSOM complete sono lavoro
futuro di design.

In `1.16.1` la cache NASA Black Marble VIIRS viene rivalidata ogni 7 giorni:
il valore salvato resta disponibile durante il controllo e in caso di errore
NASA. Il pulsante Meteo `Aggiorna` avvia anche i controlli cache-aware VIIRS e
AOD; AOD mantiene la propria TTL di 18 ore.

In `1.17.1` le cache provider AOD e VIIRS riusano una misura valida anche quando
la posizione Windows oscilla entro 500 metri. La policy spaziale non modifica
le chiavi usate per identificare i refresh asincroni; evita soltanto fetch NASA
duplicati per la stessa area. Il controllo AOD avviene prima di avviare il
worker, quindi una cache fresca non presenta uno stato di recupero transitorio.

La stessa patch distingue inoltre la ricerca automatica della posizione dalla
sua reale assenza nella parte alta Home. Sessione, Meteo, condizioni planetarie,
cielo profondo e Luna mostrano uno stato di attesa coerente; i testi delle card
possono occupare due righe senza modificare le altezze correnti. In assenza di
dati non vengono presentati suggerimenti favorevoli come se le condizioni
fossero state calcolate.

In `1.17.2` il refresh Open-Meteo distingue gli errori temporanei dagli errori
client permanenti. Timeout, problemi di rete, HTTP `408`/`425`/`5xx` e risposte
incomplete mantengono la cache e programmano un retry forzato dopo 5 minuti;
HTTP `4xx` permanenti e `429` restano sul normale controllo orario. Il log
include lo status HTTP senza esporre coordinate o parametri della richiesta.

In `1.18.0` la parte bassa Home usa il contratto `homeNightPlanOverview`: la
card piano e' state-aware, gli stati `monitor` e `discouraged` non mostrano una
falsa sequenza numerata, e pianeti/cielo profondo fuori piano sono una tabella
unica filtrabile senza score o motivazioni lunghe. La distribuzione Windows
`dist/NightScope` e' stata rigenerata su richiesta con PyInstaller `6.21.0`:
bundle `VERSION` `1.18.0`, smoke e QML smoke dell'eseguibile con exit code `0`.

In `1.18.1` la notte osservativa non usa piu' fasce orarie generiche. Skyfield
calcola per la posizione attiva il tramonto locale e l'alba successiva; lo
stesso intervallo limita campionamento astronomico, meteo, seeing, score,
Planner, Home e Sky Compass. Open-Meteo fornisce 48 ore e le ore vengono
selezionate tramite timestamp completi, quindi finestre discontinue come
`05:00-22:00` non possono essere costruite. Giorno polare e buio continuo sono
stati espliciti. La distribuzione Windows non e' stata rigenerata in questo
passaggio.

In `1.18.2` i calcoli astronomici pesanti non occupano piu' il thread Qt. La
geometria Luna-target usa una timeline Skyfield batch e viene riutilizzata tra
Planner e diagnostica; il refresh freddo costruisce in background uno snapshot
con notte, oggetti, Luna, eventi e visibilita' mensile. Anche il tick live Sky
Compass e il reload deep-sky VIIRS applicano soltanto risultati ancora validi
per request id e posizione. Scoring, payload QML e UI visibile restano invariati.

In `1.18.3` il condizionamento per inquinamento luminoso non tronca piu' a dieci
gli oggetti deep-sky ancora utili: l'intero pool raggiunge Home e Sky Compass
prima dell'esclusione dei quattro target del piano. La lista Home degli altri
oggetti trattiene inoltre lo scroll di mouse e touchpad quando il puntatore e'
sulla lista scrollabile, senza trasferirlo alla pagina quando raggiunge un
estremo. La distribuzione Windows e' stata rigenerata su richiesta con bundle
`VERSION` `1.18.3`; smoke e QML smoke dell'eseguibile terminano con exit code
`0`.

In `1.18.4` gli orari astronomici esposti con precisione al minuto conservano
anche il minuto che contiene il tramonto calcolato con secondi da Skyfield. Home
e Planner non ripiegano quindi sulla fine della finestra quando il momento
migliore coincide con il tramonto. La migliore finestra meteo viene inoltre
limitata all'alba locale esatta, senza produrre label come `04:00-07:00` quando
la notte termina alle `06:12`. La distribuzione Windows `1.18.4` e' stata poi
rigenerata manualmente per la verifica visuale.

Anche il primo recupero Open-Meteo successivo allo snapshot astronomico usa ora
un worker: il thread QML mantiene lo stato di caricamento e applica il risultato
solo al completamento, senza attendere i timeout di rete su un avvio senza
cache.

La difficolta' osservativa dei pianeti distingue inoltre i target: Mercurio,
Marte, Urano e Nettuno non ereditano piu' automaticamente `Facile` dalla sola
categoria Pianeta. La classe considera target, apertura, altezza e tipo di
strumento e continua a entrare nel vincolo pratico del Planner NSOM.

I refresh AOD e OpenAQ in volo sono ora location-safe anche durante un cambio
posizione: la presentazione precedente viene rimossa subito e un completamento
con chiave obsoleta avvia automaticamente il recupero per la localita' corrente.
OpenAQ ricontrolla inoltre la validita' delle credenziali prima di applicare il
risultato.

Il grafico e il dettaglio orario della pagina Meteo consumano ora
`observingWeatherHourly`, cioe' soltanto i campioni della notte astronomica
attiva. Il payload completo a 48 ore resta disponibile internamente per
compatibilita', ma non viene piu' presentato sotto una label notturna.

Il fallback legacy di Sky Compass resta disponibile se la selezione NSOM genera
un errore, ma il passaggio viene ora registrato come warning diagnostico invece
di essere silenzioso; forma e contenuto del payload QML di fallback non cambiano.

Lo stack Earthaccess include inoltre un constraint `botocore` compatibile con
`aiobotocore 3.7.x`; la `.venv` di riferimento usa `botocore 1.43.0` e supera
`python -m pip check` senza dipendenze rotte.

In `1.18.5` le finestre dei target campionati includono l'estremo astronomico
esatto e stimano il passaggio della soglia tra due campioni. Le righe Home non
mostrano quindi piu' intervalli nulli come `18:48-18:48` o `05:48-05:48`; il
campione all'alba serve solo come confine e non puo' diventare il momento
migliore dell'oggetto. La distribuzione Windows resta alla `1.18.4`.

La descrizione Bortle della parte alta e della lista Home usa ora un'unica
classificazione. Bortle 7 e' presentato coerentemente come `transizione
suburbana-urbana`, senza alternare le precedenti etichette `cielo urbano` e
`cielo suburbano luminoso`.

In `1.18.6` grafico e dettaglio della pagina Meteo mostrano una finestra mobile
delle prossime 24 ore a partire dall'ora locale corrente. Le ore appartenenti
alla notte osservativa attiva hanno un accento distinto e la selezione del
dettaglio resta legata al timestamp quando il timer orario fa scorrere la
previsione. Score, seeing, trasparenza, Home e ranking NSOM continuano a usare
soltanto `observingWeatherHourly`. La distribuzione Windows `1.18.6` e' stata
poi rigenerata manualmente per la verifica visuale.

In `1.18.7` la lista Home fuori piano e' ordinata prima per inizio della
finestra osservativa e soltanto a parita' per momento migliore, categoria e
nome. Nel dettaglio Meteo il cyan distingue l'ora selezionata dal teal delle ore
notturne e la scrollbar orizzontale sovrapposta alle schede non viene piu'
mostrata. La distribuzione Windows resta alla `1.18.6`.

`1.17.0` avvia la revisione della parte alta della Home con un contratto
`homeObservingOverview` dedicato. Le card visibili separano ora stato e finestra
della sessione, score solo meteo, condizioni descrittive planetarie/deep-sky e
impatto lunare. I punteggi numerici di categoria non sono piu' esposti in questa
sezione. Sky Compass usa lo stesso stato di sessione per distinguere una
direzione consigliata da un semplice orientamento geometrico e mostra i tipi
target in italiano. `Piano della notte` resta il prossimo capitolo separato.

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

I sidecar runtime `user_preferences.json`, `location_cache.json` e
`nasa_aod_cache.json` vivono nella stessa cartella di `nightscope.db`. I valori
VIIRS elaborati sono invece nella tabella `SkyQualityEstimate`. Copiando la
cartella NightScope completa si preservano profili, osservazioni, cache e
preferenze. La password Earthdata resta nel vault di sistema e va reinserita
sul nuovo computer.

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
- Dopo un test Earthdata riuscito, la pagina Meteo può mostrare anche `Aerosol
  atmosferico` da NASA MAIAC AOD. Il dato viene mantenuto come risultato
  processato compatto con TTL locale e resta separato da seeing e trasparenza
  meteo; `ObservationConditionsService` può usarlo come input condizioni solo
  quando i gate provider-quality lo accettano.
- La API key OpenAQ viene salvata tramite vault di sistema quando disponibile;
  dopo un test connessione riuscito NightScope ricorda un'impronta sicura della
  key verificata e la pagina Meteo può mostrare `Particolato locale`. OpenAQ PM
  resta fallback/context rispetto ad AOD e non viene sommato come seconda
  sorgente aerosol indipendente. Misure OpenAQ storiche non vengono presentate
  come condizioni atmosferiche attuali.
- PyInstaller è il percorso di build supportato.
- Il workflow di test per sviluppo e review e' documentato in
  `docs/TESTING.md`; la full suite parallela usa `pytest-xdist` via
  `requirements-dev.txt`.

## Manuale utente

Il manuale sintetico per l'utente finale è in [manuale.html](manuale.html).
