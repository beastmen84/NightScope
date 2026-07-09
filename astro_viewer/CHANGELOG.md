# Changelog

## NightScope 1.12.12 - 2026-07-09

- Chiusa la serie ObservationConditions consumer reroute dopo la review dello
  split adapter Sky Compass 1.12.11.
- Gli audit ora registrano Home recommendedDeepSky, Best Object e Sky Compass
  come consumer reroutati sui boundary raw/display corretti.
- `docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md`,
  `docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md`,
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` e
  `docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md` sono stati rigenerati dai tool
  developer-only.
- Il prossimo lavoro backend consigliato e' la review del presenter contract
  Equipment, ora che la migrazione raw-target ObservationConditions e' stabile.
- Nessun cambio a ranking, QML/UI, Planner, Home, Best Object, Sky Compass,
  logging, rete o scritture runtime.

## NightScope 1.12.11 - 2026-07-09

- Implementato il runtime split adapter Sky Compass definito in 1.12.10.
- Il ramo NSOM Sky Compass calcola `ObservableTargetValue` usando oggetti
  compositi con target physics raw dal read-model e geometria display/live
  corrente.
- Direzione, visibilita', horizon/current position, score payload e campi QML
  restano sui target display/live; non vengono esposti campi NSOM a QML.
- Aggiornati gli audit ObservationConditions/backend/legacy: Home
  recommendedDeepSky, Best Object e Sky Compass risultano reroutati sui boundary
  raw/display corretti.
- Conservati fallback legacy senza sky quality e fallback su errore servizio;
  nessun cambio a Planner, Home, Best Object, Equipment, logging, rete o
  scritture runtime.

## NightScope 1.12.10 - 2026-07-09

- Aggiunto `docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md`, report
  developer-only per il reroute futuro di Sky Compass sul boundary
  `ObservationConditionedTargetReadModel`.
- Definita la policy Sky Compass: `ObservableTargetValue` deve usare target
  physics raw da `nsom_target_input`, mentre direzione, visibilita',
  horizon/current position e payload restano sul target display/live.
- Documentato che boost da Night Plan e Best Object restano presentation/context
  policy e non target physics NSOM.
- Aggiornati gli audit ObservationConditions/backend/legacy: Home e Best Object
  sono reroutati, Sky Compass ha policy definita e runtime adapter ancora
  pending.
- Nessun cambio runtime a Sky Compass, QML/UI, Planner, Home, Best Object,
  Equipment, logging, rete o scritture runtime.

## NightScope 1.12.9 - 2026-07-09

- Reroutato il ramo runtime Best Object NSOM sul boundary
  `ObservationConditionedTargetReadModel`: lo scoring/selection usa il target
  raw `nsom_target_input`, mentre il risultato esposto resta il
  `qml_display_target` compatibile.
- Conservati rollback e fallback: `AppController(use_nsom_best_object=False)`
  e sky quality mancante continuano a usare il path legacy esistente.
- Aggiunto test di regressione che verifica che il servizio Best Object riceva
  i target raw e che il controller ritorni il display target selezionato.
- Rigenerati gli audit ObservationConditions/backend/legacy: Home e Best Object
  risultano reroutati; Sky Compass resta l'unico consumer ObservationConditions
  ancora da valutare.
- Nessun cambio a QML/UI, Planner, Home `recommendedDeepSky`, Equipment,
  logging, rete o scritture runtime.

## NightScope 1.12.8 - 2026-07-09

- Reroutato il ramo runtime Home `recommendedDeepSky` NSOM: il ranking ora usa
  `ObservationConditionedTargetReadModel.nsom_target_input`, cioe' il target raw
  preservato dal boundary ObservationConditions.
- Il payload QML continua a ricevere
  `ObservationConditionedTargetReadModel.qml_display_target`, quindi chiavi,
  score display/base e compatibilita' UI restano invariati.
- Il fallback con sky quality mancante e il rollback
  `AppController(use_nsom_home_recommended_deep_sky=False)` restano sul path
  legacy moon-adjusted.
- Best Object, Sky Compass, Planner, Equipment, QML, logging, rete e scritture
  runtime non sono stati modificati.
- Rigenerati gli audit `OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT`,
  `NSOM_BACKEND_MIGRATION_STATUS_AUDIT` e
  `NSOM_LEGACY_BACKEND_SURFACE_AUDIT`: Home risulta completato, Best Object e
  Sky Compass restano i consumer ObservationConditions da valutare.

## NightScope 1.12.7 - 2026-07-09

- Aggiunto `docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md`,
  audit developer-only per la policy di reroute dei consumer NSOM
  ObservationConditions.
- Il report confronta `ObservableTargetValue` costruito dal target raw del
  read-model contro il target display condizionato, evidenziando il doppio
  conteggio potenziale su Home, Best Object e Sky Compass.
- Definita la policy: i consumer NSOM dovrebbero calcolare dal raw target del
  read-model e mantenere il display target condizionato per payload QML e
  compatibilita' score.
- Corretto un bug interno di fedelta' del read-model Home: la cache Home
  aggregata ora conserva il breakdown deep-sky gia' calcolato invece di
  ricostruirlo come `display_only_projection`.
- Nessun reroute runtime ancora applicato: ranking, selezione Best Object, Sky
  Compass, QML, logging, rete e scritture runtime restano invariati.

## NightScope 1.12.6 - 2026-07-09

- Introdotto il read-model interno `ObservationConditionedTargetReadModel`
  per separare target raw, target display condizionato, breakdown condizioni,
  score raw, score display e policy di input NSOM.
- Aggiunto `ObservationConditionsService.condition_deep_sky_pollution_context()`
  come entrypoint che conserva i `ConditionedTarget` completi; il vecchio
  `apply_deep_sky_pollution_context()` resta wrapper compatibile e mantiene lo
  stesso output `CelestialObject`.
- `AppController` mantiene cache read-model private per deep-sky/Home, senza
  nuove property Qt/QML e senza modificare payload, ranking, Best Object, Sky
  Compass o Planner.
- Rigenerati gli audit `OBSERVATION_CONDITIONS_READ_MODEL_AUDIT`,
  `NSOM_BACKEND_MIGRATION_STATUS_AUDIT` e
  `NSOM_LEGACY_BACKEND_SURFACE_AUDIT`: lo stato passa a
  `read_model_boundary_introduced_consumer_reroute_pending`.
- Resta aperta una review successiva per decidere se e come Home, Best Object e
  Sky Compass debbano leggere il lato raw del read-model senza cambi silenziosi
  di ranking.

## NightScope 1.12.5 - 2026-07-09

- Aggiunto `docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md`, audit
  developer-only del boundary `ObservationConditionsService`.
- L'audit conferma che `ObservationConditionsService` e' runtime attivo, non
  dead legacy: crea copie `CelestialObject` condizionate per compatibilita'
  Home/Detail/Sky Compass e puo' alimentare path NSOM default-on.
- Identificato il rischio architetturale
  `observation-conditions-conditioned-score-as-nsom-intrinsic`: gli score gia'
  condizionati possono diventare input `IntrinsicTargetQuality`/`ObservableTargetValue`.
- Aggiornati gli audit backend per raccomandare come prossimo step un boundary
  read-model che separi raw target, display score condizionato e input NSOM.
- Nessun cambio runtime: nessuno scoring, QML, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, logging, rete o scrittura runtime modificati.

## NightScope 1.12.4 - 2026-07-09

- Rimosso il path backend Notifications ormai non consumato dalla Home:
  `NotificationService`, `AppController.notifications`, lo storage runtime e il
  DTO `Notification`.
- Aggiornati test e audit Advanced Observing per trattare Notifications come
  dead legacy rimosso, non come consumer da proteggere con input legacy.
- Rigenerati gli audit `NOTIFICATIONS_DEAD_LEGACY_AUDIT`,
  `NSOM_LEGACY_BACKEND_SURFACE_AUDIT` e
  `NSOM_BACKEND_MIGRATION_STATUS_AUDIT`.
- Nessun cambio a Planner, Home recommendedDeepSky, Best Object, Advanced
  Observing visible payload, Sky Compass, QML, logging, rete o scritture
  runtime.

## NightScope 1.12.3 - 2026-07-09

- Aggiunto `docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md`, audit developer-only che
  conferma l'assenza di consumer QML/Home per Notifications.
- Riclassificato Notifications come `dead_legacy_pending_removal`, non come
  superficie NSOM da migrare.
- Aggiornati gli audit backend per indicare la rimozione del path
  `NotificationService`/`AppController.notifications` come prossimo cleanup.
- Nessun cambio runtime in questo commit: nessun scoring, QML, logging, rete o
  scrittura runtime modificati.

## NightScope 1.12.2b - 2026-07-08

- Indurita la projection Equipment condivisa `ObserverCapability/Q_target`: il
  profilo di pesi target-specific ora e' metadata immutabile invece di un
  dizionario mutabile.
- Aggiunto un test di regressione che prova l'immutabilita' del profilo pesi e
  la compatibilita' con JSON strict.
- Nessun cambio a scoring, Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, QML, logging, rete o
  scritture runtime.

## NightScope 1.12.2 - 2026-07-08

- Estratto l'adapter condiviso `ObserverCapability/Q_target` in
  `astro_viewer/app/services/observer_capability_adapter.py`.
- `EquipmentNsomComparisonService` ora usa l'adapter condiviso invece di una
  copia privata della formula di capability derivata dalle configurazioni.
- Aggiunti test diretti per configurazioni telescopio/binocolo, proiezione
  target-specific, JSON strict e parita' fra comparison rows e adapter.
- Aggiornati `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md`,
  `docs/EQUIPMENT_NSOM_POLICY_READINESS.md` e gli audit backend: Equipment ha
  ora lo stato `observer_adapter_extracted`, mentre il runtime setup helper
  resta invariato.
- Nessun cambio a QML/UI, Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, logging, rete o scritture
  runtime.

## NightScope 1.12.1 - 2026-07-08

- Aggiunto `docs/EQUIPMENT_NSOM_POLICY_READINESS.md`, audit developer-only che
  decide la policy Equipment/ObserverCapability dopo il confronto 1.12.0.
- Deciso che `EquipmentService.suggest_for_profile(...)` resta per ora il
  runtime setup helper per oculari, Barlow, binocoli, fallback e payload
  `setupOptions`; non viene aggiunto un path NSOM default-off Equipment.
- Registrato che `Q_target` e `ObserverCapability` sono pronti come prossimo
  adapter/read-model condiviso, ma non sostituiscono da soli lo score di setup
  o la presentazione Equipment.
- Documentati i confini: sky quality e seeing non devono modificare
  `ObserverCapability`; `RecommendationConfidence` resta metadata-only.
- Aggiornati gli audit backend: il prossimo step consigliato e' estrarre un
  adapter `ObserverCapability/Q_target` condiviso, senza cambiare le
  raccomandazioni Equipment runtime.
- Nessun cambio a QML/UI, Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, logging, rete o scritture
  runtime.

## NightScope 1.12.0 - 2026-07-08

- Aggiunto `EquipmentNsomComparisonService`, helper developer-only che confronta
  la formula corrente di `EquipmentService` con `ObserverCapability`,
  `Q_target` e `PracticalTargetValue` NSOM.
- Generato `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md` con scenari deterministici
  per pianeti, ammassi aperti, galassie, seeing, inquinamento luminoso,
  binocoli e telescopi.
- Esplicitato che la formula legacy Equipment miscela target traits, sky
  quality, seeing e praticita' di setup in uno score unico, mentre NSOM tiene
  `ObservableTargetValue` separato da `ObserverCapability`.
- Aggiornati gli audit backend per registrare Equipment come
  `comparison_layer_available`; il prossimo step consigliato e' una review
  1.12.0 seguita da policy/readiness Equipment.
- Nessun cambio a raccomandazioni Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.11.1 - 2026-07-08

- Rimosso il path backend Sky Map morto:
  `SkyMapService`, `AppController.skyMap`, lo storage `_sky_map` e i ricalcoli
  `_sky_map_service.map_targets(...)`.
- Aggiornati i test che stubavano Sky Map solo come dipendenza accessoria del
  controller.
- Aggiornati `docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md` e
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md`: Sky Map e' ora
  `removed_dead_legacy`, non piu' una superficie residua o un target NSOM.
