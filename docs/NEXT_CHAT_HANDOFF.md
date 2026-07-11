# NightScope NSOM - Punto Della Situazione Per Nuova Chat

Data: 2026-07-11
Workspace: `C:\Users\beast\PycharmProjects\NightScope`  
Versione corrente sorgente: `1.20.1`
Distribuzione Windows corrente: `1.18.8`
Commit rilevanti prima di questo aggiornamento del handoff:

- `f9d912f Refine catalogue visibility presentation`
- `e7ade3f Document completed 1.20.0 Calendar`
- `2172d20 Add observable planetary conjunctions`
- `29fb424 Finalize 1.20.0 Calendar validation`
- `4cd7024 Connect Calendar UI to annual events`
- `679d41e Build complete annual Calendar contract`
- `7d9a506 Polish observing detail session copy`
- `b8844f7 Validate 1.19.0 object detail`
- `a63124d Align observing object detail UI`
- `87893d2 Add observing detail presentation contract`
- `a0364ee Document 1.18.8 validation`
- `6a369ed Polish Home and weather presentation`
- `2b66704 Record 1.18.7 validation commit`
- `9b440e4 Document 1.18.7 validation`
- `a091991 Fix Home chronology and weather selection`
- `ce6f49c Document 1.18.6 validation`
- `39faaa7 Show rolling 24-hour weather forecast`
- `be2ab2e Document 1.18.5 validation`
- `8606f18 Keep moon geometry sampling unchanged`
- `3a511a0 Unify Home Bortle presentation`
- `f43b99a Fix sampled observing windows`
- `7c90b43 Finalize 1.18.4 validation`
- `bd1664b Align Earthaccess botocore dependency`
- `6d25b5f Log Sky Compass NSOM fallback failures`
- `8b2363e Show only observing-night weather hours`
- `b1ced9f Reschedule providers after location changes`
- `2fda8da Refine practical planet difficulty`
- `0ad23be Move initial weather lookup off UI thread`
- `fb39ed0 Fix observing-night boundary precision`
- `be9f5a7 Document 1.18.3 Windows distribution build`
- `3c5aca7 Release 1.18.3 Home list fixes`
- `b57049f Keep Home list wheel scrolling contained`
- `4f5cdec Remove residual Home target cap`
- `167ac2a Release 1.18.2 astronomy performance hardening`
- `02ea0c3 Move cold astronomy refresh off UI thread`
- `e5825f5 Move Sky Compass live refresh off UI thread`
- `f62d6ab Batch Moon geometry calculations`
- `d67699f Reuse moon geometry across NSOM refreshes`
- `8ea8a7a Release 1.18.1 local observing night`
- `b750f9f Harden local night regression coverage`
- `669c150 Align observing logic to the local night`
- `ea0b8b1 Use location-aware observing night`
- `8765348 Document 1.18.0 Windows distribution build`
- `da10990 Connect lower Home QML to night plan overview`
- `d54e847 Add Home night plan overview contract`
- `94dabec Make Home target pool and Sky Compass live`
- `b8edbd0 Align Home plan with target equipment`
- `69ce9dd Harden Open-Meteo transient failure retries`
- `3bb2b40 Record 1.17.1 build commit`
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
- `1.17.2` registra lo status HTTP Open-Meteo e programma un retry forzato dopo
  5 minuti soltanto per errori temporanei; cache, scoring, Session e QML restano
  invariati;
- `1.18.0` avvia la chiusura della parte bassa Home riallineando prima il
  contratto backend: quattro opportunita' Planner selezionate prima dell'ordine
  cronologico e telescopio scelto per target nei profili multi-strumento;
- il Planner non mantiene piu' due tappe nascoste e non usa piu' il primo
  telescopio del profilo per tutti i target; binocolo e occhio nudo conservano
  capability proprie;
- il secondo step `1.18.0` espone `homeVisibleAlternatives` come pool Home
  unificato di pianeti e cielo profondo, senza il precedente limite di dieci
  oggetti deep-sky e con esclusione dei quattro target gia' nel piano;
- Sky Compass usa lo stesso pool completo, filtra la geometria live
  `observable_now` e bilancia valore osservativo, quota corrente e densita'
  direzionale; piano e Best Object restano annotazioni/tie-break e non
  alterano artificialmente la direzione;
- il timer Sky Compass continua anche quando nessun target e' osservabile in
  quel momento, cosi' la bussola puo' attivarsi quando un target sorge senza
  richiedere un refresh manuale;
