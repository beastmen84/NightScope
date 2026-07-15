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
  - Aggiunta e modifica Telescopi usano soltanto placeholder. Appena un campo
    contiene un valore non e' piu' visibile se rappresenta marca, modello, tipo
    ottico, apertura, focale, montatura o note.
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

- [ ] **VIS-017 - Telescopi - sottotitolo inglese (`APERTA`)**
  - `Models available to observing profiles` e' poco naturale.
  - Preferire `Models available for observing profiles`.

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

## Nota Per Screenshot Pubblici

- [ ] Prima di pubblicare immagini su GitHub, oscurare identificativi account,
  coordinate personali e qualsiasi altro dato non destinato alla diffusione.
