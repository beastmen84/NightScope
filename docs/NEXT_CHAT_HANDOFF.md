# NightScope - Next Chat Handoff

Aggiornato: 2026-07-15

## Stato Versioni

- Versione sorgente: `1.33.0`
- Distribuzione Windows corrente: `1.32.3`, rigenerata dall'utente dopo il
  commit `836c90f` e usata per il controllo visuale con localita'.
- Dist `1.33.0` non rigenerata.
- Commit sorgente validato: `398f28a Audit release readiness and add bilingual manual`
- Commit checklist visuale: `4eb2c32 Record calendar visual findings`

Il commit che aggiorna questo handoff contiene solo documentazione. Per lo
stato del codice usare `398f28a`; non sostituire questo hash con un valore
previsto prima del commit.

## Commit Recenti

- `4eb2c32 Record calendar visual findings`
- `f747474 Record weather page visual findings`
- `86b61a8 Record observation log visual findings`
- `11e7628 Record binocular catalog visual findings`
- `1f1d211 Record filter and reducer visual findings`
- `cb67d21 Record eyepiece and Barlow visual findings`
- `4a0b67a Record telescope catalog visual findings`
- `f89e264 Record celestial object visual findings`
- `9ca9b77 Add visual review checklist`
- `398f28a Audit release readiness and add bilingual manual`
- `1c30467 Harden AOD quality and observing presentation`
- `7be80cf Remove legacy location normalization`
- `9247a4f Resolve location timezones from coordinates`
- `010d61f Clarify partial sky quality states`
- `41d3c9c Remove synthetic sky quality fallback`
- `034a9c3 Polish location-aware observing UI`
- `836c90f Polish no-location UI presentation`
- `283c943 Stabilize equipment seed identities`
- `7c7c196 Fix initial UI review findings`
- `8ebc6bc Add comet observing windows`
- `50bffc1 Fix ISS calendar refresh lifecycle`
- `c758dac Add ISS calendar passes`
- `5f6c2d0 Fix localization review findings`
- `60c5d46 Complete scalable application localization`
- `5ef1fdf Add Italian and English UI translations`
- `53244e2 Add observation log`
- `87f2285 Make filter recommendations aperture-aware`
- `a859d75 Add photographic reducer recommendations`
- `40a0a39 Add profile-aware filter recommendations`
- `cbc14c4 Localize remaining profile messages`
- `bbeec59 Add filter and reducer equipment UI`
- `276c686 Add Sky Compass Home filter`

## Commit Equipment Recenti

- `7c7c196 Fix initial UI review findings`
- `87f2285 Make filter recommendations aperture-aware`
- `a859d75 Add photographic reducer recommendations`
- `d360b58 Refine target filter preferences`
- `40a0a39 Add profile-aware filter recommendations`
- `1b524a9 Harden equipment catalog integrity`
- `6e2732d Package accessory catalog seeds`
- `bbeec59 Add filter and reducer equipment UI`
- `294a2de Add filter and reducer catalog persistence`

## Commit Catalogo Recenti

- `a859d75 Add photographic reducer recommendations`
- `e1b3c5d Align content migration test with schema 10`
- `f9331b8 Refresh managed catalogue content safely`
- `60a9510 Replace Solar System placeholder images`
- `7de6a6f Replace catalogue placeholder images`
- `f30bc17 Add source-backed object curiosities`
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

I punti 1, 2, 3 e 4 della roadmap catalogo sono conclusi: identita' canonica,
supporto multi-catalogo/import Caldwell, contenuti visibili con curiosita' e
asset scientifici dedicati, inclusi i nove corpi del Sistema Solare, e cataloghi
Filtri/Riduttori collegati ai profili. Testo descrittivo e note osservative
restano separati dai nuovi contenuti editoriali. L'audit `1.25.1` ha inoltre
chiuso integrita' profili/Equipment, aggiornamento dei seed editoriali e
localizzazione dei messaggi residui senza modificare NSOM.

Il punto 5 e' concluso per lo scope concordato. Da `1.26.0` il dettaglio
osservativo puo' mostrare un filtro primario e un colore opzionale confrontando
le preferenze del target con il profilo attivo. Da `1.27.0` puo' inoltre
raccomandare un riduttore fotografico usando il telescopio gia' scelto per il
target e compatibilita' esatte normalizzate. Entrambe sono proiezioni score-free
e non cambiano la configurazione calcolata. Un eventuale calcolo ottico reale
del riduttore resta futuro e richiederebbe camera, sensore, image circle e
backfocus.

La pagina separata `Log Osservazioni` e' implementata da `1.28.0` tra Calendario
e Meteo. La sezione resta fuori dal dettaglio oggetto e non modifica score,
ranking, NSOM o configurazioni consigliate.

La localizzazione `1.30.0` copre QML, messaggi Python, read model, formati
locali e contenuti strutturati dei seed. Il selettore nella barra laterale
cambia live lingua e locale, preserva le altre preferenze e non ricalcola
astronomia, meteo, equipaggiamento, score o NSOM. I testi inseriti dall'utente
restano invariati.

Da `1.31.0` il Calendario include eventi operativi transitori. `1.32.0` aggiunge
alle finestre ISS anche le comete osservabili per la posizione attiva. Entrambe
restano score-free, non creano `CatalogueObject` e non entrano in Equipment,
Planner, Home ranking o NSOM. Home continua a consumare la stessa proiezione
cronologica del Calendario.

`1.32.1` chiude il primo passaggio di correzione della panoramica UI richiesto
dall'utente: barra laterale piu' compatta, stati coerenti prima della localita',
form Equipment piu' chiari e voci integrate modificabili ma non eliminabili.
Il profilo iniziale si chiama `Default`; `Occhio nudo` e' soltanto la modalita'
derivata quando non sono assegnati telescopi o binocoli. Il prossimo passo e'
il controllo visivo manuale dell'utente sulle schermate corrette.

`1.32.2` corregge il difetto trovato nella review successiva: l'identita' delle
righe Equipment integrate non dipende piu' da marca, modello o parametri che
potrebbero essere corretti. I CSV possiedono ID espliciti e le compatibilita'
riduttore-telescopio li referenziano direttamente. Il controllo visivo puo'
quindi partire dal commit sorgente `283c943`.

`1.32.3` chiude il secondo controllo visuale senza localita'. La pagina Meteo
non presenta piu' SQM o limite visuale a zero; Home, Meteo e Calendario portano
direttamente alla configurazione della localita' e le sezioni vuote usano testo
breve. Terminologia, unita' e formati dei cataloghi Equipment/Catalogo sono
uniformati. Il prossimo passo e' il controllo visuale manuale con una localita'
configurata, partendo dal commit sorgente `836c90f`.

