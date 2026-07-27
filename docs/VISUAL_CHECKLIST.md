# NightScope - Visual Review Checklist

Aggiornato: 2026-07-27

Questo documento conserva i controlli visuali di release iniziati con la
sorgente `1.33.1` e i successivi passaggi per lingua e funzionalita'. Le
verifiche sugli artefatti `1.42.0` restano separate in `RELEASE_CHECKLIST.md` e
devono essere ripetute dopo la rigenerazione delle dist Windows e Linux.

## Verifica Sorgente Spagnolo 1.34.0

- [x] Manuale spagnolo renderizzato in Chromium a `1440x900` e `390x844`:
  nessun overflow orizzontale, selettore e persistenza ES/EN/ES corretti,
  navigazione alla sezione finale non coperta dall'header.
- [x] Cataloghi Qt IT/EN/ES completi: `1665` traduzioni finite e `0` unfinished
  per lingua; contenuti spagnoli completi per `7` sezioni, `821` elementi e
  `2038` campi.
- [x] Smoke QML separati italiano, inglese e spagnolo superati in runtime
  temporanei; suite completa `794 passed`.
- [ ] Eseguire la matrice visuale pagina-per-pagina in spagnolo su una nuova
  build Windows `1.34.1`. I controlli sorgente sopra non approvano da soli un
  nuovo artefatto pubblico.

## Verifica Sorgente Provider 1.34.1

- [x] Pagina Provider dati renderizzata direttamente in IT/EN/ES a `1400x900`
  e `774x900`: card affiancate o impilate senza sovrapposizioni.
- [x] `Autorizar aplicación` resta leggibile per intero nel pulsante spagnolo.
- [x] Guide UI e manuale includono profilo Earthdata completo, campi indicati
  come facoltativi, autorizzazione LAADS OPeNDAP, secondo test e flusso API Keys
  OpenAQ.
- [x] Cataloghi `1679/1679`, smoke QML IT/EN/ES e gate completo `817 passed`.
- [ ] Ripetere il controllo sulla dist Windows dopo la rigenerazione; la `dist`
  non e' stata modificata in questo passaggio.

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
| Log osservazioni - elenco | controllata | controllata | completata |
| Log osservazioni - aggiunta | controllata | controllata | completata |
| Log osservazioni - modifica | controllata | controllata | completata |
| Meteo - sintesi e qualita' cielo | controllata | controllata | completata |
| Meteo - AOD e OpenAQ | controllata | controllata | completata |
| Meteo - previsioni orarie | controllata | controllata | completata |
| Calendario - panoramica, filtri e timeline | controllata | controllata | completata |
| Calendario - Luna, opposizioni e congiunzioni | controllata | controllata | completata |
| Calendario - sciami meteorici e comete | controllata | controllata | completata |
| Calendario - eclissi e passaggi ISS | verificata da codice/test | verificata da codice/test | completata senza caso live |
| Home - sintesi osservativa e Sky Compass | controllata | controllata | completata |
| Home - piano, filtri e oggetti visibili | controllata | controllata | completata |
| Home - prossimi eventi | controllata | controllata | completata |
| Home - dettaglio Luna e cielo profondo | controllata | controllata | completata |

## Correzioni Risolte

- [x] **VIS-001 - Localita' - traduzione sorgente Windows (`RISOLTA`)**
  - In inglese `Windows specifies` e' una traduzione errata di `Windows precisa`.
  - Fino alla `1.35.0`, il testo previsto era `Posizione Windows precisa` /
    `Precise Windows location`; dalla `1.35.1` il controllo deve aspettarsi
    `Posizione di sistema` / `System location`, con descrizione specifica del
    provider Windows o GeoClue 2.
  - La stessa sorgente compare anche nel sottotitolo della pagina Meteo, quindi
    la correzione deve aggiornare entrambe le presentazioni.

- [x] **VIS-002 - Provider - nome NASA Earthdata (`RISOLTA`)**
  - Il marchio ufficiale deve restare `NASA Earthdata` anche in italiano,
    invece di `Earthdata NASA`.

- [x] **VIS-003 - Profili - riepilogo oculari e Barlow (`RISOLTA`)**
  - `Disponibili` / `Available` sembra descrivere tutto il profilo, ma il
    conteggio include intenzionalmente soltanto oculari e Barlow usati per le
    combinazioni di ingrandimento.
  - Rendere esplicito il significato, per esempio `Opzioni di ingrandimento` /
    `Magnification options`.

