# Changelog

## NightScope 1.33.2 - 2026-07-15

- Adottata la Mozilla Public License 2.0 per NightScope, Copyright 2026 Davide
  Marchi. Aggiunti avviso consolidato per software/dati e archivio completo
  delle licenze delle dipendenze validate.
- Aggiunto un generatore deterministico dell'archivio licenze con modalita'
  `--check`; il gate standard ora fallisce quando dipendenze o testi legali non
  sono allineati all'ambiente installato.
- Limitata la dipendenza Qt a `PySide6_Essentials` e aggiunti hook PyInstaller
  che raccolgono solo i moduli QML usati da NightScope. Rimossi dal futuro
  bundle plugin e moduli Qt Addons/GPL-only non utilizzati.
- Il build Windows verifica prima l'archivio licenze, copia `LICENSE` e i file
  third-party nella radice dell'app e blocca il rilascio se mancano DLL Qt
  necessarie o compaiono moduli GPL-only inattesi.
- Una build PyInstaller temporanea e isolata ha superato audit legale/Qt e
  smoke QML dell'eseguibile (`5223` file, `469,8 MiB`). La `dist` persistente
  `1.33.2` e' stata poi rigenerata e ha superato audit Qt/licenze e smoke
  backend/QML.
- L'audit rifiuta ora database, backup, preferenze, cache e log runtime nella
  cartella da pubblicare. I controlli manuali vanno eseguiti su una copia del
  bundle pulito, evitando di distribuire stato locale creato durante i test.
- Gate completo con security superato: `791 passed`, `613 warnings` note,
  `7 subtests`, coverage runtime `84%`, nessuna vulnerabilita' installata nota
  e Bandit invariato a `0 high`, `26 medium`, `12 low`.
- Pubblicata la release GitHub `v1.33.2` dal commit sorgente
  `9c17204f718223e83183367e9ccea078805b5a00`. Lo ZIP Windows x64 estratto
  contiene `5221` file, supera l'audit Qt/licenze/stato runtime e non include
  database o log dell'utente.
- SHA-256 pubblicato per `NightScope-v1.33.2-windows-x64.zip`:
  `33424e4e8317dee951230d795e2f0de936946910ede232ba478e893c73e02967`.

## NightScope 1.33.1 - 2026-07-15

- Completato il passaggio di correzione derivato dalla matrice visuale
  italiano/inglese: risolti tutti i 36 rilievi registrati in
  `docs/VISUAL_CHECKLIST.md` senza modificare score, soglie astronomiche o
  selezione dell'equipaggiamento.
- Resa la localizzazione dei contenuti strutturati consapevole della lingua di
  ogni singolo campo. Nomi, descrizioni, note e categorie dei cataloghi
  Oggetti ed Equipment non dipendono piu' da una lingua unica dichiarata per
  l'intero CSV; i designatori NGC/IC restano canonici e le traduzioni inglesi
  Caldwell sono deterministiche e protette da regressioni lessicali.
- Localizzati soltanto in presentazione i nomi delle costellazioni, conservando
  i valori IAU canonici per filtri e servizi. I nomi paese dinamici dei provider
  restano intenzionalmente canonici; la timezone IANA continua a essere il dato
  operativo autorevole.
- Aggiunte etichette persistenti e unita' ai form Equipment, corretti campi
  AFOV Fisso/Zoom e decimali precompilati, reso reattivo il menu delle classi
  filtro e uniformate le classi dei filtri colorati. I nomi lunghi dei
  riduttori possono occupare due righe e i binocoli usano ordinamento naturale.
- Corretto l'aggiornamento dei riduttori affinche' preservi compatibilita'
  descrittive e associazioni esatte quando non vengono sostituite. Il percorso
  di aggiunta gestisce correttamente l'assenza di compatibilita' testuale.
- Uniformati angoli, radianza VIIRS, terminologia astronomica e testi operativi
  in Home, Calendario, Meteo, Log e dettaglio oggetto. Le eclissi usano titoli
  completi e naturali, la metrica Home distingue Catalogo da Distanza e le
  occorrenze italiane visibili di `target` sono state sostituite con `oggetto`.
- Riallineate le intestazioni della tabella Oggetti visibili usando lo stesso
  componente delle righe, stabilizzata la colonna azioni del Log e aumentata
  l'altezza delle schede Prossimi eventi per consentire titoli su due righe.
- Cataloghi Qt italiano e inglese completi e compilati (`1665/1665`); suite
  mirata localizzazione, Equipment, Home e Calendario: `113 passed`.
- Gate completo `--fast` superato: `788 passed`, `613 warnings` note di
  compatibilita' Skyfield/NumPy e `7 subtests`; `pip check`, Ruff,
  `compileall`, smoke backend e smoke QML puliti. `qmllint` termina con exit
  `0` su tutti i 30 file QML e gli smoke QML separati passano in italiano e
  inglese con runtime temporanei.
- Schema SQLite invariato a `16`. La dist esistente resta `1.32.3`; la dist
  `1.33.1` non e' stata rigenerata.

## NightScope 1.33.0 - 2026-07-14

- Eseguito un audit pre-release completo su codice Python/QML, database,
  provider, dipendenze, dati, immagini, packaging, localizzazione, privacy e
  documentazione. Non sono emersi difetti funzionali applicativi ad alta
  severità; i gate di release ancora aperti sono raccolti in
  `docs/RELEASE_CHECKLIST.md`.
- Riscritto il README GitHub interamente in inglese come panoramica di prodotto
  e sviluppo, separandolo dal changelog e rendendo espliciti stato pre-release,
  uso della rete, privacy, limiti, build portatile e assenza della licenza di
  progetto.
- Sostituito il manuale italiano con un manuale HTML unico italiano/inglese,
  responsive, stampabile e navigabile. Aggiunte guida iniziale, formule ottiche,
  logica NSOM/equipaggiamento, calendario transitorio, provider, stati dei dati,
  privacy, backup, troubleshooting e sicurezza solare.
- Aggiunto nella testata della sidebar il pulsante di aiuto che apre il manuale
  nella lingua corrente, con percorso valido sia da sorgente sia nel bundle
  PyInstaller.
- Corretto il manuale sulla semantica atmosferica: AOD resta la sorgente aerosol
  primaria; OpenAQ può entrare nella trasparenza soltanto come fallback non
  additivo quando qualità e freschezza sono accettate.
- Rimossi da log informativi coordinate, chiavi località, payload diagnostici
  Windows, dettagli di normalizzazione e username Earthdata. Rimossa anche la
  diagnostica Windows inutilizzata dalla superficie pubblica del controller;
  aggiunti test di regressione privacy.
- Rimosso `deep-translator 1.11.4` dalle dipendenze developer dopo il finding
  `PYSEC-2022-252`; gli updater usano ora un adapter developer minimale,
  timeout-bounded e coperto da mock, senza dipendenza runtime aggiuntiva.
- Allineato `requirements-dev.txt` agli strumenti documentati. Il runner esegue
  una sola suite per invocazione, usa coverage di default, `--fast` per saltarlo
  e `--security` per aggiungere `pip-audit`; pytest è limitato a quattro worker
  per evitare pressione eccessiva sulla memoria. Gli smoke test backend/QML usano
  una directory runtime temporanea e non toccano database, preferenze, cache o
  log personali. La coverage esclude test e utility developer, evitando una
  percentuale artificialmente gonfiata.
- Unificata la directory runtime di database, preferenze, cache e log. Nel
  bundle portatile `logs/nightscope.log` viene ora scritto accanto
  all'eseguibile e non dentro la directory dati `_internal`; aggiunta una
  copertura di regressione per override e cambio sicuro dell'handler.
- Aggiornate architettura, localizzazione, fonti GeoNames con licenza CC BY 4.0,
  audit e checklist di rilascio. Nessuna modifica a NSOM, Planner, ranking Home,
  Equipment scoring, Sky Compass o schema SQLite, ancora `16`.
- Validazione finale superata: `785` test e `7` subtest, coverage runtime `84%`,
  `15` test traduzioni,
  cataloghi IT/EN completi (`1595/1595`), smoke QML in entrambe le lingue,
  lint di `30` file QML, `228` immagini verificate, `pip check`, Ruff,
  `compileall` e `pip-audit` puliti.
- La dist esistente resta `1.32.3`; dist `1.33.0` non rigenerata.

## NightScope 1.32.9 - 2026-07-14

- Decodificato il bit field MAIAC `AOD_QA`: sono accettati soltanto pixel clear,
  non adiacenti a contaminazioni e con qualità AOD migliore. La policy scoring
  usa la stessa decodifica e non tratta più il valore grezzo come un indice
  numerico.
- Resa adattiva l'estrazione locale AOD: pixel esatto, area 5x5 e infine 11x11,
  con almeno tre pixel affidabili. Mediana AOD e QA rappresentativo restano
  semanticamente separati; risultato, log e UI conservano raggio e distanza
  del pixel valido più vicino.
- Aggiunta una cache negativa di 6 ore per `no_granules` e `no_valid_pixel`.
  Errori di autenticazione, ricerca, download e parsing non vengono memorizzati;
  i risultati positivi mantengono la TTL di 18 ore e il riuso entro 500 metri.
- Il messaggio AOD senza dati riassume intervallo di ricerca, prodotti e numero
  di granuli controllati, senza presentare come conclusivo l'ultimo granulo
  analizzato.
- Home e la sintesi Meteo mostrano la trasparenza atmosferica prevista senza la
  penalità Bortle; fondo cielo e Bortle restano metriche separate. Il composito
  backend esistente resta disponibile ai consumer compatibili.
- Le date intervallo del Calendario possono occupare al massimo due righe, così
  le finestre cometarie non vengono troncate. Uniformata inoltre l'unità VIIRS a
  `nW/cm² sr`.
- Aggiornati e compilati i cataloghi italiano/inglese completi `1594/1594`.
- Verificati `pip check`, Ruff, compileall, `qmllint` sui 30 QML e smoke backend/
  QML italiano e inglese su runtime temporanei. Suite completa parallela: `774
  passed`, `613 warnings`, `7 subtests passed` in `65,28 s`.
- Nessuna migrazione database; schema SQLite ancora `16`. La dist esistente e'
  `1.32.3`; dist `1.32.9` non rigenerata.

## NightScope 1.32.8 - 2026-07-14

- Limitata la normalizzazione del fuso alla sola acquisizione di una nuova
  localita'. Il controller considera autorevoli le posizioni salvate dalla
  build corrente e non contiene piu' percorsi di rinormalizzazione legacy.
- Rimossi il parametro interno per imporre un fuso alle coordinate manuali e i
  relativi test di compatibilita'. Coordinate manuali e citta' selezionate
  usano sempre `timezonefinder`, con il fuso del computer come unico fallback.
- Reso lazy anche il fallback di sistema: una risposta geografica o una
  mappatura Windows valida non avvia piu' inutilmente PowerShell, che sulla
  macchina di sviluppo richiedeva circa due secondi per chiamata.
- Il fuso GeoNames non partecipa piu' neppure alla selezione manuale di una
  citta'. Il catalogo resta necessario per ricerca citta' offline, coordinate e
  metadati descrittivi; non e' un duplicato del dataset dei fusi.
- Misurato il costo GeoNames: `8.529.230` byte nel bundle corrente (`1,14%`) e
  circa `55 MB` nel database runtime dopo l'import di `33.775` citta' e
  `327.374` alias. Rimuoverlo richiederebbe una scelta esplicita di prodotto:
  eliminare la ricerca citta' offline.
- Verificati `pip check`, Ruff, compileall, smoke standard e QML
  italiano/inglese su runtime temporanei; suite completa parallela: `764
  passed`, `613 warnings`, `7 subtests passed` in `103,34 s`.
- Nessuna migrazione database; schema SQLite ancora `16`. La dist esistente e'
  `1.32.3`; dist `1.32.8` non rigenerata.

## NightScope 1.32.7 - 2026-07-14

- Aggiunta la risoluzione offline del fuso IANA da coordinate WGS84 tramite
  `timezonefinder 8.2.5`; coordinate manuali e posizione Windows non dipendono
  piu' dalla copertura del catalogo citta' per ottenere gli orari locali.
- Le coordinate ricevute restano invariate. Per la posizione Windows precisa
  il match GeoNames entro 50 km arricchisce soltanto citta', paese e regione;
  il precedente tentativo di dedurre il fuso dalla citta' entro 500 km e' stato
  rimosso.
- Posizione Windows approssimata e coordinate manuali usano lo stesso lookup
  geografico. Un fuso IANA valido del provider IP resta autorevole; il fuso del
  computer interviene solo se la risoluzione offline non e' disponibile.
- Le posizioni manuali gia' salvate vengono rinormalizzate al caricamento e
  mantengono nome e coordinate originali. Il resolver e' lazy, condiviso e non
  effettua query di rete.
- Documentate fonte, licenze MIT/ODbL e raccolta automatica dei dati tramite
  l'hook PyInstaller di `timezonefinder`.
- Verificati `pip check`, Ruff, compileall, hook PyInstaller, smoke standard e
  QML italiano/inglese; suite completa parallela: `766 passed`, `642 warnings`,
  `7 subtests passed` in `106.17s`.
- Nessuna migrazione database; schema SQLite ancora `16`. La dist esistente e'
  `1.32.3`; dist `1.32.7` non rigenerata.

## NightScope 1.32.6 - 2026-07-14

- La scheda Home del cielo profondo usa ora lo stato esplicito `Parziale`
  quando il diagnostico dispone del meteo ma non della qualita' cielo reale.
  Il valore NSOM interno resta disponibile ai consumer, mentre badge e testo
  non presentano piu' il risultato come un giudizio completo.
- I suggerimenti deep-sky senza Bortle distinguono la trasparenza disponibile
  dall'inquinamento luminoso mancante e non dichiarano piu' un buon potenziale
  per gli oggetti deboli senza quel dato.
- Il controllo cache VIIRS precede ora il gate delle credenziali Earthdata. Una
  misura reale stale resta utilizzabile, ma Meteo avvisa che deve essere
  aggiornata; una cache fresca continua a non richiedere accesso di rete.
- Freschezza cache e confidenza della misura restano dimensioni separate: la
  correzione non abbassa artificialmente la confidenza del dato VIIRS salvato.
- Aggiornati e compilati i cataloghi italiano/inglese completi `1590/1590`.
- Verificati `pip check`, Ruff, compileall, tutti i 30 QML e smoke
  italiano/inglese; suite completa parallela: `753 passed`, `613 warnings`,
  `7 subtests passed` in `119.03s`.
- Nessuna migrazione database; schema SQLite ancora `16`. La dist esistente e'
  `1.32.3`; dist `1.32.6` non rigenerata.

## NightScope 1.32.5 - 2026-07-14

- Rimossi `light_pollution_seed.csv`, il provider di baseline urbana e il
  fallback sintetico che assegnava Bortle `5/6` senza dati geografici reali.
- `LightPollutionService` restituisce ora qualita' cielo solo da cache NASA
  VIIRS o da un dataset locale World Atlas/VIIRS realmente fornito; altrimenti
  espone uno stato assente e ripulisce le vecchie cache non VIIRS.
- Meteo presenta Bortle, SQM, limite visuale e confidenza come `n/d` quando il
  dato non esiste. Seeing e gli altri consumer continuano sugli input
  disponibili senza applicare una penalita' luminosa inventata.
- Home distingue gli oggetti soltanto compatibili con l'occhio nudo dalla
  visibilita' locale verificata, riequilibra le colonne Nome/Tipo e consente ai
  titoli dei prossimi eventi di occupare al massimo due righe.
- Rimossi dal packaging e dalla documentazione i riferimenti al seed e al suo
  import; mantenuto il supporto preparato per dataset locali reali opzionali.
- Aggiornati e compilati i cataloghi italiano/inglese completi `1586/1586`.
- Verificati `pip check`, Ruff, compileall, tutti i 30 QML e smoke
  italiano/inglese; suite completa parallela: `751 passed`, `613 warnings`,
  `7 subtests passed` in `112.43s`.
- Nessuna migrazione database; schema SQLite ancora `16`. La dist esistente e'
  `1.32.3`; dist `1.32.5` non rigenerata.

## NightScope 1.32.4 - 2026-07-14

- Corretto il percorso realmente usato dal Catalogo per le dimensioni
  angolari: il formatter backend emette ora `°` e non piu' `deg`; aggiunta una
  regressione sul payload mostrato, non soltanto sul fallback QML.
- In assenza di telescopi e binocoli, la tabella inferiore Home esclude i target
  marcati `requires_optical_instrument` dal read model Equipment. La colonna
  oggetto e' piu' stretta, la difficolta' mostra per intero le etichette e il
  layout compatto entra prima sui viewport intermedi.
- Sostituita nella Home la fotografia statica della Luna con un'icona neutra;
  immagini e fase dinamica nel dettaglio oggetto restano invariate.
- Chiarito che le metriche superiori Meteo sono aggregate sulla finestra
  osservativa: medie per nuvole, vento, umidita' e temperatura, massimo per la
  probabilita' di precipitazione, seeing/trasparenza notturni e Bortle locale.
- Localizzata la sorgente `NightScope local urban baseline`; resi espliciti i
  campi obbligatori delle coordinate manuali e uniformati i relativi pulsanti
  allo stile dell'app.
- Verificata senza modifiche la pipeline ISS per Addis Abeba: 26 passaggi
  geometrici sopra `10°` nella finestra di 10 giorni, ma nessuno insieme
  illuminato e con Sole locale sotto `-6°`; il conteggio `0` e' corretto.
- Aggiornati e compilati i cataloghi italiano/inglese completi `1586/1586`.
- Verificati `pip check`, Ruff, compileall, tutti i 30 QML e smoke
  italiano/inglese; suite completa parallela: `750 passed`, `613 warnings`,
  `7 subtests passed`.
- Nessuna migrazione database; schema SQLite ancora `16`. La dist esistente e'
  `1.32.3`; dist `1.32.4` non rigenerata.

## NightScope 1.32.3 - 2026-07-14

- Corretto lo stato Meteo senza localita': SQM, limite visuale, confidenza e
  dati VIIRS non possono piu' mostrare zeri o valori precedenti come se fossero
  misure disponibili.