- il terzo step `1.18.0` aggiunge `homeNightPlanOverview`: stato sessione,
  riepilogo quantitativo del profilo, massimo quattro righe piano compatte e
  lista alternativa completa senza score legacy o motivazioni Equipment lunghe;
- soltanto lo stato `recommended` puo' esporre la sequenza numerata; `monitor`
  mostra la possibile finestra e `discouraged` resta esplicitamente senza piano;
- il quarto step `1.18.0` collega il QML inferiore a quel contratto: card piano
  state-aware, nessuna falsa sequenza negli stati non consigliati e tabella
  unica filtrabile per gli altri oggetti visibili;
- la distribuzione Windows `dist/NightScope` e' stata rigenerata su richiesta
  esplicita per `1.18.0`; bundle `VERSION` `1.18.0`, smoke e QML smoke
  dell'eseguibile passati, runtime utente preservati;
- `1.18.1` sostituisce tutte le fasce notturne fisse con un unico
  `ObservingNightWindow` Skyfield, dal tramonto locale all'alba successiva;
- campionamento astronomico, meteo, seeing, score, Home, Planner e Sky Compass
  consumano lo stesso confine; giorno polare, buio continuo ed effemeridi
  indisponibili hanno stati espliciti;
- Open-Meteo passa a 48 ore e le ore sono filtrate tramite timestamp completi;
  gruppi separati da piu' di 90 minuti non possono produrre una finestra
  discontinua come `05:00-22:00`;
- la cache Skyfield per localita'/notte evita di ricalcolare gli eventi solari
  per ogni target; la suite completa chiude con `658 passed, 7 subtests passed`;
- nessuna modifica QML e nessuna nuova build Windows: la distribuzione resta
  correttamente alla `1.18.0`;
- `1.18.2` riusa la geometria Luna-target tra Planner e diagnostica, la calcola
  in batch su una timeline Skyfield condivisa e mantiene in cache le coordinate
  stellari Messier gia' risolte;
- il tick Sky Compass, il refresh astronomico freddo, il cambio notte e il
  reload deep-sky VIIRS lavorano ora fuori dal thread Qt; request id e chiave
  posizione scartano i risultati superati;
- lo snapshot astronomico include anche visibilita' mensile del catalogo e
  geometria Luna-target, cosi' Equipment e Planner non riaprono calcoli pesanti
  sul thread UI;
- nessuna modifica a scoring, ranking o QML in `1.18.2`; la distribuzione resta
  intenzionalmente alla `1.18.0`;
- il primo step `1.18.3` corregge il limite residuo nel ramo di condizionamento
  deep-sky con Bortle/VIIRS attivo: penalita', visibilita' e ordine restano
  invariati, ma tutti i target ancora utili raggiungono il pool Home prima
  dell'esclusione dei quattro oggetti del piano;
- il secondo step `1.18.3` assegna la rotella alla lista Home degli altri
  oggetti mentre il puntatore e' al suo interno e la lista e' scrollabile:
  mouse e touchpad restano confinati anche a top/bottom, mentre fuori dalla
  lista continua a scorrere la pagina;
- la distribuzione Windows `1.18.3` e' stata rigenerata su richiesta; versione
  e QML nel bundle, smoke eseguibile, QML smoke, integrita' database e
  conservazione dei cinque file runtime sono stati verificati;
- il primo step `1.18.4` conserva il minuto contenente il tramonto Skyfield nei
  clock `HH:MM` consumati da Home e Planner e limita la fine della migliore
  finestra meteo all'alba locale esatta;
- il secondo step `1.18.4` sposta su worker anche il primo recupero Open-Meteo
  dopo lo snapshot astronomico e chiude lo stato di caricamento soltanto dopo
  l'applicazione del risultato ancora valido per localita' e request id;
- il terzo step `1.18.4` rende target-specifica la difficolta' dei pianeti per
  telescopio, binocolo e occhio nudo; Urano e Nettuno non risultano piu'
  automaticamente `Facile` e il Planner riceve la classe pratica corretta;
- il quarto step `1.18.4` rende location-safe i completamenti AOD/OpenAQ:
  presentazioni precedenti azzerate al cambio posizione, risultato obsoleto
  scartato e nuovo recupero programmato automaticamente;
- il quinto step `1.18.4` collega grafico e dettaglio Meteo alla nuova property
  `observingWeatherHourly`, limitata alla notte attiva; `weatherHourly` conserva
  le 48 ore complete soltanto come contratto di compatibilita';
- il sesto step `1.18.4` mantiene il fallback legacy Sky Compass ma registra un
  warning diagnostico quando la selezione NSOM solleva un'eccezione;
