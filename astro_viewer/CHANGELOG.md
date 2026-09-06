# Changelog

## Unreleased

## NightScope 1.46.18 - 2026-09-06

- Chiarito l'emisfero dei periodi osservativi per 56 galassie NGC già arricchite,
  con corrispondenza boreale/australe esplicita in italiano, inglese e spagnolo.
  Conservati il periodo originario e tutte le condizioni specifiche; nessuna
  modifica a descrizioni, note osservative, difficoltà, identità o raccomandazioni.
- Manifest separato, fonti della correzione e campioni visuali nelle tre lingue
  e nei due temi. Nessun nuovo oggetto, dist o pubblicazione; Windows pubblico
  resta 1.46.13 e Linux 1.43.0.
- Nella curiosità di NGC 1266, fusione minore e soppressione della formazione
  stellare tornano a essere interpretazioni proposte, distinte dai deflussi
  osservati, come nella fonte NASA; correzione coerente in IT/EN/ES.
- L'audit ammette correzioni a campi dichiarati di NGC già accettati senza
  contarli come nuovi oggetti e blocca stagioni prive di emisfero. I manifest
  storici restano intatti. Vedi TESTING per il gate finale delle correzioni.
- Gate completo finale superato: 1.515 test e dieci subtest, copertura 86%,
  audit di sicurezza e smoke backend/QML normale/rosso in runtime isolati.

## NightScope 1.46.17 - 2026-09-06

- Chiarito l'emisfero dei periodi osservativi per 87 globulari e nebulose storiche,
  con corrispondenza boreale/australe esplicita in italiano, inglese e spagnolo.
  Conservati il periodo originario e tutte le condizioni specifiche; nessuna
  modifica a descrizioni, note osservative, difficoltà, identità o raccomandazioni.
- Manifest separato, fonti della correzione e campioni visuali nelle tre lingue
  e nei due temi. Nessun nuovo oggetto, dist o pubblicazione; Windows pubblico
  resta 1.46.13 e Linux 1.43.0. Il gate completo finale segue l'ultimo step.

## NightScope 1.46.16 - 2026-09-06

- Chiarito l'emisfero dei periodi osservativi per 57 ammassi aperti e altri campi stellari,
  con corrispondenza boreale/australe esplicita in italiano, inglese e spagnolo.
  Conservati il periodo originario e tutte le condizioni specifiche; nessuna
  modifica a descrizioni, note osservative, difficoltà, identità o raccomandazioni.
- Manifest separato, fonti della correzione e campioni visuali nelle tre lingue
  e nei due temi. Nessun nuovo oggetto, dist o pubblicazione; Windows pubblico
  resta 1.46.13 e Linux 1.43.0. Il gate completo finale segue l'ultimo step.

## NightScope 1.46.15 - 2026-09-06

- Chiarito l'emisfero dei periodi osservativi per 75 galassie storiche,
  con corrispondenza boreale/australe esplicita in italiano, inglese e spagnolo.
  Conservati il periodo originario e tutte le condizioni specifiche; nessuna
  modifica a descrizioni, note osservative, difficoltà, identità o raccomandazioni.
- Manifest separato, fonti della correzione e campioni visuali nelle tre lingue
  e nei due temi. Nessun nuovo oggetto, dist o pubblicazione; Windows pubblico
  resta 1.46.13 e Linux 1.43.0. Il gate completo finale segue l'ultimo step.

## NightScope 1.46.14 - 2026-09-06

- Corretti i tre difetti di codice della review 1.45.21–1.46.13: gli overlay
  editoriali restano integri durante la manutenzione ordinaria delle traduzioni;
  le finestre utili concluse non diventano falsi consigli futuri o di quota;
  splash e dialogo di errore iniziale rispettano la preferenza rossa salvata.
- Aggiunte regressioni sui pack reali EN/ES, sui limiti temporali assoluti e
  sul disegno dei widget iniziali nelle tre lingue. In rosso la splash non
  carica l'icona a colori; la palette evita anche aloni subpixel di Windows.
- Nessuna modifica a formule, dati editoriali, scoring, DB o dist. Le correzioni
  dei periodi stagionali e di NGC 1266 proseguono nei successivi step editoriali.
  Windows pubblico resta 1.46.13 e Linux 1.43.0; nessun push o run GitHub atteso.
- Suite estesa a 1.481 test e 10 sottotest: nel run completo le sole due
  anomalie erano riferimenti documentali alla versione precedente, corretti
  e verificati con tutti i 49 test di tooling. Smoke backend/QML normale/rosso
  ripetuti in isolamento; widget iniziali controllati anche su Windows nativo.
  Il gate fresco con sicurezza e copertura segue l'ultimo step editoriale.

## NightScope 1.46.13 - 2026-09-06

- Release pubblicata dall'utente su GitHub, solo Windows x64:
  `NightScope-v1.46.13-windows-x64.zip`, tag `v1.46.13` su `b34ec4a`.
  Linux rimane alla `v1.43.0`. Successivamente allineati README, manuale,
  documentazione corrente e sito EN/IT/ES, inclusi link e metadati; corretta
  la revisione del footer inglese del manuale. Nessun bump versione, rebuild
  o sostituzione del pacchetto pubblicato. Le verifiche e le note di mancata
  pubblicazione qui sotto descrivono i passaggi precedenti alla release.
  Verifica finale: 49 test documentazione/tooling superati, Ruff e inventario
  documentale validi; nessuna modifica al codice runtime o alla grafica del sito.
- Ultimo step immagini: backup automatico SQLite coerente anche in WAL,
  sostituzione atomica solo dopo verifica, conservazione del backup precedente
  in caso di errore e limite temporale alla copia.
- Migrazione dei dati da cartelle precedenti comprensiva delle foto personali,
  copiate prima del DB senza alterare originali o file in conflitto. Ripristino
  di foto sostituite/rimosse da un vecchio backup verificato in un runtime nuovo.
- Miniature Home danneggiate tornano al predefinito; audit del pacchetto esteso
  ai plugin del selettore file e alle cartelle di immagini personali annidate.
- Documentazione di backup/ripristino nelle tre lingue; nessuna nuova GUI di
  backup, esportazione di credenziali o modifica a editoriale/formule/scoring.
  Gate completo con sicurezza superato: 1.452 test e 10 sottotest, copertura
  86%, smoke backend e QML normale/rosso. 35 QML lintati, 2.088 messaggi
  compilati per IT/EN/ES, 21 stati Home personali e 48 stati delle categorie
  verificati; tre audit pixel rossi superati. Nessuna dist, push, tag o
  pubblicazione: la serie sorgente delle immagini è conclusa.
- Successivo rebuild Windows richiesto dall'utente: dist 1.46.13 da `be30cda`,
  audit Qt/legale/runtime e smoke backend/QML normale/rosso superati. Verificati
  108 asset e cinque file legali per hash, schema 27 e integrita' dei tre DB
  temporanei, nove immagini solari e parita' dei 323 record editoriali per
  tabella. Dist precedente e relativi dati rimossi senza backup, come richiesto;
  nessun bump versione, pacchetto Linux, tag, push o pubblicazione.
- Verificata nel bundle anche la selezione foto nativa Windows, il fallback Qt,
  anteprima/salvataggio/alias/annullamento, blocco immagini e ripristino in
  rosso. La foto lunare personale viene ricaricata dopo il riavvio senza
  originale sintetico. Copie/runtime di test rimossi, audit finale superato;
  46 test di documentazione/tooling superati. Nessuna modifica al codice app.

## NightScope 1.46.12 - 2026-09-05

- Secondo step immagini: importazione locale con anteprima, conferma,
  sostituzione e ripristino dal dettaglio Catalogo/Home, anche per il Sistema
  Solare. Associazione per oggetto canonico condivisa fra alias.
- Schema 27 e tabella personale separata dai seed; file JPEG gestiti dall'app
  e miniature in user_images, nomi basati su hash, nessun percorso originale
  nel DB. Originale invariato, proporzioni e orientamento conservati, metadati
  personali rimossi; decodifica in background con limiti di formato/peso/pixel.
- Gestione IT/EN/ES; annullamento/cambio oggetto scartano i risultati tardivi.
  In rosso non si aprono selettori o anteprime; il ripristino resta disponibile.
  Foto mancanti o non decodificabili tornano al predefinito. Nessuna modifica
  all'editoriale, alle formule astronomiche o ai criteri di raccomandazione.
- Gate completo con sicurezza superato: 1.429 test e 10 sottotest, copertura
  86%, smoke backend/QML normale/rosso. 2.088 messaggi compilati per IT/EN/ES,
  lint di 35 QML, 36 scenari grafici ripetuti anche dal selettore Qt e sei audit
  pixel rossi. Due fixture Planner ora fissano l'orario senza cambiare asserzioni;
  i precedenti fallimenti dopo le 23 non dipendevano dalle immagini.
- Backup/ripristino integrale nella successiva 1.46.13; nessuna dist,
  pubblicazione, push o attesa dei run GitHub.

## NightScope 1.46.11 - 2026-09-05

- Primo step della nuova gestione immagini: tutti i cataloghi deep-sky usano
  16 illustrazioni coerenti per categoria, indipendenti dal completamento
  dell'editoriale. Conservate senza modifiche le nove fotografie del Sistema
  Solare; rimosse dal pacchetto sorgente le 219 fotografie Messier/Caldwell.
- Asset generati con IA e dichiarati come illustrazioni in IT/EN/ES, non come
  fotografie dell'oggetto selezionato. Mappatura da tipi canonici, categoria
  neutra per tipi sconosciuti, stesso comportamento da Catalogo e Home.
- JPEG RGB 512 x 512 ottimizzati senza ritaglio: 614.168 byte complessivi,
  rispetto ai 15.235.688 byte dei vecchi ritagli; risparmio asset di 14.621.520
  byte. Provenienza, prompt e hash registrati; nessuna rigenerazione nel resize.
- Schema DB 26: ritirati soltanto i record standard riconosciuti da ID,
  percorso e licenza; ID limitati ai 219 originali e ai tre vecchi fallback,
  senza wildcard. Preservati percorsi/licenze personalizzati e ID soltanto
  simili a quelli ritirati. Nessuna modifica
  all'editoriale o alle formule astronomiche. Caricamento QML asincrono e
  limitato al ramo di dettaglio attivo; sorgenti immagini vuote in visione rossa.
- Sostituito il downloader deep-sky con un controllo locale permanente di
  inventario, formato, categorie e hash; aggiunte regressioni su migrazione,
  alias/lingue, integrita' e risorse mancanti o alterate.
- Gate completo con sicurezza superato: 1.407 test e 10 subtest, copertura
  86%, smoke backend/QML normale/rosso superati. Lint su 34 QML e 2.065 messaggi
  compilati per lingua. Verificati 24 scenari di dettaglio IT/EN/ES e 48 stati
  delle miniature Home; in rosso immagini non caricate. Migrazione dell'intero
  seed storico in un DB temporaneo: personalizzazioni e altre 33 tabelle intatte.
- Importazione delle fotografie personali e integrazione backup/ripristino
  restano i successivi step 1.46.12 e 1.46.13. Nessun rebuild dist, push, tag,
  pubblicazione o attesa dei run GitHub in questo passaggio.

## NightScope 1.46.10 - 2026-09-05

- Corrette le anomalie A1-A8/N1 dell'audit 1.46.9: meteo incompleto/non finito,
  soglia delle nebulose planetarie, finestre positive prima dell'alba,
  ammissione al piano e opportunita' NSOM nulle, cronologia e durate al cambio d'ora.
- Introdotti timestamp completi per finestre e piano; campionamento e confronti
  in UTC, presentazione locale con offset per distinguere le ore autunnali ripetute.
- Allineato il criterio di crepuscolo tra notte e filtro mensile: buio
  astronomico per deep-sky, Urano e Nettuno; tramonto per Luna e pianeti luminosi.
  Il Sole conserva il percorso diurno e non entra nel piano notturno.
- Il fallimento del recupero effemeridi disattiva le previsioni astronomiche:
  niente dati dimostrativi, con avviso persistente su tutte le pagine.
- Disegno lunare con terminatore sferico proiettato e meta' disco ai quarti;
  magnitudine -12,7 esplicitamente indicata come riferimento di Luna piena.
- Ricerca aggiornamenti per artefatto Windows/Linux x64 realmente disponibile;
  corretti inoltre le coordinate OpenAQ uguali a zero e il veto cometario della
  Luna sotto l'orizzonte. Nessuna ricalibrazione dei pesi NSOM o dell'imaging.
- Aggiunte regressioni dedicate e aggiornati contratti/documentazione. I due
  nuovi messaggi UI sono revisionati e compilati in IT/EN/ES; nessuna modifica
  ai 323 oggetti editoriali, ai manifest, alle traduzioni dei contenuti o al DB.
- Gate completo con sicurezza superato: 1.332 test e 10 subtest, copertura 86%,
  smoke backend/QML normale/rosso superati. Ripetuti il confronto di 288
  posizioni Skyfield/Astropy e le 240 identita' ottiche su 48 configurazioni.
- Il passaggio di correzione della sorgente non ha modificato la dist e non ha
  atteso run GitHub. Verifica in `docs/ASTRONOMICAL_CORRECTIONS_1_46_10.md`.
- Successivo rebuild Windows richiesto dall'utente: dist 1.46.10 da `ae34df5`,
  audit Qt/legale/runtime e smoke backend/QML normale/rosso superati. Verificati
  310 asset e cinque file legali per hash, integrita' dei tre DB temporanei e
  parita' dei 323 record per ciascuna tabella editoriale. Vecchia dist e backup
  precedente rimossi manualmente dall'utente; nessun nuovo backup, come richiesto.
  Copia temporanea di questo test rimossa; quella storica 1.46.9 resta segnalata.
  Nessun bump versione, pacchetto Linux, archivio/tag, push o pubblicazione.
- Successiva rifinitura grafica del ciclo lunare: rimosso l'alone che rendeva
  visibile il riquadro delle icone; esterno trasparente, disco in ombra e
  geometria delle fasi invariati. Controllati gli otto simboli a piu' dimensioni
  e il passaggio normale/rosso/normale. Questa modifica e' solo nella sorgente
  1.46.10: la dist costruita da `ae34df5` non e' stata rigenerata.
  Gate completo ripetuto: 1.348 test e 10 subtest, copertura 86%; audit, lint
  QML e smoke backend/QML normale/rosso superati. Nessun run GitHub atteso.

### Audit preliminare della sorgente 1.46.9

- Audit astronomico e logico esteso alla struttura del programma, senza bump
  versione o modifiche al comportamento: rapporto in
  `docs/ASTRONOMICAL_CODE_AUDIT_1_46_9.md`, confronto Skyfield/Astropy su 288
  posizioni e 240 verifiche dimensionali su 48 configurazioni ottiche.
- Documentati difetti riproducibili nelle soglie delle nebulose planetarie,
  nelle finestre/DST, nell'ammissione dei pianeti al piano e nei dati meteo
  incompleti; registrati anche incoerenze sul crepuscolo, provenienza dei dati
  di fallback, illustrazione lunare e disponibilita' aggiornamenti per piattaforma.
  Le correzioni funzionali, successivamente autorizzate, sono nella 1.46.10 sopra.
