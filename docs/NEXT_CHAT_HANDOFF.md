# NightScope - Next Chat Handoff

Aggiornato: 2026-07-25

## Stato Versioni

- Versione sorgente: `1.41.0`
- Repository pubblico: `https://github.com/beastmen84/NightScope`
- Release pubblica stabile: `v1.40.1`, tag sul commit sorgente
  `7b6da6d358f28cacb8836b4520ae6cb407d98fc5`.
- Asset: `NightScope-v1.40.1-windows-x64.zip`, SHA-256
  `7001aa1aa3cee8139602e4e97cdf9955f9055456585260f1aba5b3b55c42da97`.
- Distribuzione Windows corrente: `1.40.1`, pubblicata su GitHub.
- Metadati, tag, asset e digest della release `1.40.1` verificati su GitHub il
  2026-07-24. Il sorgente `1.41.0` non e' ancora distribuito come release.
- Commit sorgente della release pubblica validato:
  `7b6da6d Fix NSOM recommendation input boundaries`

La localizzazione spagnola e' stata introdotta nel sorgente `1.34.0`; il
follow-up di hardening e le guide provider appartengono a `1.34.1`. I fix
Earthdata e layout appartengono a `1.34.2`; la review editoriale italiana e
inglese descritta sotto appartiene al sorgente `1.34.3`.

## Catalogo NGC e ammissione raccomandazioni

Il catalogo canonico contiene ora 7.585 target deep-sky fisici. Il snapshot
OpenNGC al commit `36cb178a` fornisce 7.839 designazioni NGC utilizzabili,
risolte in 7.571 target fisici: 205 identita' riusano oggetti
Messier/Caldwell e 7.366 sono nuovi target NGC-only. `NGC 412`, marcato
`NonEx`, non viene importato. Alias dello stesso catalogo, inclusi NGC 6/20 e
NGC 650/651, condividono identita', preferenza e calcoli.

I 7.366 target NGC-only partono con `Home` disattivato; le identita'
Messier/Caldwell mantengono il default attivo anche sotto designazione NGC. Le
scelte utente restano in `CatalogueRecommendationPreference`. Lo schema 19
rimuove il vecchio vincolo un target/una designazione per catalogo e la
migrazione da schema 18 conserva gli override. Descrizione e curiosita' NGC-only
mostrano `Work in progress`; non sono state create migliaia di traduzioni o
fonti editoriali fittizie.

`CatalogueRepository` applica il flag effettivo in SQL prima che Skyfield legga
coordinate o calcoli visibilita'. Raccomandazioni, visibilita' mensile e
geometria lunare dei target fissi usano batch NumPy/Skyfield con fallback
scalare identico su Windows e Linux. La join delle preferenze usa la chiave
`NOCASE` indicizzata: la query tutto-attivo scende da circa 18,9 s a 0,15 s.
Nel benchmark Windows end-to-end, il profilo con i 219 default richiede 7,55 s;
il caso estremo con tutti i 7.585 target attivi richiede 12,45 s, inclusi
catalogo mensile, eventi, Equipment, NSOM, Planner e Sky Compass. L'incremento
di circa 4,9 s resta compatibile con il worker esistente; non e' stato
introdotto multiprocesso.

La pagina catalogo usa una `ListView` virtualizzata, espande tutte le 7.839
designazioni sotto il filtro NGC, mantiene l'alias esatto nel dettaglio e
accetta codici compatti come `NGC1` senza far coincidere `C23` con `NGC 23`.
Il flag `Home` usa ora un `QAbstractListModel`: il click aggiorna soltanto le
righe che condividono l'`object_id`, senza ricostruire 7.594 mappe QML. Un
debounce da 200 ms conserva soltanto lo stato piu' recente, ammette un solo
worker e scarta snapshot con generazione, localita' o input runtime obsoleti.
Il worker prepara anche Equipment, inquinamento luminoso, geometria lunare,
NSOM, Best Object, Planner e Sky Compass; la UI applica lo snapshot gia'
calcolato. Nel benchmark tutto-attivo, con 5.452 target osservabili correnti,
il click impiega circa 27 ms, il worker circa 3,2 s e l'applicazione UI circa
6 ms. Thread e segnali sono condivisi da Windows e Linux.

Il snapshot, l'hash, l'attribuzione OpenNGC e il testo completo
CC-BY-SA-4.0 sono inclusi nei sorgenti e nei bundle. I cataloghi Qt IT/EN/ES
contengono 1.731 voci finite e zero incomplete.

Sul sorgente finale il gate `tools/run_checks.py --fast` passa con 960 test,
643 warning Skyfield/NumPy gia' noti, 10 subtest, smoke backend, QML normale e
Red Night Vision. Il gate di sicurezza immediatamente precedente ha riportato
84% di copertura su 16.429 statement runtime e nessuna vulnerabilita' nota.

## Esecuzione sorgente e dist Linux 1.41.0

