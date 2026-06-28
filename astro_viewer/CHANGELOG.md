# Changelog

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