- il settimo step `1.18.4` vincola `botocore` al range richiesto da
  `aiobotocore 3.7.0`; `.venv` riallineata a `botocore 1.43.0`, `pip check`
  pulito e test AOD/VIIRS passati;
- la `dist` `1.18.4` e' stata rigenerata manualmente dall'utente per il
  confronto visuale; il bundle `_internal/VERSION` risulta `1.18.4`;
- il primo step `1.18.5` elimina le finestre target a durata zero includendo
  l'alba esatta come solo confine e interpolando il passaggio della soglia tra
  campioni; un target utile soltanto al confine finale viene escluso;
- il secondo step `1.18.5` condivide la classificazione Bortle tra le due
  sezioni Home; Bortle 7 e' `transizione suburbana-urbana` sia nella card
  superiore sia nel messaggio della lista;
- `1.18.6` espone `weatherNext24Hours`, una finestra visuale mobile dall'ora
  corrente con `isObservingNight`; grafico e dettaglio Meteo mostrano 24 ore,
  evidenziano la notte e mantengono la selezione per timestamp;
- il timer Meteo gia' esistente aggiorna la proiezione all'inizio di ogni ora;
  score, seeing, trasparenza, Home e NSOM restano sul payload notturno
  `observingWeatherHourly`;
- la `dist` `1.18.6` e' stata rigenerata manualmente dall'utente per la verifica
  visuale; il bundle `_internal/VERSION` risulta `1.18.6`;
- `1.18.7` ordina le alternative Home per inizio finestra prima del `best_time`,
  usa cyan per la selezione Meteo e teal per la notte, e rimuove la scrollbar
  sovrapposta dal dettaglio orario;
- la `dist` `1.18.7` e' stata rigenerata manualmente dall'utente per il
  confronto visuale; il bundle `_internal/VERSION` risulta `1.18.7`;
- `1.18.8` collega la card inferiore della navigazione a
  `homeObservingOverview.session`, centra le immagini delle righe piano, usa
  uno spareggio naturale per nomi Messier/Caldwell e porta la legenda notte
  nell'header del grafico Meteo;
- la `dist` `1.18.8` e' stata rigenerata manualmente dall'utente per la verifica
  visuale; il bundle `_internal/VERSION` risulta `1.18.8`;
- il primo step `1.19.0` introduce `observingObjectDetail`: geometria live,
  Session e setup target-specific restano separati dal ramo Catalogo e non
  espongono score grezzi;
- il secondo step collega il QML, distingue finestra e momento migliore,
  sostituisce i placeholder deep sky, conserva il ciclo lunare e rende il
  blocco superiore responsive;
- la rifinitura finale qualifica soltanto nel dettaglio i badge di stato come
  `Sessione consigliata`, `Sessione da monitorare` e `Sessione sconsigliata`:
  il contratto e i badge compatti della Home restano invariati;
- corretto nel seed il periodo migliore lunare e aggiunta una migrazione
  idempotente per il solo valore legacy `Tutte le fasi tranne Luna piena piena`;
- `Storico osservazioni` non e' piu' nel dettaglio; repository, tabella e slot
  restano intenzionalmente disponibili per la futura pagina `Log Osservazioni`;
- `1.20.1` rimuove dalla lista Catalogo la colonna mensile ridondante ma
  conserva checkbox, selettore e filtro sul mese scelto;
- il dettaglio Catalogo calcola separatamente la visibilita' del solo oggetto
  nel mese locale corrente, con cache dedicata e senza dipendere da flag o mese
  selezionato nella lista;
- tipi oggetto e modalita' osservative del Catalogo hanno label italiane in
  lista, filtri e dettaglio, mantenendo invariati i valori canonici backend;
- report/tooling storici di migrazione rimossi in `1.15.2`;
- il closeout backend non introduce rete, logging automatico o scritture
  runtime; `1.16.1` cambia separatamente solo quando i provider gia' esistenti
  vengono controllati.

## Nota Di Review Sui Dati Home

Nello screenshot Home caricato con `1.17.0`, lo stato `Consigliata` e'
coerente con le soglie attuali: pioggia massima `61% < 65%`, indice meteo
`45 > 25` e nuvolosita' media `40% < 85%`, quindi non scatta un blocker.

La dicitura `Migliore finestra` continua a indicare il blocco relativo di tre
ore con penalita' minore, non una finestra in cui ogni ora supera il gate di
usabilita'. Da `1.18.1` il blocco deve pero' essere consecutivo e interamente
contenuto tra tramonto e alba della posizione attiva; da `1.18.4` anche la label
finale viene troncata all'alba esatta. Il difetto intermittente
`05:00-22:00`, causato dall'unione di due porzioni di notti diverse in una
previsione mobile di 24 ore, e' coperto da regressione e non e' piu' possibile.