NightScope e' stato installato ed eseguito da sorgente su Ubuntu 26.04 LTS con
Python 3.14.4, PySide/Qt 6.11.1 e sessione GNOME/Wayland. D-Bus utente,
GeoClue 2 e Secret Service risultano disponibili; Qt seleziona `wayland` per
l'avvio normale e carica anche il fallback `xcb` dopo l'installazione delle
librerie native documentate nel README.

Il teardown esplicito del motore QML elimina i binding verso context object
null osservati alla chiusura su Linux. Il generatore licenze risolve la licenza
Python dalla standard library Linux e mantiene invariato il confronto esatto
dell'archivio nell'ambiente Windows. Il gate Ruff ha ora una configurazione
esplicita e resta stabile con le versioni 0.15 e 0.16.

Il gate `tools/run_checks.py --fast` ha chiuso con `923 passed`, `1 skipped`,
`642 warnings` note e `10 subtests`; smoke backend/QML, avvio reale Wayland e
sonda XCB sono passati.

`packaging/build_linux_debian12.sh` usa Docker o Podman e costruisce il
candidate PyInstaller dentro Debian 12/Python 3.12, con baseline glibc 2.36.
La dist locale `1.41.0` contiene `5.415` file per `575 MiB`; audit, backend,
QML normale/rosso dentro Debian 12 e Debian 13, Wayland normale/rosso e XCB
sull'host sono passati. Il runtime hook Linux impedisce di mischiare i moduli
GIO/GVFS dell'host recente con la GLib Debian inclusa. Lo spec include Secret
Service ma non il backend keyring Windows.

`tools/generate_linux_native_notices.py` usa il `COLLECT-00.toc` della stessa
build e `dpkg` per inventariare `146` ELF nativi, `84` pacchetti binari,
`63` pacchetti sorgente Debian e il runtime CPython. Il bundle contiene `64`
avvisi copyright e `15` testi di licenza comuni. Tutti i `64` URL Debian
Sources/CPython unici sono stati verificati. L'audit rifiuta file ELF non
inventariati, entry stale, hash diversi, URL sorgente non validi o testi
mancanti.

`packaging/archive_linux.sh` ha prodotto
`NightScope-v1.41.0-debian-12-x64.tar.gz` (`272.546.505` byte, `260 MiB`) e il
checksum adiacente, SHA-256
`24490604996561e90b2b3e78ed1d2be1b4530d6ec679190ca81fe32c5f396ef5`.
Il flusso documentato nel README e' stato ripetuto da una directory temporanea
pulita con checksum, estrazione, audit, backend e QML normale/rosso passati.

Il formato pubblico scelto e' il tar gzip Debian 12 x86-64, non un binario
Linux universale. La stessa build e' stata verificata anche su Debian 13 e
Ubuntu 26.04. Va pubblicata come GitHub pre-release: una release stabile
Linux-only verrebbe proposta dall'Update Manager anche ai client Windows
1.40.1. Prima della pubblicazione restano commit/tag e upload degli asset
GitHub. Restano come prove opzionali una sessione
interattiva save/read/delete di Secret Service e una richiesta GeoClue
autorizzata con coordinate reali.

## Recommendation e confine NSOM 1.40.1

Il parser condiviso di `TargetObservationTraits` accetta ora direttamente il
formato Skyfield con simbolo dei gradi. Equipment e difficolta' consumano
quindi l'altezza runtime reale invece del fallback zero.

Il contesto urbano di `ObservationConditionsService` resta una proiezione di
presentazione con score, nota e ordinamento compatibili. Non modifica piu'
`visible` e non esclude candidati prima dei read model: Home, Planner, Best
Object e Sky Compass ricevono il target grezzo e applicano una sola volta il
fattore NSOM di sky background. Le prove reali a Nairobi, Roma e Sydney hanno
conservato rispettivamente `195/195`, `148/148` e `165/165` candidati, con tutte
le altezze interpretate. La matrice Equipment rigenerata copre 375 combinazioni
senza violazioni.

Il gate completo `tools/run_checks.py --security` e' passato: `917 passed`,
`642 warnings` note, `10 subtests`, coverage `84%` su `16.032` statement,
snapshot MPC, smoke backend/QML normale/rosso e audit dipendenze superati,
senza vulnerabilita' note.

## Backend Credenziali Linux Secret Service 1.40.0

`credential_backend` e' ora il confine condiviso da Earthdata e OpenAQ.
Windows conserva il dispatcher `keyring` esistente e nella venv verificata usa
`WinVaultKeyring`. Su Linux NightScope costruisce direttamente
`keyring.backends.SecretService.Keyring` e dichiara lo storage sicuro
disponibile soltanto se Secret Service e' raggiungibile o attivabile via D-Bus.

Configurazioni Linux che selezionano backend null, fail, plaintext o plugin
arbitrari non vengono usate. In assenza di Secret Service i controlli
credenziali riportano l'archivio di sistema come non disponibile; password e
API key non ricadono mai su JSON o SQLite. `keyring 25.7.0` dichiara gia'
`SecretStorage>=3.2` e `jeepney>=0.4.2` come dipendenze condizionali Linux.