- Aggiunti contratti e limiti scientifici nei moduli di astronomia, ottica,
  seeing, provider, NSOM e imaging. Corretto il riferimento documentale a
  un'elevazione osservatore non utilizzata; editoriale, traduzioni, formule,
  soglie, schema, dist e release pubbliche invariati.
- Verifica audit: gate completo iniziale con sicurezza superato (1.251 test e
  10 subtest); dopo le sole modifiche documentali, 153 test mirati superati e
  confronto degli AST eseguibili identico in tutti i 15 moduli Python modificati.
  Ruff, documentazione, confini architetturali e baseline Bandit invariati.

## NightScope 1.46.9 - 2026-09-05

- Ripreso l'arricchimento NGC con 20 nebulose planetarie: descrizione, note
  osservative, periodo/condizioni e curiosita' specifici in italiano canonico
  e overlay inglese/spagnolo revisionati. Batch volutamente contenuto per
  distinguere strutture reali, limiti visuali e particolarita' scientifiche.
- Chiariti NGC 2371/2372 come singolo oggetto, la sovrapposizione prospettica
  di NGC 2438 a M46, gli anelli infrarossi di NGC 1514 e la formazione locale
  dello ione HeH+ in NGC 7027. Conservate le cautele su compagne probabili,
  interpretazioni dei venti stellari ed eta' ricavate dal moto del gas.
- Verificati 26 URL distinti del manifest; 72 scene campione nelle tre lingue,
  in modalita' normale e Red Night Vision, ai livelli note e descrizione/
  curiosita'. Audit statico e similarita' senza avvisi o frasi lunghe condivise.
- Copertura editoriale: 323 oggetti completi, di cui 95 NGC-only (75 galassie
  e 20 planetarie); restano 7.271 NGC-only. Nove batch accettati: tre di
  arricchimento e sei correttivi sui 197 oggetti storici gia' revisionati.
- Aggiunte regressioni su identita'/alias e qualificazioni IT/EN/ES. Nessuna
  modifica al precedente editoriale, alle misure del catalogo, alle immagini,
  al runtime o ai punteggi NSOM/raccomandazioni; preservata la suite accelerata.
- Gate completo con sicurezza superato: 1.251 test e 10 subtest in 310,46
  secondi, copertura 86%, audit e smoke backend/QML normale/rosso tutti verdi.
  Allineati i conteggi attesi a 323, mantenendo inalterati i controlli di
  unicita', fonti, lunghezza, incipit e similarita'.
- Rigenerata successivamente, su richiesta, la dist Windows locale dal commit
  `42b0cb2` per le verifiche manuali, senza bump versione. Conservata la dist
  precedente completa con hash verificati dei dati runtime. Audit del bundle
  e smoke impacchettati backend/QML normale/rosso superati; controllata anche
  una copia del vecchio DB, con 323 descrizioni e curiosita' aggiornate e stato
  utente preservato, salvo il normale refresh della posizione automatica.
- Nessun tag, archivio di release, bundle Linux o pubblicazione. Ultime release
  pubbliche invariate: Windows `1.45.21`, Linux `1.43.0`.

## NightScope 1.46.8 - 2026-09-05

- Corretti i residui dell'editoriale storico: 92 descrizioni e cinque
  curiosita' su 94 oggetti Messier/Caldwell, con revisione IT/EN/ES. Rimosse
  frasi riutilizzate dentro paragrafi diversi e finali costruiti soltanto su
  misure di catalogo, preservando i campi non dichiarati nel manifest.
- Chiariti l'aspetto tenue di NGC 246 e il profilo di taglio di NGC 4945;
  conservata la distinzione ellittica/lenticolare di M84 presente nelle fonti.
  Corrette la terminologia delle correnti stellari di NGC 4449 e dei bracci
  flocculenti di NGC 2775, la provenienza del sistema triplo di NGC 246 e
  l'ipotesi di origine di Omega Centauri. NGC 559 ora cita uno studio
  fotometrico che stima 224 milioni di anni, non i circa due miliardi del
  testo precedente.
- L'audit trova anche frasi narrative condivise di almeno 12 parole
  normalizzate, in descrizioni, note e curiosita' IT/EN/ES. Il controllo e'
  globale anche senza `--batch`, esclude brevi consigli e ripetizioni interne
  allo stesso oggetto e rispetta le deroghe motivate accettate. Prima della
  correzione: 133 famiglie su 85 oggetti; dopo: zero, senza deroghe. Il risultato
  zero della `1.46.7` riguardava invece il confronto di paragrafi interi.
- Verificati con audit live tutti i 101 URL distinti del manifest. Dodici
  campioni hanno prodotto 72 scene Object Detail IT/EN/ES, normale e Red Night
  Vision, sulle schede descrizione/curiosita': testi integri, senza
  sovrapposizioni, e monocromia rossa conservata. Il confronto dei campi
  conferma 97 testi modificati per lingua e nessun cambiamento alle altre
  sezioni delle traduzioni; 91 test mirati superati in 19,95 secondi.
- Otto batch accettati, di cui sei correttivi su 197 oggetti storici distinti.
  Nessuna nuova voce NGC: restano 303 oggetti completi, 75 NGC-only arricchiti
  e 7.291 da completare. Il prossimo batch NGC e' riservato alla `1.46.9`.
- Gate sorgente editoriale, prima della messa a punto dei test, superato con
  sicurezza: 1.237 test e 10 subtest in
  423,37 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit
  invariata, nessuna vulnerabilita' nota e smoke test backend/QML
  normale/Red Night Vision riusciti. L'audit editoriale passa senza avvisi.
- La versione sorgente passa a `1.46.8`; `dist`, tag e artefatti di release
  non sono stati prodotti. Le release pubbliche restano Windows `v1.45.21`
  e Linux `v1.43.0`.
- Ottimizzata la preparazione dei database nei test: base reale ricostruita
  per sessione e worker, copie private per ogni test e import GeoNames dai
  relativi file temporanei. Invariati bootstrap/migrazioni/recupero sotto
  test, calcoli astronomici, assert, tolleranze e matrici di casi. Nessuna
  modifica al codice applicativo o ai contenuti; nessun nuovo bump versione.
- Il confronto locale con quattro worker e coverage misura 310,62 secondi
  prima e 216,43 dopo: 94,19 secondi in meno, circa il 30,3%. Conservati tutti
  i 1.237 test originali, aggiunti dieci controlli di equivalenza, isolamento,
  provenienza e ciclo di vita delle fixture: 1.247 test e 10 subtest superati.
  Nessuna riga coperta persa; copertura effettiva da 17.526 a 17.539 righe su
  20.396, sempre 86% arrotondato. Gate completo con sicurezza e tre smoke test
  superato; inventario aggiornato a 250 Python, 34 QML e 17 file operativi.
- Aggiunti il riepilogo dei test piu' lenti nel runner e l'opzione diagnostica
  `--fresh-test-databases`, che ripristina la creazione completa per ogni
  preparazione e supera cinque scenari mirati. Nessun test saltato o escluso
  e nessuna nuova release pubblica.

## NightScope 1.46.7 - 2026-09-04

- Conclusa la rimessa a punto del debito editoriale storico misurato: riscritte
  le note osservative di 51 galassie Messier/Caldwell e, per C21, C48, C57 e
  C60, anche le quattro descrizioni rimaste in famiglie duplicate. Curiosita',
  periodi e difficolta' gia' distinti non sono stati riaperti.
- Le nuove indicazioni distinguono scala e luminosita' superficiale, polvere,
  barre, asimmetrie, compagne nello stesso campo, limiti visuali realistici e i
  pochi casi in cui un filtro e' utile su una regione H II separata, non sulla
  galassia nel suo insieme. Non sono sostituzioni lessicali della prosa
  precedente.
- Tutti i 51 testi italiani e i relativi overlay inglesi e spagnoli sono stati
  revisionati individualmente. I 50 URL NASA Hubble distinti che sostengono i
  51 oggetti del manifest hanno superato l'audit live.
- Dieci campioni rappresentativi hanno prodotto 120 scene Object Detail finali:
  IT/EN/ES, modalita' normale e Red Night Vision, sia sull'intestazione con le
  note sia sulle schede inferiori, senza tagli, sovrapposizioni o perdita della
  monocromia rossa.
- Il controllo deterministico passa da 2 famiglie/4 oggetti a zero per le
  descrizioni e da 5 famiglie/51 oggetti a zero per le note osservative. Le
  cinque correzioni cumulative coprono 177 oggetti storici; la copertura resta
  303 oggetti completi, inclusi 75 NGC-only, con 7.291 NGC-only ancora da
  arricchire.
- Gate sorgente completo con sicurezza superato: 1.227 test e 10 subtest in
  269,93 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit
  invariata, nessuna vulnerabilita' nota e smoke test backend/QML
  normale/Red Night Vision riusciti. L'audit editoriale passa senza avvisi.
- La versione sorgente passa a `1.46.7`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.6 - 2026-09-04

- Completata la rimessa a punto delle 20 nebulose a emissione, riflessione e
  planetarie ancora coinvolte nel debito editoriale storico. Sono state
  riscritte le note osservative senza riaprire descrizioni, curiosita', periodi
  o difficolta' gia' distinti.
- Le nuove indicazioni distinguono scala del campo, luminosita' superficiale,
  componenti miste emissione/riflessione, confronti con e senza filtro, gusci
  compatti e limiti realistici dell'osservazione visuale. Non sono sostituzioni
  lessicali della prosa precedente.
- Tutti i 20 testi italiani e i relativi overlay inglesi e spagnoli sono stati
  revisionati individualmente. I 20 URL oggetto-specifici del manifest hanno
  superato l'audit live.
- Sette campioni rappresentativi hanno prodotto 84 scene Object Detail finali:
  IT/EN/ES, modalita' normale e Red Night Vision, sia sull'intestazione con le
  note sia sulle schede inferiori, senza tagli, sovrapposizioni o perdita della
  monocromia rossa.
- Il debito storico misurato resta a 2 famiglie/4 oggetti per le descrizioni e
  scende da 10 famiglie/71 oggetti a 5/51 per le note osservative. Rimangono
  soltanto galassie; la copertura non cambia: 303 oggetti completi, inclusi 75
  NGC-only, e 7.291 NGC-only ancora da arricchire.
- Gate sorgente completo con sicurezza superato: 1.227 test e 10 subtest in
  266,69 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit
  invariata, nessuna vulnerabilita' nota e smoke test backend/QML
  normale/Red Night Vision riusciti. Il solo avviso resta il debito storico
  residuo atteso.
- La versione sorgente passa a `1.46.6`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.5 - 2026-09-04

- Completata la rimessa a punto dei 41 ammassi globulari ancora coinvolti nel
  debito editoriale storico: riscritte tutte le note osservative e, per C42,
  C47, C66, C81, C93 e C107, anche le descrizioni duplicate. Curiosita',
  periodi e difficolta' non sono stati riaperti.
- Le nuove indicazioni distinguono concentrazione del nucleo, estensione
  dell'alone, risoluzione stellare, assorbimento interstellare, campi affollati,
  altezza sull'orizzonte e confronti visuali realmente utili. Non sono semplici
  sostituzioni lessicali della prosa precedente.
- Tutti i 41 testi italiani e i relativi overlay inglesi e spagnoli sono stati
  revisionati individualmente. Le 41 pagine NASA Hubble dedicate hanno
  superato l'audit live.
- Otto campioni rappresentativi hanno prodotto 96 scene Object Detail finali:
  IT/EN/ES, modalita' normale e Red Night Vision, sia sull'intestazione con le
  note sia sulle schede inferiori, senza tagli, sovrapposizioni o perdita della
  monocromia rossa.
- Il debito storico misurato scende da 5 famiglie/10 oggetti a 2/4 per le
  descrizioni e da 16 famiglie/112 oggetti a 10/71 per le note osservative.
  Restano soltanto nebulose e galassie; la copertura non cambia: 303 oggetti
  completi, inclusi 75 NGC-only, e 7.291 NGC-only ancora da arricchire.
- Gate sorgente completo con sicurezza superato: 1.227 test e 10 subtest in
  269,79 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit
  invariata, nessuna vulnerabilita' nota e smoke test backend/QML
  normale/Red Night Vision riusciti. Il solo avviso resta il debito storico
  residuo atteso.
- La versione sorgente passa a `1.46.5`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.4 - 2026-09-04

- Completata la rimessa a punto dei 48 ammassi aperti coinvolti nel debito
  editoriale storico: tutte le note osservative sono ora specifiche del
  bersaglio e dieci descrizioni appartenenti a quattro famiglie duplicate sono
  state riscritte. Curiosita', periodi e difficolta' non sono stati riaperti.
- Le nuove indicazioni distinguono ampiezza del campo, morfologie stellari,
  contrasti cromatici, compagni, assorbimento interstellare e casi misti
  ammasso-nebulosa. I filtri sono consigliati soltanto per il gas adiacente a
  C50, C82, C100 e M46, non per la luce continua degli ammassi.
- Tutti i 48 testi italiani e i relativi overlay inglesi e spagnoli sono stati
  revisionati individualmente. I 48 URL specifici dell'oggetto hanno superato
  l'audit live.
- Nove campioni rappresentativi hanno prodotto 108 scene Object Detail finali:
  IT/EN/ES, modalita' normale e Red Night Vision, sia sull'intestazione con le
  note sia sulle schede inferiori, senza tagli, sovrapposizioni o perdita della
  monocromia rossa.
- Il debito storico misurato scende da 9 famiglie/20 oggetti a 5/10 per le
  descrizioni e da 22 famiglie/160 oggetti a 16/112 per le note osservative.
  La copertura resta 303 oggetti completi, inclusi 75 NGC-only; ne restano 7.291.
- Gate sorgente completo con sicurezza superato: 1.227 test e 10 subtest in
  270,49 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit
  invariata, nessuna vulnerabilita' nota e smoke test backend/QML
  normale/Red Night Vision riusciti. Il solo avviso resta il debito storico
  residuo atteso.
- La versione sorgente passa a `1.46.4`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.3 - 2026-09-04

- Corretto il primo insieme organico di prosa generica del baseline storico:
  riscritte le note osservative di 17 galassie Messier/Caldwell e, nei quattro
  casi coinvolti da famiglie duplicate, anche le descrizioni di C17, C53, C65
  e C77. Curiosita' e periodo consigliato non sono stati riaperti.
- Ogni testo italiano e i corrispondenti overlay inglesi e spagnoli sono stati
  revisionati come contenuti specifici dell'oggetto: difficolta' reale,
  ingrandimento o campo utile, dettagli visuali plausibili e contesto di
  confronto sostituiscono formule costruite soltanto da magnitudine e misura.
- Esteso il manifest editoriale con il tipo `baseline_remediation`: ogni voce
  dichiara esattamente i campi cambiati, le fonti possono provare solo quei
  campi e il controllo di similarita' non accredita come revisionato il testo
  lasciato intatto. I batch NGC completi restano distinti e retrocompatibili.
