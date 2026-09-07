# Parità degli aggiornamenti osservativi accorpati

Data: 2026-09-07. Correzione sorgente successiva a `57d4b37` (1.46.21),
non ancora rilasciata. Riferimento precedente alle ottimizzazioni: `cda5912`.
VERSION, website, dati personali e distribuzioni non vengono modificati.

## Difetto riprodotto

La gestione introdotta in `8e86509` (1.46.20) sceglieva soltanto il flag
`apply_pollution` dell'ultima richiesta che ricostruiva l'attrezzatura.
Un aggiornamento meteo dopo il cambio profilo perdeva quindi il rinnovo dei
dati grezzi e del modello d'inquinamento luminoso richiesto dal profilo.

Con il catalogo predefinito, Roma, una notte e un meteo deterministici, il
passaggio da Newton 150/750 a occhio nudo esponeva M31 al quarto posto anziché
al dodicesimo. M45 conservava nei dati grezzi il precedente setup telescopico.
Il risultato corretto coincideva sia con `cda5912` sia con il controller
sincrono attuale. Il problema interessava il ranking pubblico, non solo cache
interne. Home overview, best object, piano e punteggi per categoria coincidevano
nel caso iniziale: non si sostiene che tutti questi risultati fossero errati.

## Correzione e limiti del lavoro

- La decisione di aggiornare i dati grezzi/modelli d'inquinamento e distinta
  dall'applicazione dell'inquinamento alla lista finale. Rimane la regola
  dell'ultimo rebuild per quest'ultima, compresi meteo e cambio mese.
- Ogni richiesta di rebuild cattura un'istantanea dei propri input, senza
  eseguire calcoli sul thread Qt. Il worker conserva l'ultima preparazione
  con inquinamento e l'ultima preparazione complessiva; non ricostruisce
  tutti i risultati intermedi destinati a essere sostituiti.
- Se sorgenti, strumenti e condizioni dell'attrezzatura coincidono, basta una
  preparazione. Se differiscono, vengono eseguite le due preparazioni necessarie
  a preservare i dati della sequenza originale, ma un solo ranking finale.
  Le condizioni finali correnti continuano a governare NSOM, Planner e bussola.
- Le routine scientifiche condivise, i punteggi, le soglie, i filtri e il
  campionamento non vengono riscritti. Restano un solo worker, accorpamento per
  tipo, annullamento cooperativo e pubblicazione atomica sul thread Qt.
- Il contesto temporaneo appartiene esclusivamente al worker ed e ripristinato
  anche in caso di errore/annullamento. Sorgenti finali vuote non recuperano
  accidentalmente gli oggetti di una preparazione intermedia.

La prima correzione sperimentale ripristinava l'ordine con meteo fisso, ma
non tutti i dati interni quando il meteo cambiava veramente durante la coda.
Il confronto indipendente ha motivato le istantanee per richiesta: non e stata
accettata come completa una semplice sostituzione del flag con `any()`.

## Verifiche

Le regressioni permanenti sono in `astro_viewer/tests/test_observing_refresh.py`.
Confrontano il percorso accorpato con la sequenza sincrona originale, inclusi
stato completo, raccomandazioni pubbliche e Home. Coprono aggiunta/rimozione
di strumenti, meteo/condizioni variabili, sei permutazioni dei tre eventi,
duplicati, cambio mese, VIIRS, primo meteo, richieste superate e worker reale
interrotto dopo aver preparato i dati d'inquinamento. Controlli dedicati
proteggono il numero di preparazioni e l'unico ranking finale.

Un precedente test di profilo/condizioni usava come riferimento un unico
ricalcolo nel contesto finale, non la sequenza precedente alle ottimizzazioni.
Ora usa i due percorsi sincroni originali e confronta anche i payload pubblici;
conservate le verifiche di mancata pubblicazione obsoleta e callback eseguite
una volta. Non sono state eliminate asserzioni di equivalenza.