- Il prossimo backend NSOM reale diventa Equipment/ObserverCapability, mentre
  cleanup dei rollback interni e UI explanation restano decisioni separate.
- Nessun cambio a QML/UI, Planner, Home recommendedDeepSky, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, scoring NSOM, logging, rete o
  scritture runtime.

## NightScope 1.11.0 - 2026-07-08

- Aggiunto l'audit developer-only delle superfici backend legacy:
  `docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md`.
- Riclassificata Sky Map come `dead_legacy`: la Home QML usa Sky Compass e non
  consuma piu' `controller.skyMap`, mentre il controller calcola ancora
  `_sky_map`.
- Interrotta la raccomandazione di creare una Sky Map NSOM comparison layer:
  il prossimo step consigliato e' rimuovere il path Sky Map morto dopo review.
- Classificati i rollback NSOM esistenti come safety net interne temporanee,
  non come contratti pubblici da preservare indefinitamente.
- Distinti i campi di compatibilita' payload/UI dagli score decisionali NSOM e
  dalle superfici legacy ancora attive.
- Aggiornato `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` per riflettere la
  nuova direzione di cleanup.
- Nessun cambio a runtime, QML/UI, scoring, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, logging, rete o scritture
  runtime.

## NightScope 1.10.6 - 2026-07-08

- Chiusa la migrazione backend Detail/Object NSOM come stato documentato in
  `docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md`.
- Confermato che `NSOM_DETAIL_OBJECT_ENABLED = True` resta il default e che il
  rollback e' `AppController(use_nsom_detail_object=False)`.
- Documentato che `selectedObject` resta il payload QML compatibile e che il
  payload NSOM Detail/Object resta interno/separato.
- Aggiornato l'audit backend complessivo: Detail/Object non e' piu' una
  superficie da chiudere; il prossimo backend step consigliato e' Sky Map NSOM
  comparison.
- Nota successiva: questa raccomandazione e' stata superata dall'audit 1.11.0,
  che classifica Sky Map come legacy morto da rimuovere, non da migrare.
- Nessun cambio a runtime, QML/UI, Home, Best Object, Planner, Sky Compass,
  logging, rete o scritture runtime.

## NightScope 1.10.5 - 2026-07-08

- Abilitata di default la path interna Detail/Object NSOM impostando
  `NSOM_DETAIL_OBJECT_ENABLED = True`.
- Preservato il rollback esplicito
  `AppController(use_nsom_detail_object=False)`.
- Confermato che la default path costruisce solo il payload interno separato
  `detailObjectNsom`; `selectedObject` e la pagina QML restano invariati.
- Aggiornati readiness audit e audit backend: Detail/Object e' ora una
  superficie backend default-on chiusa, con UI/spiegazioni visibili ancora fuori
  scope.
- Nessun cambio a Home, Best Object, Planner, Sky Compass, logging, rete o
  scritture runtime.

## NightScope 1.10.4 - 2026-07-08

- Aggiunto l'audit developer-only di readiness default-on per Detail/Object
  NSOM: `docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/detail_nsom_default_on_readiness_audit.py`.
- Confermato che la path runtime Detail/Object NSOM e' pronta per uno switch
  default-on separato, ma `NSOM_DETAIL_OBJECT_ENABLED` resta `False` in questo
  commit.
- Verificati rollback `AppController(use_nsom_detail_object=False)`, payload
  interno separato, `selectedObject` invariato, assenza di campi NSOM in QML e
  neutralita' di `SessionViability` / `RecommendationConfidence`.
- Aggiornati readiness audit e audit backend complessivo: il prossimo step puo'
  essere una commit di switch default-on se la review accetta la readiness.
- Nessun cambio a runtime default, UI/QML, Home, Best Object, Planner, Sky
  Compass, logging, rete o scritture runtime.

## NightScope 1.10.3 - 2026-07-08