Il gate completo `tools/run_checks.py --security` e' passato: `912 passed`,
`642 warnings` note, `10 subtests`, coverage `84%` su `16.036` statement,
snapshot MPC da `2.683` righe, smoke backend/QML normale/rosso e audit
dipendenze superati, senza vulnerabilita' note. La suite focalizzata
credenziali ha chiuso `25 passed`; quella estesa con runtime, tooling e scenari
di release `84 passed`.

I prossimi step Linux sono il packaging nativo e le prove interattive reali di
Secret Service e GeoClue su un desktop Linux.

## Percorsi Runtime Linux XDG 1.39.0

`RuntimePaths` separa dati, configurazione, cache e stato prima della costruzione
dei servizi. Su Linux usa rispettivamente
`~/.local/share/NightScope`, `~/.config/NightScope`,
`~/.cache/NightScope` e `~/.local/state/NightScope`, rispettando soltanto
override `XDG_*_HOME` assoluti. `NIGHTSCOPE_RUNTIME_DIR` ha priorita' e continua
a co-localizzare tutto per test e smoke.

Windows resta invariato: root del progetto da sorgente e directory
dell'eseguibile nella dist portabile. `AppController` riceve percorsi espliciti
per preferenze, cache posizione e cache NASA AOD, ma mantiene fallback
database-adjacent per i costruttori esistenti.

La migrazione copia da un runtime portabile precedente database, backup,
preferenze e cache nelle nuove directory senza sovrascrivere file XDG gia'
presenti. Database, schema, scoring, raccomandazioni e UI non cambiano. Il
prossimo step Linux e' la verifica e dichiarazione del backend
`keyring`/Secret Service; packaging e prova GeoClue D-Bus reale restano
successivi.

Il gate completo `tools/run_checks.py --security` e' passato: `907 passed`,
`642 warnings` note, `10 subtests`, coverage `84%` su `16.024` statement,
snapshot MPC da `2.683` righe, smoke backend/QML normale/rosso e audit
dipendenze superati, senza vulnerabilita' note. La suite focalizzata su runtime,
database, piattaforma, posizione, tooling e scenari di release aveva inoltre
chiuso `150 passed`.

## Controllo Aggiornamenti 1.38.0

`UpdateManager`, separato da `AppController`, legge il `VERSION` già incluso
nel bundle e interroga una sola volta per sessione l'endpoint pubblico
`releases/latest` di GitHub. Il controllo parte 750 ms dopo il caricamento QML
su un thread daemon, usa timeout di 4 secondi e non mostra errori se rete o API
non sono disponibili.

Solo una release stabile con versione numericamente successiva e URL HTTPS del
repository ufficiale può attivare il popup. Il dialogo mostra versione
installata e disponibile, apre la pagina GitHub nel browser e consente di
rimandare oppure salvare `ignored_update_version` in `user_preferences.json`.
L'opzione di esclusione preserva tutte le altre preferenze. Il popup e'
localizzato in italiano, inglese e spagnolo e usa i componenti tematizzati
anche in Red Night Vision.

La richiesta reale ha restituito correttamente `v1.37.0` per un client
`1.36.0` e nessun aggiornamento per `1.38.0`. La sonda QML a `1040 x 700`, in
spagnolo e Red Night Vision, ha aperto il dialogo al centro con geometria
`560 x 204`. I cataloghi IT/EN/ES contengono `1.697` voci complete e zero
incomplete.

Il gate completo `tools/run_checks.py --security` e' passato: `889 passed`,
`642 warnings` note, `10 subtests`, coverage `84%` su `15.965` statement,
snapshot MPC da `2.683` righe, smoke backend/QML normale/rosso e audit
dipendenze superati, senza vulnerabilita' note.

## Red Night Vision 1.37.0

La barra laterale termina con un selettore persistente `Normale` / `Visione
rossa`, collocato sotto la card `Stasera`. `AppearanceManager` conserva
`red_night_vision_enabled` in `user_preferences.json` senza passare da
`AppController`; il cambio e' esclusivamente visuale e non ricalcola dati.

Tutti i colori QML sono ora token di `AppTheme`. La palette rossa copre pagine,
componenti, hover/focus, Canvas, bussola, fase lunare e icone SVG, colorate da
`NightVisionIcon` con `QtQuick.Effects`. Le fotografie di dettaglio, i crediti
associati e le miniature del piano Home non vengono caricati e lasciano il
layout in modalita' rossa. Il manuale e' intenzionalmente escluso da questo
passaggio. `DarkCheckBox` e i campi `DarkTextField` impediscono ai controlli Qt
nativi di introdurre indicatori grigi nei form aperti durante l'uso notturno.

La matrice offscreen delle 13 viste a `1240 x 820`, incluso un oggetto reale
nel dettaglio, ha misurato nel tema rosso `G=74`, `B=61` come massimi, zero
pixel oltre le soglie `G>90` o `B>80` e nessuna sorgente fotografica caricata;
lo stesso render normale raggiunge `G=247`, `B=255`. Anche il layout minimo
`1040 x 700` e il selettore spagnolo sono stati verificati. Un render con il
backend Windows nativo conferma inoltre che le icone SVG restano visibili dopo
la colorazione `MultiEffect`; il backend Qt `offscreen` non renderizza gli
shader e non viene quindi usato per validare la visibilita' delle icone. Il
runner standard include ora uno smoke QML rosso separato. Traduzioni IT/EN/ES:
`1.692` voci complete ciascuna.

