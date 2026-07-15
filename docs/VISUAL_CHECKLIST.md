# NightScope - Visual Review Checklist

Aggiornato: 2026-07-15

Questo documento e' la coda unica del controllo visuale pre-release. Durante
la raccolta delle schermate si aggiornano soltanto risultati e stato dei
rilievi; codice, layout e traduzioni verranno corretti in un unico passaggio
quando la panoramica sara' completa e l'utente dara' conferma.

Stati usati:

- `APERTA`: correzione confermata.
- `DA DECIDERE`: comportamento corretto ma presentazione da valutare.
- `VERIFICATA`: controllo superato, nessuna modifica richiesta.
- `RISOLTA`: correzione applicata e verificata.

## Matrice In Corso

Scenario corrente: localita' valida, NASA Earthdata e OpenAQ configurati,
profilo Equipment con telescopio, oculare, filtro e riduttore.

| Pagina | Italiano | Inglese | Stato |
| --- | --- | --- | --- |
| Provider dati | controllata | controllata | completata |
| Configurazione localita' | controllata | controllata | completata |
| Profili | controllata | controllata | completata |
| Oggetti celesti - elenco | controllata | controllata | completata |
| Oggetti celesti - dettaglio | controllata | controllata | completata |
| Telescopi - elenco | controllata | controllata | completata |
| Telescopi - aggiunta | controllata | controllata | completata |
| Telescopi - modifica | controllata | controllata | completata |
| Oculari e Barlow - elenco | controllata | controllata | completata |
| Oculari - aggiunta | controllata | controllata | completata |
| Oculari - modifica | controllata | controllata | completata |
| Barlow - aggiunta | controllata | controllata | completata |
| Barlow - modifica | controllata | controllata | completata |
| Filtri e riduttori - elenco | controllata | controllata | completata |
| Filtri - aggiunta | controllata | controllata | completata |
| Filtri - modifica | controllata | controllata | completata |
| Riduttori - aggiunta | controllata | controllata | completata |
| Riduttori - modifica | controllata | controllata | completata |
| Binocoli - elenco | controllata | controllata | completata |
| Binocoli - aggiunta | controllata | controllata | completata |
| Binocoli - modifica | controllata | controllata | completata |

## Correzioni Aperte

- [ ] **VIS-001 - Localita' - traduzione sorgente Windows (`APERTA`)**
  - In inglese `Windows specifies` e' una traduzione errata di `Windows precisa`.
  - Testo previsto: `Posizione Windows precisa` / `Precise Windows location`.

- [ ] **VIS-002 - Provider - nome NASA Earthdata (`APERTA`)**
  - Il marchio ufficiale deve restare `NASA Earthdata` anche in italiano,
    invece di `Earthdata NASA`.

- [ ] **VIS-003 - Profili - riepilogo oculari e Barlow (`APERTA`)**
  - `Disponibili` / `Available` sembra descrivere tutto il profilo, ma il
    conteggio include intenzionalmente soltanto oculari e Barlow usati per le
    combinazioni di ingrandimento.
  - Rendere esplicito il significato, per esempio `Opzioni di ingrandimento` /
    `Magnification options`.

- [ ] **VIS-004 - Profili - titolo capacita' inglese (`APERTA`)**
  - `Profile capacity` e' poco idiomatico; usare `Profile capabilities`.

- [ ] **VIS-005 - Sidebar - stato serata inglese (`APERTA`)**
  - `To be monitored` e' comprensibile ma meccanico; valutare
    `Monitor conditions` mantenendo invariata la semantica dello stato.

- [ ] **VIS-006 - Profili - nome riduttore troncato (`APERTA`)**
  - Il nome `Celestron Reducer-Corrector...` viene eliso nella colonna dei
    riduttori.
  - Consentire al nome un massimo di due righe senza rendere instabile la
    griglia o allargare eccessivamente la scheda.