- [x] **VIS-004 - Profili - titolo capacita' inglese (`RISOLTA`)**
  - `Profile capacity` e' poco idiomatico; usare `Profile capabilities`.

- [x] **VIS-005 - Sidebar - stato serata inglese (`RISOLTA`)**
  - `To be monitored` e' comprensibile ma meccanico; valutare
    `Monitor conditions` mantenendo invariata la semantica dello stato.
  - Lo stesso concetto compare nel riepilogo Home e nel dettaglio oggetto come
    `Session to monitor`; uniformare badge, titolo e stato con una formulazione
    inglese naturale senza modificare il codice canonico `monitor`.

- [x] **VIS-006 - Profili - nome riduttore troncato (`RISOLTA`)**
  - Il nome `Celestron Reducer-Corrector...` viene eliso nella colonna dei
    riduttori.
  - Consentire al nome un massimo di due righe senza rendere instabile la
    griglia o allargare eccessivamente la scheda.

- [x] **VIS-008 - Oggetti celesti - nomi catalogo localizzati (`RISOLTA`)**
  - La sorgente `catalogue_objects_seed.csv` e' italiana, ma il generatore la
    dichiara inglese. In inglese restano quindi soprannomi come `Nebulosa Iris`
    e `Galassia Fuochi d'Artificio`; in italiano 59 nomi NGC/IC perdono lo
    spazio del designatore, per esempio `NGC188` e `IC342`.
  - Correggere la lingua sorgente e rigenerare i contenuti preservando sempre
    i designatori canonici; tradurre soltanto il soprannome descrittivo.
  - Verificare anche ricerca, descrizione breve e tutti i 219 oggetti seed, non
    soltanto le righe Caldwell mostrate negli screenshot.
  - La Home conferma la causa: `en.json` non contiene la sezione
    `catalogue_objects`, quindi `_catalogue_details()` ricade sul testo italiano
    per nome e descrizione. Nell'elenco inglese restano `Galassia Ago d'Argento`
    e `Galassia Balena`; nel dettaglio C3 la nota inglese termina con
    `Galassia spirale nella costellazione di Dragone`. In italiano lo stesso
    override produce `NGC4236` senza lo spazio canonico.

- [x] **VIS-009 - Dettaglio oggetto - credito immagine inglese (`RISOLTA`)**
  - Il testo `HiPS a colori e ritaglio: CDS` resta italiano nella pagina
    inglese, sia dal Catalogo sia aprendo lo stesso oggetto dalla Home.
  - Conservare invariati survey, enti e licenza, localizzando soltanto la parte
    descrittiva dell'attribuzione.

- [x] **VIS-010 - Dettaglio oggetto - nota osservativa inglese (`RISOLTA`)**
  - La frase di C1 `Use a medium shot...; increases moderately...` usa un
    termine fotografico errato e una forma verbale non corretta.
  - Testo coerente con il dominio: `Use a medium field under dark skies;
    increase magnification moderately to separate the many faint stars from
    the background.`
  - Controllare le altre note osservative inglesi generate per individuare
    traduzioni automatiche analoghe.

- [x] **VIS-011 - Dettaglio oggetto - formato decimale inglese (`RISOLTA`)**
  - Nel dettaglio inglese C1 la dimensione massima appare come `0,233°`, mentre
    nell'elenco inglese e' correttamente `0.233°`.
  - Assicurare che i label numerici preformattati seguano il nuovo locale dopo
    il cambio lingua live oppure derivarli dal valore numerico in presentazione.

- [x] **VIS-012 - Oggetti celesti - soglia geometrica (`RISOLTA`)**
  - `Utile (≥15°)` / `Useful (≥15°)` non chiarisce che il valore indica se
    l'oggetto puo' raggiungere teoricamente almeno 15° dalla posizione attiva,
    indipendentemente dalla visibilita' nel mese.
  - Preferire una dicitura descrittiva come `Raggiunge ≥15°` /
    `Reaches ≥15°`, senza cambiare il calcolo.

- [x] **VIS-015 - Form Equipment - etichette persistenti (`RISOLTA`)**
  - Aggiunta e modifica Telescopi, Oculari, Barlow, Filtri, Riduttori e Binocoli
    usano soltanto placeholder. Appena un campo contiene un valore non e' piu'
    visibile cosa rappresenta; anche i selettori di tipo o sistema non hanno
    un'etichetta propria.
  - Aggiungere label sempre visibili con unita' e indicazione obbligatorio /
    facoltativo, mantenendo gli asterischi coerenti con la validazione reale.
  - Applicare lo stesso criterio agli altri form Equipment che mostreranno lo
    stesso schema durante il controllo visuale.

- [x] **VIS-016 - Telescopi - tipo e montatura in inglese (`RISOLTA`)**
  - La pagina e il form inglesi mostrano valori italiani come `rifrattore`,
    `rifrattore Petzval` ed `equatoriale`.
  - Il seed mescola note inglesi con categorie italiane, pur essendo dichiarato
    sorgente inglese dal generatore dei contenuti.
  - Normalizzare i valori integrati in una sorgente coerente e rigenerare le
    traduzioni; valori personalizzati o modificati dall'utente devono restare
    invariati.

- [x] **VIS-017 - Cataloghi Equipment - sottotitoli inglesi (`RISOLTA`)**
  - `Models available to observing profiles` nei Telescopi e `Optical
    accessories available to observing profiles` in Oculari/Barlow e
    Filtri/Riduttori sono poco naturali; lo stesso primo testo compare nei
    Binocoli.
  - Preferire `Models available for observing profiles` e `Optical accessories
    available for observing profiles`.

- [x] **VIS-018 - Oculari - unita' AFOV nelle schede (`RISOLTA`)**
  - Le pill mostrano `50 gradi` / `50 degrees`, mentre i form e gli altri angoli
    dell'app usano il simbolo `°`.
  - Mostrare `50°`, `68°` e valori analoghi: e' piu' compatto e coerente in
    entrambe le lingue.

- [x] **VIS-019 - Form Equipment - decimali precompilati italiani (`RISOLTA`)**
  - Gli elenchi italiani localizzano correttamente `1,25″`, `2,25x` e `0,59x`,
    ma i form di modifica precompilano gli stessi valori come `1.25`, `2.25` e
    `0.59`.
  - Formattare i valori iniziali secondo il locale corrente, continuando ad
    accettare sia virgola sia punto in input come gia' fa il parser.

- [x] **VIS-020 - Oculari - campi AFOV Fisso/Zoom (`RISOLTA`)**
  - Con tipo `Fisso` il form mostra `AFOV medio` e un intervallo facoltativo,
    anche se per un oculare a focale fissa serve un singolo AFOV.
  - Usare `AFOV (°)` e nascondere l'intervallo per `Fisso`; per `Zoom` mantenere
    AFOV medio e intervallo, indicando il formato atteso, per esempio `48-68`.

- [x] **VIS-021 - Filtri e riduttori - contenuti inglesi (`RISOLTA`)**
  - Nell'elenco e nei form inglesi restano in italiano note dei filtri,
    connessioni e note dei riduttori.
  - `filter_catalog_seed.csv` e `reducer_catalog_seed.csv` contengono testo
    italiano, ma `update_content_translations.py` li dichiara sorgenti inglesi;
    di conseguenza `en.json` non contiene le sezioni `equipment_filters` e
    `equipment_reducers`.
  - Correggere la lingua sorgente, includere connessioni e note e
    rigenerare l'inglese per 48 filtri e 24 riduttori. Il cambio lingua live deve
    aggiornare questi payload di presentazione senza modificare dati utente,
    associazioni Equipment, recommendation o score.

- [x] **VIS-022 - Filtri - classe non aggiornata al cambio lingua (`RISOLTA`)**
  - Nel form italiano del filtro CLS compare `Reduction of light pollution`,
    mentre la scheda mostra correttamente `Riduzione inquinamento luminoso`.
  - `filterClassOptions` e' esposta come proprieta' costante: dopo il cambio
    lingua il modello del menu conserva le label gia' materializzate.
  - Rendere reattive soltanto le label visibili, conservando invariati i codici
    canonici delle classi filtro.

- [x] **VIS-023 - Riduttori - compatibilita' esatta fail-closed (`SUPERATA`)**
  - La compatibilita' descrittiva generica e' stata ritirata: non e'
    sufficientemente certa per guidare calcoli visuali o fotografici.
  - Il form usa soltanto associazioni esatte a ID normalizzati dei telescopi,
    mostra per primi quelli del profilo attivo e include i modelli creati
    dall'utente.
  - Con zero associazioni il riduttore resta visibile nel catalogo, ma la UI lo
    segnala come non configurato e i due motori lo escludono.

- [x] **VIS-024 - Binocoli - ordinamento naturale (`RISOLTA`)**
  - L'ordinamento lessicografico del modello colloca Canon `8x20` dopo `18x50`
    e Celestron Nature DX ED `10x42` prima di `8x42`.
  - Applicare un ordinamento naturale stabile a marca e modello, mantenendo
    unite le serie commerciali e interpretando numericamente le specifiche;
    non ordinare globalmente solo per ingrandimento e diametro.

- [x] **VIS-025 - Log osservazioni - intestazione Voto disallineata (`RISOLTA`)**
  - Nell'elenco italiano e inglese `Voto` / `Rating` non si trova sopra il
    valore `4/5`, ma molto piu' a destra verso i pulsanti di azione.
  - Intestazione e delegato dichiarano uno spazio azioni di `142 px`; nella
    riga, pero', le dimensioni implicite dei pulsanti `Modifica` e `Elimina`
    allargano quel blocco, mentre lo spacer dell'intestazione resta invariato.
  - Usare una geometria condivisa e stabile per le colonne, riservando in
    intestazione la larghezza effettiva delle azioni e mantenendo il voto
    centrato sopra il relativo valore in entrambe le lingue.

- [x] **VIS-026 - Log osservazioni - messaggi inglesi (`RISOLTA`)**
  - La validazione dell'oggetto usa `Indicates the observed object.`: deve
    essere l'imperativo `Specify the observed object.`.
  - Il rifiuto di una data futura usa `The Observations Log...`, incoerente con
    il nome pagina `Observation Log`; mantenere il nome singolare e una frase
    naturale, per esempio `The Observation Log only accepts past observations.`
  - Il messaggio dopo la modifica `Updated observation.` e' meno naturale di
    `Observation updated.`; uniformare anche questo stato alle altre conferme.

- [x] **VIS-027 - Meteo - unita' radianza VIIRS (`RISOLTA`)**
  - Scheda e riga sorgente mostrano `nW/cm² sr`, notazione ambigua perche' non
    rende esplicito che anche lo steradiante e' al denominatore.
  - La specifica NASA VNP46A3 dichiara `nWatts/(cm^2 sr)`, equivalente a
    `nW·cm⁻²·sr⁻¹`; usare una forma compatta e inequivocabile come
    `nW/(cm²·sr)` in tutte le presentazioni italiano/inglese.
  - Riferimento: `https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A3/`.

- [x] **VIS-028 - Meteo - terminologia inglese (`RISOLTA`)**
  - Il dettaglio orario usa `Cloudiness`, mentre sintesi e grafico usano il
    termine piu' preciso `Cloud cover`; uniformare la pagina su `Cloud cover`.
  - La classe atmosferica `Velata` e' tradotta letteralmente come `Veiled`,
    poco naturale per aerosol e particolato: usare `Hazy`. Nella stessa scala,
    `High aerosols` va reso come `High aerosol load`.
  - Mantenere invariati codici, soglie AOD/OpenAQ e logica NSOM: sono correzioni
    delle sole label di presentazione.

- [x] **VIS-029 - Calendario - terminologia inglese (`RISOLTA`)**
  - `Maximum approach` non e' il termine astronomico naturale per una
    congiunzione; usare `Closest approach`.
  - I titoli `Maximum Southern Delta Aquariids` e `Maximum Perseids` vanno
    formulati come `Southern Delta Aquariids peak` e `Perseids peak`.
    Analogamente, `Night close to {date}` va reso `Night around {date}`.
  - Alcuni consigli sono traduzioni troppo letterali: `The dark sky counts
    more than the telescope`, `Observe for a long time with a reclining chair`,
    `more chances to wait for stable seeing` e `before fine detailing` devono
    diventare frasi osservative idiomatiche, senza cambiare la raccomandazione.
  - Ricontrollare nello stesso passaggio tutte le stringhe inglesi prodotte da
    `CalendarOverviewService`, non soltanto i casi visibili negli screenshot.

- [x] **VIS-030 - Calendario - angoli e composizione delle finestre (`RISOLTA`)**
  - Congiunzioni, opposizioni e fasi lunari mostrano `gradi` / `degrees`, mentre
    ISS e comete usano gia' `°`. Uniformare gli angoli del Calendario al simbolo
    `°`, mantenendo virgola italiana e punto inglese per i decimali.
  - La label riutilizzabile `Intorno alle` / `Around` viene inserita con
    l'iniziale maiuscola dentro una frase (`finestra locale Intorno alle...`).
    Separare il testo autonomo dalla forma incorporata oppure comporre l'intera
    frase, cosi' da ottenere `intorno alle` / `around` nel contesto corrente.

- [x] **VIS-031 - Calendario - inglese delle eclissi (`RISOLTA`)**
  - Il titolo e' composto come `Lunar Eclipse {kind}` con `partial`, `total` o
    `penumbral` interpolato in coda, producendo forme come `Lunar Eclipse
    partial`. Usare l'ordine naturale `Partial lunar eclipse`, `Total lunar
    eclipse` e `Penumbral lunar eclipse` senza affidarsi alla capitalizzazione
    accidentale del frammento.
  - Anche `Maximum of the eclipse` e `complete schedules of the phases` sono
    meccanici; preferire `Eclipse maximum` e `full phase timings` nelle label e
    nei consigli. Il ramo non era presente negli screenshot, ma il difetto e'
    confermato nel catalogo di traduzione.

- [x] **VIS-032 - Calendario - affidabilita' cometaria (`RISOLTA`)**
  - `Affidabilita' della luminosita': Indicativa` / `Brightness estimate
    confidence: Approximate` accosta una label di confidenza a un qualificatore
    che descrive invece il tipo di stima; inoltre la magnitudine e' gia'
    presentata come intervallo approssimativo.
  - Rendere il dato semanticamente esplicito, preferibilmente
    `Affidabilita' della stima: Bassa` / `Estimate confidence: Low`, mantenendo
    invariati modello fotometrico, intervallo di magnitudine e soglie della
    finestra cometaria.