- Tutti i 17 URL NASA Hubble specifici dell'oggetto hanno superato l'audit live.
  Sette campioni hanno prodotto 84 scene Object Detail finali: IT/EN/ES,
  modalita' normale e Red Night Vision, sia sull'intestazione con le note sia
  sulle schede descrizione/curiosita', senza tagli o sovrapposizioni.
- Il debito storico misurato scende da 11 famiglie/24 oggetti a 9/20 per le
  descrizioni e da 23 famiglie/177 oggetti a 22/160 per le note osservative.
  La copertura non cambia: 303 oggetti completi, dei quali 75 NGC-only, e 7.291
  NGC-only ancora da lavorare.
- Gate sorgente completo con sicurezza superato: 1.227 test e 10 subtest in
  392,39 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit
  invariata, nessuna vulnerabilita' nota e smoke test backend/QML
  normale/Red Night Vision riusciti. Il solo avviso emesso e' il debito
  editoriale storico residuo atteso.
- La versione sorgente passa a `1.46.3`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.2 - 2026-09-04

- Ricontrollati integralmente i 50 oggetti del batch `1.46.1` nelle tre lingue:
  descrizioni, indicazioni osservative e curiosita' restano specifiche, utili e
  prive di duplicazioni editoriali sostanziali.
- Reso esplicito il debito qualitativo precedente al programma: il baseline
  immutabile protegge le 228 identita', non la formulazione storica. Il nuovo
  controllo normalizza identificativi, alias tra parentesi e misure e segnala,
  senza confonderle con errori dei nuovi batch, 11 famiglie di descrizioni quasi
  identiche su 24 oggetti e 23 famiglie di note osservative su 177 oggetti.
- Accettato un secondo batch deliberatamente contenuto di 25 galassie NGC-only,
  scelte per valore osservativo o scientifico e disponibilita' di prove dirette.
  Ogni oggetto riceve i quattro testi canonici italiani e overlay inglesi e
  spagnoli revisionati, senza riempitivi generici o curiosita' derivate dal solo
  tipo di catalogo.
- Il manifest `batch_1_46_2.json` conserva identita', designazioni, fonti NED e
  una fonte istituzionale o bibliografica specifica per ogni curiosita'. Tutti i
  50 URL distinti hanno superato l'audit live; sei campioni hanno prodotto 36
  scene Object Detail IT/EN/ES in modalita' normale e Red Night Vision, senza
  tagli, sovrapposizioni o perdita dell'attribuzione.
- La copertura sale a 303 oggetti completi: 228 nel baseline e 75 NGC-only;
  restano 7.291 NGC-only da lavorare in batch successivi. Il gate protegge anche
  il conteggio del debito editoriale storico per impedirne la scomparsa silente.
- Gate sorgente completo con sicurezza superato: 1.225 test e 10 subtest in
  382,12 secondi, copertura aggregata 86%, documentazione completa per 247 file
  Python, 34 QML e 17 operativi, grafo import aciclico, baseline Bandit invariata,
  nessuna vulnerabilita' nota e smoke test backend/QML normale/Red Night Vision
  riusciti. Il solo avviso emesso e' il debito editoriale storico atteso.
- La versione sorgente passa a `1.46.2`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.1 - 2026-09-04

- Accettato il primo batch editoriale della serie `1.46.x`: 50 galassie
  NGC-only scelte come insieme di riferimento per morfologia, luminosita'
  superficiale, orientamento e accessibilita' dal cielo boreale e australe.
- Aggiunti per ogni oggetto descrizione breve, note osservative, periodo
  consigliato, difficolta' per cinque classi strumentali e curiosita' canoniche
  italiane; gli overlay inglese e spagnolo sono completi e revisionati sugli
  stessi quattro testi.
- Il manifest `batch_1_46_1.json` conserva identita' e designazioni esatte,
  prove NED per i dati di catalogo, una fonte istituzionale o bibliografica per
  ciascuna curiosita', date di accesso e accettazione separata dei controlli
  fattuali e linguistici. L'audit live ha verificato 99 URL distinti.
- L'audit deterministico passa con 278 oggetti editorialmente completi: 228 nel
  baseline immutabile e 50 NGC-only; restano 7.316 oggetti NGC-only da lavorare
  in batch successivi.
- Aggiunto `render_editorial_samples.py`, che apre un runtime isolato e produce
  automaticamente i campioni Object Detail del manifest in IT/EN/ES e nelle
  modalita' normale/Red Night Vision. Revisionate 36 scene `1440 x 1000` per
  sei oggetti rappresentativi, incluso il caso multi-designazione NGC 5906/5907,
  senza testi tagliati o sovrapposti.
- Gate sorgente completo con sicurezza superato: 1.224 test e 10 subtest in
  315,84 secondi, copertura aggregata 86%, 247 moduli Python documentati, grafo
  import aciclico, baseline Bandit invariata, nessuna vulnerabilita' nota e
  smoke test backend/QML normale/Red Night Vision riusciti.
- La versione sorgente passa a `1.46.1`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.46.0 - 2026-09-04

- Preparata la serie editoriale `1.46.x` senza aggiungere ancora contenuti NGC:
  il baseline identifica i 228 oggetti gia' completi e l'inventario misura
  esplicitamente 7.366 oggetti NGC-only ancora da revisionare.
- Aggiunti manifest JSON versionati per batch da 1 a 100 oggetti, con identita'
  fisica e designazioni, fonti HTTPS per ciascun campo, date di accesso, stati di
  revisione fattuale/IT/EN/ES, campioni visuali e deroghe motivate alla
  similarita'. Un batch incompleto non puo' risultare accettato.
- Aggiunto un audit editoriale deterministico al gate sorgente: verifica campi
  canonici italiani, overlay inglesi e spagnoli, provenienza, duplicati,
  copertura dei manifest e conteggio residuo; con `--batch` controlla anche le
  quasi-duplicazioni rispetto al corpus esistente.
- L'audit live delle fonti puo' ora essere limitato al manifest corrente, evitando
  di ricontrollare l'intero archivio a ogni batch.
- La generazione automatica non crea o sovrascrive piu' testi editoriali per
  impostazione predefinita. L'opzione esplicita `--draft-editorial` produce solo
  bozze che richiedono comunque revisione umana nelle tre lingue.
- Per i futuri oggetti NGC completati, la descrizione canonica sostituisce il
  placeholder nelle viste catalogo e le note osservative sostituiscono il
  placeholder nei target runtime. Il testo non viene duplicato nel campo
  storico `descrizione` del catalogo e non entra in punteggi o ranking.
- Superati 86 test focalizzati su catalogo, localizzazione, strumenti e nuovi
  casi di accettazione/rifiuto dei batch. Il gate sorgente completo ha superato
  1.223 test e 10 subtest in 300,73 secondi con copertura aggregata 86%, audit
  dipendenze senza vulnerabilita' note, grafo import e baseline Bandit invariati,
  audit editoriale pulito e smoke test backend/QML normale/Red Night Vision
  riusciti.
- La versione sorgente passa a `1.46.0`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release. Le release
  pubbliche restano Windows `v1.45.21` e Linux `v1.43.0`.

## NightScope 1.45.22 - 2026-09-03

- Lo splash di avvio viene ora mostrato a ogni lancio normale, prima del lavoro
  sul database e del caricamento QML, così l'utente riceve un riscontro continuo
  fino al primo frame dell'interfaccia.
- Il primo utilizzo conserva il testo introduttivo inglese. Dagli avvii
  successivi titolo, passaggi e stato seguono la lingua salvata italiana,
  inglese o spagnola e distinguono apertura, creazione e ricostruzione del
  database locale.
- Eliminato il preflight duplicato usato soltanto per decidere se mostrare lo
  splash; il bootstrap effettivo resta l'unico proprietario di controllo,
  migrazione e seeding del database. Aggiunti tempi diagnostici per servizi,
  scena QML e primo frame e una preferenza di completamento scritta senza
  perdere le impostazioni esistenti.
- Aggiunti 17 testi di avvio revisionati ai cataloghi Qt; italiano, inglese e
  spagnolo contengono ora 2.063 messaggi finiti e zero traduzioni incomplete.
- Verificate nativamente su Windows le varianti primo utilizzo inglese e avvio
  ordinario IT/EN/ES, senza tagli, sovrapposizioni o regressioni dei bordi
  trasparenti.
- Gate sorgente locale completo: 1.215 test e 10 subtest superati in 290,96
  secondi, copertura aggregata 86%, audit dipendenze senza vulnerabilita' note e
  smoke test backend, QML normale e Red Night Vision riusciti. Superati anche
  due avvii reali isolati, prima con database nuovo e poi con database esistente
  e lingua spagnola salvata.
- Allineati README, manuale e documentazione allo stato pubblico effettivo:
  `v1.45.21` e' la release Windows corrente, mentre il pacchetto Linux resta a
  `v1.43.0`. L'icona iniziale del README e' stata sostituita con una schermata
  reale della Home dell'applicazione.
- Aggiunto il sito ufficiale statico in inglese, italiano e spagnolo, con pagina
  prodotto responsive, download distinti per piattaforma, metadati SEO e social,
  dati strutturati `SoftwareApplication`, sitemap, `robots.txt` e pubblicazione
  isolata della sola cartella `website/` tramite GitHub Pages.
- Corretto il ridimensionamento dello screenshot nella testata del sito: conserva
  ora il formato panoramico e non estende più verticalmente la prima sezione.
- La versione sorgente passa a `1.45.22`; `dist` non e' stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release.

## NightScope 1.45.21 - 2026-09-03

- Corretta la seconda causa del confronto licenze non riproducibile emersa
  nella run GitHub di `1.45.20`: il generatore interpretava il modulo
  `packaging/licenses/` come raccolta di documenti legali e incorporava anche
  sorgenti Python e bytecode `.pyc` dipendente da percorso e timestamp.
- Il rilevamento include ora i documenti con nomi legali noti e i contenuti
  arbitrari solo sotto la directory standard `<package>.dist-info/licenses`;
  codice, bytecode e `__pycache__` sono sempre esclusi.
- Rigenerato l'archivio Windows eliminando 2.172 righe spurie, senza cambiare
  l'inventario legale di 62 componenti. Due installazioni Windows pulite e
  indipendenti producono ora lo stesso SHA-256 dell'archivio.
- Gate sorgente locale completo: 1.209 test e 10 subtest superati, copertura
  aggregata 86%, audit dipendenze senza vulnerabilità note e smoke test backend,
  QML normale e Red Night Vision riusciti.
- La versione sorgente passa a `1.45.21`; `dist` non è stata rigenerata o
  modificata in questo commit. Successivamente sono stati pubblicati il tag, la
  release GitHub e il solo ZIP Windows x64; Linux resta disponibile alla
  `v1.43.0`.

## NightScope 1.45.20 - 2026-09-03

- Corretta la causa comune delle run GitHub `Source validation` fallite su
  Windows: il runner flottante installava Python e dipendenze transitive diverse
  dall'ambiente registrato in `THIRD_PARTY_LICENSES.txt`.
- Aggiunta una closure Windows di 62 componenti con versioni esatte, condivisa
  dalle installazioni runtime e sviluppo del job sorgente. Il job usa ora
  Python 3.14.5, la stessa patch registrata nell'archivio legale.
- Linux/Python 3.12 e l'audit separato su Python 3.14 restano flottanti, così il
  progetto conserva un segnale sulle dipendenze più recenti senza rendere
  instabile il confronto legale byte-per-byte di Windows.
- Aggiunti controlli che impongono la corrispondenza esatta tra constraints,
  inventario dell'archivio licenze e versione Python del workflow.
- Gate sorgente locale completo: 1.204 test e 10 subtest superati, copertura
  aggregata 86%, audit dipendenze senza vulnerabilità note e smoke test backend,
  QML normale e Red Night Vision riusciti.
- La versione sorgente passa a `1.45.20`; `dist` non è stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release.

## NightScope 1.45.19 - 2026-09-03

- Estratto `EquipmentProfileRepository`, responsabile del ciclo di vita dei
  profili e di tutte le assegnazioni di telescopi, oculari, Barlow, binocoli,
  filtri, riduttori e camere.
- La composition root inietta separatamente repository dei cataloghi e dei
  profili; `ProfileEquipmentService` e `AppController` non usano più il
  repository globale per la persistenza dell'inventario utente.
- Conservata sul vecchio `EquipmentCatalogRepository` l'API profili per
  compatibilità. Le cancellazioni forzate continuano a rimuovere catalogo e
  assegnazioni nella stessa transazione SQLite.
- Aggiunti test che riaprono dopo il bootstrap un database popolato con tutte le
  famiglie di equipaggiamento e verificano il rollback completo di una
  cancellazione interrotta. Non è stata introdotta alcuna migrazione dello
  schema o degli identificatori esistenti.
- Il gate sorgente completo con coverage e sicurezza passa con 1.203 test e 10
  subtest in 359,33 secondi, coverage aggregata 86%, nessuna vulnerabilità nota
  e smoke test backend, QML normale e Red Night Vision riusciti.
- La versione sorgente passa a `1.45.19`; `dist` non è stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release.

## NightScope 1.45.18 - 2026-09-02

- Estratto dal controller Qt `LocationCommandWorkflow`, che ora gestisce
  ricerca, selezioni città/MPC/manuali, provider di sistema/online, fallback di
  avvio, località recenti e messaggi con input e risultati espliciti.
- `AppController` non interroga più direttamente `LocationRepository` o
  `LocationService`; conserva slot e segnali Qt, cancellazione delle richieste,
  scarto dei risultati obsoleti, persistenza e scheduling dei refresh.
- Aggiunti 28 test unitari del workflow e verificati 72 test mirati inclusi gli
  scenari controller e i percorsi runtime.
- Il gate sorgente completo con coverage e sicurezza passa con 1.201 test e 10
  subtest in 306,74 secondi, coverage aggregata 86%, nessuna vulnerabilità nota
  e smoke test backend, QML normale e Red Night Vision riusciti.
- La versione sorgente passa a `1.45.18`; `dist` non è stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release.

## NightScope 1.45.17 - 2026-09-02

- Estratti da `location_service.py` gli adapter concreti Windows/WinRT,
  Linux/GeoClue, geolocalizzazione IP con cache e inserimento manuale.
- La composition root costruisce ora un bundle immutabile di adapter e lo
  inietta nel servizio; ordinamento, fallback, arricchimento città e politica
  timezone restano isolati in `LocationService`.
- Conservati gli import storici tramite una facciata compatibile e verificati
  precedenza dei provider, errori, timeout, cache e payload QML con 115 test
  mirati.
- Il gate sorgente completo con coverage e sicurezza passa con 1.172 test e 10
  subtest in 330,30 secondi, coverage aggregata 86%, nessuna vulnerabilità nota
  e smoke test backend, QML normale e Red Night Vision riusciti.
- La versione sorgente passa a `1.45.17`; `dist` non è stata rigenerata o
  modificata e non sono stati creati tag o artefatti di release.

## NightScope 1.45.16 - 2026-09-02