- [ ] **VIS-008 - Oggetti celesti - nomi catalogo localizzati (`APERTA`)**
  - La sorgente `catalogue_objects_seed.csv` e' italiana, ma il generatore la
    dichiara inglese. In inglese restano quindi soprannomi come `Nebulosa Iris`
    e `Galassia Fuochi d'Artificio`; in italiano 59 nomi NGC/IC perdono lo
    spazio del designatore, per esempio `NGC188` e `IC342`.
  - Correggere la lingua sorgente e rigenerare i contenuti preservando sempre
    i designatori canonici; tradurre soltanto il soprannome descrittivo.
  - Verificare anche ricerca, descrizione breve e tutti i 219 oggetti seed, non
    soltanto le righe Caldwell mostrate negli screenshot.

- [ ] **VIS-009 - Dettaglio oggetto - credito immagine inglese (`APERTA`)**
  - Il testo `HiPS a colori e ritaglio: CDS` resta italiano nella pagina
    inglese.
  - Conservare invariati survey, enti e licenza, localizzando soltanto la parte
    descrittiva dell'attribuzione.

- [ ] **VIS-010 - Dettaglio oggetto - nota osservativa inglese (`APERTA`)**
  - La frase di C1 `Use a medium shot...; increases moderately...` usa un
    termine fotografico errato e una forma verbale non corretta.
  - Testo coerente con il dominio: `Use a medium field under dark skies;
    increase magnification moderately to separate the many faint stars from
    the background.`
  - Controllare le altre note osservative inglesi generate per individuare
    traduzioni automatiche analoghe.

- [ ] **VIS-011 - Dettaglio oggetto - formato decimale inglese (`APERTA`)**
  - Nel dettaglio inglese C1 la dimensione massima appare come `0,233°`, mentre
    nell'elenco inglese e' correttamente `0.233°`.
  - Assicurare che i label numerici preformattati seguano il nuovo locale dopo
    il cambio lingua live oppure derivarli dal valore numerico in presentazione.

- [ ] **VIS-012 - Oggetti celesti - soglia geometrica (`APERTA`)**
  - `Utile (≥15°)` / `Useful (≥15°)` non chiarisce che il valore indica se
    l'oggetto puo' raggiungere teoricamente almeno 15° dalla posizione attiva,
    indipendentemente dalla visibilita' nel mese.
  - Preferire una dicitura descrittiva come `Raggiunge ≥15°` /
    `Reaches ≥15°`, senza cambiare il calcolo.

- [ ] **VIS-015 - Form Equipment - etichette persistenti (`APERTA`)**
  - Aggiunta e modifica Telescopi, Oculari, Barlow, Filtri, Riduttori e Binocoli
    usano soltanto placeholder. Appena un campo contiene un valore non e' piu'
    visibile cosa rappresenta; anche i selettori di tipo o sistema non hanno
    un'etichetta propria.
  - Aggiungere label sempre visibili con unita' e indicazione obbligatorio /
    facoltativo, mantenendo gli asterischi coerenti con la validazione reale.
  - Applicare lo stesso criterio agli altri form Equipment che mostreranno lo
    stesso schema durante il controllo visuale.

- [ ] **VIS-016 - Telescopi - tipo e montatura in inglese (`APERTA`)**
  - La pagina e il form inglesi mostrano valori italiani come `rifrattore`,
    `rifrattore Petzval` ed `equatoriale`.
  - Il seed mescola note inglesi con categorie italiane, pur essendo dichiarato
    sorgente inglese dal generatore dei contenuti.
  - Normalizzare i valori integrati in una sorgente coerente e rigenerare le
    traduzioni; valori personalizzati o modificati dall'utente devono restare
    invariati.

- [ ] **VIS-017 - Cataloghi Equipment - sottotitoli inglesi (`APERTA`)**
  - `Models available to observing profiles` nei Telescopi e `Optical
    accessories available to observing profiles` in Oculari/Barlow e
    Filtri/Riduttori sono poco naturali; lo stesso primo testo compare nei
    Binocoli.
  - Preferire `Models available for observing profiles` e `Optical accessories
    available for observing profiles`.