- Aggiunto l'accesso diretto a `Localita'` da Home, Meteo e Calendario;
  alleggeriti i messaggi ripetuti nelle sezioni vuote e uniformata la
  terminologia di configurazione.
- Localizzati i barilotti degli oculari e delle Barlow con separatore decimale
  e simbolo dei pollici; aggiornato a `°` il fallback QML delle dimensioni
  angolari. Il formatter backend prioritario e' stato corretto in `1.32.4`.
- Rifinite le etichette dei form Equipment con unita' tra parentesi, esempio
  italiano `0,63` e checkbox binocolo `Stabilizzato` senza falso indicatore di
  campo facoltativo.
- Aggiornati e compilati i cataloghi italiano/inglese completi `1575/1575`.
- Verificati `pip check`, Ruff, compileall, tutti i QML e smoke italiano/inglese;
  suite completa parallela: `748 passed`, `613 warnings`, `7 subtests passed`.
- Nessuna migrazione database; schema SQLite ancora `16`. Dist `1.32.3` non
  rigenerata.

## NightScope 1.32.2 - 2026-07-14

- Corrette le chiavi delle voci integrate dei sei cataloghi strumenti: sono ora
  dichiarate esplicitamente nei CSV e non vengono piu' ricalcolate da marca,
  modello o parametri tecnici modificabili.
- Le correzioni dei dati seed aggiornano la riga esistente senza duplicarla;
  una collisione con una voce personalizzata conserva il dato utente e non
  interrompe il bootstrap.
- Le compatibilita' riduttore-telescopio referenziano direttamente le chiavi
  immutabili, quindi restano valide anche dopo la correzione del nome di un
  prodotto.
- Mantenute tutte le 468 chiavi gia' generate dalla `1.32.1`; nessuna migrazione
  aggiuntiva, schema SQLite ancora `16`. Gli upgrade diretti da versioni piu'
  vecchie agganciano una sola volta le righe integrate legacy alle chiavi
  esplicite prima di applicare il reseed.
- Verificati `pip check`, Ruff, compileall, integrita' SQLite e suite completa
  parallela: `747 passed`, `613 warnings`, `7 subtests passed` in `108,27 s`.
- Dist `1.32.2` non rigenerata.

## NightScope 1.32.1 - 2026-07-14

- Rinominato il profilo iniziale in `Default`; `Occhio nudo` resta la modalità
  osservativa derivata quando il profilo non contiene telescopi o binocoli. La
  migrazione sceglie un nome libero senza sovrascrivere profili utente omonimi.
- Portato lo schema SQLite a `16` con chiavi seed stabili e stato di modifica:
  le voci integrate dei sei cataloghi strumenti sono modificabili ma non
  eliminabili, e le correzioni utente sopravvivono ai bootstrap successivi.
- Resi espliciti campi obbligatori e facoltativi nei form equipaggiamento;
  validazioni e conversioni numeriche mantengono aperto il dialogo e mostrano
  l'errore, mentre gli indicatori privi di dati non vengono renderizzati.
- Ridotta la spaziatura verticale della navigazione laterale e corretti gli
  stati senza località in Home, Meteo, Calendario e filtri posizione-dipendenti
  del catalogo, evitando dati dimostrativi o indicatori fuorvianti.
- Aggiornati i cataloghi italiano/inglese completi `1571/1571`.
- Verificati `pip check`, Ruff, compileall, `qmllint` e smoke backend/QML in
  italiano e inglese; suite completa parallela: `743 passed`, `613 warnings`,
  `7 subtests passed` in `138,45 s`.
- Dist `1.32.1` non rigenerata.

## NightScope 1.32.0 - 2026-07-14

- Aggiunta `CometWindowEventSource`, seconda sorgente transitoria score-free:
  usa elementi pubblici NASA/JPL SBDB e calcolo locale Skyfield senza creare
  `CatalogueObject` o coinvolgere score, Equipment, Planner, Home ranking o
  NSOM.
- Introdotta una finestra mobile di 90 giorni con campioni ogni 30 minuti,
  soglie di altezza, buio, elongazione, Luna e magnitudine prevista; le notti
  consecutive vengono aggregate in un solo evento per cometa.
- Esposte magnitudine come intervallo indicativo, altezza massima, elongazione,
  distanza e illuminazione lunare, numero di notti utili, fonte e freschezza.
- Aggiunta cache SQLite SBDB con TTL di 24 ore, fallback massimo di 7 giorni e
  retry con backoff sui `5xx`; aggiunto pandas runtime per il supporto alle
  orbite cometarie Skyfield, senza introdurre astroquery o account esterni.
- Il motore conserva i risultati transitori per sorgente: la ISS continua a
  ricalcolarsi ogni ora, le comete ogni 6 ore e gli eventi non ancora in
  scadenza restano disponibili tra i due intervalli.
- Calendario, Home e dettaglio supportano tipo, filtro, conteggio e indicazioni
  specifiche per le comete; il contratto passa a `calendar_overview_v4`.
- Aggiornati i cataloghi italiano/inglese completi `1552/1552` e aggiunti test
  offline per calcolo, aggregazione, cache, fallback, retry, limite di
  luminosita' e cadenze indipendenti delle sorgenti.
- Verificati `pip check`, Ruff, compileall, `qmllint`, smoke backend/QML in
  italiano e inglese e render Calendar largo/compatto; suite completa
  parallela: `739 passed`, `613 warnings`, `7 subtests passed` in `128,93 s`.
- Dist `1.32.0` non rigenerata.

## NightScope 1.31.1 - 2026-07-14

- Separata la preparazione rete/cache delle sorgenti transitorie dal calcolo
  Skyfield: gli eventi annuali non attendono piu' CelesTrak e il lock del
  motore protegge soltanto la propagazione astronomica.
- Aggiunto un refresh ISS dedicato ogni ora, con sostituzione atomica degli
  eventi transitori, scarto dei risultati di localita' precedenti e download
  OMM ancora vincolato alla TTL di 6 ore.
- Corretta l'inclusione degli eventi istantanei appartenenti a date passate,
  che potevano occupare oggi e mascherare un duplicato futuro.
- Stabilizzati gli ID ISS tramite il numero continuo di rivoluzione e aggiunti
  data/ora reale dell'ultimo aggiornamento orbitale e copy neutro nel dettaglio.
- Aggiornati i cataloghi italiano/inglese completi `1518/1518` e aggiunte
  regressioni per filtro temporale, separazione del worker, timer e ID stabili.
- Verificati `pip check`, Ruff, compileall, `qmllint`, smoke test backend/QML e
  suite completa parallela: `733 passed`, `563 warnings`, `7 subtests passed`
  in `90,36 s`.
- Dist `1.31.1` non rigenerata.

## NightScope 1.31.0 - 2026-07-13

- Aggiunta una pipeline di eventi transitori score-free, distinta dagli eventi
  astronomici annuali e pronta per ulteriori provider senza creare oggetti di
  catalogo o coinvolgere Planner, Equipment, Home ranking e NSOM.
- Integrati come prima sorgente i passaggi visibili della ISS per la posizione
  attiva, con finestra ingresso-uscita, culminazione, altezza massima,
  direzioni, durata, illuminazione e dettaglio sorgente nel Calendario.
- La Home riusa il contratto cronologico del Calendario e include i passaggi
  ISS ancora in corso o futuri tra i prossimi eventi; quelli conclusi vengono
  rimossi anche se appartengono alla data corrente.
- Aggiunta `OrbitalElementCache` allo schema SQLite `15`: i dati OMM pubblici
  CelesTrak vengono aggiornati ogni 6 ore, con fallback offline massimo di 3
  giorni e previsione mobile limitata a 10 giorni.
- Riutilizzate Skyfield, SGP4, Requests e NumPy gia' installate; pandas e
  astroquery non sono necessari per questa prima sorgente e non sono stati
  aggiunti.
- Verificati `pip check`, Ruff, compileall, cataloghi Qt completi `1517/1517`,
  `qmllint`, smoke test backend/QML e suite completa parallela: `731 passed`,
  `561 warnings`, `7 subtests passed` in `90,40 s`.
- Dist `1.31.0` non rigenerata.

## NightScope 1.28.0 - 2026-07-13

- Aggiunta la pagina `Log Osservazioni` tra Calendario e Meteo, con riepilogo,
  ricerca testuale, filtro per valutazione ed elenco completo senza tagli.
- Sostituito il vecchio inserimento legato al dettaglio oggetto con un
  contratto CRUD dedicato: aggiunta, modifica ed eliminazione delle sessioni,
  con data/ora locale, oggetto, luogo, telescopio, oculare, voto e note.
- I nuovi record propongono localita' e setup del profilo attivo; il backend
  valida formato, voto e natura retrospettiva del log. La tabella SQLite
  esistente resta invariata e i dati utente continuano a essere preservati.
- Aggiunti read model e riepiloghi score-free separati da NSOM, Planner, Home,
  Equipment e raccomandazioni osservative.
- Verificati Ruff, compileall, `pip check`, `qmllint`, QML smoke in runtime
  temporaneo e suite completa parallela: `711 passed`, `557 warnings`,
  `7 subtests passed` in `115,69 s`.
- Dist `1.28.0` non rigenerata.

## NightScope 1.27.1 - 2026-07-13

- Limitate le raccomandazioni filtro alle configurazioni che selezionano un
  telescopio reale; setup a occhio nudo o binocolo non espongono piu' accessori
  da oculare non utilizzabili.
- La selezione confronta ora l'apertura del telescopio con
  `minimum_aperture_mm`, scarta le classi prive di prodotti adatti nel catalogo
  e preferisce, fra i filtri posseduti validi, la soglia supportata piu' alta.
- Aggiunto il vincolo specifico di `280 mm` per il filtro giallo opzionale su
  Urano e Nettuno. Se manca un prodotto adatto viene mostrata soltanto la classe
  primaria, senza unire primaria e fallback nello stesso testo.
- Rimossi il percorso di migrazione dei vecchi filtri duplicati per barilotto,
  la classe `COLOR_UNSPECIFIED` e i relativi test: la base di sviluppo parte
  direttamente dal catalogo canonico con classi colore esplicite.
- Corretta la concordanza italiana nel selettore dei telescopi compatibili dei
  riduttori: `1 selezionato`, altrimenti `N selezionati`.
- Verificati Ruff, compileall, `pip check`, `qmllint` della pagina Equipment e
  suite completa parallela: `703 passed`, `557 warnings`, `7 subtests passed`
  in `119,08 s`.
- Dist `1.27.1` non rigenerata.

## NightScope 1.27.0 - 2026-07-13

- Aggiunto a `CatalogueObject` il flag fotografico
  `imaging_reducer_recommended`: il seed lo abilita per 53 target estesi senza
  modificare gli altri metadati delle 219 righe catalografiche.
- Introdotto `ReducerRecommendationService`, separato da Equipment e NSOM. Il
  servizio parte dal telescopio scelto per il target, richiede una
  compatibilita' esatta normalizzata e considera soltanto riduttori dichiarati
  adatti all'imaging.
- Il dettaglio osservativo indica i riduttori compatibili gia' nel profilo
  attivo oppure, se assenti, quelli presenti nel catalogo come suggerimenti non
  disponibili. Piu' prodotti compatibili vengono elencati deterministicamente:
  senza camera e sensore non viene inventata una priorita' ottica.
- Portato `observingObjectDetail` alla versione `v3` e lo schema SQLite alla
  versione `14`. Le migrazioni esistenti ricevono il nuovo flag con valore
  predefinito falso e il bootstrap riallinea solo il campo gestito dal seed.
- La compatibilita' dei riduttori personalizzati usa ora una selezione
  ricercabile dei modelli `TelescopeModel`, con collegamenti normalizzati
  molti-a-molti preservati durante il reseed e validati dal repository.
- La raccomandazione e' esclusivamente fotografica e di presentazione: non
  calcola focale o campo risultanti e non modifica `EquipmentService`,
  `ObserverCapability`, score, ranking, Planner, Home, Sky Compass o NSOM.
- Verificati confronto strutturato dei 219 oggetti, Ruff, compileall, `pip
  check`, `qmllint`, QML smoke test temporaneo e suite completa parallela:
  `701 passed`, `557 warnings`, `7 subtests passed` in `126,42 s`.
- Dist `1.27.0` non rigenerata.

## NightScope 1.26.0 - 2026-07-13

- Normalizzato il catalogo filtri a 48 modelli visuali unici: il formato
  `1.25\"`/`2\"` non e' piu' un dato applicativo e le precedenti varianti di
  formato vengono consolidate senza perdere le assegnazioni ai profili.
- Sostituita la classe generica `COLOR` con classi colore esplicite e aggiunto
  il relativo menu a tendina per i filtri utente. Le righe legacy non
  riconoscibili restano leggibili come `COLOR_UNSPECIFIED`, ma non sono
  selezionabili ne' raccomandabili.
- Aggiunti otto filtri Celestron mancanti, incluso il polarizzatore variabile e
  le principali classi Wratten visuali. Il seed conserva un solo modello per
  prodotto, indipendentemente dal barilotto.
- Esteso il catalogo oggetti con preferenza filtro primaria, alternativa
  equivalente e colore opzionale. Le preferenze deep-sky coprono 35 nebulose
  Messier/Caldwell con classi UHC, OIII o H-beta; Luna e pianeti usano una
  policy separata per attenuazione/contrasto e colore facoltativo.
- Il dettaglio osservativo usa soltanto i filtri assegnati al profilo attivo e
  mostra al massimo una raccomandazione primaria e una colorata opzionale. Se
  un prodotto adatto e' presente ne indica il nome; altrimenti espone la classe
  suggerita come non disponibile. Le alternative sono preferenze, non filtri
  da sovrapporre.
- Portato `observingObjectDetail` alla versione `v2` e lo schema SQLite alla
  versione `13`. La migrazione riclassifica i colori riconoscibili, consolida i
  duplicati di formato e rimappa gli ID gia' usati dai profili.
- Filtri e riduttori non entrano in EquipmentService, ObserverCapability,
  score, ranking, Planner o NSOM. I riduttori restano inventario passivo in
  attesa della policy dedicata.
- Verificati confronto strutturato dei 219 oggetti, Ruff, compileall, `pip
  check`, `qmllint`, QML smoke test temporaneo e suite completa parallela:
  `692 passed`, `557 warnings`, `7 subtests passed` in `87,19 s`.
- Dist `1.26.0` non rigenerata.

## NightScope 1.25.1 - 2026-07-12

- Resi completamente read-only tutti gli elementi Equipment inclusi: la UI
  nasconde sia `Modifica` sia `Elimina` e il repository blocca gli aggiornamenti
  anche fuori dalla QML. Questo impedisce che una modifica delle chiavi del seed
  produca duplicati non eliminabili al bootstrap successivo.
- Abilitate le foreign key su ogni connessione Equipment, rimossi in migrazione
  i collegamenti a profili inesistenti e corretti i conteggi d'uso con profili
  distinti, inclusa la transizione dal vecchio `telescope_id` alla relazione
  molti-a-molti.
- Aggiunta `ReducerTelescopeCompatibility` con un seed di 16 associazioni esatte
  tra riduttori dedicati e modelli di telescopio. Il testo descrittivo resta
  disponibile, ma il futuro punto 5 può usare ID normalizzati senza interpretare
  stringhe libere. Filtri e riduttori restano inventario passivo e non entrano
  ancora in setup, score, ranking o NSOM.
- Le descrizioni e curiosita' incluse sono ora contenuti gestiti: il bootstrap
  aggiorna le righe `is_builtin`, mentre l'importatore marca come personalizzate
  le righe utente e le preserva nei successivi avvii. Rimossa la vecchia
  correzione speciale della copia lunare, ormai coperta dalla regola generale.
- Portato lo schema SQLite alla versione `12`, con migrazione verificata dallo
  schema `10` di `1.25.0`; la spec PyInstaller include anche il nuovo seed di
  compatibilita'.
- Portata a 228 la copertura di descrizioni e curiosita', aggiungendo il Sole con
  istruzioni di sicurezza esplicite e curiosita' NASA. Sostituite 180 note
  osservative duplicate con indicazioni specifiche basate su nome, dimensione e
  magnitudine; arricchite le descrizioni Caldwell troppo simili senza cambiare
  identita', classificazione, difficolta', score o ranking.
- Tradotti in italiano i messaggi residui per profilo duplicato e diagnostica
  della posizione Windows.
- Verificati `pip check`, Ruff, compileall, smoke Python/QML, `qmllint`, 228
  asset e 227 URL delle curiosita'. Suite completa parallela: `683 passed`,
  `558 warnings`, `7 subtests passed` in `60,32 s`.
- Dist `1.25.1` non rigenerata.

## NightScope 1.25.0 - 2026-07-12

- Aggiunta la pagina `Filtri e riduttori`, coerente con il layout a due colonne
  di oculari e Barlow, con ricerca condivisa e CRUD per gli elementi creati
  dall'utente.
- Il catalogo integrato comprende 77 filtri visuali di 6 produttori e 24
  riduttori/correttori di 7 produttori, selezionati da cataloghi e manuali
  ufficiali. I filtri espongono classe, formato, dati spettrali, trasmissione e
  apertura minima; i riduttori fattore, sistema/modelli compatibili,
  connessione, backfocus, impiego visuale/fotografico e correzione del campo.
- Filtri e riduttori possono essere assegnati o rimossi dal profilo attivo e
  sono visibili nei relativi gruppi. In questa release restano inventario
  passivo: non modificano capacità, setup consigliato, score, ranking o NSOM.
- Aggiunta la provenienza `is_builtin` a telescopi, oculari, Barlow, binocoli,
  filtri e riduttori. Il pulsante `Elimina` non appare per gli elementi
  integrati e il repository ne impedisce comunque la cancellazione; gli
  elementi personalizzati restano eliminabili con rimozione esplicita dai
  profili che li usano.
- Lo schema SQLite passa a `10` con migrazione idempotente, due cataloghi e due
  tabelle di assegnazione. Il bootstrap marca i seed esistenti senza
  sovrascrivere modifiche locali e conserva come personalizzate le altre righe.
- Aggiornata la spec PyInstaller per includere entrambi i nuovi seed; la `dist`
  non e' stata rigenerata.
- Verificati CRUD e migrazione repository, assegnazione profilo senza refresh
  NSOM, layout offscreen, `pip check`, Ruff, compileall, smoke Python/QML e
  `qmllint`. Suite completa parallela: `677 passed`, `557 warnings`,
  `7 subtests passed` in `50,21 s`.

## NightScope 1.24.2 - 2026-07-12

- Aggiunto a destra di `Piano della notte` il pulsante checkable
  `Solo suggeriti ora`, disabilitato quando Sky Compass non ha target
  osservabili e non selezionato per impostazione predefinita.
- Quando attivo, il filtro interseca per ID canonico sia le tappe del piano sia
  `Altri oggetti visibili stasera` con tutti i target della direzione scelta da
  Sky Compass, inclusi quelli oltre i tre target principali mostrati nella card.
- Conteggi e filtri `Tutti / Pianeti / Cielo profondo` lavorano sul sottoinsieme
  corrente; ordine cronologico del piano e ordine delle alternative restano
  invariati. Aggiunti messaggi dedicati quando una scheda non ha corrispondenze.
- Il filtro segue il refresh live Sky Compass ogni 60 secondi, aggiorna il
  modello solo quando cambia l'insieme degli ID e si spegne automaticamente su
  `no_targets`. Nessun cambio a formule, score, ranking o servizi NSOM.
- Verificati interazione e auto-reset QML, rendering offscreen, `pip check`,
  Ruff, compileall, smoke Python/QML, `qmllint` e 228 asset. Suite completa
  parallela: `670 passed`, `557 warnings`, `7 subtests passed` in `51,86 s`.
- Dist `1.24.2` non rigenerata.

## NightScope 1.24.1 - 2026-07-12

- Sostituiti i nove SVG illustrativi di Sole, Luna, Mercurio, Venere, Marte,
  Giove, Saturno, Urano e Nettuno con JPEG RGB locali `512 x 512` ricavati da
  immagini scientifiche ufficiali NASA/JPL Photojournal.
- Ogni asset conserva PIA, pagina sorgente e credito esatto nel seed. Il
  dettaglio mostra il credito cliccabile; le immagini sono rappresentazioni
  statiche e processate, non indicano fase, orientamento o aspetto corrente.
- Aggiornati anche i percorsi diretti di astronomia, Calendario e fallback Luna;
  rimossi i nove SVG non piu' referenziati. Il bootstrap migra solo i vecchi
  asset generati da NightScope e preserva immagini personalizzate dall'utente.
- Aggiunto `sync_solar_system_images.py`, che scarica gli originali PIA,
  applica ritagli deterministici, normalizza il formato e verifica file e seed.
- Verificati `pip check`, Ruff, compileall, smoke Python/QML, `qmllint` e tutti
  i 228 JPEG. Suite completa parallela: `668 passed`, `558 warnings`,
  `7 subtests passed` in `54,21 s`; le warning restano quelle Skyfield/NumPy
  gia' note.
- Dist `1.24.1` non rigenerata.

## NightScope 1.24.0 - 2026-07-12

- Aggiunta la tabella `ObjectCuriosity` e il seed dedicato con 227 curiosita'
  italiane per Luna, pianeti, Messier e Caldwell. Ogni testo descrive un fatto
  specifico, conserva una fonte apribile e resta separato da descrizioni
  osservative, Equipment e NSOM.
- Verificate le 226 URL distinte; i 227 testi sono unici, lunghi almeno 158
  caratteri e superano i controlli automatici contro duplicati e formulazioni
  eccessivamente simili.
- Aggiunta nel dettaglio Home e Catalogo la card `Curiosita'`, con collegamento
  esplicito alla fonte.
- Sostituiti tutti i placeholder dei 219 target cielo profondo con JPEG RGB
  dedicati `512 x 512`: 200 cutout 2MASS, 15 Pan-STARRS1 e 4 SkyMapper DR4,
  generati da CDS `hips2fits` e verificati anche visivamente per le categorie
  in cui il solo infrarosso non rappresentava bene il soggetto.
- Ogni immagine conserva URL esatta, attribuzione e dichiarazione di licenza;
  il credito e' visibile e cliccabile nel dettaglio. La policy esclude DSS e
  asset editoriali privi di diritti di ridistribuzione chiari.
- Il bootstrap aggiorna i vecchi asset deep-sky gestiti da NightScope senza
  sostituire immagini personalizzate dall'utente. Lo schema SQLite passa a `9`.
- Aggiunti tool ripetibili per sincronizzare/verificare gli asset e controllare
  le fonti delle curiosita'; Pillow resta una dipendenza solo di sviluppo.
- Verificati `pip check`, Ruff, compileall, smoke Python/QML, `qmllint`, 219
  asset e 226 fonti. Suite completa parallela: `667 passed`, `558 warnings`,
  `7 subtests passed` in `58,91 s`; le warning restano quelle Skyfield/NumPy
  gia' note.
- Dist `1.24.0` non rigenerata.

## NightScope 1.23.3 - 2026-07-12

- Revisionate esternamente le due colonne editoriali del catalogo:
  `short_description` cambia per 222 dei 227 target e `observing_notes` per 205.
- Verificati con confronto CSV strutturato numero e ordine delle 227 righe, ID,
  stagioni e cinque livelli di difficolta': nessun dato fuori dalle due colonne
  editoriali e' cambiato e non sono presenti ID duplicati o testi vuoti.
- Rimosso il BOM UTF-8 introdotto dall'editor esterno, che trasformava la prima
  intestazione in `\ufeffobject_id` e impediva il bootstrap del database.
- Reso il test del dettaglio C23 indipendente da una singola formulazione
  redazionale, mantenendo il controllo sulla presenza di una nota sostanziale.
- Verificati `pip check`, Ruff, compileall, smoke Python/QML e `qmllint`.
  Suite completa parallela: `664 passed`, `558 warnings`, `7 subtests passed`
  in `53,45 s`; le warning restano quelle Skyfield/NumPy gia' note.
- Dist `1.23.3` non rigenerata.

## NightScope 1.23.2 - 2026-07-12

- Corretto l'ordine del classificatore NSOM: `Planetary nebula` viene ora
  assegnato a `PLANETARY_NEBULA` prima del controllo generico su `planet`.
  La correzione riguarda 17 target complessivi, 13 Caldwell e 4 Messier.
- Mappati esplicitamente i 3 `Supernova remnant`, 2 Caldwell e 1 Messier, sulla
  classe NSOM esistente `DIFFUSE_NEBULA`; non sono state aggiunte categorie o
  modificate formule e pesi NSOM.
- Allineati per i resti di supernova il riconoscimento deep-sky, il profilo
  atmosferico, la penalita' da inquinamento luminoso, il bonus intrinseco e la
  presentazione delle difficolta'. Equipment continua a usare i metadati
  osservativi espliciti gia' presenti nel catalogo.
- Centralizzata la normalizzazione inglese/italiana dei resti di supernova per
  evitare divergenze tra classificatore, condizioni, score e presenter.
- Aggiunto un contratto parametrico su tutti i tipi presenti nei 219 record
  Messier/Caldwell e sulle varianti italiane supportate.
- Verificati `pip check`, Ruff, compileall, smoke Python/QML e `qmllint`.
  Suite completa parallela: `664 passed`, `558 warnings`, `7 subtests passed`
  in `54,24 s`; le warning restano quelle Skyfield/NumPy gia' note.
- Dist `1.23.2` non rigenerata.

## NightScope 1.23.1 - 2026-07-12

- Aggiunte a `object_descriptions_seed.csv` le 109 righe Caldwell con
  descrizione italiana, nota osservativa, stagione consigliata e difficolta'
  per occhio nudo, binocolo e tre classi di telescopio.
- Portato `object_images_seed.csv` a copertura esplicita di tutti i 219 target
  cielo profondo: aggiunti 109 Caldwell e i 79 Messier che prima usavano solo
  il fallback runtime.
- I mapping nuovi usano i placeholder locali tipizzati ammasso/nebulosa/galassia;
  non vengono presentati come immagini astronomiche reali e potranno essere
  sostituiti singolarmente nel successivo passaggio asset e licenze.
- Il dettaglio Caldwell espone ora `catalogueIntroText`, `bestSeen` e il testo
  osservativo completo tramite lo stesso contratto gia' usato dai Messier.
- Corretta la capitalizzazione italiana di `Galassia di Seyfert` per C24 e
  trattata C63 come nebulosa planetaria ampia a bassa luminosita' superficiale.
- Aggiunti test di copertura ID/file, esistenza asset e ripristino idempotente
  dei contenuti mancanti senza sovrascrivere modifiche locali.
- Suite completa parallela: `630 passed`, `557 warnings`, `7 subtests passed`
  in `52,93 s`; le warning restano quelle Skyfield/NumPy gia' note.
- Dist `1.23.1` non rigenerata.

## NightScope 1.23.0 - 2026-07-12

- Importati tutti i 109 target Caldwell dalla lista J2000 dell'Astronomical
  League: coordinate, magnitudine quando disponibile, dimensione, tipo,
  costellazione e identificativo NGC/IC.