Il test della prima dist ha portato due correzioni sorgente: il link della
fonte Curiosita' incorpora il token colore nel rich text e reagisce allo switch
rosso; il nome della posizione attiva e' separato dalle coordinate e puo'
andare a capo senza ellissi. La prova QML con il nome lungo dell'osservatorio
Orion ha restituito `truncated=False`; il link Luna ha prodotto
`style="color:#d94a3d"`. La rimozione della vecchia stringa combinata porta i
cataloghi IT/EN/ES a `1.692` voci complete e zero incomplete.

Il gate completo `tools/run_checks.py --security` e' stato ripetuto dopo il
follow-up: `867 passed`, `642 warnings` note, `10 subtests`, coverage `84%` su
`15.823` statement, `qmllint` con exit code zero e nessuna vulnerabilita' nota.

## Ricerca Localita' GeoNames E MPC 1.36.0

La card Localita' combina ora citta' GeoNames e osservatori MPC in una ricerca
offline unica. `LocationRepository` mantiene i due domini separati, assegna
priorita' al codice MPC esatto e restituisce un contratto di risultato comune.
La selezione MPC passa a `LocationService`, che usa le coordinate del catalogo
e risolve il fuso IANA offline con `timezonefinder`.

`mpc_observatories_seed.csv` e' uno snapshot del 2026-07-22 generato dall'API
ufficiale MPC. Contiene `2.683` postazioni terrestri fisse; satelliti, roving,
geocentro e record non superficiali sono esclusi. Il tool
`astro_viewer/tools/update_mpc_observatories.py` aggiorna lo snapshot e la
modalita' `--check` lo valida senza rete. Longitudine e costanti di parallasse
originali sono conservate; latitudine geodetica e quota sono derivate su WGS84.

Lo schema passa a `17` con la tabella `MpcObservatory`. Bootstrap e preflight
usano `DataImportLog`, quindi un database esistente viene migrato e popolato
senza perdere dati utente. PyInstaller include il seed e l'audit della dist lo
considera obbligatorio. UI, manuale e traduzioni IT/EN/ES sono allineati. La
dist non e' stata rigenerata; la release pubblica resta `1.34.2`.

Il gate completo `tools/run_checks.py --security` e' passato in `262,9 s`:
snapshot MPC da `2.683` righe, smoke backend/QML e audit di sicurezza superati,
senza vulnerabilita' note. Dopo l'ultima regressione sul ranking, la suite
finale conta `853 passed`, `642 warnings` note, `10 subtests` e coverage runtime
`84%` su `15.764` statement. I cataloghi IT/EN/ES contengono `1.691` traduzioni
complete e nessuna voce incompleta.

## Posizione Di Sistema Linux 1.35.1

La posizione automatica usa ora un contratto neutro rispetto alla piattaforma.
Su Windows `LocationService` conserva gli stessi provider preciso e
approssimato nello stesso ordine; su Linux seleziona
`GeoClueLocationProvider`, basato sul plugin Qt Positioning `geoclue2` e sul
desktop ID `io.github.beastmen84.NightScope`.

GeoClue richiede una singola posizione con timeout, valida coordinate e
accuratezza e normalizza errori di permesso, servizio, timeout e plugin assente.
Il risultato riusa reverse lookup citta' e timezonefinder offline. Il percorso
e' coperto con sorgenti Qt simulate e test indipendenti dall'host; resta da
eseguire il test D-Bus reale su un desktop Linux con GeoClue installato.

La preferenza canonica e' `use_system_location_on_startup`; il vecchio campo
Windows viene letto e migrato senza perdere il consenso. La pagina Localita',
i messaggi, il manuale e i cataloghi IT/EN/ES usano `Posizione di sistema`, con
testo specifico WinRT o GeoClue in base alle capacita'. `PySide6_Addons`,
Qt Positioning e `Qt6Positioning.dll` fanno ora parte del contratto dipendenze,
PyInstaller e licenze. Database, scoring, raccomandazioni e directory runtime
non sono cambiati; la dist non e' stata rigenerata.

Il gate completo `tools/run_checks.py --security` e' passato in `206,6 s`:
`841 passed`, `613 warnings` note, `10 subtests`, coverage runtime `84%` su
`15.615` statement, smoke backend/QML superati e nessuna vulnerabilita' nota.

## Confine Piattaforma 1.35.0

Il primo step Linux-ready introduce
`astro_viewer.app.platform_capabilities` come unico rilevamento della famiglia
del sistema operativo. Il valore immutabile viene costruito una sola volta da
`sys.platform` e pubblicato come `platformCapabilities` sia nell'avvio normale
sia nello smoke test QML.

