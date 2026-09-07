# Audit prestazionale NightScope 1.46.18

Data: 7 settembre 2026. Sorgente esaminato: `cda5912`, branch `master`.

## Esito

Ci sono colli di bottiglia reali e riproducibili anche su un computer potente.
Non è giustificato attribuire la segnalazione soltanto a un PC poco potente.
Le priorità sono il lavoro sincrono sul thread dell'interfaccia, la duplicazione
dei dati tra Python e QML e alcuni calcoli astronomici ripetuti inutilmente.

L'audit comprende ispezione del sorgente, profilazione, misure locali e tre
esperimenti di ottimizzazione reversibili. **Nessuna ottimizzazione è stata
applicata al codice dell'applicazione.** Database personali, preferenze e
distribuzioni non sono stati modificati; non sono stati eseguiti commit o push.

Non è ancora una diagnosi del computer dell'utente: mancano versione installata,
hardware, configurazione del catalogo e azione che provoca il rallentamento.
Un blocco di NightScope e un rallentamento dell'intero sistema non sono la stessa
cosa: il secondo richiede anche misure di memoria, paging, disco e altri processi.

## Ambiente e metodo

- Windows 11, AMD Ryzen 9 8940HX, 16 core / 32 processori logici, circa 32 GB RAM.
- Interprete configurato in PyCharm: `.venv\Scripts\python.exe`, Python 3.14.5;
  NumPy 2.5.2. Nessun pacchetto installato per l'audit.
- SQLite isolato, creato con bootstrap e dati GeoNames reali del repository:
  62.439.424 byte, schema 27. Nessuna copia del database personale necessaria.
- 7.585 oggetti fisici nel catalogo, 219 abilitati inizialmente alle
  raccomandazioni; il controller aggiunge 9 voci del Sistema Solare.
- Astronomia congelata a Roma, 7 settembre 2026, ore 22:00 Europe/Rome;
  confronto tra configurazione predefinita e tutti gli oggetti abilitati.
- Controller con un Newton 150/750, quattro oculari e una Barlow 2x;
  48 campioni meteo sintetici coerenti, 11 nella finestra osservativa,
  temperatura 18 °C, umidità 55%, nuvolosità 10%, indice meteo 94.
- QML reale in modalità `offscreen`, cambi pagina avviati dal normale ciclo
  degli eventi, con 100 ms di assestamento inclusi nei tempi di navigazione.
- Rete disabilitata nei benchmark applicativi; servizi online esaminati nel
  sorgente, non interrogati con credenziali reali.
- Tempi wall-clock e CPU del processo misurati separatamente; memoria residente
  e memoria privata impegnata distinte. Profilazione `cProfile` separata dalle
  misure ordinarie, perché introduce overhead.

Le prove non costituiscono una campagna statistica su hardware controllato:
frequenze CPU e attività di Windows variano tra processi. Confrontare soprattutto
gli esperimenti prima/dopo nello stesso processo, non interpretare differenze
tra sessioni come miglioramenti del sorgente. Non sommare i tempi delle tabelle
per ricavare un tempo di avvio end-to-end mai misurato.

Il confronto locale con `b34ec4a`, indicato nell'handoff come base Windows
1.46.13, non mostra differenze nei principali file qui coinvolti: motore
Skyfield, controller, bootstrap, backup, query del catalogo e QML. Cambia invece
`main.py`. Questo suggerisce che diversi costi non siano nuovi della 1.46.18;
non verifica il contenuto dell'eseguibile effettivamente installato dall'utente.

## Misure principali