- Verificata la composizione ufficiale Caldwell di 46 ammassi, 35 galassie e
  28 nebulose. Il catalogo esclude intenzionalmente i Messier: C1-C109 usano
  quindi ID canonici distinti `caldwell-C1`-`caldwell-C109`.
- Il catalogo visibile contiene ora 228 righe: 109 Caldwell, 110 Messier e 9
  corpi del Sistema Solare. Ricerca, filtri, dettaglio e visibilita' mensile
  riusano il contratto generico senza duplicare target o conteggi.
- La ricerca ordina corrispondenze esatte prima di prefissi e sottostringhe;
  `C23` e `NGC 891` risolvono lo stesso target, mentre una ricerca come `Giove`
  mostra prima il pianeta e poi eventuali nomi composti.
- Portato lo schema SQLite alla versione `8`: aggiunti indici univoci
  case-insensitive per ID e designazioni e attivata l'integrita' referenziale
  durante il bootstrap.
- Il bootstrap valida prima dell'import ID, designazioni, riferimenti,
  ordinamento, primaria unica, dimensione angolare e tipo osservativo dei seed.
- Aggiunte etichette italiane per galassie irregolari, peculiari e di Seyfert e
  per nebulose oscure. I resti di supernova usano il fallback visivo nebulosa.
- Benchmark locale con 219 target profondi: raccomandazioni in circa `1,04 s` e
  visibilita' mensile completa in circa `1,73 s`.
- Suite completa parallela: `628 passed`, `558 warnings`, `7 subtests passed`
  in `46,92 s`; le warning restano quelle Skyfield/NumPy gia' note.
- Dist `1.23.0` non rigenerata.

## NightScope 1.22.0 - 2026-07-12

- Separata l'identita' fisica degli oggetti dalle designazioni catalografiche:
  `CatalogueObject` contiene il target unico e `CatalogueDesignation` associa
  uno o piu' codici di catalogo allo stesso `object_id`.
- Portato lo schema SQLite alla versione `7`; la migrazione copia i dati dal
  vecchio `MessierObject`, conserva descrizioni locali e ID `messier-Mxx`, crea
  le designazioni Messier e rimuove la tabella ritirata.
- Sostituito `MessierRepository` con `CatalogueRepository`; controller, motore
  Skyfield e strumenti di validazione consumano ora il repository generico.
- Separati i seed fisici `catalogue_objects_seed.csv` e le designazioni
  `catalogue_designations_seed.csv`, entrambi inclusi nel package PyInstaller.
- La lista generale conta ogni oggetto fisico una volta. Ricerca, lookup e filtro
  di catalogo riconoscono anche designazioni secondarie; il filtro cambia codice
  e ordinamento mostrati senza cambiare l'ID runtime.
- Aggiunti vincoli e test per una sola designazione primaria, alias
  case-insensitive e una designazione secondaria simulata sullo stesso target:
  il totale resta 110 anziche' diventare 111.
- Caldwell non e' ancora importato; questa release prepara il contratto dati
  necessario per aggiungerlo senza duplicare gli oggetti condivisi con Messier.
- Verificati dipendenze, Ruff, compileall, smoke Python, QML smoke e `qmllint`;
  suite completa parallela: `625 passed`, `558 warnings`, `7 subtests passed`
  in `43,56 s`. Le warning restano quelle Skyfield/NumPy gia' note.
- Dist `1.22.0` non rigenerata.

## NightScope 1.21.1 - 2026-07-12

- Verificata l'intera composizione NSOM: qualita' intrinseca, ambiente,
  capacita' osservatore, finestra, cronologia, Session e vincoli pratici
  entrano una sola volta nei rispettivi livelli.
- Rimossa la seconda costruzione dell'intrinseco durante
  `ObservableTargetValue` e il secondo calcolo seeing nello stesso refresh
  meteo; VIIRS aggiorna seeing prima delle raccomandazioni Equipment.
- Corretta la confidence runtime: OpenAQ riconosce il campo canonico
  `available`, la geometria lunare e' valutata per singolo target e la mancanza
  VIIRS non viene duplicata come fallback generico.
- Centralizzata la deduplicazione per ID canonico, stabile e case-insensitive,
  nei pool Home, ranking Home/Best Object, Planner e Sky Compass.
- Resi difensivi anche piano Home, alternative e conteggi Equipment: una stessa
  riga identificata non puo' incrementare due volte sequenze o contatori.
- Resi difensivi i contatori annuali del Calendario e i partecipanti degli
  eventi: stesso ID normalizzato compare una volta, senza introdurre cap e
  senza eliminare eventi privi di ID.
- Il Planner valuta al massimo una volta ogni target e presenta fino a quattro
  opportunita' uniche; l'ordinamento cronologico avviene solo dopo la selezione.
- Corretta la documentazione che riportava ancora la formula Planner ritirata e
  la dicitura fuorviante `esattamente quattro`.
- Suite completa parallela: `621 passed`, `558 warnings`, `7 subtests passed`
  in `38,23 s`; le warning sono la deprecazione Skyfield/NumPy gia' nota.
- Verificati `pip check`, Ruff, `compileall`, smoke Python, smoke QML e
  `pyside6-qmllint`; il lint QML termina con exit `0` e conserva le warning
  statiche gia' note.
- Distribuzione non rigenerata: sorgente `1.21.1`, dist esistente `1.20.0`.

## NightScope 1.21.0 - 2026-07-11

- Consolidato `NsomObservationEnvironmentService` come unico proprietario di
  geometria, Luna, fondo cielo VIIRS/Bortle, seeing/trasparenza e AOD/OpenAQ.
- Separati definitivamente qualita' intrinseca e condizioni runtime:
  `intrinsic_score` e `atmospheric_transparency_score` restano interni e non
  cambiano il payload QML.
- Unificati Home, Best Object, Planner e Sky Compass sugli stessi
  `ObservationConditionInputs`; i dati provider mancanti sono fattori neutrali,
  non selezionano un algoritmo alternativo.
- Corretto il Planner per considerare una finestra gia' iniziata come
  osservabile adesso e per usare lo strumento selezionato per ogni target.
- Rimossi `PlannerScoringService`, il ranking Sky Compass parallelo, i servizi
  Advanced Observing/Detail ombra, i flag AOD/Luna e il fallback Best Object del
  vecchio `ObservingScoreService`.
- Rimossi snapshot diagnostici automatici, export/controller wiring e test di
  comparazione o rollback non piu' rappresentativi del runtime.
- Rinominato il modello attivo delle categorie Home in
  `ObservingCategoryScores`; il contratto QML resta invariato.
- Allineato lo smoke Python a `homeObservingOverview`, eliminando l'ultimo
  accesso alla property rimossa `advancedScores`.
- Rimossa la componente QML inutilizzata `ObjectRow.qml`.
- Aggiornati architettura, logica di calcolo, modello NSOM, closeout e audit di
  cleanup alla topologia runtime effettiva.
- Suite completa parallela: `610 passed`, `558 warnings`, `7 subtests passed`
  in `41,05 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota.
- Verificati `pip check`, Ruff, `compileall`, smoke Python, smoke QML e
  `qmllint`; quest'ultimo mantiene le warning QML statiche gia' note ma termina
  con exit code `0`.
- Distribuzione non rigenerata: sorgente `1.21.0`, dist esistente `1.20.0`.

## NightScope 1.20.1 - 2026-07-11

- Rimossa dalla tabella `Oggetti celesti` la colonna ridondante `Visibile nel
  mese`: checkbox e selettore del mese continuano a filtrare il catalogo senza
  mostrare una colonna composta soltanto da trattini o risultati gia' filtrati.
- Il dettaglio Catalogo mostra ora `Visibile nel mese corrente`, calcolato per
  il solo oggetto aperto usando posizione, anno e mese locali correnti,
  indipendentemente dal flag e dal mese selezionato nella lista.
- Aggiunta una cache dedicata per oggetto e mese corrente; un probe locale sul
  singolo M31 richiede circa `0,03 s` al primo accesso e riusa poi il risultato.
- Distinti `No` e dato non disponibile: `No` indica un risultato astronomico
  negativo, mentre posizione assente o calcolo fallito restano `—`.
- Localizzati nella presentazione i tipi di oggetto e le modalita' osservative
  del Catalogo (`Ammasso aperto`, `Campo largo`, `Alto ingrandimento`, ecc.);
  valori canonici inglesi, filtri e logica backend restano invariati.
- Il testo introduttivo della scheda usa la nota osservativa italiana e non
  concatena piu' la descrizione tecnica inglese del seed. Il ramo dettaglio
  osservativo condiviso resta invariato.
- Verificati `pip check`, ruff, compileall, smoke Python/QML, `qmllint`,
  interazione reale delle combo localizzate e rendering offscreen
  desktop/compatto.
- Suite completa parallela: `721 passed`, `557 warnings`, `7 subtests passed`
  in `49,02 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota.
- Distribuzione non rigenerata in questo step: sorgente `1.20.1`, dist
  esistente `1.20.0`.

## NightScope 1.20.0 - 2026-07-11

- Uniformato il Calendario a un orizzonte completo di 365 giorni: fasi
  lunari, opposizioni, congiunzioni planetarie e solari, eclissi lunari e sciami
  non subiscono piu' il precedente taglio ai 18 eventi con utilita' maggiore.
- Portate anche le fasi lunari da 90 a 365 giorni e le eclissi da 730 a 365,
  cosi' tutti i filtri condividono lo stesso confine temporale.
- Aggiunti quattro sciami maggiori alla lista annuale e mantenuto il massimo
  del giorno corrente anche quando l'istante convenzionale di mezzanotte e'
  gia' trascorso.
- Separati nel modello istante evento, tipo di timing, finestra osservativa,
  visibilita' locale, target associati e separazione angolare.
- Aggiunti gli avvicinamenti tra tutte le 21 coppie dei sette pianeti tramite
  `Skyfield.searchlib.find_minima()`: entrano nel Calendario quando la
  separazione minima e' al massimo 6 gradi.
- La finestra delle congiunzioni planetarie richiede che entrambi i pianeti
  superino 8 gradi nella stessa notte locale; le opportunita' inferiori a 20
  minuti restano presenti ma sono marcate `Finestra breve`.
- Separate le congiunzioni col Sole come categoria informativa: titolo, stato,
  setup e consigli dichiarano che non sono target visuali e impediscono di
  suggerire strumenti ottici vicino al Sole.
- Il massimo di un'eclissi sotto l'orizzonte o in luce diurna non produce piu'
  una falsa finestra osservativa; il copy distingue il massimo dalle eventuali
  fasi iniziali o finali da verificare.
- Portato a v2 il contratto score-free `calendarOverview`: `usefulness` resta
  interno, le evidenze applicano una penalita' alla non visibilita' locale e le
  congiunzioni solari non occupano la preview osservativa Home.
- Il setup di un evento futuro non usa piu' il seeing della sessione corrente e
  riusa i dati reali del target quando disponibili.
- Collegati Calendario e card Home `Prossimi eventi` al nuovo contratto; la
  timeline mostra l'intero periodo selezionato e la Home apre direttamente il
  dettaglio dell'evento conservando la navigazione di ritorno.
- La preview Home mantiene 4/8 righe per il layout ma offre `Vedi tutti`; il
  Calendario conserva l'intero dataset annuale senza cap.
- Separati contatori e filtri per congiunzioni planetarie e solari, mantenendo
  lo stato locale al posto del numero grezzo nelle righe.
- Il dettaglio evento mostra separatamente istante, finestra, visibilita',
  priorita' descrittiva, separazione, setup e consigli; per una coppia offre un
  pulsante per ciascun pianeta e non usa piu' il fuorviante `per stasera`.
- Compattati i timing lunghi nella tessera data/ora e nascosta la finestra
  duplicata quando coincide gia' con il timing principale.
- Probe deterministico Addis Ababa: `82` eventi in circa `2,80 s` nel worker;
  50 fasi lunari, 5 opposizioni, 11 congiunzioni planetarie, 4 solari, 10
  sciami e 2 eclissi. La ricerca delle 21 coppie richiede meno di un secondo.
- Verificati `pip check`, ruff, compileall, smoke Python/QML, `qmllint` e
  rendering offscreen a 1600 e 960 px senza sovrapposizioni.