`1.32.4` chiude il primo controllo visuale con Addis Abeba, provider opzionali
non configurati e profilo senza strumenti. Il Catalogo usa ora davvero `°` nel
formatter backend; la Home mostra soltanto alternative realistiche a occhio
nudo, usa un'icona Luna neutra e assegna piu' spazio alla difficolta'. Meteo
esplicita l'aggregazione notturna e localizza la baseline urbana. Il conteggio
ISS `0` e' stato verificato con OMM correnti ed e' corretto. Il prossimo passo
e' un nuovo controllo visuale dell'utente partendo dal commit `034a9c3`.

`1.32.5` elimina la baseline urbana sintetica dopo la decisione di non mostrare
un Bortle inventato quando Earthdata non e' disponibile. Qualita' cielo locale
deriva ora soltanto da cache NASA VIIRS reale o da un dataset locale reale
esplicitamente fornito; in assenza di entrambi la UI mostra `n/d`. Seeing,
Equipment e condizioni osservative continuano con gli input disponibili senza
applicare penalita' luminose presunte. Home riequilibra inoltre Nome/Tipo e
limita a due righe i titoli dei prossimi eventi. Il prossimo passo e' il nuovo
controllo visuale dell'utente dal commit `41d3c9c`.

`1.32.6` chiude i due difetti trovati nella review successiva. Se il meteo
produce un diagnostico deep-sky ma manca la qualita' cielo reale, Home lo
presenta come `Parziale` con badge ambra e testo non ottimistico, senza cambiare
lo score NSOM interno. Una cache VIIRS reale stale resta disponibile, ma Meteo
ne segnala ora la necessita' di aggiornamento anche quando Earthdata non e'
configurato o verificato. Il controllo visuale puo' ripartire dal commit
`010d61f`.

`1.32.7` risolve il caso delle coordinate fuori dalla copertura utile del
catalogo citta'. Coordinate manuali e posizioni Windows ricavano ora il fuso
IANA direttamente da poligoni geografici offline; citta' e paese restano
metadati descrittivi. Il match GeoNames entro 50 km resta solo sulla posizione
Windows precisa e non sceglie mai il fuso. Il controllo visuale precedente
nelle schermate fornite dall'utente e' coerente; il prossimo controllo della
localita' deve partire dal commit sorgente `9247a4f`.

`1.32.8` elimina i percorsi di compatibilita' per vecchie coordinate salvate e
limita la normalizzazione alla sola acquisizione di una nuova localita'. Anche
la selezione dal catalogo citta' ricava il fuso dalle coordinate, senza usare
il campo timezone GeoNames. Il fallback di sistema e' ora realmente lazy e non
avvia PowerShell quando esiste gia' un risultato valido. Il controllo visuale
puo' ripartire dal commit sorgente `7be80cf`.

`1.32.9` chiude la review successiva dei dati AOD e delle ultime due
incongruenze visive. MAIAC decodifica ora `AOD_QA`, usa soltanto pixel clear di
qualita' migliore e prova pixel esatto, area 5x5 e area 11x11 con almeno tre
campioni affidabili. Le assenze reali hanno cache negativa di 6 ore; errori
transitori non vengono memorizzati. Home e Meteo mostrano la trasparenza
atmosferica separata dal Bortle, le finestre cometarie possono usare due righe
per la data e l'unita' VIIRS visibile usa `cm²`. Il prossimo passo e' il
controllo visuale dell'utente dal commit sorgente `1c30467`.

`1.33.0` conclude un audit pre-release completo senza modificare NSOM, Planner,
ranking Home, Equipment scoring, Sky Compass o schema SQLite. README e manuale
sono stati separati dalla cronologia: il README GitHub e' ora in inglese e il
manuale HTML e' unico, bilingue, responsive e accessibile dalla sidebar nella
lingua corrente. Privacy dei log, ownership della directory runtime e tooling
di validazione sono stati corretti. Non sono emersi difetti applicativi ad alta
severita', ma NightScope non e' ancora approvato per il rilascio: restano review
visuale, licenza/notice, matrice provider, rebuild/test della dist e produzione
di lock/SBOM, firma o policy esplicita e hash dell'artefatto.

Il controllo visuale configurato e' ora tracciato in
`docs/VISUAL_CHECKLIST.md`. Durante la raccolta delle schermate non applicare
le correzioni annotate: aggiornare la checklist e fare un unico passaggio di
correzione quando la panoramica sara' completa e l'utente dara' conferma.
Le coppie italiano/inglese completate sono Provider dati, Configurazione
localita', Profili, elenco Oggetti celesti, dettaglio Oggetto celeste,
elenco/aggiunta/modifica Telescopi, Oculari/Barlow, Filtri/Riduttori e Binocoli,
elenco/aggiunta/modifica del Log osservazioni, l'intera pagina Meteo con
sintesi, qualita' cielo, AOD/OpenAQ e previsioni orarie, e il Calendario con
panoramica, filtri, timeline e dettagli di Luna, opposizioni, congiunzioni,
sciami e comete. Per i cataloghi sono stati verificati conteggi, layout,
obbligatorieta', protezione delle voci integrate e assenza delle pill opzionali
vuote. Nei Binocoli resta da sostituire l'ordinamento lessicografico con quello
naturale, cosi' che specifiche come `8x20` precedano `10x20` e `18x50`.

Nel Log date, medie e riepiloghi seguono il locale, mentre i testi registrati
dall'utente restano invariati. CRUD e validazione sono coerenti e la suite
mirata passa con `7 passed`. Restano da allineare `Voto` / `Rating` sopra il
relativo valore, poiche' le dimensioni implicite dei pulsanti allargano soltanto
la riga, e da correggere tre messaggi inglesi di validazione/stato annotati come
VIS-026.

Nel Meteo le medie corrispondono alle ore evidenziate della notte osservativa;
la finestra piu' breve in sidebar resta correttamente una proiezione operativa.
Formati locali, Bortle/VIIRS, freschezza AOD e stato storico OpenAQ sono
coerenti; le quattro suite mirate passano con `67 passed`. Restano da esprimere
la radianza VNP46A3 come `nW/(cm²·sr)`, uniformare `Cloud cover` e correggere le
label atmosferiche inglesi `Veiled` / `High aerosols`. VIS-001 compare anche nel
sottotitolo Meteo come `Windows specifies`. Nessun codice applicativo e' stato
modificato durante questo passaggio.

Nel Calendario i contatori sono coerenti: `49 + 5 + 11 + 4 + 10 + 2 + 0 + 2`
corrisponde agli `83` eventi della vista annuale. Layout, filtri, ordinamento,
formati locali e distinzione tra istante astronomico e finestra osservativa
sono corretti. Congiunzioni solari, raccomandazioni del profilo, link agli
oggetti catalogati e finestra cometaria restano semanticamente separati. ISS ed
eclissi non erano disponibili come casi live negli screenshot; i relativi rami
sono stati verificati da codice e test senza attribuire loro una verifica
visuale inesistente. Le suite Calendario/ISS/comete passano con `19 passed` e
quella delle traduzioni con `15 passed`.

