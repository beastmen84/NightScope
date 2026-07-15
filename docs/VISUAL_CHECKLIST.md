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

## Decisioni Aperte

- [ ] **VIS-007 - Localita' - paese dinamico in italiano (`DA DECIDERE`)**
  - `Ethiopia` arriva dai metadati dinamici della localita' e non dal catalogo
    delle traduzioni UI.
  - Se si decide di localizzarlo, tradurre soltanto la visualizzazione tramite
    codice paese; conservare i dati canonici e non reintrodurre un catalogo
    citta'.

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

## Nota Per Screenshot Pubblici

- [ ] Prima di pubblicare immagini su GitHub, oscurare identificativi account,
  coordinate personali e qualsiasi altro dato non destinato alla diffusione.