- [ ] **VIS-018 - Oculari - unita' AFOV nelle schede (`APERTA`)**
  - Le pill mostrano `50 gradi` / `50 degrees`, mentre i form e gli altri angoli
    dell'app usano il simbolo `°`.
  - Mostrare `50°`, `68°` e valori analoghi: e' piu' compatto e coerente in
    entrambe le lingue.

- [ ] **VIS-019 - Form Equipment - decimali precompilati italiani (`APERTA`)**
  - Gli elenchi italiani localizzano correttamente `1,25″`, `2,25x` e `0,59x`,
    ma i form di modifica precompilano gli stessi valori come `1.25`, `2.25` e
    `0.59`.
  - Formattare i valori iniziali secondo il locale corrente, continuando ad
    accettare sia virgola sia punto in input come gia' fa il parser.

- [ ] **VIS-020 - Oculari - campi AFOV Fisso/Zoom (`APERTA`)**
  - Con tipo `Fisso` il form mostra `AFOV medio` e un intervallo facoltativo,
    anche se per un oculare a focale fissa serve un singolo AFOV.
  - Usare `AFOV (°)` e nascondere l'intervallo per `Fisso`; per `Zoom` mantenere
    AFOV medio e intervallo, indicando il formato atteso, per esempio `48-68`.

- [ ] **VIS-021 - Filtri e riduttori - contenuti inglesi (`APERTA`)**
  - Nell'elenco e nei form inglesi restano in italiano note dei filtri,
    compatibilita' descrittive, connessioni e note dei riduttori.
  - `filter_catalog_seed.csv` e `reducer_catalog_seed.csv` contengono testo
    italiano, ma `update_content_translations.py` li dichiara sorgenti inglesi;
    di conseguenza `en.json` non contiene le sezioni `equipment_filters` e
    `equipment_reducers`. Inoltre `compatible_models` non e' incluso tra i
    campi traducibili dei riduttori.
  - Correggere la lingua sorgente, includere tutti i campi descrittivi e
    rigenerare l'inglese per 48 filtri e 24 riduttori. Il cambio lingua live deve
    aggiornare questi payload di presentazione senza modificare dati utente,
    associazioni Equipment, recommendation o score.

- [ ] **VIS-022 - Filtri - classe non aggiornata al cambio lingua (`APERTA`)**
  - Nel form italiano del filtro CLS compare `Reduction of light pollution`,
    mentre la scheda mostra correttamente `Riduzione inquinamento luminoso`.
  - `filterClassOptions` e' esposta come proprieta' costante: dopo il cambio
    lingua il modello del menu conserva le label gia' materializzate.
  - Rendere reattive soltanto le label visibili, conservando invariati i codici
    canonici delle classi filtro.

- [ ] **VIS-023 - Riduttori - compatibilita' descrittiva persa (`APERTA`)**
  - Alcuni riduttori integrati, come Baader Alan Gee Mark II, hanno una
    compatibilita' testuale generica ma nessuna associazione esatta; il form
    mostra correttamente `0 selezionati` nella lista opzionale.
  - Il percorso di aggiornamento non reinvia pero' `compatible_models` e usa il
    default vuoto del repository: salvare anche una modifica non correlata puo'
    quindi cancellare la descrizione mostrata nella scheda.
  - Preservare il testo esistente quando non viene sostituito esplicitamente;
    le associazioni esatte selezionate devono continuare a usare gli ID
    normalizzati dei telescopi.

- [ ] **VIS-024 - Binocoli - ordinamento naturale (`APERTA`)**
  - L'ordinamento lessicografico del modello colloca Canon `8x20` dopo `18x50`
    e Celestron Nature DX ED `10x42` prima di `8x42`.
  - Applicare un ordinamento naturale stabile a marca e modello, mantenendo
    unite le serie commerciali e interpretando numericamente le specifiche;
    non ordinare globalmente solo per ingrandimento e diametro.

