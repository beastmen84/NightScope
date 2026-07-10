# NightScope NSOM - Punto Della Situazione Per Nuova Chat

Data: 2026-07-10  
Workspace: `C:\Users\beast\PycharmProjects\NightScope`  
Versione corrente: `1.15.2`  
Ultimi commit completati:

- `6a880c0 Audit NSOM migration artifact cleanup`
- cleanup `1.15.2` dei report/tool/test storici NSOM

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
- UI/QML non toccata;
- report/tooling storici di migrazione rimossi in `1.15.2`;
- nessuna rete, logging automatico o scrittura runtime introdotta.

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
- nessun nuovo fetch provider e nessuna nuova chiamata rete;
- AOD e OpenAQ entrano nello score solo quando i dati sono gia' presenti e
  passano i gate provider-quality;
- AOD e OpenAQ non sono additivi: AOD e' primary quando eligible, OpenAQ PM e'
  fallback/context;
- confidence/provider confidence restano metadata e non scalano lo score;
- `stale=0.5` e' stato accettato come policy conservativa nel replay 1.14.18.

Attenzione importante:

- Non lanciare `astro_viewer/tools/nsom_aod_openaq_real_provider_probe.py`
  per sbaglio. Quello e' il tool che usa NASA/OpenAQ reali.
- Per report/audit offline usare solo i tool readiness/replay/closeout che
  rileggono report gia' presenti.

## Residui Non Bloccanti

Questi non bloccano il backend NSOM chiuso:

1. `AOD/OpenAQ real observing feedback`
   - Policy: monitorare risultati reali prima di qualunque tuning ulteriore.
   - Non fare tuning pesi adesso.

2. `Catalogue / Universe raw score semantics`
   - I raw score/catalogue score restano input upstream.
   - Da trattare come futura policy Universe/read-model, non come hotfix di
     ranking.

3. `Visible UI explanations`
   - La UI non va toccata automaticamente.
   - L'audit dice esplicitamente `Ready for visible UI redesign: False`.
   - Eventuali spiegazioni visibili vanno progettate in uno step separato.

4. `Equipment recommendations`
   - Chiuso come setup-local.
   - `EquipmentService` resta owner concreto di oculari/Barlow/binocoli.
   - Non introdurre ora un replacement path NSOM Equipment.

5. `ObservationConditions prepared-object cache`
   - Non e' codice morto.
   - Resta boundary attivo raw/display per compatibilita' e presentation.
   - Consumer reroute chiuso.

## Ultimi Commit Rilevanti

```text
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

Dopo `1.15.2`:

```powershell
.\.venv\Scripts\python.exe -m compileall astro_viewer
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_nsom_model.py astro_viewer/tests/test_nsom_diagnostic_adapters.py astro_viewer/tests/test_nsom_runtime_snapshot.py astro_viewer/tests/test_nsom_formula_parity_sensitivity.py astro_viewer/tests/test_planner_nsom_experimental.py astro_viewer/tests/test_home_nsom_recommended_deep_sky_ranking.py astro_viewer/tests/test_best_object_nsom_ranking.py astro_viewer/tests/test_sky_compass_nsom_ranking.py astro_viewer/tests/test_detail_nsom_runtime.py astro_viewer/tests/test_advanced_observing_nsom_runtime.py astro_viewer/tests/test_advanced_observing_nsom_presentation_runtime.py astro_viewer/tests/test_observer_capability_adapter.py astro_viewer/tests/test_observation_conditions_service.py astro_viewer/tests/test_observation_conditions_read_model.py astro_viewer/tests/test_equipment_setup_read_model.py astro_viewer/tests/test_equipment_setup_score_read_model.py
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- compileall: passed;
- focused runtime NSOM tests: `235 passed`;
- full suite: `616 passed, 7 subtests passed`.

## Come Ripartire Nella Nuova Chat

Primo contesto da leggere:

1. `docs/NEXT_CHAT_HANDOFF.md`
2. `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
3. `docs/CALCULATION_LOGIC.md`
4. `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
5. `docs/ARCHITECTURE.md`

Sequenza consigliata:

1. Fare una review rapida di `1.15.0`.
2. Decidere se aprire un nuovo capitolo su:
   - monitoraggio AOD/OpenAQ reale;
   - policy Catalogue/Universe raw score;
   - eventuale design UI/explanations.
3. Non fare tuning e non toccare UI senza uno step esplicito.

## Regole Di Scope Da Mantenere

- Non cambiare scoring se lo step e' audit/review/documentazione.
- Non introdurre QML/UI senza prompt esplicito.
- Non introdurre logging automatico, rete o scritture runtime nei report.
- Usare `-n auto` nei test pytest quando possibile.
- Aggiornare sempre documentazione base e changelog a ogni commit/versione.
- Se si rigenerano report, evitare il real-provider probe salvo richiesta
  esplicita dell'utente.
