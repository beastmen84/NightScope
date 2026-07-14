# NightScope - Next Chat Handoff

Aggiornato: 2026-07-14

## Stato Versioni

- Versione sorgente: `1.31.1`
- Dist `1.31.1` non rigenerata; la distribuzione dichiarata nel README resta
  `1.20.0`.
- Durante il lavoro l'utente ha avviato manualmente una build `1.21.1`; non
  assumerne l'esito senza una conferma successiva.
- Commit sorgente validato: `50bffc1 Fix ISS calendar refresh lifecycle`

Il commit che aggiorna questo handoff contiene solo documentazione. Per lo
stato del codice usare `50bffc1`; non sostituire questo
hash con un valore previsto prima del commit.

## Commit UI Recenti

- `50bffc1 Fix ISS calendar refresh lifecycle`
- `c758dac Add ISS calendar passes`
- `5f6c2d0 Fix localization review findings`
- `60c5d46 Complete scalable application localization`
- `5ef1fdf Add Italian and English UI translations`
- `53244e2 Add observation log`
- `87f2285 Make filter recommendations aperture-aware`
- `a859d75 Add photographic reducer recommendations`
- `40a0a39 Add profile-aware filter recommendations`
- `cbc14c4 Localize remaining profile messages`
- `bbeec59 Add filter and reducer equipment UI`
- `276c686 Add Sky Compass Home filter`

## Commit Equipment Recenti

- `87f2285 Make filter recommendations aperture-aware`
- `a859d75 Add photographic reducer recommendations`
- `d360b58 Refine target filter preferences`
- `40a0a39 Add profile-aware filter recommendations`
- `1b524a9 Harden equipment catalog integrity`
- `6e2732d Package accessory catalog seeds`
- `bbeec59 Add filter and reducer equipment UI`
- `294a2de Add filter and reducer catalog persistence`

## Commit Catalogo Recenti

- `a859d75 Add photographic reducer recommendations`
- `e1b3c5d Align content migration test with schema 10`
- `f9331b8 Refresh managed catalogue content safely`
- `60a9510 Replace Solar System placeholder images`
- `7de6a6f Replace catalogue placeholder images`
- `f30bc17 Add source-backed object curiosities`
- `0cb9222 Refresh catalogue observing descriptions`
- `ce77d6d Fix catalogue NSOM target taxonomy`
- `f2b8f90 Align Caldwell detail content test`
- `2a00e63 Complete catalogue content seeds`
- `9a39501 Add Caldwell catalogue`
- `2ae2289 Correct catalogue overlap example`
- `2256899 Migrate recommendation matrix seed reader`
- `f45e3eb Update catalogue maintenance seeds`
- `d4877c4 Migrate catalogue consumers to canonical IDs`
- `4312c14 Introduce generic catalogue persistence`

## Commit NSOM Recenti

- `67b7023 Harden presentation counts`
- `ce43d94 Align seeing refresh fixtures`
- `bbba6af Deduplicate NSOM runtime targets`
- `1b1895a Fix NSOM factor accounting`
- `7658a65 Complete NSOM backend consolidation`
- `f1294c5 Fix NSOM target timing and equipment context`
- `021187e Unify NSOM observation environment`
- `82d89d0 Separate intrinsic NSOM target inputs`

## Stato Generale

Il rework NSOM backend e il relativo passaggio UI sono conclusi per lo scope
corrente. Home, Meteo, dettaglio osservativo, Calendario e dettaglio Catalogo
sono stati verificati e rifiniti. La UI mantiene payload compatibili e non
espone modelli/scalari NSOM grezzi.

I punti 1, 2, 3 e 4 della roadmap catalogo sono conclusi: identita' canonica,
supporto multi-catalogo/import Caldwell, contenuti visibili con curiosita' e
asset scientifici dedicati, inclusi i nove corpi del Sistema Solare, e cataloghi
Filtri/Riduttori collegati ai profili. Testo descrittivo e note osservative
restano separati dai nuovi contenuti editoriali. L'audit `1.25.1` ha inoltre
chiuso integrita' profili/Equipment, aggiornamento dei seed editoriali e
localizzazione dei messaggi residui senza modificare NSOM.