## Decisioni Aperte

- [ ] **VIS-007 - Localita' - paese dinamico in italiano (`DA DECIDERE`)**
  - `Ethiopia` arriva dai metadati dinamici della localita' e non dal catalogo
    delle traduzioni UI.
  - Se si decide di localizzarlo, tradurre soltanto la visualizzazione tramite
    codice paese; conservare i dati canonici e non reintrodurre un catalogo
    citta'.

- [ ] **VIS-013 - Dettaglio oggetto - dimensione massima (`DA DECIDERE`)**
  - `Dim. max` / `Max size` e' la massima dimensione angolare convertita in
    gradi e affianca gia' la dimensione catalogata in primi d'arco.
  - Valutare `Dim. angolare max` / `Maximum angular size` oppure la rimozione
    del dato duplicato dalla scheda, mantenendolo dove serve ai calcoli.

- [ ] **VIS-014 - Oggetti celesti - nomi costellazioni (`DA DECIDERE`)**
  - L'italiano mostra i nomi IAU latini (`Cepheus`, `Draco`, `Cygnus`), mentre
    i testi descrittivi usano `Cefeo`, `Dragone` e `Cigno`.
  - Scegliere se mantenere esplicitamente i nomi canonici oppure localizzare
    soltanto il display e i filtri, preservando il valore canonico interno.

## Verifiche Superate

- [x] **VIS-V01 (`VERIFICATA`)** - Layout, allineamenti e spaziature delle tre
  coppie italiano/inglese sono coerenti e senza sovrapposizioni.
- [x] **VIS-V02 (`VERIFICATA`)** - Coordinate e numeri usano correttamente
  virgola in italiano e punto in inglese.
- [x] **VIS-V03 (`VERIFICATA`)** - I valori del profilo sono coerenti con
  telescopio da 1500 mm e oculare zoom 8-24 mm: 62x-188x e pupilla 0,8-2,4 mm.
- [x] **VIS-V04 (`VERIFICATA`)** - Stati e azioni NASA Earthdata/OpenAQ sono
  completi e coerenti nelle due lingue.
- [x] **VIS-V05 (`VERIFICATA`)** - Il PNG italiano dei provider e' integro;
  l'apparente contenuto mancante era un artefatto dell'anteprima combinata.
- [x] **VIS-V06 (`VERIFICATA`)** - Elenco e dettaglio Oggetti celesti non
  mostrano sovrapposizioni, tagli o instabilita' nelle schermate fornite.
- [x] **VIS-V07 (`VERIFICATA`)** - Il filtro mensile passa coerentemente da
  228 a 182 oggetti; C1, indicato come non visibile nel mese, viene escluso.
- [x] **VIS-V08 (`VERIFICATA`)** - Per Addis Abeba C1 culmina teoricamente a
  circa 13,7°, quindi il valore negativo rispetto alla soglia di 15° e'
  corretto.
- [x] **VIS-V09 (`VERIFICATA`)** - La griglia Telescopi mostra 133 modelli in
  due colonne senza sovrapposizioni o testi tagliati nelle righe fornite.
- [x] **VIS-V10 (`VERIFICATA`)** - Marca, modello, tipo ottico, apertura intera
  positiva, focale intera positiva e montatura sono obbligatori sia in QML sia
  nel repository; soltanto le note sono facoltative e Salva resta disabilitato
  finche' i dati richiesti non sono validi.
- [x] **VIS-V11 (`VERIFICATA`)** - I modelli integrati sono modificabili ma non
  eliminabili; i modelli utente espongono Elimina e il repository applica la
  stessa protezione anche oltre la UI.
- [x] **VIS-V12 (`VERIFICATA`)** - Apertura, focale e rapporto focale seguono il
  formato locale: virgola decimale italiana e punto/raggruppamento inglese.