| Operazione | Catalogo predefinito | Tutti abilitati | Dove si paga il costo |
| --- | ---: | ---: | --- |
| Snapshot astronomico completo | 7,26 s | 14,92 s | Worker; comprende calendario e visibilità mensile |
| Applicazione snapshot e raccomandazioni | 0,108 s | 7,01 s | Thread dell'interfaccia |
| Completamento meteo e raccomandazioni | 0,161 s | 9,94 s | Thread dell'interfaccia, rete esclusa |
| Ricalcolo attrezzatura isolato | 0,095 s | 7,71 s | Thread dell'interfaccia |
| Ricalcolo risultati osservativi isolato | 0,051 s | 3,58 s | Thread dell'interfaccia |
| Completamento provider condizioni | 0,053 s | 2,84 s | Thread dell'interfaccia |
| Cambio mese settembre → ottobre | 6,44 s | 11,86 s | Thread dell'interfaccia |
| Ritorno ottobre → settembre | 5,39 s | 9,60 s | Thread dell'interfaccia; cache del mese precedente persa |
| Posizioni live, secondo passaggio del solo motore | 0,210 s / 133 oggetti | 5,03 s / 4.464 oggetti | Worker, ripetuto ogni minuto |

I benchmark del controller sono in `controller-verified-default` e
`controller-verified-all`. Quelli del solo motore sono in `baseline` e
`all-enabled`: i due livelli hanno pool leggermente diversi, perché il
controller applica ulteriori criteri di selezione. Il caso esteso non è il
comportamento predefinito: abilita esplicitamente l'intero catalogo.

| Altra operazione | Misura |
| --- | ---: |
| Apertura pagina telescopi, tutti i 133 modelli | 3,78–4,31 s nelle navigazioni ordinarie |
| Apertura pagina oculari / Barlow | 1,61 s |
| Apertura pagina filtri / riduttori | 1,53 s |
| Primo bootstrap completo, incluso GeoNames | 29,71 s |
| Bootstrap su database già popolato | 3,02–7,18 s tra sessioni |
| Visibilità mensile di 7.585 oggetti, solo motore | 4,80–10,82 s tra sessioni |
| Calendario annuale, 85 eventi nello scenario | 1,84–4,48 s tra sessioni |
| Ricerca catalogo, per modifica del testo | 43–87 ms; svuotamento 106–182 ms |
| Ricerca città con GeoNames reale | circa 114–118 ms; un primo `Ro` 533 ms |

## Rilievi e interventi

### P1 — Pagina telescopi: copie e conversioni ripetute dell'intero catalogo

Riferimenti: `app/ui/pages/EquipmentTelescopesPage.qml:260,333,347`;
`app/viewmodels/app_controller.py:1412`; `app/services/localization.py:277`.
Tutti i percorsi `app/` di questo rapporto sono relativi ad `astro_viewer/`.

La proprietà `telescopeCatalogModels` restituisce ogni volta
`render_payload(self._telescope_catalog_models)`. Durante una singola apertura
con 133 modelli, il profilo registra **407 chiamate al getter**, 22,7 milioni
di chiamate Python e 6,74 secondi cumulativi nella preparazione/localizzazione
del payload, su 8,87 secondi profilati. Questi ultimi non sono tempi ordinari.