La Home NSOM e' chiusa per parte alta, piano, alternative, Sky Compass e
dettaglio osservativo. La card `Prossimi eventi` usa ora la proiezione
`calendarOverview.homeItems`: conserva la cronologia osservativa ma non porta
in Home le congiunzioni col Sole, che restano disponibili nel Calendario.

## Review Calendario Post 1.19.0

Review eseguita senza modificare runtime o QML del Calendario.

Problemi concreti trovati:

- `SkyfieldAstronomyEngine.upcoming_events()` calcola le fasi lunari per soli
  90 giorni, opposizioni/congiunzioni per 365 giorni ed eclissi lunari per 730
  giorni, poi conserva soltanto i 18 eventi con `usefulness` maggiore;
- i filtri QML `6 mesi`, `12 mesi` e `Tutti` non descrivono quindi un dataset
  completo. Un probe Addis Ababa del 2026-07-11 restituisce 18 eventi: 4 fasi
  lunari, 5 opposizioni, 3 eclissi e 6 sciami, nessuna congiunzione; due eclissi
  del 2028 occupano il cap pur essendo fuori dalla vista annuale;
- `EventRow.qml` espone il numero grezzo `usefulness` senza significato
  dichiarato. E' una priorita' legacy per tipo evento, non uno score NSOM;
- `best_time` mescola istante astronomico esatto e finestra osservativa. Per
  esempio l'ora della Luna nuova puo' cadere di giorno ma viene presentata
  accanto alle vere finestre degli sciami;
- la visibilita' locale dell'evento non e' calcolata: le eclissi chiedono
  esplicitamente di verificare l'orizzonte e gli eventi planetari possono
  cadere sotto l'orizzonte o in luce diurna;
- il setup di eventi futuri usa target sintetici e il seeing della sessione
  corrente, quindi puo' descrivere le condizioni di oggi come se fossero
  quelle della data futura;
- i contatori `Panoramica` ignorano il filtro temporale attivo e i test coprono
  soprattutto wiring QML/setup, non completezza e cronologia del provider.

Direzione consigliata prima di ridisegnare il QML:

1. introdurre un read model Calendario con orizzonte temporale unico e nessun
   cap per utilita';
2. separare istante evento, finestra osservativa e visibilita' locale;
3. mantenere `usefulness` interno e mostrare al massimo una priorita'
   descrittiva;
4. usare profilo/equipment senza seeing corrente per eventi futuri;
5. non applicare la Session NSOM di stasera a date future; meteo e Session
   potranno entrare solo entro il reale orizzonte previsionale;
6. collegare alla fine Calendario e card Home `Prossimi eventi` al nuovo
   contratto e verificarli graficamente.

Implementazione `1.20.0` completata:

- orizzonte unico di 365 giorni e rimozione completa del cap a 18;
- probe deterministico Addis Ababa dal 2026-07-11: 82 eventi, composti da 50
  fasi lunari, 5 opposizioni, 11 congiunzioni planetarie, 4 congiunzioni
  solari, 10 sciami e 2 eclissi;
- le congiunzioni planetarie sono minimi di separazione apparente entro 6
  gradi trovati con Skyfield sulle 21 coppie possibili; la finestra locale
  richiede entrambi i pianeti sopra 8 gradi e marca come breve una durata
  inferiore a 20 minuti;
- le congiunzioni col Sole sono una categoria informativa separata, senza
  suggerimenti ottici e con avvertenza di sicurezza;
- un massimo di eclissi sotto l'orizzonte o in luce diurna non produce una
  finestra locale fittizia; il dettaglio distingue il massimo dalle altre fasi;
- eventi ordinati cronologicamente e sempre conservati anche se non visibili
  localmente;
- `calendarOverview_v2` score-free con timing compatto, finestra, visibilita',
  separazione, partecipanti, priorita' descrittiva e setup futuro senza seeing
  corrente;
- QML Calendario e card Home collegati nel secondo step: filtri annuali senza
  dataset nascosto, contatori planetari/solari separati, stato locale al posto
  del numero grezzo e navigazione Home -> evento -> oggetto preservata;
- il dettaglio apre entrambi i pianeti della coppia, non ripete una finestra
  uguale al timing e non usa piu' il testo fuorviante `per stasera`;