Le sonde indipendenti caricano le routine originali direttamente da Git
(`cda5912`), usano il catalogo reale in runtime temporanei e bloccano la rete.
Confrontano 23 gruppi di risultati, oltre all'ordine pubblico e al setup di M45.
I log sono conservati in `build/performance-overlap-fix-20260907/` (ignorato).
La prova iniziale del difetto rimane separata in
`build/performance-parity-recheck-1.46.21-20260907/`.

Gate finale `tools/run_checks.py --coverage --security` superato: 1.911 test
e dieci sottotest in 263,48 s; copertura 87% (19.039 / 21.948 istruzioni).
Sono 182 casi aggiuntivi rispetto ai 1.729 test della riverifica iniziale.
Ruff, documentazione, dipendenze, cicli import, baseline Bandit, compilazione,
licenze e audit dati passano. `pip-audit` non rileva vulnerabilità note.
Smoke isolati da sorgente: backend 11,2 s, QML normale 10,4 s, rosso 11,1 s.
Log: `full-source-gate-final.log`; il precedente `full-source-gate.log`
riguarda la correzione intermedia ed e distinto dall'approvazione finale.

Il confronto AST ripetuto con `cda5912` conferma che le 19 routine condivise
di calcolo restano identiche salvo i controlli di annullamento già presenti.
Il motore astronomico e i tratti fisici non sono cambiati in questa correzione;
la precedente riverifica numerica rimane documentata nel suo report separato.

Quattro matrici indipendenti superate, dieci sequenze ciascuna: catalogo
predefinito (135 bersagli) e completo (4.466), aggiunta e rimozione degli
strumenti, con meteo realmente variabile. Tutti i 23 gruppi di risultati,
l'ordine pubblico delle raccomandazioni e il setup grezzo di M45 coincidono
con `cda5912` in tutti i 40 scenari. Nel caso predefinito senza strumenti M31
torna al dodicesimo posto; le posizioni nel catalogo completo sono naturalmente
diverse, ma coincidono anch'esse con il rispettivo riferimento.

Passano inoltre i quattro aggiornamenti ordinari indipendenti (meteo, profilo,
condizioni, mese) con il catalogo completo: nessuna differenza nei 23 gruppi.
In questa sonda le richieste sul thread Qt impiegano circa 0,10 ms per le sole
condizioni e 7,26-10,03 ms per i rebuild. Sono misure locali di accodamento,
non una garanzia di assenza di pause della Home o sul PC dell'utente.

File di risultato: `default-add-optics-weather-change-matrix.json`,
`default-remove-optics-weather-change-matrix.json`,
`all-add-optics-weather-change-matrix.json`,
`all-remove-optics-weather-change-matrix.json` e `all-results.json`.
Log corrispondenti: `default-add-weather-change-final.log`,
`default-remove-weather-change-final.log`, `all-add-weather-change-final.log`,
`all-remove-weather-change-final.log`, `ordinary-all-final.log`.
Tutti questi processi terminano con codice zero. Il confronto strutturale
e registrato in `calculation-structure.json` e nel relativo log.

Durante la costruzione dei test, una fixture iniziale simulava impropriamente
un risultato meteo `None`: il servizio reale restituisce invece un riepilogo
anche quando mancano dati. Corretta la sola fixture e ripetuti i controlli;
il test ora copre un profilo inizialmente senza meteo seguito dal primo
riepilogo. Nessun percorso produttivo e stato modificato per adattarsi al test.

## Confini dell'approvazione

Le verifiche deterministiche non dimostrano ogni possibile interleaving,
localita, data o combinazione di strumenti. La correzione non dichiara risolti
tutti i rallentamenti, ne sostituisce una prova sul PC interessato.
Questo lavoro non rigenera o approva il bundle Windows pubblico, non esegue
una build Linux e non crea tag, push o release. Il prossimo pacchetto richiede
una nuova versione e il proprio gate di distribuzione.