Nello step `1.35.0`, Windows conservava integralmente il comportamento
precedente ed era l'unica piattaforma a dichiarare disponibile la posizione di
sistema. Linux e macOS erano riconosciuti ma riportavano provider `none`:
GeoClue, percorsi XDG, Secret Service e packaging Linux appartenevano ai
passaggi successivi. Lo stato corrente di GeoClue e' descritto nella sezione
`1.35.1` precedente.

Il gate completo `tools/run_checks.py --security` e' passato in `245,7 s`:
`832 passed`, `613 warnings` note, `10 subtests`, coverage runtime `84%` su
`15.465` statement, smoke backend/QML superati e nessuna vulnerabilita' nota.

## Review Editoriale Italiana E Inglese 1.34.3

Le `228` schede oggetto italiane e inglesi, i relativi fun fact, i cataloghi Qt
e il manuale sono stati ricontrollati con metriche di completezza e unicita',
LanguageTool e review manuale della terminologia. Le descrizioni e i fun fact
restano tutti unici per lingua; la somiglianza tra alcune note osservative
deriva da istruzioni tecnicamente condivise e non e' stata ridotta con
riscritture artificiali.

Sono stati corretti accordi e calchi italiani, separatori decimali angolari,
grammatica e terminologia inglese e le classificazioni di M84, M86, C51 e C53.
M78 ora evita esplicitamente filtri a banda stretta. Gli override inglesi e
l'overlay TS sono deterministici e coperti da regressioni. Il seed descrittivo
di C53 passa da `Elliptical galaxy` a `Lenticular galaxy`; schema SQLite,
scoring, raccomandazioni, database binario e dist non sono stati modificati. Il
bootstrap aggiorna un database esistente solo se tipo e descrizione di C53
corrispondono ancora esattamente ai vecchi valori seed; una descrizione
personalizzata viene preservata.

Il gate completo `tools/run_checks.py --security` e' passato in `163,5 s`:
`822 passed`, `613 warnings` note, `10 subtests`, coverage runtime `84%` su
`15.413` statement, smoke backend/QML superati e nessuna vulnerabilita' nota.
I cataloghi Qt IT/EN/ES contengono `1679` traduzioni finite e nessuna voce
incompleta; i test mirati di localizzazione e tooling hanno chiuso `35 passed`.

## Correzione Autorizzazione Earthdata 1.34.2

Un test controllato con un account Earthdata nuovo ha distinto due risposte del
flusso LAADS OPeNDAP: password errata produce `HTTP 401` con credenziali non
valide; credenziali corrette senza autorizzazione dell'app producono `HTTP 403`
con il segnale OAuth di pre-autorizzazione richiesta. Dopo l'autorizzazione, le
stesse credenziali superano il test.

`EarthdataConnectionTester` valuta ora il segnale di autorizzazione e il rifiuto
delle credenziali prima del fallback HTTP generico. Il controller puo' quindi
salvare `authorization_required=True`, mostrare lo stato `Autorizza` e abilitare
il pulsante `Autorizza app`; `Test connessione` resta disponibile per il secondo
controllo. Un `403` privo di segnali OAuth non viene reinterpretato. I log
registrano soltanto classificazione e codice HTTP, mai username o password.

Validazione del fix: `tools/run_checks.py --security` superato in `250,6 s`;
`821 passed`, `613 warnings` note e `10 subtests`, coverage runtime `84%` su
`15.410` statement, smoke backend/QML superati e nessuna vulnerabilita' nota.
Non sono stati rigenerati database o distribuzione Windows.

## Correzioni Layout 1.34.2

La griglia credenziali Earthdata usa ora `620` px, non `720`, come soglia della
singola card per mantenere affiancati nome utente e password. Nel dettaglio
evento la card con fatti, sorgente e freschezza usa entrambe le colonne quando
la pagina supera la soglia larga di `1160` px; sotto tale soglia resta su una
sola colonna. Il caso ISS e' stato renderizzato offscreen a `1600x1100`: la card
`Pass details` occupa la riga completa senza overflow o vuoti laterali.
Il gate completo successivo alle correzioni e' passato in `335,3 s`: `821`
test superati, `613` warning noti, `10` subtest, coverage runtime `84%`, smoke
backend/QML superati e nessuna vulnerabilita' nota rilevata da `pip-audit`.

## Hardening Da Review Profonda

Il passaggio `1.34.1` del 2026-07-21 ha corretto edge case riprodotti su OpenAQ,
Open-Meteo, Earthdata/VIIRS, refresh NASA AOD, cache IP, input Equipment, mese
Catalogo e avvio con directory log non scrivibile. I refresh OpenAQ, VIIRS e AOD
usano ora generazioni di richiesta; lo stato Open-Meteo e' isolato per thread e
il `NETRC` temporaneo Earthdata e' serializzato. VIIRS distingue errori provider
da vera assenza di granuli e OpenAQ non mette piu' in cache i fallimenti come
no-data.

La cache IP ha TTL 24 ore e viene indicata come gia' caricata. I numeri non
finiti vengono respinti sia dal controller sia dal repository Equipment. Il
mese iniziale del Catalogo viene riallineato dopo aver conosciuto la timezone
della localita', senza sovrascrivere una selezione esplicita dell'utente.
Schema SQLite, dati seed, scoring e raccomandazioni non sono cambiati. La `dist`
non e' stata rigenerata in questo passaggio.