- Suite completa parallela: `716 passed`, `558 warnings`, `7 subtests passed`
  in `40,03 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota,
  ripetuta dalle ricerche astronomiche.
- Distribuzione non rigenerata: sorgente `1.20.0`, dist `1.18.8`.

## NightScope 1.19.0 - 2026-07-11

- Qualificati nel dettaglio i badge `Sessione consigliata`, `Sessione da
  monitorare` e `Sessione sconsigliata`, senza modificare i badge compatti e il
  contratto della Home.
- Corretto il testo lunare `Tutte le fasi tranne Luna piena` nel seed e tramite
  migrazione idempotente dei database che conservano il precedente refuso.
- Aggiunto il contratto read-only `observingObjectDetail` per il dettaglio
  aperto da Home/Calendario, mantenendo `selectedObject` invariato per il ramo
  Catalogo e per la compatibilita' esistente.
- Separati nel payload stato geometrico, stato Session, finestra utile, momento
  migliore, durata sopra soglia e setup specifico del target; nessuno score
  grezzo viene esposto dal nuovo contratto.
- Riutilizzata la geometria aggiornata ogni minuto dal worker Sky Compass per
  pianeti e deep sky selezionati.
- Corretto lo stato `Osservabile ora`: deep sky a 12 gradi non supera piu' la
  soglia utile di 15 gradi, mentre pianeti e Luna mantengono la soglia di 8.
- Allineato il runtime NSOM interno del dettaglio al raw target del read model e
  al telescopio scelto per il singolo oggetto nei profili multi-equipment.
- Collegato `ObjectDetailPage.qml` al nuovo contratto soltanto per Home e
  Calendario; il ramo Catalogo continua a usare il proprio payload raw.
- Distinti badge geometrico e stato Session, corretta la semantica della durata
  sopra soglia e sostituita la duplicazione `Finestra migliore` con il momento
  migliore reale.
- Nelle schede deep sky sostituiti i placeholder Sorge/Tramonta con inizio e
  fine della finestra utile; pianeti e Luna mantengono gli eventi reali.
- Resa completa la descrizione, trasformate le motivazioni in `Valutazione
  osservativa` state-aware e mantenuta invariata la sezione del ciclo lunare.
- Rimossa dalla pagina la card `Storico osservazioni`; persistenza e slot
  backend restano disponibili per una futura pagina `Log Osservazioni`.
- Reso responsive il blocco superiore: sotto 1180 px di area contenuto passa a
  una colonna, evitando la compressione dell'immagine e dei testi.
- Aggiunte regressioni sul nuovo contratto, sulle soglie, sulla selezione del
  target/setup, sui badge qualificati e sulla migrazione del testo lunare.
  Distribuzione non rigenerata: sorgente `1.19.0`, dist `1.18.8`.
- Verificati `pip check`, ruff, compileall, `qmllint`, rendering offscreen,
  `31` test mirati e suite completa parallela: `709 passed`, `27 warnings`,
  `7 subtests passed` in `32,32 s`.

## NightScope 1.18.8 - 2026-07-11

- Sostituita la vecchia card laterale di qualita' osservativa con un riepilogo
  compatto della Session NSOM: stato, finestra e fattore limitante provengono
  da `homeObservingOverview.session`, senza score o barra numerica legacy.
- Centrata verticalmente l'immagine dell'oggetto rispetto al blocco testuale
  nelle righe del piano osservativo consigliato.
- Reso naturale lo spareggio finale per nome nella lista Home: gli identificativi
  numerici seguono `M3, M40, M100` e la stessa regola supporta futuri nomi
  Caldwell come `C2, C14`.
- Spostata la legenda `Notte osservativa` nell'header della card di copertura
  nuvolosa, liberando spazio verticale per il grafico.
- Aggiunte regressioni sul contratto QML e sull'ordinamento naturale.
  Distribuzione Windows non rigenerata: sorgente `1.18.8`, dist `1.18.7`.
- Verificati `pip check`, ruff, compileall, `qmllint`, test mirati e suite
  completa parallela: `700 passed`, `27 warnings`, `7 subtests passed` in
  `41,25 s`.

## NightScope 1.18.7 - 2026-07-11

- Corretto l'ordinamento delle alternative Home: la chiave primaria e' ora
  l'inizio della finestra osservativa, non il `best_time` condiviso da molti
  oggetti crescenti verso l'alba.
- Conservati come spareggi il momento migliore, la categoria e il nome; il
  gruppo mostrato nello screenshot segue ora `M74, M76, M77, M45, M38, M37`.
- Distinta la selezione del dettaglio Meteo con accento cyan, lasciando il teal
  esclusivamente alla marcatura delle ore notturne.
- Rimossa la scrollbar orizzontale visibile dal selettore orario e ripristinata
  l'altezza compatta delle schede; lo scorrimento orizzontale resta attivo.
- Aggiunte regressioni su ordine a `best_time` condiviso e contratto QML.
  Distribuzione Windows non rigenerata: sorgente `1.18.7`, dist `1.18.6`.
- Verificati `pip check`, ruff, compileall, `qmllint`, test Home/Meteo/release e
  suite completa parallela: `699 passed`, `27 warnings`, `7 subtests passed` in
  `37,05 s`.

## NightScope 1.18.6 - 2026-07-11

- Aggiunta la property read-only `weatherNext24Hours`, che seleziona i campioni
  dall'ora locale corrente fino all'estremo esclusivo delle 24 ore successive.
- Annotato ogni campione visuale con `isObservingNight`, usando la stessa notte
  astronomica attiva di `observingWeatherHourly`.
- Riportati grafico della copertura nuvolosa e dettaglio orario a una previsione
  mobile di 24 ore; ore diurne neutre e ore notturne con accento teal.
- Conservata la selezione del dettaglio tramite timestamp durante il refresh
  all'inizio di ogni ora; su viewport stretti grafico e selettore scorrono
  orizzontalmente senza comprimere le etichette.
- Nessuna modifica a score, seeing, trasparenza, stato sessione o ranking NSOM:
  questi consumano ancora soltanto `observingWeatherHourly`.
- Aggiunte regressioni su finestra mobile, marcatura notturna e contratto QML;
  distribuzione Windows non rigenerata e ancora alla `1.18.4`.
- Verificati `pip check`, ruff, compileall, `qmllint`, rendering offscreen di
  `WeatherBars`/`WeatherPage` e suite completa parallela: `698 passed`,
  `27 warnings`, `7 subtests passed` in `32,92 s`.

## NightScope 1.18.5 - 2026-07-11

- Incluso sempre l'estremo astronomico esatto nella timeline di altitudine dei
  target, anche quando la cadenza da 15/30 minuti non coincide con l'alba;
  timeline e valori della diagnostica Luna-target restano invariati.
- Escluso il campione finale dalla scelta del momento migliore e interpolato il
  passaggio della soglia di altitudine tra campioni adiacenti.
- Rimosse le finestre Home a durata zero osservate nella `dist` `1.18.4`: nel
  probe Addis Ababa M44 passa da `18:48-18:48` a `18:48-18:57`, mentre
  M36/M37/M38/M42 terminano all'alba reale `06:12`.
- Aggiunte regressioni per estremo non allineato, singolo campione utile,
  target crescente fino all'alba e target che raggiunge la soglia soltanto al
  confine finale. Distribuzione Windows non rigenerata: resta `1.18.4`.
- Centralizzata la descrizione Bortle usata dalla Home: la classe 7 e' ora
  `transizione suburbana-urbana` sia nella card cielo profondo sia nel messaggio
  della lista, eliminando il contrasto `urbano`/`suburbano luminoso`.
- Verificati `pip check`, ruff, compileall, probe astronomico reale e suite
  completa parallela: `696 passed`, `28 warnings`, `7 subtests passed` in
  `37,14 s`; i warning sono la deprecazione Skyfield/NumPy gia' nota.

## NightScope 1.18.4 - 2026-07-11

- Trattati gli orari astronomici `HH:MM` come intervalli con precisione al
  minuto: quando il tramonto Skyfield contiene secondi, il relativo minuto non
  viene piu' escluso da Home e Planner.
- Impedito al Planner di sostituire un `best_time` coincidente con il tramonto
  con l'estremo finale della finestra dell'oggetto.
- Limitata la label della migliore finestra meteo all'alba locale esatta; un
  ultimo campione alle `06:00` con alba alle `06:12` termina ora alle `06:12`,
  non alle `07:00`.
- Aggiunte regressioni sul confine al secondo e sulla finestra meteo
  `04:00-06:12`. Distribuzione Windows non rigenerata.
- Spostato su worker anche il primo recupero Open-Meteo successivo allo snapshot
  astronomico: un avvio senza cache non occupa piu' il thread QML durante i
  timeout di rete.
- Mantenuto lo stato di caricamento generale fino all'applicazione del risultato
  meteo e conservata la continuazione attraverso un eventuale cambio notte.
- Sostituita la difficolta' unica dei pianeti con una policy per target e
  strumento: Mercurio, Marte, Urano e Nettuno considerano apertura e altezza e
  non vengono piu' classificati automaticamente `Facile` come Giove.
- Allineate anche le proiezioni binocolo, occhio nudo e telescopio senza oculari;
  la difficolta' risultante continua ad alimentare il vincolo pratico NSOM.
- Resi location-safe i completamenti AOD e OpenAQ: il cambio posizione rimuove
  subito la presentazione precedente e un risultato con chiave obsoleta viene
  scartato prima di riprogrammare il provider sulla localita' corrente.
- Impedito a un risultato OpenAQ gia' in volo di riapparire dopo rimozione o
  invalidazione delle credenziali.
- Aggiunta la property read-only `observingWeatherHourly` e collegati grafico e
  dettaglio Meteo ai soli campioni compresi nella notte astronomica attiva.
- Conservato `weatherHourly` come payload completo a 48 ore di compatibilita',
  senza piu' mostrarlo sotto il sottotitolo `finestra notturna`.
- Reso osservabile il fallback Sky Compass: un'eccezione della selezione NSOM
  produce ora un warning con traceback prima di usare il payload legacy
  invariato.
- Vincolato `botocore>=1.42.90,<1.43.1` per rispettare il requisito dichiarato
  da `aiobotocore 3.7.0`; riallineata la `.venv` a `botocore 1.43.0` e verificato
  `pip check` senza dipendenze rotte.
- Allineato il fixture minimale delle completion provider al nuovo controllo
  credenziali OpenAQ, mantenendo coperta l'indipendenza dei domini di refresh.
- Verificati `pip check`, ruff, compileall, `qmllint` e suite completa parallela:
  `690 passed`, `27 warnings`, `7 subtests passed` in `37,58 s`; i warning QML
  e Skyfield/NumPy sono quelli storici gia' noti. Distribuzione Windows non
  rigenerata: sorgente `1.18.4`, bundle ancora `1.18.3`.

## NightScope 1.18.3 - 2026-07-11

- Rimosso il limite residuo di dieci target dal condizionamento deep-sky per
  inquinamento luminoso: con contesto Bortle/VIIRS attivo restano applicati
  penalita', filtro di utilita' e ordinamento, ma il pool Home non viene piu'
  troncato prima dell'esclusione dei quattro oggetti del piano.
- Aggiunta una regressione che attraversa servizio condizioni, read-model,
  controller e payload `homeVisibleAlternatives` con sedici target e verifica
  che i dodici oggetti fuori dal piano raggiungano la Home.
- La lista Home `Altri oggetti visibili stasera` trattiene ora gli eventi di
  rotella di mouse e touchpad finche' il puntatore e' sulla lista scrollabile,
  anche quando raggiunge il primo o l'ultimo elemento; lo scroll della pagina
  resta disponibile fuori dalla lista o quando il contenuto entra interamente.
- Aggiunto un controllo del contratto QML del gestore annidato; verificati
  `qmllint`, test Home/release e caricamento offscreen dell'intera scena.
- Verificati ruff e compileall completi, smoke Python, QML smoke e suite
  parallela: `672 passed`, `27 warnings`, `7 subtests passed` in `33,58 s`;
  restano soltanto i warning Skyfield/NumPy gia' noti.
- Rigenerata su richiesta la distribuzione Windows `dist/NightScope` con
  PyInstaller `6.21.0`; verificati bundle `VERSION` `1.18.3`, presenza del nuovo
  gestore QML, smoke e QML smoke dell'eseguibile con exit code `0`.
- Ripristinati dopo build e smoke i cinque file runtime con confronto SHA-256;
  database finale `integrity_check=ok`, `user_version=6`. SHA-256 di
  `NightScope.exe`:
  `E849EEDB6CCE3A99E94DC74AAC7D0BF39F53F8AB0D95B2F74BC63EE511A2671E`.

## NightScope 1.18.2 - 2026-07-11

- Rimossa l'invalidazione della cache geometria Luna-target dallo snapshot
  diagnostico NSOM: Planner, AOD e OpenAQ riusano i dati della stessa posizione
  e notte senza ripetere calcoli Skyfield identici.
- Aggiunto `moon_geometry_batch`, che valuta tutti i target sulla stessa
  timeline notturna da 30 minuti e riusa osservatore e posizione apparente
  della Luna; il metodo singolo conserva la stessa semantica tramite il batch.
- Memorizzate le coordinate stellari Messier gia' risolte, evitando una nuova
  query SQLite per ogni tick geometrico.
- Spostato il refresh live Sky Compass da 60 secondi su worker daemon; request
  id e chiave posizione impediscono a risultati obsoleti di sostituire lo
  snapshot corrente.
- Serializzati gli accessi condivisi al motore astronomico tra Sky Compass,
  geometria lunare, catalogo, cambio notte e refresh completi.
- Spostati su worker anche i refresh astronomici freddi di avvio/localita', il
  cambio notte e il reload deep-sky successivo a VIIRS. Lo snapshot immutabile
  include notte osservativa, Sistema Solare, cielo profondo, Luna, eventi,
  geometria batch e visibilita' mensile del catalogo.
- Benchmark locale su 102 target: geometria Luna-target da circa `3,06 s` a
  `0,30 s`; Sky Compass a cache calda circa `0,15 s`. Il controller ritorna
  dall'inizializzazione in circa `0,22 s` e completa lo snapshot in background.
- Verificati ruff, compileall, smoke Python, QML smoke e suite completa
  parallela: `670 passed`, `7 subtests passed` in `31,14 s`; restano soltanto i
  warning Skyfield/NumPy gia' noti.
- Nessuna modifica a scoring, ranking, payload QML o UI visibile; distribuzione
  Windows non rigenerata e `dist/NightScope` ancora alla versione `1.18.0`.

## NightScope 1.18.1 - 2026-07-11

- Sostituita la notte fissa `18:00-07:00` con `ObservingNightWindow`, calcolata
  da Skyfield tra tramonto locale e alba successiva per la posizione attiva.
- Usato lo stesso intervallo per campionamento di pianeti e Messier, geometria
  lunare, `observable_now`, Sky Compass, Home e Planner.
- Gestiti esplicitamente giorno polare, buio continuo e indisponibilita' delle
  effemeridi, senza ricadere silenziosamente su una fascia oraria generica.
- Estesa da 24 a 48 ore la previsione Open-Meteo; la cache usa una nuova chiave
  `48h` e puo' ancora leggere la precedente chiave `24h` come fallback durante
  la transizione.
- Selezionate le ore meteo tramite timestamp locali completi dentro la notte
  astronomica, condividendole tra score globale, seeing/trasparenza, digest
  Home e stato della sessione.
- Impedito al selettore della migliore finestra di unire ore separate da un
  intervallo diurno; aggiunta la regressione esplicita per `05:00-22:00`.
- Resi i campioni della card Meteo rappresentativi dell'intera notte reale,
  anziche' legati agli orari fissi `20`, `22`, `00`, `02`, `04`.
- Allineati cronologia e label Planner alla posizione relativa del target nella
  notte; le opportunita' gia' trascorse non vengono riproposte durante una
  sessione in corso.
- Conservato l'avviso meteo Sky Compass anche nello stato senza target
  osservabili al momento.
- Aggiunta una cache per localita'/notte degli eventi solari Skyfield, evitando
  di ricalcolare tramonto e alba per ogni target e geometria lunare.
- Verificati ruff, compileall e suite completa: `658 passed`, `7 subtests
  passed`; restano solo i warning Skyfield/NumPy gia' noti.
- Nessuna modifica QML e nessuna rigenerazione della distribuzione Windows;
  `dist/NightScope` resta alla versione `1.18.0`.

## NightScope 1.18.0 - 2026-07-10

- Avviata la messa a punto della parte bassa Home con il riallineamento del
  contratto Planner/Equipment prima delle modifiche QML.
- Ridotto il piano sorgente a quattro `ObservationOpportunity`: la selezione
  avviene per valore NSOM e soltanto dopo viene applicato l'ordine cronologico.
- Conservato nel read-model Equipment interno lo strumento scelto per ciascun
  target e passato al Planner il telescopio corrispondente, evitando di usare
  sempre il primo telescopio assegnato al profilo.
- Evitata la contaminazione delle raccomandazioni binocolo/occhio nudo con
  apertura e focale di un telescopio non selezionato.
- Aggiunti test per limite a quattro, selezione del secondo telescopio del
  profilo e capability non-telescopio.
- Rimossi i limiti interni a 55 candidati dettagliati e 10 risultati dal
  catalogo Messier della Home: tutti gli oggetti sopra la soglia utile nella
  notte entrano ora nel pool condiviso.
- Esposta la property read-only `homeVisibleAlternatives`, ordinata per orario,
  con pianeti e cielo profondo unificati e le quattro tappe del piano escluse.
- Distinti sui target `visible` per la notte e `observableNow` per l'istante
  corrente, con altitudine/azimut numerici strutturati oltre alle label legacy.
- Reso Sky Compass indipendente dal ranking del piano: `inPlan` e `isBest`
  restano annotazioni/spareggi, mentre direzione e target usano
  `ObservableTargetValue`, altitudine corrente e densita' della zona.
- Il tick da 60 secondi continua anche quando nessun target e' osservabile al
  momento, cosi' una finestra che si apre piu' tardi riattiva automaticamente
  la bussola senza refresh pesanti.
- Benchmark locale sul catalogo corrente: 96 Messier utili calcolati in circa
  `0,6 s` e snapshot live aggiornato in circa `0,3 s`.
- Aggiunto il contratto read-only `homeNightPlanOverview` per la parte bassa
  Home: stato sessione, riepilogo quantitativo del profilo, piano compatto e
  lista alternativa unificata pronta per la tabella.
- Nei setup del piano il nome del telescopio compare solo quando il profilo ne
  contiene piu' di uno; motivazioni lunghe, score Planner e score legacy dei
  target non entrano nel nuovo payload Home.
- Gli stati `monitor` e `discouraged` non possono proiettare una falsa sequenza
  numerata anche se ricevono accidentalmente elementi Planner.
- Collegata la parte bassa `HomePage.qml` a `homeNightPlanOverview`: la card
  piano ora usa titolo, badge, messaggio, finestra e righe compatte dal
  contratto backend.
- Unificate le vecchie sezioni `Altri pianeti` e `Oggetti cielo profondo` in
  una tabella filtrabile `Altri oggetti visibili stasera`, senza score numerici
  o motivazioni Equipment lunghe.
- Il riepilogo profilo in Home usa il sommario multi-equipment backend, cosi'
  i profili con piu' telescopi non vengono ridotti al primo strumento.
- Aggiunti componenti QML dedicati per righe piano e tabella alternative.
- Rigenerata su richiesta la distribuzione Windows `dist/NightScope` con
  PyInstaller `6.21.0`; verificati bundle `VERSION` `1.18.0`, presenza dei
  nuovi QML Home, smoke test e QML smoke dell'eseguibile con exit code `0`.
- Preservati e ripristinati byte per byte database, backup e sidecar runtime;
  database finale con `integrity_check=ok` e `user_version=6`.

## NightScope 1.17.2 - 2026-07-10

- Aggiunto al log Open-Meteo lo status code degli errori HTTP, senza registrare
  coordinate o parametri della richiesta.
- Classificati come temporanei timeout, errori di rete, HTTP `408`/`425`/`5xx`
  e risposte non valide o vuote; il fallback continua a usare immediatamente
  l'ultima previsione disponibile.
- Programmato per gli errori temporanei un retry automatico dopo 5 minuti, con
  `force_refresh=True` per bypassare correttamente la TTL della cache.
- Evitato il retry breve per HTTP `4xx` permanenti e `429`, lasciando il normale
  controllo orario per errori client o rate limit.
- Aggiunti test provider/controller per logging status, classificazione,
  conservazione cache, timer breve e retry forzato.
- Nessuna modifica a scoring, ranking NSOM, soglie sessione, payload Home o QML.
- La distribuzione Windows non e' stata rigenerata in questo step.

## NightScope 1.17.1 - 2026-07-10

- Reso tollerante al normale jitter della posizione Windows il riuso delle
  cache provider NASA AOD e Black Marble VIIRS entro un raggio conservativo di
  500 metri.
- Mantenute invariate le chiavi esatte usate dal ciclo asincrono: la prossimita'
  e' applicata soltanto alla ricerca dei dati provider gia' salvati.
- Aggiunto un preflight sincrono della cache AOD prima di avviare il worker, in
  modo che una misura fresca non mostri uno stato di recupero e non autentichi
  Earthdata inutilmente.
- Ignorate le entry AOD con timestamp futuro e aggiunti test per riuso vicino,
  limite spaziale, cache persistente e assenza di rete su cache hit.
- Distinti nella parte alta Home gli stati di posizione `pending` e
  `unavailable`: durante il rilevamento automatico le card mostrano dati in
  attesa invece di dichiarare che la posizione non e' configurata.
- Rimossi i suggerimenti favorevoli planetari/deep-sky quando i relativi dati
  non esistono e corretta la sessione senza meteo ma con posizione valida.
- Abilitato il wrapping fino a due righe per sottotitoli e riepiloghi delle card
  superiori Home, mantenendo le dimensioni correnti e senza cambiare il layout.
- Nessuna modifica a scoring, ranking NSOM o formule AOD/OpenAQ; il contratto
  QML Home e' esteso soltanto con stati presentazionali additivi.
- Rigenerata la distribuzione Windows `dist/NightScope` con PyInstaller
  `6.21.0`; verificati `VERSION` `1.17.1`, QML Home aggiornato e smoke test
  dell'eseguibile con exit code `0`.
- Preservati e ripristinati byte per byte database, backup e sidecar runtime
  prima e dopo lo smoke; database finale con `integrity_check=ok` e
  `user_version=6`.

## NightScope 1.17.0 - 2026-07-10

- Aggiunto `HomeObservingOverviewService` con contratto
  `home_observing_overview_v1` per la parte alta della Home.
- Separati nel payload stato della sessione, indice meteo, diagnostiche NSOM di
  categoria planetaria/deep-sky e impatto lunare.
- Esposta e collegata al QML la property Qt read-only
  `homeObservingOverview`.
- Sostituiti nella parte alta Home il generico `Qualita' osservativa` e i due
  punteggi numerici di categoria con stato della sessione, score esplicitamente
  meteo e condizioni descrittive planetarie/deep-sky.
- Resi state-aware la finestra osservativa e gli stati senza dati; la scheda
  Luna descrive ora soltanto l'impatto lunare.
- Reso Sky Compass state-aware: con sessione non consigliata presenta una
  direzione geometrica di orientamento, non un invito a osservare.
- Localizzati i tipi target mostrati da Sky Compass e rese neutrali le relative
  motivazioni; aggiunta cautela esplicita anche senza dati meteo.
- Mantenuti invariati scoring, ranking e selezione target di Planner, Best
  Object, Home e Sky Compass, oltre ai payload NSOM diagnostici interni.
- Rigenerata la distribuzione Windows `dist/NightScope` con
  `packaging/build_windows.ps1`, preservando e verificando via SHA-256 database,
  backup e sidecar runtime gia' presenti.
- Verificati nel bundle `VERSION` `1.17.0`, QML Home aggiornato, integrita' del
  database e smoke test QML dell'eseguibile con exit code `0`.

## NightScope 1.16.1 - 2026-07-10

- Aggiunta una policy esplicita per la cache NASA Black Marble VIIRS: stati
  `missing`, `fresh` e `stale`, con rivalidazione in background ogni 7 giorni.
- Mantenuto il dato VIIRS stale come fallback immediato mentre viene cercato un
  prodotto mensile piu' recente; un errore NASA non cancella la stima salvata.
- Usato `SkyQualityEstimate.updated_at` come istante dell'ultimo recupero VIIRS
  riuscito, senza migrazioni o nuove colonne database.
- Esteso il pulsante Meteo `Aggiorna` ai controlli cache-aware VIIRS e AOD: una
  cache VIIRS fresca evita la rete e AOD conserva la propria TTL di 18 ore.
- Aggiunti test per cache VIIRS fresca, scaduta, malformata, rivalidazione,
  fallback su errore e integrazione del refresh manuale.
- Nessuna modifica a scoring, ranking NSOM, formule AOD/OpenAQ o payload QML.

## NightScope 1.16.0 - 2026-07-10

- Avviato il primo passaggio UI Meteo post-backend NSOM senza introdurre una
  UI NSOM-aware di ranking: nessun nuovo pannello NSOM e nessuna modifica a
  scoring, formule, refresh provider o ordinamenti.
- Rinominata la card Meteo AOD da `Trasparenza atmosferica` ad `Aerosol
  atmosferico`, con metrica `Effetto aerosol` e nuova freschezza della misura
  nel payload `atmosphericTransparency`.
- Rinominata la card OpenAQ da `Atmosfera locale` a `Particolato locale`, con
  label `Aria locale` e freschezza esposta accanto a PM2.5/PM10 e fonte.
- Distinta la `Trasparenza meteo` dalla misura AOD per evitare ambiguita' fra
  forecast, aerosol satellitare e ranking NSOM.
- Aggiunta `confidenceLabel` localizzata a `SkyQuality.to_qml()` mantenendo il
  campo grezzo `confidence` per compatibilita'.
- Aggiornati README, documenti tecnici e commenti provider: AOD/OpenAQ non sono
  piu' descritti come esclusivamente display-only, ma come dati condizioni che
  possono entrare nel backend solo quando gia' presenti e accettati dai gate.
- Rigenerata la distribuzione Windows con `packaging/build_windows.ps1` e
  verificato il bundle `dist/NightScope`: `VERSION` incorporato `1.16.0` e QML
  smoke test eseguito dall'eseguibile con exit code `0`.

## NightScope 1.15.2 - 2026-07-10

- Corretto `docs/NEXT_CHAT_HANDOFF.md` con l'hash effettivo del commit
  `d84de3a`, la review di ripartenza su `1.15.2`, la policy AOD/OpenAQ da
  valutare dopo uso reale e uno snapshot sintetico delle librerie `.venv`.
- Chiarito che `CelestialObject.score` / raw catalogue score resta un input
  backend Universe/read-model: non e' esposto come score nel Catalogo Oggetti
  Celesti e non coincide con lo score Home complessivo.
- Valutata la policy backend Catalogue/Universe raw score nello scope corrente:
  la separazione tra `IntrinsicTargetQuality`, metadata catalogo/provenance,
  osservabilita' catalogo, payload Home e ranking NSOM e' sufficiente; nessun
  nuovo `UniverseTargetProfile` runtime viene introdotto.
- Verificato il confine NSOM/QML: Planner, Home, Best Object e Sky Compass
  arrivano alla UI tramite payload esistenti, Detail/Object resta interno e la
  property read-only `advancedObservingNsom` non e' letta dai QML.
- Precisato che `Ready for visible UI redesign: False` indica solo assenza di
  una UI NSOM-aware progettata per spiegazioni/score/confidence/fonti, non un
  problema della UI compatibile attuale o del backend NSOM.
- Rimosso il set storico di report, generatori e test di migrazione NSOM ormai
  sostituito da `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md` e
  `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`.