- [x] **VIS-033 - Home - metrica Distanza/Catalogo (`RISOLTA`)**
  - Nel dettaglio osservativo di C3 la scheda mostra `Distanza` / `Distance`,
    ma il valore e' `Catalogo Caldwell` / `Catalog Caldwell`.
  - Non e' un valore runtime errato: per gli oggetti deep-sky
    `SkyfieldAstronomyEngine._catalogue_details()` conserva intenzionalmente il
    catalogo nel campo legacy `distance`, mentre `ObjectDetailPage.qml` assegna
    sempre la label distanza a ogni dettaglio non aperto dal Catalogo.
  - Separare la presentazione per tipologia: mostrare `Catalogo: Caldwell` per
    il cielo profondo quando non esiste una distanza fisica, e mantenere
    `Distanza` soltanto per corpi che trasportano realmente quella misura. Non
    inventare una distanza assente dal dataset.

- [x] **VIS-034 - Home - terminologia e testi operativi (`RISOLTA`)**
  - Correggere le forme inglesi troppo letterali: `It rises 07:04` /
    `It sets 19:59`, `18:48 evening`, `Stay low`, `a promising observation
    window is foreseen`, `Bortle Sky 6`, `Difficulty: Average` e `Colored
    (yellow)`. Usare rispettivamente forme come `Rises at`, `Sets at`, un orario
    senza suffisso ridondante, `Remains low`, testo meteo diretto, `Bortle 6
    sky`, `Difficulty: Medium` e `Color filter (yellow)`.
  - In italiano sostituire gli anglicismi visibili `Nessun target osservabile`
    e `target penalizzato` con `oggetto`, preservando i termini tecnici davvero
    adottati in astronomia, come `seeing`.
  - Rileggere nello stesso passaggio le motivazioni Equipment inglesi, per
    esempio `readable lunar detail`, senza cambiare selezione di telescopio,
    oculare, filtro o riduttore.