- Aggiornata come singola unita' compatibile la famiglia runtime Earthdata:
  `earthaccess` 0.18.0, `s3fs`/`fsspec` 2026.7.0, `aiobotocore` 3.9.0 e
  `botocore` 1.43.56.
- Resi espliciti e adiacenti in `requirements.txt` i cinque vincoli del provider
  NASA AOD; il limite `botocore<1.43.57` segue la finestra supportata da
  `aiobotocore` 3.9.0 invece di installare una release piu' nuova ma
  incompatibile.
- Aggiunta una salvaguardia automatica contro aggiornamenti parziali della
  famiglia e rigenerato l'archivio deterministico delle licenze.
- Passano l'import reale dello stack, `pip check` e 47 test mirati del provider
  NASA AOD e dei vincoli di packaging.
- Il gate sorgente completo con coverage e sicurezza passa con 1.170 test e 10
  subtest in 310,65 secondi, coverage aggregata 86% e nessuna vulnerabilita'
  nota; passano anche gli smoke backend e QML nelle due modalita'.

## NightScope 1.45.15 - 2026-09-02

- Aggiornata la baseline runtime della `.venv` a PySide6/Qt/shiboken6 6.11.2,
  Skyfield 1.55, NumPy 2.5.2 e dati IERS del 31 agosto 2026; Astropy resta alla
  versione corrente 8.0.1.
- Alzati i minimi dichiarati per PySide6 Essentials/Addons, Skyfield e NumPy e
  rigenerato l'archivio deterministico delle licenze con le versioni installate.
- Conservato `timezonefinder==8.2.5`: la 8.3.0 non pubblica un wheel Windows e
  imporrebbe una compilazione da sorgente nel percorso d'installazione
  supportato.
- Il gate sorgente completo con coverage e sicurezza passa con 1.169 test e 10
  subtest in 220,73 secondi, coverage aggregata 86% e nessuna vulnerabilita'
  nota; passano anche 85 test astronomici/timezone mirati, entrambi gli smoke
  QML e `qmllint` 6.11.2 su tutti i 34 file QML.
- Nessun sorgente applicativo o QML e' stato modificato. La versione sorgente
  passa a `1.45.15`; `dist` non e' stata rigenerata o modificata e non sono
  stati creati tag o artefatti di release.

## NightScope 1.45.14 - 2026-09-02

- Aggiornata la toolchain della `.venv` Python 3.14.5 a pip 26.2.1, Ruff 0.16.5,
  coverage 7.16.0, PyInstaller 6.22.2 e `pyinstaller-hooks-contrib` 2026.7.
- Alzati i minimi dichiarati di Ruff, coverage e PyInstaller e rigenerato
  l'archivio deterministico delle licenze con i metadati di PyInstaller 6.22.2.
- Il gate sorgente completo con coverage e sicurezza passa con 1.169 test e 10
  subtest in 423,58 secondi, coverage aggregata 86%, nessuna vulnerabilita' nota
  e smoke test backend, QML normale e Red Night Vision riusciti.
- Nessun comportamento runtime e' stato modificato. La versione sorgente passa
  a `1.45.14`; `dist` non e' stata rigenerata o modificata e non sono stati
  creati tag o artefatti di release.

## NightScope 1.45.13 - 2026-09-02

- Ispezionati tutti gli 88 moduli Python di test/supporto e documentati i 87 che
  non dichiaravano ancora il contratto protetto; completato anche il modulo CLI
  di bootstrap del database individuato dal nuovo inventario.
- Aggiunto un gate automatico per 240 moduli Python, 34 file QML e 15 file
  operativi. Il runner standard lo esegue prima dei controlli architetturali e
  ora include anche i moduli Python di packaging in Ruff e `compileall`.
- Aggiornata la valutazione architetturale con misure correnti e una roadmap
  esplicita per controller, provider/localita', persistenza, Skyfield, QML e
  localizzazione.
- Nessun comportamento runtime e' stato modificato. La versione sorgente passa
  a `1.45.13`; `dist` non e' stata rigenerata o modificata e non sono stati
  creati tag o artefatti di release.

## NightScope 1.45.12 - 2026-09-02

- Documentati 29 moduli Python di manutenzione e packaging e 15 file operativi
  tra script, specifica PyInstaller, CI, configurazione, schema e manuale.
- Le intestazioni dichiarano input autorevoli, uso della rete, file riscritti e
  confine esplicito dei comandi che possono modificare `build` o `dist`.
- Nessun comando di build e' stato eseguito. La versione sorgente passa a
  `1.45.12`; `dist` non e' stata rigenerata o modificata e non sono stati
  creati tag o artefatti di release.

## NightScope 1.45.11 - 2026-09-02

- Documentati tutti i 34 file QML con responsabilita' e contratto espliciti:
  shell di navigazione, 15 pagine e 18 componenti condivisi.
- I commenti distinguono stato puramente visuale, segnali di navigazione,
  read model consumati e operazioni che devono restare nei servizi Python.
- Nessun comportamento runtime e' stato modificato. La versione sorgente passa
  a `1.45.11`; `dist` non e' stata rigenerata o modificata e non sono stati
  creati tag o artefatti di release.

## NightScope 1.45.10 - 2026-09-02

- Documentati file per file i 12 moduli SQLite, i 6 moduli astronomici, i due
  viewmodel Qt e la composition/entry point in `main.py`.
- I confini ora dichiarano esplicitamente proprieta' di persistenza, import e
  bootstrap, calcoli Skyfield, provider orbitali e orchestrazione asincrona QML.
- Nessun comportamento runtime e' stato modificato. La versione sorgente passa
  a `1.45.10`; `dist` non e' stata rigenerata o modificata e non sono stati
  creati tag o artefatti di release.

## NightScope 1.45.9 - 2026-09-02

- Documentati a livello di modulo tutti i 71 servizi applicativi non vuoti:
  dominio, provider, presentazione, cataloghi, attrezzatura e localizzazione.
- Le descrizioni esplicitano effetti collaterali dei provider, confini del
  ranking, separazione tra dati grezzi e proiezioni UI e contratti verso QML.
- Nessun comportamento runtime e' stato modificato. La versione sorgente passa
  a `1.45.9`; `dist` non e' stata rigenerata o modificata e non sono stati
  creati tag o artefatti di release.

## NightScope 1.45.8 - 2026-09-02

- Definito un contratto esplicito per documentare ogni file sorgente scritto a
  mano, con esclusioni limitate a dati, asset, output generati e storico.
- Documentati a livello di modulo composition root, snapshot asincrone,
  capability/piattaforma, percorsi runtime e tutti i modelli applicativi. Le
  descrizioni chiariscono responsabilita' e confini senza cambiare comportamento.
- La versione sorgente passa a `1.45.8`. `dist` non e' stata rigenerata o
  modificata; nessun tag o artefatto di release e' stato creato.

## NightScope 1.45.7 - 2026-09-02

- Esteso il gate AST: oltre ai cicli, modelli, database, astronomia e servizi
  non possono importare il livello Qt `viewmodels` o la composition root
  `application`. Il vincolo e' coperto anche da una regressione sintetica.
- Completata la valutazione architetturale della serie 1.45.x con misure,
  responsabilita', punti forti e debito residuo prioritizzato. La descrizione
  corrente distingue esplicitamente i confini realmente applicati dalle
  dipendenze pragmatiche ancora presenti.
- Separati i documenti operativi correnti dallo storico: i precedenti handoff e
  risultati di test restano conservati in `docs/archive`, mentre le guide vive
  sono brevi e orientate al prossimo intervento.
- Definito il contratto editoriale per le future descrizioni e curiosita' NGC:
  ricerca per oggetto, fonti verificabili, revisione italiana/inglese/spagnola,
  batch versionati e separazione assoluta da ranking e visibilita'. Nessun
  contenuto NGC mancante e' stato generato in questo step architetturale.
- La versione sorgente passa a `1.45.7`. `dist` non e' stata rigenerata o
  modificata; nessun tag, checksum o artefatto di release e' stato creato.

## NightScope 1.45.6 - 2026-09-02

- Integrati nel runner standard il controllo dei cicli di importazione e una
  scansione Bandit incrementale. Le 51 segnalazioni esistenti sono revisionate
  per severita', percorso e impronta del codice: ogni nuova segnalazione, ogni
  riclassificazione e ogni modifica della sorgente interessata blocca il gate;
  una severita' alta non puo' entrare in baseline.
- Pytest tratta come errori tutti i warning inattesi. Restano filtrate soltanto
  le due deprecazioni Skyfield causate dalle assegnazioni `dtype` e `shape`
  rimosse da NumPy 2.5, con regex, categoria e modulo espliciti. Il nuovo gate
  ha anche individuato e corretto una connessione SQLite non chiusa in un test
  della composition root.
- Aggiunta una CI GitHub con gate completo su Windows/Python 3.14 e
  Linux/Python 3.12, piu' un audit separato della chiusura delle dipendenze.
  La CI riusa `tools/run_checks.py` e non costruisce artefatti di distribuzione.
- La versione sorgente passa a `1.45.6`. `dist` non e' stata rigenerata o
  modificata; nessun tag, checksum o artefatto di release e' stato creato.

## NightScope 1.45.5 - 2026-09-02

- Eliminati i cicli d'importazione tra policy aerosol e condizioni, tra
  servizio Equipment e builder delle configurazioni, e tra bootstrap del
  database ed entry point. Un controllo AST dedicato rende ora esplicito e
  verificabile il vincolo di aciclicita' dei moduli di produzione.
- Gli input atmosferici immutabili vivono nel livello `models`; il builder
  ottico dipende da un `Protocol` minimo e da tipi `TypedDict`, mentre i calcoli
  condivisi hanno un'unica implementazione indipendente dal motore di
  raccomandazione. Gli import storici degli input restano compatibili.
- La versione sorgente passa a `1.45.5`. `dist` non e' stata rigenerata o
  modificata; nessun tag o artefatto di release e' stato creato.

## NightScope 1.45.4 - 2026-09-02

- Estratti da `AppController` caricamento e mapping dei cataloghi Equipment,
  parsing e validazione degli input, query dell'inventario dei profili e read
  model presentati a QML. I nuovi servizi sono privi di dipendenze Qt e
  ricevono repository o dati espliciti dalla composition root.
- Il controller conserva mutazioni persistenti, messaggi localizzati, segnali
  e notifiche dipendenti dal profilo. Wrapper compatibili mantengono invariati
  gli helper storici, inclusi i test che costruiscono il controller senza
  eseguirne il costruttore.
- La versione sorgente passa a `1.45.4`. `dist` non e' stata rigenerata o
  modificata; nessun tag, checksum o artefatto di release e' stato creato.

## NightScope 1.45.3 - 2026-09-02

- Separati da `AppController` caricamento e normalizzazione dei record di
  catalogo, ricerca sulle designazioni, filtri, proiezioni localizzate e
  calcolo dell'osservabilita' geometrica statica. Le identita' multi-catalogo e
  l'ordinamento numerico restano invariati.
- La costruzione degli oggetti e dei metadati di dettaglio vive ora in un
  servizio dedicato. Il controller conserva notifiche del modello QML, cache di
  visibilita' e accesso sincronizzato al motore astronomico, con wrapper
  compatibili per i chiamanti esistenti.
- La versione sorgente passa a `1.45.3`. `dist` non e' stata rigenerata o
  modificata; nessun tag o artefatto di release e' stato creato.

## NightScope 1.45.2 - 2026-09-02

- Estratti da `AppController` gli algoritmi di presentazione degli stati
  osservativi, delle motivazioni, delle finestre meteo e della decisione di
  sessione. I nuovi servizi ricevono dati espliciti e non dipendono da QObject,
  segnali o stato UI.
- Le funzioni condivise per orari della notte, parsing di date e finestre a
  cavallo della mezzanotte sono ora raccolte in `observing_time`; selezione e
  sintesi delle ore meteo vivono in `weather_presentation`. Il controller
  conserva wrapper compatibili per i test e le integrazioni esistenti.
- La versione sorgente passa a `1.45.2`. `dist` non e' stata rigenerata o
  modificata; tag e artefatti restano fuori da questa serie di commit.

## NightScope 1.45.1 - 2026-09-02

- Estratto da `AppController` il workflow sincrono che prepara le
  raccomandazioni di catalogo. Arricchimento con l'equipaggiamento, read model
  delle condizioni, ranking NSOM, scelta del miglior oggetto, piano notturno e
  payload Sky Compass appartengono ora al livello applicativo e sono privi di
  dipendenze Qt.
- I contratti immutabili usati dai worker asincroni vivono ora in un modulo
  applicativo dedicato. Il controller conserva debounce, timer, generazioni di
  richiesta, rifiuto dei risultati obsoleti, segnali e applicazione dello stato,
  mantenendo invariati i contratti QML e gli adattatori interni esistenti.
- La versione sorgente passa a `1.45.1`. `dist` non e' stata rigenerata o
  modificata; tag, checksum e artefatti restano un'attivita' di release separata.

## NightScope 1.45.0 - 2026-09-02

- Introdotta una composition root applicativa esplicita che costruisce
  repository, provider, servizi di dominio e motore astronomico fuori da
  `AppController`. L'entry point passa ora al controller un contenitore di
  dipendenze gia' risolto, mantenendo il costruttore storico come percorso di
  compatibilita' per test e integrazioni esistenti.
- Il fallback da Skyfield ai dati astronomici di emergenza appartiene ora alla
  composizione dell'applicazione; percorsi runtime, cache, credenziali, refresh,
  punteggi e contratti QML restano invariati.
- La versione sorgente passa a `1.45.0`. La cartella `dist` non e' stata
  rigenerata: i futuri artefatti Windows e Linux richiederanno una richiesta e
  una validazione di release separate.

## NightScope 1.44.0 - 2026-09-01

- Stabilizzata la direzione live di Sky Compass senza rallentare il refresh
  astronomico da 60 secondi. Quando due zone hanno punteggi vicini, la zona gia'
  mostrata resta selezionata e una concorrente marginale deve risultare prima
  per cinque refresh consecutivi; il cambio resta immediato se la nuova zona ha
  un vantaggio di almeno il 15% e cinque punti oppure se la zona corrente non ha
  piu' target osservabili.
- Il normale refresh Home/Planner apre una nuova decisione Sky Compass, mentre
  il percorso live continua ad aggiornare altitudine, azimut, settore e
  `observable_now` dalla snapshot esistente senza richiamare meteo, provider,
  Planner, equipaggiamento o Recommendation Engine. Punteggi NSOM, soglie di
  osservabilita', otto settori da 45 gradi e comportamento dei refresh non live
  restano invariati.
- La versione sorgente passa a `1.44.0`; i nuovi bundle Windows/Linux devono
  essere rigenerati e verificati rispetto al tag sorgente `v1.44.0`.

## NightScope 1.43.0 - 2026-07-29

- Le linee sotto le tessere metriche usano ora un teal informativo coerente e
  attenuato per impostazione predefinita in Profili, Dettaglio oggetto e Meteo,
  senza suggerire stati o soglie inesistenti. Un colore diverso richiede un
  significato esplicito: resta quindi nelle categorie evento del Calendario e
  nei reali esiti di visibilita' del catalogo. Lista e dettaglio catalogo
  condividono ora la stessa semantica tri-state: verde per `Si'`, corallo per
  `No` e grigio quando l'esito non e' noto.
