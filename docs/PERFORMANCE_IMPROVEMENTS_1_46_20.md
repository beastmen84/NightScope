# NightScope 1.46.20 - Reattività dei ricalcoli

Data: 2026-09-07. Baseline: commit `e947838`, sorgente 1.46.19.
Intervento autorizzato dopo la review delle prime ottimizzazioni, con priorità
alla conservazione dei risultati. Solo sorgente: nessuna nuova distribuzione,
modifica dei dati personali, push, tag o pubblicazione.

## Modifiche e garanzie

- Gli errori di visibilità mensile sono distinti da una risposta valida vuota.
  I getter non riprovano continuamente; selezionare esplicitamente lo stesso
  mese, oppure tornare al mese dopo averne scelto un altro, consente il recupero.
- Profilo e ricalcoli senza località non eseguono più un ordinamento NSOM
  intermedio destinato a essere sostituito dopo il contesto d'inquinamento.
  Conservato l'ordinamento finale, inclusi i casi senza meteo.
- La preparazione di attrezzatura, candidati, NSOM, miglior oggetto, Planner e
  bussola passa a un worker per meteo, profilo, provider ambientali, VIIRS e mese.
  Le 19 routine di calcolo esistenti sono condivise, non riscritte con formule
  alternative. Il controller diretto mantiene il percorso sincrono; l'avvio
  applicativo abilita il coordinamento asincrono.
- Il coordinatore cattura gli input sul thread Qt, mantiene un solo worker
  attivo e accorpa le richieste pendenti per tipo. Generazione e firma del
  contesto proteggono località, notte, mese, lingua, profilo e sorgenti correnti.
  Nessun worker pubblica direttamente su QObject, modelli o repository.
- Il mese precedente rimane selezionato fino a geometria e preparazione complete.
  Gli errori conservano gli output precedenti e completano la gestione dei
  provider, compresa la riprogrammazione meteo; non selezionano un mese fallito.
- Le richieste astronomiche sono limitate a un task attivo e all'ultimo pendente.
  La geometria mancante nei getter dei dettagli viene richiesta separatamente,
  senza attendere il lock astronomico sul thread Qt. Le richieste sono deduplicate,
  la coda dei dettagli è limitata a 32 e le risposte superate vengono ignorate.
- La pubblicazione adotta la direzione iniziale già calcolata della bussola;
  le cinque conferme per i successivi piccoli cambi di direzione restano intatte.
  La chiusura annulla le pubblicazioni pendenti; non interrompe forzatamente
  una chiamata Skyfield già in corso.

Le copie separano i contenitori esterni. I DTO congelati e i servizi senza stato
mutabile per richiesta sono condivisi in sola lettura. Non si tratta di una
duplicazione profonda dell'intero catalogo. I controlli includono l'assenza di
mutazioni degli input durante il calcolo.

## Confronto con il commit precedente

La sonda offline carica nello stesso processo i metodi originali da `e947838`,
ripristina gli stessi input prima di ciascun percorso e confronta tutti i campi
pubblicabili, geometria lunare, raccomandazioni, attrezzatura, punteggi, Planner,
bussola e selezione mensile. Database copiato in un runtime temporaneo, Roma,
notte del 7 settembre 2026, meteo fissato, Newton 150/750, quattro oculari e Barlow.

Entrambi i cataloghi, predefinito e interamente abilitato, danno **zero campi
diversi** nei quattro aggiornamenti. Il caso esteso contiene 4.466 bersagli,
4.457 oggetti deep sky e 4.462 candidati bussola; punteggio meteo 94.

| Aggiornamento, catalogo esteso | Prima, sincrono | Nuovo, totale | Ritorno della richiesta | Massimo intervallo eventi Qt |
| --- | ---: | ---: | ---: | ---: |
| Meteo | 7,33 s | 9,22 s | 4,37 ms | 609 ms |
| Profilo | 5,88 s | 5,75 s | 0,32 ms | 496 ms |
| Condizioni | 2,09 s | 2,52 s | 0,12 ms | 387 ms |
| Mese | 11,69 s | 13,71 s | 12,97 ms | 520 ms |