- Aggiunta la path runtime interna Detail/Object NSOM default-off:
  `astro_viewer/app/services/detail_nsom_runtime.py`.
- Aggiunto il flag `NSOM_DETAIL_OBJECT_ENABLED = False` e il rollback esplicito
  `AppController(use_nsom_detail_object=False)`.
- Il controller puo' costruire un payload interno separato tramite
  `_selected_object_nsom_payload()` quando il flag e' forzato on, ma non espone
  nuove property QML e non modifica `selectedObject`.
- Il payload interno contiene `IntrinsicTargetQuality`,
  `ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
  `PracticalTargetValue`, `SessionViability` e `RecommendationConfidence`;
  sessione e confidence restano metadata-only.
- Aggiornati readiness audit e audit backend: Detail/Object ora ha una path
  interna default-off disponibile; UI visibile e default-on restano step
  successivi.
- Nessun cambio a QML/UI, Home, Best Object, Planner, Sky Compass, logging,
  rete o scritture runtime.

## NightScope 1.10.2 - 2026-07-08

- Aggiunto il contratto developer-only Detail/Object NSOM:
  `docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/detail_nsom_policy_contract.py`.
- Risolti i blocker policy del readiness audit: source split osservativo/catalogo,
  semantica dello score visualizzato e payload/display contract.
- Aggiornato `docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md` a
  `ready_for_default_off_detail_nsom_path`; il prossimo step puo' essere un
  path runtime Detail/Object NSOM default-off con rollback esplicito.
- Documentato che `selectedObject.score` resta compatibility data legacy/base e
  che il futuro payload NSOM deve restare separato (`detailObjectNsom`) senza
  aggiungere campi a `selectedObject` nel primo path runtime.
- Nessun cambio a `selectedObject`, QML/UI, Home, Best Object, Planner, Sky
  Compass, logging, rete o scritture runtime.

## NightScope 1.10.1 - 2026-07-08

- Aggiunto il readiness audit developer-only per Detail/Object NSOM:
  `docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/detail_nsom_readiness_audit.py`.
- Il verdetto e' `not_ready_for_default_off_detail_nsom_path`: un futuro path
  runtime deve attendere policy esplicite per source split osservativo/catalogo,
  semantica dello score visualizzato e contratto payload/display.
- Confermato che `RecommendationConfidence` resta metadata-only con score
  effect zero.
- Verificata assenza di wiring in controller/QML, logging automatico, rete,
  scritture runtime e cambi a `selectedObject`, Home, Best Object, Planner o
  Sky Compass.

## NightScope 1.10.0 - 2026-07-08

- Avviata la migrazione Detail/Object con un confronto NSOM developer-only:
  `astro_viewer/app/services/detail_nsom_comparison.py`.
- Aggiunto il report esplicito
  `docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md`, generato dal tool
  `astro_viewer/tools/detail_nsom_comparison_report.py`.
- Il confronto distingue il Detail osservativo, che oggi mostra una copia
  legacy moon-adjusted, dal Detail catalogo, che mantiene lo score raw.
- Esposti in parallelo `ObservableTargetValue`, `PracticalTargetValue`,
  `SessionViability` e `RecommendationConfidence` senza usarli nel payload
  runtime.
- Aggiunti test per JSON stretto, source policy osservativo/catalogo,
  sessione metadata-only, equipment su solo `PracticalTargetValue`, confidence
  score-neutral e assenza di wiring runtime/QML.
- Nessun cambio a `selectedObject`, QML/UI, Home, Best Object, Planner, Sky
  Compass, logging, rete o scritture runtime.

## NightScope 1.9.7 - 2026-07-08

- Aggiunto l'audit complessivo developer-only dello stato NSOM backend:
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/nsom_backend_migration_status_audit.py`.
- Confermato che Planner, Home `recommendedDeepSky`, Best Object, Advanced
  Observing backend e Sky Compass sono superfici NSOM default-on chiuse con
  rollback interni espliciti.
- Identificati i residui non bloccanti: Detail/selected object, Sky Map,
  Equipment recommendations, cache di oggetti condizionati, Notifications e
  score raw di catalogo.
- Raccomandato come prossimo step `1.10.0 Detail/Object NSOM comparison layer`.
- Nessun cambio runtime, QML/UI, scoring, logging, rete, scritture runtime o
  report runtime wiring.

## NightScope 1.9.6 - 2026-07-07

- Chiusa la migrazione Sky Compass NSOM come stato documentato.
- Sky Compass usa ora di default `SkyCompassNsomDirectionService` con base
  `ObservableTargetValue.value` e policy di presentazione per piano
  osservativo, Best Object e presenza target.
- Il rollback legacy resta esplicito con
  `AppController(use_nsom_sky_compass=False)`.
- Documentato che il payload `skyCompass` resta legacy-compatible e che il
  campo `score` resta dato legacy/base di compatibilita', non rationale NSOM.
- Documentato il fallback legacy quando manca sky quality o il path NSOM
  fallisce.
- Nessun cambio a QML/UI visibile, logging, rete, scritture runtime o report
  runtime wiring.

## NightScope 1.9.5 - 2026-07-07

- Abilitato Sky Compass NSOM di default impostando
  `NSOM_SKY_COMPASS_ENABLED = True`.
- Il default del controller ora usa `SkyCompassNsomDirectionService` quando e'
  disponibile sky quality; la base candidato e' `ObservableTargetValue.value`,
  con boost da piano osservativo, Best Object e presenza target come policy di
  presentazione.
- Il rollback resta esplicito con
  `AppController(use_nsom_sky_compass=False)` e conserva il path legacy
  `SkyCompassService`.
- Conservato il fallback legacy quando manca sky quality o il path sperimentale
  fallisce.
- Aggiornato il readiness/status report
  `docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md` per registrare lo stato
  default-on attivo e blocker vuoti.
- Nessun campo NSOM viene aggiunto al payload `skyCompass`; nessuna modifica
  QML/UI, logging, rete, scrittura runtime o report runtime wiring.

## NightScope 1.9.4 - 2026-07-07

- Aggiunto il default-on readiness audit developer-only per Sky Compass NSOM:
  `docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/sky_compass_nsom_default_on_readiness_audit.py`.
- Il verdetto e' `ready_for_sky_compass_nsom_default_on_switch`, con blocker
  vuoti e cambio richiesto separato: `NSOM_SKY_COMPASS_ENABLED = True`.
- Verificati default-off legacy, opt-in NSOM, rollback
  `AppController(use_nsom_sky_compass=False)`, fallback legacy se manca sky
  quality o il servizio sperimentale fallisce, payload `skyCompass` invariato e
  assenza di campi NSOM in QML.
- Documentato che il campo `score` resta legacy/base compatibility data e non
  e' una rationale NSOM della direzione; il rischio e' non bloccante per lo
  switch backend.
- Confermato che `PracticalTargetValue`, `ObserverCapability`,
  `SessionViability`, meteo/equipaggiamento e `RecommendationConfidence` non
  entrano nello score runtime Sky Compass NSOM.
- Nessun cambio runtime: il flag Sky Compass NSOM resta `False`; nessun cambio a
  Home, Best Object, Planner, QML/UI, logging, rete o scritture runtime.

## NightScope 1.9.3 - 2026-07-07

- Introdotto il path runtime Sky Compass NSOM sperimentale e interno con
  `NSOM_SKY_COMPASS_ENABLED = False`.
- Aggiunto `SkyCompassNsomDirectionService`: usa `ObservableTargetValue.value`
  come base candidato e mantiene boost da piano osservativo, Best Object e
  presenza target come policy di presentazione.
- Aggiunto l'opt-in interno `AppController(use_nsom_sky_compass=True)` e il
  rollback/fallback legacy esplicito tramite `use_nsom_sky_compass=False`.
- Preservato il payload `skyCompass`: nessun campo NSOM esposto a QML e score
  visualizzato ancora compatibile con il valore legacy/base del target.
- Aggiunto fallback al `SkyCompassService` legacy quando manca sky quality o il
  servizio sperimentale non riesce a costruire il payload.