- Snellita la documentazione base: `README.md`, `docs/ARCHITECTURE.md`,
  `docs/CALCULATION_LOGIC.md` e `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
  descrivono lo stato corrente invece di duplicare il diario completo della
  migrazione.
- Mantenuti runtime NSOM, test comportamentali attivi, read-model e boundary
  Observer/ObservationConditions/Equipment.
- Nessun cambio a scoring, QML/UI, provider, logging, rete o scritture runtime.

## NightScope 1.15.1 - 2026-07-10

- Aggiunto `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`, audit statico per
  distinguere codice/documentazione NSOM runtime da report, tool e test storici
  di migrazione ormai sostituibili dal closeout backend.
- Definito il perimetro del cleanup `1.15.2`: mantenere core/runtime/test
  comportamentali e documentazione base, rimuovere generatori/report storici e
  test che validano solo quei report.
- Nessun cambio runtime, scoring, QML/UI, provider, logging, rete o scritture
  runtime.

## NightScope 1.15.0 - 2026-07-10

- Aggiunto `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`, closeout developer-only
  dello stato backend NSOM dopo lo switch AOD/OpenAQ default-on.
- Dichiarate chiuse per lo scope corrente le superfici backend NSOM:
  Planner, Home `recommendedDeepSky`, Best Object, Advanced Observing backend,
  Sky Compass e Detail/Object internal payload.
- Confermato che AOD/OpenAQ resta default-on con rollback esplicito tramite
  `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)` e che
  confidence/provider confidence restano metadata.
- I residui sono non bloccanti: monitoraggio AOD/OpenAQ reale prima di tuning,
  policy futura Catalogue/Universe raw score e design futuro di spiegazioni UI.
- Nessun cambio runtime, scoring, QML/UI, logging, rete o scritture runtime in
  questo closeout.

## NightScope 1.14.19 - 2026-07-10

- Abilitato di default il path AOD/OpenAQ calibrato:
  `ObservationConditionFeatureFlags.experimental_aerosol_scoring` ora vale
  `True`.
- Aggiunto `docs/NSOM_AOD_OPENAQ_DEFAULT_ON_SWITCH.md`, report developer-only
  che documenta review 1.14.18 accettata, rollback esplicito tramite
  `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`,
  confidence neutrality e assenza di wiring runtime/QML.
- Nessuna formula, peso, provider call, UI/QML, logging o scrittura runtime e'
  stata aggiunta: l'effetto runtime compare solo quando i dati AOD/OpenAQ sono
  gia' disponibili e passano i gate provider-quality.
- Planner/Home/Best Object/Advanced Observing/Sky Compass/Detail/Equipment non
  sono stati modificati direttamente; ricevono solo il normale output
  condition-adjusted quando usano `ObservationConditionsService`.

## NightScope 1.14.18 - 2026-07-10

- Aggiunto `docs/NSOM_AOD_OPENAQ_STALE_CURRENT_REPLAY_AUDIT.md`, audit
  developer-only che rilegge il probe reale espanso e tratta gli stessi AOD
  `stale` come `current` solo nel replay offline.
- Il replay conferma che il peso `stale=0.5` e' una policy conservativa
  ragionevole: l'effetto AOD current raddoppia circa rispetto a stale, ma resta
  entro scala moderata (`-7.38` massimo deep-sky) e mantiene pianeti/Luna quasi
  neutrali (`-0.277` massimo solar-system).
- OpenAQ PM fallback e rami `none` restano invariati nel replay; confidence e
  provider confidence restano metadata e non entrano nello score.
- Nessun default-on in questo commit: `experimental_aerosol_scoring` resta
  `False`, senza QML/UI, logging, rete, scritture runtime o modifiche a
  Planner/Home/Best Object/Advanced Observing/Sky Compass/Detail/Equipment.

## NightScope 1.14.17 - 2026-07-10

- Aggiunto `docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_READINESS_AUDIT.md`, audit
  developer-only che rilegge il probe reale espanso senza rete e senza
  abilitare `experimental_aerosol_scoring`.
- Il nuovo audit accetta coverage reale, source policy, fallback OpenAQ,
  casi provider a effetto zero, safety runtime/credentiali e scala reale del
  modifier: il massimo effetto deep-sky resta modesto e maggiore di quello su
  pianeti/Luna.
- Il default-on AOD/OpenAQ resta bloccato da evidenza temporale insufficiente:
  nel probe checked-in tutti gli AOD utilizzabili sono `stale` e manca una
  seconda esecuzione provider su data/orario diverso.
- Nessun cambio runtime, QML/UI, Planner, Home, Best Object, Advanced
  Observing, Sky Compass, Detail/Object, Equipment, logging, rete o scritture
  runtime. Il flag aerosol resta `False`.

## NightScope 1.14.16 - 2026-07-10

- Esteso il probe reale AOD/OpenAQ a un set `expanded` da 15 localita':
  Bologna, San Pedro de Atacama, New Delhi, Mauna Kea, Addis Ababa, Cairo,
  Marrakech, Mexico City, Los Angeles, Beijing, Tokyo, Singapore, Sydney,
  Cape Town e Reykjavik.
- Aggiornato `docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md` con conteggio
  localita', set usato e ragioni policy AOD/OpenAQ per ogni localita', cosi'
  la review vede perche' una sorgente diventa `aod`, `particulate` o `none`.
- Confermato su dati provider reali ampliati che il flag off resta neutro, che
  i rami `aod`, `particulate` e `none` sono tutti osservati, e che le penalita'
  deep-sky restano maggiori di pianeti/Luna quando il flag sperimentale viene
  abilitato manualmente.
- Aggiunti test offline per il set espanso e per il report checked-in, senza
  rendere il probe provider-backed parte della suite automatica.
- Nessun default-on e nessun wiring runtime/QML: AOD/OpenAQ resta un path
  esplicito developer-only fino alla review.

## NightScope 1.14.15 - 2026-07-10

- Aggiunto `astro_viewer/tools/nsom_aod_openaq_real_provider_probe.py`, probe
  developer-only esplicito per usare NASA Earthdata AOD e OpenAQ reali su cinque
  localita' miste senza wiring runtime/QML e senza salvare credenziali nei
  report.
- Generato `docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md`: Bologna, San Pedro de
  Atacama, New Delhi, Mauna Kea e Addis Ababa coprono rami policy `none`, `aod`
  e `particulate`.
- Confermato con dati provider reali che il flag off resta neutro, OpenAQ PM e'
  fallback non additivo, AOD policy-eligible resta primario e i target deep-sky
  ricevono penalita' maggiori di pianeti/Luna quando il flag sperimentale viene
  abilitato manualmente.
- Corretto il parser locale di `nasa_login.txt` per preservare apostrofi finali
  nelle password e per non confondere username/password OpenAQ con Earthdata.
- Nessun default-on: `experimental_aerosol_scoring` resta `False`; il prossimo
  passo e' review umana del report reale prima di decidere lo switch.

## NightScope 1.14.14 - 2026-07-10

- Aggiunto `docs/NSOM_AOD_OPENAQ_FIELD_CALIBRATION.md`, report
  developer-only con fixture deterministiche field-like per validare la scala
  AOD/OpenAQ calibrata senza abilitare il default-on.
- Aggiunto `astro_viewer/tools/nsom_aod_openaq_field_calibration.py` con scenari
  per aria pulita, foschia moderata, AOD alto deep-sky, target solari protetti,
  OpenAQ PM fallback, AOD stale e provider respinti/context-only.
- Le fixture rientrano nelle bande attese: aria pulita e provider respinti sono
  neutrali, deep-sky e' piu' sensibile di pianeti/Luna, PM locale resta piu'
  debole di AOD alto.
- Il default-on resta disabilitato: la scala e' accettabile per una review di
  switch stretto, ma la decisione finale resta accettazione umana o raccolta di
  osservazioni reali.
- Nessun cambio Planner, Home, Best Object, Advanced Observing, Sky Compass,
  Detail/Object, Equipment, QML/UI, logging, rete o scritture runtime.

## NightScope 1.14.13 - 2026-07-10

- Aggiunto `docs/NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS.md`, audit
  developer-only per decidere se il path AOD/OpenAQ calibrato e default-off sia
  pronto a un futuro switch default-on.
- Aggiunto `astro_viewer/tools/nsom_aod_openaq_default_on_readiness.py` con gate
  espliciti per provider-quality, source ownership, formula shape, confidence
  neutrality, safety runtime e scala aerosol.
- Confermato che provider-quality, AOD-primary/OpenAQ-fallback, confidence
  neutrality e formula shape sono accettati; il default-on resta bloccato solo
  da `aerosol_score_scale`.
- Aggiornato l'audit backend complessivo per includere il nuovo report e
  puntare la prossima review a 1.14.13.
- Nessun cambio runtime: `experimental_aerosol_scoring` resta `False`, nessuna
  esposizione QML/UI, logging, rete, file write runtime o cambio Planner/Home/
  Best Object/Advanced Observing/Sky Compass/Detail/Object/Equipment.

## NightScope 1.14.12 - 2026-07-10

- Calibrata in modo mirato la formula aerosol AOD/OpenAQ sperimentale e
  default-off: il `penalty_cap` di classe target viene interpretato come perdita
  massima di trasparenza (`penalty_cap / 100`) e il modifier compatibile viene
  derivato da `target.score * transparency_loss`.
- Aggiunti `max_transparency_loss` e `transparency_loss` a
  `AerosolScoringBreakdown`, mantenendo AOD primario, OpenAQ PM fallback locale
  piu' debole e `RecommendationConfidence` fuori dallo score.
- Risolto il blocker `penalty-cap-vs-transparency-shape`; resta bloccante per
  un eventuale default-on solo la validazione umana della scala aerosol.
- Rigenerati i report developer-only AOD/OpenAQ e aggiornato l'audit backend
  complessivo per puntare la prossima review a 1.14.12.
- Nessun cambio runtime default: `experimental_aerosol_scoring` resta `False`,
  quindi Planner, Home, Best Object, Advanced Observing, Sky Compass,
  Detail/Object, Equipment, QML/UI, logging, rete e scritture runtime non
  cambiano.

## NightScope 1.14.11 - 2026-07-10

- Aggiunto `docs/NSOM_AOD_OPENAQ_CALIBRATION_AUDIT.md`, report
  developer-only per verificare la formula aerosol AOD/OpenAQ default-off senza
  abilitare scoring runtime o modificare pesi.
- Aggiunto `astro_viewer/tools/nsom_aod_openaq_calibration_audit.py` con
  scenari deterministici per target class, AOD fresco/stale, OpenAQ PM fallback,
  sorgenti respinte, prodotto AOD con confidence diversa e target protetti
  pianeta/Luna.
- Confermata la direzione della formula 1.14.9: AOD resta primario quando passa
  i gate provider-quality, OpenAQ PM locale resta fallback piu' debole, dati
  storici/context-only restano neutrali e `RecommendationConfidence` non entra
  nello score.
- Identificati due blocker di calibrazione prima di un eventuale default-on:
  scala assoluta del modifier aerosol e forma penalty-cap/transparency; il
  rounding dei modifier piccoli su pianeti/Luna e' documentato come nota non
  bloccante.
- Aggiornato l'audit backend complessivo per includere il nuovo report e
  puntare la prossima review a 1.14.11.
- Nessun cambio runtime, scoring default, Planner, Home, Best Object, Advanced
  Observing, Sky Compass, Detail/Object, Equipment, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.14.10 - 2026-07-10

- Aggiunta configurazione `pytest.ini` per limitare la discovery a
  `astro_viewer/tests`, escludere cartelle pesanti come `.venv`, `build` e
  `dist`, e registrare marker developer-only.
- Aggiunto `requirements-dev.txt` con `pytest-xdist` per rendere riproducibile
  la full suite parallela.
- Aggiunto `docs/TESTING.md` con workflow consigliato: `compileall
  astro_viewer`, test focused per area, full suite parallela con `pytest -q -n
  auto` e fallback seriale.
- Misurata la full suite su Windows: seriale circa `0:06:06`, parallela circa
  `0:01:14`, entrambe con `1036 passed, 7 subtests passed`.
- Nessun cambio runtime, NSOM scoring, QML/UI, provider, logging o file write
  runtime.

## NightScope 1.14.9 - 2026-07-10

- Implementato il primo path di scoring aerosol AOD/OpenAQ come esperimento
  interno e default-off: `ObservationConditionFeatureFlags.experimental_aerosol_scoring`
  resta `False` di default.
- Aggiunta `AerosolScoringBreakdown` e formula target-specific in
  `ObservationConditionsService`: AOD policy-eligible e' primario, OpenAQ PM
  locale e' fallback piu' debole, freshness e' input esplicito, e il modifier e'
  cappato per classe target.
- Mantenuta la neutralita' del runtime normale: con flag spento i modifier AOD e
  PM restano `0.0`, i `CelestialObject` originali non vengono mutati e non ci
  sono cambi Planner, Home, Best Object, Advanced Observing, Sky Compass,
  Detail/Object, Equipment o QML/UI.
- Aggiornati i report developer-only
  `docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md`,
  `docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md` e
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md`; aggiunto
  `docs/NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT.md`.
- Aggiunti test per formula AOD/PM, source precedence, default-off neutrality,
  protezione pianeti/Luna, rejection provider non eleggibili, confidence
  score-neutral e assenza di wiring runtime/QML dei report.

## NightScope 1.14.8 - 2026-07-09

- Aggiunto `docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md`, report
  developer-only che formalizza le policy provider-quality per NASA AOD e OpenAQ
  prima di qualsiasi scoring aerosol.
- Aggiunto `AerosolProviderQualityPolicyService` con decisioni immutabili per:
  AOD freshness, valore finito, uncertainty, QA raw traceability, pixel locali;
  OpenAQ freshness, distanza locale e rappresentativita'; source precedence e
  regole anti double-counting.
- Estesi gli input diagnostici interni con uncertainty/QA/method/pixel AOD e
  distanza OpenAQ strutturata. Il payload QML resta invariato.
- Aggiornato `docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md`: i blocker policy
  1.14.7 sono risolti come gate espliciti, quindi il prossimo passo puo' essere
  un esperimento aerosol default-off.
- Nessuno scoring e' stato abilitato: `experimental_aerosol_scoring` resta
  `False`, la formula non e' implementata e il modifier resta `0.0`.
- Nessun cambio Planner, Home, Best Object, Advanced Observing, Sky Compass,
  Detail/Object, Equipment, QML/UI, logging, rete o scritture runtime.

## NightScope 1.14.7 - 2026-07-09

- Aggiunto `docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md`, audit
  developer-only per valutare se NASA AOD e OpenAQ PM2.5/PM10 sono pronti a
  entrare nello scoring NSOM.
- Confermato che AOD/OpenAQ restano score-neutral: `experimental_aerosol_scoring`
  resta `False` di default e `intended_aerosol_modifier(...)` produce ancora
  `0.0` anche con flag sperimentale forzato.
- Documentate freshness e source precedence: AOD fresco/recent/stale e' il
  candidato primario di aerosol column, OpenAQ PM e' fallback/context quando
  AOD non e' utile o e' storico.
- Bloccata ogni abilitazione scoring finche' non vengono risolti formalmente
  AOD QA/uncertainty, rappresentativita' locale OpenAQ e double-counting con
  VIIRS sky background, meteo/transparency e geometria lunare.
- Nessun cambio runtime, QML/UI, logging, rete o scrittura runtime; Planner,
  Home, Best Object, Advanced Observing, Sky Compass, Detail/Object ed
  Equipment non cambiano.

## NightScope 1.14.6 - 2026-07-09

- Abilitata di default la geometria lunare nel Planner NSOM tramite
  `NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED = True`.
- Lo switch e' stretto al Planner: il default globale
  `ObservationConditionFeatureFlags.experimental_moon_geometry_scoring` resta
  `False`, quindi i modifier generici di `ObservationConditionsService`,
  AOD/OpenAQ e gli altri consumer non vengono abilitati implicitamente.
- Il Planner ora costruisce la mappa `moon_geometry_by_object_id` di default
  quando la location e i target permettono il calcolo locale; la geometria
  modifica solo `ObservationEnvironment.lunar_sky_background`.
- Preservato rollback esplicito via
  `NightPlannerService(nsom_scoring_service=PlannerNsomScoringService(feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=False)))`.
- Aggiornati report e test di readiness/calibrazione per distinguere default
  Planner attivo, rollback illumination-only e provider-backed AOD/OpenAQ
  ancora fuori scope.
- Nessun QML/UI, logging, rete o scrittura runtime; Home, Best Object, Sky
  Compass, Advanced Observing, Detail/Object ed Equipment non cambiano.

## NightScope 1.14.5 - 2026-07-09

- Aggiunto `docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md`, audit
  developer-only per decidere se il path Planner Moon geometry e' pronto per
  uno switch default-on separato.
- L'audit usa i dati del report 1.14.4 e classifica come accettati i guardrail:
  deep-sky peggiora con Luna alta/vicina, migliora quando la Luna e' lontana o
  fuori finestra, pianeti/Luna restano protetti, geometria mancante conserva il
  baseline illuminazione-only.
- Confermato che l'effetto resta nel boundary Sky
  `ObservationEnvironment.lunar_sky_background` e che
  `RecommendationConfidence` resta metadata score-neutral.
- Il default runtime resta off: `NightPlannerService` non usa ancora la
  geometria lunare senza uno switch esplicito successivo.
- Nessun cambio a Planner ranking di default, Home, Best Object, Sky Compass,
  QML/UI, logging, rete o scritture runtime.

## NightScope 1.14.4 - 2026-07-09

- Aggiunto `docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md`, report
  developer-only per confrontare il Planner NSOM default con il path
  sperimentale `experimental_moon_geometry_scoring=True`.
- Coperti scenari deterministici per pianeta, Luna, galassia, nebulosa diffusa,
  ammasso aperto e ammasso globulare con geometria mancante, Luna tramontata
  prima della finestra, Luna bassa/vicina, Luna alta/vicina e Luna alta/lontana.
- Confermato che l'effetto sperimentale resta confinato a
  `ObservationEnvironment.lunar_sky_background`: ObserverCapability,
  SessionViability, timing, practical constraints e confidence non entrano nel
  percorso matematico dello score.
- Corretta la metadata confidence del Planner: `moon_geometry_confidence`
  indica la disponibilita' reale di `MoonGeometryConditionInput`, non la sola
  presenza di `MoonSummary`.
- Nessun cambio al default runtime, nessun QML/UI, nessun logging, rete o
  scrittura runtime; il report resta tooling esplicito per sviluppatori.

## NightScope 1.14.3 - 2026-07-09

- Aggiunto il path sperimentale/default-off per usare la geometria lunare nel
  Planner NSOM.
- `PlannerNsomScoringService` accetta `MoonGeometryConditionInput` e, solo con
  `experimental_moon_geometry_scoring=True`, usa il fattore geometrico nel
  componente Sky `ObservationEnvironment.lunar_sky_background`.
- `NightPlannerService` puo' ricevere una mappa opzionale
  `moon_geometry_by_object_id`; `AppController` la costruisce solo se il
  servizio Planner dichiara il flag attivo, quindi il runtime default non
  aggiunge calcoli lunari al planning normale.
- Pianeti e Luna restano protetti dai danni di background lunare tramite i
  profili NSOM esistenti; `RecommendationConfidence` resta metadata e non entra
  nello score.
- Aggiornato `docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md` per distinguere
  diagnostica runtime disponibile, path Planner sperimentale e default runtime
  invariato.

## NightScope 1.14.2 - 2026-07-09

- Aggiunta `MoonGeometrySummary`, DTO runtime locale per diagnostica Luna-target:
  altezza Luna, separazione angolare Luna-target, Luna sopra orizzonte, overlap
  con la finestra target e policy di campionamento bounded start/mid/best/end.
- Implementato `SkyfieldAstronomyEngine.moon_geometry(...)` usando location,
  tempo locale ed effemeridi gia' disponibili; nessun provider esterno, meteo,
  VIIRS, AOD o OpenAQ viene richiesto.
- Collegata la geometria lunare alla snapshot diagnostica NSOM come metadata
  score-neutral: `moon_geometry_available`, campi runtime target,
  `moon_geometry_future_factor` e `moon_geometry_score_effect = 0.0`.
- Mantenuto invariato lo scoring: `experimental_moon_geometry_scoring` resta
  neutrale, Planner/Home/Best Object/Sky Compass/Detail/Equipment non cambiano
  ranking o output QML.
- Aggiornato il report developer-only
  `docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md` da readiness futura a
  diagnostica runtime disponibile, con marker statici e test JSON strict.

## NightScope 1.14.1 - 2026-07-09

- Aggiunto `docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md`, audit
  developer-only che separa le fonti dati NSOM tra input locali sempre
  disponibili dopo la location, input locali opzionali e provider esterni
  opzionali.
- Documentato che la location e le effemeridi locali bastano per calcolare
  geometria Luna-target senza meteo, VIIRS, AOD, OpenAQ o profilo equip.
- Mappati i campi Luna correnti: fase, illuminazione e phase angle sono gia'
  disponibili; altezza Luna, separazione Luna-target, Luna sopra orizzonte e
  overlap con la finestra target sono predisposti come input futuri
  score-neutral.
- Confermato che l'attuale scoring usa illuminazione lunare e background Luna,
  mentre `experimental_moon_geometry_scoring`, AOD NASA e OpenAQ restano
  neutrali rispetto allo score.
- Nessun cambio a runtime, scoring, Planner, Home, Best Object, Advanced
  Observing, Sky Compass, Detail/Object, Equipment, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.14.0 - 2026-07-09

- Aggiunto `docs/NSOM_UNIVERSE_TARGET_PROFILE_POLICY.md`, report
  developer-only che decide se introdurre ora un `UniverseTargetProfile`
  runtime dopo l'audit raw score 1.13.9.
- Decisione: non introdurre ora un nuovo DTO runtime. `IntrinsicTargetQuality`
  e l'adapter corrente restano il boundary Universe interno; un
  `UniverseTargetProfile` verra' considerato solo quando servono provenance
  esplicita, nuovi cataloghi, calibrazione intrinseca o spiegazioni visibili.
- Definito il contratto futuro del profilo Universe: `object_id`,
  `target_class`, `intrinsic_score_seed`, `score_provenance`,
  `geometry_summary`, `magnitude_and_size` e separazione dei campi score
  presentation-only.
- Confermati come non attivi i criteri di ingresso per implementarlo:
  calibrazione intrinseca, sorgenti catalogo multiple, explanation UI,
  rimozione dei payload score compatibili e modello surface-brightness.
- Nessun cambio a runtime, scoring, Planner, Home, Best Object, Advanced
  Observing, Sky Compass, Detail/Object, Equipment, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.13.9 - 2026-07-09

- Aggiunto `docs/NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY_AUDIT.md`, audit
  developer-only del confine tra `CelestialObject.score`, catalogo/prepared
  objects, `IntrinsicTargetQuality` e campi score di compatibilita' payload.
- Classificato `CelestialObject.score` come seme Universe/IntrinsicTargetQuality
  provvisorio e compatibile, non come score NSOM finale da calibrare
  direttamente.
- Confermata la separazione raw/display introdotta da ObservationConditions:
  gli input NSOM usano il target raw, mentre lo score display resta
  compatibilita' QML/presentazione.
- Documentati i residui futuri non bloccanti: provenance esplicita del raw
  score/catalogo, eventuale `UniverseTargetProfile` e semantica visibile degli
  score.
- Nessun cambio a runtime, scoring, Planner, Home, Best Object, Advanced
  Observing, Sky Compass, Detail/Object, Equipment, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.13.8 - 2026-07-09

- Rimossi i rollback runtime interni per Planner, Home `recommendedDeepSky`,
  Best Object, Advanced Observing backend, Sky Compass e Detail/Object internal
  payload.
- `AppController` non accetta piu' i parametri `use_nsom_*`; `NightPlannerService`
  non accetta piu' `use_nsom_planner_scoring`.
- I path NSOM default-on restano l'unica selezione runtime per le superfici gia'
  migrate; i fallback tecnici per sky quality mancante o failure del servizio
  Sky Compass restano fallback dati, non rollback configurabili.
- Aggiornati audit/report backend, legacy, overall e rollback cleanup per
  registrare la rimozione e mantenere traccia storica dei rollback rimossi.
- Nessuna esposizione QML/UI, logging, rete o scrittura runtime aggiunta.

## NightScope 1.13.7 - 2026-07-09

- Aggiunto `docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md`, audit
  developer-only per decidere la policy dei rollback legacy interni rimasti dopo
  i closeout backend NSOM.
- Decisione policy: rimuovere in un prossimo step focalizzato i rollback
  interni di Planner, Home `recommendedDeepSky`, Best Object, Advanced
  Observing backend, Sky Compass e Detail/Object internal payload.
- Motivazione: l'app non e' distribuita, i rollback sono interni e non un
  contratto pubblico, mentre le superfici backend NSOM risultano chiuse.
- Aggiornati gli audit backend/legacy/overall per indicare come prossimo step
  la review `1.13.7` e poi la rimozione dei rollback interni in `1.13.8`.
- Nessun flag viene rimosso in questo commit e nessun runtime, scoring, QML/UI,
  logging, rete o scrittura runtime cambia.

## NightScope 1.13.6 - 2026-07-09

- Aggiunto `docs/NSOM_OVERALL_BACKEND_READINESS_AUDIT.md`, audit
  developer-only complessivo dello stato NSOM backend dopo il closeout
  Equipment.
- L'audit conferma Planner, Home `recommendedDeepSky`, Best Object, Advanced
  Observing backend, Sky Compass e Detail/Object come superfici NSOM chiuse,
  Equipment come servizio setup-local NSOM-bounded, ObservationConditions come
  boundary compatibile chiuso, e Sky Map/Notifications come legacy rimosso.
- Classificati i residui non bloccanti: rollback legacy interni, campi payload
  legacy/base per compatibilita' QML, cache ObservationConditions e score raw
  catalogo/Universe.
- Prossimo step consigliato: review 1.13.6 e audit policy per cleanup dei
  rollback interni prima di qualunque lavoro UI/explanation visibile.
- Nessun cambio a runtime, scoring, Planner, Home, Best Object, Advanced
  Observing, Sky Compass, Detail/Object, Equipment, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.13.5 - 2026-07-09

- Aggiunto `docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md`, closeout
  developer-only della serie Equipment NSOM.
- Marcata la migrazione Equipment come
  `equipment_nsom_migration_closed_setup_local`: `EquipmentService` resta il
  runtime setup recommender, mentre `ObserverCapability/Q_target`, presenter
  boundary, score ownership e score component boundary restano confini NSOM
  espliciti.
- Aggiornati gli audit backend/legacy e i report Equipment per indicare che
  non serve un path Equipment NSOM default-off ora; il prossimo passo e'
  scegliere la prossima area backend NSOM o fare un audit complessivo.
- Nessun cambio a ranking Equipment, selection score, Planner, Home, Best
  Object, Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete
  o scritture runtime.

## NightScope 1.13.4 - 2026-07-09

- Aggiunto `docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md`, audit
  developer-only sulla necessita' di un path Equipment NSOM default-off.
- Decisione policy: non aggiungere ora un replacement path Equipment; mantenere
  `EquipmentService` come servizio setup-local con boundary NSOM espliciti.
- Motivazione: `Q_target` e `PracticalTargetValue` non sostituiscono scelta
  oculare, posizione zoom, Barlow, binocolo, fallback e compatibilita' payload.
- Aggiornati gli audit backend/legacy: Equipment passa a
  `equipment_default_off_path_policy_set_setup_local`; il prossimo step e'
  review 1.13.4 e closeout 1.13.5 della migrazione Equipment.