## Guide Configurazione Provider

La pagina Provider dati contiene ora due guide numerate localizzate in italiano,
inglese e spagnolo. La guida Earthdata copre creazione e attivazione account,
compilazione di tutti i campi del profilo anche quando indicati come facoltativi,
salvataggio, test, autorizzazione LAADS OPeNDAP e ripetizione del test. Non viene
attribuito il blocco dei campi mancanti al solo VIIRS o al solo AOD: entrambi
usano il flusso Earthdata condiviso da NightScope.

La guida OpenAQ porta dalla registrazione alla pagina account e alla sezione
`API Keys`, quindi a salvataggio e test in NightScope. La griglia QML passa a
una colonna quando lo spazio effettivo non basta; le card sono state renderizzate
in IT/EN/ES a `1400x900` e `774x900`. Il pulsante spagnolo `Autorizar aplicación`
e' stato allargato dopo il controllo visuale. Il manuale multilingue replica le
procedure con sequenze numerate. Database, schema, credenziali locali e `dist`
non sono stati modificati.

Validazione conclusiva del passaggio:

- `tools/run_checks.py --security`: superato in `218,6 s`;
- suite con coverage: `817 passed`, `613 warnings`, `10 subtests passed`,
  coverage runtime `84%` su `15.403` statement;
- `pip-audit`: nessuna vulnerabilita' nota;
- cataloghi Qt IT/EN/ES: `1679` finite, `0` unfinished per lingua;
- smoke QML separati IT/EN/ES: tutti superati in runtime temporanei;
- `qmllint`: `31` file, `0` failure, `760` warning statici noti;
- immagini: `219` deep-sky e `9` Sistema Solare valide;
- Bandit invariato: `0 high`, `26 medium`, `12 low`.

## Commit Recenti

- `4193e11 Add localized provider setup guides`
- `6256d5f Bump source version to 1.34.1`
- `1513201 Fix provider and runtime edge cases`
- `64f3caf Fix Spanish localization review findings`
- `5a1faa6 Add reviewed Spanish localization`
- `72342fa Document public 1.33.2 release`
- `ecf6232 Update handoff after bundle validation`
- `9c17204 Reject runtime state in release bundles`
- `e4bdd19 Create FUNDING.yml`
- `3baa6a6 Update handoff for licensing release gate`
- `da5a636 Add MPL licensing and Qt bundle audit`
- `73b0533 Clarify pre-release validation status`
- `5325455 Document visual review completion`
- `ea821fc Resolve bilingual visual review findings`
- `4b5c525 Update handoff with Home header finding`
- `9b2078f Record Home table header misalignment`
- `c28ecf1 Record Home visual findings`
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
severita'. La review visuale allora residua e' chiusa da `1.33.1`; NightScope
non e' ancora approvato per il rilascio perche' restano matrice provider,
matrice visuale sulla dist, bundle finale pulito, lock/SBOM, firma o policy
esplicita. Bundle pubblico, commit sorgente e hash sono ora verificati.

`1.33.1` chiude il controllo visuale bilingue tracciato in
`docs/VISUAL_CHECKLIST.md`: tutti i 36 rilievi VIS-001--VIS-036 sono risolti e
marcati completati. Il passaggio ha riguardato Provider, localita', Profili,
cataloghi celesti ed Equipment, Log, Meteo, Calendario e tutte le viste Home,
senza cambiare scoring NSOM, Planner o ranking.

`1.33.2` adotta MPL-2.0 per NightScope, Copyright 2026 Davide Marchi. I file
`THIRD_PARTY_NOTICES.md` e `THIRD_PARTY_LICENSES.txt` consolidano licenze,
copyright e attribuzioni di runtime, Qt/PySide, GeoNames, timezone, dati
astronomici e immagini. L'archivio e' rigenerabile e il gate standard ne
verifica la coerenza con la dependency closure installata.

Il requisito Qt e' stato ristretto a `PySide6_Essentials`. Hook PyInstaller
locali raccolgono solo i moduli QML usati e rimuovono input virtuale e tooling
QML che trascinavano DLL GPL-only non utilizzate. `build_windows.ps1` copia i
tre documenti legali nella radice del bundle e blocca build con archivio stale,
DLL Qt obbligatorie assenti o moduli GPL-only inattesi.

La dist `1.33.2` persistente e' stata rigenerata e supera audit Qt/licenze e
smoke backend/QML. Poiche' NightScope salva i dati accanto all'eseguibile, i
test hanno creato database, backup e log nella cartella. L'audit rifiuta ora
questo stato runtime: usare una copia per i controlli e archiviare soltanto un
bundle pulito verificato immediatamente prima della pubblicazione.

Il repository pubblico e' `https://github.com/beastmen84/NightScope`. La release
`v1.33.2` punta al commit sorgente verificato
`9c17204f718223e83183367e9ccea078805b5a00`; note e asset pubblicano anche il
digest SHA-256 dello ZIP.