Il punto 5 e' concluso per lo scope concordato. Da `1.26.0` il dettaglio
osservativo puo' mostrare un filtro primario e un colore opzionale confrontando
le preferenze del target con il profilo attivo. Da `1.27.0` puo' inoltre
raccomandare un riduttore fotografico usando il telescopio gia' scelto per il
target e compatibilita' esatte normalizzate. Entrambe sono proiezioni score-free
e non cambiano la configurazione calcolata. Un eventuale calcolo ottico reale
del riduttore resta futuro e richiederebbe camera, sensore, image circle e
backfocus.

La pagina separata `Log Osservazioni` e' implementata da `1.28.0` tra Calendario
e Meteo. La sezione resta fuori dal dettaglio oggetto e non modifica score,
ranking, NSOM o configurazioni consigliate.

La localizzazione `1.30.0` copre QML, messaggi Python, read model, formati
locali e contenuti strutturati dei seed. Il selettore nella barra laterale
cambia live lingua e locale, preserva le altre preferenze e non ricalcola
astronomia, meteo, equipaggiamento, score o NSOM. I testi inseriti dall'utente
restano invariati.

Da `1.31.0` il Calendario include anche eventi operativi transitori. La prima
sorgente implementata calcola i passaggi ISS visibili per la posizione attiva;
non crea `CatalogueObject`, non riceve score e non entra in Equipment, Planner,
Home ranking o NSOM. Home continua a consumare la stessa proiezione cronologica
del Calendario e mostra i passaggi ISS tra i prossimi eventi.

## ISS ed Eventi Transitori 1.31.x

- `TransientCalendarEventSource` e' il confine generico per future sorgenti
  operative; `IssPassEventSource` e' l'unica implementazione attuale. Da
  `1.31.1` il confine separa preparazione provider/cache e calcolo Skyfield.
- Il motore annuale Skyfield resta proprietario di fasi, opposizioni,
  congiunzioni, eclissi e sciami. Non chiama provider transitori: una sorgente
  lenta o fallita non ritarda e non elimina questi eventi.
- La ISS usa gli OMM pubblici CelesTrak del NORAD `25544`, senza account. Il
  calcolo riusa Skyfield, SGP4, Requests e NumPy gia' installati; pandas e
  astroquery non sono stati aggiunti perche' non servono a questa pipeline.
- La finestra mobile e' di 10 giorni. Un passaggio richiede quota ISS almeno
  `10 gradi`, satellite illuminato e Sole locale a quota non superiore a
  `-6 gradi`; i campioni della finestra visibile sono distanziati di 10 secondi.
- Ogni evento espone inizio, fine, culminazione, altezza massima, direzione
  iniziale/finale, durata, illuminazione, fonte e freschezza dei dati.
- Il dettaglio usa indicazioni operative score-free e non presenta la ISS come
  setup personalizzato o oggetto apribile. Il Calendario ha filtro e conteggio
  `ISS`; Home mantiene gli 8 eventi successivi su layout largo e 4 su stretto.
- Gli intervalli conclusi vengono esclusi anche se appartengono al giorno
  corrente; un passaggio gia' iniziato ma non concluso resta visibile. Gli
  eventi istantanei di date passate vengono eliminati prima della deduplica.
- `CalendarOverviewService` e' ora `calendar_overview_v3`; i nuovi campi sono
  generici per supportare in seguito comete o asteroidi senza cambiare il
  contratto base.
- Il controller prepara rete/cache fuori dal lock astronomico, propaga gli
  eventi sotto lock e rimpiazza solo il sottoinsieme transitorio se la location
  key e' ancora attuale. Il ricalcolo avviene ogni ora; il fetch OMM resta
  limitato dalla TTL di 6 ore.
- Gli ID dei passaggi derivano dalla rivoluzione orbitale e non dai secondi del
  picco previsto. Il dettaglio espone l'ora reale dell'ultimo aggiornamento.

## Localizzazione Completa 1.30.0

- `TranslationManager` viene installato prima del controller e del caricamento
  QML; italiano e' lingua sorgente/fallback e i pack sono scoperti dai file
  `<codice>.json`, senza una lista di lingue in Python, QML o packaging.
