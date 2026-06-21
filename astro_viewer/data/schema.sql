CREATE TABLE IF NOT EXISTS City (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT NOT NULL,
    ascii_name TEXT,
    country TEXT NOT NULL,
    country_code TEXT,
    admin_region TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timezone TEXT NOT NULL,
    population INTEGER,
    search_name TEXT
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

CREATE TABLE IF NOT EXISTS TelescopeBrand (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS TelescopeModel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    optical_type TEXT NOT NULL,
    aperture_mm INTEGER NOT NULL,
    focal_length_mm INTEGER NOT NULL,
    focal_ratio REAL,
    mount_type TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (brand_id) REFERENCES TelescopeBrand(id),
    UNIQUE (brand_id, name)
);

CREATE INDEX IF NOT EXISTS idx_telescope_model_brand ON TelescopeModel(brand_id);

CREATE TABLE IF NOT EXISTS EyepieceCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    focal_length_mm REAL NOT NULL,
    apparent_field_deg REAL NOT NULL,
    barrel_size TEXT,
    notes TEXT,
    UNIQUE (brand, model, focal_length_mm)
);

CREATE TABLE IF NOT EXISTS BarlowCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    multiplier REAL NOT NULL,
    barrel_size TEXT,
    notes TEXT,
    UNIQUE (brand, model, multiplier)
);

CREATE TABLE IF NOT EXISTS SkyQualityEstimate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_key TEXT NOT NULL UNIQUE,
    bortle_class INTEGER NOT NULL,
    limiting_magnitude REAL NOT NULL,
    sky_brightness REAL NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ObjectImages (
    object_id TEXT PRIMARY KEY,
    image_path TEXT NOT NULL,
    thumbnail_path TEXT,
    attribution TEXT NOT NULL,
    source_url TEXT,
    license TEXT,
    verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ObjectDescription (
    object_id TEXT PRIMARY KEY,
    short_description TEXT NOT NULL,
    observing_notes TEXT NOT NULL,
    best_seen TEXT,
    difficulty_naked_eye TEXT,
    difficulty_binocular TEXT,
    difficulty_small_scope TEXT,
    difficulty_medium_scope TEXT,
    difficulty_large_scope TEXT
);

CREATE TABLE IF NOT EXISTS EquipmentProfile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 0,
    telescope_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_equipment_profile_active ON EquipmentProfile(active);
