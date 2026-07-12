# NightScope - Next Chat Handoff

Aggiornato: 2026-07-12

## Stato Versioni

- Versione sorgente: `1.23.3`
- Dist `1.23.3` non rigenerata.
- Durante il lavoro l'utente ha avviato manualmente una build `1.21.1`; non
  assumerne l'esito senza una conferma successiva.
- Commit sorgente validato: `0cb9222 Refresh catalogue observing descriptions`

Il commit release che aggiorna questo handoff contiene solo metadata e
documentazione. Per lo stato del codice usare `0cb9222`; non sostituire questo
hash con un valore previsto prima del commit.

## Commit Catalogo Recenti

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

I punti 1 e 2 della roadmap finale sono conclusi: identita' canonica,
supporto multi-catalogo e import Caldwell. Anche il testo descrittivo e le note
osservative sono stati revisionati; restano futuri curiosita' e nuovi asset
immagine. Non iniziarli automaticamente.

Resta come idea futura una pagina separata `Log Osservazioni`. La sezione
osservazioni e' stata rimossa dal dettaglio oggetto, ma repository e persistenza
restano disponibili. Non implementare il Log senza richiesta esplicita.

## Catalogo Canonico 1.23.3

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
- Lo schema SQLite e' `8`; il bootstrap migra e rimuove `MessierObject` senza
  perdere descrizioni locali e valida identita', riferimenti e primarie dei
  seed prima dell'import.
- I seed correnti sono `catalogue_objects_seed.csv` e
  `catalogue_designations_seed.csv`: 110 Messier e 109 Caldwell, senza
  sovrapposizioni per definizione del Caldwell originale.
- La UI espone 228 righe complessive: 219 target cielo profondo e 9 corpi del
  Sistema Solare. Il filtro Caldwell contiene C1-C109 in ordine naturale.
- Tutti i tipi raw dei 219 target confluiscono nelle classi NSOM esistenti. Le
  17 nebulose planetarie usano `PLANETARY_NEBULA`; i 3 resti di supernova usano
  `DIFFUSE_NEBULA`. Caldwell non introduce categorie Equipment o nuovi pesi.
- `object_descriptions_seed.csv` copre tutti i 219 target profondi; i Caldwell
  hanno nota osservativa, stagione e difficolta' strumentali.
- Le due colonne editoriali coprono 227 target complessivi e sono state
  revisionate in `1.23.3`; ID, ordine, `best_seen` e difficolta' sono invariati.
  Il CSV deve restare UTF-8 senza BOM per il loader `csv.DictReader` corrente.
- `object_images_seed.csv` copre esplicitamente gli stessi 219 ID. Le righe
  senza asset dedicato dichiarano un placeholder locale tipizzato; il passaggio
  futuro sulle immagini dovra' sostituirle con fonte e licenza verificabili.

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

## Validazione 1.23.3

Eseguita nella venv corrente:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\python.exe -m pytest -n auto -q
.\.venv\Scripts\python.exe astro_viewer\main.py --smoke-test
.\.venv\Scripts\python.exe astro_viewer\main.py --qml-smoke-test
```

Risultati:

- `pip check`: nessuna dipendenza rotta.
- Ruff: pulito.
- Compileall: pulito.
- Suite: `664 passed`, `558 warnings`, `7 subtests passed` in `53,45 s`.
- Smoke Python: exit `0`.
- Smoke QML: exit `0`.
- `pyside6-qmllint`: exit `0`; restano warning statiche QML gia' note.

Le 558 warning pytest provengono dalla deprecazione dtype Skyfield/NumPy nota.

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

Il changelog conserva la cronologia delle vecchie fasi di migrazione; non usare
quelle entry come descrizione del runtime corrente.