Restano quattro rilievi di sola presentazione nel Calendario: terminologia
inglese troppo letterale (`Maximum approach`, titoli e consigli degli sciami),
uso alternato di `gradi` / `degrees` e `°` con maiuscola incorporata in
`Intorno alle` / `Around`, composizione inglese errata dei titoli eclissi e
semantica poco chiara di `Brightness estimate confidence: Approximate`. Sono
registrati come VIS-029--VIS-032. Nessun codice applicativo e' stato modificato
durante questo passaggio.

Restano accodati etichette persistenti, sottotitoli inglesi, simbolo AFOV,
decimali precompilati italiani e campi AFOV specifici per Fisso/Zoom. Il
passaggio Filtri/Riduttori ha inoltre rilevato che i relativi seed italiani sono
dichiarati sorgenti inglesi, `en.json` non contiene le due sezioni, il menu
classe filtro non e' reattivo al cambio lingua e la modifica di un riduttore
puo' cancellare `compatible_models`. Nessun codice applicativo e' stato
modificato durante la raccolta.

## Audit Pre-Release 1.33.0

- `docs/RELEASE_CANDIDATE_REVIEW.md` contiene finding, verifiche e debito
  residuo; `docs/RELEASE_CHECKLIST.md` e' il gate operativo da completare prima
  del primo rilascio pubblico.
- Il repository non ha ancora una licenza di progetto ne' un notice consolidato
  delle dipendenze, dataset e immagini. Non pubblicare un artefatto finche'
  questa scelta non e' chiusa.
- `README.md` e' una panoramica inglese di prodotto e sviluppo; lo storico e'
  solo in `astro_viewer/CHANGELOG.md`.
- `manuale.html` contiene italiano e inglese nello stesso file. Selezione lingua,
  query `?lang=`, persistenza, stampa, navigazione desktop/mobile, formule
  Equipment, confini NSOM, ISS/comete, provider, privacy e sicurezza solare
  sono documentati.
- Il pulsante `?` nella testata sidebar apre il manuale nella lingua runtime.
  `manuale.html` era gia' incluso nello spec PyInstaller; il nuovo `manualUrl`
  risolve correttamente root sorgente e `_MEIPASS`.
- Rimossi dai log coordinate, location key, payload diagnostici Windows,
  username Earthdata e valori di coordinate non valide. Rimossa la diagnostica
  Windows non usata dalla superficie pubblica del controller.
- Database, preferenze, cache e `logs/nightscope.log` condividono una sola
  directory runtime. Nel bundle il log non viene piu' scritto sotto `_internal`.
- Gli smoke test usano `NIGHTSCOPE_RUNTIME_DIR` in una `TemporaryDirectory` e
  non leggono o modificano dati personali. Una directory nuova non avvia
  geolocalizzazione automatica.
- `deep-translator 1.11.4` e' stato rimosso dopo l'advisory
  `PYSEC-2022-252`. Gli updater usano un adapter developer minimale basato su
  Requests, con timeout, limite input e test mock; l'output automatico resta da
  revisionare manualmente.
- `tools/run_checks.py` esegue una sola suite, limita pytest a quattro worker,
  usa coverage runtime di default, supporta `--fast` e `--security` e non misura
  test/utility come codice applicativo. Non ripristinare `-n auto`: su Windows
  ha creato pressione eccessiva sulla memoria e ha destabilizzato PyCharm.
- Coverage runtime reale: `84%` su `15.212` statement. I punti piu' bassi sono
  l'entry point process/UI, coperto separatamente dagli smoke; non usare la
  percentuale da sola come approvazione di release.
- QML lint termina con exit `0` su 30 file ma conserva molte warning
  `unqualified access`. Gli smoke IT/EN passano; una loro eliminazione richiede
  un passaggio QML separato con review visuale, non una riscrittura pre-release.

## Localita' e Fusi 1.32.8

- `CoordinateTimezoneService` usa `timezonefinder 8.2.5` offline e mantiene una
  sola istanza lazy condivisa. Nessun account e nessuna query di rete sono
  necessari.
- Il dato operativo della localita' e' la terna coordinate esatte + fuso IANA.
  Citta', paese e regione servono alla presentazione e alla ricerca, non alla
  costruzione della notte locale o degli orari evento.
- Windows Geolocator restituisce coordinate e accuratezza; lo script vede
  soltanto il fuso del PC, non un fuso geografico, una citta' o un paese. Il
  lookup a poligoni sostituisce quindi il precedente fallback basato sul PC.
- La posizione Windows precisa conserva latitudine/longitudine ricevute e puo'
  arricchire citta', paese e regione con GeoNames entro 50 km. La posizione
  Windows approssimata non tenta il reverse lookup citta'.
- Le coordinate manuali conservano il nome scelto dall'utente e non cercano di
  inventare citta' o paese. Non esiste piu' un parametro interno per imporre
  manualmente il fuso: `timezonefinder` lo ricava sempre dalle coordinate.
- Anche una citta' selezionata dalla ricerca offline usa `timezonefinder`; il
  fuso GeoNames non e' una sorgente operativa. Le posizioni salvate dalla build
  corrente vengono riutilizzate direttamente e il controller non contiene
  migrazioni o rinormalizzazioni legacy.
- Un fuso IANA valido fornito dal provider IP resta autorevole. Se manca o non
  e' valido, anche quel flusso usa il lookup geografico; il fuso del computer e'
  soltanto il fallback in caso di indisponibilita' della libreria/dataset.
- Il vecchio tentativo di usare il fuso della citta' entro 500 km e' rimosso.
  Una regressione verifica inoltre che neppure la citta' entro 50 km possa
  scegliere il fuso se il resolver geografico fallisce.
- Il fallback di sistema viene valutato soltanto dopo il fallimento delle
  sorgenti valide. Questo evita una chiamata PowerShell misurata in circa due
  secondi nei normali flussi Windows e manuali.
- `timezonefinder` restituisce un identificatore di fuso IANA, non il nome di
  citta', paese o regione. GeoNames resta quindi per la ricerca citta' offline
  e i metadati descrittivi. I tre file inclusi occupano `8.529.230` byte
  (`8,13 MiB`, `1,14%` della dist corrente); citta' e alias importati occupano
  circa `55 MiB` nel database runtime compattato. Rimuoverlo significherebbe
  eliminare la ricerca citta' offline e non e' stato fatto in questa release.