- Aggiunti test per flag default-off, path opt-in NSOM, rollback legacy,
  high-light-pollution, boost da piano/Best Object, JSON stretto, payload
  invariato, assenza di wiring QML/report e assenza di mutazione dei target.
- Nessun cambio runtime predefinito: Sky Compass legacy resta attivo di default;
  nessun cambio a Home, Best Object, Planner, QML/UI, logging, rete o scritture
  runtime.

## NightScope 1.9.2 - 2026-07-07

- Aggiunto il readiness/policy report developer-only
  `docs/SKY_COMPASS_NSOM_POLICY_READINESS.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/sky_compass_nsom_policy_readiness.py`.
- Documentate le policy per un futuro path Sky Compass NSOM default-off:
  `ObservableTargetValue.value` come base candidato, boost da piano/Best Object
  e concentrazione direzionale come presentation policy, `PracticalTargetValue`
  reference-only, sessione/caution e confidence come metadata.
- Chiarito che un futuro path sperimentale deve preservare payload
  `skyCompass`, fallback legacy e assenza di campi NSOM in QML.
- Aggiunti test per determinismo, JSON stretto, copertura decisioni, evidenza
  dal comparison report, no runtime/QML wiring e allineamento del report
  checked-in.
- Nessun cambio a Sky Compass runtime, Home, Best Object, Planner, QML,
  logging, rete o scritture runtime.

## NightScope 1.9.1 - 2026-07-07

- Aggiunto il report developer-only
  `docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/sky_compass_nsom_comparison_report.py` per rigenerare il
  report fuori dal runtime.
- Il report copre 8 scenari deterministici: cielo buio, Luna brillante, alto
  inquinamento luminoso, meteo scarso, sessione bloccata, piccolo telescopio,
  grande telescopio e boost da piano/Best Object.
- Documentato che Sky Compass non e' un ranking puro per target-value: la
  formula legacy combina score candidato preparato, membership nel piano, Best
  Object e concentrazione direzionale.
- Aggiunti test per output deterministico, JSON stretto, componenti legacy
  non disponibili, separazione sessione/equipaggiamento, confidence neutrality,
  assenza di wiring runtime/QML e allineamento del report checked-in.
- Nessun cambio a Sky Compass runtime, Home, Best Object, Planner, QML,
  logging, rete o scritture runtime.

## NightScope 1.9.0 - 2026-07-07

- Avviata la migrazione Sky Compass con
  `SkyCompassNsomComparisonService`, un helper developer-only e side-effect-free.
- Il comparison layer confronta la formula legacy direzionale
  `sum(item.score + in_plan_bonus + best_object_bonus + target_presence_bonus)`
  con proiezioni NSOM per `IntrinsicTargetQuality`,
  `ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
  `PracticalTargetValue`, `SessionViability` e `RecommendationConfidence`.
- Evidenziato che Sky Compass legacy miscela score candidato gia' preparato,
  membership nel piano, Best Object e concentrazione direzionale in uno score
  di direzione.
- Confermato che sessione/meteo e confidence restano metadata nel confronto e
  che l'equipaggiamento influenza solo il riferimento `PracticalTargetValue`.
- Aggiunti test di regressione per JSON stretto, bright Moon/high light
  pollution, sessione bloccata, equipaggiamento, confidence neutrality, target
  invisibili/senza direzione, assenza di mutazioni e assenza di wiring QML.
- Nessun cambio a Sky Compass runtime, payload QML, Home, Best Object, Planner,
  logging, rete, scritture runtime o report runtime wiring.

## NightScope 1.8.18 - 2026-07-07

- Chiuso lo stato della migrazione Advanced Observing NSOM come backend
  default-on.
- Documentato che `NSOM_ADVANCED_OBSERVING_ENABLED = True` e che il rollback
  resta esplicito con `AppController(use_nsom_advanced_observing=False)`.
- Confermato che `advancedScores` resta legacy-compatible per card Home,
  Planner e NotificationService, mentre `advancedObservingNsom` resta una
  property read-only separata.
- Registrato che il metadata runtime di `advancedObservingNsom` e' allineato
  allo stato default-on (`default_on_internal_projection`).
- Documentato che UI visibile, copy/localizzazione e sostituzione futura degli
  score legacy restano lavori separati e non bloccano la migrazione backend.
- Nessun cambio a scoring, Planner, Home Best Object, Sky Compass, QML visibile,
  logging, rete, scritture runtime o report runtime wiring.

## NightScope 1.8.17 - 2026-07-07

- Abilitato Advanced Observing NSOM di default impostando
  `NSOM_ADVANCED_OBSERVING_ENABLED = True`.
- Il default calcola ora lo snapshot interno parallelo
  `_advanced_observing_nsom_scores` e la presentazione read-only
  `advancedObservingNsom`.
- `advancedScores` resta legacy-compatible e continua a essere il contratto
  visibile delle card Home e l'input per Planner e NotificationService.
- Il rollback resta esplicito con
  `AppController(use_nsom_advanced_observing=False)`.
- Aggiornato il report di readiness per registrare lo switch backend attivo.
- Nessuna UI QML visibile, nessun logging automatico, rete, scrittura runtime o
  wiring dei report developer-only.

## NightScope 1.8.16 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_default_on_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md`,
  audit per lo switch default-on backend/interno di Advanced Observing NSOM.
- Il verdetto e' `ready_for_advanced_observing_nsom_backend_default_on`: nessun
  blocker per abilitare la proiezione NSOM interna in un commit separato.
- Chiarito che lo switch backend non sostituisce `advancedScores`, non rende UI
  QML visibile e non cambia Planner, NotificationService, Home Best Object o
  Sky Compass.
- Registrati come non bloccanti per il backend: design UI visibile,
  copy/localizzazione e sostituzione futura degli score legacy.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessun cambio runtime,
  scoring, logging, rete o scritture runtime in questo audit.

## NightScope 1.8.15 - 2026-07-07

- Rafforzata la property QML read-only `advancedObservingNsom`.
- La property ora restituisce una copia difensiva profonda dello snapshot
  `_advanced_observing_nsom_presentation`, invece di esporre direttamente il
  dizionario privato.
- Aggiunto un test sul Qt property system: la property e' non scrivibile, usa
  `weatherChanged`, restituisce payload JSON-compatibile e non permette di
  mutare lo snapshot interno.
- Nessuna UI QML visibile legge la property; `advancedScores` resta il contratto
  Home visibile.
- Nessun cambio a Planner, NotificationService, Home Best Object, Sky Compass,
  scoring, logging, rete o scritture runtime. Il flag
  `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`.

## NightScope 1.8.14 - 2026-07-07

- Aggiunta in `AppController` la property QML read-only
  `advancedObservingNsom`.
- La property usa il lifecycle esistente `weatherChanged`, non introduce nuovi
  signal e legge solo lo snapshot privato
  `_advanced_observing_nsom_presentation`.
- Quando `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`, o lo snapshot non e'
  disponibile, la property restituisce `{}`.
- Quando il path Advanced Observing NSOM viene forzato internamente, la property
  espone il payload `advanced_observing_nsom_presentation_v1` gia' proiettato,
  senza ricomputare al read.
- Nessuna UI QML visibile legge `advancedObservingNsom`; `advancedScores` resta
  il contratto Home pubblico usato dalle card esistenti.
- Aggiornati i report developer-only di readiness/contract/policy per
  distinguere property QML read-only presente da UI visibile assente.
- Nessun cambio a Planner, NotificationService, Home Best Object, Sky Compass,
  scoring, logging, rete o scritture runtime. Il flag
  `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`.

## NightScope 1.8.13 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_qml_presentation_policy.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md`, policy
  per una futura superficie QML `advancedObservingNsom`.
- Definita la policy di lifecycle: una futura property read-only dovra' usare
  lo snapshot privato `_advanced_observing_nsom_presentation` e il lifecycle
  esistente `weatherChanged`, senza ricomputare al read e senza introdurre un
  nuovo signal.