`1.34.0` aggiunge lo spagnolo (Spagna) all'intera superficie localizzata:
messaggi Qt/Python, contenuti strutturati, nomi dei cataloghi, Equipment e tutte
le 14 sezioni del manuale. Le traduzioni automatiche sono state corrette con un
passaggio editoriale deterministico, includendo terminologia astronomica e
ottica, tono formale, privacy, provider e sicurezza solare. La logica di
scoring e raccomandazione non cambia. Questa versione non e' ancora stata
costruita o pubblicata come pacchetto Windows.

La seconda review del `2026-07-21` ha letto tutte le `228` schede spagnole e
verificato con LanguageTool i contenuti narrativi, i cataloghi e l'Equipment.
Descrizioni, note e curiosita' restano tutte uniche e con lunghezze comparabili
ai testi italiani e inglesi. Il lessico e' ora uniforme su `visión periférica`,
`brillo superficial`, `aumento`, `apertura` e `sistema solar`; alias, refusi e
calchi sono stati corretti. M84, M86, C51 e C53 hanno descrizioni spagnole
scientificamente coerenti e M78 non suggerisce piu' filtri a banda stretta. I
tipi canonici usati da filtri e scoring non sono stati modificati.

La pipeline dei contenuti ora distingue la lingua sorgente per catalogo e per
campo, genera descrizioni Caldwell inglesi deterministiche e include traduzioni
complete per Filtri, Riduttori e modelli compatibili. Le costellazioni sono
localizzate solo in presentazione, mantenendo internamente i valori IAU
canonici. I nomi paese dei provider restano canonici e il fuso IANA rimane il
dato autorevole. La dimensione angolare massima resta una metrica esplicita:
sono decisioni di prodotto, non rilievi residui.

Home condivide ora la stessa geometria tra intestazione e righe della tabella
Oggetti visibili; gli orari sono `HH:MM`, l'origine distingue `Catalogo` dalla
distanza reale e le card evento consentono al massimo due righe. Calendario usa
titoli eclissi naturali, terminologia inglese corretta e angoli visibili in
`°`. Meteo mostra VIIRS come `nW/(cm²·sr)`. Log, moduli Equipment, menu
reattivi, AFOV Fisso/Zoom, decimali locali, associazioni Riduttori e ordinamento
naturale Binocoli sono stati allineati al contratto visuale italiano/inglese.

I cataloghi Qt contengono `1665` stringhe finite e nessuna incompleta per
lingua. I contenuti generati sono coperti da controlli contro le regressioni
lessicali individuate durante la review. La distribuzione non e' stata
rigenerata: il controllo visivo successivo deve usare una nuova build esplicita
quando richiesta.

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
- Da `1.34.0`, `astro_viewer/translations` contiene pack completi `it`, `en` ed
  `es`; PyInstaller include l'intera directory e quindi acquisisce nuovi pack
  senza cambiare la spec.
- Gli updater estraggono `1665` messaggi per lingua, preservano le traduzioni
  gia' revisionate, rifiutano cataloghi incompleti o placeholder incompatibili
  e producono output idempotente.
- Le correzioni spagnole revisionate sono riproducibili tramite
  `tools/translation_reviews/es.json`; l'updater rifiuta riferimenti obsoleti e
  placeholder alterati.
- Le righe sintetiche del Sistema Solare nel Catalogo Oggetti conservano i
  nomi Qt lazy e le descrizioni `objects` fino al payload QML. La tabella, la
  ricerca nella lingua attiva e il dettaglio di fallback mostrano quindi
  `Sun`/`Moon`/pianeti in inglese e `Sol`/`Luna`/pianeti in spagnolo senza
  ricalcolare l'astronomia.
- La prosa strutturata spagnola applica inoltre override e normalizzazioni
  editoriali deterministici in `tools/update_content_translations.py`; i test
  vietano il ritorno dei termini superati e proteggono unicita', alias e
  classificazioni presentate.
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

## Validazione 1.34.1

Eseguita nella venv corrente dopo il passaggio di hardening e le guide provider:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
# smoke QML separati it/en/es con user_preferences e runtime temporanei
git diff --check
```

Risultati:

- Gate completo con security: `817 passed`, `613 warnings`, `10 subtests
  passed` in `120,46 s`; durata complessiva `218,6 s`.
- Coverage runtime `84%` su `15403` statement; `pip check`, Ruff, `compileall`,
  archivio third-party, `pip-audit`, smoke backend e smoke QML puliti.
- Cataloghi Qt IT/EN/ES: `1679` traduzioni finite e `0` unfinished per lingua;
  smoke QML separati italiano, inglese e spagnolo completati con exit `0`.
- Verifica mirata guide provider: `23 passed`; `qmllint` su 31 file senza
  failure e con le 760 warning statiche note; rendering diretto della pagina
  Provider completato in IT/EN/ES a larghezza desktop e minima.
- Bandit resta sul baseline revisionato: `0 high`, `26 medium`, `12 low`.
- Nessuna modifica a schema, seed data, scoring o recommendation policy; nessuna
  build o release `1.34.1` generata.

## Validazione 1.34.0

Eseguita nella venv corrente:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py astro_viewer\tests\test_developer_tooling.py
# smoke QML separati it/en/es con user_preferences e runtime temporanei
# manuale es verificato in Chromium a 390x844, 621x844 e 1440x900
git diff --check
```