- Anche le barrette verticali delle intestazioni e dei cataloghi Equipment
  adottano il teal informativo predefinito. Home, Provider, Posizione, Profilo
  attivo, Dettaglio oggetto ed Eventi usano invece verde, ambra o corallo quando
  indicano rispettivamente un esito positivo, attenzione o un problema; nei
  marker di stato il cyan indica un'operazione in corso e il grigio un dato
  realmente non disponibile. Luna segue ora l'impatto reale e le condizioni
  planetarie/cielo profondo lo stesso colore del badge.
- Lo schema SQLite passa alla versione 25. La versione 24 separa la categoria
  dello strumento (`TRADITIONAL` o `SMART_INTEGRATED`) dal tipo ottico; la 25
  aggiunge il contratto persistente `SmartTelescopeCapability` per capacita'
  visuali, accessori esterni, sensore integrato, live stacking, video, mosaico,
  controllo delle pose, filtri interni e fonte tecnica. Seestar S30 e S50
  vengono inizializzati con il rispettivo sensore Sony IMX662/IMX462, focale
  150/250 mm, pixel da 2,9 µm e geometria 1920 x 1080 del canale astronomico
  principale.
- Il form dei telescopi usa ora menu a discesa controllati per categoria e tipo
  ottico, conserva una scelta `Altro` con descrizione personalizzata e
  distribuisce i campi in colonne uniformi, evitando larghezze dipendenti dal
  contenuto. Se la categoria e' smart mostra una sezione scorrevole per
  specifiche integrate e capacita' esplicite. I filtri interni standard sono
  ora scelte leggibili, con un campo aggiuntivo mostrato solo per modelli non
  coperti dall'elenco; il formato persistente e i codici personalizzati
  esistenti restano compatibili. I campi tecnici possono restare incompleti, ma
  in quel caso il motore fallisce in modo chiuso e non sostituisce implicitamente
  il sensore con una camera esterna.
- I telescopi smart non generano piu' combinazioni visuali fittizie con oculari
  o Barlow. Il percorso visuale li rimanda al piano EAA/fotografico mantenendo
  la capacita' visuale e i punteggi NSOM separati; in un profilo misto, gli
  strumenti tradizionali e i binocoli continuano a seguire il comportamento
  precedente.
- Il motore fotografico costruisce per S30/S50 un solo treno con sensore
  integrato e ignora camere, riduttori e Barlow assegnati al profilo. Il piano
  smart mostra campo e campionamento reali, integrazione totale con pose gestite
  dal dispositivo, disponibilita' del mosaico, filtro dual-band per le nebulose
  e un avviso di sottocampionamento per i pianeti alla scala nativa. Live
  stacking e video vengono ammessi solo quando dichiarati dal modello. Il Sole
  resta bloccato finche' il profilo non dichiara esplicitamente un filtro solare
  certificato a tutta apertura.
- La raccomandazione visuale per pianeti, Luna e target ad alto ingrandimento
  tratta ora il limite imposto dal seeing come vincolo pratico di selezione,
  senza alterare i pesi dello score: quando esistono configurazioni entro il
  limite esclude quelle superiori e, se tutte lo superano, conserva soltanto
  quella meno eccedente segnalandola come `seeing_limited`. Anche
  l'ingrandimento ideale di questi profili non puo' piu' superare il relativo
  limite utile; i target a largo campo restano invariati.
- Corretto l'intervallo delle singole pose fotografiche quando interviene il
  limite d'inseguimento: il limite inferiore converge ora in modo monotono al
  50% del massimo invece di diminuire bruscamente all'aumentare della posa
  desiderata. Ranking fotografico, limite superiore e integrazione totale
  restano invariati.
- Il provider NASA AOD distingue ora gli errori TLS, timeout e connessione
  (`connection_error`) dalle credenziali realmente respinte (`auth_error`).
  Restano invariati i tre tentativi Earthaccess, il comportamento fail-neutral
  e i fallback atmosferici esistenti.
- Aggiornata la venv di sviluppo con gli aggiornamenti compatibili disponibili
  per runtime, dati astronomici e strumenti di qualita': `aiobotocore 3.8.0`,
  `aiohttp 3.14.3`, `astropy-iers-data 0.2026.7.27.0.56.29`,
  `certifi 2026.7.22`, `coverage 7.15.2`, `filelock 3.32.0`,
  `jaraco.functools 4.6.0`, `pandas 3.0.5`, `platformdirs 4.11.0`,
  `Ruff 0.16.0`, `soupsieve 2.9.1`, `tqdm 4.70.0` e `yarl 1.24.5`.
- Allineati `aiobotocore 3.8.0` e `botocore 1.43.46` aggiornando il vincolo
  dichiarato alla finestra supportata `>=1.43.3,<1.43.47`. Le versioni
  `botocore` successive restano escluse finche' non sono accettate da
  `aiobotocore`.
- Rigenerato l'archivio Windows delle licenze sulla closure aggiornata delle
  dipendenze.
- Corretto nel manuale multilingue il riferimento alla release pubblica, ancora
  fermo alla storica `1.34.2`: italiano, inglese e spagnolo indicano ora
  correttamente la `1.42.0`.
- La review finale Windows passa con `tools/run_checks.py --security`:
  `1.132 passed`, `643 warnings` Skyfield/NumPy note, `10 subtests`, coverage
  `85%` su `19.500` statement e nessuna vulnerabilita' nota. I 34 file QML
  passano `qmllint` con zero errori e `832` warning `unqualified` gia' noti; i
  cataloghi IT/EN/ES contengono `2.046` stringhe complete ciascuno e gli smoke
  backend, QML normale e Red Night Vision restano verdi.
- Generato il bundle Linux `1.43.0` nella baseline Debian 12
  x86-64/glibc 2.36. La dist contiene `5.430` file per `577 MiB`, incluso il
  seed delle capacita' dei telescopi smart. Il tar deterministico misura
  `273.473.021` byte e ha SHA-256
  `ecdb48f9844b99bd3795e93b8d817f03de6943a171893c624b10fa84522f1250`.
  Checksum, audit, estrazione pulita, backend e QML normale/rosso sono passati
  su Debian 12, Debian 13 e Ubuntu 26.04, inclusi Wayland e XCB.
- La versione sorgente passa a `1.43.0`. Il bundle Windows, il tag `v1.43.0` e
  la release GitHub restano da creare, verificare e pubblicare; la release
  pubblica corrente rimane `v1.42.0`.

## NightScope 1.42.0 - 2026-07-27

- Corretto il piano fotografico per i target molto impegnativi: quando la
  stima supera il tetto di 15 ore, integrazione e numero di pose vengono ora
  mostrati come soglie minime cumulative su piu' notti, non come un intervallo
  esatto o come la durata di una singola sessione. La policy
  `imaging_exposure_v2` aggiunge inoltre un avviso specifico se un target di
  cielo profondo non raggiunge mai i 30 gradi, senza confondere la finestra
  visuale con una finestra fotografica ideale.
- Le alternative visuali ad alto ingrandimento non scelgono piu'
  automaticamente la combinazione estrema: rispettano il limite fisico dello
  strumento e, per galassie e nebulose estese a bassa luminosita'
  superficiale, conservano campo, pupilla d'uscita e contrasto evitando la
  Barlow.
- I blocchi del Planner espongono ora soltanto fattori meteo realmente
  limitanti. Condizioni favorevoli presenti nel riepilogo generale, come
  `vento debole`, non possono piu' comparire sotto `Fattore limitante`.
- Aggiunta la pagina `Cameras`, organizzata in due cataloghi indipendenti:
  37 camere astronomiche di ZWO, QHYCCD, Player One Astronomy, Atik e SVBONY,
  e 40 corpi macchina di Canon, Nikon, Sony, Fujifilm, Panasonic, OM System,
  Pentax e Sigma. La selezione comprende 7 SVBONY e 33 mirrorless; i campi
  persistiti descrivono sensore, pixel, risoluzione, profondita' in bit, frame
  rate e funzioni fotografiche utili al motore separato, con fonti tecniche
  ufficiali per ogni modello.
- La review dei seed Cameras corregge il frame rate del formato massimo 5.8K
  della Panasonic GH7, il backfocus della QHY268C e i riferimenti ZWO prima
  generici. I test verificano ora anche identita' marca/modello univoche e
  coerenza fra risoluzione, passo pixel e dimensioni fisiche dei sensori
  astronomici.
- Lo schema SQLite passa alla versione 23: la versione 20 introduce
  `AstronomyCameraCatalog` e `CameraBodyCatalog`, mentre la 21 aggiunge le
  associazioni persistenti delle due categorie ai profili. La versione 22
  aggiunge a ogni associazione profilo-telescopio lo stato, disattivato per
  impostazione iniziale, del filtro solare certificato a tutta apertura; la 23
  ritira i campi non calcolabili del diametro barilotto di oculari/Barlow e la
  compatibilita' testuale generica dei riduttori. I valori barilotto inseriti
  dall'utente in database precedenti vengono conservati nelle note, mentre la
  compatibilita' esatta reducer-telescopio resta invariata. I modelli integrati
  possono essere corretti ma non eliminati; i modelli utente hanno CRUD
  completo e, se assegnati, richiedono conferma prima della rimozione anche dai
  profili.
- La pagina `Profili` mostra ora camere astronomiche e corpi macchina
  nell'inventario assegnato e nei dialoghi di aggiunta/rimozione. La griglia
  passa in modo responsivo fra quattro, due e una colonna; la sezione delle
  capacita' e' esplicitamente visuale. Un segnale dedicato aggiorna soltanto
  l'inventario: camere e body non attivano Equipment, raccomandazioni visuali,
  Planner, Home, dettaglio oggetto, Sky Compass o NSOM.
- Ogni telescopio assegnato al profilo espone ora il flag
  `Filtro solare a tutta apertura disponibile`, persistito separatamente per
  profilo e strumento. Il controllo ricorda esplicitamente di usare soltanto
  filtri certificati fissati davanti all'obiettivo e mai filtri solari da
  oculare; il suo segnale aggiorna il solo inventario e non ricalcola ne'
  notifica il motore visuale.
- Rifinita la resa visuale dei profili dopo il controllo sull'interfaccia
  reale: i gruppi della griglia restano allineati in alto, i tag delle camere
  rimangono a destra quando lo spazio e' sufficiente e scendono su una seconda
  riga soltanto nelle celle strette. I dialoghi Cameras usano tre colonne
  uniformi e diciture piu' naturali per dimensioni del sensore e passo pixel.
- Revisionata la terminologia Cameras in italiano, inglese e spagnolo secondo
  l'uso fotografico e astronomico: modello e tecnologia del sensore, modalita'
  colore, risoluzione orizzontale/verticale, FPS a piena risoluzione, Delta T
  sotto ambiente, montatura obiettivo e modalita' Bulb sono ora distinti senza
  traduzioni letterali. Gli overlay editoriali e un test multilingua dedicato
  proteggono anche `Rolling shutter` dall'errata resa spagnola come tapparella.
- Introdotta la prima fondazione backend del motore fotografico, ancora
  non collegata al runtime: `ImagingCamera` normalizza senza confonderli i dati
  delle camere astronomiche e dei corpi macchina, mentre
  `ImagingTrainConfiguration` descrive il treno telescopio-camera a fuoco
  diretto, con reducer fotografico compatibile oppure con Barlow. Il builder
  calcola focale e rapporto focale effettivi, campo orizzontale/verticale e
  diagonale, campionamento in arcsec/pixel e spaziatura residua di backfocus.
  Montatura e inventario restano quelli dichiarati nel profilo; il builder non
  contiene scoring, tempi di posa, segnali, DTO QML o effetti sul motore visuale.
- Aggiunto il secondo strato backend fotografico:
  `ImagingTargetTraitsAdapter` classifica il target e sceglie in modo esplicito
  fra foto per cielo profondo e video per Luna/pianeti;
  `ImagingRecommendationService` ordina quindi i treni con uno score additivo e
  deterministico basato su inquadratura, campionamento, camera, montatura e
  acquisizione. Le camere planetarie ad alto frame rate, le camere raffreddate
  da cielo profondo, i body con Bulb, reducer e Barlow vengono confrontati con
  regole distinte e senza riusare score visuali, Home o NSOM.
- Aggiunto il terzo strato backend fotografico, non registrato direttamente nel
  controller: `ImagingExposureAdvisor` produce per il candidato foto un
  intervallo di posa singola, un intervallo di integrazione totale e il numero
  indicativo di frame. La policy e' auditabile e usa rapporto focale,
  luminosita' del target, SQM o fallback Bortle, trasparenza, geometria lunare e
  un limite prudenziale distinto per montatura; video non riceve tempi di posa
  still.
- Aggiunto il quarto strato backend fotografico:
  `ImagingVideoCaptureAdvisor` produce per Sole, Luna e pianeti un intervallo
  prudenziale per una singola clip stackabile senza derotazione, un intervallo
  FPS e il numero indicativo di frame acquisiti. Le finestre sono distinte per
  target; gli FPS effettivamente raggiungibili hanno precedenza, altrimenti il
  massimo di catalogo resta soltanto un limite superiore dichiarato. Giove usa
  clip piu' brevi, Saturno e i pianeti deboli obiettivi FPS distinti; un GoTo
  altazimutale conserva la normale finestra di Giove e limita soltanto le clip
  lunghe per la rotazione di campo.
- Collegati i quattro strati con `ImagingRuntimeAssembler`, invocabile soltanto
  on demand dal backend. Lo snapshot usa telescopi, camere astronomiche, body,
  reducer e Barlow del profilo attivo; costruisce i treni, sceglie il miglior
  candidato e restituisce un risultato tipizzato con il solo advisor foto o
  video pertinente. Gli ID del filtro solare vengono prima limitati ai
  telescopi effettivamente assegnati, mantenendo il Sole fail-closed.
- `ImagingRuntimeConditionsAdapter` porta nel piano foto SQM/Bortle,
  trasparenza atmosferica grezza e geometria lunare, e nel piano video seeing e
  altezza corrente. Le condizioni non cambiano lo score statico; FPS
  raggiungibili restano sconosciuti senza telemetria della camera. Stati
  espliciti distinguono profilo o inventario mancanti, treni non validi e
  target bloccati.
- Completato il collegamento selettivo al dettaglio oggetto:
  `ImagingRecommendationPresenter` produce un DTO localizzato e senza score,
  mentre la nuova card `Piano fotografico`, subito sotto la configurazione
  visuale, mostra treno ottico, campo del sensore, campionamento, focale e
  rapporto focale effettivi, backfocus e il solo piano coerente con foto o
  video. Le foto espongono posa singola, integrazione totale, numero indicativo
  di pose e limite prudenziale; i pianeti espongono durata della clip, FPS,
  frame indicativi e provenienza del frame rate.
- Gli avvisi fotografici restano metadati score-neutral e vengono limitati a
  quattro, scelti in ordine di priorita' fra visibilita', seeing,
  montatura/rotazione di campo, camera non raffreddata e pianeta debole. Se il
  target non entra nel campo del sensore, la card indica esplicitamente
  ritaglio o mosaico; il massimo FPS di catalogo non viene presentato come
  prestazione misurata.