- Ogni lingua usa `<codice>.json` per metadata, formati e contenuti editoriali,
  `<codice>.ts` per i messaggi QML/Python e `<codice>.qm` per il runtime.
- `translationManager` espone automaticamente alla barra laterale le lingue
  scoperte; `engine.retranslate()` aggiorna live i binding `qsTr()`.
- La preferenza `language` condivide `user_preferences.json` e viene aggiornata
  atomicamente preservando le altre chiavi.
- Le stringhe Python sono lazy e i servizi interni consumano valori canonici;
  date, numeri e payload vengono renderizzati solo al boundary Qt/QML.
- `astro_viewer/translations` contiene pack completi `it` ed `en`; PyInstaller
  include l'intera directory e quindi acquisisce anche nuovi pack senza cambiare
  la spec.
- Gli updater estraggono `1518` messaggi per lingua, preservano le traduzioni
  gia' revisionate, rifiutano cataloghi incompleti o placeholder incompatibili
  e producono output idempotente.
- La review successiva ha corretto la terminologia astronomica inglese, i nomi
  IAU delle costellazioni, i caratteri invisibili nei contenuti, la sicurezza
  per l'osservazione solare, `R.A.` e l'ordinamento localizzato dei filtri.
- I test di regressione coprono ora anche label dentro oggetti QML, termini
  editoriali revisionati, assenza di `U+200B` e sorting dopo il rendering.
- L'aggiunta del francese richiede solo `fr.json`, `fr.ts` e `fr.qm`, seguendo
  `docs/LOCALIZATION.md`; nessuna modifica applicativa e' necessaria.
- La barra di navigazione usa uno `ScrollView`, mantenendo selettore lingua e
  riepilogo sessione accessibili anche all'altezza minima supportata.

## Log Osservazioni 1.28.0

- `ObservationRepository` espone inserimento, elenco completo ordinato,
  modifica ed eliminazione; non esiste piu' il limite storico di 10 record.
- `ObservationLogService` valida data/ora locale, oggetto e voto `1-5`, rifiuta
  record futuri e costruisce entry QML e riepilogo senza dipendenze NSOM.
- Il controller espone `observationLog`, `observationLogSummary`, default locali
  e slot CRUD sincroni. Il vecchio `saveObservation` legato all'oggetto
  selezionato e `observationHistory` sono stati rimossi.
- La UI permette ricerca su oggetto, luogo, setup e note, filtro per voto,
  inserimento, modifica ed eliminazione con conferma.
- La tabella `ObservationHistory` non cambia schema; bootstrap, copia runtime e
  preservazione dei dati utente restano invariati.

## Catalogo Canonico 1.27.0

- `CatalogueObject` contiene una riga per target fisico.
- `CatalogueDesignation` associa catalogo, codice e ordine allo stesso
  `object_id`; un indice parziale consente una sola designazione primaria.
- Gli ID Messier esistenti restano `messier-Mxx` per non rompere asset,
  descrizioni o riferimenti persistiti.
- `CatalogueRepository` restituisce ogni oggetto una volta con `designations`,
  `catalogues`, `primary_catalogue` e `primary_designation`.
- Ricerca e lookup riconoscono ID fisico, codice breve e forma qualificata, per
  esempio `messier-M31`, `M31` e `Messier-M31`; lo stesso vale per eventuali
  designazioni secondarie.
- Il filtro catalogo proietta la designazione richiesta ma non cambia l'ID e non
  incrementa `catalogueTotalCount`.
- Lo schema SQLite corrente e' `15`; la versione `14` ha introdotto il flag
  riduttori, mentre la `15` aggiunge la cache orbitale. Il bootstrap migra e
  rimuove `MessierObject`, valida
  identita', riferimenti e primarie dei seed e distingue contenuti editoriali
  gestiti da import personalizzati.
- I seed correnti sono `catalogue_objects_seed.csv` e
  `catalogue_designations_seed.csv`: 110 Messier e 109 Caldwell, senza
  sovrapposizioni per definizione del Caldwell originale.
- `catalogue_objects_seed.csv` abilita `imaging_reducer_recommended` su 53
  target estesi. Il flag e' indipendente dalla tassonomia e non entra in score
  o ranking.
- La UI espone 228 righe complessive: 219 target cielo profondo e 9 corpi del
  Sistema Solare. Il filtro Caldwell contiene C1-C109 in ordine naturale.