- Definite le policy di copy/placement/score-label: la UI visibile resta
  bloccata, la copy futura deve passare da chiavi localizzabili e i valori NSOM
  vanno etichettati come diagnostica `ObservableTargetValue`, non come score
  legacy `/100`, input Planner o soglie NotificationService.
- Confermato che `advancedScores` resta l'unico contratto QML pubblico
  corrente; nessuna property QML, logging, rete, scrittura runtime o modifica a
  Planner, NotificationService, Home, Best Object o Sky Compass.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; il prossimo step
  utile e' una review della policy prima di qualsiasi esposizione QML.

## NightScope 1.8.12 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_qml_exposure_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md`, audit di
  readiness per una futura esposizione QML di `advancedObservingNsom`.
- Confermato che la proiezione interna 1.8.10/1.8.11 e' safe-to-keep, ma non
  ancora pronta per una property QML pubblica o UI visibile.
- Bloccanti registrati: lifecycle/notify-signal della property, copy UI,
  localizzazione e semantica score/label per evitare di presentare valori NSOM
  come score legacy `/100` di actionability.
- `advancedScores` resta l'unico contratto QML pubblico corrente; nessun
  cambio a Planner, NotificationService, Best Object o Sky Compass.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.11 - 2026-07-07

- Rafforzata la proiezione interna/default-off Advanced Observing NSOM
  introdotta in 1.8.10.
- Corretta la fedelta' del metadata sessione:
  `_advanced_observing_nsom_presentation` ora preserva lo stato `monitor` del
  controller quando il meteo corrente blocca la sessione ma esiste una finestra
  osservativa utile piu' tardi.
- Aggiunta copertura regression per la proiezione dello stato `monitor`,
  mantenendo `SessionViability`/session state come metadata fuori dai valori di
  categoria.
- `advancedScores` resta legacy-compatible; non sono stati aggiunti property
  QML, input Planner, input NotificationService, input Best Object o input Sky
  Compass.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessun logging, rete
  o scrittura runtime introdotti.

## NightScope 1.8.10 - 2026-07-07

- Aggiunto `astro_viewer/app/services/advanced_observing_nsom_presentation.py`,
  builder interno del payload `advancedObservingNsom` definito dal contratto
  1.8.9.
- `AppController` ora puo' proiettare il payload NSOM Advanced Observing solo
  quando `use_nsom_advanced_observing=True`, salvandolo nello snapshot privato
  `_advanced_observing_nsom_presentation`.
- Il payload condiviso `advancedScores` resta legacy-compatible e continua a
  essere l'unico dato pubblico letto da QML, Planner e NotificationService.
- Aggiornato `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md`: il
  blocker `advanced-observing-runtime-projection-not-implemented` e' risolto;
  resta il blocker separato `advanced-observing-qml-exposure-review-required`.
- Aggiunti test per JSON stretto, proiezione forced-on/off, consumer legacy
  invariati e assenza di property QML.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.9 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_presentation_contract.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md`, contratto
  per una futura superficie QML-safe separata `advancedObservingNsom`.
- Definito che il futuro payload NSOM non sostituisce `advancedScores`, non e'
  input Planner, non e' soglia NotificationService e non alimenta Home Best
  Object o Sky Compass.
- Definito che Advanced Observing NSOM usa diagnostiche di categoria da
  `ObservableTargetValue`; `ObserverCapability`, `PracticalTargetValue`,
  `SessionViability`, `RecommendationConfidence` e `ObservationOpportunity`
  restano fuori dal valore categoria.
- I blocker default-on rimasti sono implementativi: proiezione runtime
  default-off del nuovo contratto e review separata per eventuale esposizione
  QML.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.8 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_presentation_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md`, audit di
  readiness per la presentazione/default-on Advanced Observing NSOM.
- Confermato che lo split 1.8.7 protegge Planner e NotificationService:
  `advancedScores` resta legacy-compatible e lo snapshot NSOM resta interno.
- Registrato il verdetto: Advanced Observing NSOM non e' ancora pronto per
  default-on, perche' i valori NSOM forced-on non hanno un contratto
  QML/presentazione e non modificano la superficie visuale.
- Bloccanti rimasti: visibilita' dello snapshot NSOM, contratto di presentazione
  NSOM e semantica score/label `/100`.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.7 - 2026-07-07

- Implementato lo split dei consumer Advanced Observing NSOM nel controller.
- `advancedScores` resta il payload legacy-compatible condiviso con QML,
  Planner e NotificationService.
- Quando `use_nsom_advanced_observing=True`, il controller calcola i valori
  Advanced Observing NSOM solo come snapshot interno parallelo
  `_advanced_observing_nsom_scores`.
- Planner e NotificationService ricevono input consumer-specifici
  legacy-compatible, quindi i valori NSOM di categoria non vengono usati come
  fattore di trasparenza Planner o soglia diretta di notifica.
- Aggiornato `docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md`: i blocker
  Planner e NotificationService risultano risolti dallo split; resta bloccante
  la policy di presentazione/QML prima di qualunque default-on.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.6 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_downstream_policy.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md`, policy report
  sui consumer downstream di `advancedScores`.
- Registrata la decisione che `advancedScores` deve restare legacy-compatible
  finche' Planner e NotificationService non ricevono input consumer-specifici o
  una policy esplicita di split.
- Evidenziato il rischio Planner: il Planner NSOM usa `advancedScores` come
  fattore di trasparenza atmosferica; usare direttamente i valori Advanced
  Observing NSOM forced-on cambierebbe ranking e ownership.
- Evidenziato il rischio notifiche: in sessione bloccata i valori NSOM di
  categoria restano fisici/alti e potrebbero generare notifiche favorevoli senza
  un gate di `SessionViability`.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessun cambiamento
  runtime a formule, Planner, NotificationService, Home, Best Object, Sky
  Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.5 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_runtime_review.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md`, review del path
  Advanced Observing NSOM forced-on introdotto in 1.8.4.
- Il report confronta punteggi legacy e forced-on NSOM sugli scenari
  deterministici gia' usati per Advanced Observing, verificando JSON stretto,
  payload compatibile, confidence neutra, sessione fuori dallo score, protezione
  planetaria da Moon/light-pollution background e sensibilita' deep-sky.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; il default runtime
  resta legacy.
- Emerso blocker esplicito per default-on: `advancedScores` e' condiviso con
  QML, Planner e NotificationService, quindi una futura attivazione deve
  decidere se questi consumer usano, ignorano o ricevono una copia
  legacy-compatible degli score avanzati.
- Nessun cambiamento runtime a formule, flag, Home, Best Object, Planner, Sky
  Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.4 - 2026-07-07

- Aggiunto `astro_viewer/app/services/advanced_observing_nsom_service.py`, path
  runtime interno e sperimentale per Advanced Observing NSOM.
- Introdotto il flag `NSOM_ADVANCED_OBSERVING_ENABLED = False`; il default
  runtime resta il legacy `AdvancedObservingService`.
- Aggiunto override interno del controller
  `use_nsom_advanced_observing`, senza toggle QML e senza esporre campi NSOM nel
  payload `advancedScores`.
- Il path forced-on calcola punteggi planetario/deep-sky da
  `ObservableTargetValue` di categoria, mantiene `SessionViability` e
  `RecommendationConfidence` come metadata paralleli e non usa
  `ObserverCapability`.
- Aggiunti test per default-off legacy invariato, forced-on NSOM, protezione
  planetaria da Moon/light-pollution background, sessione bloccata fuori dallo
  score, confidence neutra, payload QML compatibile, assenza di report/QML
  wiring e no mutation.
