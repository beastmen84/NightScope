# NightScope - Next Chat Handoff

Aggiornato: 2026-07-13

## Stato Versioni

- Versione sorgente: `1.27.1`
- Dist `1.27.1` non rigenerata; la distribuzione dichiarata nel README resta
  `1.20.0`.
- Durante il lavoro l'utente ha avviato manualmente una build `1.21.1`; non
  assumerne l'esito senza una conferma successiva.
- Commit sorgente validato: `87f2285 Make filter recommendations aperture-aware`

Il commit release che aggiorna questo handoff contiene solo metadata e
documentazione. Per lo stato del codice usare `87f2285`; non sostituire questo
hash con un valore previsto prima del commit.

## Commit UI Recenti

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

Resta come idea futura una pagina separata `Log Osservazioni`. La sezione
osservazioni e' stata rimossa dal dettaglio oggetto, ma repository e persistenza
restano disponibili. Non implementare il Log senza richiesta esplicita.

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
- Lo schema SQLite e' `14`; il bootstrap migra e rimuove `MessierObject`, valida
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

## Validazione 1.27.1

Eseguita nella venv corrente:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\python.exe -m pytest -n 4 -q
.\.venv\Scripts\pyside6-qmllint.exe astro_viewer\app\ui\pages\EquipmentFiltersReducersPage.qml
```

Risultati:

- `pip check`: nessuna dipendenza rotta.
- Ruff: pulito.
- Compileall: pulito.
- Suite: `703 passed`, `557 warnings`, `7 subtests passed` in `119,08 s`.
- `pyside6-qmllint` sulla pagina Equipment: exit `0`, nessun warning.
- Verificati setup telescopio/binocolo, soglie prodotto e target, fallback
  singolo, catalogo canonico a 48 filtri e persistenza Equipment.
- QML smoke non eseguito per non creare file runtime; la dist non e' stata
  rigenerata.

Le 557 warning pytest provengono dalla deprecazione dtype Skyfield/NumPy nota.

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
- `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
- `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
- `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`
- `docs/TESTING.md`
- `docs/IMAGE_ASSET_POLICY.md`

Il changelog conserva la cronologia delle vecchie fasi di migrazione; non usare
quelle entry come descrizione del runtime corrente.