Risultati:

- Gate completo senza coverage: `797 passed`, `613 warnings`, `7 subtests
  passed` in `119,77 s`; durata complessiva `202,9 s`.
- `pip check`, Ruff, `compileall`, archivio third-party, smoke backend e smoke
  QML standard puliti.
- Cataloghi Qt IT/EN/ES: `1665` traduzioni finite e `0` unfinished per lingua.
- Contenuti spagnoli: `7` sezioni, `821` elementi, `2038` campi tradotti;
  overlay editoriale TS con `617` correzioni globali e `5` contestuali.
- Test mirati localizzazione/tooling: `33 passed`; localizzazione e flussi reali
  del catalogo: `90 passed`, `29 warnings` note e `7 subtests`. Smoke QML
  separati italiano, inglese e spagnolo completati con exit `0` in runtime
  temporanei.
- Manuale spagnolo: desktop, breakpoint `621 px` e mobile senza overflow
  orizzontale; `IT`/`EN`/`ES` restano su una sola riga. Cambio lingua,
  persistenza e navigazione alle ancore verificati in Chromium.
- Nessuna build o release `1.34.0`: il pacchetto pubblico resta `1.33.2` e la
  matrice visuale completa dell'app spagnola resta aperta.

## Validazione 1.33.2

Eseguita nella venv corrente:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
.\.venv\Scripts\python.exe tools\generate_third_party_licenses.py --check
# Bandit su astro_viewer e tools, esclusi i test
# Build PyInstaller isolata con dist/work temporanei
# tools/audit_qt_bundle.py e --qml-smoke-test sull'eseguibile temporaneo
git diff --check
```

Risultati:

- Gate completo: `791 passed`, `613 warnings`, `7 subtests passed` in
  `153,85 s`; coverage runtime `84%` su `15.242` statement.
- `pip check`, Ruff, compileall, archivio third-party, smoke backend e smoke QML
  puliti; `pip-audit` non rileva vulnerabilita' note.
- Bandit invariato: `0 high`, `26 medium`, `12 low`.
- Archivio licenze: `61` distribuzioni coperte, inclusi runtime Python,
  dipendenze transitive e termini del bootloader PyInstaller.
- Bundle temporaneo: `5223` file, `469,8 MiB`; audit Qt/licenze e smoke QML
  dell'eseguibile superati. La directory temporanea e' stata rimossa.
- Dist persistente `1.33.2` rigenerata: versione e manuale `1.33.2`, file legali
  presenti, audit Qt/licenze e smoke backend/QML superati.
- L'esecuzione in-place ha creato `nightscope.db`, `nightscope.db.backup` e
  `logs`; la cartella e' una copia di validazione. Il nuovo audit rifiuta stato
  runtime nel bundle destinato alla pubblicazione.
- Lo ZIP pubblico e' stato estratto in una directory temporanea: `5221` file,
  `434.071.829` byte non compressi, audit Qt/licenze/stato runtime superato,
  nessun database o log NightScope. SHA-256 locale e GitHub coincidono:
  `33424e4e8317dee951230d795e2f0de936946910ede232ba478e893c73e02967`.

## Validazione 1.33.1

Eseguita nella venv corrente dopo le correzioni visuali e la review finale del
sorgente:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
# pyside6-qmllint eseguito su tutti i file astro_viewer/app/ui/**/*.qml
# smoke QML italiano e inglese eseguiti in runtime temporanei separati
git diff --check
```

Risultati:

- Gate con coverage e security: `788 passed`, `613 warnings`, `7 subtests
  passed` in `112,44 s`; coverage runtime `84%` su `15.242` statement.
- `pip check`, Ruff, compileall, smoke backend e smoke QML puliti;
  `pip-audit` non rileva vulnerabilita' note.
- Bandit: `0 high`, `26 medium`, `12 low`, invariato rispetto alla baseline
  revisionata.
- Suite mirate finali: `113 passed`, con soli warning Skyfield/NumPy gia' noti.
- Cataloghi Qt italiano/inglese completi e compilati: `1665/1665` ciascuno,
  nessuna stringa incompleta.
- Test traduzioni: `15 passed`.
- `qmllint`: exit `0` su tutti i 30 QML; restano `760` warning statiche note
  relative soprattutto agli accessi non qualificati.
- Immagini: `219` JPEG deep-sky e `9` JPEG Sistema Solare validi.
- Smoke QML isolati in italiano e inglese: entrambi completati con exit `0`.
- Schema SQLite invariato a `16`; nessuna migrazione e nessuna modifica ai dati
  runtime dell'utente.
- `git diff --check`: pulito.
- Dist corrente `1.32.3`; dist `1.33.1` non rigenerata.

La review del codice e dei contratti QML non ha rilevato regressioni funzionali.
La review visuale bilingue del sorgente e' conclusa; resta aperta la verifica
visuale della dist Windows dopo il rebuild.

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
