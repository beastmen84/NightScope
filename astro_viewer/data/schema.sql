CREATE TABLE IF NOT EXISTS City (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT NOT NULL,
    country TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timezone TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_city_name ON City(city_name);
CREATE INDEX IF NOT EXISTS idx_city_country ON City(country);

CREATE TABLE IF NOT EXISTS MessierObject (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    messier_id TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    costellazione TEXT NOT NULL,
    magnitudine REAL,
    ascensione_retta TEXT NOT NULL,
    declinazione TEXT NOT NULL,
    dimensione_apparente TEXT,
    descrizione TEXT
);

CREATE INDEX IF NOT EXISTS idx_messier_id ON MessierObject(messier_id);
CREATE INDEX IF NOT EXISTS idx_messier_type ON MessierObject(tipo);
CREATE INDEX IF NOT EXISTS idx_messier_constellation ON MessierObject(costellazione);

CREATE TABLE IF NOT EXISTS WeatherCache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL UNIQUE,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_weather_cache_key ON WeatherCache(cache_key);

CREATE TABLE IF NOT EXISTS ObservationHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    object_name TEXT NOT NULL,
    location TEXT NOT NULL,
    telescope TEXT,
    eyepiece TEXT,
    rating INTEGER,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_observation_date ON ObservationHistory(date);
CREATE INDEX IF NOT EXISTS idx_observation_object ON ObservationHistory(object_name);