- [x] **VIS-V13 (`VERIFICATA`)** - I cataloghi affiancati mostrano correttamente
  134 oculari e 35 Barlow, senza sovrapposizioni, troncamenti o instabilita'
  nelle righe fornite; ricerca, contatori e scroll restano separati e leggibili.
- [x] **VIS-V14 (`VERIFICATA`)** - Per gli oculari sono obbligatori marca,
  modello, tipo, focale singola oppure intervallo focale Zoom e AFOV; intervallo
  AFOV, barilotto e note sono facoltativi. Per le Barlow sono obbligatori marca,
  modello e moltiplicatore maggiore di 1; barilotto e note sono facoltativi.
  QML e repository applicano le stesse regole di base.
- [x] **VIS-V15 (`VERIFICATA`)** - Oculari e Barlow integrati espongono
  `Modifica` ma non `Elimina`; le voci utente restano eliminabili e il
  repository blocca comunque la cancellazione delle voci integrate.
- [x] **VIS-V16 (`VERIFICATA`)** - Tipo `Fisso` / `Fixed`, note dei prodotti,
  dimensioni del barilotto e moltiplicatori risultano coerenti e localizzati
  nelle due lingue; marchi e nomi commerciali restano invariati.
- [x] **VIS-V17 (`VERIFICATA`)** - I cataloghi affiancati mostrano 48 filtri e
  24 riduttori senza sovrapposizioni o troncamenti nelle righe fornite. Le pill
  opzionali compaiono soltanto quando esiste un valore: per esempio CLS non
  mostra box vuoti e UHC-E omette correttamente la trasmissione assente.
- [x] **VIS-V18 (`VERIFICATA`)** - Per i filtri sono obbligatori marca, modello
  e classe; lunghezza d'onda, banda, trasmissione, apertura minima e note sono
  facoltative ma validate se presenti. Per i riduttori sono obbligatori marca,
  modello, fattore tra 0 e 1, sistema ottico e almeno un uso visuale/fotografico;
  connessione, backfocus, correzione campo, note e telescopi esatti sono
  facoltativi. Il form rende obbligatori gli stessi campi del repository;
  controller e repository validano anche gli opzionali quando compilati.
- [x] **VIS-V19 (`VERIFICATA`)** - Filtri e riduttori integrati sono
  modificabili ma non eliminabili; le voci utente espongono `Elimina` e il
  repository mantiene la protezione oltre la UI.
- [x] **VIS-V20 (`VERIFICATA`)** - Fattori, backfocus, bande e trasmissioni
  presenti nelle schede seguono il locale corrente. La griglia dei telescopi
  compatibili offre ricerca, selezione multipla, conteggio e scroll, mentre il
  repository valida e deduplica gli ID selezionati.
- [x] **VIS-V21 (`VERIFICATA`)** - Il catalogo mostra 94 binocoli in due colonne
  senza sovrapposizioni, troncamenti o pill vuote nelle righe fornite; ricerca,
  conteggio, specifica `ingrandimento×diametro` e badge `IS` sono coerenti nelle
  due lingue.
- [x] **VIS-V22 (`VERIFICATA`)** - Marca, modello, ingrandimento intero positivo
  e diametro obiettivo intero positivo sono obbligatori sia nel form sia nel
  controller/repository. La stabilizzazione e' un attributo booleano e Salva
  resta disabilitato finche' i quattro valori richiesti non sono validi.
- [x] **VIS-V23 (`VERIFICATA`)** - I binocoli integrati espongono `Modifica` ma
  non `Elimina`; le voci utente restano eliminabili e il repository impedisce
  comunque la cancellazione delle voci integrate.
- [x] **VIS-V24 (`VERIFICATA`)** - Marchi, nomi commerciali e sigle come `IS`
  restano invariati, mentre titoli, azioni, ricerca e attributo di
  stabilizzazione sono tradotti correttamente in italiano e inglese.

## Nota Per Screenshot Pubblici

- [ ] Prima di pubblicare immagini su GitHub, oscurare identificativi account,
  coordinate personali e qualsiasi altro dato non destinato alla diffusione.