- Rafforzato lo scoring del video planetario con una componente di apertura
  del telescopio al 15%, monotona e saturante, senza applicarla ai piani a disco
  intero di Sole e Luna. A parita' di rapporto focale una maggiore apertura
  viene quindi riconosciuta per la risoluzione disponibile, ma campionamento,
  camera e velocita' di acquisizione mantengono il peso principale.
- Resa prudenziale la geometria video dei corpi macchina: risoluzione video e
  sensore fotografico non vengono piu' usati per inventare area attiva,
  ritaglio o scala d'immagine. Campo e campionamento video sono mostrati come
  `Non verificato`, gli input mancanti riducono la completezza e, a parita' di
  score, viene preferito il fuoco diretto a un modificatore ottico non
  verificabile.
- La compatibilita' dei riduttori e' ora esclusivamente l'associazione esatta
  ai modelli di telescopio: il testo generico e i relativi tag sono rimossi.
  Un riduttore senza collegamenti resta nel catalogo e puo' essere assegnato,
  ma non entra in alcun suggerimento visuale o fotografico; l'interfaccia lo
  segnala esplicitamente, mostra per primi i telescopi del profilo attivo e
  include anche i modelli creati dall'utente.
- Oculari e Barlow non espongono piu' il diametro del barilotto, dato che
  NightScope non possiede la controparte meccanica del portaoculari del
  telescopio e non lo usava in alcun calcolo. Barlow assegnate con lo stesso
  moltiplicatore vengono ora raggruppate in una sola alternativa otticamente
  equivalente sia nel motore visuale sia in quello fotografico.
- Il calcolo fotografico viene richiesto soltanto per l'oggetto selezionato.
  Un segnale dedicato aggiorna la card quando cambiano target, inventario
  fotografico o condizioni correnti, senza cache, worker o cicli sui 7.585
  oggetti e senza collegare camere o risultati a Home, Planner, Equipment
  visuale, Sky Compass, raccomandazioni visuali o NSOM.
- L'aggiornamento della card fotografica confronta ora una firma semantica
  degli input: modifiche a target, telescopi, camere, reducer, Barlow, filtro
  solare o condizioni pertinenti invalidano il risultato, mentre cambi a
  oculari, filtri visuali o binocoli non provocano ricalcoli fotografici
  ridondanti.
- Corrette le quattro estremita' quadrate visibili nella schermata di
  inizializzazione al primo avvio: la finestra frameless usa ora uno sfondo
  realmente trasparente e dipinge bordo e riempimento su una superficie interna
  arrotondata, invece di applicare il solo raggio al backing opaco.
- Revisionata in italiano, inglese e spagnolo la terminologia del piano
  fotografico: fuoco primario, riduttore di focale, scala d'immagine,
  posa singola, integrazione, rotazione di campo, seeing, backfocus, frame
  rate e treno ottico usano forme astronomiche controllate dagli overlay e da
  test multilingua dedicati.
- Completezza e limiti restano metadati paralleli e non modificano il punteggio:
  seeing, fondo cielo, precisione d'inseguimento, connessione meccanica e cerchio
  d'immagine non vengono inventati. Gain/ISO, rumore di lettura, autoguida,
  precisione d'inseguimento e banda del filtro restano limiti espliciti
  dell'advisor e non vengono sostituiti con valori sintetici. Lo scorer ammette
  il Sole in modalita' video soltanto per gli ID telescopio che il chiamante
  dichiara dotati del filtro solare a tutta apertura; l'insieme vuoto resta il
  default sicuro. Anche il video advisor non inventa esposizione/gain, ROI,
  throughput, codec, diametro/fase apparente, percentuale di frame selezionati
  o derotazione. Condizioni e inventario sono ora collegati soltanto
  nell'assembler backend on demand; il presenter e la card Detail consumano il
  risultato tipizzato senza esporre lo scorer o registrarlo direttamente in
  QML.
- La montatura dei telescopi usa ora una tassonomia stabile selezionata da menu:
  OTA, altazimutale, equatoriale, forcella e Dobson, con varianti manuale,
  motorizzata, GoTo e PushTo dove pertinenti. I valori storici dei seed vengono
  normalizzati durante il bootstrap; il vecchio valore generico `manuale`
  conserva un codice esplicito non specificato. L'adattatore visuale mantiene
  gli stessi coefficienti precedenti, mentre i codici distinti restano
  disponibili al backend fotografico separato.
- Il gate finale `tools/run_checks.py --fast` passa con 1.091 test, 643 warning
  Skyfield/NumPy gia' noti e 10 subtest in 245,20 secondi, oltre agli smoke
  backend, QML normale e Red Night Vision. Il catalogo Cameras ha inoltre QML
  lint senza warning; la
  pagina Profili con camere assegnate e' stata verificata nativamente a
  `1040 × 700` e `1709 × 1047` in entrambe le modalita'. Il nuovo controllo
  del filtro solare e il relativo avviso di sicurezza sono stati verificati
  nativamente a `1400 × 900`; la scena rossa raggiunge al massimo verde 74 e
  blu 61, senza pixel oltre soglia. La nuova card fotografica e' stata
  verificata con M31 e Saturno in modalita' normale e rossa, senza tagli; il
  probe rosso raggiunge al massimo verde 16 e blu 15. I quattro angoli dello
  splash nativo hanno alpha zero. I cataloghi Qt IT/EN/ES contengono 1.979 voci
  finite e zero incomplete.
- Aggiunti nel catalogo i comandi `Attiva risultati` e
  `Disattiva risultati`: operano sull'intero risultato filtrato corrente,
  mostrano il numero esatto di target coinvolti e chiedono conferma prima
  della modifica. Gli alias vengono deduplicati per oggetto fisico e i nove
  oggetti del Sistema Solare restano attivi e non modificabili.
- La modifica massiva valida tutti i target prima di scrivere, usa una sola
  transazione SQLite, aggiorna il modello senza reset e avvia un solo refresh
  delle raccomandazioni. Le notifiche di migliaia di righe vengono accorpate e
  la UI mostra lo stato del refresh in background. Nel benchmark Windows,
  attivare o disattivare 7.366-7.585 target richiede circa 80-110 ms con una
  localita' configurata e circa 150 ms senza localita'; il singolo flag resta
  entro circa 10-28 ms. I controlli sono verificati al layout minimo sia in
  modalita' normale sia in Red Night Vision.
- Eliminato il blocco dell'interfaccia quando si cambia il flag `Home` nel
  catalogo esteso: un `QAbstractListModel` aggiorna soltanto le righe dello
  stesso target fisico, senza ricreare tutte le 7.594 righe o perdere la
  posizione di scroll. La preferenza SQLite resta immediata, mentre un debounce
  da 200 ms accorpa click ravvicinati secondo lo stato piu' recente e mantiene
  un solo worker attivo, senza accodare calcoli ormai superati.
- Il refresh del flag `Home` prepara ora nel worker anche Equipment, contesto
  di inquinamento luminoso, geometria lunare, ranking NSOM, Best Object,
  Planner e Sky Compass. Generazione, localita' e firma degli input scartano
  risultati obsoleti; il thread UI applica soltanto lo snapshot finale. Nel
  benchmark Windows con tutto attivo il click passa a circa 27 ms, la
  preparazione di 5.452 target osservabili richiede circa 3,2 s in background
  e l'applicazione grafica finale circa 6 ms. La soluzione usa thread e segnali
  Qt/Python compatibili con Windows e Linux, senza multiprocesso.
- Rifinita la tabella `Oggetti celesti`: l'area delle righe occupa soltanto lo
  spazio verticale disponibile, evitando il secondo scroll dell'intera pagina;
  la colonna Costellazione guadagna 8 px senza troncare il nome esteso di M17.
  Cambiare il flag `Home` conserva inoltre posizione e filtri della lista,
  invece di riportarla apparentemente a un altro gruppo di oggetti.
- Corretto il conteggio dei risultati quando si attiva o disattiva
  `Visibili nel mese`: la notifica del totale filtrato parte ora dopo il reset
  effettivo del modello, così checkbox, righe mostrate, stato vuoto e azioni
  massive non possono più apparire sfasati di un click.
- Corrette due identita' incrociate nel seed NGC: il numero nel nome comune
  `47 Tucanae` non viene piu' interpretato come `NGC 47`, quindi NGC 47/58
  formano il proprio target NGC-only mentre solo NGC 104 riusa Caldwell C106.
  Inoltre NGC 6882/6885 risolvono entrambe a Caldwell C37; resta intenzionale
  la distinzione editoriale tra Caldwell C49/NGC 2239 e Caldwell C50/NGC 2244.
  I database gia' inizializzati eliminano il vecchio target NGC 6882 isolato
  e ne trasferiscono l'eventuale preferenza utente a C37.
- Importato l'intero intervallo canonico NGC 1-7840 dal snapshot OpenNGC
  bloccato al commit `36cb178a`: 7.839 designazioni utilizzabili risolvono
  7.571 target fisici, 205 identita' Messier/Caldwell gia' esistenti vengono
  riusate e 7.366 nuovi target NGC-only portano il catalogo deep-sky a 7.585
  oggetti unici. `NGC 412`, marcato non esistente dalla sorgente, viene
  escluso; alias e oggetti composti come NGC 6/20 e NGC 650/651 non duplicano
  calcoli o preferenze.
- I target NGC-only partono esclusi dai suggerimenti automatici ma possono
  essere attivati singolarmente e mantengono la scelta nel database locale.
  Gli oggetti gia' curati come Messier o Caldwell conservano il proprio valore
  iniziale anche quando possiedono designazioni NGC. Descrizione e curiosita'
  dei nuovi oggetti mostrano esplicitamente `Work in progress`, in attesa
  dell'arricchimento editoriale graduale.
- Lo schema SQLite passa alla versione 19: `CatalogueDesignation` ammette piu'
  alias dello stesso catalogo per un solo target, continuando a imporre
  designazioni normalizzate uniche e una sola designazione primaria. La
  migrazione da schema 18 conserva le preferenze utente.
- L'ammissione ai suggerimenti viene risolta in SQL prima di coordinate,
  visibilita' e geometria lunare. Skyfield elabora inoltre in batch NumPy i
  target fissi per raccomandazioni, visibilita' mensile e separazione dalla
  Luna, con fallback scalare multipiattaforma. La join delle preferenze usa la
  chiave `NOCASE` indicizzata invece di applicare `LOWER()` riga per riga: nel
  caso tutto attivo la sola query passa da circa `18,9 s` a `0,15 s`. Nel
  benchmark Windows end-to-end il refresh controllato passa da `7,55 s` con i
  219 default a `12,45 s` con tutti i 7.585 target attivi, incluso catalogo
  mensile, eventi, Equipment, NSOM, Planner e Sky Compass. Il lavoro resta nel
  worker esistente e non e' stato introdotto multiprocesso.
- La pagina Oggetti celesti usa ora una lista virtualizzata adatta a migliaia
  di righe, conserva la designazione NGC esatta nel dettaglio anche per gli
  alias e accetta ricerche compatte come `NGC1` senza confonderle con codici
  Caldwell come `C23`. Aggiunti attribuzione, licenza completa
  `CC-BY-SA-4.0`, snapshot riproducibile e controllo offline OpenNGC; aggiornate
  le traduzioni IT/EN/ES e i bundle Windows/Linux.
- Il gate finale `tools/run_checks.py --fast` passa con 966 test, 643 warning
  Skyfield/NumPy gia' noti, 10 subtest, smoke backend, QML normale e Red Night
  Vision. Il test asincrono dell'Update Manager attende ora la consegna del
  segnale Qt prima del teardown, eliminando la relativa race del runner
  parallelo. Il gate di sicurezza precedente ha inoltre confermato 84% di
  copertura su 16.429 statement runtime e nessuna vulnerabilita' nota
  nell'ambiente installato.
- Aggiunta al catalogo Oggetti celesti la colonna compatta `Home`: i 219
  oggetti Messier e Caldwell sono attivi per impostazione iniziale, restano
  modificabili e salvano ogni scelta nel database locale; i 9 oggetti del
  Sistema Solare S1-S9 sono invece sempre selezionati e non disattivabili. Un
  oggetto modificabile disattivato resta consultabile nel catalogo ma viene
  escluso, prima dei calcoli di raccomandazione, da configurazioni Equipment,
  Home, Best Object, Planner e Sky Compass. Lo schema SQLite passa alla
  versione 18 mantenendo gli override utente separati dai valori predefiniti
  del seed.
- Ridisegnata la schermata di preparazione al primo avvio: i testi sono ora in
  inglese e quattro step distinti mostrano database, cataloghi locali, servizi
  applicativi e caricamento dell'interfaccia. L'avanzamento resta monotono,
  riporta il numero di righe elaborate durante l'importazione delle localita' e
  la schermata attende il primo frame della UI QML prima di chiudersi, con un
  fallback di sicurezza.
- Generato il bundle Linux `1.42.0` nella baseline Debian 12 x86-64/glibc 2.36.
  La dist contiene `5.419` file per `576 MiB`, inclusi i nuovi cataloghi camera
  e la licenza OpenNGC. Il tar deterministico misura `273.018.788` byte e ha
  SHA-256
  `1961ac3be264001d1735bcff09c7bf23e58835c75c2dc49af679c8d6e532da2a`.
  Checksum, audit, estrazione pulita, backend e QML normale/rosso sono passati
  su Debian 12, Debian 13 e Ubuntu 26.04, inclusi Wayland e XCB.

## NightScope 1.41.0 - 2026-07-24

- Verificata l'esecuzione da sorgente su Ubuntu 26.04 LTS con Python 3.14.4,
  PySide/Qt 6.11.1 e GNOME/Wayland. Il backend Wayland viene selezionato
  automaticamente e il fallback X11/XCB carica correttamente tutte le librerie
  native richieste.
- Documentati i pacchetti Ubuntu e i comandi Bash per creare la venv,
  installare le dipendenze runtime/developer e avviare NightScope.
- Corretto il teardown QML: il `TranslationManager` rilascia il riferimento al
  `QQmlApplicationEngine` prima della distruzione dei context object. La
  chiusura reale Wayland e gli smoke QML normale/rosso non producono piu'
  binding verso controller null; avvio e comportamento Windows restano
  invariati.
- Il generatore delle licenze risolve ora la licenza Python sia dalla root
  dell'installazione Windows sia dalla directory standard library usata da
  Linux. Windows conserva il confronto byte-per-byte con l'archivio di release;
  gli altri host verificano l'intera closure installata senza confrontarla con
  l'inventario binario Windows.
- Il test dell'ordine dei provider Windows dichiara esplicitamente la
  piattaforma `win32`, evitando che un host Linux sostituisca correttamente i
  mock Windows con GeoClue. Il runtime dei provider non cambia.
- Il test del retry meteo verifica l'intervallo configurato invece del tempo
  residuo nativo, che Qt puo' arrotondare di pochi millisecondi su Linux. Il
  ritardo runtime resta invariato su tutte le piattaforme.
