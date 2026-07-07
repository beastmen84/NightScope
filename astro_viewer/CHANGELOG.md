# Changelog

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