- Nessun cambio a ranking Equipment, selection score, Planner, Home, Best
  Object, Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete
  o scritture runtime.

## NightScope 1.13.3 - 2026-07-09

- Introdotto `EquipmentSetupScoreReadModel`, boundary immutabile dei componenti
  reali di `EquipmentService._configuration_score`.
- `EquipmentService._configuration_score(...)` ora somma gli stessi componenti
  tramite il read-model e restituisce lo stesso score finale clampato 0-100.
- `EquipmentNsomComparisonService` usa il read-model per il breakdown legacy,
  eliminando la duplicazione diagnostica della formula.
- Aggiunto `docs/EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY.md`, report
  developer-only con parity check su score e componenti.
- Aggiornati gli audit backend/legacy: Equipment passa a
  `equipment_setup_score_component_boundary_introduced`; il prossimo step e'
  una review 1.13.3 seguita da audit policy su un eventuale path Equipment
  default-off.
- Nessun cambio a ranking Equipment, selection score, Planner, Home, Best
  Object, Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete
  o scritture runtime.

## NightScope 1.13.2 - 2026-07-09

- Aggiunto `docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md`, audit
  developer-only della formula reale
  `EquipmentService._configuration_score`.
- L'audit classifica i componenti `angular_scale`, `magnification`,
  `exit_pupil`, `light_gathering`, `seeing_compatibility` e `handling` per
  ownership NSOM e policy di replacement.
- Confermato che lo score Equipment miscela target traits, configurazione
  osservatore, sky quality, seeing e praticita' di setup in uno score locale;
  non e' `ObservableTargetValue`, `PracticalTargetValue`, `Q_target` o
  `RecommendationConfidence`.
- Aggiornati gli audit backend/legacy: Equipment passa a
  `equipment_setup_score_ownership_audited`; il prossimo step consigliato e'
  un read-model dei componenti dello score con parity test stretti.
- Nessun cambio a scoring Equipment, ranking, selection score, Planner, Home,
  Best Object, Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging,
  rete o scritture runtime.

## NightScope 1.13.1 - 2026-07-09

- Introdotto il boundary runtime-neutral
  `astro_viewer/app/services/equipment_setup_read_model.py` per separare il
  payload setup prodotto da `EquipmentService` dalla projection verso
  `CelestialObject`.
- `AppController._apply_equipment(...)` continua a chiamare
  `EquipmentService.suggest_for_profile(...)`, ma ora passa dal read-model
  immutabile prima di copiare `recommended_setup`, `setupOptions`,
  `difficulty`, `barlow` ed explanation nei target display.
- Il read-model preserva il payload EquipmentService, supporta fallback senza
  inventare chiavi, resta JSON strict-compatible e non espone campi NSOM/QML.
- Aggiornati gli audit Equipment/backend/legacy: Equipment passa a
  `equipment_setup_read_model_boundary_introduced`; il replacement dello score
  Equipment resta rinviato a una review di ownership dei componenti di setup.
- Nessun cambio a ranking Equipment, selection score, Planner, Home, Best
  Object, Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete
  o scritture runtime.

## NightScope 1.13.0 - 2026-07-09

- Aggiunto `docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md`, audit
  developer-only del contratto presenter Equipment prima di qualunque
  replacement runtime.
- L'audit registra payload, `setupOptions`, fallback, `selectionScore`, uso
  reference-only di `Q_target` e neutralita' di `RecommendationConfidence`.
- Aggiornati gli audit backend/legacy: Equipment passa da semplice
  `observer_adapter_extracted` a `equipment_presenter_contract_audited`, ma il
  runtime helper `EquipmentService.suggest_for_profile(...)` resta invariato.
- Il prossimo step consigliato e' estrarre un DTO/read-model presenter Equipment
  runtime-neutral, preservando forma payload e QML esistenti.
- Nessun cambio a raccomandazioni Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.12.12 - 2026-07-09

- Chiusa la serie ObservationConditions consumer reroute dopo la review dello
  split adapter Sky Compass 1.12.11.
- Gli audit ora registrano Home recommendedDeepSky, Best Object e Sky Compass
  come consumer reroutati sui boundary raw/display corretti.
- `docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md`,
  `docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md`,
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` e
  `docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md` sono stati rigenerati dai tool
  developer-only.
- Il prossimo lavoro backend consigliato e' la review del presenter contract
  Equipment, ora che la migrazione raw-target ObservationConditions e' stabile.
- Nessun cambio a ranking, QML/UI, Planner, Home, Best Object, Sky Compass,
  logging, rete o scritture runtime.

## NightScope 1.12.11 - 2026-07-09

- Implementato il runtime split adapter Sky Compass definito in 1.12.10.
- Il ramo NSOM Sky Compass calcola `ObservableTargetValue` usando oggetti
  compositi con target physics raw dal read-model e geometria display/live
  corrente.
- Direzione, visibilita', horizon/current position, score payload e campi QML
  restano sui target display/live; non vengono esposti campi NSOM a QML.
- Aggiornati gli audit ObservationConditions/backend/legacy: Home
  recommendedDeepSky, Best Object e Sky Compass risultano reroutati sui boundary
  raw/display corretti.
- Conservati fallback legacy senza sky quality e fallback su errore servizio;
  nessun cambio a Planner, Home, Best Object, Equipment, logging, rete o
  scritture runtime.

## NightScope 1.12.10 - 2026-07-09

- Aggiunto `docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md`, report
  developer-only per il reroute futuro di Sky Compass sul boundary
  `ObservationConditionedTargetReadModel`.
- Definita la policy Sky Compass: `ObservableTargetValue` deve usare target
  physics raw da `nsom_target_input`, mentre direzione, visibilita',
  horizon/current position e payload restano sul target display/live.
- Documentato che boost da Night Plan e Best Object restano presentation/context
  policy e non target physics NSOM.
- Aggiornati gli audit ObservationConditions/backend/legacy: Home e Best Object
  sono reroutati, Sky Compass ha policy definita e runtime adapter ancora
  pending.
- Nessun cambio runtime a Sky Compass, QML/UI, Planner, Home, Best Object,
  Equipment, logging, rete o scritture runtime.

## NightScope 1.12.9 - 2026-07-09

- Reroutato il ramo runtime Best Object NSOM sul boundary
  `ObservationConditionedTargetReadModel`: lo scoring/selection usa il target
  raw `nsom_target_input`, mentre il risultato esposto resta il
  `qml_display_target` compatibile.
- Conservati rollback e fallback: `AppController(use_nsom_best_object=False)`
  e sky quality mancante continuano a usare il path legacy esistente.
- Aggiunto test di regressione che verifica che il servizio Best Object riceva
  i target raw e che il controller ritorni il display target selezionato.
- Rigenerati gli audit ObservationConditions/backend/legacy: Home e Best Object
  risultano reroutati; Sky Compass resta l'unico consumer ObservationConditions
  ancora da valutare.
- Nessun cambio a QML/UI, Planner, Home `recommendedDeepSky`, Equipment,
  logging, rete o scritture runtime.

## NightScope 1.12.8 - 2026-07-09

- Reroutato il ramo runtime Home `recommendedDeepSky` NSOM: il ranking ora usa
  `ObservationConditionedTargetReadModel.nsom_target_input`, cioe' il target raw
  preservato dal boundary ObservationConditions.
- Il payload QML continua a ricevere
  `ObservationConditionedTargetReadModel.qml_display_target`, quindi chiavi,
  score display/base e compatibilita' UI restano invariati.
- Il fallback con sky quality mancante e il rollback
  `AppController(use_nsom_home_recommended_deep_sky=False)` restano sul path
  legacy moon-adjusted.
- Best Object, Sky Compass, Planner, Equipment, QML, logging, rete e scritture
  runtime non sono stati modificati.
- Rigenerati gli audit `OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT`,
  `NSOM_BACKEND_MIGRATION_STATUS_AUDIT` e
  `NSOM_LEGACY_BACKEND_SURFACE_AUDIT`: Home risulta completato, Best Object e
  Sky Compass restano i consumer ObservationConditions da valutare.

## NightScope 1.12.7 - 2026-07-09

- Aggiunto `docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md`,
  audit developer-only per la policy di reroute dei consumer NSOM
  ObservationConditions.
- Il report confronta `ObservableTargetValue` costruito dal target raw del
  read-model contro il target display condizionato, evidenziando il doppio
  conteggio potenziale su Home, Best Object e Sky Compass.
- Definita la policy: i consumer NSOM dovrebbero calcolare dal raw target del
  read-model e mantenere il display target condizionato per payload QML e
  compatibilita' score.
- Corretto un bug interno di fedelta' del read-model Home: la cache Home
  aggregata ora conserva il breakdown deep-sky gia' calcolato invece di
  ricostruirlo come `display_only_projection`.
- Nessun reroute runtime ancora applicato: ranking, selezione Best Object, Sky
  Compass, QML, logging, rete e scritture runtime restano invariati.

## NightScope 1.12.6 - 2026-07-09

- Introdotto il read-model interno `ObservationConditionedTargetReadModel`
  per separare target raw, target display condizionato, breakdown condizioni,
  score raw, score display e policy di input NSOM.
- Aggiunto `ObservationConditionsService.condition_deep_sky_pollution_context()`
  come entrypoint che conserva i `ConditionedTarget` completi; il vecchio
  `apply_deep_sky_pollution_context()` resta wrapper compatibile e mantiene lo
  stesso output `CelestialObject`.
- `AppController` mantiene cache read-model private per deep-sky/Home, senza
  nuove property Qt/QML e senza modificare payload, ranking, Best Object, Sky
  Compass o Planner.
- Rigenerati gli audit `OBSERVATION_CONDITIONS_READ_MODEL_AUDIT`,
  `NSOM_BACKEND_MIGRATION_STATUS_AUDIT` e
  `NSOM_LEGACY_BACKEND_SURFACE_AUDIT`: lo stato passa a
  `read_model_boundary_introduced_consumer_reroute_pending`.
- Resta aperta una review successiva per decidere se e come Home, Best Object e
  Sky Compass debbano leggere il lato raw del read-model senza cambi silenziosi
  di ranking.

## NightScope 1.12.5 - 2026-07-09

- Aggiunto `docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md`, audit
  developer-only del boundary `ObservationConditionsService`.
- L'audit conferma che `ObservationConditionsService` e' runtime attivo, non
  dead legacy: crea copie `CelestialObject` condizionate per compatibilita'
  Home/Detail/Sky Compass e puo' alimentare path NSOM default-on.
- Identificato il rischio architetturale
  `observation-conditions-conditioned-score-as-nsom-intrinsic`: gli score gia'
  condizionati possono diventare input `IntrinsicTargetQuality`/`ObservableTargetValue`.
- Aggiornati gli audit backend per raccomandare come prossimo step un boundary
  read-model che separi raw target, display score condizionato e input NSOM.
- Nessun cambio runtime: nessuno scoring, QML, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, logging, rete o scrittura runtime modificati.

## NightScope 1.12.4 - 2026-07-09

- Rimosso il path backend Notifications ormai non consumato dalla Home:
  `NotificationService`, `AppController.notifications`, lo storage runtime e il
  DTO `Notification`.
- Aggiornati test e audit Advanced Observing per trattare Notifications come
  dead legacy rimosso, non come consumer da proteggere con input legacy.
- Rigenerati gli audit `NOTIFICATIONS_DEAD_LEGACY_AUDIT`,
  `NSOM_LEGACY_BACKEND_SURFACE_AUDIT` e
  `NSOM_BACKEND_MIGRATION_STATUS_AUDIT`.
- Nessun cambio a Planner, Home recommendedDeepSky, Best Object, Advanced
  Observing visible payload, Sky Compass, QML, logging, rete o scritture
  runtime.

## NightScope 1.12.3 - 2026-07-09

- Aggiunto `docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md`, audit developer-only che
  conferma l'assenza di consumer QML/Home per Notifications.
- Riclassificato Notifications come `dead_legacy_pending_removal`, non come
  superficie NSOM da migrare.
- Aggiornati gli audit backend per indicare la rimozione del path
  `NotificationService`/`AppController.notifications` come prossimo cleanup.
- Nessun cambio runtime in questo commit: nessun scoring, QML, logging, rete o
  scrittura runtime modificati.

## NightScope 1.12.2b - 2026-07-08

- Indurita la projection Equipment condivisa `ObserverCapability/Q_target`: il
  profilo di pesi target-specific ora e' metadata immutabile invece di un
  dizionario mutabile.
- Aggiunto un test di regressione che prova l'immutabilita' del profilo pesi e
  la compatibilita' con JSON strict.
- Nessun cambio a scoring, Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, QML, logging, rete o
  scritture runtime.

## NightScope 1.12.2 - 2026-07-08

- Estratto l'adapter condiviso `ObserverCapability/Q_target` in
  `astro_viewer/app/services/observer_capability_adapter.py`.
- `EquipmentNsomComparisonService` ora usa l'adapter condiviso invece di una
  copia privata della formula di capability derivata dalle configurazioni.
- Aggiunti test diretti per configurazioni telescopio/binocolo, proiezione
  target-specific, JSON strict e parita' fra comparison rows e adapter.
- Aggiornati `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md`,
  `docs/EQUIPMENT_NSOM_POLICY_READINESS.md` e gli audit backend: Equipment ha
  ora lo stato `observer_adapter_extracted`, mentre il runtime setup helper
  resta invariato.
- Nessun cambio a QML/UI, Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, logging, rete o scritture
  runtime.

## NightScope 1.12.1 - 2026-07-08

- Aggiunto `docs/EQUIPMENT_NSOM_POLICY_READINESS.md`, audit developer-only che
  decide la policy Equipment/ObserverCapability dopo il confronto 1.12.0.
- Deciso che `EquipmentService.suggest_for_profile(...)` resta per ora il
  runtime setup helper per oculari, Barlow, binocoli, fallback e payload
  `setupOptions`; non viene aggiunto un path NSOM default-off Equipment.
- Registrato che `Q_target` e `ObserverCapability` sono pronti come prossimo
  adapter/read-model condiviso, ma non sostituiscono da soli lo score di setup
  o la presentazione Equipment.
- Documentati i confini: sky quality e seeing non devono modificare
  `ObserverCapability`; `RecommendationConfidence` resta metadata-only.
- Aggiornati gli audit backend: il prossimo step consigliato e' estrarre un
  adapter `ObserverCapability/Q_target` condiviso, senza cambiare le
  raccomandazioni Equipment runtime.
- Nessun cambio a QML/UI, Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, logging, rete o scritture
  runtime.

## NightScope 1.12.0 - 2026-07-08

- Aggiunto `EquipmentNsomComparisonService`, helper developer-only che confronta
  la formula corrente di `EquipmentService` con `ObserverCapability`,
  `Q_target` e `PracticalTargetValue` NSOM.
- Generato `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md` con scenari deterministici
  per pianeti, ammassi aperti, galassie, seeing, inquinamento luminoso,
  binocoli e telescopi.
- Esplicitato che la formula legacy Equipment miscela target traits, sky
  quality, seeing e praticita' di setup in uno score unico, mentre NSOM tiene
  `ObservableTargetValue` separato da `ObserverCapability`.
- Aggiornati gli audit backend per registrare Equipment come
  `comparison_layer_available`; il prossimo step consigliato e' una review
  1.12.0 seguita da policy/readiness Equipment.
- Nessun cambio a raccomandazioni Equipment runtime, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, QML/UI, logging, rete o
  scritture runtime.

## NightScope 1.11.1 - 2026-07-08

- Rimosso il path backend Sky Map morto:
  `SkyMapService`, `AppController.skyMap`, lo storage `_sky_map` e i ricalcoli
  `_sky_map_service.map_targets(...)`.
- Aggiornati i test che stubavano Sky Map solo come dipendenza accessoria del
  controller.
- Aggiornati `docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md` e
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md`: Sky Map e' ora
  `removed_dead_legacy`, non piu' una superficie residua o un target NSOM.
- Il prossimo backend NSOM reale diventa Equipment/ObserverCapability, mentre
  cleanup dei rollback interni e UI explanation restano decisioni separate.
- Nessun cambio a QML/UI, Planner, Home recommendedDeepSky, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, scoring NSOM, logging, rete o
  scritture runtime.

## NightScope 1.11.0 - 2026-07-08

- Aggiunto l'audit developer-only delle superfici backend legacy:
  `docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md`.
- Riclassificata Sky Map come `dead_legacy`: la Home QML usa Sky Compass e non
  consuma piu' `controller.skyMap`, mentre il controller calcola ancora
  `_sky_map`.
- Interrotta la raccomandazione di creare una Sky Map NSOM comparison layer:
  il prossimo step consigliato e' rimuovere il path Sky Map morto dopo review.
- Classificati i rollback NSOM esistenti come safety net interne temporanee,
  non come contratti pubblici da preservare indefinitamente.
- Distinti i campi di compatibilita' payload/UI dagli score decisionali NSOM e
  dalle superfici legacy ancora attive.
- Aggiornato `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` per riflettere la
  nuova direzione di cleanup.
- Nessun cambio a runtime, QML/UI, scoring, Planner, Home, Best Object,
  Advanced Observing, Sky Compass, Detail/Object, logging, rete o scritture
  runtime.

## NightScope 1.10.6 - 2026-07-08

- Chiusa la migrazione backend Detail/Object NSOM come stato documentato in
  `docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md`.
- Confermato che `NSOM_DETAIL_OBJECT_ENABLED = True` resta il default e che il
  rollback e' `AppController(use_nsom_detail_object=False)`.
- Documentato che `selectedObject` resta il payload QML compatibile e che il
  payload NSOM Detail/Object resta interno/separato.
- Aggiornato l'audit backend complessivo: Detail/Object non e' piu' una
  superficie da chiudere; il prossimo backend step consigliato e' Sky Map NSOM
  comparison.
- Nota successiva: questa raccomandazione e' stata superata dall'audit 1.11.0,
  che classifica Sky Map come legacy morto da rimuovere, non da migrare.
- Nessun cambio a runtime, QML/UI, Home, Best Object, Planner, Sky Compass,
  logging, rete o scritture runtime.

## NightScope 1.10.5 - 2026-07-08

- Abilitata di default la path interna Detail/Object NSOM impostando
  `NSOM_DETAIL_OBJECT_ENABLED = True`.
- Preservato il rollback esplicito
  `AppController(use_nsom_detail_object=False)`.
- Confermato che la default path costruisce solo il payload interno separato
  `detailObjectNsom`; `selectedObject` e la pagina QML restano invariati.
- Aggiornati readiness audit e audit backend: Detail/Object e' ora una
  superficie backend default-on chiusa, con UI/spiegazioni visibili ancora fuori
  scope.
- Nessun cambio a Home, Best Object, Planner, Sky Compass, logging, rete o
  scritture runtime.

## NightScope 1.10.4 - 2026-07-08

- Aggiunto l'audit developer-only di readiness default-on per Detail/Object
  NSOM: `docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/detail_nsom_default_on_readiness_audit.py`.
- Confermato che la path runtime Detail/Object NSOM e' pronta per uno switch
  default-on separato, ma `NSOM_DETAIL_OBJECT_ENABLED` resta `False` in questo
  commit.
- Verificati rollback `AppController(use_nsom_detail_object=False)`, payload
  interno separato, `selectedObject` invariato, assenza di campi NSOM in QML e
  neutralita' di `SessionViability` / `RecommendationConfidence`.
- Aggiornati readiness audit e audit backend complessivo: il prossimo step puo'
  essere una commit di switch default-on se la review accetta la readiness.
- Nessun cambio a runtime default, UI/QML, Home, Best Object, Planner, Sky
  Compass, logging, rete o scritture runtime.

## NightScope 1.10.3 - 2026-07-08

- Aggiunta la path runtime interna Detail/Object NSOM default-off:
  `astro_viewer/app/services/detail_nsom_runtime.py`.
- Aggiunto il flag `NSOM_DETAIL_OBJECT_ENABLED = False` e il rollback esplicito
  `AppController(use_nsom_detail_object=False)`.
- Il controller puo' costruire un payload interno separato tramite
  `_selected_object_nsom_payload()` quando il flag e' forzato on, ma non espone
  nuove property QML e non modifica `selectedObject`.