Sono singole coppie diagnostiche, non medie statistiche o misure sul PC segnalato.
Gli eventi Qt continuano durante il calcolo, ma non si promettono frame regolari:
Python/GIL, allocazioni, garbage collection e pubblicazione hanno ancora costi.
Alcuni tempi totali aumentano. Il risultato principale è rimuovere il calcolo
continuo dal thread dell'interfaccia, non dichiarare una riduzione generalizzata
di CPU o RAM. La sonda conserva stati di confronto e serializza payload: la sua
memoria non rappresenta il normale consumo applicativo.

Nel catalogo predefinito il cambio mese richiede circa 2,50 s prima e 2,53 s dopo,
con ritorno in 13,8 ms e intervallo massimo Qt di 146 ms. Gli altri tre percorsi
completano in circa 0,08–0,16 s dopo l'intervento.

### La prova QML non equivale alla sola prova del worker

La stessa fixture è stata provata con la vera interfaccia, selettore mensile,
cambio profilo e navigazione Home/catalogo/profili. Con il catalogo predefinito:
richiesta mensile 14,6 ms, completamento 3,51 s, intervallo massimo Qt 526 ms;
profilo 0,50 ms / 0,82 s / 341 ms. Con tutto il catalogo abilitato, invece,
restano pause lunghe durante navigazione e pubblicazione: intervalli massimi
di 16,55 s nel caso mese e 35,60 s nel caso profilo. Questa sonda estesa è stata
eseguita contemporaneamente al primo gate con coverage: i tempi non sono un
benchmark isolato né una prova di regressione rispetto al vecchio QML.
Sono però evidenza sufficiente per **non dichiarare risolti tutti i blocchi UI**.

Il codice della Home costruisce payload completi per l'intero insieme dei
bersagli e li ricostruisce su più notifiche. Questa parte non è stata riscritta
nel presente intervento: va profilata e ottimizzata separatamente, preservando
lista completa, ordine, immagini personali, lingua e stato temporale.

## Verifiche

I dettagli del gate finale, degli smoke e della prova QML sono riportati in
`TESTING.md` e `VISUAL_CHECKLIST.md`. Le regressioni dedicate coprono cache
fallita/vuota, retry, accorpamento, worker reale e thread di pubblicazione,
annullamento dopo il lock, contesto superato, cambio lingua, errori nelle fasi
di cattura/avvio/calcolo/pubblicazione, mantenimento del meteo periodico e shutdown.
Il percorso sincrono e quello separato sono confrontati anche senza attrezzatura,
senza meteo, con oggetti esclusi e con criteri temporali legacy.

Le prime regressioni hanno riprodotto quattro fallimenti della cache e quattro
ricalcoli doppi prima delle correzioni. Un test strutturale è stato aggiornato
per trovare le routine estratte nel modulo condiviso, senza eliminare le sue
asserzioni. Le prove del mese fallito hanno inoltre individuato e fatto correggere
una riaccodatura della stessa richiesta fra geometria e pubblicazione.

Log e sonde locali, esclusi da Git: `build/performance-audit-1.46.20/`.
`default-parity.log`, `all-parity.log` e i corrispondenti JSON conservano le coppie
di confronto; i runtime delle sonde sono copie isolate, non database dell'utente.
Le directory `qml-default/` e `qml-all/` conservano i risultati QML: complessivamente
36 scene nelle tre lingue e nei due temi, più otto stati di transizione.

## Limiti e ottimizzazioni restanti

- Non diminuiscono precisione, soglie, catalogo, contenuti editoriali o frequenze
  di timer e backup. Nessun risultato approssimato specifico per PC lenti.
- Resta utile profilare il costo puro di raccomandazioni/NSOM, la pubblicazione
  dei modelli QML e la memoria in sessioni prolungate sul PC che presenta il problema.
- Restano separati avvio e calendario annuale, ricerche/debounce, GPS manuale,
  download e virtualizzazione delle schede se nuove misure la giustificano.
- Il workflow preesistente delle abilitazioni di catalogo resta distinto, con
  le proprie regole; i fallback sincroni e tutti gli altri percorsi dell'app
  non vengono dichiarati universalmente non bloccanti.
- Il bundle locale Windows resta 1.46.18. Linux, pacchetto aggiornato, GPU nativa,
  antivirus e pressione di memoria sul PC interessato richiedono prove dedicate.