- Il toggle Home `Solo suggeriti ora` usa tutti gli ID in `skyCompass.targets`
  per filtrare piano e alternative senza cambiare ordine o ranking. Resta attivo
  durante i tick live e si spegne automaticamente quando il payload non ha
  target; i filtri per categoria e i conteggi operano sul sottoinsieme corrente.
- Tutti i tipi raw dei 219 target confluiscono nelle classi NSOM esistenti. Le
  17 nebulose planetarie usano `PLANETARY_NEBULA`; i 3 resti di supernova usano
  `DIFFUSE_NEBULA`. Caldwell non introduce categorie Equipment o nuovi pesi.
- `object_descriptions_seed.csv` copre tutti i 228 target selezionabili. Le 180
  note prima duplicate sono ora specifiche per oggetto; i Caldwell includono
  contesto misurabile e il Sole espone una procedura di sicurezza esplicita.
- Le righe seed di `ObjectDescription` e `ObjectCuriosity` usano
  `is_builtin = 1` e vengono aggiornate dal bootstrap. L'importatore descrizioni
  assegna `is_builtin = 0`, quindi le righe personalizzate vengono preservate.
  Il CSV deve restare UTF-8 senza BOM per il loader `csv.DictReader` corrente.
- `ObjectCuriosity` e `object_curiosities_seed.csv` coprono gli stessi 228
  target con testi italiani specifici, fonte e URL: 228 testi unici, 227 URL
  verificate e nessun ingresso in NSOM, Equipment o ranking.
- `object_images_seed.csv` usa un JPEG RGB locale `512 x 512` dedicato per
  ognuno dei 219 target profondi: 200 2MASS, 15 Pan-STARRS1 e 4 SkyMapper DR4,
  tutti da CDS `hips2fits` con URL esatta, attribuzione e licenza ODbL nel seed.
- I nove target del Sistema Solare usano altrettanti JPEG RGB `512 x 512`
  derivati da immagini PIA NASA/JPL, con pagina sorgente e credito missione. Le
  immagini sono statiche e processate, non descrivono fase o aspetto corrente.
- Il dettaglio Home e Catalogo mostra curiosita', fonte e credito immagine
  cliccabili. Il bootstrap sostituisce i vecchi SVG deep-sky e Sistema Solare
  gestiti da NightScope ma conserva righe immagine personalizzate dall'utente.
- `sync_catalogue_images.py --check` e `sync_solar_system_images.py --check`
  validano offline tutti gli asset;
  `audit_curiosity_sources.py` ricontrolla le fonti via rete. La policy completa
  e' in `docs/IMAGE_ASSET_POLICY.md`; DSS non e' usato.

## Equipment 1.27.0

- La pagina `Filtri e riduttori` usa due cataloghi affiancati con ricerca e
  layout responsive coerente con `Oculari e Barlow`.
- Il seed contiene 48 filtri visuali unici di 6 produttori e 24
  riduttori/correttori di 7 produttori; provenienza e riferimenti sono in
  `astro_viewer/data/DATA_SOURCES.md`.
- I filtri conservano classe, banda/lunghezza d'onda, trasmissione e apertura
  minima. Il barilotto non e' modellato e le classi colorate identificano il
  colore specifico. I riduttori conservano fattore, sistema e modelli
  compatibili, connessione, backfocus, uso visuale/fotografico e correzione del
  campo.
- `ReducerTelescopeCompatibility` conserva 16 associazioni esatte tra riduttori
  dedicati e `TelescopeModel`; i riduttori universali non ricevono associazioni
  artificiali. Il campo descrittivo dei modelli resta disponibile alla UI.
- I riduttori creati dall'utente usano la stessa relazione normalizzata: il
  form offre ricerca e selezione multipla sui 133 modelli di telescopio, il
  repository valida gli ID e i collegamenti sopravvivono al reseed.
- Filtri e riduttori possono essere assegnati e rimossi dal profilo attivo.
  `equipmentChanged` aggiorna immediatamente anche un dettaglio osservativo
  aperto, ma non ricalcola NSOM o capacita'.