- Il payload interno contiene `IntrinsicTargetQuality`,
  `ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
  `PracticalTargetValue`, `SessionViability` e `RecommendationConfidence`;
  sessione e confidence restano metadata-only.
- Aggiornati readiness audit e audit backend: Detail/Object ora ha una path
  interna default-off disponibile; UI visibile e default-on restano step
  successivi.
- Nessun cambio a QML/UI, Home, Best Object, Planner, Sky Compass, logging,
  rete o scritture runtime.

## NightScope 1.10.2 - 2026-07-08

- Aggiunto il contratto developer-only Detail/Object NSOM:
  `docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/detail_nsom_policy_contract.py`.
- Risolti i blocker policy del readiness audit: source split osservativo/catalogo,
  semantica dello score visualizzato e payload/display contract.
- Aggiornato `docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md` a
  `ready_for_default_off_detail_nsom_path`; il prossimo step puo' essere un
  path runtime Detail/Object NSOM default-off con rollback esplicito.
- Documentato che `selectedObject.score` resta compatibility data legacy/base e
  che il futuro payload NSOM deve restare separato (`detailObjectNsom`) senza
  aggiungere campi a `selectedObject` nel primo path runtime.
- Nessun cambio a `selectedObject`, QML/UI, Home, Best Object, Planner, Sky
  Compass, logging, rete o scritture runtime.

## NightScope 1.10.1 - 2026-07-08

- Aggiunto il readiness audit developer-only per Detail/Object NSOM:
  `docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/detail_nsom_readiness_audit.py`.
- Il verdetto e' `not_ready_for_default_off_detail_nsom_path`: un futuro path
  runtime deve attendere policy esplicite per source split osservativo/catalogo,
  semantica dello score visualizzato e contratto payload/display.
- Confermato che `RecommendationConfidence` resta metadata-only con score
  effect zero.
- Verificata assenza di wiring in controller/QML, logging automatico, rete,
  scritture runtime e cambi a `selectedObject`, Home, Best Object, Planner o
  Sky Compass.

## NightScope 1.10.0 - 2026-07-08

- Avviata la migrazione Detail/Object con un confronto NSOM developer-only:
  `astro_viewer/app/services/detail_nsom_comparison.py`.
- Aggiunto il report esplicito
  `docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md`, generato dal tool
  `astro_viewer/tools/detail_nsom_comparison_report.py`.
- Il confronto distingue il Detail osservativo, che oggi mostra una copia
  legacy moon-adjusted, dal Detail catalogo, che mantiene lo score raw.
- Esposti in parallelo `ObservableTargetValue`, `PracticalTargetValue`,
  `SessionViability` e `RecommendationConfidence` senza usarli nel payload
  runtime.
- Aggiunti test per JSON stretto, source policy osservativo/catalogo,
  sessione metadata-only, equipment su solo `PracticalTargetValue`, confidence
  score-neutral e assenza di wiring runtime/QML.
- Nessun cambio a `selectedObject`, QML/UI, Home, Best Object, Planner, Sky
  Compass, logging, rete o scritture runtime.

## NightScope 1.9.7 - 2026-07-08

- Aggiunto l'audit complessivo developer-only dello stato NSOM backend:
  `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/nsom_backend_migration_status_audit.py`.
- Confermato che Planner, Home `recommendedDeepSky`, Best Object, Advanced
  Observing backend e Sky Compass sono superfici NSOM default-on chiuse con
  rollback interni espliciti.
- Identificati i residui non bloccanti: Detail/selected object, Sky Map,
  Equipment recommendations, cache di oggetti condizionati, Notifications e
  score raw di catalogo.
- Raccomandato come prossimo step `1.10.0 Detail/Object NSOM comparison layer`.
- Nessun cambio runtime, QML/UI, scoring, logging, rete, scritture runtime o
  report runtime wiring.

## NightScope 1.9.6 - 2026-07-07

- Chiusa la migrazione Sky Compass NSOM come stato documentato.
- Sky Compass usa ora di default `SkyCompassNsomDirectionService` con base
  `ObservableTargetValue.value` e policy di presentazione per piano
  osservativo, Best Object e presenza target.
- Il rollback legacy resta esplicito con
  `AppController(use_nsom_sky_compass=False)`.
- Documentato che il payload `skyCompass` resta legacy-compatible e che il
  campo `score` resta dato legacy/base di compatibilita', non rationale NSOM.
- Documentato il fallback legacy quando manca sky quality o il path NSOM
  fallisce.
- Nessun cambio a QML/UI visibile, logging, rete, scritture runtime o report
  runtime wiring.

## NightScope 1.9.5 - 2026-07-07

- Abilitato Sky Compass NSOM di default impostando
  `NSOM_SKY_COMPASS_ENABLED = True`.
- Il default del controller ora usa `SkyCompassNsomDirectionService` quando e'
  disponibile sky quality; la base candidato e' `ObservableTargetValue.value`,
  con boost da piano osservativo, Best Object e presenza target come policy di
  presentazione.
- Il rollback resta esplicito con
  `AppController(use_nsom_sky_compass=False)` e conserva il path legacy
  `SkyCompassService`.
- Conservato il fallback legacy quando manca sky quality o il path sperimentale
  fallisce.
- Aggiornato il readiness/status report
  `docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md` per registrare lo stato
  default-on attivo e blocker vuoti.
- Nessun campo NSOM viene aggiunto al payload `skyCompass`; nessuna modifica
  QML/UI, logging, rete, scrittura runtime o report runtime wiring.

## NightScope 1.9.4 - 2026-07-07

- Aggiunto il default-on readiness audit developer-only per Sky Compass NSOM:
  `docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/sky_compass_nsom_default_on_readiness_audit.py`.
- Il verdetto e' `ready_for_sky_compass_nsom_default_on_switch`, con blocker
  vuoti e cambio richiesto separato: `NSOM_SKY_COMPASS_ENABLED = True`.
- Verificati default-off legacy, opt-in NSOM, rollback
  `AppController(use_nsom_sky_compass=False)`, fallback legacy se manca sky
  quality o il servizio sperimentale fallisce, payload `skyCompass` invariato e
  assenza di campi NSOM in QML.
- Documentato che il campo `score` resta legacy/base compatibility data e non
  e' una rationale NSOM della direzione; il rischio e' non bloccante per lo
  switch backend.
- Confermato che `PracticalTargetValue`, `ObserverCapability`,
  `SessionViability`, meteo/equipaggiamento e `RecommendationConfidence` non
  entrano nello score runtime Sky Compass NSOM.
- Nessun cambio runtime: il flag Sky Compass NSOM resta `False`; nessun cambio a
  Home, Best Object, Planner, QML/UI, logging, rete o scritture runtime.

## NightScope 1.9.3 - 2026-07-07

- Introdotto il path runtime Sky Compass NSOM sperimentale e interno con
  `NSOM_SKY_COMPASS_ENABLED = False`.
- Aggiunto `SkyCompassNsomDirectionService`: usa `ObservableTargetValue.value`
  come base candidato e mantiene boost da piano osservativo, Best Object e
  presenza target come policy di presentazione.
- Aggiunto l'opt-in interno `AppController(use_nsom_sky_compass=True)` e il
  rollback/fallback legacy esplicito tramite `use_nsom_sky_compass=False`.
- Preservato il payload `skyCompass`: nessun campo NSOM esposto a QML e score
  visualizzato ancora compatibile con il valore legacy/base del target.
- Aggiunto fallback al `SkyCompassService` legacy quando manca sky quality o il
  servizio sperimentale non riesce a costruire il payload.
- Aggiunti test per flag default-off, path opt-in NSOM, rollback legacy,
  high-light-pollution, boost da piano/Best Object, JSON stretto, payload
  invariato, assenza di wiring QML/report e assenza di mutazione dei target.
- Nessun cambio runtime predefinito: Sky Compass legacy resta attivo di default;
  nessun cambio a Home, Best Object, Planner, QML/UI, logging, rete o scritture
  runtime.

## NightScope 1.9.2 - 2026-07-07

- Aggiunto il readiness/policy report developer-only
  `docs/SKY_COMPASS_NSOM_POLICY_READINESS.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/sky_compass_nsom_policy_readiness.py`.
- Documentate le policy per un futuro path Sky Compass NSOM default-off:
  `ObservableTargetValue.value` come base candidato, boost da piano/Best Object
  e concentrazione direzionale come presentation policy, `PracticalTargetValue`
  reference-only, sessione/caution e confidence come metadata.
- Chiarito che un futuro path sperimentale deve preservare payload
  `skyCompass`, fallback legacy e assenza di campi NSOM in QML.
- Aggiunti test per determinismo, JSON stretto, copertura decisioni, evidenza
  dal comparison report, no runtime/QML wiring e allineamento del report
  checked-in.
- Nessun cambio a Sky Compass runtime, Home, Best Object, Planner, QML,
  logging, rete o scritture runtime.

## NightScope 1.9.1 - 2026-07-07

- Aggiunto il report developer-only
  `docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md`.
- Aggiunto il tool esplicito
  `astro_viewer/tools/sky_compass_nsom_comparison_report.py` per rigenerare il
  report fuori dal runtime.
- Il report copre 8 scenari deterministici: cielo buio, Luna brillante, alto
  inquinamento luminoso, meteo scarso, sessione bloccata, piccolo telescopio,
  grande telescopio e boost da piano/Best Object.
- Documentato che Sky Compass non e' un ranking puro per target-value: la
  formula legacy combina score candidato preparato, membership nel piano, Best
  Object e concentrazione direzionale.
- Aggiunti test per output deterministico, JSON stretto, componenti legacy
  non disponibili, separazione sessione/equipaggiamento, confidence neutrality,
  assenza di wiring runtime/QML e allineamento del report checked-in.
- Nessun cambio a Sky Compass runtime, Home, Best Object, Planner, QML,
  logging, rete o scritture runtime.

## NightScope 1.9.0 - 2026-07-07

- Avviata la migrazione Sky Compass con
  `SkyCompassNsomComparisonService`, un helper developer-only e side-effect-free.
- Il comparison layer confronta la formula legacy direzionale
  `sum(item.score + in_plan_bonus + best_object_bonus + target_presence_bonus)`
  con proiezioni NSOM per `IntrinsicTargetQuality`,
  `ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
  `PracticalTargetValue`, `SessionViability` e `RecommendationConfidence`.
- Evidenziato che Sky Compass legacy miscela score candidato gia' preparato,
  membership nel piano, Best Object e concentrazione direzionale in uno score
  di direzione.
- Confermato che sessione/meteo e confidence restano metadata nel confronto e
  che l'equipaggiamento influenza solo il riferimento `PracticalTargetValue`.
- Aggiunti test di regressione per JSON stretto, bright Moon/high light
  pollution, sessione bloccata, equipaggiamento, confidence neutrality, target
  invisibili/senza direzione, assenza di mutazioni e assenza di wiring QML.
- Nessun cambio a Sky Compass runtime, payload QML, Home, Best Object, Planner,
  logging, rete, scritture runtime o report runtime wiring.

## NightScope 1.8.18 - 2026-07-07

- Chiuso lo stato della migrazione Advanced Observing NSOM come backend
  default-on.
- Documentato che `NSOM_ADVANCED_OBSERVING_ENABLED = True` e che il rollback
  resta esplicito con `AppController(use_nsom_advanced_observing=False)`.
- Confermato che `advancedScores` resta legacy-compatible per card Home,
  Planner e NotificationService, mentre `advancedObservingNsom` resta una
  property read-only separata.
- Registrato che il metadata runtime di `advancedObservingNsom` e' allineato
  allo stato default-on (`default_on_internal_projection`).
- Documentato che UI visibile, copy/localizzazione e sostituzione futura degli
  score legacy restano lavori separati e non bloccano la migrazione backend.
- Nessun cambio a scoring, Planner, Home Best Object, Sky Compass, QML visibile,
  logging, rete, scritture runtime o report runtime wiring.

## NightScope 1.8.17 - 2026-07-07

- Abilitato Advanced Observing NSOM di default impostando
  `NSOM_ADVANCED_OBSERVING_ENABLED = True`.
- Il default calcola ora lo snapshot interno parallelo
  `_advanced_observing_nsom_scores` e la presentazione read-only
  `advancedObservingNsom`.
- `advancedScores` resta legacy-compatible e continua a essere il contratto
  visibile delle card Home e l'input per Planner e NotificationService.
- Il rollback resta esplicito con
  `AppController(use_nsom_advanced_observing=False)`.
- Aggiornato il report di readiness per registrare lo switch backend attivo.
- Nessuna UI QML visibile, nessun logging automatico, rete, scrittura runtime o
  wiring dei report developer-only.

## NightScope 1.8.16 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_default_on_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md`,
  audit per lo switch default-on backend/interno di Advanced Observing NSOM.
- Il verdetto e' `ready_for_advanced_observing_nsom_backend_default_on`: nessun
  blocker per abilitare la proiezione NSOM interna in un commit separato.
- Chiarito che lo switch backend non sostituisce `advancedScores`, non rende UI
  QML visibile e non cambia Planner, NotificationService, Home Best Object o
  Sky Compass.
- Registrati come non bloccanti per il backend: design UI visibile,
  copy/localizzazione e sostituzione futura degli score legacy.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessun cambio runtime,
  scoring, logging, rete o scritture runtime in questo audit.

## NightScope 1.8.15 - 2026-07-07

- Rafforzata la property QML read-only `advancedObservingNsom`.
- La property ora restituisce una copia difensiva profonda dello snapshot
  `_advanced_observing_nsom_presentation`, invece di esporre direttamente il
  dizionario privato.
- Aggiunto un test sul Qt property system: la property e' non scrivibile, usa
  `weatherChanged`, restituisce payload JSON-compatibile e non permette di
  mutare lo snapshot interno.
- Nessuna UI QML visibile legge la property; `advancedScores` resta il contratto
  Home visibile.
- Nessun cambio a Planner, NotificationService, Home Best Object, Sky Compass,
  scoring, logging, rete o scritture runtime. Il flag
  `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`.

## NightScope 1.8.14 - 2026-07-07

- Aggiunta in `AppController` la property QML read-only
  `advancedObservingNsom`.
- La property usa il lifecycle esistente `weatherChanged`, non introduce nuovi
  signal e legge solo lo snapshot privato
  `_advanced_observing_nsom_presentation`.
- Quando `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`, o lo snapshot non e'
  disponibile, la property restituisce `{}`.
- Quando il path Advanced Observing NSOM viene forzato internamente, la property
  espone il payload `advanced_observing_nsom_presentation_v1` gia' proiettato,
  senza ricomputare al read.
- Nessuna UI QML visibile legge `advancedObservingNsom`; `advancedScores` resta
  il contratto Home pubblico usato dalle card esistenti.
- Aggiornati i report developer-only di readiness/contract/policy per
  distinguere property QML read-only presente da UI visibile assente.
- Nessun cambio a Planner, NotificationService, Home Best Object, Sky Compass,
  scoring, logging, rete o scritture runtime. Il flag
  `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`.

## NightScope 1.8.13 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_qml_presentation_policy.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md`, policy
  per una futura superficie QML `advancedObservingNsom`.
- Definita la policy di lifecycle: una futura property read-only dovra' usare
  lo snapshot privato `_advanced_observing_nsom_presentation` e il lifecycle
  esistente `weatherChanged`, senza ricomputare al read e senza introdurre un
  nuovo signal.
- Definite le policy di copy/placement/score-label: la UI visibile resta
  bloccata, la copy futura deve passare da chiavi localizzabili e i valori NSOM
  vanno etichettati come diagnostica `ObservableTargetValue`, non come score
  legacy `/100`, input Planner o soglie NotificationService.
- Confermato che `advancedScores` resta l'unico contratto QML pubblico
  corrente; nessuna property QML, logging, rete, scrittura runtime o modifica a
  Planner, NotificationService, Home, Best Object o Sky Compass.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; il prossimo step
  utile e' una review della policy prima di qualsiasi esposizione QML.

## NightScope 1.8.12 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_qml_exposure_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md`, audit di
  readiness per una futura esposizione QML di `advancedObservingNsom`.
- Confermato che la proiezione interna 1.8.10/1.8.11 e' safe-to-keep, ma non
  ancora pronta per una property QML pubblica o UI visibile.
- Bloccanti registrati: lifecycle/notify-signal della property, copy UI,
  localizzazione e semantica score/label per evitare di presentare valori NSOM
  come score legacy `/100` di actionability.
- `advancedScores` resta l'unico contratto QML pubblico corrente; nessun
  cambio a Planner, NotificationService, Best Object o Sky Compass.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.11 - 2026-07-07

- Rafforzata la proiezione interna/default-off Advanced Observing NSOM
  introdotta in 1.8.10.
- Corretta la fedelta' del metadata sessione:
  `_advanced_observing_nsom_presentation` ora preserva lo stato `monitor` del
  controller quando il meteo corrente blocca la sessione ma esiste una finestra
  osservativa utile piu' tardi.
- Aggiunta copertura regression per la proiezione dello stato `monitor`,
  mantenendo `SessionViability`/session state come metadata fuori dai valori di
  categoria.
- `advancedScores` resta legacy-compatible; non sono stati aggiunti property
  QML, input Planner, input NotificationService, input Best Object o input Sky
  Compass.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessun logging, rete
  o scrittura runtime introdotti.

## NightScope 1.8.10 - 2026-07-07

- Aggiunto `astro_viewer/app/services/advanced_observing_nsom_presentation.py`,
  builder interno del payload `advancedObservingNsom` definito dal contratto
  1.8.9.
- `AppController` ora puo' proiettare il payload NSOM Advanced Observing solo
  quando `use_nsom_advanced_observing=True`, salvandolo nello snapshot privato
  `_advanced_observing_nsom_presentation`.
- Il payload condiviso `advancedScores` resta legacy-compatible e continua a
  essere l'unico dato pubblico letto da QML, Planner e NotificationService.
- Aggiornato `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md`: il
  blocker `advanced-observing-runtime-projection-not-implemented` e' risolto;
  resta il blocker separato `advanced-observing-qml-exposure-review-required`.
- Aggiunti test per JSON stretto, proiezione forced-on/off, consumer legacy
  invariati e assenza di property QML.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.9 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_presentation_contract.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md`, contratto
  per una futura superficie QML-safe separata `advancedObservingNsom`.
- Definito che il futuro payload NSOM non sostituisce `advancedScores`, non e'
  input Planner, non e' soglia NotificationService e non alimenta Home Best
  Object o Sky Compass.
- Definito che Advanced Observing NSOM usa diagnostiche di categoria da
  `ObservableTargetValue`; `ObserverCapability`, `PracticalTargetValue`,
  `SessionViability`, `RecommendationConfidence` e `ObservationOpportunity`
  restano fuori dal valore categoria.
- I blocker default-on rimasti sono implementativi: proiezione runtime
  default-off del nuovo contratto e review separata per eventuale esposizione
  QML.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.8 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_presentation_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md`, audit di
  readiness per la presentazione/default-on Advanced Observing NSOM.
- Confermato che lo split 1.8.7 protegge Planner e NotificationService:
  `advancedScores` resta legacy-compatible e lo snapshot NSOM resta interno.
- Registrato il verdetto: Advanced Observing NSOM non e' ancora pronto per
  default-on, perche' i valori NSOM forced-on non hanno un contratto
  QML/presentazione e non modificano la superficie visuale.
- Bloccanti rimasti: visibilita' dello snapshot NSOM, contratto di presentazione
  NSOM e semantica score/label `/100`.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.7 - 2026-07-07

- Implementato lo split dei consumer Advanced Observing NSOM nel controller.
- `advancedScores` resta il payload legacy-compatible condiviso con QML,
  Planner e NotificationService.
- Quando `use_nsom_advanced_observing=True`, il controller calcola i valori
  Advanced Observing NSOM solo come snapshot interno parallelo
  `_advanced_observing_nsom_scores`.
- Planner e NotificationService ricevono input consumer-specifici
  legacy-compatible, quindi i valori NSOM di categoria non vengono usati come
  fattore di trasparenza Planner o soglia diretta di notifica.
- Aggiornato `docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md`: i blocker
  Planner e NotificationService risultano risolti dallo split; resta bloccante
  la policy di presentazione/QML prima di qualunque default-on.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessuna esposizione
  QML, logging, rete o scrittura runtime.

## NightScope 1.8.6 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_downstream_policy.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md`, policy report
  sui consumer downstream di `advancedScores`.
- Registrata la decisione che `advancedScores` deve restare legacy-compatible
  finche' Planner e NotificationService non ricevono input consumer-specifici o
  una policy esplicita di split.
- Evidenziato il rischio Planner: il Planner NSOM usa `advancedScores` come
  fattore di trasparenza atmosferica; usare direttamente i valori Advanced
  Observing NSOM forced-on cambierebbe ranking e ownership.
- Evidenziato il rischio notifiche: in sessione bloccata i valori NSOM di
  categoria restano fisici/alti e potrebbero generare notifiche favorevoli senza
  un gate di `SessionViability`.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; nessun cambiamento
  runtime a formule, Planner, NotificationService, Home, Best Object, Sky
  Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.5 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_runtime_review.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md`, review del path
  Advanced Observing NSOM forced-on introdotto in 1.8.4.
- Il report confronta punteggi legacy e forced-on NSOM sugli scenari
  deterministici gia' usati per Advanced Observing, verificando JSON stretto,
  payload compatibile, confidence neutra, sessione fuori dallo score, protezione
  planetaria da Moon/light-pollution background e sensibilita' deep-sky.
- Il flag `NSOM_ADVANCED_OBSERVING_ENABLED` resta `False`; il default runtime
  resta legacy.
- Emerso blocker esplicito per default-on: `advancedScores` e' condiviso con
  QML, Planner e NotificationService, quindi una futura attivazione deve
  decidere se questi consumer usano, ignorano o ricevono una copia
  legacy-compatible degli score avanzati.
- Nessun cambiamento runtime a formule, flag, Home, Best Object, Planner, Sky
  Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.4 - 2026-07-07

- Aggiunto `astro_viewer/app/services/advanced_observing_nsom_service.py`, path
  runtime interno e sperimentale per Advanced Observing NSOM.
- Introdotto il flag `NSOM_ADVANCED_OBSERVING_ENABLED = False`; il default
  runtime resta il legacy `AdvancedObservingService`.
- Aggiunto override interno del controller
  `use_nsom_advanced_observing`, senza toggle QML e senza esporre campi NSOM nel
  payload `advancedScores`.
- Il path forced-on calcola punteggi planetario/deep-sky da
  `ObservableTargetValue` di categoria, mantiene `SessionViability` e
  `RecommendationConfidence` come metadata paralleli e non usa
  `ObserverCapability`.
- Aggiunti test per default-off legacy invariato, forced-on NSOM, protezione
  planetaria da Moon/light-pollution background, sessione bloccata fuori dallo
  score, confidence neutra, payload QML compatibile, assenza di report/QML
  wiring e no mutation.
- Nessun cambiamento runtime di default a Home, Best Object, Planner, Sky
  Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.3 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_policy_readiness.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md`, audit di policy
  e readiness per un futuro path Advanced Observing NSOM default-off.
- Registrate decisioni esplicite su ruolo Advanced Observing, separazione
  `SessionViability`, seeing planetario, protezione pianeti/Luna da
  Moon/light-pollution background, target-class deep-sky, weather cap legacy,
  ObserverCapability differito e `RecommendationConfidence` metadata-only.
- Il report dichiara che non restano blocker per implementare un path
  default-off, ma mantiene i rischi non bloccanti su score display, UI scalare,
  seeing ownership e badge deep-sky aggregato.
- Nessun cambiamento runtime a `AdvancedObservingService`, Home, Best Object,
  Planner, Sky Compass, QML/UI, logging, rete o scritture runtime.

## NightScope 1.8.2 - 2026-07-07

- Review della 1.8.1: il report Advanced Observing e' stato verificato come
  developer-only, coerente con le formule legacy disponibili e utile per
  decidere la policy prima di un path runtime default-off.
- Nessun codice runtime modificato; restano da decidere esplicitamente
  session/actionability, protezione planetaria da sky background, target-class
  deep-sky, score display e ruolo futuro di `ObserverCapability`.

## NightScope 1.8.1 - 2026-07-07

- Aggiunto il tool developer-only
  `astro_viewer/tools/advanced_observing_nsom_comparison_report.py`.
- Generato `docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md` con scenari
  deterministici per sessione buona/scarsa/bloccata, Luna brillante, light
  pollution alta, seeing scarso, trasparenza scarsa e bassa confidence.
- Il report confronta formule legacy `AdvancedObservingService` e proiezioni
  NSOM reference-only, chiarendo che la migrazione futura dovrebbe trattare gli
  advanced scores come diagnostica/presentazione di categoria, non come nuovo
  owner indipendente di score.
- Aggiunti test per output deterministico, JSON stretto, ownership, confidence
  metadata-only e assenza di wiring runtime/QML.
- Nessun cambiamento runtime a punteggi avanzati, Home, Best Object, Planner,
  Sky Compass, UI, logging, rete o scritture runtime.