- `timezonefinder` include circa 67 MB di dati e dipendenze nella venv. Alla
  data del passaggio PyPI non pubblica una wheel Windows `8.2.5`; l'installazione
  corrente ha compilato con successo una wheel dal sorgente su Python `3.14.5`.
- PyInstaller `6.21.0` trova l'hook contrib `hook-timezonefinder.py`; la verifica
  locale raccoglie 21 gruppi/file dati per circa 67 MB. La dist non e' stata
  costruita, quindi il bundle frozen va verificato soltanto quando l'utente ne
  richiedera' la rigenerazione.
- Licenza codice `timezonefinder`: MIT. Dataset `timezone-boundary-builder`:
  ODbL 1.0. Fonte e attribuzione sono in `astro_viewer/data/DATA_SOURCES.md`.

## ISS, Comete ed Eventi Transitori 1.32.0

- `TransientCalendarEventSource` e' il confine generico per sorgenti operative.
  Le implementazioni correnti sono `IssPassEventSource` e
  `CometWindowEventSource`; preparazione provider/cache e calcolo Skyfield sono
  fasi separate.
- Il motore annuale Skyfield resta proprietario di fasi, opposizioni,
  congiunzioni, eclissi e sciami. Non chiama provider transitori: una sorgente
  lenta o fallita non ritarda e non elimina questi eventi.
- La ISS usa gli OMM pubblici CelesTrak del NORAD `25544`, senza account. Il
  calcolo riusa Skyfield, SGP4, Requests e NumPy.
- La finestra mobile e' di 10 giorni. Un passaggio richiede quota ISS almeno
  `10 gradi`, satellite illuminato e Sole locale a quota non superiore a
  `-6 gradi`; i campioni della finestra visibile sono distanziati di 10 secondi.
- Ogni evento espone inizio, fine, culminazione, altezza massima, direzione
  iniziale/finale, durata, illuminazione, fonte e freschezza dei dati.
- Il dettaglio usa indicazioni operative score-free e non presenta la ISS come
  setup personalizzato o oggetto apribile. Il Calendario ha filtro e conteggio
  `ISS`; Home mantiene gli 8 eventi successivi su layout largo e 4 su stretto.
- Gli intervalli conclusi vengono esclusi anche se appartengono al giorno
  corrente; un passaggio gia' iniziato ma non concluso resta visibile. Gli
  eventi istantanei di date passate vengono eliminati prima della deduplica.
- Le comete usano il servizio pubblico NASA/JPL SBDB Query senza account. La
  query seleziona nuclei non frammentati `C`/`P` con elementi orbitali e
  parametri di magnitudine totale `M1`/`K1`, entro 730 giorni dal perielio.
- pandas e' una dipendenza runtime da `1.32.0` per `skyfield.data.mpc` e le
  orbite cometarie; nella venv validata e' installato `3.0.3`. `astroquery` non
  e' installato: aggiungere quel wrapper non ridurrebbe le query e introdurrebbe
  una dipendenza non necessaria.
- La finestra cometaria mobile e' di 90 giorni, campionata ogni 30 minuti. Una
  notte richiede almeno 60 minuti con magnitudine prevista `<= 14,5`, quota
  `>= 20 gradi`, Sole `<= -12 gradi`, elongazione `>= 30 gradi` e Luna ad
  almeno `25 gradi`, salvo illuminazione lunare `<= 35%`.
- Le notti consecutive vengono aggregate; per ogni cometa resta il migliore
  gruppo continuo, con ID stabile `comet-window-<spkid>`. Sono esposte al
  massimo le 12 comete previste piu' luminose, poi ordinate cronologicamente.
- La magnitudine e' presentata come intervallo indicativo di circa `+/- 1` e
  non come misura precisa. Il dettaglio mostra inoltre picco consigliato,
  altezza, elongazione, Luna, notti utili, fonte e freschezza. Le indicazioni di
  setup sono generiche e non leggono il profilo attrezzatura o il meteo.
- `CalendarOverviewService` e' ora `calendar_overview_v4`; Calendario espone
  conteggio/filtro `Comete`, Home e dettaglio riconoscono `comet_window` senza
  creare link a un oggetto di catalogo.
- Il controller prepara rete/cache fuori dal lock astronomico, propaga gli
  eventi sotto lock e rimpiazza solo il sottoinsieme transitorio se la location
  key e' ancora attuale. Il timer si sveglia ogni ora, ma il motore conserva i
  risultati per sorgente: ISS viene ricostruita ogni ora, comete ogni 6 ore.
  Cambiare localita' forza entrambe le sorgenti.
- Gli ID dei passaggi derivano dalla rivoluzione orbitale e non dai secondi del
  picco previsto. Il dettaglio espone l'ora reale dell'ultimo aggiornamento.
- La Home mantiene l'ordinamento cronologico puro e i limiti precedenti (8
  eventi su layout largo, 4 su stretto). Un eventuale bilanciamento per sorgente
  e' una decisione di prodotto rinviata: l'utente ha gia' un'idea da valutare
  separatamente.

## Correzioni UI ed Equipment 1.32.1

- Il profilo iniziale e' `Default`. La migrazione schema rinomina soltanto il
  vecchio profilo seed con ID `1`; se esiste gia' un profilo utente `Default`,
  sceglie il primo suffisso libero senza sovrascriverlo.
- `Occhio nudo` resta una modalita' osservativa, non un nome profilo. Viene
  usata soltanto quando il profilo non contiene telescopi o binocoli; un profilo
  con solo binocolo conserva indicazioni coerenti.
- Lo schema SQLite `16` aggiunge `seed_key` e `is_user_modified` a telescopi,
  oculari, Barlow, binocoli, filtri e riduttori. Le righe seed non modificate
  seguono gli aggiornamenti inclusi; dopo una correzione utente, bootstrap e
  reseed preservano valori e compatibilita' del riduttore.
- Tutte le voci catalogo mostrano `Modifica`. `Elimina` resta disponibile solo
  per le voci create dall'utente ed e' protetto anche nel repository; i test
  coprono modifica persistente e blocco eliminazione per tutti e sei i cataloghi.
- I form segnano i campi obbligatori con `*`, descrivono gli altri come
  facoltativi e validano numeri, range Zoom/AFOV, Barlow, filtri e riduttori. Un
  errore mantiene aperto il dialogo e mostra il messaggio del controller.
- Le schede non mostrano pill colorate per focale relativa, banda,
  trasmissione o backfocus assenti. Il doppio campo di focale massima Zoom e'
  stato rimosso.
- La sidebar usa pulsanti e spaziature verticali piu' compatti. Home, Meteo e
  Calendario mostrano `n/d` o una richiesta di localita' prima della
  configurazione; i filtri mensili del Catalogo restano disabilitati senza una
  posizione valida.