- Tutti i cataloghi Equipment espongono `is_builtin`. Le voci seed non mostrano
  `Modifica` o `Elimina` e il repository blocca entrambe le operazioni; le voci
  create dall'utente restano modificabili ed eliminabili dopo aver rimosso i
  collegamenti ai profili.
- Le connessioni Equipment abilitano le foreign key. La migrazione elimina
  assegnazioni orfane nelle sei tabelle profilo e i conteggi d'uso considerano
  profili validi distinti, senza duplicare il telescopio tra campo legacy e
  relazione molti-a-molti.

## Raccomandazione Filtri 1.27.1

- `CatalogueObject` espone `best_filter_class`, `fallback_filter_class` e
  `optional_color_filter_class`; le 219 righe conservano invariati tutti i
  metadati astronomici precedenti.
- Il seed assegna una preferenza primaria a 35 nebulose: 12 UHC, 20 OIII e 3
  H-beta. Il fallback e' riservato ad alternative equivalenti, non allo stacking.
- Luna e Venere preferiscono polarizzatore con ND come alternativa. Marte,
  Giove e Saturno preferiscono contrasto con Moon & Skyglow come alternativa.
  Gli eventuali colori, incluso il giallo per Urano e Nettuno, restano
  raccomandazioni secondarie separate.
- `FilterRecommendationService` opera solo se il setup target-specifico sceglie
  un telescopio reale. Il catalogo completo e l'apertura verificano prima la
  classe; soltanto i filtri del profilo attivo possono risultare disponibili.
- Il match scarta prodotti sotto la relativa `minimum_aperture_mm` e preferisce
  la soglia valida piu' alta prima dei tie-break per nome e ID. Il colore giallo
  opzionale per Urano e Nettuno richiede almeno `280 mm`.
- L'ordine resta primaria/fallback, ma se nessun prodotto posseduto e' adatto
  viene mostrata soltanto la classe primaria utilizzabile come
  `non disponibile`, senza testo ambiguo con due classi.
- `observingObjectDetail_v3` trasporta un payload sanitizzato con `primary`,
  `optionalColor` e il ramo separato `reducerRecommendation`; il dettaglio
  Catalogo non mostra configurazioni osservative e resta invariato.
- Il runtime usa direttamente il catalogo canonico senza migrazioni dei vecchi
  duplicati per barilotto e senza la classe `COLOR_UNSPECIFIED`.
- Questa funzione non modifica EquipmentService, ObserverCapability, score,
  ranking, Planner, Home, Sky Compass o NSOM.

## Raccomandazione Riduttori 1.27.0

- `ReducerRecommendationService` opera solo se il target abilita
  `imaging_reducer_recommended` e la configurazione consigliata contiene un ID
  telescopio.
- Il match richiede `imaging_compatible` e un collegamento esatto
  `ReducerTelescopeCompatibility`; le descrizioni testuali non vengono
  interpretate.
- Prima vengono cercati i riduttori nel profilo attivo. Se non esiste un match
  posseduto, i prodotti compatibili del catalogo sono mostrati come
  `non disponibili`; senza match esatto la riga non compare.
- Piu' match sono elencati in ordine deterministico. Non viene scelto un
  presunto migliore senza dati su camera, sensore, image circle e backfocus.
- La funzione non calcola focale o campo risultanti e non modifica
  EquipmentService, ObserverCapability, score, ranking, Planner, Home, Sky
  Compass o NSOM.

## NSOM Canonico

Il runtime ha un solo percorso di ranking:

1. `IntrinsicTargetQuality` usa qualita' intrinseca separata dalla geometria.
2. `NsomObservationEnvironmentService` compone geometria, Luna, fondo cielo
   VIIRS/Bortle, seeing/trasparenza, AOD/OpenAQ e orizzonte.
3. `ObserverCapability` e `PracticalTargetValue` aggiungono lo strumento
   selezionato per il target.
4. `SessionViability` e' binaria, cosi' il meteo non viene moltiplicato due
   volte.
5. Planner e Best Object classificano `ObservationOpportunity`.
6. `RecommendationConfidence` resta metadata e non scala lo score.

Consumer attivi:

- Home categorie: `NsomCategoryScoreService`.
- Home cielo profondo: `HomeRecommendedDeepSkyNsomRankingService`.
- Best Object: `BestObjectNsomSelectionService`.
- Planner: `NightPlannerService` + `PlannerNsomScoringService`.
- Sky Compass: unico `SkyCompassService`.

Audit invarianti `1.21.1`:

- ogni ID target canonico viene valutato/conteggiato una sola volta;
- la prima occorrenza resta stabile e gli elementi senza ID non sono rimossi;
- piano e alternative Home, Sky Compass e conteggi Equipment sono difensivi
  anche se ricevono input ripetuti;
- intrinseco e seeing non vengono ricostruiti due volte nello stesso passaggio;
- confidence OpenAQ usa il campo runtime corretto, la geometria lunare e' per
  target e l'assenza VIIRS non viene duplicata come fallback generico.

I provider opzionali mancanti producono fattori neutrali e confidence minore;
non selezionano un vecchio algoritmo. Solo un'eccezione inattesa in Sky Compass
usa il fallback geometrico con lo stesso payload QML.

## Cleanup 1.21.0

Rimossi:

- `PlannerScoringService` e rollback formula Planner;
- servizio Sky Compass NSOM parallelo;
- servizi/payload ombra Advanced Observing e Detail/Object;
- snapshot ed export diagnostici automatici nel controller;
- feature flag AOD/OpenAQ e geometria lunare;
- fallback Best Object in `ObservingScoreService`;
- exporter Planner senza chiamanti;
- test di comparazione, characterization e rollback ritirati;
- `ObjectRow.qml` inutilizzato.

`nsom_runtime_builders.py` contiene solo factory runtime realmente usate.
`ObservingCategoryScores` e' il modello interno corrente per le categorie Home.

## Confini Dati

- `CelestialObject.intrinsic_score` e'
  interno e non compare in QML.
- `SeeingTransparency.atmospheric_transparency_score` esclude il fondo cielo
  statico ed e' interno.
- `CelestialObject.score` resta un campo display/compatibilita'; non spiega da
  solo l'ordine NSOM.
- AOD/OpenAQ non muta `CelestialObject.score` e influenza una sola volta la
  trasparenza atmosferica canonica.
- VIIRS/Bortle e' fondo cielo statico, distinto da meteo e aerosol.
- Geometria lunare e telescope mapping sono calcolati per target.

## UI Completata

### Home

- Parte alta usa `homeObservingOverview` con Sessione, Meteo, condizioni
  planetarie, cielo profondo e Luna.
- Parte bassa usa `homeNightPlanOverview`.
- Piano: fino a quattro opportunita' migliori, poi ordine cronologico.
- Altri oggetti: lista completa scrollabile, ordinamento temporale e nome
  naturale (`M3`, `M40`, `M100`).
- Scroll interno non propaga alla pagina quando il puntatore e' nella lista.
- Sidebar usa lo stato Sessione corrente, non la vecchia qualita' osservativa.

### Meteo

- Copertura nuvolosa e dettaglio orario mostrano le prossime 24 ore.
- Le ore della notte osservativa sono evidenziate senza conflitto con l'ora
  selezionata.
- Scrollbar orizzontale del dettaglio e' nascosta.
- AOD e OpenAQ hanno semantica/freschezza esplicita.

### Dettaglio Osservativo

- Read model score-free con finestra, stato locale, setup target-specific e
  ciclo lunare quando applicabile.
- Nessuna sezione osservazioni.
- Il ramo Catalogo resta separato.

### Calendario

- Orizzonte unico di 365 giorni, senza cap agli eventi.
- Eventi e partecipanti con lo stesso ID normalizzato sono contati una volta;
  gli eventi senza ID restano nel dataset.
- Include congiunzioni tra pianeti osservabili e conserva le congiunzioni
  solari come categoria informativa separata.
- Eventi, finestre, visibilita', partecipanti e separazione sono campi distinti.
- Home `Prossimi eventi` usa la proiezione Calendar corrente.
- I passaggi ISS usano una sorgente a 10 giorni separata dall'orizzonte annuale
  e vengono uniti soltanto nella proiezione cronologica finale.
- Il contratto distingue `startsAt`, `endsAt`, `peakAt`, fatti operativi e
  metadati sorgente; non assegna un target catalogo alla ISS.

### Catalogo