- rendering offscreen a `1600x1000` e `960x900` completato per timeline e
  dettagli senza sovrapposizioni; distribuzione Windows non rigenerata.

Implementazione `1.20.1` completata:

- rimossa soltanto la colonna `Visibile nel mese` dalla tabella; il filtro
  mensile continua a usare l'intero catalogo e il mese selezionato;
- il dettaglio espone `Visibile nel mese corrente` come `Sì`, `No` o `—` e
  calcola un solo oggetto per posizione/mese corrente;
- cache del dettaglio separata da quella completa della lista, con primo probe
  M31 in circa `0,03 s` e accessi successivi cache-hit;
- localizzati tipi e modalita' osservative nella sola presentazione; le combo
  inviano ancora al backend i valori canonici;
- rimossa dalla testata del dettaglio la frase tecnica inglese concatenata al
  testo osservativo italiano;
- nessuna modifica a score, ranking, Planner, Home, Equipment, Sky Compass o
  dettaglio osservativo; distribuzione Windows non rigenerata.

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

Dopo la rifinitura Catalogo `1.20.1`:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer\app\ui astro_viewer\app\ui\main.qml astro_viewer\app\ui\components\DarkComboBox.qml astro_viewer\app\ui\pages\ObjectCataloguePage.qml astro_viewer\app\ui\pages\ObjectDetailPage.qml
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer\tests
```

Risultati:

- `pip check`, ruff e compileall: passed;
- smoke Python e QML sorgente: exit code `0`;
- `qmllint`: exit code `0`, con i warning storici sugli accessi QML non
  qualificati;
- rendering offscreen lista e dettagli alle aree contenuto `1334x1000` e
  `774x700`: completato senza sovrapposizioni;
- probe QML delle combo: label `Ammasso aperto` -> valore backend `Open cluster`
  e `Alto ingrandimento` -> `HighMagnification`;
- probe dettaglio M31: circa `0,03 s` al primo calcolo mensile e cache-hit agli
  accessi successivi;
- suite completa parallela: `721 passed, 557 warnings, 7 subtests passed` in
  `49.02 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota;
- nessuna build Windows: sorgente `1.20.1`, `dist/NightScope` `1.18.8`.

Dopo il riallineamento e le rifiniture finali del dettaglio osservativo
`1.19.0`:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer\app\ui astro_viewer\app\ui\main.qml astro_viewer\app\ui\pages\ObjectDetailPage.qml
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer\tests
```

Risultati:

- `pip check`: nessuna dipendenza rotta;
- ruff completo: passed;
- compileall completo: passed;
- `qmllint`: exit code `0`, con i warning storici sugli accessi QML non
  qualificati;
- test mirati dettaglio/database, inclusi badge e migrazione Luna: `31 passed`;
- rendering offscreen del dettaglio deep sky a `974x820`: completato, senza
  sovrapposizioni; sotto 1180 px il blocco superiore passa a una colonna;
- suite completa parallela: `709 passed, 27 warnings, 7 subtests passed` in
  `32.32 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota;
- nessuna build Windows: sorgente `1.19.0`, `dist/NightScope` `1.18.8`.

Dopo la proiezione Meteo mobile `1.18.6`:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer\app\ui astro_viewer\app\ui\pages\WeatherPage.qml astro_viewer\app\ui\components\WeatherBars.qml
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer\tests
```

Risultati:

- `pip check`: nessuna dipendenza rotta;
- ruff completo: passed;
- compileall completo: passed;
- `qmllint`: exit code `0`, restano soltanto i warning storici sugli accessi
  QML non qualificati;
- test Meteo/release mirati: `39 passed, 16 warnings`;
- `WeatherBars` renderizzato offscreen a `960x220` e `WeatherPage` a
  `1280x900` con controller fittizio, senza usare i file runtime;
- suite completa parallela: `698 passed, 27 warnings, 7 subtests passed` in
  `32.92 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota;
- nessuna build Windows: sorgente `1.18.6`, `dist/NightScope` `1.18.4`.

Dopo i due fix Home `1.18.5`:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer\tests
```

Risultati:

- `pip check`: nessuna dipendenza rotta;
- ruff completo: passed;
- compileall completo: passed;
- probe reale Addis Ababa: M44 `18:48-18:57`, M36 `05:31-06:12`,
  M37 `05:47-06:12`, M38 `05:23-06:12`, M42 `05:46-06:12`;
- test mirati finestre/geometria lunare: `12 passed`, valori diagnostici
  Luna-target invariati;
- test mirati Home/Bortle: `15 passed`;
- suite completa parallela: `696 passed, 28 warnings, 7 subtests passed` in
  `37.14 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota;