## NightScope 1.8.0 - 2026-07-07

- Aggiunto `AdvancedObservingNsomComparisonService`, layer developer-only che
  confronta i punteggi avanzati legacy planetario/deep-sky con confini NSOM di
  riferimento.
- Esposte le formule legacy reali di `AdvancedObservingService`, inclusi
  componenti meteo, seeing/trasparenza, vento, Luna, light pollution e cap
  meteo, senza inventare breakdown non disponibili.
- La proiezione NSOM separa `SessionViability`, `ObservationEnvironment`,
  `EffectiveObservability`, `ObservableTargetValue` e
  `RecommendationConfidence`; la confidence resta metadato e non modifica gli
  score.
- Nessun cambiamento runtime: punteggi avanzati, Home, Best Object, Planner,
  Sky Compass, QML/UI, logging, rete e scritture runtime restano invariati.
- Riportato il changelog in uso come traccia umana del lavoro NSOM, con
  riepilogo retroattivo delle tappe 1.4-1.7.

## NightScope 1.7.6 - 2026-07-05

- Chiusa la migrazione Best Object NSOM come stato documentato.
- Best Object usa ora di default `ObservationOpportunity` con policy
  Home-specific; il path legacy resta rollback esplicito con
  `AppController(use_nsom_best_object=False)` e fallback quando manca la sky
  quality runtime.
- Documentato che il payload QML resta invariato e che lo score mostrato resta
  legacy/base compatibility score, quindi puo' non essere monotono con la
  selezione NSOM.

## NightScope 1.7.0-1.7.5 - 2026-07-02/2026-07-05

- Aggiunto il confronto developer-only Best Object vs NSOM e il report
  `docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md`.
- Introdotto il path runtime Best Object NSOM prima default-off, poi indurito
  con policy per sessioni bloccate, target invisibili e finestre incerte.
- Aggiunto l'audit developer-only di readiness e abilitato Best Object NSOM di
  default con `NSOM_BEST_OBJECT_ENABLED = True`.
- Conservato rollback legacy esplicito, nessuna esposizione QML e nessun
  collegamento runtime ai report.

## NightScope 1.6.0-1.6.5 - 2026-07-02

- Aggiunto confronto e report NSOM per Home `recommendedDeepSky`.
- Introdotto e poi abilitato di default il ranking Home deep-sky basato su
  `ObservableTargetValue`.
- Chiusura migrazione Home `recommendedDeepSky`: rollback esplicito con
  `AppController(use_nsom_home_recommended_deep_sky=False)`, payload QML
  invariato e fallback legacy quando manca la sky quality runtime.

## NightScope 1.5.0-1.5.9 - 2026-07-01/2026-07-02

- Portata avanti la migrazione Planner NSOM fino al default-on.
- Aggiunti review target-specific di `ObserverCapability`, proiezione
  sperimentale `Q_target`, soglie di review calibrazione, decision log e policy
  per opportunita' non azionabili.
- Risolti i blocker mirati `small-equipment-planet-q-target` e
  `open-cluster-recurring-demotion`.
- Abilitato Planner NSOM di default con `NSOM_PLANNER_SCORING_ENABLED = True` e
  chiusa la migrazione Planner mantenendo rollback esplicito con
  `NightPlannerService(use_nsom_planner_scoring=False)`.

## NightScope 1.4.0-1.4.9 - 2026-06-30/2026-07-01

- Introdotto il core NSOM interno con DTO immutabili per Universe, Sky,
  Observer, Session, Opportunity e Confidence.
- Aggiunto il primo path Planner NSOM sperimentale default-off, poi pulito dai
  riferimenti di ownership legacy.
- Aggiunti fixture di confronto/divergenza, explanation fields, report
  deterministico Planner, trace matematico, hardening dei casi all-zero e test
  di formula parity/sensitivity.
- Tutto il tooling di report resta developer-only, senza QML, logging
  automatico, rete o scritture runtime.

## NightScope 1.3.8e - 2026-06-30

- Indurito l'export diagnostico NSOM: snapshot Planner coerenti, JSON stretto,
  semantica VIIRS distinta tra dati provider reali, dataset derivati e fallback.
- Aggiunto refresh snapshot dopo completamento OpenAQ/AOD senza ricomputare
  Planner, Home, Equipment o Sky Compass.
- Confermati no QML, no file writes automatici, no logging automatico, no
  signal emission e confidence parallela score-neutral.

## NightScope 1.3.5 - 2026-06-29

- Rafforzata la diagnostica di `ObservationConditionsService`: `moon_adjusted_score()` ora registra l'illuminazione lunare quando applica la penalità Luna.
- Aggiunto un flag interno non esposto a QML per riconoscere target già condizionati dal contesto deep-sky light pollution, mantenendo il fallback legacy basato sulla nota esistente.
- Preparato il boundary diagnostico per AOD NASA e particolato OpenAQ tramite input provider-neutral, ancora neutri e senza effetto sui punteggi.

## NightScope 1.3.4 - 2026-06-29

- Esteso `ObservationConditionsService` con input diagnostici provider-neutral per NASA AOD e particolato OpenAQ.
- Aggiunta diagnostica di freschezza per input atmosferici normalizzati mantenendo `aod_modifier` e `pm25_modifier` neutrali.
- Confermato che AOD e OpenAQ non modificano punteggi, Planner, best-object selection, Recommendation Engine, Sky Compass live refresh o UI.

## NightScope 1.3.3 - 2026-06-29

- Stabilizzato il confine tra `ObservationConditionsService`, `PlannerScoringService` e `NightPlannerService`.
- Spostati breakdown e penalità specifici del Planner nel servizio di scoring del Planner, mantenendo `ObservationConditionsService` come layer condiviso per Home/Detail, deep-sky context e diagnostica futura.
- Aggiunta cache dei candidati Home/Sky Compass già condizionati, evitando riapplicazioni al volo del moon adjustment nel percorso Sky Compass.
- `NightPlannerService` ora riusa un `PlannerScoringService` iniettabile e calcola lo score dei target visibili una sola volta durante la costruzione del piano.
- Aggiornata la documentazione architetturale dei confini 1.3 senza cambiare punteggi, Planner output, Recommendation Engine, Sky Compass live refresh, OpenAQ o NASA AOD.

## NightScope 1.3.2 - 2026-06-29

- Esteso il breakdown interno di `ObservationConditionsService` con diagnostica per penalità Luna, penalità inquinamento luminoso, fattori placeholder e flag anti doppio conteggio.
- Aggiunto `condition_target()` come API diagnostica interna che restituisce target condizionato, target originale e breakdown completo senza cambiare i consumer.
- Popolati placeholder neutrali per meteo, seeing, trasparenza, equipaggiamento, NASA AOD e PM2.5, senza usarli nel punteggio.
- Rafforzati i test di equivalenza per Home/Detail, pollution context, fixture Planner, best-object ed equipaggiamento.

## NightScope 1.3.1 - 2026-06-29

- Rafforzato `ObservationConditionsService` con test sui confini di attivazione del contesto inquinamento luminoso: Bortle 7, VIIRS 20, VIIRS 19.99 e sky quality mancante.
- Aggiunta copertura per magnitudine non numerica in pollution context e moon adjustment.
- Aggiunta una guardia interna contro la doppia applicazione del contesto deep-sky pollution su target già condizionati dal servizio.
- Confermati invariati AppController, Planner, best-object selection, equipaggiamento, Sky Compass live refresh, OpenAQ e NASA AOD.

## NightScope 1.3.0 - 2026-06-29

- Introdotto `ObservationConditionsService` come foundation del futuro layer condizioni, senza cambiare formule o punteggi.
- Spostati dietro il nuovo servizio solo moon-adjusted score Home/Detail e deep-sky pollution context già applicato da `AppController`.
- Aggiunti breakdown interni/test-only per score base, penalità Luna, penalità inquinamento luminoso, score finale e componenti applicate.
- Lasciati intenzionalmente invariati Planner, best-object selection, Recommendation Engine, equipaggiamento, Sky Compass live refresh, OpenAQ e NASA AOD.

## NightScope 1.2.12 - 2026-06-29

- Aggiunta una snapshot stabile dei candidati di Sky Compass nel controller: il refresh normale continua a costruire il set completo, mentre il tick live riusa solo quella lista.
- Il live refresh ogni 60 secondi non richiama più `_sky_compass_candidates()` e non riapplica filtri Home, scoring deep-sky corretto per Luna, Planner, meteo, VIIRS, OpenAQ, NASA AOD o equipaggiamento.
- La corsia live aggiorna solo campi posizionali correnti e si ferma se non esiste una snapshot valida.

## NightScope 1.2.11 - 2026-06-29

- Attivata la corsia backend live di Sky Compass: un `QTimer` controller-owned ogni 60 secondi aggiorna solo altitudine, azimut e direzione correnti dei target già preparati.
- `LIVE_TICK` ora sporca e ripulisce solo il dominio `COMPASS_LIVE`, senza toccare meteo, OpenAQ, NASA AOD, VIIRS, Planner, equipaggiamento o Recommendation Engine.
- Aggiunto `skyCompassChanged` come segnale QML dedicato, così il live refresh aggiorna solo la card Sky Compass.
- Aggiunta API astronomica leggera `refresh_current_positions()` per riusare Skyfield senza ricampionare finestre osservative o ricostruire cataloghi.

## NightScope 1.2.10 - 2026-06-29

- Introdotto `RefreshManager` come foundation per il ciclo Refresh & Data Lifecycle: classificazione di refresh reasons, refresh domains e dirty domains.
- Collegato il lifecycle layer ai refresh esistenti di location, meteo, OpenAQ, VIIRS, NASA AOD e profili/equipaggiamento senza cambiare il comportamento applicativo.
- Documentata la corsia futura `LIVE_TICK` per Sky Compass senza introdurre timer o refresh live in questa release.
- Resi neutri i motivi generici `TTL_EXPIRED` e `ASYNC_COMPLETED`, sostituiti nei percorsi operativi da motivi specifici per meteo, OpenAQ, NASA AOD e sky quality.
- Corretto lo stato dirty VIIRS: `SKY_QUALITY` resta pendente finché il refresh asincrono non termina, fallisce o viene scartato.

## NightScope 1.2.9 - 2026-06-29

- Persistito lo stato di test connessione OpenAQ usando un'impronta sicura della API key verificata, senza salvare la key in chiaro nelle preferenze.
- Aggiunta cache persistente compatta per i risultati processati NASA AOD, così le riaperture dell'app riusano dati recenti entro TTL senza riscaricare granuli.

## NightScope 1.2.8 - 2026-06-29

- Aggiunta nella pagina Meteo la sezione display-only `Trasparenza atmosferica`, basata sui risultati NASA MAIAC AOD già recuperati tramite Earthdata.
- La sezione resta nascosta senza test Earthdata riuscito, mostra un fallback compatto senza località e indica `Recupero dati NASA AOD...` durante il download.
- Mostrati AOD 550 nm, label descrittiva della trasparenza, data misura, prodotto NASA, metodo di estrazione, incertezza e QA raw senza alimentare punteggi, Planner, Sky Compass o Recommendation Engine.

## NightScope 1.2.7 - 2026-06-29

- Aggiunto retry controllato ai timeout transitori Open-Meteo, mantenendo invariati cache e logica meteo.

## NightScope 1.2.6 - 2026-06-29

- Attivato il refresh backend NASA AOD quando esistono località attiva e credenziali Earthdata verificate, con logging diagnostico del risultato.
- Il dato AOD restava interno e non veniva ancora mostrato in UI o usato nei punteggi.

## NightScope 1.2.5 - 2026-06-28

- Aggiunto backend NASA AOD display-only: VIIRS MAIAC `VNP19A2.002` come sorgente primaria e MODIS MAIAC `MCD19A2.061` come fallback.
- Il provider recupera solo risultati AOD compatti, cancella i granuli NASA temporanei dopo l'estrazione e mantiene una cache in memoria dei risultati processati.
- Integrata autenticazione Earthdata tramite `earthaccess` con retry/backoff, riusando le credenziali Earthdata verificate già presenti.
- Aggiunte dipendenze `earthaccess` e `netCDF4`; MODIS resta fallback con rischio packaging da monitorare per le librerie native.
- AOD non è ancora esposto in Meteo e non alimenta Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi.

## NightScope 1.2.4 - 2026-06-28

- Aggiunta classificazione di freschezza per `Atmosfera locale`: corrente, recente, vecchia e storica.
- Le misure OpenAQ oltre 7 giorni non mostrano più una limpidezza come condizione attuale; la UI indica l'ultima misura disponibile come dato storico.
- Aggiornata la scala descrittiva della limpidezza con il livello intermedio `Velata`, usando il peggiore valore disponibile tra PM2.5 e PM10.
- Mantenuto OpenAQ come dato informativo display-only: nessun uso in Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi.

## NightScope 1.2.3 - 2026-06-28

- Corretto `Atmosfera locale`: la card Meteo resta nascosta finché OpenAQ non ha API key configurata e test connessione positivo.
- Aggiornato il recupero dati OpenAQ al flusso v3 corretto: ricerca località vicine e lettura delle ultime misure da `/v3/locations/{id}/latest`.
- Limitato il raggio OpenAQ al massimo supportato di 25 km ed evitato l'endpoint globale `/v3/measurements` che produceva HTTP 404.

## NightScope 1.2.2 - 2026-06-28

- Aggiunta la sezione `Atmosfera locale` nella pagina Meteo, basata su OpenAQ v3 e visibile solo con API key configurata.
- Mostrati PM2.5, PM10, limpidezza descrittiva e fonte/stazione più recente disponibile, con cache in memoria per località arrotondata.
- Chiarito che i dati OpenAQ restano display-only: non alimentano Recommendation Engine, Planner, Sky Compass, seeing, trasparenza o punteggi osservativi.

## NightScope 1.2.1 - 2026-06-28

- Il `Piano osservativo consigliato` continua a selezionare i target migliori per punteggio, ma ora li visualizza in ordine cronologico della notte osservativa.
- La numerazione del piano segue l'ordine temporale mostrato, rendendo la sezione una timeline operativa.

## NightScope 1.2.0 - 2026-06-28

- Aperto il ciclo NightScope 1.2.
- Chiusa la serie NightScope 1.1 con `1.1.15` come ultimo stato stabile.

## NightScope 1.1.15 - 2026-06-28

- Allineati i badge data di `Prossimi eventi` in Home alla stessa categorizzazione colori usata dal Calendario.

## NightScope 1.1.14 - 2026-06-28

- Spostate le alternative di `Sky Compass` nella testata della card, in alto a destra, riducendo l'altezza del corpo.
- Aggiunto a `GlassCard` uno slot opzionale per contenuti custom nella testata senza cambiare le card esistenti.

## NightScope 1.1.13 - 2026-06-28

- Ridotta l'altezza minima di `Sky Compass` quando non ci sono dati visualizzabili.
- Ripristinata la griglia desktop `Prossimi eventi` a quattro colonne per due righe sui layout ampi.
- Allineato verticalmente il badge data nelle card compatte degli eventi.

## NightScope 1.1.12 - 2026-06-28

- Promosso `Sky Compass` sopra `Piano della notte` come prima card pratica dopo i riepiloghi meteo/qualità.
- Riorganizzato `Sky Compass` full-width in tre colonne: bussola/direzione, motivazioni e target principali con alternative.
- Spostati `Prossimi eventi` in fondo alla Home con layout a griglia compatta.
- Rifinite le motivazioni generate da `Sky Compass` per piano osservativo, mix pianeti/deep-sky e ammassi nella stessa zona.

## NightScope 1.1.11 - 2026-06-28

- Rifiniti i breakpoint della card `Sky Compass` in layout 50/50: alternative di nuovo nella testata in alto a destra e sezioni inferiori su due colonne.
- Ripristinato l'accento teal sui badge delle direzioni alternative.

## NightScope 1.1.10 - 2026-06-28

- Ripristinato il layout 50/50 tra `Sky Compass` e `Prossimi eventi` nella sezione `Dettagli osservativi`.
- Resi i breakpoint interni di `Sky Compass` dipendenti dalla larghezza della card, così il layout resta corretto anche in colonna dimezzata.

## NightScope 1.1.9 - 2026-06-28

- Aggiunta a `GlassCard` la modalità opt-in `contentFillsHeight` per card con contenuto verticale elastico.
- Aggiornata `Ricerca città` in `Località` per far riempire alla lista risultati lo spazio interno disponibile senza magic number.

## NightScope 1.1.8 - 2026-06-28

- Rimossa la vecchia card `Mappa cielo` dalla Home e promosso `Sky Compass` nella sua posizione come guida direzionale principale.
- Riorganizzato `Sky Compass` con bussola a sinistra, direzione principale al centro, alternative nella testata e sezioni testuali a due colonne.
- Evidenziato il settore consigliato nella bussola e sostituite le icone testuali dei target con icone disegnate coerenti con il tipo oggetto.

## NightScope 1.1.7 - 2026-06-28

- Rifinita la presentazione di `Sky Compass` con motivazioni più naturali basate sul mix reale dei target nella direzione selezionata.
- Aggiornato il conteggio a `target osservabili` e ridotta l'importanza visiva delle direzioni alternative.
- Aggiunte icone minime per tipo oggetto nella lista dei target principali.

## NightScope 1.1.6 - 2026-06-28

- Rifinito `Sky Compass` trasformandolo da riepilogo direzionale in assistente osservativo orientato alla domanda "dove guardare per primo".
- Aggiunte motivazioni pratiche della direzione scelta, target principali prioritizzati e alternative più leggibili.
- Rimossa la dicitura `Aggiornato ora` dalla card Sky Compass per ridurre rumore visivo.

## NightScope 1.1.5 - 2026-06-28

- Aggiunto il prototipo `Sky Compass` in Home sotto `Mappa cielo`, per indicare la direzione ampia migliore usando i target già disponibili.
- Introdotto `SkyCompassService`, che raggruppa i target Home in otto direzioni e non chiama meteo, VIIRS, Planner o Recommendation Engine.
- Aggiornata la documentazione del refresh Home chiarendo che Sky Compass v1 non è un planetario, non introduce timer QML e non usa ancora `ObservationSnapshot`.

## NightScope 1.1.4 - 2026-06-28

- Aggiunta configurazione OpenAQ nella pagina `Provider dati`, con API key salvata nel vault di sistema, test connessione e rimozione.
- Il test OpenAQ verifica solo raggiungibilità e accettazione della API key tramite endpoint metadati v3; non recupera dati qualità aria e non modifica Meteo, Planner o Recommendation Engine.
- Aggiornata la documentazione per chiarire che OpenAQ è disponibile solo per configurazione e validazione connessione in questa fase.

## NightScope 1.1.3 - 2026-06-28

- Corretto il layout della card `Ricerca città` in `Località`: il pannello risultati resta ora dentro il bordo della card anche nel layout desktop a due colonne.

## NightScope 1.1.2 - 2026-06-27

- Riorganizzata la pagina `Località` mettendo la ricerca città come flusso principale sotto la posizione attuale.
- Spostate le card Windows e geolocalizzazione IP nella colonna destra, mantenendo invariati provider e azioni.
- Rinominata la card online in `Località IP (ipapi/ipwho)` per rendere esplicito il tipo di provider usato.

## NightScope 1.1.1 - 2026-06-27

- Aggiunta la pagina `Provider dati` sotto `Configurazione`.
- Spostata la configurazione Earthdata NASA fuori da `Località`, mantenendo invariati credenziali, stato, test connessione, autorizzazione app e rimozione.
- Aggiornati README e manuale per indicare la nuova collocazione della configurazione Earthdata.

## NightScope 1.1 - 2026-06-27

- Aggiunta la pagina `Oggetti celesti` come catalogo informativo separato da Home, Planner e Recommendation Engine.
- Esteso il catalogo a oggetti Messier e Sistema Solare, con ricerca, filtri, click-through al dettaglio oggetto e layout dettaglio in modalità catalogo.
- Aggiunte le colonne `Utile (≥15°)` e `Visibile nel mese`, distinguendo osservabilità utile da visibilità astronomica mensile.
- Allineata la visibilità mensile del Sistema Solare tra Catalogo, Home e dettaglio oggetto, evitando raccomandazioni contraddittorie.
- Rifinita la presentazione delle raccomandazioni separando `Visibile con...` da `Osservazione consigliata`.
- Reso più conservativo il comportamento planetario quando il seeing non è disponibile.
- Aggiunto supporto alle posizioni reali degli oculari zoom, inclusi i click del Baader Hyperion Zoom 8-24 mm.
- Migliorata la scelta pratica per ammassi globulari medi senza alterare i pesi globali del Recommendation Engine v2.
- Disambiguate le opzioni setup quando telescopi diversi condividono lo stesso label oculare.
- Aggiunta una matrice qualità ripetibile da 375 casi per controllare pianeti, categorie Messier, profili strumenti, seeing e cielo/VIIRS sintetici.
- Aggiornata la documentazione tecnica su refresh Home, architettura raccomandazioni e logica di calcolo.

## NightScope 1.0 - 2026-06-23

- Stabilizzata la Home osservativa con suggerimenti basati su profilo, meteo, Luna e qualità cielo.
- Completata la separazione tra profili strumenti e cataloghi telescopi, oculari e Barlow.
- Aggiunta pagina dettaglio oggetto con descrizione, finestra osservativa, configurazione consigliata e motivazioni.
- Migliorata la gestione della località con posizione Windows, fallback online, ricerca città offline e coordinate manuali.
- Integrato supporto opzionale Earthdata NASA per dati VIIRS Black Marble, con fallback locale.
- Consolidati i test di regressione, smoke test applicativo, QML smoke test e validazioni astronomiche.
- Aggiornato packaging Windows PyInstaller con manuale utente offline.
- Pulito il repository dagli output storici generati in `reports/`.

## NightScope RC1 - 2026-06-21

- Aggiunto logging applicativo con rotazione in `logs/nightscope.log`.
- Irrobustito il bootstrap SQLite con integrity check, backup, quarantena DB corrotto e ricostruzione.
- Irrobustita la gestione Open-Meteo per timeout, API non raggiungibile, payload vuoti, JSON non valido e rate limiting.
- Irrobustito il caricamento Skyfield con fallback controllato tramite app controller.
- Aggiunti stati loading, vuoto ed errore alle schermate Home e Meteo.
- Aggiunti test astronomici per Addis Ababa, Roma, Milano, Cape Town e Oslo.
- Aggiunti test timezone/DST per Europe/Rome.
- Aggiunti test scenario release per forecast online, meteo offline e posizione Windows non disponibile.
- Aggiunti spec PyInstaller Windows, build script e icona applicazione.
