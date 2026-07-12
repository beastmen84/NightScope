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
    aliases TEXT,
    search_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_city_name ON City(city_name);
CREATE INDEX IF NOT EXISTS idx_city_country ON City(country);
CREATE INDEX IF NOT EXISTS idx_city_coordinates ON City(latitude, longitude);

CREATE TABLE IF NOT EXISTS CityAlias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'geonames',
    FOREIGN KEY (city_id) REFERENCES City(id) ON DELETE CASCADE,
    UNIQUE (city_id, normalized_alias)
);

CREATE INDEX IF NOT EXISTS idx_city_alias_normalized ON CityAlias(normalized_alias);

CREATE TABLE IF NOT EXISTS DataImportLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL UNIQUE,
    source_path TEXT NOT NULL,
    source_size INTEGER NOT NULL,
    source_mtime TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS CatalogueObject (
    object_id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL,
    costellazione TEXT NOT NULL,
    magnitudine REAL,
    ascensione_retta TEXT NOT NULL,
    declinazione TEXT NOT NULL,
    dimensione_apparente TEXT,
    max_angular_size_deg REAL,
    recommended_observation_type TEXT,
    descrizione TEXT
);

CREATE INDEX IF NOT EXISTS idx_catalogue_object_type ON CatalogueObject(tipo);
CREATE INDEX IF NOT EXISTS idx_catalogue_object_constellation ON CatalogueObject(costellazione);
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_object_id_normalized
ON CatalogueObject(LOWER(object_id));

CREATE TABLE IF NOT EXISTS CatalogueDesignation (
    catalogue TEXT NOT NULL,
    designation TEXT NOT NULL,
    object_id TEXT NOT NULL,
    sort_index INTEGER,
    is_primary INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (catalogue, designation),
    UNIQUE (object_id, catalogue),
    FOREIGN KEY (object_id) REFERENCES CatalogueObject(object_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_catalogue_designation_object ON CatalogueDesignation(object_id);
CREATE INDEX IF NOT EXISTS idx_catalogue_designation_catalogue ON CatalogueDesignation(catalogue, sort_index);
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_designation_primary
ON CatalogueDesignation(object_id)
WHERE is_primary = 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_designation_normalized
ON CatalogueDesignation(LOWER(catalogue), LOWER(designation));
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_object_catalogue_normalized
ON CatalogueDesignation(object_id, LOWER(catalogue));

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
    is_builtin INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (brand_id) REFERENCES TelescopeBrand(id),
    UNIQUE (brand_id, name)
);

CREATE INDEX IF NOT EXISTS idx_telescope_model_brand ON TelescopeModel(brand_id);

CREATE TABLE IF NOT EXISTS EyepieceCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    eyepiece_type TEXT NOT NULL DEFAULT 'Fixed',
    focal_length_mm REAL NOT NULL,
    min_focal_length_mm REAL,
    max_focal_length_mm REAL,
    apparent_field_deg REAL NOT NULL,
    afov_min REAL,
    afov_max REAL,
    barrel_size TEXT,
    zoom_click_positions_mm TEXT,
    notes TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, focal_length_mm)
);

CREATE TABLE IF NOT EXISTS BarlowCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    multiplier REAL NOT NULL,
    barrel_size TEXT,
    notes TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, multiplier)
);

CREATE TABLE IF NOT EXISTS BinocularCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    magnification INTEGER NOT NULL,
    objective_diameter_mm INTEGER NOT NULL,
    image_stabilized INTEGER NOT NULL DEFAULT 0,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, magnification, objective_diameter_mm)
);

CREATE TABLE IF NOT EXISTS FilterCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    filter_class TEXT NOT NULL,
    barrel_size TEXT NOT NULL,
    central_wavelength_nm REAL,
    bandwidth_nm REAL,
    transmission_pct REAL,
    minimum_aperture_mm INTEGER,
    notes TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, barrel_size)
);

CREATE TABLE IF NOT EXISTS ReducerCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    reduction_factor REAL NOT NULL,
    optical_system TEXT NOT NULL,
    compatible_models TEXT,
    connection TEXT,
    backfocus_mm REAL,
    visual_compatible INTEGER NOT NULL DEFAULT 0,
    imaging_compatible INTEGER NOT NULL DEFAULT 1,
    corrected_field INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, reduction_factor)
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

CREATE TABLE IF NOT EXISTS ObjectCuriosity (
    object_id TEXT PRIMARY KEY,
    curiosity_text TEXT NOT NULL,
    source_label TEXT NOT NULL,
    source_url TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS EquipmentProfile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL DEFAULT 0,
    telescope_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_equipment_profile_active ON EquipmentProfile(active);

CREATE TABLE IF NOT EXISTS EquipmentProfileTelescope (
    profile_id INTEGER NOT NULL,
    telescope_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, telescope_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS EquipmentProfileEyepiece (
    profile_id INTEGER NOT NULL,
    eyepiece_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, eyepiece_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS EquipmentProfileBarlow (
    profile_id INTEGER NOT NULL,
    barlow_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, barlow_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS EquipmentProfileBinocular (
    profile_id INTEGER NOT NULL,
    binocular_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, binocular_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS EquipmentProfileFilter (
    profile_id INTEGER NOT NULL,
    filter_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, filter_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS EquipmentProfileReducer (
    profile_id INTEGER NOT NULL,
    reducer_id TEXT NOT NULL,
    PRIMARY KEY (profile_id, reducer_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
);
