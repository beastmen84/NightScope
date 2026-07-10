# NightScope NSOM - Punto Della Situazione Per Nuova Chat

Data: 2026-07-10  
Workspace: `C:\Users\beast\PycharmProjects\NightScope`  
Versione corrente: `1.16.1`
Commit rilevanti prima di questo aggiornamento del handoff:

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
- report/tooling storici di migrazione rimossi in `1.15.2`;
- il closeout backend non introduce rete, logging automatico o scritture
  runtime; `1.16.1` cambia separatamente solo quando i provider gia' esistenti
  vengono controllati.

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
   - La UI non va toccata automaticamente.
   - Primo passaggio esplicito avviato in `1.16.0`: solo WeatherPage
     condition-data semantics (`Aerosol atmosferico`, `Particolato locale`,
     freshness e confidence localizzata).
   - L'audit dice esplicitamente `Ready for visible UI redesign: False`, ma
     questo non significa UI rotta o backend NSOM non pronto.
   - Significa che la UI visibile e' ancora una superficie compatibility, non
     una UI NSOM-aware progettata per spiegare "perche'" NSOM ordina o sceglie
     un target.
   - La UI continua a ricevere gli stessi payload compatibili: stesse chiavi
     QML, stessi blocchi Home/Planner/Best Object/Sky Compass, stessi campi
     display dove servono, nessun pannello NSOM e nessuna spiegazione visibile
     tipo "Luna alta + AOD stale + seeing scarso".
   - Alcuni campi mostrati, in particolare `score`, restano legacy/base
     compatibility data: servono a non rompere la UI, ma non sempre spiegano in
     modo monotono l'ordine NSOM.
   - Verifica confine backend/QML: Planner, Home, Best Object e Sky Compass
     arrivano alla UI solo tramite payload esistenti (`nightPlan`,
     `recommendedDeepSky`, `bestObjectOfNight`, `skyCompass`), senza campi NSOM
     visibili.
   - Detail/Object resta interno: nessuna property `detailObjectNsom` e nessun
     campo NSOM aggiunto a `selectedObject`.
   - Advanced Observing ha una property Qt read-only `advancedObservingNsom`
     disponibile sul controller ma non letta dai QML; la UI continua a usare
     `advancedScores`.
   - Non emergono fix UI obbligatori dal confine NSOM/QML; resta da fare solo
     una verifica visuale delle schermate.
   - Prima di toccare la UI NSOM-aware bisogna decidere:
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

Dopo `1.16.1`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/services/light_pollution_service.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_viirs_cache_policy.py astro_viewer/tests/test_refresh_lifecycle.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m compileall astro_viewer
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_viirs_cache_policy.py astro_viewer/tests/test_refresh_lifecycle.py astro_viewer/tests/test_release_scenarios.py astro_viewer/tests/test_phase6_real_data.py
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- ruff focused: passed;
- compileall: passed;
- QML smoke: passed;
- focused VIIRS/refresh/release tests: `103 passed, 7 subtests passed`;
- full suite: `622 passed, 7 subtests passed`.

Distribuzione Windows:

- l'ultima `dist/NightScope` rigenerata resta la `1.16.0`, verificata nel commit
  documentale `9debe8f`;
- la `dist` non e' stata rigenerata automaticamente per `1.16.1`, per non
  sostituire `nightscope.db` e i sidecar runtime usati nel confronto visuale;
- rigenerarla solo su richiesta esplicita, valutando prima la conservazione dei
  dati runtime correnti.

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

1. Fare una review rapida di `1.16.1`.
2. Prossimo capitolo consigliato:
   - continuare la verifica UI un pezzo alla volta dopo WeatherPage, senza
     cambiare scoring o ranking salvo prompt esplicito.
3. Capitoli da lasciare separati:
   - monitoraggio AOD/OpenAQ reale;
   - eventuale design UI/explanations.
4. Non fare tuning e non toccare UI senza uno step esplicito.

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