- I cataloghi Qt italiano/inglese sono completi `1571/1571`. Il tentativo di
  acquisizione automatica con `QQuickWindow.grabWindow()` e plugin offscreen si
  e' bloccato ed e' stato interrotto; non considerarlo un controllo visivo
  superato. L'utente eseguira' la verifica manuale.

## Identita' Seed Equipment 1.32.2

- I sei CSV Equipment dichiarano una `seed_key` esplicita per ogni riga; le 468
  chiavi iniziali coincidono esattamente con quelle gia' salvate dalla `1.32.1`.
  Non cambiare una chiave quando si correggono marca, modello o dati tecnici.
- Bootstrap usa l'ID esplicito per gli `UPSERT`: una correzione seed aggiorna la
  stessa riga e mantiene ID database e assegnazioni. Le modifiche utente con
  `is_user_modified = 1` restano protette.
- Se la nuova identita' naturale collide con una riga custom, il dato utente
  viene conservato e l'aggiornamento seed conflittuale viene saltato con warning.
- `reducer_telescope_compatibility_seed.csv` conserva le colonne descrittive ma
  risolve le associazioni con `reducer_seed_key` e `telescope_seed_key`; rinominare
  un prodotto non spezza quindi i collegamenti.
- Gli upgrade diretti da uno schema precedente al `16` usano la vecchia
  identita' soltanto una volta per collegare le righe integrate senza chiave
  agli ID espliciti. Il reseed ordinario non ricalcola l'ownership dai campi
  visibili. Lo schema SQLite resta `16`.
- Le chiavi dei contenuti tradotti Equipment restano un contratto distinto e
  sono ancora costruite dai campi identitari. Se un futuro fix cambia quei
  campi, rigenerare e verificare insieme i pack italiano/inglese; in `1.32.2`
  nessun valore descrittivo dei cataloghi e' stato modificato.

## Correzioni Visuali Senza Localita' 1.32.3

- La scheda `Qualita' cielo locale` verifica `hasValidLocation` per SQM, limite
  visuale, confidenza e ramo VIIRS: senza localita' ogni valore e' `n/d` e un
  payload precedente non puo' riapparire.
- Home, Meteo e Calendario espongono `Configura localita'` e inoltrano il
  comando alla pagina `location` tramite segnali QML dedicati. I messaggi nelle
  sezioni interne sono stati abbreviati per evitare la ripetizione dello stesso
  invito operativo.
- I messaggi relativi alla configurazione utente usano `localita'`; i testi di
  rilevamento Windows/IP continuano a usare `posizione` quando descrivono la
  sorgente fisica del dato.
- Oculari e Barlow mantengono il valore grezzo del barilotto nel database ma
  espongono una label derivata locale, per esempio `1,25″ / 2″`. Il fallback
  QML delle dimensioni angolari usa `°`; il formatter backend prioritario e'
  stato corretto nella `1.32.4`.
- I form mostrano unita' tra parentesi, `0,63` nell'esempio italiano del
  riduttore e `Stabilizzato` come booleano, senza definirlo facoltativo.
- Nessun cambiamento a seed, ownership Equipment, schema SQLite, score, NSOM,
  Planner, Home ranking, ISS o comete. Cataloghi Qt completi `1575/1575`.

## Correzioni Visuali Con Localita' 1.32.4

- Il `deg` osservato nella dist `1.32.3` non dipendeva da una build vecchia:
  `ObjectCataloguePage.qml` preferiva `max_angular_size_label`, generata dal
  backend come `{value} deg`, e non raggiungeva il fallback `%1°`. Il formatter
  condiviso produce ora `{value}°`; i test coprono il payload renderizzato in
  italiano e inglese.
- `homeNightPlanOverview` usa il gia' esistente
  `EquipmentSetupReadModel.requires_optical_instrument`: senza telescopi o
  binocoli nasconde le alternative che richiedono uno strumento. E' un filtro
  di presentazione score-free; non modifica NSOM, Planner, ordinamento o regole
  di idoneita' a occhio nudo.
- La tabella alternative limita la colonna nome, amplia la difficolta' a `175`
  pixel e passa al layout compatto sotto `900` pixel. Le etichette lunghe hanno
  quindi spazio stabile; le righe `Non adatto a occhio nudo` dello screenshot
  non compaiono piu' nel profilo privo di strumenti.
- La scheda Luna Home usa `resources/icons/moon.svg`, icona neutra e non legata
  alla fase. La fotografia del dettaglio Catalogo e il rendering dinamico del
  ciclo lunare non cambiano.
- Le metriche superiori Meteo dichiarano `Sintesi notte osservativa`:
  nuvolosita', vento, umidita' e temperatura sono medie; precipitazioni e' la
  probabilita' massima; seeing e trasparenza usano le stesse ore; Bortle e'
  locale e non orario.
- In `1.32.4` la sorgente sintetica `NightScope local urban baseline` veniva
  localizzata. `1.32.5` ha poi rimosso sorgente, seed e fallback: non e' piu'
  un dato disponibile nel runtime corrente.
- Nelle coordinate manuali soltanto latitudine e longitudine sono obbligatorie;
  il nome resta facoltativo come gia' previsto dal controller. I pulsanti della
  pagina usano ora `DarkButton`. La sidebar non e' stata modificata: la
  precedente osservazione sul suo cambiamento era una lettura errata.
- Verifica ISS su `9.0486, 38.7836`, `Africa/Addis_Ababa`, iniziata il
  `2026-07-14 13:27 +03:00`, con OMM CelesTrak epoca
  `2026-07-14T03:41:05.800704Z`: 26 passaggi geometrici sopra `10°` in 10
  giorni, 14 illuminati soltanto di giorno e 12 notturni interamente in ombra.
  Nessun campione soddisfa insieme quota, ISS illuminata e Sole locale `<= -6°`;
  il conteggio Calendario `0` e' quindi corretto e la pipeline non e' cambiata.
- Cataloghi Qt completi `1586/1586`; schema SQLite ancora `16`.

## Qualita' Cielo Reale 1.32.5

- Rimossi `astro_viewer/data/light_pollution_seed.csv`, il relativo importer e
  la voce PyInstaller. Non viene piu' assegnato automaticamente Bortle `5/6`.
- `LightPollutionService` risolve soltanto cache NASA Black Marble VNP46A3 o
  file locali reali opzionali `light_pollution_world_atlas.csv` e
  `light_pollution_viirs_samples.csv`; altrimenti restituisce `None`.
- All'avvio vengono eliminate da `SkyQualityEstimate` le vecchie righe non
  VIIRS. I dataset locali reali vengono letti direttamente e non confluiscono
  nella cache provider; non e' stata necessaria una migrazione schema.
- Meteo espone Bortle, SQM, limite visuale e confidenza come `n/d` quando manca
  una fonte reale. Seeing usa comunque il meteo notturno e non introduce una
  penalita' da inquinamento luminoso sconosciuto.
