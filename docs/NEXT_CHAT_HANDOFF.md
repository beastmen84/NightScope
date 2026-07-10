# NightScope NSOM - Punto Della Situazione Per Nuova Chat

Data: 2026-07-10  
Workspace: `C:\Users\beast\PycharmProjects\NightScope`  
Versione corrente sorgente: `1.17.1`
Distribuzione Windows corrente: `1.17.1`
Commit rilevanti prima di questo aggiornamento del handoff:

- `38e971d Document 1.17.1 Windows distribution build`
- `c3895dc Record Home startup state review`
- `190e095 Fix Home startup location states`
- `4e59e1f Fix provider cache reuse for location jitter`
- `792bd30 Record 1.17.0 build commit`
- `48a840e Document 1.17.0 Windows distribution build`
- `71abc8a Record Home UI completion commits`
- `b3f78db Make Home Sky Compass session-aware`
- `319e820 Migrate upper Home cards to overview contract`
- `8a1f318 Add Home overview presentation contract`
- `04f60e4 Release 1.16.1 VIIRS cache revalidation`
- `9debe8f Document 1.16.0 Windows distribution build`
- `a814c7c Release 1.16.0 Weather condition semantics`
- `efaf29c Clarify visible UI readiness meaning`
- `7e42f12 Document NSOM QML boundary audit`
- `d1da051 Evaluate catalogue raw score policy`
- `06603d2 Clarify backend raw score policy`
- `05397dc Update NSOM handoff state`
- `d84de3a Remove closed NSOM migration artifacts`

## Stato Breve

La migrazione backend NSOM per le superfici di raccomandazione principali e'
chiusa per lo scope corrente.

Report di chiusura principale:

- `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
- `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`

Il closeout dichiara:

- backend default-on blockers: nessuno;
- runtime behaviour changed by closeout: `False`;
- ready for visible UI redesign: `False`;
- UI/QML non toccata dal closeout backend `1.15.2`;
- `1.16.0` avvia solo un passaggio semantico Meteo su AOD/OpenAQ/freshness,
  senza pannelli NSOM o spiegazioni visibili del ranking;
- `1.16.1` aggiunge solo hardening della cache VIIRS e del refresh provider,
  senza modificare scoring, ranking o payload QML;
- `1.17.0` aggiunge il contratto read-only `homeObservingOverview` e collega le
  card superiori Home: stato sessione, score solo meteo, condizioni descrittive
  planetarie/deep-sky e impatto lunare circoscritto;
- Sky Compass e' ora state-aware nella presentazione: in sessione non
  consigliata resta orientamento geometrico, con tipi target localizzati e
  motivazioni neutrali; ranking e target non cambiano;
- la parte alta Home e' completata per lo scope `1.17.0`; `Piano della notte`
  resta fuori e sara' il capitolo successivo;
- `1.17.1` rende le cache provider AOD/VIIRS tolleranti al jitter della
  posizione Windows entro 500 metri e controlla la cache AOD prima di avviare
  il worker; chiavi asincrone, scoring, ranking e payload provider restano
  invariati;
- la stessa patch distingue in Home la ricerca posizione `pending` dalla reale
  assenza `unavailable`, usa copy neutro senza falsi suggerimenti favorevoli e
  consente due righe nelle card superiori senza cambiarne le dimensioni;
- report/tooling storici di migrazione rimossi in `1.15.2`;
- il closeout backend non introduce rete, logging automatico o scritture
  runtime; `1.16.1` cambia separatamente solo quando i provider gia' esistenti
  vengono controllati.

## Nota Di Review Sui Dati Home

Nello screenshot Home caricato con `1.17.0`, lo stato `Consigliata` e'
coerente con le soglie attuali: pioggia massima `61% < 65%`, indice meteo
`45 > 25` e nuvolosita' media `40% < 85%`, quindi non scatta un blocker.

La dicitura `Migliore finestra` indica pero' il blocco relativo di tre ore con
penalita' minore, non una finestra in cui ogni ora supera il gate di usabilita'.
Per questo puo' includere anche un'ora sfavorevole come il `100%` di nuvole
mostrato alle `00:00`. Non e' stato cambiato alcun algoritmo: copy e policy
andranno rivalutati sul prossimo screenshot solo con uno step esplicito.

## Superfici Backend NSOM Chiuse

Sono nello stato default-on previsto:

- Planner: `ObservationOpportunity` ranking;
- Home `recommendedDeepSky`: `ObservableTargetValue` ordering;
- Best Object: selezione Home-specific basata su concetti NSOM;
- Advanced Observing backend: proiezione categoria/observable;
- Sky Compass: direction policy basata su `ObservableTargetValue`;
- Detail/Object internal payload;
- AOD/OpenAQ condition scoring.

Le vecchie rollback constructor path interne sono state rimosse negli step
precedenti. Per AOD/OpenAQ resta invece un rollback esplicito di flag:

```python
ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)
```

## AOD/OpenAQ

Stato corrente:

- `ObservationConditionFeatureFlags.experimental_aerosol_scoring = True`;
- formula e pesi non sono stati cambiati nello switch default-on;
- lo switch scoring non introduce fetch provider; `1.16.1` fa invece
  schedulare al comando Meteo `Aggiorna` i normali controlli cache-aware;
- AOD e OpenAQ entrano nello score solo quando i dati sono gia' presenti e
  passano i gate provider-quality;
- AOD e OpenAQ non sono additivi: AOD e' primary quando eligible, OpenAQ PM e'
  fallback/context;
- confidence/provider confidence restano metadata e non scalano lo score;
- `stale=0.5` e' stato accettato come policy conservativa nel replay 1.14.18.
- In `1.16.0` la pagina Meteo presenta AOD come `Aerosol atmosferico` e
  OpenAQ come `Particolato locale`, con freschezza visibile; questo resta copy
  di dati condizioni, non una UI NSOM-aware.

Cache provider in `1.16.1`:

- VIIRS Black Marble usa stati `missing`, `fresh` e `stale`;
- `SkyQualityEstimate.updated_at` registra l'ultimo recupero VIIRS riuscito;
- la rivalidazione VIIRS avviene dopo 7 giorni;
- un valore stale resta subito disponibile e viene mantenuto se NASA fallisce;
- AOD resta separato con cache memory+JSON e TTL di 18 ore;
- il pulsante Meteo `Aggiorna` schedula entrambi i controlli senza bypassare
  cache VIIRS fresca o TTL AOD;
- i file satellitari originali restano temporanei e non sono conservati.

Attenzione importante:

- Il probe reale AOD/OpenAQ e' stato rimosso nel cleanup `1.15.2`; non
  ripristinarlo o lanciarlo da history salvo richiesta esplicita. Quel tool usa
  NASA/OpenAQ reali.
- Per audit offline rileggere i documenti base, il closeout e la cronologia Git;
  non introdurre nuove chiamate rete.

## Residui E Decisioni Non Bloccanti

Questi non bloccano il backend NSOM chiuso:

1. `AOD/OpenAQ real observing feedback`
   - Policy: monitorare risultati reali dopo l'uso del programma a valle della
     nuova implementazione NSOM, prima di qualunque tuning ulteriore.
   - Non fare tuning pesi adesso.

2. `Catalogue / Universe raw score semantics` valutato
   - I raw score/catalogue score restano input upstream backend.
   - Non sono esposti come score nel Catalogo Oggetti Celesti e non sono lo
     score Home complessivo gia' calcolato dopo le altre considerazioni.
   - Policy valutata nello scope corrente: `IntrinsicTargetQuality`, metadata
     catalogo/provenance, osservabilita' catalogo, payload Home e ranking NSOM
     sono gia' separati a sufficienza.
   - Chiuso per lo scope backend corrente: nessun nuovo
     `UniverseTargetProfile` runtime adesso; rivalutarlo solo se
     serviranno multi-catalogue provenance, calibrazione intrinseca o
     spiegazioni score visibili.

3. `Visible UI explanations`
   - La UI non va toccata automaticamente: ogni superficie richiede uno step
     esplicito.
   - Primo passaggio esplicito avviato in `1.16.0`: solo WeatherPage
     condition-data semantics (`Aerosol atmosferico`, `Particolato locale`,
     freshness e confidence localizzata).
   - L'audit dice esplicitamente `Ready for visible UI redesign: False`, ma
     questo descrive il closeout backend storico, non vieta gli step UI
     successivi esplicitamente autorizzati.
   - `1.17.0` introduce `homeObservingOverview` come contratto presentazionale
     dedicato e lo usa nelle card superiori Home. Non e' un pannello di debug e
     non espone spiegazioni tecniche complete del ranking target.
   - Nella parte alta Home `advancedScores` non e' piu' mostrato: i valori
     numerici planetario/deep-sky restano backend diagnostico, mentre la UI usa
     etichette e fattori descrittivi. Lo score numerico rimasto e' dichiarato
     nella card `Meteo osservativo`.
   - Planner, liste Home, Best Object e Sky Compass continuano a usare i
     rispettivi payload (`nightPlan`, `recommendedDeepSky`,
     `bestObjectOfNight`, `skyCompass`) senza esporre payload diagnostici NSOM.
   - Detail/Object resta interno: nessuna property `detailObjectNsom` e nessun
     campo NSOM aggiunto a `selectedObject`.
   - Advanced Observing ha una property Qt read-only `advancedObservingNsom`
     disponibile sul controller ma non letta direttamente dai QML.
   - Resta necessaria la verifica visuale della nuova Home sulla `dist` solo
     quando richiesta dall'utente.
   - Prima di estendere le spiegazioni NSOM ad altre superfici bisogna decidere:
     1. quali spiegazioni NSOM mostrare davvero;
     2. se sostituire, affiancare o nascondere i vecchi score display;
     3. copy/testi comprensibili e non tecnici per fattori, confidence e fonti;
     4. contratto dati QML prima di cambiare QML;
     5. verifica grafica Home, Detail, Planner e Sky Compass.

4. `Equipment recommendations`
   - Chiuso come setup-local.
   - `EquipmentService` resta owner concreto di oculari/Barlow/binocoli.
   - Non introdurre ora un replacement path NSOM Equipment.

5. `ObservationConditions prepared-object cache`
   - Non e' codice morto.
   - Resta boundary attivo raw/display per compatibilita' e presentation.
   - Consumer reroute chiuso.

## Commit Rilevanti Prima Di Questo Aggiornamento

```text
9debe8f Document 1.16.0 Windows distribution build
a814c7c Release 1.16.0 Weather condition semantics
efaf29c Clarify visible UI readiness meaning
7e42f12 Document NSOM QML boundary audit
d1da051 Evaluate catalogue raw score policy
06603d2 Clarify backend raw score policy
05397dc Update NSOM handoff state
d84de3a Remove closed NSOM migration artifacts
6a880c0 Audit NSOM migration artifact cleanup
bde221a Close backend NSOM migration scope
c8b392f Enable AOD OpenAQ condition scoring by default
e326d1f Add AOD OpenAQ stale current replay audit
2b50c77 Add AOD OpenAQ real provider readiness audit
540daba Expand AOD OpenAQ real provider probe
277cf45 Add AOD OpenAQ real provider probe
d3a6534 Add AOD OpenAQ field calibration fixtures
30c2e60 Add AOD OpenAQ default-on readiness audit
```

## Ultima Validazione Eseguita

Dopo la correzione degli stati transitori e del wrapping Home `1.17.1`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/services/home_observing_overview.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_home_observing_overview.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m compileall astro_viewer/app/services/home_observing_overview.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_home_observing_overview.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_home_observing_overview.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer/app/ui astro_viewer/app/ui/components/GlassCard.qml astro_viewer/app/ui/pages/HomePage.qml
.\.venv\Scripts\python.exe astro_viewer/main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m pytest -q -n auto
.\packaging\build_windows.ps1
Start-Process -FilePath .\dist\NightScope\NightScope.exe -ArgumentList '--qml-smoke-test' -WindowStyle Hidden -Wait -PassThru
```