- Lista senza colonna mensile ridondante.
- Filtro `visibili nel mese` resta attivo.
- Dettaglio mostra `Visibile nel mese corrente` calcolato per posizione e mese
  locali, indipendentemente dal filtro lista.
- Tipi e modalita' osservative sono localizzati in italiano.

## Cache e Refresh

- VIIRS viene rivalidato ogni 7 giorni mantenendo il valore stale in caso di
  errore NASA.
- AOD usa TTL 18 ore e preflight cache prima del worker.
- AOD e VIIRS riusano dati validi entro 500 metri per assorbire jitter della
  posizione Windows.
- Risultati provider con location key stale vengono scartati.
- AOD/OpenAQ completati ricalcolano i consumer NSOM senza ripetere effemeridi o
  geometria lunare.
- Open-Meteo conserva la cache sui fallimenti retryable e programma il retry
  controllato.
- `OrbitalElementCache` conserva OMM/TLE per provider e oggetto. Per la ISS il
  TTL e' 6 ore; se CelesTrak non risponde, un elemento resta utilizzabile fino
  a 3 giorni dalla propria epoca, poi i passaggi non vengono inventati.
- Il timer ISS ricalcola ogni ora la finestra mobile usando la cache: non
  trasforma la cadenza di calcolo in una richiesta CelesTrak oraria.

## Validazione 1.31.1

Eseguita nella venv corrente:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer tools
.\.venv\Scripts\python.exe -m compileall -q astro_viewer tools
.\.venv\Scripts\python.exe -m pytest -q -n 4 astro_viewer\tests
.\tools\update_translations.ps1 -UpdateOnly
.\tools\update_translations.ps1 -CompileOnly
$qmlFiles = Get-ChildItem astro_viewer\app\ui -Recurse -Filter *.qml | Select-Object -ExpandProperty FullName
& .\.venv\Lib\site-packages\PySide6\qmllint.exe -I astro_viewer\app\ui @qmlFiles
.\.venv\Scripts\python.exe -m astro_viewer.main --smoke-test
.\.venv\Scripts\python.exe -m astro_viewer.main --qml-smoke-test
```

Risultati:

- `pip check`: nessuna dipendenza rotta.
- Ruff: pulito.
- Compileall: pulito.
- Suite: `733 passed`, `563 warnings`, `7 subtests passed` in `90,36 s`.
- Cataloghi: `1518` messaggi completi per lingua; entrambi i `.qm` compilati.
- Updater TS verificato idempotente: il secondo passaggio rileva `0` messaggi
  nuovi e `1518` gia' presenti per lingua.
- `qmllint` su tutta la UI: exit `0`; restano solo warning storici di accesso
  non qualificato, nessun errore QML.
- Smoke backend e QML del bootstrap di produzione: exit `0`. I test lingua
  continuano a caricare la scena QML in italiano e inglese da runtime
  temporanei.
- Verificati cambio live, fallback italiano, formati locali, contenuti seed,
  persistenza della lingua, preservazione delle altre preferenze, terza lingua
  sintetica, packaging, ordine della navigazione e assenza di ricalcoli NSOM.
- Dist non rigenerata.

Le 563 warning pytest provengono dalla deprecazione dtype Skyfield/NumPy nota.

## Regole Operative

- Usare sempre `.venv`.
- Eseguire test in parallelo con `pytest -n auto` salvo diagnosi mirate.
- Aggiornare documentazione e changelog con ogni release.
- Fare commit focalizzati a fine step.
- Non rigenerare `dist` salvo richiesta esplicita dell'utente.
- Non salvare i cinque file runtime che l'utente preferisce ricreare puliti.
- Non leggere, modificare o includere `nasa_login.txt`.
- Non esporre score/fattori NSOM in QML senza prima definire un contratto UI
  comprensibile.

## Documenti Correnti

- `docs/ARCHITECTURE.md`
- `docs/CALCULATION_LOGIC.md`
- `docs/LOCALIZATION.md`
- `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
- `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
- `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`
- `docs/TESTING.md`
- `docs/IMAGE_ASSET_POLICY.md`

Il changelog conserva la cronologia delle vecchie fasi di migrazione; non usare
quelle entry come descrizione del runtime corrente.