- nessuna build Windows: sorgente `1.18.5`, `dist/NightScope` `1.18.4`.

Dopo il completamento sorgente `1.18.4`:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer\app\ui astro_viewer\app\ui\pages\HomePage.qml astro_viewer\app\ui\pages\WeatherPage.qml astro_viewer\app\ui\components\HomePlanStepRow.qml astro_viewer\app\ui\components\HomeVisibleTargetRow.qml astro_viewer\app\ui\components\GlassCard.qml
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer\tests
```

Risultati:

- `pip check`: nessuna dipendenza rotta;
- ruff completo: passed;
- compileall completo: passed;
- `qmllint`: exit code `0`, con i warning storici sugli accessi QML non
  qualificati;
- suite completa parallela: `690 passed, 27 warnings, 7 subtests passed` in
  `37.58 s`; i warning Python sono la deprecazione Skyfield/NumPy gia' nota;
- fixture minimale delle completion provider riallineato al controllo
  credenziali OpenAQ e test mirato passato;
- nessuna build o esecuzione della distribuzione: sorgente `1.18.4`,
  `dist/NightScope` ancora `1.18.3`.

Dopo le correzioni Home `1.18.3`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer\app\ui astro_viewer\app\ui\pages\HomePage.qml
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- ruff completo: passed;
- compileall completo: passed;
- smoke sorgente: exit code `0`;
- QML smoke sorgente: exit code `0`;
- `qmllint`: exit code `0`, con i warning storici sugli accessi QML non
  qualificati della pagina;
- regressione condizioni/Home/Sky Compass: `117 passed`;
- integrazione Home/release QML: `43 passed`, oltre al controllo mirato
  `6 passed`;
- suite completa parallela: `672 passed, 27 warnings, 7 subtests passed` in
  `33.58 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota;
- la verifica visuale della rotella resta da eseguire sulla nuova distribuzione
  richiesta dall'utente;
- build PyInstaller `6.21.0`: passed in circa `203 s`;
- bundle `_internal/VERSION`: `1.18.3` e nuovo `WheelHandler` presente nel QML
  Home impacchettato;
- bundled smoke: exit code `0` in circa `49 s`;
- bundled QML smoke: exit code `0` in circa `8 s`;
- `NightScope.exe` SHA-256:
  `E849EEDB6CCE3A99E94DC74AAC7D0BF39F53F8AB0D95B2F74BC63EE511A2671E`;
- `nightscope.db`, `nightscope.db.backup`, `user_preferences.json`,
  `location_cache.json` e `nasa_aod_cache.json` ripristinati dopo build e smoke
  con corrispondenza SHA-256 rispetto al backup iniziale;
- database finale: `integrity_check=ok`, `user_version=6`;
- sorgente e `dist/NightScope` allineate alla `1.18.3`.

Dopo l'hardening prestazioni astronomiche `1.18.2`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- ruff completo: passed;
- compileall completo: passed;
- smoke sorgente: exit code `0`;
- QML smoke sorgente: exit code `0`;
- suite completa parallela: `670 passed, 28 warnings, 7 subtests passed` in
  `31.14 s`;
- i 28 warning sono la deprecazione Skyfield/NumPy gia' nota in
  `skyfield.searchlib`;
- benchmark Roma/102 target: geometria Luna-target `3.06 s -> 0.30 s`, refresh
  Sky Compass a cache calda circa `0.15 s`;
- probe runtime asincrono: costruttore controller circa `0.22 s`,
  `isLoading=True` durante il worker, snapshot completo circa `3.25 s` senza
  bloccare l'event loop;
- QML non modificato e distribuzione Windows non rigenerata: sorgente
  `1.18.2`, `dist/NightScope` ancora `1.18.0`.