- Home parla di oggetti `compatibili` con l'occhio nudo quando la visibilita'
  locale non puo' essere verificata. La tabella assegna piu' spazio al nome e
  meno al tipo; le card eventi sono alte `92` pixel e il titolo usa al massimo
  due righe.
- Cataloghi Qt italiano/inglese completi `1586/1586`; schema SQLite ancora
  `16`.

## Stati Parziali Qualita' Cielo 1.32.6

- `homeObservingOverview.deepSky` usa `state: partial` e label `Parziale` quando
  esiste un diagnostico di categoria basato sul meteo ma `SkyQuality` e'
  assente. `scoreValue` resta disponibile al backend; la QML usa un badge ambra
  invece del colore dello score.
- Senza Bortle il suggerimento dichiara che la visibilita' degli oggetti deboli
  deve essere verificata; una trasparenza sotto `40` resta esplicitamente
  limitante senza nascondere l'assenza dell'inquinamento luminoso.
- `_schedule_viirs_sky_quality_refresh()` classifica la cache prima del gate
  Earthdata. Una cache fresca non avvia rete; una cache stale senza account
  verificato non avvia rete, resta utilizzabile e produce un avviso visibile in
  Meteo.
- Confidenza della misura e freschezza cache restano separate: la correzione non
  declassa il campo `confidence` del dato VIIRS reale salvato.
- Cataloghi Qt italiano/inglese completi `1590/1590`; schema SQLite ancora `16`.

## Localizzazione Completa 1.30.0

- `TranslationManager` viene installato prima del controller e del caricamento
  QML; italiano e' lingua sorgente/fallback e i pack sono scoperti dai file
  `<codice>.json`, senza una lista di lingue in Python, QML o packaging.
- Ogni lingua usa `<codice>.json` per metadata, formati e contenuti editoriali,
  `<codice>.ts` per i messaggi QML/Python e `<codice>.qm` per il runtime.
- `translationManager` espone automaticamente alla barra laterale le lingue
  scoperte; `engine.retranslate()` aggiorna live i binding `qsTr()`.
- La preferenza `language` condivide `user_preferences.json` e viene aggiornata
  atomicamente preservando le altre chiavi.
- Le stringhe Python sono lazy e i servizi interni consumano valori canonici;
  date, numeri e payload vengono renderizzati solo al boundary Qt/QML.
- `astro_viewer/translations` contiene pack completi `it` ed `en`; PyInstaller
  include l'intera directory e quindi acquisisce anche nuovi pack senza cambiare
  la spec.
- Gli updater estraggono `1586` messaggi per lingua, preservano le traduzioni
  gia' revisionate, rifiutano cataloghi incompleti o placeholder incompatibili
  e producono output idempotente.
- La review successiva ha corretto la terminologia astronomica inglese, i nomi
  IAU delle costellazioni, i caratteri invisibili nei contenuti, la sicurezza
  per l'osservazione solare, `R.A.` e l'ordinamento localizzato dei filtri.
- I test di regressione coprono ora anche label dentro oggetti QML, termini
  editoriali revisionati, assenza di `U+200B` e sorting dopo il rendering.
- L'aggiunta del francese richiede solo `fr.json`, `fr.ts` e `fr.qm`, seguendo
  `docs/LOCALIZATION.md`; nessuna modifica applicativa e' necessaria.
- La barra di navigazione usa uno `ScrollView`, mantenendo selettore lingua e
  riepilogo sessione accessibili anche all'altezza minima supportata.

## Log Osservazioni 1.28.0

- `ObservationRepository` espone inserimento, elenco completo ordinato,
  modifica ed eliminazione; non esiste piu' il limite storico di 10 record.
- `ObservationLogService` valida data/ora locale, oggetto e voto `1-5`, rifiuta
  record futuri e costruisce entry QML e riepilogo senza dipendenze NSOM.
- Il controller espone `observationLog`, `observationLogSummary`, default locali
  e slot CRUD sincroni. Il vecchio `saveObservation` legato all'oggetto
  selezionato e `observationHistory` sono stati rimossi.
- La UI permette ricerca su oggetto, luogo, setup e note, filtro per voto,
  inserimento, modifica ed eliminazione con conferma.
- La tabella `ObservationHistory` non cambia schema; bootstrap, copia runtime e
  preservazione dei dati utente restano invariati.

## Catalogo Canonico 1.27.0

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
- Lo schema SQLite corrente e' `16`; la versione `14` ha introdotto il flag
  riduttori, la `15` la cache orbitale e la `16` la proprieta' persistente dei
  seed Equipment e la migrazione del profilo `Default`. Il bootstrap migra e
  rimuove `MessierObject`, valida
  identita', riferimenti e primarie dei seed e distingue contenuti editoriali
  gestiti da import personalizzati.
- I seed correnti sono `catalogue_objects_seed.csv` e
  `catalogue_designations_seed.csv`: 110 Messier e 109 Caldwell, senza
  sovrapposizioni per definizione del Caldwell originale.
- `catalogue_objects_seed.csv` abilita `imaging_reducer_recommended` su 53
  target estesi. Il flag e' indipendente dalla tassonomia e non entra in score
  o ranking.
- La UI espone 228 righe complessive: 219 target cielo profondo e 9 corpi del
  Sistema Solare. Il filtro Caldwell contiene C1-C109 in ordine naturale.
- Il toggle Home `Solo suggeriti ora` usa tutti gli ID in `skyCompass.targets`
  per filtrare piano e alternative senza cambiare ordine o ranking. Resta attivo
  durante i tick live e si spegne automaticamente quando il payload non ha
  target; i filtri per categoria e i conteggi operano sul sottoinsieme corrente.
- Tutti i tipi raw dei 219 target confluiscono nelle classi NSOM esistenti. Le
  17 nebulose planetarie usano `PLANETARY_NEBULA`; i 3 resti di supernova usano
  `DIFFUSE_NEBULA`. Caldwell non introduce categorie Equipment o nuovi pesi.
- `object_descriptions_seed.csv` copre tutti i 228 target selezionabili. Le 180
  note prima duplicate sono ora specifiche per oggetto; i Caldwell includono
  contesto misurabile e il Sole espone una procedura di sicurezza esplicita.
- Le righe seed di `ObjectDescription` e `ObjectCuriosity` usano
  `is_builtin = 1` e vengono aggiornate dal bootstrap. L'importatore descrizioni
  assegna `is_builtin = 0`, quindi le righe personalizzate vengono preservate.
  Il CSV deve restare UTF-8 senza BOM per il loader `csv.DictReader` corrente.