- [x] **VIS-035 - Home - unita' angolari (`RISOLTA`)**
  - Stato, metriche, valutazione osservativa e configurazioni mostrano
    `gradi` / `degrees` (`28 gradi`, `0.96 degrees`, `Stay low (15 degrees)`),
    mentre Calendario e altri dati tecnici stanno convergendo sul simbolo `°`.
  - Usare `°` per altezza, azimut, soglie e campo reale in entrambe le lingue,
    mantenendo la localizzazione dei decimali e senza modificare i valori
    numerici o le soglie geometriche.

- [x] **VIS-036 - Home - intestazioni Oggetti visibili (`RISOLTA`)**
  - Le intestazioni `Oggetto`, `Tipo`, `Finestra`, `Direzione` e `Difficolta'`
    risultano spostate a sinistra rispetto ai valori delle rispettive colonne;
    il disallineamento diventa particolarmente evidente da `Tipo` in poi.
  - Header e righe usano due `RowLayout` indipendenti. Il delegate
    `HomeVisibleTargetRow` aggiunge inoltre margini laterali e la barra colore,
    quindi la duplicazione delle larghezze nominali non garantisce le stesse
    coordinate effettive.
  - Definire un solo contratto condiviso per margini, barra e larghezze delle
    cinque colonne, mantenendo lo spazio gia' assegnato a Nome e Difficolta'.
    Verificare l'allineamento sia in italiano sia in inglese; la vista compatta,
    che non mostra l'header tabellare, deve restare invariata.