Dopo la correzione della notte locale `1.18.1`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall astro_viewer
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m pytest -q
```

Risultati:

- Python `3.14.5`, Skyfield `1.54`, PySide6 `6.11.1`, pytest `9.1.1` e
  ruff `0.15.21` verificati nella `.venv`;
- confine Addis Ababa del fixture `2026-07-10`: tramonto `18:48`, alba
  `06:12`; lo stesso confine viene ritrovato correttamente dopo mezzanotte;
- giorno polare e buio continuo verificati su Tromso;
- regressione `05:00, 20:00, 21:00`: il salto diurno spezza il gruppo e non
  produce `05:00-22:00`;
- ruff completo: passed;
- compileall completo: passed;
- smoke sorgente: exit code `0`;
- QML smoke sorgente: exit code `0`;
- suite completa: `658 passed, 26 warnings, 7 subtests passed` in `152.80 s`;
- i 26 warning sono la deprecazione Skyfield/NumPy gia' nota in
  `skyfield.searchlib`;
- QML non modificato e distribuzione Windows non rigenerata: sorgente
  `1.18.1`, `dist/NightScope` ancora `1.18.0`.

Dopo la rigenerazione Windows `1.18.0`:

```powershell
.\packaging\build_windows.ps1
Start-Process -FilePath .\dist\NightScope\NightScope.exe -ArgumentList '--smoke-test' -WindowStyle Hidden -Wait -PassThru
Start-Process -FilePath .\dist\NightScope\NightScope.exe -ArgumentList '--qml-smoke-test' -WindowStyle Hidden -Wait -PassThru
```

Risultati:

- Windows build PyInstaller `6.21.0`: passed;
- bundle `_internal/VERSION`: `1.18.0`;
- `NightScope.exe` SHA-256:
  `EF47CAF138C16EF7C14FCF4233D0DD3B5FB0FF02F5D4108795C2448F9D01E18A`;
- bundled smoke: exit code `0`;
- bundled QML smoke: exit code `0`;
- nuovi QML Home presenti nel bundle:
  `HomePlanStepRow.qml`, `HomeVisibleTargetRow.qml` e `HomePage.qml` con
  `homeNightPlanOverview`;
- `nightscope.db`, `nightscope.db.backup`, `user_preferences.json`,
  `location_cache.json` e `nasa_aod_cache.json` salvati prima del `COLLECT`,
  ripristinati, ricontrollati via SHA-256 e ripristinati nuovamente dopo gli
  smoke test;
- database finale: `integrity_check=ok`, `user_version=6`.

Al completamento QML della parte bassa Home `1.18.0`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall astro_viewer
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
.\.venv\Scripts\pyside6-qmllint.exe -I astro_viewer\app\ui astro_viewer\app\ui\pages\HomePage.qml astro_viewer\app\ui\components\HomePlanStepRow.qml astro_viewer\app\ui\components\HomeVisibleTargetRow.qml
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- ruff completo: passed;
- compileall completo: passed;
- smoke Python: passed;
- QML smoke isolato: passed; un run parallelo con lo smoke Python ha prodotto
  un exit code `1` senza messaggio, poi il rilancio isolato e' passato;
- qmllint: exit code `0`, con i warning storici sugli accessi QML non
  qualificati e warning analoghi nei nuovi delegate;
- full suite: `651 passed, 7 subtests passed`;
- distribuzione Windows rigenerata nel passaggio successivo su richiesta
  esplicita.

Durante il terzo step Home inferiore `1.18.0`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/services/home_night_plan_overview.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_home_night_plan_overview.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m compileall -q astro_viewer/app/services/home_night_plan_overview.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_home_night_plan_overview.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_home_night_plan_overview.py astro_viewer/tests/test_home_night_target_pool.py astro_viewer/tests/test_home_observing_overview.py astro_viewer/tests/test_release_scenarios.py astro_viewer/tests/test_phase3_services.py astro_viewer/tests/test_phase6_real_data.py astro_viewer/tests/test_equipment_setup_read_model.py
```

Risultati:

- ruff e compileall focused: passed;
- unit test nuovo contratto: `5 passed`;
- Home/Equipment/release integration: `120 passed, 7 subtests passed`;
- lettura reale della property verificata per stati recommended/monitor/discouraged.