- `ObjectCuriosity` e `object_curiosities_seed.csv` coprono gli stessi 228
  target con testi italiani specifici, fonte e URL: 228 testi unici, 227 URL
  verificate e nessun ingresso in NSOM, Equipment o ranking.
- `object_images_seed.csv` usa un JPEG RGB locale `512 x 512` dedicato per
  ognuno dei 219 target profondi: 200 2MASS, 15 Pan-STARRS1 e 4 SkyMapper DR4,
  tutti da CDS `hips2fits` con URL esatta, attribuzione e licenza ODbL nel seed.
- I nove target del Sistema Solare usano altrettanti JPEG RGB `512 x 512`
  derivati da immagini PIA NASA/JPL, con pagina sorgente e credito missione. Le
  immagini sono statiche e processate, non descrivono fase o aspetto corrente.
- Il dettaglio Home e Catalogo mostra curiosita', fonte e credito immagine
  cliccabili. Il bootstrap sostituisce i vecchi SVG deep-sky e Sistema Solare
  gestiti da NightScope ma conserva righe immagine personalizzate dall'utente.
- `sync_catalogue_images.py --check` e `sync_solar_system_images.py --check`
  validano offline tutti gli asset;
  `audit_curiosity_sources.py` ricontrolla le fonti via rete. La policy completa
  e' in `docs/IMAGE_ASSET_POLICY.md`; DSS non e' usato.

## Equipment 1.27.0

- La pagina `Filtri e riduttori` usa due cataloghi affiancati con ricerca e
  layout responsive coerente con `Oculari e Barlow`.
- Il seed contiene 48 filtri visuali unici di 6 produttori e 24
  riduttori/correttori di 7 produttori; provenienza e riferimenti sono in
  `astro_viewer/data/DATA_SOURCES.md`.
- I filtri conservano classe, banda/lunghezza d'onda, trasmissione e apertura
  minima. Il barilotto non e' modellato e le classi colorate identificano il
  colore specifico. I riduttori conservano fattore, sistema e modelli
  compatibili, connessione, backfocus, uso visuale/fotografico e correzione del
  campo.
- `ReducerTelescopeCompatibility` conserva 16 associazioni esatte tra riduttori
  dedicati e `TelescopeModel`; i riduttori universali non ricevono associazioni
  artificiali. Il campo descrittivo dei modelli resta disponibile alla UI.
- I riduttori creati dall'utente usano la stessa relazione normalizzata: il
  form offre ricerca e selezione multipla sui 133 modelli di telescopio, il
  repository valida gli ID e i collegamenti sopravvivono al reseed.
- Filtri e riduttori possono essere assegnati e rimossi dal profilo attivo.
  `equipmentChanged` aggiorna immediatamente anche un dettaglio osservativo
  aperto, ma non ricalcola NSOM o capacita'.
- Tutti i cataloghi Equipment espongono `is_builtin`, `seed_key` e
  `is_user_modified`. Le voci seed mostrano `Modifica` ma non `Elimina`; il
  repository consente le correzioni, marca l'override e continua a bloccare la
  cancellazione. Le voci create dall'utente restano modificabili ed eliminabili
  dopo aver rimosso i collegamenti ai profili.
- Le connessioni Equipment abilitano le foreign key. La migrazione elimina
  assegnazioni orfane nelle sei tabelle profilo e i conteggi d'uso considerano
  profili validi distinti, senza duplicare il telescopio tra campo legacy e
  relazione molti-a-molti.

## Raccomandazione Filtri 1.27.1

- `CatalogueObject` espone `best_filter_class`, `fallback_filter_class` e
  `optional_color_filter_class`; le 219 righe conservano invariati tutti i
  metadati astronomici precedenti.
- Il seed assegna una preferenza primaria a 35 nebulose: 12 UHC, 20 OIII e 3
  H-beta. Il fallback e' riservato ad alternative equivalenti, non allo stacking.
- Luna e Venere preferiscono polarizzatore con ND come alternativa. Marte,
  Giove e Saturno preferiscono contrasto con Moon & Skyglow come alternativa.
  Gli eventuali colori, incluso il giallo per Urano e Nettuno, restano
  raccomandazioni secondarie separate.
- `FilterRecommendationService` opera solo se il setup target-specifico sceglie
  un telescopio reale. Il catalogo completo e l'apertura verificano prima la
  classe; soltanto i filtri del profilo attivo possono risultare disponibili.
- Il match scarta prodotti sotto la relativa `minimum_aperture_mm` e preferisce
  la soglia valida piu' alta prima dei tie-break per nome e ID. Il colore giallo
  opzionale per Urano e Nettuno richiede almeno `280 mm`.
- L'ordine resta primaria/fallback, ma se nessun prodotto posseduto e' adatto
  viene mostrata soltanto la classe primaria utilizzabile come
  `non disponibile`, senza testo ambiguo con due classi.
- `observingObjectDetail_v3` trasporta un payload sanitizzato con `primary`,
  `optionalColor` e il ramo separato `reducerRecommendation`; il dettaglio
  Catalogo non mostra configurazioni osservative e resta invariato.
- Il runtime usa direttamente il catalogo canonico senza migrazioni dei vecchi
  duplicati per barilotto e senza la classe `COLOR_UNSPECIFIED`.
- Questa funzione non modifica EquipmentService, ObserverCapability, score,
  ranking, Planner, Home, Sky Compass o NSOM.

## Raccomandazione Riduttori 1.27.0

- `ReducerRecommendationService` opera solo se il target abilita
  `imaging_reducer_recommended` e la configurazione consigliata contiene un ID
  telescopio.
- Il match richiede `imaging_compatible` e un collegamento esatto
  `ReducerTelescopeCompatibility`; le descrizioni testuali non vengono
  interpretate.
- Prima vengono cercati i riduttori nel profilo attivo. Se non esiste un match
  posseduto, i prodotti compatibili del catalogo sono mostrati come
  `non disponibili`; senza match esatto la riga non compare.
- Piu' match sono elencati in ordine deterministico. Non viene scelto un
  presunto migliore senza dati su camera, sensore, image circle e backfocus.
- La funzione non calcola focale o campo risultanti e non modifica
  EquipmentService, ObserverCapability, score, ranking, Planner, Home, Sky
  Compass o NSOM.

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
  statico ed e' numerico interno; QML riceve soltanto il label localizzato
  `atmosphericTransparency`.
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
- Prima di configurare la localita', riepilogo, Luna, alternative e prossimi
  eventi mostrano uno stato non disponibile senza riusare valori dimostrativi.
- Con localita' e meteo ma senza qualita' cielo reale, la scheda cielo profondo
  mostra `Parziale`; il suo score interno non viene esposto come valutazione
  completa.
- La metrica primaria cielo profondo usa la trasparenza atmosferica; Bortle e
  fondo cielo restano nella metrica separata e nel relativo suggerimento.