- [x] **VIS-037 - Provider dati - campi Earthdata troppo presto su due righe (`RISOLTA`)**
  - La card portava la password sotto il nome utente gia' sotto `720` px,
    nonostante due campi utilizzabili potessero ancora stare affiancati.
  - La soglia interna e' ora `620` px; il fallback a una colonna resta attivo
    quando lo spazio effettivo della card diventa insufficiente.

- [x] **VIS-038 - Dettaglio ISS - riga Pass details incompleta (`RISOLTA`)**
  - Nel layout desktop le tre card del corpo erano disposte in una griglia a
    due colonne; la terza occupava solo la colonna sinistra e lasciava vuota la
    meta' destra della pagina.
  - La card dei dettagli estende ora la propria colonna su tutta la griglia
    larga e torna automaticamente a una sola colonna sotto `1160` px.

## Decisioni Risolte

- [x] **VIS-007 - Localita' - paese dinamico in italiano (`RISOLTA`)**
  - `Ethiopia` arriva dai metadati dinamici della localita' e non dal catalogo
    delle traduzioni UI.
  - Se si decide di localizzarlo, tradurre soltanto la visualizzazione tramite
    codice paese; conservare i dati canonici e non reintrodurre un catalogo
    citta'.
  - Decisione: mantenere i nomi paese forniti dai provider nel formato
    canonico. La timezone IANA derivata dalle coordinate e' il dato operativo;
    non viene reintrodotto il catalogo citta'.