Risultati:

- ruff e compileall focused: passed;
- Home/release focused tests: `32 passed`;
- qmllint: exit code `0`, con i warning storici sugli accessi QML non
  qualificati della pagina;
- QML smoke: passed;
- full suite: `638 passed, 7 subtests passed`;
- Windows build PyInstaller `6.21.0`: passed;
- bundled QML smoke: exit code `0`.

Durante lo hardening provider-cache `1.17.1`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/database/sky_quality_repository.py astro_viewer/app/services/light_pollution_service.py astro_viewer/app/services/nasa_aod_provider.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_nasa_aod_provider.py astro_viewer/tests/test_viirs_cache_policy.py
.\.venv\Scripts\python.exe -m compileall astro_viewer/app/database/sky_quality_repository.py astro_viewer/app/services/light_pollution_service.py astro_viewer/app/services/nasa_aod_provider.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_nasa_aod_provider.py astro_viewer/tests/test_viirs_cache_policy.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_nasa_aod_provider.py astro_viewer/tests/test_viirs_cache_policy.py astro_viewer/tests/test_refresh_lifecycle.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- ruff focused: passed;
- compileall focused: passed;
- provider/refresh focused tests: `76 passed`;
- full suite: `636 passed, 7 subtests passed`.

Dopo il completamento della parte alta Home `1.17.0`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/services/sky_compass_service.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_sky_compass_service.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m compileall astro_viewer/app/services/sky_compass_service.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_sky_compass_service.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_sky_compass_service.py astro_viewer/tests/test_sky_compass_nsom_ranking.py astro_viewer/tests/test_sky_compass_live_refresh.py astro_viewer/tests/test_release_scenarios.py astro_viewer/tests/test_home_observing_overview.py
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m pytest -q -n auto
.\packaging\build_windows.ps1
Start-Process -FilePath .\dist\NightScope\NightScope.exe -ArgumentList '--qml-smoke-test' -WindowStyle Hidden -Wait -PassThru
```

Risultati:

- ruff focused: passed;
- compileall: passed;
- focused Home/Sky Compass tests: `60 passed`;
- QML smoke: passed;
- full suite: `630 passed, 7 subtests passed`;
- bundled QML smoke: exit code `0`.

Distribuzione Windows:

- `dist/NightScope` e' stata rigenerata su richiesta esplicita per `1.17.1` con
  PyInstaller `6.21.0`;
- `VERSION` incorporato: `1.17.1`; QML Home `pending`/wrapping verificato nel
  bundle;
- `NightScope.exe` SHA-256:
  `F59A7D75A8C0BE71E3D526902C0CB82282325D0A479B652C0A6D60EC80C137D4`;
- `nightscope.db`, `nightscope.db.backup`, `user_preferences.json`,
  `location_cache.json` e `nasa_aod_cache.json` sono stati salvati prima del
  `COLLECT`, ripristinati, ricontrollati via SHA-256 e ripristinati nuovamente
  dopo lo smoke test;
- database finale: `integrity_check=ok`, `user_version=6`.

## Ambiente `.venv` Verificato

Snapshot controllato prima del prossimo step:

- runtime/UI: `PySide6 6.11.1`, `astropy 8.0.1`, `skyfield 1.54`,
  `numpy 2.5.1`, `requests 2.34.2`, `keyring 25.7.0`, `tzdata 2026.2`;
- AOD/Earthdata: `earthaccess 0.18.0`, `python-cmr 0.13.0`,
  `h5py 3.16.0`, `netCDF4 1.7.4`, `s3fs 2026.6.0`, `aiohttp 3.14.1`;
- test/build: `pytest 9.1.1`, `pytest-xdist 3.8.0`,
  `pytest-cov 7.1.0`, `ruff 0.15.21`, `pyinstaller 6.21.0`,
  `Nuitka 4.1.3`.

## Come Ripartire Nella Nuova Chat

Primo contesto da leggere:

1. `docs/NEXT_CHAT_HANDOFF.md`
2. `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
3. `docs/CALCULATION_LOGIC.md`
4. `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
5. `docs/ARCHITECTURE.md`

Sequenza consigliata:

1. Non rigenerare nuovamente la `dist` senza richiesta esplicita: sorgente e
   distribuzione corrente sono entrambe `1.17.1`.
2. Confrontare lo screenshot Home aggiornato, inclusi stato iniziale di ricerca
   posizione, wrapping e coerenza dei dati caricati.
3. Solo dopo il confronto passare alla seconda parte Home, `Piano della notte`,
   un pezzo alla volta, verificando prima il contratto dati di ogni sezione.
4. Capitoli da lasciare separati:
   - monitoraggio AOD/OpenAQ reale;
   - eventuale design UI/explanations.
5. Non fare tuning e non toccare UI senza uno step esplicito.

## Regole Di Scope Da Mantenere

- Non cambiare scoring se lo step e' audit/review/documentazione.
- Non introdurre QML/UI senza prompt esplicito.
- Non introdurre logging automatico, rete o scritture runtime nei report.
- Usare `-n auto` nei test pytest quando possibile.
- Aggiornare sempre documentazione base e changelog a ogni commit/versione.
- Se sono stati modificati file, chiudere il lavoro con un commit mirato dopo
  le validazioni appropriate.
- Se si rigenerano report, evitare il real-provider probe salvo richiesta
  esplicita dell'utente.
