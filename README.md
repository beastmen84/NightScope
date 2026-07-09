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

Versione corrente: `1.14.7`.

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
allora default-off puo' proiettarlo con pesi espliciti per classe target quando serve
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
Lo step `1.5.6` risolve il blocker mirato `open-cluster-recurring-demotion`:
per gli ammassi aperti soltanto, `Q_target` applica una floor di usabilita' alla
dimensione field-of-view quando campo e comfort sono utilizzabili ma non
ottimali. La correzione resta nel layer `ObserverCapability` e modifica
`PracticalTargetValue` solo tramite `Q_target`; `ObservableTargetValue`, sky,
sessione, confidence, Planner legacy e UI/QML restano invariati. I report
developer-only e il decision log sono rigenerati e non restano blocker
default-on aperti.
Lo step `1.5.7` aggiunge l'audit developer-only di readiness per il futuro
switch default-on del Planner NSOM. Il report
`docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md` verifica che non restino
blocker di calibrazione o policy, che le decisioni accettate/deferred siano
documentate, che i deferred siano non bloccanti, che in quello step il flag
Planner NSOM fosse ancora disabilitato e che comparison, trace e decision
log restino tooling non collegato a runtime, QML, logging automatico, rete o
scritture file runtime. Lo step `1.5.7` non abilita NSOM Planner.
Lo step `1.5.8` abilita Planner NSOM di default impostando
`NSOM_PLANNER_SCORING_ENABLED = True`. La modifica runtime e' limitata al
default del flag: il rollback legacy mantenuto in quello step viene rimosso in
`1.13.8`, senza QML, logging
automatico, rete, scritture file runtime o wiring dei report developer-only.
Lo step `1.5.9` chiude la migrazione Planner NSOM: il Planner NSOM e' il path
default supportato. Il rollback esplicito interno mantenuto allora viene
rimosso in `1.13.8`; il confronto legacy resta developer-only tramite report e
`PlannerScoringService`.
Non cambia scoring rispetto a `1.5.8`, non aggiunge QML/UI e non collega report
al runtime. Restano documentati come deferred non bloccanti
`medium-equipment-q-target-review-band` e
`moon-planet-favouring-category-factor`; sono punti di osservazione/calibrazione
futura, non blocker della migrazione Planner.
Lo step `1.6.5` chiude la migrazione Home `recommendedDeepSky`: la lista Home
di cielo profondo usa ora di default l'ordinamento NSOM `ObservableTargetValue`,
costruito da `IntrinsicTargetQuality`, `ObservationEnvironment` ed
`EffectiveObservability`. Il rollback interno mantenuto allora viene rimosso in
`1.13.8`. Best Object, Sky
Compass, QML/UI, payload e report runtime restano invariati. La Home continua a
mostrare lo score legacy/base per compatibilita', quindi lo score visibile puo'
non essere monotono rispetto all'ordine NSOM. Se manca la sky quality runtime,
`recommendedDeepSky` usa ancora il path legacy moon-adjusted.
Lo step `1.7.0` avvia l'analisi Best Object aggiungendo un layer di confronto
developer-only tra la formula legacy `item.score * weather_factor *
difficulty_factor` e i concetti NSOM: `IntrinsicTargetQuality`,
`ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
`PracticalTargetValue`, `SessionViability` e `RecommendationConfidence`. Il
confronto evidenzia dove il legacy mescola valore target, meteo/sessione e
difficolta', marcando i componenti non disponibili invece di ricostruirli. Non
cambia Best Object, `recommendedDeepSky`, Planner, Sky Compass, QML/UI, logging,
rete o scritture file runtime.
Lo step `1.7.1` aggiunge il report developer-only
`docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md`, generato da scenari deterministici
che confrontano ordine Best Object legacy, ordine NSOM `ObservableTargetValue`,
ordine NSOM `PracticalTargetValue`, metadati `SessionViability` e metadati
`RecommendationConfidence`. Il report conclude che Best Object e' oggi piu'
vicino a un ibrido Home-specific; una futura migrazione dovrebbe valutare
`ObservationOpportunity` con policy di presentazione Home, non un puro valore
Observable o Practical. Nessun report e' collegato al runtime o a QML.
Lo step `1.7.2` introduce il primo path runtime Best Object NSOM, interno e
spento di default tramite `NSOM_BEST_OBJECT_ENABLED = False`. Quando viene
forzato con `AppController(use_nsom_best_object=True)`, Best Object valuta
`ObservationOpportunity` con policy Home-specific: `PracticalTargetValue`
deriva da `ObservableTargetValue` e `Q_target`, `SessionViability` gestisce la
non-actionability delle sessioni bloccate e `RecommendationConfidence` resta
metadato senza effetto sullo score. Il rollback legacy esplicito introdotto in
quello step viene rimosso in `1.13.8`. Il payload QML resta invariato,
lo score mostrato resta legacy/base per compatibilita' e, se manca la sky
quality runtime, il controller usa ancora il path legacy.
Lo step `1.7.3` risolve le policy Best Object per target non azionabili:
sessioni bloccate e target invisibili restano non azionabili, mentre i target
visibili con finestra incerta sono marcati come timing incerto. L'ordine
pratico preservato resta diagnostico interno e non diventa ordine di
raccomandazione runtime.
Lo step `1.7.4` aggiunge l'audit developer-only di readiness per il default-on
di Best Object NSOM, verificando rollback, policy non-actionable, assenza di
QML/report runtime wiring e score-neutrality della confidence.
Lo step `1.7.5` abilita Best Object NSOM di default con
`NSOM_BEST_OBJECT_ENABLED = True`. La selezione Best Object usa ora
`ObservationOpportunity` con policy Home-specific quando meteo e sky quality
runtime sono disponibili; il rollback legacy esplicito mantenuto allora viene
rimosso in `1.13.8`. Non vengono aggiunti campi QML,
logging, rete, scritture runtime o collegamenti ai report.
Lo step `1.7.6` chiude la migrazione Best Object NSOM come stato documentato:
Best Object e' default-on su NSOM. Il rollback interno mantenuto allora viene
rimosso in `1.13.8`; resta il fallback quando manca la sky quality. Il payload QML resta invariato e lo score
mostrato resta legacy/base per compatibilita', quindi puo' non essere monotono
rispetto alla selezione NSOM.
Lo step `1.8.0` avvia la migrazione dei punteggi osservativi avanzati con un
layer developer-only `AdvancedObservingNsomComparisonService`. Il servizio
confronta le formule legacy `AdvancedObservingService` per planetario e cielo
profondo con proiezioni NSOM di riferimento, separando meteo/sessione,
trasparenza/seeing, Luna, light pollution e confidence. Non cambia i punteggi
avanzati, Home, Best Object, Planner, Sky Compass, QML/UI, logging, rete o
scritture runtime. Da questo step il changelog `astro_viewer/CHANGELOG.md`
viene riportato in pari come traccia umana sintetica del lavoro NSOM.
Lo step `1.8.1` aggiunge il report developer-only
`docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md`: scenari deterministici
per sessione buona/scarsa/bloccata, Luna brillante, light pollution alta,
seeing scarso, trasparenza scarsa e bassa confidence mostrano le formule
legacy e le proiezioni NSOM di riferimento. Il report resta esplicito,
non collegato al runtime e non modifica punteggi avanzati o UI.
Lo step `1.8.2` e' una review-only del report 1.8.1: non modifica codice o
runtime, ma conferma che prima di un path default-off servono decisioni esplicite
su session/actionability, protezione planetaria da sky background, target-class
deep-sky e score display.
Lo step `1.8.3` aggiunge il report developer-only
`docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md`. Il report registra le
decisioni di policy per un futuro path Advanced Observing NSOM default-off:
Advanced Observing resta una superficie diagnostica/presentazione, la
`SessionViability` resta separata, i pianeti/Luna sono protetti da penalita' di
Moon/light-pollution background, la diagnostica deep-sky conserva componenti per
classe target, `ObserverCapability` e' differito e `RecommendationConfidence`
resta metadato senza effetto score. Non cambia `AdvancedObservingService`, Home,
Best Object, Planner, Sky Compass, QML/UI, logging, rete o scritture runtime.
Lo step `1.8.4` introduce il primo path runtime Advanced Observing NSOM,
interno e spento di default con `NSOM_ADVANCED_OBSERVING_ENABLED = False`. Il
controller mantiene il legacy come default e offre solo override interno
`use_nsom_advanced_observing=True`. Il path sperimentale conserva il payload
`advancedScores` esistente, calcola i valori planetario/deep-sky da
`ObservableTargetValue` di categoria, tiene `SessionViability` e
`RecommendationConfidence` fuori dallo score e non espone campi NSOM a QML.
Lo step `1.8.5` aggiunge il report developer-only
`docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md`, che confronta il path
forced-on NSOM con il legacy senza cambiare il flag. Il report conferma che il
path sperimentale e' safe-to-keep, ma non pronto per default-on: `advancedScores`
e' ancora condiviso con QML, Planner e NotificationService, quindi serve una
policy prima di farlo diventare default.
Lo step `1.8.6` aggiunge il report developer-only
`docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md`. La policy stabilisce che
`advancedScores` deve restare legacy-compatible finche' Planner e
NotificationService non ricevono input consumer-specifici o una policy di split:
il Planner lo usa come fattore di trasparenza e le notifiche lo usano come
soglia diretta, quindi i valori NSOM di categoria non possono diventare default
senza un passaggio dedicato. Il flag Advanced Observing NSOM resta spento.
Lo step `1.8.7` implementa lo split dei consumer: il payload condiviso
`advancedScores` resta legacy-compatible per QML, Planner e NotificationService,
mentre un forced-on Advanced Observing NSOM calcola solo uno snapshot interno
parallelo `_advanced_observing_nsom_scores`. Planner e notifiche ricevono metodi
consumer-specifici che ritornano lo score legacy, cosi' i valori NSOM di
categoria non vengono usati come trasparenza Planner o soglie di notifica. Il
flag resta `NSOM_ADVANCED_OBSERVING_ENABLED = False`; il blocker default-on
rimasto e' la policy di presentazione/QML.
Lo step `1.8.8` aggiunge il report developer-only
`docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md`. L'audit conferma che
lo split consumer e' risolto, ma Advanced Observing NSOM non e' pronto per
default-on: i valori forced-on sono ancora solo `_advanced_observing_nsom_scores`
interni, non hanno effetto sulla presentazione QML e non hanno una semantica
score/label `/100` definita. Il flag resta spento finche' non viene deciso se
NSOM Advanced Observing resta diagnostica nascosta o diventa una superficie
QML-safe separata.
Lo step `1.8.9` definisce quel contratto in
`docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md`: una futura property
separata `advancedObservingNsom`, distinta da `advancedScores`, con schema
versionato, valori categoria da `ObservableTargetValue`, sessione e confidence
come metadati a effetto score zero, e nessun uso come input Planner,
NotificationService, Best Object o Sky Compass. Il contratto e' solo
developer-only: la proiezione runtime e l'eventuale esposizione QML restano step
separati.
Lo step `1.8.10` implementa la proiezione runtime interna/default-off di quel
contratto in `astro_viewer/app/services/advanced_observing_nsom_presentation.py`.
Quando `use_nsom_advanced_observing=True`, `AppController` salva un payload
privato `_advanced_observing_nsom_presentation` coerente con il contratto; non
aggiunge property QML, non sostituisce `advancedScores` e non alimenta Planner,
NotificationService, Best Object o Sky Compass. Il blocker di proiezione runtime
e' risolto, mentre l'eventuale esposizione `advancedObservingNsom` resta un
passaggio separato di review UI/QML. Il flag
`NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`.
Lo step `1.8.11` fa hardening di quella proiezione interna: il metadata
sessione del payload privato ora rispecchia anche lo stato `monitor`, usato
quando il meteo blocca la sessione corrente ma una finestra osservativa utile e'
prevista piu' tardi. La sessione resta metadata fuori dai valori categoria,
`advancedScores` resta legacy-compatible e non vengono aggiunte property QML o
nuovi input per Planner, NotificationService, Best Object o Sky Compass.
Lo step `1.8.12` aggiunge il report developer-only
`docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md`. L'audit conferma che
la proiezione interna `advancedObservingNsom` e' safe-to-keep, ma non ancora
pronta per una property QML pubblica o una UI visibile: servono prima policy su
notify-signal/lifecycle, copy localizzata, placement UI e semantica score/label
per non confondere diagnostiche NSOM con gli score legacy `/100`. Il flag resta
spento e `advancedScores` resta l'unico contratto QML pubblico corrente.
Lo step `1.8.13` definisce quella policy nel report developer-only
`docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md`: una futura property
read-only `advancedObservingNsom` dovra' usare lo snapshot privato
`_advanced_observing_nsom_presentation`, il notify/lifecycle esistente
`weatherChanged`, copy tramite chiavi localizzabili e label che descrivono i
valori come diagnostica NSOM, non come score legacy `/100`. La UI visibile e la
property pubblica non vengono ancora implementate; `advancedScores` resta
l'unico contratto QML pubblico e `NSOM_ADVANCED_OBSERVING_ENABLED` resta
`False`.
Lo step `1.8.14` implementa quella property come superficie QML read-only:
`AppController.advancedObservingNsom` legge solo lo snapshot privato
`_advanced_observing_nsom_presentation`, usa il lifecycle `weatherChanged`,
non introduce nuovi signal e restituisce `{}` quando il path NSOM e' spento o
lo snapshot non e' disponibile. Nessuna UI QML visibile la consuma ancora:
`advancedScores` resta il payload delle card Home esistenti, il flag
`NSOM_ADVANCED_OBSERVING_ENABLED` resta `False` e Planner, NotificationService,
Best Object e Sky Compass non cambiano.
Lo step `1.8.15` rafforza la stessa property: ogni lettura restituisce una
copia difensiva JSON-compatibile dello snapshot privato, inclusa la lettura via
Qt property system. Questo impedisce mutazioni accidentali del payload interno e
mantiene invariati UI visibile, scoring, flag Advanced Observing NSOM e consumer
runtime.
Lo step `1.8.16` aggiunge
`docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md`: l'audit conclude
che Advanced Observing NSOM e' pronto per uno switch default-on limitato alla
proiezione backend/interna. Lo switch non deve sostituire `advancedScores`, non
deve rendere UI QML visibile e non deve cambiare Planner, NotificationService,
Home Best Object o Sky Compass. La UI visibile, la copy/localizzazione e
l'eventuale sostituzione degli score legacy restano item separati e non
bloccanti per il solo default-on backend.
Lo step `1.8.17` abilita Advanced Observing NSOM di default impostando
`NSOM_ADVANCED_OBSERVING_ENABLED = True`. Il default ora calcola lo snapshot
interno parallelo `_advanced_observing_nsom_scores` e la presentazione read-only
`advancedObservingNsom`; il payload visibile `advancedScores` resta legacy per
compatibilita' con le card Home, Planner e NotificationService. Il rollback
interno mantenuto allora viene rimosso in `1.13.8`.
Non vengono aggiunti UI visibile, logging, rete, scritture runtime o wiring dei
report developer-only.
Lo step `1.8.18` chiude la migrazione Advanced Observing NSOM come stato
backend default-on documentato. Advanced Observing NSOM e' ora calcolato di
default come proiezione interna/parallela; `advancedScores` resta il contratto
legacy-compatible visibile e consumer-safe, mentre `advancedObservingNsom` resta
una property read-only separata non usata dalla UI visibile. Il rollback
runtime mantenuto allora viene rimosso in `1.13.8`. UI visibile,
copy/localizzazione e sostituzione futura degli score legacy restano lavori
separati, non blocker della migrazione backend.
Lo step `1.9.0` avvia la migrazione Sky Compass con un comparison layer
developer-only: `SkyCompassNsomComparisonService` confronta la formula legacy
direzionale con `IntrinsicTargetQuality`, `ObservationEnvironment`,
`EffectiveObservability`, `ObservableTargetValue`, `PracticalTargetValue`,
`SessionViability` e `RecommendationConfidence`. Sky Compass runtime, payload
QML, ranking direzionale, Home, Best Object e Planner restano invariati; il
layer non scrive file, non logga, non usa rete e non viene collegato alla UI.
Lo step `1.9.1` aggiunge il report developer-only
`docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md`, generato dal tool esplicito
`astro_viewer/tools/sky_compass_nsom_comparison_report.py`. Il report usa 8
scenari deterministici e mostra che Sky Compass e' una policy direzionale e di
presentazione, non un ranking puro per target-value: NSOM puo' fornire
riferimenti `ObservableTargetValue`/`PracticalTargetValue`, ma boost da piano,
Best Object e concentrazione direzionale restano policy separate. Nessun
runtime, payload QML o ranking viene modificato.
Lo step `1.9.2` aggiunge il readiness/policy report developer-only
`docs/SKY_COMPASS_NSOM_POLICY_READINESS.md`, generato da
`astro_viewer/tools/sky_compass_nsom_policy_readiness.py`. Il report risolve la
policy per un futuro path Sky Compass NSOM default-off: base candidato
`ObservableTargetValue.value`, boost da piano/Best Object e concentrazione
direzionale come policy di presentazione, `PracticalTargetValue` solo
reference-only, sessione e confidence come metadata, fallback legacy e payload
`skyCompass` invariato. Nessun flag runtime viene aggiunto in questo step.
Lo step `1.9.3` introduce quel path runtime sperimentale, interno e spento di
default con `NSOM_SKY_COMPASS_ENABLED = False`. Quando il controller viene
forzato con `AppController(use_nsom_sky_compass=True)`, Sky Compass usa
`ObservableTargetValue.value` come base candidato e conserva i boost da piano,
Best Object e presenza target come policy di presentazione. Il payload
`skyCompass` resta compatibile e non espone campi NSOM; se manca sky quality o
il path sperimentale fallisce, il controller torna al `SkyCompassService`
legacy. Il comportamento runtime predefinito resta invariato.
Lo step `1.9.4` aggiunge il readiness audit developer-only
`docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md`, generato da
`astro_viewer/tools/sky_compass_nsom_default_on_readiness_audit.py`. Il verdetto
e' `ready_for_sky_compass_nsom_default_on_switch`: nessun blocker, rollback
esplicito `AppController(use_nsom_sky_compass=False)`, fallback legacy quando
manca sky quality o il servizio sperimentale fallisce, payload `skyCompass`
invariato e nessuna esposizione QML. Il flag resta `False`; lo switch default-on
deve essere un commit separato che imposta solo
`NSOM_SKY_COMPASS_ENABLED = True`.
Lo step `1.9.5` abilita Sky Compass NSOM di default impostando
`NSOM_SKY_COMPASS_ENABLED = True`. Il default del controller usa ora
`SkyCompassNsomDirectionService` quando sky quality e' disponibile. Il rollback
esplicito mantenuto allora viene rimosso in `1.13.8`; resta il fallback legacy
quando manca sky quality o il path NSOM fallisce. Il payload
`skyCompass` resta invariato e non espone campi NSOM; nessuna modifica QML/UI,
logging, rete, scrittura runtime o report runtime wiring viene introdotta.
Lo step `1.9.6` chiude la migrazione Sky Compass NSOM come stato documentato:
Sky Compass e' default-on su NSOM `ObservableTargetValue`; il path legacy resta
solo fallback dati/errore dopo `1.13.8` e il payload QML resta compatibile. Il campo
`score` nei target Sky Compass continua a essere il valore legacy/base mostrato
per compatibilita' e non una spiegazione NSOM della direzione.
Lo step `1.9.7` aggiunge l'audit complessivo developer-only dello stato NSOM
backend: Planner, Home `recommendedDeepSky`, Best Object, Advanced Observing
backend e Sky Compass risultano chiusi come superfici default-on con rollback
espliciti. Il report `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` identifica
come residui non bloccanti Detail/selected object, Sky Map, Equipment
recommendations, cache di oggetti condizionati, Notifications e score raw di
catalogo. Il prossimo step consigliato e' un confronto NSOM Detail/Object,
senza UI o scoring change.
Lo step `1.10.0` avvia quel confronto Detail/Object con
`DetailObjectNsomComparisonService` e il report developer-only
`docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md`. Il layer confronta il payload
Detail legacy effettivo con `ObservableTargetValue`, `PracticalTargetValue`,
`SessionViability` e `RecommendationConfidence` paralleli. Non cambia
`selectedObject`, UI/QML, Home, Best Object, Planner, Sky Compass, logging, rete
o scritture runtime.
Lo step `1.10.1` aggiunge il readiness audit developer-only
`docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md`. Il verdetto e'
`not_ready_for_default_off_detail_nsom_path`: prima di qualunque path runtime
Detail NSOM servono una decisione esplicita sulla differenza tra Detail
osservativo e Detail catalogo, una semantica del punteggio visualizzato e un
contratto payload/display. Confidence resta metadata-only e non ci sono cambi a
runtime o QML.
Lo step `1.10.2` aggiunge il contratto policy/display Detail/Object in
`docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md` e aggiorna il readiness audit a
`ready_for_default_off_detail_nsom_path`. La policy stabilisce che
`selectedObject.score` resta compatibility data legacy/base, che il futuro
payload NSOM deve essere separato (`detailObjectNsom`) e che la prima runtime
path deve restare default-off, senza aggiungere campi NSOM a `selectedObject` e
senza UI/QML visibile.
Lo step `1.10.3` implementa quella path runtime interna default-off con
`astro_viewer/app/services/detail_nsom_runtime.py` e
`NSOM_DETAIL_OBJECT_ENABLED = False`. Il rollback esplicito mantenuto in questa
fase viene rimosso in `1.13.8`. Se forzata on, la path costruisce
solo un payload interno separato tramite `_selected_object_nsom_payload()`;
`selectedObject`, payload QML, Home, Best Object, Planner, Sky Compass,
logging, rete e scritture runtime restano invariati. Il payload contiene valori
NSOM Detail/Object separati, ma `SessionViability` e
`RecommendationConfidence` restano metadata-only e non modificano score.
Lo step `1.10.4` aggiunge
`docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md`: l'audit conclude che
la path Detail/Object NSOM e' pronta per uno switch default-on separato, ma
mantiene `NSOM_DETAIL_OBJECT_ENABLED = False` in questo commit. Il prossimo
passo, dopo review, puo' essere una commit limitata allo switch del flag; la UI
visibile e le spiegazioni NSOM in pagina Detail restano fuori scope.
Lo step `1.10.5` esegue quello switch: `NSOM_DETAIL_OBJECT_ENABLED = True`.
La default path Detail/Object ora costruisce il payload interno NSOM separato
quando richiesto dal backend, ma `selectedObject`, QML/UI e lo score visibile
restano compatibili con il comportamento legacy. Il rollback runtime mantenuto
allora viene rimosso in `1.13.8`.
Lo step `1.10.6` chiude la migrazione backend Detail/Object NSOM in
`docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md`. Detail/Object e' ora una
superficie backend default-on; il rollback esplicito mantenuto allora viene
rimosso in `1.13.8` e la UI visibile resta
immutata e ogni spiegazione NSOM in pagina Detail rimane un futuro step
separato.
Lo step `1.11.0` aggiunge
`docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md`: l'audit riclassifica Sky Map come
`dead_legacy`, perche' Home QML consuma Sky Compass e non `controller.skyMap`,
mentre il controller calcola ancora `_sky_map`. Di conseguenza Sky Map non e'
piu' un target di migrazione NSOM; il prossimo step consigliato e' rimuovere il
path Sky Map morto dopo review. L'audit distingue anche rollback interni
temporanei, campi payload/UI di compatibilita' e superfici legacy/hybrid ancora
attive come Equipment, Notifications e cache ObservationConditions.
Lo step `1.11.1` esegue quel cleanup: rimuove `SkyMapService`,
`AppController.skyMap`, lo storage `_sky_map` e i ricalcoli Sky Map dal
controller. Sky Compass resta la superficie direzionale supportata; non viene
aggiunto nessun campo QML e nessun ranking NSOM cambia. Gli audit backend ora
registrano Sky Map come `removed_dead_legacy`; il prossimo backend NSOM reale
consigliato e' Equipment/ObserverCapability.
Lo step `1.12.0` aggiunge il confronto developer-only
`docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md`: la formula corrente di
`EquipmentService` viene confrontata con `ObserverCapability`, `Q_target` e
`PracticalTargetValue` NSOM. La raccomandazione Equipment runtime non cambia e
non viene esposto nessun campo QML; il prossimo passo e' review 1.12.0 e poi
policy/readiness prima di decidere un eventuale path NSOM default-off.
Lo step `1.12.1` chiude quella decisione in
`docs/EQUIPMENT_NSOM_POLICY_READINESS.md`: `EquipmentService` resta il setup
helper runtime per oculari, Barlow, binocoli, fallback e `setupOptions`; non si
aggiunge un path NSOM default-off Equipment. Il prossimo passo backend e'
estrarre un adapter/read-model condiviso `ObserverCapability/Q_target` senza
cambiare le raccomandazioni runtime.
Lo step `1.12.2` estrae quell'adapter in
`astro_viewer/app/services/observer_capability_adapter.py`: il confronto
Equipment ora riusa la stessa proiezione `ObserverCapability/Q_target` invece
di una formula privata del report. `EquipmentService.suggest_for_profile(...)`
resta invariato e non viene aggiunto nessun flag o campo QML.
Lo step `1.12.2b` indurisce la projection estratta: il profilo di pesi
target-specific viene esposto come metadata immutabile e resta serializzabile
in JSON strict. Non cambia nessuno score runtime e non viene aggiunto wiring
QML/report automatico.
Lo step `1.12.3` aggiunge `docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md`: l'audit
conferma che Notifications non ha piu' consumer QML/Home e lo riclassifica come
`dead_legacy_pending_removal`, quindi non e' una superficie da migrare a NSOM.
Il prossimo cleanup puo' rimuovere `NotificationService`,
`AppController.notifications` e il DTO collegato senza cambiare UI visibile.
Lo step `1.12.4` esegue quel cleanup: il backend Notifications, la property
Qt, lo storage runtime e il DTO sono rimossi. Gli audit ora classificano
Notifications come `removed_dead_legacy`; il prossimo backend step puo'
concentrarsi su ObservationConditions/read-model o sul contratto presenter
Equipment, senza mantenere un path notifiche non usato.
Lo step `1.12.5` aggiunge
`docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md`: l'audit conferma che
`ObservationConditionsService` non e' codice morto ma un path runtime ibrido.
L'audit raccomandava di separare in un read-model esplicito lo score raw del
target, lo score/display condizionato e gli input NSOM `ObservableTargetValue`,
senza cambiare ranking o QML.
Lo step `1.12.6` introduce quel boundary interno:
`ObservationConditionedTargetReadModel` conserva target raw, target display
condizionato, breakdown condizioni, score raw e score display. Le cache sono
private nel controller e non espongono campi QML; ranking e payload restano
immutati. Gli audit ora indicano
`read_model_boundary_introduced_consumer_reroute_pending`: il prossimo lavoro e'
una review mirata sul possibile reroute dei consumer NSOM verso l'input raw,
non un cambio UI.
Lo step `1.12.7` aggiunge
`docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md`: l'audit definisce la
policy di reroute per Home recommendedDeepSky, Best Object e Sky Compass. La
direzione NSOM corretta e' calcolare dal target raw del read-model e mantenere
il target display condizionato per payload/QML compatibili. Il runtime non e'
ancora reroutato; il primo step consigliato dopo review e' Home
recommendedDeepSky.
Lo step `1.12.8` applica quel reroute solo a Home `recommendedDeepSky`: il
ranking NSOM legge `ObservationConditionedTargetReadModel.nsom_target_input`,
mentre il payload QML continua a usare
`ObservationConditionedTargetReadModel.qml_display_target`. Il rollback
runtime mantenuto allora viene rimosso in `1.13.8`; il fallback con sky
quality mancante resta legacy moon-adjusted. Best Object e Sky Compass non
sono ancora reroutati.
Lo step `1.12.9` applica lo stesso boundary a Best Object: il servizio NSOM
riceve candidati raw dal read-model e il controller rimappa l'oggetto scelto al
display target compatibile. Il rollback runtime mantenuto allora viene rimosso
in `1.13.8`; il fallback senza sky quality resta invariato. Sky Compass resta l'unico consumer ObservationConditions
ancora da valutare per un eventuale reroute raw-target.
Lo step `1.12.10` aggiunge
`docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md`: la policy conferma che Sky
Compass non deve ricevere solo target raw. Il contributo `ObservableTargetValue`
deve usare target physics raw da `nsom_target_input`, mentre direzione,
visibilita', horizon/current position e payload devono restare sul target
display/live. Il runtime Sky Compass non cambia in questo step; il prossimo
lavoro e' un adapter split se la policy viene accettata.
Lo step `1.12.11` implementa quello split adapter nel runtime Sky Compass:
il servizio NSOM riceve una mappa di oggetti observable compositi, costruiti con
target physics raw e geometria display/live corrente. Il payload QML continua a
usare i target display/live, e i fallback senza sky quality o su errore servizio
restano legacy. Home, Best Object e Sky Compass risultano ora reroutati sui
boundary raw/display ObservationConditions.
Lo step `1.12.12` chiude la serie ObservationConditions consumer reroute:
gli audit developer-only registrano Home `recommendedDeepSky`, Best Object e
Sky Compass come completati sul boundary raw/display, senza ulteriori cambi di
ranking o payload. Il prossimo lavoro backend consigliato e' il presenter
contract Equipment, non altro lavoro sulla cache ObservationConditions.
Lo step `1.13.0` aggiunge
`docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md`, audit developer-only del
contratto presenter Equipment. L'audit definisce cosa resta ownership di
presentazione/setup (`setupOptions`, fallback, `selectionScore`, campi payload)
e cosa resta reference-only NSOM (`ObserverCapability`/`Q_target`,
`RecommendationConfidence` metadata-only). `EquipmentService.suggest_for_profile(...)`
resta invariato, non viene aggiunto un path Equipment NSOM runtime e non viene
esposto alcun campo QML. Il prossimo step backend consigliato e' un DTO/read-model
presenter Equipment runtime-neutral che preservi payload e comportamento
correnti.
Lo step `1.13.1` introduce quel boundary in
`astro_viewer/app/services/equipment_setup_read_model.py`: il runtime continua a
usare `EquipmentService.suggest_for_profile(...)`, ma `AppController` proietta il
payload attraverso un read-model immutabile prima di aggiornare i campi
`CelestialObject` gia' esistenti. Il payload QML resta invariato, non vengono
aggiunti campi NSOM alla UI e il prossimo lavoro consigliato e' una review dei
componenti dello score/setup Equipment prima di qualunque replacement.
Lo step `1.13.2` aggiunge
`docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md`, audit developer-only della
formula reale `EquipmentService._configuration_score`. L'audit classifica
`angular_scale`, `magnification`, `exit_pupil`, `light_gathering`,
`seeing_compatibility` e `handling` per ownership NSOM e conferma che lo score
Equipment miscela target traits, setup osservatore, sky quality, seeing e
praticita' di presentazione. Non e' `ObservableTargetValue`,
`PracticalTargetValue`, `Q_target` o `RecommendationConfidence`; il prossimo
step consigliato e' estrarre un read-model dei componenti dello score con parity
test stretti, senza cambiare il ranking runtime.
Lo step `1.13.3` introduce quel boundary in
`astro_viewer/app/services/equipment_setup_score_read_model.py`.
`EquipmentService._configuration_score(...)` costruisce ora un
`EquipmentSetupScoreReadModel` con i componenti reali dello score e restituisce
lo stesso totale clampato 0-100. Il confronto Equipment usa il read-model per il
breakdown legacy, quindi la diagnostica non duplica piu' la formula. Nessun
ranking, payload QML, score di selection o raccomandazione runtime cambia; il
prossimo step e' una review del boundary e poi un audit policy per decidere se
serve davvero un path Equipment NSOM default-off.
Lo step `1.13.4` aggiunge
`docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md` e chiude la decisione:
non viene introdotto un path Equipment NSOM default-off. `EquipmentService`
resta un servizio setup-local che sceglie oculare, posizione zoom, Barlow,
binocolo e fallback payload; `ObserverCapability`, `Q_target` e il read-model
componenti restano boundary/metadata NSOM. Nessun comportamento runtime cambia;
il prossimo step consigliato e' il closeout Equipment `1.13.5`.
Lo step `1.13.5` aggiunge `docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md` e chiude
la serie Equipment NSOM per lo scope backend corrente. Equipment resta un
servizio setup-local, non un target-ranking surface: il runtime continua a usare
`EquipmentService.suggest_for_profile(...)`, mentre adapter osservatore,
presenter boundary, ownership dello score e component boundary restano
espliciti per NSOM. Non viene aggiunto nessun path Equipment default-off e non
cambiano raccomandazioni, payload QML, logging, rete o scritture runtime.
Lo step `1.13.6` aggiunge `docs/NSOM_OVERALL_BACKEND_READINESS_AUDIT.md`,
audit complessivo developer-only dopo il closeout Equipment. L'audit conferma
le superfici backend NSOM gia' chiuse, classifica i residui non bloccanti
come rollback interni, payload compatibility, cache ObservationConditions e
score raw catalogo/Universe, e raccomanda come prossimo step un audit policy
per il cleanup dei rollback prima di qualunque lavoro UI/explanation visibile.
Nessun comportamento runtime o QML cambia.
Lo step `1.13.7` aggiunge `docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md` e decide
la policy per i rollback legacy interni rimasti: poiche' l'app non e'
distribuita e le superfici backend NSOM sono chiuse, i rollback interni devono
essere rimossi in un prossimo step focalizzato. Questo commit non rimuove ancora
flag o branch runtime; aggiorna solo audit, report e documentazione.
Lo step `1.13.8` implementa quella policy: i parametri di rollback runtime
interni `AppController(use_nsom_...=False)` e
`NightPlannerService(use_nsom_planner_scoring=False)` sono rimossi. Planner,
Home `recommendedDeepSky`, Best Object, Advanced Observing backend, Sky Compass
e Detail/Object internal payload usano ora i rispettivi path NSOM default-on
senza selettore legacy interno. Restano solo fallback tecnici per input mancanti
o failure servizio dove gia' previsti, ad esempio sky quality mancante; non sono
rollback configurabili. Nessuna UI/QML, logging, rete o scrittura runtime viene
aggiunta.
Lo step `1.13.9` aggiunge
`docs/NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY_AUDIT.md`, audit developer-only del
confine tra score raw catalogo/prepared object, `CelestialObject.score` e
`IntrinsicTargetQuality`. Lo score raw resta un seme Universe provvisorio e un
campo di compatibilita' payload, non uno score NSOM finale da calibrare
direttamente; la provenance esplicita del catalogo e la semantica visibile degli
score restano lavori futuri non bloccanti. Nessun runtime, scoring, QML/UI,
logging, rete o scrittura runtime cambia.
Lo step `1.14.0` aggiunge
`docs/NSOM_UNIVERSE_TARGET_PROFILE_POLICY.md` e decide di non introdurre ora un
`UniverseTargetProfile` runtime: sarebbe un wrapper pass-through su
`IntrinsicTargetQuality` e sui source fields gia' esistenti. Il contratto futuro
del profilo Universe e' documentato, ma l'implementazione resta rinviata finche'
non servono provenance esplicita, nuovi cataloghi, calibrazione intrinseca o
spiegazioni visibili. Nessun comportamento runtime o QML cambia.
Lo step `1.14.1` aggiunge
`docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md`, audit developer-only delle
fonti dati NSOM. La distinzione operativa e': location ed effemeridi locali
abilitano calcoli astronomici sempre disponibili, il profilo equip e' locale e
opzionale con fallback a occhio nudo, mentre meteo, VIIRS, NASA AOD e OpenAQ
sono provider opzionali. Il report identifica la geometria lunare come prossimo
blocco backend locale: altezza Luna, separazione Luna-target e overlap con la
finestra osservativa richiedono solo location/tempo e non provider esterni.
AOD/OpenAQ restano lavori successivi perche' richiedono freshness, qualita' e
controllo double-counting.
Lo step `1.14.2` implementa quella geometria lunare come diagnostica runtime
locale e score-neutral: `SkyfieldAstronomyEngine.moon_geometry(...)` calcola
altezza Luna, separazione Luna-target e overlap con la finestra target usando
solo location, tempo locale ed effemeridi gia' disponibili. I campi entrano
nella snapshot diagnostica NSOM e nei breakdown interni come
`moon_geometry_future_factor`, ma l'effetto score corrente resta `0.0`.
Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object,
Equipment e QML/UI non cambiano comportamento; non vengono introdotti logging,
rete o scritture runtime.
Lo step `1.14.3` aggiunge il primo uso sperimentale della geometria lunare nel
Planner NSOM, ancora default-off: quando `experimental_moon_geometry_scoring` e'
attivo, il Planner puo' usare `MoonGeometryConditionInput` per modulare
`ObservationEnvironment.lunar_sky_background`. Il path default resta identico
alla 1.14.2, perche' `AppController` costruisce la mappa di geometria Planner
solo se il servizio Planner dichiara esplicitamente il flag attivo. Nessun QML,
Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment,
logging, rete o scrittura runtime viene aggiunto.
Lo step `1.14.4` aggiunge
`docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md`, report developer-only per
verificare la direzione matematica della geometria lunare prima di qualunque
default-on. Il report mostra scenari con Luna vicina/lontana, alta/bassa,
fuori finestra e geometria mancante; l'effetto resta confinato al componente
Sky `lunar_sky_background`. La metadata `moon_geometry_confidence` ora indica
la disponibilita' reale di `MoonGeometryConditionInput`, ma resta fuori dalla
formula dello score.
Lo step `1.14.5` aggiunge
`docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md`, audit developer-only
che classifica la geometria lunare Planner come pronta per uno switch default-on
separato. Lo switch non e' ancora abilitato: il default runtime resta
illumination-only e `NightPlannerService` usa la geometria lunare solo con
opt-in esplicito del servizio NSOM.
Lo step `1.14.6` abilita quello switch in modo stretto per il Planner:
`NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED = True`. Il default globale
`ObservationConditionFeatureFlags.experimental_moon_geometry_scoring` resta
`False`, quindi AOD/OpenAQ e i modifier generici restano fuori scope. Il
rollback esplicito e' l'iniezione di un `PlannerNsomScoringService` con
`experimental_moon_geometry_scoring=False`.
Lo step `1.14.7` aggiunge
`docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md`, audit developer-only per i provider
NASA AOD e OpenAQ. Il report conferma che gli input sono disponibili come
diagnostica Sky/Confidence con freshness e precedenza AOD-primary/PM-fallback,
ma blocca qualunque scoring finche' non sono definite policy formali per AOD
QA/uncertainty, rappresentativita' locale OpenAQ e double-counting con VIIRS,
meteo/transparency e geometria lunare. `experimental_aerosol_scoring` resta
`False` e gli aerosol modifier restano `0.0`.

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