- [x] **VIS-013 - Dettaglio oggetto - dimensione massima (`RISOLTA`)**
  - `Dim. max` / `Max size` e' la massima dimensione angolare convertita in
    gradi e affianca gia' la dimensione catalogata in primi d'arco.
  - Valutare `Dim. angolare max` / `Maximum angular size` oppure la rimozione
    del dato duplicato dalla scheda, mantenendolo dove serve ai calcoli.
  - Decisione: mantenere il dato con label esplicita `Dimensione angolare
    massima` / `Maximum angular size`.

- [x] **VIS-014 - Oggetti celesti - nomi costellazioni (`RISOLTA`)**
  - L'italiano mostra i nomi IAU latini (`Cepheus`, `Draco`, `Cygnus`), mentre
    i testi descrittivi usano `Cefeo`, `Dragone` e `Cigno`.
  - Scegliere se mantenere esplicitamente i nomi canonici oppure localizzare
    soltanto il display e i filtri, preservando il valore canonico interno.
  - Decisione: localizzare elenco, dettaglio e filtri; i valori IAU canonici
    restano invariati internamente.

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
  AFOV e note sono facoltativi. Per le Barlow sono obbligatori marca, modello e
  moltiplicatore maggiore di 1; le note sono facoltative. Il barilotto non e'
  raccolto perche' manca la controparte meccanica del telescopio. QML e
  repository applicano le stesse regole di base.
- [x] **VIS-V15 (`VERIFICATA`)** - Oculari e Barlow integrati espongono
  `Modifica` ma non `Elimina`; le voci utente restano eliminabili e il
  repository blocca comunque la cancellazione delle voci integrate.
- [x] **VIS-V16 (`VERIFICATA`)** - Tipo `Fisso` / `Fixed`, note dei prodotti,
  moltiplicatori e label delle alternative Barlow equivalenti risultano
  coerenti e localizzati; marchi e nomi commerciali restano invariati.
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
- [x] **VIS-V25 (`VERIFICATA`)** - Elenco e dialoghi di aggiunta/modifica del
  Log sono leggibili e privi di sovrapposizioni o troncamenti nelle schermate
  fornite, salvo il disallineamento dell'intestazione registrato in VIS-025.
  Etichette persistenti e aree di input restano chiare anche a campi compilati.
- [x] **VIS-V26 (`VERIFICATA`)** - Data, ora, oggetto e valutazione sono i dati
  obbligatori; luogo, telescopio, oculare e note sono facoltativi. Il servizio
  accetta data e ora soltanto nei formati univoci `AAAA-MM-GG` e `HH:MM`, limita
  il voto a 1-5 e rifiuta osservazioni future; i test mirati confermano le
  stesse regole oltre la UI.