### Meteo

- Copertura nuvolosa e dettaglio orario mostrano le prossime 24 ore.
- Le ore della notte osservativa sono evidenziate senza conflitto con l'ora
  selezionata.
- Scrollbar orizzontale del dettaglio e' nascosta.
- AOD e OpenAQ hanno semantica/freschezza esplicita.
- `Trasparenza notturna` usa il label atmosferico da meteo e non incorpora la
  penalita' Bortle mostrata nella metrica adiacente.
- Prima della localita', metriche e timeline mostrano `n/d` e una richiesta di
  configurazione invece di valori meteo fittizi.

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
- I passaggi ISS usano una sorgente a 10 giorni separata dall'orizzonte annuale
  e vengono uniti soltanto nella proiezione cronologica finale.
- Le comete usano una sorgente a 90 giorni; ogni riga rappresenta una finestra
  multi-notte aggregata, non un evento giornaliero e non un oggetto catalogo.
- La data compatta puo' occupare al massimo due righe, cosi' gli intervalli
  cometari non vengono troncati.
- Il contratto distingue `startsAt`, `endsAt`, `peakAt`, fatti operativi e
  metadati sorgente; non assegna un target catalogo a ISS o comete.
- Prima della localita', conteggi, filtri e timeline sono disabilitati o `n/d`
  e spiegano che la posizione e' necessaria.

### Catalogo

- Lista senza colonna mensile ridondante.
- Filtro `visibili nel mese` resta disponibile soltanto con una localita'
  valida; il controller impedisce di abilitarlo anche fuori dalla QML.
- Dettaglio mostra `Visibile nel mese corrente` calcolato per posizione e mese
  locali, indipendentemente dal filtro lista.
- Tipi e modalita' osservative sono localizzati in italiano.

## Cache e Refresh

- VIIRS viene rivalidato ogni 7 giorni mantenendo il valore stale in caso di
  errore NASA.
- Una cache VIIRS stale resta disponibile anche senza Earthdata verificato, ma
  Meteo mostra che deve essere aggiornata; una cache fresca non mostra avvisi.
- `SkyQualityEstimate` conserva soltanto cache VIIRS reali; le righe storiche
  non VIIRS vengono eliminate quando il servizio viene costruito. Se non
  esiste cache e non e' presente un dataset reale opzionale, Bortle e' `n/d`.
- AOD usa TTL 18 ore per le misure positive e 6 ore per le sole assenze reali
  `no_granules`/`no_valid_pixel`; autenticazione, ricerca, download e parsing
  falliti restano ritentabili e non vengono memorizzati.
- L'estrazione AOD decodifica il bit field MAIAC, prova pixel esatto, 5x5 e
  11x11 e richiede almeno tre pixel affidabili nelle aree. Risultato, log e UI
  conservano raggio e distanza del pixel valido piu' vicino.
- AOD e VIIRS riusano dati validi entro 500 metri per assorbire jitter della
  posizione Windows.
- Risultati provider con location key stale vengono scartati.
- AOD/OpenAQ completati ricalcolano i consumer NSOM senza ripetere effemeridi o
  geometria lunare.
- Open-Meteo conserva la cache sui fallimenti retryable e programma il retry
  controllato.
- `OrbitalElementCache` conserva OMM/TLE per provider e oggetto. Per la ISS il
  TTL e' 6 ore; se CelesTrak non risponde, un elemento resta utilizzabile fino
  a 3 giorni dalla propria epoca, poi i passaggi non vengono inventati.
- Il timer ISS ricalcola ogni ora la finestra mobile usando la cache: non
  trasforma la cadenza di calcolo in una richiesta CelesTrak oraria.
- La stessa tabella conserva il payload globale SBDB sotto provider `jpl_sbdb`
  e chiave `observable_comet_candidates`. TTL rete `24 ore`, fallback massimo
  `7 giorni`, retry fino a 3 tentativi con backoff sui `5xx`.
- Il timer transitorio globale resta orario per la ISS; la cache risultati del
  motore evita di ricalcolare le comete prima del loro intervallo di 6 ore.

## Validazione 1.33.0

Eseguita nella venv corrente:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tools\run_checks.py --coverage --security
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
# pyside6-qmllint eseguito su tutti i file astro_viewer/app/ui/**/*.qml
git diff --check
```

Gli smoke QML italiano e inglese hanno usato database e preferenze distinti in
`TemporaryDirectory`; anche lo smoke backend ha usato un runtime temporaneo.
Nessun file runtime utente e' stato letto o modificato.

Risultati:

- `pip check`: nessuna dipendenza rotta.
- Ruff e compileall su applicazione e tool: puliti.
- Suite con coverage: `785 passed`, `613 warnings`, `7 subtests passed` in
  `112,92 s`; coverage runtime `84%` su `15.212` statement.
- `pip-audit`: nessuna vulnerabilita' nota nell'ambiente installato.
- Bandit: `0 high`, `26 medium`, `12 low`; SQL dinamico e subprocess sono stati
  revisionati manualmente.
- Cataloghi Qt italiano/inglese completi e compilati: `1595/1595` ciascuno.
- Test traduzioni: `15 passed`.
- `qmllint`: exit `0` su tutti i 30 QML; restano warning statiche
  `unqualified access` documentate.
- Immagini: `219` JPEG deep-sky e `9` JPEG Sistema Solare validi.
- Smoke standard e QML italiano/inglese: exit `0` in runtime temporanei.
- Manuale verificato con Chrome headless a larghezza desktop e mobile `390 px`;
  nessun overflow orizzontale, cambio IT/EN e titoli corretti.
- Schema SQLite invariato a `16`; nessuna migrazione. Nessun dato sintetico e'
  stato reintrodotto.
- `git diff --check`: pulito.
- Dist corrente `1.32.3`; dist `1.33.0` non rigenerata.

I warning provengono dalle deprecazioni `dtype` e `shape` interne a
Skyfield/NumPy gia' note. I `ResourceWarning` SQLite emersi sotto coverage erano
fixture test che non chiudevano esplicitamente due connessioni e sono stati
corretti; il gate finale non li riporta.

## Regole Operative

- Usare sempre `.venv`.
- Eseguire test in parallelo con al massimo `pytest -n 4`; non usare `-n auto`.
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
- `docs/LOCALIZATION.md`
- `docs/RELEASE_CANDIDATE_REVIEW.md`
- `docs/RELEASE_CHECKLIST.md`
- `docs/VISUAL_CHECKLIST.md`
- `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
- `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
- `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`
- `docs/TESTING.md`
- `docs/IMAGE_ASSET_POLICY.md`

Il changelog conserva la cronologia delle vecchie fasi di migrazione; non usare
quelle entry come descrizione del runtime corrente.