Durante il secondo step Home inferiore `1.18.0`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/astronomy/skyfield_engine.py astro_viewer/app/models/observing.py astro_viewer/app/services/sky_compass_service.py astro_viewer/app/services/sky_compass_nsom_ranking.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_home_night_target_pool.py astro_viewer/tests/test_sky_compass_service.py astro_viewer/tests/test_sky_compass_nsom_ranking.py astro_viewer/tests/test_sky_compass_live_refresh.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_home_night_target_pool.py astro_viewer/tests/test_sky_compass_service.py astro_viewer/tests/test_sky_compass_nsom_ranking.py astro_viewer/tests/test_sky_compass_live_refresh.py astro_viewer/tests/test_phase3_services.py astro_viewer/tests/test_phase6_real_data.py astro_viewer/tests/test_planner_nsom_experimental.py astro_viewer/tests/test_equipment_setup_read_model.py astro_viewer/tests/test_observer_capability_adapter.py
```

Risultati:

- ruff focused: passed;
- pool Home/Sky Compass focused: `67 passed`;
- regressione estesa durante l'implementazione: `237 passed, 7 subtests passed`;
- revalidazione finale del perimetro elencato sopra: `143 passed, 7 subtests passed`;
- benchmark locale sul catalogo Messier corrente: `96` target utili,
  costruzione iniziale circa `0.6 s`, refresh geometria live circa `0.3 s`.

Durante il primo step Home inferiore `1.18.0`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/services/observer_capability_adapter.py astro_viewer/app/services/night_planner_service.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_planner_nsom_experimental.py astro_viewer/tests/test_observer_capability_adapter.py astro_viewer/tests/test_equipment_setup_read_model.py astro_viewer/tests/test_phase3_services.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_phase3_services.py astro_viewer/tests/test_phase6_real_data.py astro_viewer/tests/test_planner_nsom_experimental.py astro_viewer/tests/test_planner_conditions_characterization.py astro_viewer/tests/test_equipment_setup_read_model.py astro_viewer/tests/test_observer_capability_adapter.py astro_viewer/tests/test_advanced_observing_nsom_consumer_split.py astro_viewer/tests/test_advanced_observing_nsom_presentation_runtime.py astro_viewer/tests/test_observation_conditions_service.py
```

Risultati:

- ruff focused: passed;
- Planner/Equipment/NSOM focused: `222 passed, 7 subtests passed`.

Durante lo hardening Open-Meteo `1.17.2`:

```powershell
.\.venv\Scripts\python.exe -m ruff check astro_viewer/app/services/weather_service.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_weather_hardening.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m compileall astro_viewer/app/services/weather_service.py astro_viewer/app/viewmodels/app_controller.py astro_viewer/tests/test_weather_hardening.py astro_viewer/tests/test_release_scenarios.py
.\.venv\Scripts\python.exe -m pytest -q -n auto astro_viewer/tests/test_weather_hardening.py astro_viewer/tests/test_release_scenarios.py astro_viewer/tests/test_refresh_lifecycle.py
.\.venv\Scripts\python.exe astro_viewer/main.py --qml-smoke-test
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Risultati:

- ruff e compileall focused: passed;
- Weather/release/refresh focused tests: `47 passed`;
- QML smoke: passed;
- full suite: `640 passed, 7 subtests passed`.

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

- `dist/NightScope` e' stata rigenerata su richiesta esplicita per `1.18.3` con
  PyInstaller `6.21.0`;
- `VERSION` incorporato sotto `_internal/VERSION`: `1.18.3`; QML Home con
  `WheelHandler` annidato verificato nel bundle;
- `NightScope.exe` SHA-256:
  `E849EEDB6CCE3A99E94DC74AAC7D0BF39F53F8AB0D95B2F74BC63EE511A2671E`;
- `nightscope.db`, `nightscope.db.backup`, `user_preferences.json`,
  `location_cache.json` e `nasa_aod_cache.json` sono stati salvati prima del
  `COLLECT`, ripristinati, ricontrollati via SHA-256 e ripristinati nuovamente
  dopo gli smoke test;
- bundled smoke e bundled QML smoke: exit code `0`;
- database finale: `integrity_check=ok`, `user_version=6`.

## Ambiente `.venv` Verificato

Snapshot controllato prima del prossimo step:

- runtime/UI: `PySide6 6.11.1`, `astropy 8.0.1`, `skyfield 1.54`,
  `numpy 2.5.1`, `requests 2.34.2`, `keyring 25.7.0`, `tzdata 2026.2`;
- AOD/Earthdata: `earthaccess 0.18.0`, `python-cmr 0.13.0`,
  `h5py 3.16.0`, `netCDF4 1.7.4`, `s3fs 2026.6.0`, `aiobotocore 3.7.0`,
  `botocore 1.43.0`, `aiohttp 3.14.1`; `pip check` pulito;
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

1. Non rigenerare la `dist` senza richiesta esplicita: sorgente e distribuzione
   sono rispettivamente `1.20.1` e `1.18.8`.
2. Home e dettaglio osservativo `1.19.0` sono verificati; il ramo Catalogo
   resta separato da NSOM ed e' stato rifinito in `1.20.1`.
3. Calendario `1.20.0` e card Home `Prossimi eventi` sono completati in
   sorgente; la verifica visuale sulla distribuzione resta subordinata a una
   richiesta esplicita di build.
4. Capitoli da lasciare separati:
   - monitoraggio AOD/OpenAQ reale;
   - eventuale design UI/explanations.
5. Non fare tuning e non toccare altre UI senza uno step esplicito.

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