- Aggiunto `ruff.toml` con target Python 3.12 e selezione esplicita delle regole
  storiche. Ruff 0.15 e 0.16 producono cosi' lo stesso gate senza modifiche
  automatiche massive al sorgente.
- Aggiunto `packaging/build_linux.sh`: genera la directory PyInstaller
  `dist/NightScope`, copia gli avvisi legali, produce un archivio licenze dalla
  closure Python Linux installata e avvia l'audit bundle multipiattaforma. Lo
  spec include Secret Service su Linux ed esclude soltanto il backend keyring
  Windows, che resta invariato nelle build Windows.
- I hook Linux rimuovono Qt Virtual Keyboard, non usato e fuori dal perimetro
  Qt selezionato, e il plugin TIFF non usato che sulla macchina di build
  richiedeva `libtiff.so.5`. Wayland, XCB, immagini applicative e QML restano
  presenti.
- La prima dist nativa Ubuntu `1.41.0` contiene `5.384` file per `550 MiB`;
  passano audit, backend smoke, QML Wayland normale/rosso e QML XCB. L'archivio
  licenze Linux copre `63` distribuzioni, incluse `jeepney` e `SecretStorage`.
- Per il candidate Ubuntu, l'inventario legale associa `118` ELF di sistema a
  `84` pacchetti binari e `61` pacchetti sorgente, registra gli SHA-256 e gli
  URL Launchpad esatti, copia `61` avvisi copyright e `15` testi canonici
  richiamati. Tutti i `61` URL sorgente rispondono HTTP 200. L'audit blocca
  file non inventariati, digest modificati, avvisi mancanti e riferimenti non
  risolti.
- `THIRD_PARTY_NOTICES.md` e il nuovo `SOURCE_CODE.md` coprono ora entrambi i
  bundle Windows/Linux, il tag sorgente `v1.41.0` e la sostituzione/relink delle
  librerie Qt `.dll`/`.so` senza modificare il runtime applicativo.
- Aggiunto `packaging/archive_linux.sh`: il primo candidate crea in modo
  deterministico
  `NightScope-v1.41.0-ubuntu-26.04-x64.tar.gz` e il relativo file `.sha256`.
  Il tar da `263.798.525` byte (`252 MiB`) conserva una directory radice
  `NightScope`, e dopo
  verifica del digest ed estrazione pulita supera nuovamente audit e smoke
  backend, Wayland normale/rosso e XCB. SHA-256:
  `630ec09655a441d79564d6ac6618848dcf4c68cd3fb47b8020b6236122b24673`.
- Il gate Ubuntu `tools/run_checks.py --fast` passa con `921 passed`, `1
  skipped`, `642 warnings` note e `10 subtests`; passano inoltre `pip check`,
  Ruff 0.16.0, `compileall`, closure licenze, snapshot MPC, smoke backend/QML,
  avvio reale Wayland e sonda XCB.
- Aggiunto `packaging/build_linux_debian12.sh`: Docker o Podman costruiscono il
  bundle di rilascio su Debian 12/Python 3.12 con baseline glibc 2.36, senza
  ereditare la baseline della workstation Ubuntu.
- La dist Debian finale contiene `5.415` file per `575 MiB`. L'inventario
  copre `146` ELF nativi, `84` pacchetti binari, `63` pacchetti sorgente Debian
  e il runtime CPython, con `64` avvisi copyright, `15` testi di licenza comuni
  e `64/64` URL Debian Sources/CPython verificati.
- Il tar finale
  `NightScope-v1.41.0-debian-12-x64.tar.gz` misura `272.546.505` byte
  (`260 MiB`) e ha SHA-256
  `24490604996561e90b2b3e78ed1d2be1b4530d6ec679190ca81fe32c5f396ef5`.
  Audit, backend e QML normale/rosso passano dopo estrazione pulita; la stessa
  build e' stata verificata su Debian 12, Debian 13 e Ubuntu 26.04.
- La versione sorgente e la release pubblica passano a `1.41.0`. Il tag
  `v1.41.0` punta al commit `7d95aa6`; la release GitHub pubblica insieme il
  bundle Windows e l'archivio Debian 12 x86-64 con checksum adiacente, cosi'
  l'Update Manager non propone una release priva dell'asset della piattaforma.
  Il tarball resta specifico per architettura e baseline glibc e non viene
  presentato come binario Linux universale.

## NightScope 1.40.1 - 2026-07-23

- Corretto il parsing dell'altezza massima prodotta dal motore Skyfield nel
  formato con simbolo dei gradi. Recommendation Engine e difficolta' non
  interpretano piu' le altitudini runtime valide come zero.
- Il contesto urbano Bortle/VIIRS conserva score, nota e ordinamento di
  compatibilita' per la presentazione, ma non modifica piu' la visibilita'
  astronomica e non elimina candidati prima di Home, Planner, Best Object e Sky
  Compass. I quattro consumer continuano a ricevere il target grezzo tramite il
  read model e applicano una sola volta il fattore NSOM di sky background.
- Verificati tre flussi Skyfield reali al 23 luglio 2026: Nairobi mantiene
  `195/195` candidati, Roma `148/148` e Sydney `165/165`, con tutte le altezze
  interpretate. La matrice Equipment aggiornata copre 375 combinazioni di
  profilo, condizioni e target senza violazioni.
- Il gate completo con coverage e security e' passato: `917 passed`, `642`
  warning note, `10 subtests`, coverage `84%` su `16.032` statement, snapshot
  MPC e smoke backend/QML normale/rosso superati, nessuna vulnerabilita' nota.
- La versione sorgente, la distribuzione Windows e la release GitHub
  `v1.40.1` sono state pubblicate dal commit `7b6da6d`.

## NightScope 1.40.0 - 2026-07-23

- Aggiunto un confine condiviso per il backend credenziali usato da Earthdata e
  OpenAQ, eliminando i due loader `keyring` duplicati.
- Su Linux NightScope usa direttamente il backend
  `keyring.backends.SecretService.Keyring` e ne verifica la disponibilita'
  runtime tramite D-Bus. Backend null, fail, plaintext o plugin selezionati
  tramite configurazione `keyring` non vengono accettati come archivi sicuri.
- Se Secret Service, il daemon D-Bus o le dipendenze Linux non sono disponibili,
  i flussi credenziali esistenti riportano l'archivio di sistema come non
  disponibile senza scrivere password o API key in JSON o SQLite.
- Windows conserva il comportamento precedente tramite il dispatcher
  `keyring`; la venv verificata usa `keyring 25.7.0` con `WinVaultKeyring`.
  `SecretStorage` e `jeepney` sono gia' dipendenze condizionali Linux di
  `keyring` e non vengono duplicate nei requisiti NightScope.
- Il gate completo con coverage e security e' passato: `912 passed`, `642`
  warning note, `10 subtests`, coverage `84%` su `16.036` statement, snapshot
  MPC e smoke backend/QML normale/rosso superati, nessuna vulnerabilita' nota.
  Il test interattivo richiede ancora un desktop Linux con D-Bus e una
  collezione Secret Service sbloccata.
- La versione sorgente passa a `1.40.0`; la distribuzione Windows e la release
  GitHub pubblicata restano `1.37.0`.

## NightScope 1.39.0 - 2026-07-23

- Introdotto `RuntimePaths` come contratto unico per database, configurazione,
  cache e stato applicativo. I consumer non derivano più obbligatoriamente
  preferenze e cache dalla cartella del database.
- Su Linux i percorsi seguono XDG: dati in
  `~/.local/share/NightScope`, configurazione in `~/.config/NightScope`, cache
  in `~/.cache/NightScope` e stato/log in
  `~/.local/state/NightScope`. Gli override assoluti `XDG_*_HOME` vengono
  rispettati; valori relativi non validi ricadono sui default.
- Su Windows il comportamento resta invariato: da sorgente tutti i file runtime
  restano nella root del progetto e nella distribuzione congelata restano
  accanto all'eseguibile. macOS e piattaforme non ancora supportate conservano
  lo stesso layout portabile precedente.
- `NIGHTSCOPE_RUNTIME_DIR` mantiene priorità su ogni piattaforma e co-localizza
  dati, configurazione, cache e stato nella directory isolata, preservando gli
  smoke test e gli strumenti di sviluppo esistenti.
- La prima esecuzione Linux copia un eventuale runtime portabile precedente
  nelle nuove directory: database e backup nei dati, preferenze nella
  configurazione, cache posizione e NASA AOD nella cache. File XDG già presenti
  non vengono sovrascritti.
- `AppController` accetta percorsi espliciti per preferenze e cache, mantenendo
  come fallback la disposizione co-locata usata da test e costruttori esistenti.
  Database, schema SQLite, scoring, raccomandazioni e UI non cambiano.
- Anche l'esecuzione diretta del bootstrap database usa il resolver canonico,
  evitando di creare un database parallelo nella root del progetto su Linux.
- Gate completo con coverage e security superato: `907 passed`, `642 warnings`
  note, `10 subtests`, coverage `84%` su `16.024` statement, snapshot MPC e
  smoke backend/QML normale/rosso superati, nessuna vulnerabilità nota.
- La versione sorgente passa a `1.39.0`; la distribuzione Windows e la release
  GitHub pubblicata restano `1.37.0`.

## NightScope 1.38.0 - 2026-07-23

- Aggiunto un controllo non bloccante della versione all'avvio. Dopo il
  caricamento della finestra, `UpdateManager` interroga in background l'endpoint
  pubblico GitHub dell'ultima release stabile senza richiedere credenziali.
- Il confronto usa componenti numeriche `major.minor.patch`, quindi gestisce
  correttamente casi come `1.10.0` rispetto a `1.9.0`. Bozze, prerelease,
  risposte malformate e URL esterni al repository ufficiale vengono ignorati.
- Se esiste una versione più recente, un dialogo localizzato e compatibile con
  Red Night Vision mostra versione installata e disponibile. L'utente può
  aprire la release nel browser, rimandare oppure ignorare quella specifica
  versione.
- Errori di rete, timeout, limiti API e indisponibilità di GitHub restano
  silenziosi nell'interfaccia e non bloccano né modificano l'avvio. Il controllo
  viene eseguito al massimo una volta per sessione.
- La preferenza `ignored_update_version` viene conservata in
  `user_preferences.json` senza sovrascrivere lingua, modalità visiva o altre
  impostazioni.
- Verificato il popup a `1040 x 700` in spagnolo e Red Night Vision: dialogo
  aperto, centrato e contenuto nella finestra a `560 x 204`.
- Gate completo con coverage e security superato: `889 passed`, `642 warnings`
  note, `10 subtests`, coverage `84%` su `15.965` statement, snapshot MPC e
  smoke backend/QML normale/rosso superati, nessuna vulnerabilità nota.
- La versione sorgente passa a `1.38.0`; la distribuzione Windows e la release
  GitHub pubblicata restano `1.37.0`.

## NightScope 1.37.0 - 2026-07-22

- Aggiunto in fondo alla barra laterale il selettore persistente
  `Normale` / `Visione rossa`. Il valore predefinito resta `Normale`; il cambio
  modifica solo la presentazione e non avvia refresh o ricalcoli applicativi.
- Introdotto `AppearanceManager`, separato da `AppController`, che conserva la
  preferenza `red_night_vision_enabled` in `user_preferences.json` mantenendo
  intatte lingua, posizione e altre impostazioni.
- Centralizzati in `AppTheme` tutti i colori QML. La palette Red Night Vision
  usa esclusivamente neri e rossi a luminanza controllata per sfondi, testi,
  bordi, controlli, stati, hover, focus, grafici, bussola e fase lunare.
- Introdotto `DarkCheckBox` e sostituiti nelle pagine i `CheckBox` e
  `TextField` con rendering nativo, evitando indicatori chiari non controllati
  dal tema anche nei form di localita' e attrezzatura.
- Aggiunto `NightVisionIcon`, basato su `QtQuick.Effects`, per colorare le icone
  SVG senza duplicare gli asset. `Qt6QuickEffects.dll` e il plugin QML Effects
  diventano parte obbligatoria dell'audit del bundle.
- Le fotografie nelle schede oggetto e le miniature del piano Home vengono
  nascoste, rimosse dal layout e non caricate quando la visione rossa è attiva.
  Diagrammi e icone funzionali restano disponibili nella palette rossa.
- Aggiunto uno smoke QML dedicato alla visione rossa. La matrice offscreen di
  tutte le 13 viste a `1240 x 820`, incluso un dettaglio oggetto reale, non
  contiene pixel oltre le soglie verde/blu previste: massimi misurati `G=74`,
  `B=61`, contro `G=247`, `B=255` nel tema normale. Verificato anche il layout
  minimo `1040 x 700` in spagnolo.
- Aggiornate e compilate le etichette del selettore per italiano, inglese e
  spagnolo. Il manuale non viene modificato in questo passaggio.
- Gate completo con coverage e security superato in `335,3 s`: `865 passed`,
  `642 warnings` note, `10 subtests`, coverage `84%` su `15.823` statement e
  nessuna vulnerabilita' nota.
- Corretto il follow-up della prova su bundle: i link delle fonti seguono ora
  la palette rossa anche dopo uno switch a runtime; nella card Posizione
  attuale il nome non compete piu' con le coordinate sulla stessa riga e puo'
  andare a capo senza ellissi.
- Gate completo ripetuto dopo il follow-up: `867 passed`, `642 warnings` note,
  `10 subtests`, coverage `84%` e nessuna vulnerabilita' nota.
- La versione sorgente passa a `1.37.0`; la distribuzione Windows e la release
  GitHub `v1.37.0` sono state pubblicate dal commit `dded6a1`.

## NightScope 1.36.0 - 2026-07-22

- La card `Ricerca città` diventa `Ricerca località` e combina nello stesso
  flusso città GeoNames e osservatori MPC. La ricerca accetta nome, nome breve,
  nomi storici e codice MPC; un codice esatto ha priorità assoluta, mentre le
  città mantengono il ranking per corrispondenza e popolazione.
- Aggiunto uno snapshot offline ricavato dall'API ufficiale Observatory Codes
  del Minor Planet Center: `2.683` postazioni terrestri fisse, inclusa `R50`.
  Satelliti, osservatori mobili, geocentro e record privi di una posizione
  terrestre utilizzabile vengono esclusi dal generatore.
- Il generatore conserva longitudine e costanti di parallasse MPC, deriva
  latitudine geodetica e quota sull'ellissoide WGS84 e normalizza le longitudini
  nell'intervallo `[-180, 180)`. La verifica `--check` dello snapshot non usa la
  rete ed è adatta al gate di release.
- Introdotta la tabella separata `MpcObservatory`; lo schema SQLite passa a
  `17`. Il bootstrap importa e aggiorna lo snapshot tramite `DataImportLog`,
  migrando in-place i database esistenti senza modificare profili, osservazioni
  o altri dati utente.
- La selezione di un osservatorio usa le coordinate MPC e il risolutore
  `timezonefinder` già esistente, quindi ricerca e calcolo del fuso restano
  offline. Fonte e accuratezza sono presentate esplicitamente come MPC.