La pagina filtra una lista esposta come variante Qt e usa un `Repeater` dentro
una griglia: prepara tutte le schede. La documentazione Qt conferma che
`Repeater` crea tutti i delegati; una vista virtualizzata può creare soltanto
quelli necessari. [Qt Repeater](https://doc.qt.io/qt-6/qml-qtquick-repeater.html)

La prova di scala dà 0,139 s con 10 modelli, 0,390 s con 40 e 3,781 s con 133.
Non serve rimuovere modelli: occorre cambiare il modo in cui arrivano alla vista.

Esperimento isolato: riutilizzando il payload già preparato, senza cambiare
contenuti o numero di schede, l'apertura passa da **4,145 a 1,948 s** nello
stesso processo. Il confronto dei dati è esatto; 408 accessi usano il payload
preparato, incluso l'accesso di controllo. Restano conversioni Qt e creazione
di tutti i delegati: il solo caching non risolve interamente il problema.

Intervento: snapshot di presentazione con invalidazione su lingua e inventario,
quindi `QAbstractListModel` e `GridView`/`ListView` con delegati riutilizzabili.
Estendere la verifica alle altre pagine attrezzatura che adottano lo stesso
schema. Preservare ricerca, filtri, selezione, IT/EN/ES e Red Night Vision.

### P1 — Cambio mese: calcolo sincrono e cache eliminata inutilmente

Riferimenti: `app/viewmodels/app_controller.py:1860,6052,6149,6229`;
`app/astronomy/skyfield_engine.py:639,738`.

`setCatalogueMonth()` cancella tutta la cache mensile e ricalcola anche
attrezzatura e risultati osservativi. La ricostruzione del catalogo arriva a
`_catalogue_visibility_map()`, che esegue Skyfield sincronicamente e acquisisce
lo stesso lock del worker astronomico. Oltre al calcolo, può quindi dover
aspettare un worker già in corso: questa attesa aggiuntiva non è inclusa nelle
misure senza concorrenza della tabella.

La chiave della cache contiene già posizione, anno e mese, ma il cambio mese
la svuota: tornare a settembre richiede altri 5,39–9,60 secondi negli scenari
misurati. Il calendario scelto per esplorare il catalogo va inoltre distinto
dalla notte corrente usata dalle raccomandazioni, preservando i contratti
attuali durante il refactoring.

Nel batch mensile si ricalcolano ad ogni istante anche stelle già risultate
visibili. La domanda è esistenziale: basta almeno un campione sopra soglia.
L'esperimento valuta soltanto i bersagli ancora senza un risultato positivo,
mantenendo Skyfield, coordinate apparenti, griglia temporale e soglia.

- Sessione estesa: **4,800 → 1,805 s**, 2,66 volte più rapido.
- Sessione con un thread BLAS: **10,819 → 3,697 s**, 2,93 volte più rapido.
- Corrispondenza esatta dei 7.585 valori booleani in entrambi i confronti.

Intervento: batch con maschera dei bersagli pendenti; cache mensile limitata per
chiave completa, inclusa revisione del catalogo; preparazione asincrona e
pubblicazione dell'ultima richiesta valida. Separare il piccolo fabbisogno
mensile dei pianeti dalle informazioni estese richieste dal catalogo.
Non sostituire il calcolo con approssimazioni o campionamenti più radi senza
una validazione scientifica esplicita.

### P1 — Raccomandazioni dopo astronomia/meteo ancora sul thread Qt

Riferimenti: `app/viewmodels/app_controller.py:3975,4345,4399,5311,5525,6355`.

La presenza del worker astronomico non rende asincrona l'intera catena.
Applicare lo snapshot e completare il meteo preparano raccomandazioni,
configurazioni strumentali, ranking e planner sul thread dell'interfaccia.
Con 4.457 oggetti deep-sky utili, il completamento meteo costa 9,94 secondi
di cui 9,86 secondi CPU: non è un'attesa della rete.

Il profilo della fase registra 4.466 chiamate a `suggest_for_profile`,
35.728 candidati telescopio, 67.460 costruzioni di `TargetObservationTraits`
e 20.464 valutazioni `observable_target_value`. Nella stessa conclusione meteo
`_refresh_conditioned_observing_candidates()` viene richiamato due volte.
Altri provider condizioni possono provocare ulteriori ricalcoli successivi.

Intervento: estendere il modello di snapshot preparato in background già
presente in `CatalogueRecommendationWorkflow`; pubblicare sul thread Qt
soltanto i dati pronti. Precalcolare le configurazioni invarianti per profilo
e i tratti fisici per oggetto; condividere solo risultati con identici input.
Home, Best Object, planner e bussola hanno contratti distinti: non unificare
i loro punteggi soltanto per risparmiare CPU. Accorpare notifiche ravvicinate
dei provider mantenendo le protezioni sulle richieste obsolete.

### P1 — Bussola live: migliaia di trasformazioni scalari ogni minuto

Riferimenti: `app/astronomy/skyfield_engine.py:524,575`;
`app/viewmodels/app_controller.py:4597,4640,4722`.

`refresh_current_positions()` attraversa i bersagli singolarmente. Per stelle
fisse ripete la preparazione dell'osservatore allo stesso istante e le
trasformazioni apparenti. Il timer è di 60 secondi e richiede posizione valida
e snapshot candidati, non che la finestra o la bussola siano visibili.

Nel caso esteso, il solo aggiornamento posizionale caldo richiede **5,03 s**
ogni ciclo. È in background, ma consuma CPU e occupa il lock astronomico;
la successiva selezione della bussola viene pubblicata su Qt.

Esperimento: vettorizzare le stelle fisse allo stesso istante, mantenendo il
percorso originale dei pianeti e la costruzione originale degli oggetti.
Risultato **5,029 → 0,237 s** su 4.464 oggetti, circa 21 volte più rapido.
Sul caso da 133 oggetti con un thread BLAS: 0,357 → 0,039 s.
Identificatori, ordine e `observable_now` coincidono; scarto massimo in
altezza 2,85e-14 gradi e in azimut 1,14e-13 gradi.

Intervento: introdurre il batch e una politica di aggiornamento legata alla
visibilità, con aggiornamento immediato al ritorno quando necessario.
Preservare isteresi live, reset dei refresh ordinari e contratto di `compass()`.
Non allungare indiscriminatamente il timer per nascondere il costo.

I confronti numerici riguardano uno scenario geografico e temporale, in due
configurazioni. Prima di integrare: poli, emisfero sud, DST, orizzonte/soglia,
pool vuoti, pianeti e più date. Non sono una certificazione scientifica completa.

### P2 — Memoria privata impegnata dal pool BLAS

La libreria OpenBLAS caricata in questo ambiente configura 24 thread per
default. In tre processi nuovi con il solo import di NumPy:

| Configurazione | Privata prima | Privata dopo import | Residente dopo import |
| --- | ---: | ---: | ---: |
| Default, 24 thread osservati | 17,00 MiB | 763,21 MiB | 35,74 MiB |
| `OPENBLAS_NUM_THREADS=1` | 16,78 MiB | 23,82 MiB | 34,24 MiB |
| `OPENBLAS_NUM_THREADS=2` | 16,76 MiB | 55,91 MiB | 34,26 MiB |

La differenza di circa **739 MiB è memoria privata impegnata, non RAM fisica
liberata**. Windows distingue il commit privato dal working set residente.
[Microsoft PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)

È un candidato per ridurre la pressione di memoria, soprattutto con più
istanze o poco margine di commit, ma non dimostra che l'utente stia facendo
paging. Il numero di thread può cambiare sul suo PC. Inoltre 24 thread creati
non significano 24 core al 100%: nei calcoli misurati CPU e wall-clock sono
spesso prossimi, compatibili con circa un core attivo.

Intervento: confrontare una politica limitata a 1–2 thread, impostata prima
degli import numerici e rispettosa di eventuali configurazioni esplicite.
NumPy documenta il controllo delle librerie BLAS tramite variabili d'ambiente.
[NumPy global state](https://numpy.org/doc/stable/reference/global_state.html)
Non è stato dimostrato un miglioramento di velocità derivante dal solo limite.
Verificare separatamente eseguibile Windows e Linux prima di adottarlo.

### P2 — Avvio: controlli e backup completi ad ogni bootstrap

Riferimenti: `main.py:187`; `app/database/bootstrap.py:209,975`;
`app/database/runtime_backup.py:27,47`.

La composizione iniziale richiama sempre `initialize_database()`. Su un
database esistente si controlla l'integrità dell'originale, si produce un
backup SQLite coerente e si controlla l'integrità della copia, poi si
sincronizzano schema e seed.

Nel profilo da 6,17 s, il controllo originale costa 2,37 s e il backup
validato 3,19 s, dei quali solo 0,73 s sono copia SQLite. La sincronizzazione
schema/seed costa circa 0,61 s. Il primo import GeoNames da 29,71 s è un costo
di inizializzazione, non il costo normale da attribuire a tutti gli avvii.

Inoltre lo snapshot astronomico iniziale aspetta calendario annuale e visibilità
mensile completa prima di pubblicare i risultati della notte, anche quando
il filtro mensile non è attivo. Sono costi da differire o memorizzare, non
semplicemente da coprire con uno splash.

Intervento: percorso rapido fondato su versione/fingerprint verificati;
politica di backup e controllo integrità con cadenza esplicita, preservando
backup precedenti, WAL, migrazioni e recupero da corruzione. Il preflight già
esistente non basta da solo a validare ogni aggiornamento di schema/seed:
non usarlo come scorciatoia senza rinforzarne il contratto. Separare gli
snapshot di calendario/catalogo da quello prioritario della notte corrente.

### P2 — Risultati obsoleti scartati solo dopo averli calcolati

Riferimenti: `app/viewmodels/app_controller.py:3766,3823,3923`.

Il percorso generale crea un worker per ogni richiesta. Il lock serializza
Skyfield; l'identificatore di generazione evita la pubblicazione di risultati
obsoleti, ma viene verificato dopo il calcolo. Una raffica può quindi lasciare
l'ultima richiesta in attesa di lavoro che non verrà mai visualizzato.

Prova controllata con gli helper della suite, metodo di avvio reale e motore
finto contatore: 5 richieste accodate, 5 chiamate al motore, 1 risultato
applicato. È una verifica della semantica, non un benchmark di cinque snapshot
astronomici reali. Il percorso specifico delle raccomandazioni del catalogo
ha già debounce e accorpamento: va preservato ed esteso, non riscritto alla cieca.

Intervento: un lavoro attivo e una sola richiesta pendente più recente;
controllo di obsolescenza prima/dopo il lock e fra fasi costose. Annullare la
pubblicazione non equivale ad annullare il consumo di CPU.
Spostare lavoro su un worker migliora la reattività, ma non elimina quel
lavoro: aggiungere thread non risolve la serializzazione del lock Skyfield.
Occorrono anche batch, caching e rimozione delle duplicazioni misurate.

### P2 — Ricerca e geolocalizzazione manuale sincrone

Riferimenti: `app/ui/pages/ObjectCataloguePage.qml:177`;
`app/ui/pages/LocationPage.qml:253`;
`app/viewmodels/app_controller.py:1843,1943,1958`;
`app/database/city_repository.py:35`; `app/services/location_providers.py:145`.

Ogni modifica del testo arriva subito al controller. Il catalogo ricostruisce
i risultati; la ricerca città interroga GeoNames con confronti parziali e
ordinamento. I 43–182 ms del catalogo e circa 114–118 ms delle città diventano
visibili digitando; un caso a cache meno favorevole costa 533 ms.

Intervento: debounce di 150–250 ms, normalizzazione e opzioni filtro
precalcolate, risultati con generazione. Considerare ricerca SQLite asincrona
o un indice specifico solo dopo aver verificato piani di query e semantica
di alias/accenti; un indice ordinario non risolve automaticamente `%testo%`.

I pulsanti di posizione di sistema e posizione approssimativa invocano
direttamente il workflow. Il provider Windows può attendere un subprocess
fino a 18 s, con eventuali fallback; il provider IP attende la rete. È un
rischio statico di blocco della UI, non un timeout riprodotto nell'audit.
Portare questi comandi sul percorso asincrono senza cambiare consenso online,
fallback o conservazione della posizione precedente. La localizzazione
automatica iniziale dispone già di un percorso asincrono.

## Copertura restante e segnali positivi

| Area | Verifica / esito |
| --- | --- |
| Architettura aggiornamenti | Snapshot astronomici e rete già separati dalla UI in diversi percorsi; lock, generazioni e debounce del catalogo sono basi utili. Il completamento pesante su Qt rimane il limite principale. |
| Motore astronomico | Finestra notturna, pianeti, deep-sky, geometria lunare, calendario, visibilità mensile e posizioni live misurati. Deep-sky e geometria lunare usano già batch: ottimizzare i punti residui, non tutto il motore. |
| Catalogo QML | Modello Qt con rendering delle sole righe richieste e notifiche compatte già presente; non confonderlo con le liste di varianti delle pagine attrezzatura. |
| Navigazione / memoria | Sei cicli catalogo → telescopi → Home, 18 cambi pagina: ritorni alla Home circa 269–279 MiB residenti, picco circa 300 MiB. Nessuna prova di crescita illimitata nel test breve; zero warning QML. |
| Riposo | 20 s senza località nella prova QML: incremento CPU sotto la risoluzione del contatore. Non copre il tick a 60 s né un'app con provider/posizione attivi. Nessuna conclusione di idle sempre gratuito. |
| Memoria con calcoli | Controller esteso: picco residente circa 521 MiB, finale circa 361 MiB; QML separato: circa 280 MiB a riposo. Non sommare massimi provenienti da processi diversi. |
| Dettagli / fotografia | Letture dettaglio nell'ordine dei millisecondi nello scenario piccolo; provata anche raccomandazione fotografica con due camere. Non certifica scalabilità con inventari enormi. |
| Fotografie | Input limitati a 20 MiB, 32 MP e lato 12.000; normalizzazione, miniature e caricamento mirato già presenti. Nessun indizio che siano la causa principale; libreria fotografica molto grande non stressata. |
| Diario osservazioni | Lettura iniziale dell'intero diario e delegati QML meritano paginazione con molti record. Rischio statico: il database di prova non contiene migliaia di osservazioni personali. |
| Meteo | Cache 45 minuti, aggiornamento ordinario orario e retry separato; non rilevato polling continuo. Costo di rete escluso dalle misure; costo di completamento UI incluso. |
| VIIRS / AOD | VIIRS richiede un sottoinsieme server; AOD legge finestre locali piccole. AOD può scaricare granuli completi tramite `earthaccess.download`, senza budget byte esplicito nel wrapper: possibile costo disco/rete da misurare con provider attivo. Cache positiva 18 h e negativa 6 h per AOD. |
| ISS / comete | Lavoro in background, dati orbitali in cache, orizzonti finiti. ISS: 10 giorni, cache 6 h; comete: 90 giorni, cache 24 h. Il limite di eventi pubblicati non limita automaticamente tutto il lavoro preliminare. Nessun benchmark orbitale live eseguito. |
| Logging / distribuzione | Rotazione log già prevista. Nessun rebuild, test antivirus, misurazione di estrazione PyInstaller o verifica di prestazioni Linux in questa sessione. |

La guida Qt raccomanda di contenere il lavoro del thread grafico, usare modelli
efficienti e spostare il lavoro lungo fuori dall'interazione. Aggiungere
`processEvents()` o garbage collection forzata non è il rimedio proposto.
[Qt Quick Performance](https://doc.qt.io/qt-6/qtquick-performance.html)

## Piano di ottimizzazione proposto

1. **Fluidità immediata:** snapshot/QAbstractListModel per attrezzatura;
   cambio mese asincrono con cache conservata; preparazione delle raccomandazioni
   estese fuori dal thread Qt. Test di invalidazione lingua/profilo e risultati
   obsoleti. Obiettivo da validare: nessuna fase monolitica di diversi secondi
   sul thread dell'interfaccia.
2. **Riduzione del lavoro:** batch live e maschera mensile; eliminazione dei
   ricalcoli identici di tratti/configurazioni; una richiesta pendente più
   recente; calendario differito; politica di refresh quando non visibile.
   Nessuna riduzione dei contenuti né alterazione intenzionale dei punteggi.
3. **PC con poche risorse e avvio:** budget thread BLAS verificato nel bundle;
   bootstrap rapido con garanzie di recupero; debounce; diario paginato;
   budget dei download opzionali. Validare sorgente, poi bundle Windows su
   runtime sacrificabile, poi PC dell'utente. Linux resta una validazione distinta.

Per ogni intervento: benchmark accoppiati su più esecuzioni, mediana e p95;
tempo massimo di ritardo del ciclo eventi Qt; CPU totale; working set e commit;
numero di richieste/ricalcoli; confronto dei risultati scientifici. Includere
configurazione predefinita ed estesa, almeno due classi hardware, interfaccia
visibile/minimizzata e sessioni lunghe. Evitare di moltiplicare i fattori di
accelerazione dei singoli esperimenti: non sono un'accelerazione dell'app intera.

## Raccolta minima per il caso segnalato

Richiedere versione esatta, sistema operativo, CPU, RAM, tipo di disco e se
NightScope è eseguito da cartella locale, USB o percorso sincronizzato;
quanti oggetti sono abilitati e quali provider opzionali sono attivi.

Chiedere quale azione rallenta e se il problema continua con NightScope
minimizzato. Durante quella stessa azione acquisire durata, CPU, memoria,
disco, numero di processi NightScope ed eventuale paging di sistema. Distinguere
prima apertura, avvii successivi e pausa dopo alcuni minuti. Non richiedere
chiavi API o un database personale completo come primo passo.

## Evidenze, riproducibilità e limiti

Output locali in `build/performance-audit-1.46.18/`, directory ignorata da Git:

- `audit_engine.py`: benchmark del motore, bootstrap, profili ed esperimenti;
  risultati `baseline`, `single-thread`, `all-enabled`.
- `audit_controller.py`: fasi del controller con meteo coerente;
  risultati validi `controller-verified-default` e `controller-verified-all`.
- `audit_ui.py`: navigazione con ciclo eventi reale, profilo telescopi,
  stabilità breve della memoria e confronto del payload preparato;
  risultati `ui-event-loop` e `ui-cached`, entrambi senza warning QML.
- `audit_native.py`, `native-default.json`, `native-1.json`, `native-2.json`:
  isolamento dei thread BLAS e del commit al solo import numerico.
- `audit_queue.py`, `queue-evidence.json`: richieste obsolete calcolate e scartate.
- `metrics.json`, file `*-profile.txt`, `*.prof` e `experiment-parity.json`
  nelle rispettive directory. `regression-tests.txt`: **146 passed in 9.58s**.

Le prime prove `controller-default` e `controller-all-enabled` sono escluse
dalle tabelle del controller: il meteo era stato costruito con argomenti
posizionali disallineati, poi corretto e verificato con asserzioni. Anche le
vecchie navigazioni `--qml` di quel primo harness sono escluse: cambi pagina
troppo ravvicinati producevano warning di incubazione e misure fuorvianti di
memoria. Usare soltanto `audit_ui.py` per ripetere la prova QML. Queste correzioni
non riguardano i benchmark indipendenti di motore, import NumPy o coda.

Esempi PowerShell dalla radice del repository; usare nuove etichette di output
per non sovrascrivere le misure. Gli script sono strumenti locali dell'audit,
non una nuova suite prestazionale pubblicata. I casi che copiano il database
richiedono la directory `baseline/runtime` già prodotta.

```powershell
& '.venv\Scripts\python.exe' 'build/performance-audit-1.46.18/audit_engine.py' --label rerun-engine --reuse-db --all-enabled --experiments
& '.venv\Scripts\python.exe' 'build/performance-audit-1.46.18/audit_controller.py' --label rerun-controller --all-enabled
& '.venv\Scripts\python.exe' 'build/performance-audit-1.46.18/audit_ui.py' --label rerun-ui
& '.venv\Scripts\python.exe' 'build/performance-audit-1.46.18/audit_ui.py' --label rerun-ui-cache --cache-only
& '.venv\Scripts\python.exe' -m pytest -q astro_viewer/tests/test_astronomy_refresh_async.py astro_viewer/tests/test_sky_compass_live_refresh.py astro_viewer/tests/test_sky_compass_service.py astro_viewer/tests/test_catalogue_object_list_model.py astro_viewer/tests/test_audit_corrections.py astro_viewer/tests/test_moon_geometry_diagnostics_runtime.py
```

Limiti espliciti: nessuna misura sul PC segnalato, nessun benchmark GPU/FPS della
finestra nativa, nessuna certificazione di assenza di leak su ore di uso, nessun
test prestazionale del bundle o di Linux, nessun download autenticato reale.
I 146 test esistenti validano i contratti selezionati del sorgente corrente;
non costituiscono la suite completa né validano un'ottimizzazione già integrata.

Conclusione: intervenire è tecnicamente giustificato. I tre esperimenti mostrano
che è possibile ridurre sensibilmente lavoro e attese mantenendo i risultati
nei casi provati. Il passo successivo è integrare per piccoli interventi con
test di correttezza e reattività, non attribuire il problema all'hardware o
disattivare indiscriminatamente funzionalità.
