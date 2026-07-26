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

CREATE TABLE IF NOT EXISTS MpcObservatory (
    mpc_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    elevation_m REAL,
    rho_cos_phi REAL NOT NULL,
    rho_sin_phi REAL NOT NULL,
    observations_type TEXT,
    first_date TEXT,
    last_date TEXT,
    web_link TEXT,
    old_names TEXT,
    source_updated_at TEXT,
    search_name TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mpc_observatory_name ON MpcObservatory(name);
CREATE INDEX IF NOT EXISTS idx_mpc_observatory_search ON MpcObservatory(search_name);
CREATE INDEX IF NOT EXISTS idx_mpc_observatory_coordinates ON MpcObservatory(latitude, longitude);

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
    best_filter_class TEXT,
    fallback_filter_class TEXT,
    optional_color_filter_class TEXT,
    imaging_reducer_recommended INTEGER NOT NULL DEFAULT 0,
    recommendation_enabled_by_default INTEGER NOT NULL DEFAULT 1
        CHECK (recommendation_enabled_by_default IN (0, 1)),
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
    FOREIGN KEY (object_id) REFERENCES CatalogueObject(object_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_catalogue_designation_object ON CatalogueDesignation(object_id);
CREATE INDEX IF NOT EXISTS idx_catalogue_designation_catalogue ON CatalogueDesignation(catalogue, sort_index);
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_designation_primary
ON CatalogueDesignation(object_id)
WHERE is_primary = 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_catalogue_designation_normalized
ON CatalogueDesignation(LOWER(catalogue), LOWER(designation));
CREATE INDEX IF NOT EXISTS idx_catalogue_object_catalogue_normalized
ON CatalogueDesignation(object_id, LOWER(catalogue));

CREATE TABLE IF NOT EXISTS CatalogueRecommendationPreference (
    object_id TEXT PRIMARY KEY COLLATE NOCASE,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS WeatherCache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL UNIQUE,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_weather_cache_key ON WeatherCache(cache_key);

CREATE TABLE IF NOT EXISTS OrbitalElementCache (
    provider TEXT NOT NULL,
    object_id TEXT NOT NULL,
    element_format TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    source_epoch TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (provider, object_id)
);

CREATE INDEX IF NOT EXISTS idx_orbital_element_cache_expiry
ON OrbitalElementCache(expires_at);

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
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
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
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
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
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
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
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, magnification, objective_diameter_mm)
);

CREATE TABLE IF NOT EXISTS AstronomyCameraCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    camera_class TEXT NOT NULL,
    sensor_model TEXT NOT NULL,
    sensor_technology TEXT NOT NULL,
    color_mode TEXT NOT NULL,
    sensor_width_mm REAL NOT NULL,
    sensor_height_mm REAL NOT NULL,
    resolution_width_px INTEGER NOT NULL,
    resolution_height_px INTEGER NOT NULL,
    pixel_size_um REAL NOT NULL,
    bit_depth INTEGER NOT NULL,
    max_fps REAL,
    cooled INTEGER NOT NULL DEFAULT 0,
    cooling_delta_c REAL,
    shutter_type TEXT NOT NULL,
    backfocus_mm REAL,
    source_url TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model)
);

CREATE TABLE IF NOT EXISTS CameraBodyCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    body_type TEXT NOT NULL,
    sensor_format TEXT NOT NULL,
    lens_mount TEXT NOT NULL,
    sensor_width_mm REAL NOT NULL,
    sensor_height_mm REAL NOT NULL,
    resolution_width_px INTEGER NOT NULL,
    resolution_height_px INTEGER NOT NULL,
    raw_bit_depth INTEGER NOT NULL,
    max_video_width_px INTEGER,
    max_video_height_px INTEGER,
    max_video_fps REAL,
    live_view INTEGER NOT NULL DEFAULT 1,
    bulb_mode INTEGER NOT NULL DEFAULT 1,
    source_url TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model)
);

CREATE TABLE IF NOT EXISTS FilterCatalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    filter_class TEXT NOT NULL,
    central_wavelength_nm REAL,
    bandwidth_nm REAL,
    transmission_pct REAL,
    minimum_aperture_mm INTEGER,
    notes TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 0,
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model)
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
    seed_key TEXT,
    is_user_modified INTEGER NOT NULL DEFAULT 0,
    UNIQUE (brand, model, reduction_factor)
);

CREATE TABLE IF NOT EXISTS ReducerTelescopeCompatibility (
    reducer_id INTEGER NOT NULL,
    telescope_model_id INTEGER NOT NULL,
    PRIMARY KEY (reducer_id, telescope_model_id),
    FOREIGN KEY (reducer_id) REFERENCES ReducerCatalog(id) ON DELETE CASCADE,
    FOREIGN KEY (telescope_model_id) REFERENCES TelescopeModel(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reducer_compatibility_telescope
ON ReducerTelescopeCompatibility(telescope_model_id);

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
    difficulty_large_scope TEXT,
    is_builtin INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ObjectCuriosity (
    object_id TEXT PRIMARY KEY,
    curiosity_text TEXT NOT NULL,
    source_label TEXT NOT NULL,
    source_url TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    is_builtin INTEGER NOT NULL DEFAULT 1
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
    has_full_aperture_solar_filter INTEGER NOT NULL DEFAULT 0
        CHECK (has_full_aperture_solar_filter IN (0, 1)),
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

CREATE TABLE IF NOT EXISTS EquipmentProfileAstronomyCamera (
    profile_id INTEGER NOT NULL,
    astronomy_camera_id INTEGER NOT NULL,
    PRIMARY KEY (profile_id, astronomy_camera_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE,
    FOREIGN KEY (astronomy_camera_id)
        REFERENCES AstronomyCameraCatalog(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS EquipmentProfileCameraBody (
    profile_id INTEGER NOT NULL,
    camera_body_id INTEGER NOT NULL,
    PRIMARY KEY (profile_id, camera_body_id),
    FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE,
    FOREIGN KEY (camera_body_id)
        REFERENCES CameraBodyCatalog(id) ON DELETE CASCADE
);