- Nessun cambiamento runtime di default a Home, Best Object, Planner, Sky
  Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.3 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_policy_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md`, audit di policy
  e readiness per un futuro path Advanced Observing NSOM default-off.
- Registrate decisioni esplicite su ruolo Advanced Observing, separazione
  `SessionViability`, seeing planetario, protezione pianeti/Luna da
  Moon/light-pollution background, target-class deep-sky, weather cap legacy,
  ObserverCapability differito e `RecommendationConfidence` metadata-only.
- Il report dichiara che non restano blocker per implementare un path
  default-off, ma mantiene i rischi non bloccanti su score display, UI scalare,
  seeing ownership e badge deep-sky aggregato.
- Nessun cambiamento runtime a `AdvancedObservingService`, Home, Best Object,
  Planner, Sky Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.2 - 2026-07-07

- Review della 1.8.1: il report Advanced Observing e' stato verificato come
  developer-only, coerente con le formule legacy disponibili e utile per
  decidere la policy prima di un path runtime default-off.
- Nessun codice runtime modificato; restano da decidere esplicitamente
  session/actionability, protezione planetaria da sky background, target-class
  deep-sky, score display e ruolo futuro di `ObserverCapability`.

## NightScope 1.8.1 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_comparison_report.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md` con scenari
  deterministici per sessione buona/scarsa/bloccata, Luna brillante, light
  pollution alta, seeing scarso, trasparenza scarsa e bassa confidence.
- Il report confronta formule legacy `AdvancedObservingService` e proiezioni
  NSOM reference-only, chiarendo che la migrazione futura dovrebbe trattare gli
  advanced scores come diagnostica/presentazione di categoria, non come nuovo
  owner indipendente di score.
- Aggiunti test per output deterministico, JSON stretto, ownership, confidence
  metadata-only e assenza di wiring runtime/QML.
- Nessun cambiamento runtime a punteggi avanzati, Home, Best Object, Planner,
  Sky Compass, UI, logging, rete o scritture runtime.

## NightScope 1.8.0 - 2026-07-07

- Aggiunto `AdvancedObservingNsomComparisonService`, layer developer-only che
  confronta i punteggi avanzati legacy planetario/deep-sky con confini NSOM di
  riferimento.
- Esposte le formule legacy reali di `AdvancedObservingService`, inclusi
  componenti meteo, seeing/trasparenza, vento, Luna, light pollution e cap
  meteo, senza inventare breakdown non disponibili.
- La proiezione NSOM separa `SessionViability`, `ObservationEnvironment`,
  `EffectiveObservability`, `ObservableTargetValue` e
  `RecommendationConfidence`; la confidence resta metadato e non modifica gli
  score.
- Nessun cambiamento runtime: punteggi avanzati, Home, Best Object, Planner,
  Sky Compass, QML/UI, logging, rete e scritture runtime restano invariati.
- Riportato il changelog in uso come traccia umana del lavoro NSOM, con
  riepilogo retroattivo delle tappe 1.4-1.7.

## NightScope 1.7.6 - 2026-07-05

- Chiusa la migrazione Best Object NSOM come stato documentato.
- Best Object usa ora di default `ObservationOpportunity` con policy
  Home-specific; il path legacy resta rollback esplicito con
  `AppController(use_nsom_best_object=False)` e fallback quando manca la sky
  quality runtime.
- Documentato che il payload QML resta invariato e che lo score mostrato resta
  legacy/base compatibility score, quindi puo' non essere monotono con la
  selezione NSOM.

## NightScope 1.7.0-1.7.5 - 2026-07-02/2026-07-05

- Aggiunto il confronto developer-only Best Object vs NSOM e il report
  `docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md`.
- Introdotto il path runtime Best Object NSOM prima default-off, poi indurito
  con policy per sessioni bloccate, target invisibili e finestre incerte.
- Aggiunto l'audit developer-only di readiness e abilitato Best Object NSOM di
  default con `NSOM_BEST_OBJECT_ENABLED = True`.
- Conservato rollback legacy esplicito, nessuna esposizione QML e nessun
  collegamento runtime ai report.

## NightScope 1.6.0-1.6.5 - 2026-07-02

- Aggiunto confronto e report NSOM per Home `recommendedDeepSky`.
- Introdotto e poi abilitato di default il ranking Home deep-sky basato su
  `ObservableTargetValue`.
- Chiusura migrazione Home `recommendedDeepSky`: rollback esplicito con
  `AppController(use_nsom_home_recommended_deep_sky=False)`, payload QML
  invariato e fallback legacy quando manca la sky quality runtime.

## NightScope 1.5.0-1.5.9 - 2026-07-01/2026-07-02

- Portata avanti la migrazione Planner NSOM fino al default-on.
- Aggiunti review target-specific di `ObserverCapability`, proiezione
  sperimentale `Q_target`, soglie di review calibrazione, decision log e policy
  per opportunita' non azionabili.
- Risolti i blocker mirati `small-equipment-planet-q-target` e
  `open-cluster-recurring-demotion`.
- Abilitato Planner NSOM di default con `NSOM_PLANNER_SCORING_ENABLED = True` e
  chiusa la migrazione Planner mantenendo rollback esplicito con
  `NightPlannerService(use_nsom_planner_scoring=False)`.

## NightScope 1.4.0-1.4.9 - 2026-06-30/2026-07-01

- Introdotto il core NSOM interno con DTO immutabili per Universe, Sky,
  Observer, Session, Opportunity e Confidence.
- Aggiunto il primo path Planner NSOM sperimentale default-off, poi pulito dai
  riferimenti di ownership legacy.
- Aggiunti fixture di confronto/divergenza, explanation fields, report
  deterministico Planner, trace matematico, hardening dei casi all-zero e test
  di formula parity/sensitivity.
- Tutto il tooling di report resta developer-only, senza QML, logging
  automatico, rete o scritture runtime.

## NightScope 1.3.8e - 2026-06-30

- Indurito l'export diagnostico NSOM: snapshot Planner coerenti, JSON stretto,
  semantica VIIRS distinta tra dati provider reali, dataset derivati e fallback.
- Aggiunto refresh snapshot dopo completamento OpenAQ/AOD senza ricomputare
  Planner, Home, Equipment o Sky Compass.
- Confermati no QML, no file writes automatici, no logging automatico, no
  signal emission e confidence parallela score-neutral.

## NightScope 1.3.5 - 2026-06-29

- Rafforzata la diagnostica di `ObservationConditionsService`: `moon_adjusted_score()` ora registra l'illuminazione lunare quando applica la penalità Luna.
- Aggiunto un flag interno non esposto a QML per riconoscere target già condizionati dal contesto deep-sky light pollution, mantenendo il fallback legacy basato sulla nota esistente.
- Preparato il boundary diagnostico per AOD NASA e particolato OpenAQ tramite input provider-neutral, ancora neutri e senza effetto sui punteggi.

## NightScope 1.3.4 - 2026-06-29

- Esteso `ObservationConditionsService` con input diagnostici provider-neutral per NASA AOD e particolato OpenAQ.
- Aggiunta diagnostica di freschezza per input atmosferici normalizzati mantenendo `aod_modifier` e `pm25_modifier` neutrali.
- Confermato che AOD e OpenAQ non modificano punteggi, Planner, best-object selection, Recommendation Engine, Sky Compass live refresh o UI.

## NightScope 1.3.3 - 2026-06-29

- Stabilizzato il confine tra `ObservationConditionsService`, `PlannerScoringService` e `NightPlannerService`.
- Spostati breakdown e penalità specifici del Planner nel servizio di scoring del Planner, mantenendo `ObservationConditionsService` come layer condiviso per Home/Detail, deep-sky context e diagnostica futura.
- Aggiunta cache dei candidati Home/Sky Compass già condizionati, evitando riapplicazioni al volo del moon adjustment nel percorso Sky Compass.
- `NightPlannerService` ora riusa un `PlannerScoringService` iniettabile e calcola lo score dei target visibili una sola volta durante la costruzione del piano.
- Aggiornata la documentazione architetturale dei confini 1.3 senza cambiare punteggi, Planner output, Recommendation Engine, Sky Compass live refresh, OpenAQ o NASA AOD.

## NightScope 1.3.2 - 2026-06-29

- Esteso il breakdown interno di `ObservationConditionsService` con diagnostica per penalità Luna, penalità inquinamento luminoso, fattori placeholder e flag anti doppio conteggio.
- Aggiunto `condition_target()` come API diagnostica interna che restituisce target condizionato, target originale e breakdown completo senza cambiare i consumer.
- Popolati placeholder neutrali per meteo, seeing, trasparenza, equipaggiamento, NASA AOD e PM2.5, senza usarli nel punteggio.
- Rafforzati i test di equivalenza per Home/Detail, pollution context, fixture Planner, best-object ed equipaggiamento.