- Aggiornati UI, cataloghi Qt italiano/inglese/spagnolo, manuale trilingue,
  architettura, fonti dati, attribuzioni, spec PyInstaller e audit del bundle.
  Il bundle deve contenere `mpc_observatories_seed.csv`.
- Aggiunte regressioni per conversione WGS84, filtri del generatore, integrità
  dello snapshot, migrazione, importazione, ranking, ricerca senza accenti,
  selezione `R50`, fuso offline, QML, packaging e manuale.
- Gate completo con coverage e security superato in `262,9 s`; dopo l'ultima
  regressione sul ranking, la suite finale conta `853 passed`, `642 warnings`
  note e `10 subtests`, con coverage runtime `84%` su `15.764` statement.
  Snapshot MPC (`2.683` righe), smoke backend/QML e audit di sicurezza sono
  superati, senza vulnerabilità note.
- La versione sorgente passa a `1.36.0`; la distribuzione non è stata
  rigenerata e la release GitHub pubblicata resta `1.34.2`.

## NightScope 1.35.1 - 2026-07-22

- Generalizzata la localizzazione automatica come `Posizione di sistema`:
  Windows conserva i provider preciso e approssimato esistenti nello stesso
  ordine, mentre Linux usa il plugin Qt Positioning `geoclue2` tramite D-Bus.
- Il provider GeoClue richiede una singola posizione con timeout controllato,
  valida coordinate e accuratezza, distingue permesso negato, servizio
  disabilitato, timeout e plugin assente e riusa la risoluzione offline di
  citta' e fuso orario. Il desktop ID stabile e'
  `io.github.beastmen84.NightScope`.
- Migrata la preferenza persistita a `use_system_location_on_startup`. Il
  vecchio campo `use_windows_location_on_startup` continua a essere letto senza
  perdere il consenso e viene sostituito al primo aggiornamento delle
  preferenze; proprieta' e slot Windows restano alias di compatibilita'.
- La pagina Localita' mostra il provider Windows o GeoClue in base alle
  capacita' della piattaforma. Titoli, azioni, fallback e messaggi di risultato
  sono neutrali rispetto al sistema operativo e localizzati in italiano,
  inglese e spagnolo; aggiornato anche il manuale trilingue.
- Dichiarata la dipendenza `PySide6_Addons` per Qt Positioning, aggiunto il
  modulo allo spec PyInstaller e reso `Qt6Positioning.dll` obbligatorio
  nell'audit del bundle. Rigenerato l'archivio licenze e aggiornata la nota Qt.
- Aggiunte regressioni per selezione provider, richiesta Qt asincrona, mapping
  degli errori, desktop ID, migrazione delle preferenze, contratto QML,
  packaging e manuale. Il backend GeoClue e' coperto deterministicamente; il
  test reale D-Bus richiede un desktop Linux con GeoClue installato.
- Gate completo con coverage e security superato in `206,6 s`: `841 passed`,
  `613 warnings` note, `10 subtests`, coverage runtime `84%` su `15.615`
  statement, smoke backend/QML superati e nessuna vulnerabilita' nota.
- Nessuna modifica a database, schema SQLite, scoring o raccomandazioni; la
  distribuzione non e' stata rigenerata.
- La versione sorgente passa a `1.35.1`; la release GitHub e il pacchetto
  Windows pubblicati restano `1.34.2`.

## NightScope 1.35.0 - 2026-07-22

- Introdotto un confine centralizzato e immutabile per il rilevamento della
  piattaforma, basato su `sys.platform`, con identificazione esplicita di
  Windows, Linux, macOS e sistemi non supportati.
- Esposte ai due percorsi di avvio QML le capacita' correnti della piattaforma:
  famiglia, indicatori del sistema operativo e disponibilita' e provider della
  posizione di sistema. La mappa e' costruita una sola volta all'avvio.
- Conservato integralmente il comportamento Windows esistente. In questo primo
  step solo il provider Windows gia' implementato risulta supportato; Linux e
  macOS vengono riconosciuti ma non dichiarano ancora un provider di posizione.
- Aggiunte regressioni indipendenti dall'host per rilevamento, immutabilita',
  payload QML e inizializzazione singola. Nessuna modifica a QML visibile,
  posizione, preferenze, directory runtime, credenziali, database, scoring o
  raccomandazioni; la distribuzione non e' stata rigenerata.
- Gate completo con coverage e security superato in `245,7 s`: `832 passed`,
  `613 warnings` note e `10 subtests`; coverage runtime `84%` su `15.465`
  statement, smoke backend/QML superati e `pip-audit` senza vulnerabilita'
  note.
- La versione sorgente passa a `1.35.0`; la release GitHub e il pacchetto
  Windows pubblicati restano `1.34.2`.

## NightScope 1.34.3 - 2026-07-22

- Completata una review editoriale approfondita dei contenuti strutturati in
  italiano e inglese, con controllo LanguageTool e verifica manuale della
  terminologia astronomica e osservativa.
- Corretti in italiano accordi riferiti a Venere, `stelle leggere`, il calco
  `target`, indicazioni incomplete sull'ingrandimento e i separatori decimali
  nelle dimensioni angolari. Riviste inoltre le schede M17, M20, M78, M84, M86,
  M109, C51, C53 e C80.
- Uniformati nelle schede italiane 46 soprannomi Messier con i nomi localizzati
  gia' usati dal catalogo; rimosso da M93 il soprannome inglese non localizzato
  e completate quattro note che terminavano senza specificare l'ingrandimento.
- Corretti in inglese errori grammaticali, pronomi derivati dal genere
  italiano, calchi e termini impropri come `Trapeze`, `Markarian Range`,
  `globular stars`, `dotted edge` e verbi osservativi privi di complemento.
  Gli override editoriali e le sostituzioni restano deterministici dopo la
  rigenerazione del language pack.
- Allineata la classificazione di C53/NGC 3115 a galassia lenticolare nel seed
  catalogo e nelle presentazioni localizzate. M84 e M86 sono ora descritte con
  la classificazione intermedia ellittica/lenticolare; C51 non contiene piu'
  riferimenti a dettagli di spirale e M78 non raccomanda filtri a banda stretta.
- Corrette due stringhe UI inglesi (`mostly cloudy` e il consiglio sul filtro
  lunare), il nome `Boötes`, la preposizione nel manuale inglese e il banner del
  manuale, ora allineato alla release pubblica `1.34.2`.
- Aggiunte regressioni per terminologia, classificazioni, decimali italiani,
  overlay TS, allineamento del manuale e aggiornamento del vecchio record C53.
  Il bootstrap migra C53 solo quando tipo e descrizione coincidono ancora con i
  valori seed obsoleti, preservando contenuti personalizzati. Nessuna modifica
  a schema SQLite, scoring, raccomandazioni o comportamento della UI; la dist
  non e' stata rigenerata.
- Gate completo con coverage e security superato in `207,1 s`: `822 passed`,
  `613 warnings` note e `10 subtests`; coverage runtime `84%`, smoke backend/QML
  superati e `pip-audit` senza vulnerabilita' note.
- La versione sorgente passa a `1.34.3`; la release GitHub e il pacchetto
  Windows pubblicati restano `1.34.2`.

## NightScope 1.34.2 - 2026-07-22

- Corretto il test connessione Earthdata LAADS: la risposta OAuth che richiede
  la pre-autorizzazione viene ora classificata prima dell'errore HTTP generico.
  Lo stato passa quindi ad `Autorizza`, il messaggio indica di autorizzare
  LAADS OPeNDAP e il relativo pulsante viene abilitato.
- Distinto il rifiuto delle credenziali dalla mancata autorizzazione. Il flusso
  reale restituisce `HTTP 401` e un messaggio di credenziali non valide per una
  password errata, mentre credenziali valide senza autorizzazione restituiscono
  `HTTP 403` con il segnale OAuth di pre-autorizzazione richiesta.
- Aggiunta diagnostica priva di credenziali per autorizzazione richiesta,
  credenziali respinte e codici HTTP non riconosciuti. Un `403` senza segnali
  OAuth resta intenzionalmente un errore generico.
- Aggiunte regressioni per il `403` OAuth, il `401` con credenziali errate e il
  `403` generico. Nessuna modifica a schema SQLite, dati provider, scoring,
  raccomandazioni o stringhe localizzate.
- Abbassata da `720` a `620` px la soglia interna della card Earthdata: nome
  utente e password restano affiancati finche' dispongono ancora di spazio
  sufficiente e passano su due righe soltanto nelle card realmente compatte.
- Nel dettaglio evento, la terza card con fatti e sorgente occupa entrambe le
  colonne del layout largo. I dettagli dei passaggi ISS non lasciano piu' vuota
  la meta' destra della riga; il layout a colonna singola resta invariato.
- Gate completo con coverage e security superato: `821 passed`, `613 warnings`
  note e `10 subtests`; coverage runtime `84%`, smoke backend/QML superati e
  `pip-audit` senza vulnerabilita' note.
- La versione sorgente passa a `1.34.2`; la release GitHub e il pacchetto
  Windows `1.34.2` sono stati pubblicati successivamente dal commit sorgente
  `5f1cf9a`.

## NightScope 1.34.1 - 2026-07-21

- Il follow-up di review profonda ha corretto le distanze OpenAQ: i campi
  `distance` della API v3 sono ora interpretati sempre in metri, una stazione a
  distanza zero conserva la priorita' e i fallimenti degli endpoint `latest`
  non vengono piu' convertiti e memorizzati come assenza di dati.
- Isolato per thread lo stato errore/retry di Open-Meteo e aggiunti identificatori
  di generazione ai refresh OpenAQ, VIIRS e NASA AOD. Risultati avviati con una
  localita' o credenziali precedenti non possono piu' chiudere o sovrascrivere
  il refresh corrente.
- Serializzato l'uso temporaneo della variabile globale `NETRC` tra test
  Earthdata e download VIIRS. VIIRS interrompe ora la scansione mensile sui
  guasti di rete, autenticazione, rate limit o HTTP e ne mostra la causa
  distinta dalla legittima assenza di granuli.
- La cache della posizione IP scade dopo 24 ore ed e' presentata esplicitamente
  come posizione gia' caricata. Gli input numerici Equipment non accettano piu'
  `NaN` o infinito, il mese Catalogo iniziale segue la timezone della localita'
  e un errore di scrittura dei log passa al logging console prima della gestione
  controllata dell'avvio.
- La pagina Provider dati usa ora lo spazio disponibile per guide operative
  localizzate e responsive. Earthdata copre registrazione, attivazione e-mail,
  compilazione di tutti i campi del profilo inclusi quelli indicati come
  facoltativi, test, autorizzazione LAADS OPeNDAP e secondo test; OpenAQ copre
  account, sezione `API Keys`, salvataggio e verifica.
- Il manuale italiano, inglese e spagnolo contiene le stesse procedure estese.
  La griglia passa a una colonna alla larghezza minima e il pulsante spagnolo
  `Autorizar aplicación` non viene piu' troncato.
- Localizzate in italiano, inglese e spagnolo le nuove diagnostiche VIIRS per
  errori di rete, autenticazione, rate limit e risposte HTTP, insieme alle guide
  provider. I cataloghi Qt risultano completi con `1679` messaggi finiti e
  nessun messaggio incompleto.
- Aggiunte regressioni per concorrenza dei provider, cache IP, credenziali
  Earthdata, input numerici non finiti, mese Catalogo, fallback del logging e
  completezza delle guide provider. Nessuna modifica a schema SQLite, seed
  data, scoring o policy delle raccomandazioni.
- Gate completo con coverage e security superato: `817 passed`, `613 warnings`
  note e `10 subtests`; coverage runtime `84%`, smoke QML separati nelle tre
  lingue, `pip-audit` senza vulnerabilita' note, `qmllint` su `31` file senza
  failure e Bandit invariato a `0 high`.
- La versione sorgente passa a `1.34.1`; la release GitHub e il pacchetto
  Windows `1.34.1` sono stati pubblicati successivamente dal commit sorgente
  `4193e11`.

## NightScope 1.34.0 - 2026-07-21

- Aggiunta la localizzazione completa in spagnolo (Spagna): `1665` messaggi
  Qt/Python, contenuti strutturati di cataloghi ed Equipment e catalogo runtime
  compilato. Terminologia astronomica, ottica, provider, privacy e sicurezza
  solare sono state revisionate editorialmente, non lasciate al solo output
  automatico.
- Tradotto integralmente in spagnolo il manuale HTML, comprese tutte le 14
  sezioni, la navigazione responsive, le formule Equipment e le avvertenze di
  sicurezza.
- Aggiunto un overlay deterministico per le traduzioni TS revisionate. Gli
  updater applicano le correzioni per testo o contesto, verificano placeholder
  e riferimenti obsoleti e restano idempotenti dopo una rigenerazione.
- Il follow-up di review ha corretto `Norma` in `Escuadra`, uniformato tutte le
  istruzioni al registro formale, distinto `Eclipse` da `Eclipses` per contesto
  e inserito l'applicazione dell'overlay nella sequenza di release documentata.
- Una seconda review editoriale integrale delle `228` schede spagnole ha
  eliminato refusi e calchi, uniformato `visión periférica`, `brillo
  superficial`, `aumento`, `apertura` e `sistema solar`, e reso coerenti alias
  come `Critter Cluster` e `Vulpecula`. Sono state inoltre corrette le
  descrizioni scientifiche contraddittorie di M84, M86, C51 e C53 e rimossa la
  raccomandazione di filtri a banda stretta per la nebulosa a riflessione M78.
  Override e normalizzazioni restano deterministici e coperti da regressioni.
- Corretto il selettore lingua del manuale, rimasto su una griglia a due
  colonne dopo l'aggiunta di `ES`: `IT`, `EN` ed `ES` restano ora sulla stessa
  riga anche su mobile. Una regressione dedicata protegge il layout a tre
  colonne; il rendering e' stato verificato a `390`, `621` e `1440 px` senza
  overflow orizzontale.
- Corrette le righe del Sistema Solare nel Catalogo Oggetti: nomi e descrizioni
  conservano ora la localizzazione lazy fino al payload QML, la ricerca accetta
  il nome nella lingua attiva e anche il dettaglio di fallback non torna
  all'italiano. Aggiunta una regressione live per tutti i nove oggetti in
  inglese e spagnolo.
- Estesi i test di localizzazione a discovery, completezza, contenuti, termini
  revisionati, preferenze, formati locali e cambio live italiano/inglese/
  spagnolo. Nessuna modifica a scoring, Planner, Home, Equipment, Sky Compass,
  schema SQLite o logica delle raccomandazioni.
- Gate completo senza coverage superato prima dell'hardening: `797 passed`,
  `613 warnings` note e `7 subtests`; cataloghi IT/EN/ES completi `1665/1665`,
  smoke QML separati nelle tre lingue e manuale spagnolo verificato in Chromium
  a larghezza desktop e mobile senza overflow orizzontale.
- La versione sorgente passa a `1.34.0`; la release GitHub e il pacchetto
  Windows pubblicati restano `1.33.2` finche' non viene eseguito un nuovo ciclo
  esplicito di build e rilascio.

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
