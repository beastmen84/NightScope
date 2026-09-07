# Ottimizzazioni prestazionali NightScope 1.46.19

Data: 7 settembre 2026. Base del confronto: `cda5912`, sorgente 1.46.18.
Implementazione locale richiesta dopo l'[audit](PERFORMANCE_AUDIT_1_46_18.md).
La priorità è conservare risultati e funzionalità, non ridurre la precisione.

## Modifiche applicate e contratti conservati

1. **Posizioni live dei bersagli fissi in batch.** Una chiamata Skyfield per
   il gruppo, invece di una chiamata per oggetto. Sistema Solare e coordinate
   mancanti/non valide mantengono il percorso precedente. Vicino alle soglie
   e ai confini di arrotondamento si torna al calcolo scalare. Non cambiano
   aggiornamento al minuto, isteresi della bussola, punteggi o ordinamento.
2. **Visibilità mensile con soli bersagli ancora da verificare.** Un oggetto
   già sopra soglia non viene ricalcolato ai campioni successivi. Conservati
   istanti di campionamento, soglie, oscurità/crepuscolo, Sole e fallback.
   Ai confini numerici viene riutilizzata l'aritmetica del batch completo.
3. **Snapshot QML per tutte e sei le pagine attrezzatura.** Le sequenze sono
   passate per valore al componente della pagina, evitando accessi ripetuti
   ai getter Python durante filtri e iterazioni. Le notifiche già esistenti
   aggiornano gli snapshot su modifiche a inventario, profilo e lingua.
   Nessun modello rimosso; schede, Repeater, layout e filtri sono conservati.
4. **Cache ottica limitata a 16.384 voci.** La chiave contiene tutti e soli i
   sette valori immutabili letti da `TargetObservationTraits`; il risultato è
   immutabile. Non conserva oggetti celesti o liste mutabili di configurazioni.
   La variazione di un input produce una nuova voce; nessuna formula cambia.
5. **Cache mensile limitata a 12 voci.** Tornare a un mese già preparato riusa
   la geometria. Posizione, fuso, anno, mese e soglia restano nella chiave;
   le invalidazioni esplicite per posizione/catalogo restano operative.
   Il mese selezionato continua a influire sui pianeti della Home: separarlo
   avrebbe modificato il comportamento attuale e non è stato fatto.
6. **Preparazione asincrona del mese richiesto dall'interfaccia.** Un worker
   attivo e una sola richiesta pendente, sostituibile con l'ultima. I dati del
   catalogo sono copiati prima del calcolo. Risultati obsoleti non vengono
   pubblicati; la selezione e i risultati precedenti restano coerenti durante
   l'attesa. Il controllo mostra un'ellissi ed è temporaneamente disabilitato.
   La pubblicazione usa il metodo sincrono precedente e il contesto corrente
   di attrezzatura/meteo. L'API `setCatalogueMonth()` resta disponibile.
7. **Lavoro duplicato evitato.** Dopo meteo e cambio mese, i candidati
   condizionati vengono calcolati una volta, nel ricalcolo finale previsto.
   I worker astronomici controllano l'obsolescenza prima e dopo l'attesa del
   lock: richieste già superate non avviano altri calcoli. Un calcolo già
   partito non viene interrotto a metà; il coordinatore astronomico generale
   non è stato trasformato in un pool limitato.
8. **Budget OpenBLAS all'avvio.** Un thread predefinito prima dell'importazione
   di NumPy. Impostazioni esplicite `OPENBLAS_NUM_THREADS`, `GOTO_NUM_THREADS`
   o `OMP_NUM_THREADS` hanno precedenza; un runtime NumPy già importato non
   viene riconfigurato. Nessun cambio a dipendenze o impostazioni globali del PC.

## Confronti diretti con il sorgente precedente

I metodi originali sono letti da `git show cda5912:<file>` ed eseguiti nello
stesso processo del confronto ottimizzato, con dati e orologio identici.
Database di benchmark isolato, Roma 7 settembre 2026 ore 22:00, rete bloccata.

| Verifica | Risultato |
| --- | --- |
| Posizioni live, 4.466 bersagli | Tutti i campi non numerici e i flag identici; massima differenza angolare 1,14 × 10⁻¹³ gradi |
| Visibilità mensile, 7.585 oggetti fisici | Tutti i valori booleani identici |
| Caratteristiche ottiche, 4.466 bersagli | Tutti i campi identici al metodo precedente |
| Completamento meteo, catalogo interamente abilitato | Identici oggetti, configurazioni, read model, Home, punteggi, Best Object, Planner e bussola |
| Cambio mese, stesso catalogo esteso | Identici risultati finali della stessa catena |
| Budget numerico, processi separati a 1 e 24 thread | Identici tutti i campi astronomici dei 4.466 bersagli, posizioni live, mappa mensile e riepilogo Luna; nessuna differenza numerica |

Misure locali accoppiate, non una promessa su altri PC:

| Calcolo | Prima | Dopo |
| --- | ---: | ---: |
| Posizioni live di 4.466 bersagli | 9,95 s | 0,65 s |
| Visibilità mensile di 7.585 oggetti | 9,78 s | 3,54 s |
| Catena meteo estesa, rete esclusa | 10,97 s | 8,74 s |
| Cambio mese sincrono esteso, cache riutilizzabile | 15,24 s | 9,66 s |

Gli ultimi due confronti verificano risultati completi e conservano i costi
residui di raccomandazioni e pubblicazione sul thread Qt. La preparazione
asincrona sposta la geometria, non elimina questi costi. La sonda conserva
anche copie dei payload di riferimento: la sua memoria non rappresenta il
normale consumo dell'applicazione. Non sommare questi tempi come misura di avvio.

La pagina con tutti i 133 telescopi si apre in circa 0,3–0,5 s nelle nuove
sessioni, contro i 3,78–4,31 s dell'audit precedente. Sono sessioni distinte;
il riscontro strutturale è la scomparsa dei 407 accessi ripetuti al getter.
La sonda di avvio NumPy conferma un pool OpenBLAS da un thread e circa 25 MiB
di memoria privata impegnata, contro circa 763 MiB nella sonda precedente a
24 thread. La memoria residente resta circa 35 MiB: non sono 738 MiB di RAM
fisica liberati e non è una prova che il PC segnalato stesse facendo paging.

## Verifiche automatiche e interfaccia

- Astronomia: 153 test mirati, inclusi otto contesti geografici/temporali,
  cambi d'ora, alte latitudini, coordinate errate e casi sulle soglie.
- Attrezzatura: 153 test e dieci subtest dopo l'integrazione degli snapshot;
  verificati payload IT/EN/ES, notifiche pertinenti, aggiornamenti e copie.
- Caratteristiche ottiche/NSOM: 135 test mirati, inclusi invalidazione,
  immutabilità e dimensione massima della cache.
- Mesi/worker/integrazione: 116 test e dieci subtest; ulteriori casi per
  risposta già completata ma superata e annullamento dopo il lock sono
  inclusi nel successivo controllo di 67 test con la documentazione.
- La matrice QML esercita sette pagine × tre lingue × due temi e confronta
  gli snapshot con i getter canonici: 42 scenari catturati, zero warning QML,
  otto campioni visuali ispezionati e cambio lingua a pagina già aperta.
- Il selettore del mese è stato azionato nel QML reale: richiesta non bloccante,
  eventi Qt attivi durante il calcolo, mese precedente coerente fino alla
  pubblicazione e mappa finale di 7.594 valori identica al calcolo diretto.
  Nessuna variazione ai flag di abilitazione delle raccomandazioni.
- **Gate finale completo: 1.609 test e dieci subtest, copertura 86%**, tutti
  i controlli sorgente/sicurezza e i tre smoke isolati superati. Lint su tutte
  le 36 sorgenti QML riuscito. Dettagli e log finali in `docs/TESTING.md`.

Le prime prove hanno rilevato errori delle nuove fixture astronomiche,
asserzioni strutturali ancora riferite ai vecchi getter QML e il vecchio
conteggio dei file. Sono stati corretti e i gruppi rieseguiti, senza eliminare
asserzioni sui risultati. La prima sonda integrale usava nomi errati per i
campi delle coordinate; quella corretta passa. Il primo tentativo di cattura
QML non importava `QQuickWindow`; quello successivo ha evidenziato la mancanza
dei font nel backend offscreen, risolta nel solo strumento di verifica.
Il primo gate completo ha fermato una nuova eccezione silenziosa nel batch
(Bandit B112): aggiunto logging diagnostico e rieseguito l'intero gate,
senza cambiare il fallback né allentare il baseline di sicurezza.

Log e strumenti locali: `build/performance-audit-1.46.18/`, prefissi `step1`
fino a `step7`; baseline e sonde precedenti restano separati. Il gate finale
e la matrice visuale corretta sono identificati precisamente in TESTING.

## Confini e lavoro restante

- Non è stata applicata una riscrittura asincrona generale di meteo, profilo,
  provider e raccomandazioni. Richiede un coordinamento completo delle
  invalidazioni e delle continuazioni: nel catalogo interamente abilitato
  questi passaggi possono ancora bloccare temporaneamente l'interfaccia.
- Non sono state cambiate frequenze di timer, backup o verifiche del database;
  nessun degrado automatico di precisione, catalogo o contenuti su PC lenti.
- Restano da valutare separatamente virtualizzazione delle schede se servisse
  ancora, debounce delle ricerche, GPS manuale, avvio/calendario annuale,
  download e uso prolungato con archivi personali grandi.
- Non c'è ancora una misura sul PC dell'utente. Nessuna nuova build Linux,
  prova GPU/antivirus, stress su memoria fisica scarsa o validazione del
  pacchetto Windows 1.46.19 viene dedotta dalle prove sorgente.
- Distribuzioni e dati personali non sono stati sostituiti. Il bundle locale
  resta 1.46.18. L'utente ha successivamente richiesto il commit locale delle
  modifiche; questo non comporta push, tag o pubblicazione.