## NightScope 1.3.1 - 2026-06-29

- Rafforzato `ObservationConditionsService` con test sui confini di attivazione del contesto inquinamento luminoso: Bortle 7, VIIRS 20, VIIRS 19.99 e sky quality mancante.
- Aggiunta copertura per magnitudine non numerica in pollution context e moon adjustment.
- Aggiunta una guardia interna contro la doppia applicazione del contesto deep-sky pollution su target già condizionati dal servizio.
- Confermati invariati AppController, Planner, best-object selection, equipaggiamento, Sky Compass live refresh, OpenAQ e NASA AOD.

## NightScope 1.3.0 - 2026-06-29

- Introdotto `ObservationConditionsService` come foundation del futuro layer condizioni, senza cambiare formule o punteggi.
- Spostati dietro il nuovo servizio solo moon-adjusted score Home/Detail e deep-sky pollution context già applicato da `AppController`.
- Aggiunti breakdown interni/test-only per score base, penalità Luna, penalità inquinamento luminoso, score finale e componenti applicate.
- Lasciati intenzionalmente invariati Planner, best-object selection, Recommendation Engine, equipaggiamento, Sky Compass live refresh, OpenAQ e NASA AOD.

## NightScope 1.2.12 - 2026-06-29

- Aggiunta una snapshot stabile dei candidati di Sky Compass nel controller: il refresh normale continua a costruire il set completo, mentre il tick live riusa solo quella lista.
- Il live refresh ogni 60 secondi non richiama più `_sky_compass_candidates()` e non riapplica filtri Home, scoring deep-sky corretto per Luna, Planner, meteo, VIIRS, OpenAQ, NASA AOD o equipaggiamento.
- La corsia live aggiorna solo campi posizionali correnti e si ferma se non esiste una snapshot valida.

## NightScope 1.2.11 - 2026-06-29

- Attivata la corsia backend live di Sky Compass: un `QTimer` controller-owned ogni 60 secondi aggiorna solo altitudine, azimut e direzione correnti dei target già preparati.
- `LIVE_TICK` ora sporca e ripulisce solo il dominio `COMPASS_LIVE`, senza toccare meteo, OpenAQ, NASA AOD, VIIRS, Planner, equipaggiamento o Recommendation Engine.
- Aggiunto `skyCompassChanged` come segnale QML dedicato, così il live refresh aggiorna solo la card Sky Compass.
- Aggiunta API astronomica leggera `refresh_current_positions()` per riusare Skyfield senza ricampionare finestre osservative o ricostruire cataloghi.

## NightScope 1.2.10 - 2026-06-29

- Introdotto `RefreshManager` come foundation per il ciclo Refresh & Data Lifecycle: classificazione di refresh reasons, refresh domains e dirty domains.
- Collegato il lifecycle layer ai refresh esistenti di location, meteo, OpenAQ, VIIRS, NASA AOD e profili/equipaggiamento senza cambiare il comportamento applicativo.
- Documentata la corsia futura `LIVE_TICK` per Sky Compass senza introdurre timer o refresh live in questa release.
- Resi neutri i motivi generici `TTL_EXPIRED` e `ASYNC_COMPLETED`, sostituiti nei percorsi operativi da motivi specifici per meteo, OpenAQ, NASA AOD e sky quality.
- Corretto lo stato dirty VIIRS: `SKY_QUALITY` resta pendente finché il refresh asincrono non termina, fallisce o viene scartato.

## NightScope 1.2.9 - 2026-06-29

- Persistito lo stato di test connessione OpenAQ usando un'impronta sicura della API key verificata, senza salvare la key in chiaro nelle preferenze.
- Aggiunta cache persistente compatta per i risultati processati NASA AOD, così le riaperture dell'app riusano dati recenti entro TTL senza riscaricare granuli.

## NightScope 1.2.8 - 2026-06-29

- Aggiunta nella pagina Meteo la sezione display-only `Trasparenza atmosferica`, basata sui risultati NASA MAIAC AOD già recuperati tramite Earthdata.
- La sezione resta nascosta senza test Earthdata riuscito, mostra un fallback compatto senza località e indica `Recupero dati NASA AOD...` durante il download.
- Mostrati AOD 550 nm, label descrittiva della trasparenza, data misura, prodotto NASA, metodo di estrazione, incertezza e QA raw senza alimentare punteggi, Planner, Sky Compass o Recommendation Engine.

## NightScope 1.2.7 - 2026-06-29

- Aggiunto retry controllato ai timeout transitori Open-Meteo, mantenendo invariati cache e logica meteo.

## NightScope 1.2.6 - 2026-06-29

- Attivato il refresh backend NASA AOD quando esistono località attiva e credenziali Earthdata verificate, con logging diagnostico del risultato.
- Il dato AOD restava interno e non veniva ancora mostrato in UI o usato nei punteggi.

## NightScope 1.2.5 - 2026-06-28

- Aggiunto backend NASA AOD display-only: VIIRS MAIAC `VNP19A2.002` come sorgente primaria e MODIS MAIAC `MCD19A2.061` come fallback.
- Il provider recupera solo risultati AOD compatti, cancella i granuli NASA temporanei dopo l'estrazione e mantiene una cache in memoria dei risultati processati.
- Integrata autenticazione Earthdata tramite `earthaccess` con retry/backoff, riusando le credenziali Earthdata verificate già presenti.
- Aggiunte dipendenze `earthaccess` e `netCDF4`; MODIS resta fallback con rischio packaging da monitorare per le librerie native.
- AOD non è ancora esposto in Meteo e non alimenta Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi.

## NightScope 1.2.4 - 2026-06-28

- Aggiunta classificazione di freschezza per `Atmosfera locale`: corrente, recente, vecchia e storica.
- Le misure OpenAQ oltre 7 giorni non mostrano più una limpidezza come condizione attuale; la UI indica l'ultima misura disponibile come dato storico.
- Aggiornata la scala descrittiva della limpidezza con il livello intermedio `Velata`, usando il peggiore valore disponibile tra PM2.5 e PM10.
- Mantenuto OpenAQ come dato informativo display-only: nessun uso in Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi.

## NightScope 1.2.3 - 2026-06-28

- Corretto `Atmosfera locale`: la card Meteo resta nascosta finché OpenAQ non ha API key configurata e test connessione positivo.
- Aggiornato il recupero dati OpenAQ al flusso v3 corretto: ricerca località vicine e lettura delle ultime misure da `/v3/locations/{id}/latest`.
- Limitato il raggio OpenAQ al massimo supportato di 25 km ed evitato l'endpoint globale `/v3/measurements` che produceva HTTP 404.

## NightScope 1.2.2 - 2026-06-28

- Aggiunta la sezione `Atmosfera locale` nella pagina Meteo, basata su OpenAQ v3 e visibile solo con API key configurata.
- Mostrati PM2.5, PM10, limpidezza descrittiva e fonte/stazione più recente disponibile, con cache in memoria per località arrotondata.
- Chiarito che i dati OpenAQ restano display-only: non alimentano Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi osservativi.

## NightScope 1.2.1 - 2026-06-28

- Il `Piano osservativo consigliato` continua a selezionare i target migliori per punteggio, ma ora li visualizza in ordine cronologico della notte osservativa.
- La numerazione del piano segue l'ordine temporale mostrato, rendendo la sezione una timeline operativa.

## NightScope 1.2.0 - 2026-06-28

- Aperto il ciclo NightScope 1.2.
- Chiusa la serie NightScope 1.1 con `1.1.15` come ultimo stato stabile.

## NightScope 1.1.15 - 2026-06-28

- Allineati i badge data di `Prossimi eventi` in Home alla stessa categorizzazione colori usata dal Calendario.

## NightScope 1.1.14 - 2026-06-28

- Spostate le alternative di `Sky Compass` nella testata della card, in alto a destra, riducendo l'altezza del corpo.
- Aggiunto a `GlassCard` uno slot opzionale per contenuti custom nella testata senza cambiare le card esistenti.

## NightScope 1.1.13 - 2026-06-28