- [x] **VIS-V27 (`VERIFICATA`)** - Date e medie dell'elenco e dei riepiloghi
  seguono correttamente il locale: `15/07/2026`, `4,0/5` in italiano e
  `07/15/2026`, `4.0/5` in inglese. Testi registrati dall'utente come `Luna` e
  `prova` restano intenzionalmente invariati al cambio lingua.
- [x] **VIS-V28 (`VERIFICATA`)** - Persistenza e read model coprono aggiunta,
  modifica, eliminazione confermata, ordinamento dal piu' recente, ricerca,
  filtro per voto e riepiloghi senza un limite artificiale ai risultati. La
  suite mirata `test_observation_log.py` passa integralmente: `7 passed`.
- [x] **VIS-V29 (`VERIFICATA`)** - Sintesi, qualita' cielo, AOD, OpenAQ,
  copertura nuvolosa e dettaglio orario sono leggibili nelle due lingue senza
  sovrapposizioni o troncamenti. Lo scroll verticale e la lista oraria
  orizzontale conservano dimensioni stabili nelle schermate fornite.
- [x] **VIS-V30 (`VERIFICATA`)** - La sintesi usa le dodici ore della notte
  osservativa evidenziate da `19:00` a `06:00`: i valori visibili producono
  correttamente circa `45%` di nuvolosita' media. La finestra `23:00-04:00`
  della sidebar e' invece il sottointervallo operativo consigliato e non viene
  confusa con l'intera notte usata per le medie.
- [x] **VIS-V31 (`VERIFICATA`)** - I dati reali sono semanticamente coerenti:
  radianza VIIRS `24,79` con 14 osservazioni ricade nella soglia Bortle 6;
  l'AOD `0,656` e' segnalato come misura di tre giorni, mentre OpenAQ mostra
  esplicitamente che la lettura di 54 giorni e' storica e non recente.
- [x] **VIS-V32 (`VERIFICATA`)** - Decimali e date seguono il locale in tutti i
  blocchi: virgola e `GG/MM/AAAA` in italiano, punto e `MM/DD/YYYY` in inglese.
  Orari, timezone IANA, nomi provider, codici prodotto e QA restano invariati.
- [x] **VIS-V33 (`VERIFICATA`)** - Selezione della notte, cache VIIRS, qualita'
  AOD e stati OpenAQ superano le suite mirate
  `test_observing_night_weather.py`, `test_viirs_cache_policy.py`,
  `test_nasa_aod_provider.py` e `test_openaq_atmosphere.py`: `67 passed`.
- [x] **VIS-V34 (`VERIFICATA`)** - Panoramica, filtri e timeline del Calendario
  sono leggibili nelle due lingue, senza sovrapposizioni o troncamenti nei casi
  forniti. La griglia passa correttamente a due colonne nello spazio disponibile
  e le schede mantengono una geometria stabile.
- [x] **VIS-V35 (`VERIFICATA`)** - Il totale di `83` eventi coincide con la
  somma delle categorie mostrate: `49 + 5 + 11 + 4 + 10 + 2 + 0 + 2`. Date,
  intervalli e decimali seguono il locale, mentre i tre orizzonti restano
  distinti: annuale, ISS a breve termine e finestre cometarie.
- [x] **VIS-V36 (`VERIFICATA`)** - I dettagli distinguono correttamente
  l'istante astronomico dalla finestra osservativa locale. Congiunzione solare,
  fase lunare diurna, opposizione e congiunzione planetaria mostrano stati,
  spiegazioni e azioni coerenti; la congiunzione solare resta esplicitamente un
  evento informativo non osservabile in sicurezza.
- [x] **VIS-V37 (`VERIFICATA`)** - Le raccomandazioni usano il profilo Equipment
  per gli eventi catalogati, aprono gli oggetti coinvolti e non trasformano
  comete o passaggi ISS in `CatalogueObject`. La cometa resta una finestra
  transitoria con sorgente, aggiornamento, intervallo di magnitudine, geometria
  locale e numero stimato di notti utili.
- [x] **VIS-V38 (`VERIFICATA`)** - I template non disponibili come caso live
  sono comunque completi: le eclissi distinguono massimo visibile, luce diurna
  e Luna sotto l'orizzonte; i passaggi ISS espongono ingresso/uscita,
  culminazione, altezza, direzioni, durata, illuminazione e freschezza orbitale.
  Lo zero ISS per la posizione e la finestra correnti e' quindi uno stato valido,
  non un tipo evento mancante.
- [x] **VIS-V39 (`VERIFICATA`)** - Le suite mirate
  `test_calendar_overview.py`, `test_iss_passes.py` e
  `test_comet_windows.py` passano integralmente (`19 passed`); anche
  `test_translations.py` passa integralmente (`15 passed`).