- Ridotta l'altezza minima di `Sky Compass` quando non ci sono dati visualizzabili.
- Ripristinata la griglia desktop `Prossimi eventi` a quattro colonne per due righe sui layout ampi.
- Allineato verticalmente il badge data nelle card compatte degli eventi.

## NightScope 1.1.12 - 2026-06-28

- Promosso `Sky Compass` sopra `Piano della notte` come prima card pratica dopo i riepiloghi meteo/qualità.
- Riorganizzato `Sky Compass` full-width in tre colonne: bussola/direzione, motivazioni e target principali con alternative.
- Spostati `Prossimi eventi` in fondo alla Home con layout a griglia compatta.
- Rifinite le motivazioni generate da `Sky Compass` per piano osservativo, mix pianeti/deep-sky e ammassi nella stessa zona.

## NightScope 1.1.11 - 2026-06-28

- Rifiniti i breakpoint della card `Sky Compass` in layout 50/50: alternative di nuovo nella testata in alto a destra e sezioni inferiori su due colonne.
- Ripristinato l'accento teal sui badge delle direzioni alternative.

## NightScope 1.1.10 - 2026-06-28

- Ripristinato il layout 50/50 tra `Sky Compass` e `Prossimi eventi` nella sezione `Dettagli osservativi`.
- Resi i breakpoint interni di `Sky Compass` dipendenti dalla larghezza della card, così il layout resta corretto anche in colonna dimezzata.

## NightScope 1.1.9 - 2026-06-28

- Aggiunta a `GlassCard` la modalità opt-in `contentFillsHeight` per card con contenuto verticale elastico.
- Aggiornata `Ricerca città` in `Località` per far riempire alla lista risultati lo spazio interno disponibile senza magic number.

## NightScope 1.1.8 - 2026-06-28

- Rimossa la vecchia card `Mappa cielo` dalla Home e promosso `Sky Compass` nella sua posizione come guida direzionale principale.
- Riorganizzato `Sky Compass` con bussola a sinistra, direzione principale al centro, alternative nella testata e sezioni testuali a due colonne.
- Evidenziato il settore consigliato nella bussola e sostituite le icone testuali dei target con icone disegnate coerenti con il tipo oggetto.

## NightScope 1.1.7 - 2026-06-28

- Rifinita la presentazione di `Sky Compass` con motivazioni più naturali basate sul mix reale dei target nella direzione selezionata.
- Aggiornato il conteggio a `target osservabili` e ridotta l'importanza visiva delle direzioni alternative.
- Aggiunte icone minime per tipo oggetto nella lista dei target principali.

## NightScope 1.1.6 - 2026-06-28

- Rifinito `Sky Compass` trasformandolo da riepilogo direzionale in assistente osservativo orientato alla domanda "dove guardare per primo".
- Aggiunte motivazioni pratiche della direzione scelta, target principali prioritizzati e alternative più leggibili.
- Rimossa la dicitura `Aggiornato ora` dalla card Sky Compass per ridurre rumore visivo.

## NightScope 1.1.5 - 2026-06-28

- Aggiunto il prototipo `Sky Compass` in Home sotto `Mappa cielo`, per indicare la direzione ampia migliore usando i target già disponibili.
- Introdotto `SkyCompassService`, che raggruppa i target Home in otto direzioni e non chiama meteo, VIIRS, Planner o Recommendation Engine.
- Aggiornata la documentazione del refresh Home chiarendo che Sky Compass v1 non è un planetario, non introduce timer QML e non usa ancora `ObservationSnapshot`.

## NightScope 1.1.4 - 2026-06-28

- Aggiunta configurazione OpenAQ nella pagina `Provider dati`, con API key salvata nel vault di sistema, test connessione e rimozione.
- Il test OpenAQ verifica solo raggiungibilità e accettazione della API key tramite endpoint metadati v3; non recupera dati qualità aria e non modifica Meteo, Planner o Recommendation Engine.
- Aggiornata la documentazione per chiarire che OpenAQ è disponibile solo per configurazione e validazione connessione in questa fase.

## NightScope 1.1.3 - 2026-06-28

- Corretto il layout della card `Ricerca città` in `Località`: il pannello risultati resta ora dentro il bordo della card anche nel layout desktop a due colonne.

## NightScope 1.1.2 - 2026-06-27

- Riorganizzata la pagina `Località` mettendo la ricerca città come flusso principale sotto la posizione attuale.
- Spostate le card Windows e geolocalizzazione IP nella colonna destra, mantenendo invariati provider e azioni.
- Rinominata la card online in `Località IP (ipapi/ipwho)` per rendere esplicito il tipo di provider usato.

## NightScope 1.1.1 - 2026-06-27

- Aggiunta la pagina `Provider dati` sotto `Configurazione`.
- Spostata la configurazione Earthdata NASA fuori da `Località`, mantenendo invariati credenziali, stato, test connessione, autorizzazione app e rimozione.
- Aggiornati README e manuale per indicare la nuova collocazione della configurazione Earthdata.

## NightScope 1.1 - 2026-06-27

- Aggiunta la pagina `Oggetti celesti` come catalogo informativo separato da Home, Planner e Recommendation Engine.
- Esteso il catalogo a oggetti Messier e Sistema Solare, con ricerca, filtri, click-through al dettaglio oggetto e layout dettaglio in modalità catalogo.
- Aggiunte le colonne `Utile (≥15°)` e `Visibile nel mese`, distinguendo osservabilità utile da visibilità astronomica mensile.
- Allineata la visibilità mensile del Sistema Solare tra Catalogo, Home e dettaglio oggetto, evitando raccomandazioni contraddittorie.
- Rifinita la presentazione delle raccomandazioni separando `Visibile con...` da `Osservazione consigliata`.
- Reso più conservativo il comportamento planetario quando il seeing non è disponibile.
- Aggiunto supporto alle posizioni reali degli oculari zoom, inclusi i click del Baader Hyperion Zoom 8-24 mm.
- Migliorata la scelta pratica per ammassi globulari medi senza alterare i pesi globali del Recommendation Engine v2.
- Disambiguate le opzioni setup quando telescopi diversi condividono lo stesso label oculare.
- Aggiunta una matrice qualità ripetibile da 375 casi per controllare pianeti, categorie Messier, profili strumenti, seeing e cielo/VIIRS sintetici.
- Aggiornata la documentazione tecnica su refresh Home, architettura raccomandazioni e logica di calcolo.

## NightScope 1.0 - 2026-06-23

- Stabilizzata la Home osservativa con suggerimenti basati su profilo, meteo, Luna e qualità cielo.
- Completata la separazione tra profili strumenti e cataloghi telescopi, oculari e Barlow.
- Aggiunta pagina dettaglio oggetto con descrizione, finestra osservativa, configurazione consigliata e motivazioni.
- Migliorata la gestione della località con posizione Windows, fallback online, ricerca città offline e coordinate manuali.
- Integrato supporto opzionale Earthdata NASA per dati VIIRS Black Marble, con fallback locale.
- Consolidati i test di regressione, smoke test applicativo, QML smoke test e validazioni astronomiche.
- Aggiornato packaging Windows PyInstaller con manuale utente offline.
- Pulito il repository dagli output storici generati in `reports/`.

## NightScope RC1 - 2026-06-21

- Aggiunto logging applicativo con rotazione in `logs/nightscope.log`.
- Irrobustito il bootstrap SQLite con integrity check, backup, quarantena DB corrotto e ricostruzione.
- Irrobustita la gestione Open-Meteo per timeout, API non raggiungibile, payload vuoti, JSON non valido e rate limiting.
- Irrobustito il caricamento Skyfield con fallback controllato tramite app controller.
- Aggiunti stati loading, vuoto ed errore alle schermate Home e Meteo.
- Aggiunti test astronomici per Addis Ababa, Roma, Milano, Cape Town e Oslo.
- Aggiunti test timezone/DST per Europe/Rome.
- Aggiunti test scenario release per forecast online, meteo offline e posizione Windows non disponibile.
- Aggiunti spec PyInstaller Windows, build script e icona applicazione.