- [x] **VIS-V40 (`VERIFICATA`)** - La Home configurata e' leggibile e stabile
  in entrambe le lingue: sessione, condizioni planetarie, Meteo, Luna, cielo
  profondo e Sky Compass non mostrano sovrapposizioni o troncamenti strutturali.
  Stato `monitor`, finestra `23:00-04:00` e rischio precipitazioni restano
  coerenti anche nella sidebar e nel piano della notte.
- [x] **VIS-V41 (`VERIFICATA`)** - `Sky Compass` segnala correttamente che non
  esiste un target osservabile nell'istante corrente, mentre i `188` oggetti
  sottostanti descrivono finestre future nella notte. Le due sezioni non sono in
  contraddizione e il toggle `Solo suggeriti ora` resta disabilitato quando la
  proiezione live non contiene target.
- [x] **VIS-V42 (`VERIFICATA`)** - I conteggi e i filtri della lista coincidono:
  `4` pianeti + `184` oggetti cielo profondo = `188` totali. Le larghezze delle
  righe mantengono leggibili Nome e Difficolta' e non troncano piu' `Non adatto
  a occhio nudo`; resta pero' da riallineare l'header ai valori come registrato
  in VIS-036.
- [x] **VIS-V43 (`VERIFICATA`)** - Home mostra gli otto prossimi eventi in
  ordine cronologico. Titoli e intervalli cometari occupano al massimo due
  righe senza ridimensionare le schede; l'azione `Vedi tutti` apre la stessa
  proiezione score-free del Calendario.
- [x] **VIS-V44 (`VERIFICATA`)** - I dettagli Luna e C3 distinguono stato
  corrente, finestra utile, descrizione, curiosita', configurazione Equipment e
  valutazione osservativa. La Luna mostra distanza reale e ciclo lunare; C3
  mostra il riduttore fotografico compatibile e la difficolta', mentre la
  configurazione lunare espone i filtri. Nessuno dei due dettagli mostra score
  o fattori NSOM grezzi. Il rilievo Distanza/Catalogo e' isolato in VIS-033.
- [x] **VIS-V45 (`VERIFICATA`)** - I valori Equipment visibili sono coerenti
  con il profilo: focale telescopio `1500 mm` e oculare `16 mm` producono circa
  `94x`, pupilla `1,6 mm` e campo `0,64°`; a `24 mm` producono circa `62x`,
  pupilla `2,4 mm` e campo `0,96°`.
- [x] **VIS-V46 (`VERIFICATA`)** - Le suite mirate per Home, dettaglio
  osservativo, piano notturno, ranking e Sky Compass passano integralmente:
  `95 passed` nei nove file `test_home_*`, `test_observing_object_detail.py` e
  `test_sky_compass_*` eseguiti in questo passaggio.
- [x] **VIS-V47 (`VERIFICATA`)** - La card `Piano fotografico` e' stata
  renderizzata nativamente su Windows con il profilo reale in modalita' normale
  e Red Night Vision. M31 mostra il piano foto, il reducer e l'avviso
  regione/mosaico; Saturno mostra Barlow, durata clip, FPS e frame senza tagli
  o sovrapposizioni. La scena rossa resta monocromatica, con verde massimo 16,
  blu massimo 15 e zero pixel oltre soglia. Lo splash del primo avvio conserva
  il bordo arrotondato visibile e ha alpha `0` nei quattro pixel d'angolo,
  mentre superficie e centro restano opachi.

## Verifica Delle Correzioni 1.33.1

- Tutti i rilievi `VIS-001` - `VIS-036` risultano `RISOLTA` nella sorgente.
- Suite mirata localizzazione, Equipment, Home e Calendario: `113 passed`.
- Gate completo: `788 passed`, `613 warnings` note Skyfield/NumPy e `7
  subtests`; `pip check`, Ruff, `compileall`, smoke backend e smoke QML passano.
- Cataloghi Qt IT/EN: `1665` traduzioni finite e `0` unfinished per lingua.
- `qmllint`: 30 file, exit `0`; smoke QML separati italiano/inglese passati con
  runtime temporanei.
- La verifica visuale dell'artefatto Windows resta aperta fino alla prossima
  rigenerazione della dist.

## Nota Per Screenshot Pubblici

- [ ] Prima di pubblicare immagini su GitHub, oscurare identificativi account,
  coordinate personali e qualsiasi altro dato non destinato alla diffusione.
