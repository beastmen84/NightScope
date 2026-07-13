# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).parent
APP_DIR = ROOT / "astro_viewer"

datas = [
    (str(ROOT / "VERSION"), "."),
    (str(ROOT / "manuale.html"), "."),
    (str(APP_DIR / "app" / "ui"), "astro_viewer/app/ui"),
    (str(APP_DIR / "translations"), "astro_viewer/translations"),
    (str(APP_DIR / "resources"), "astro_viewer/resources"),
    (str(APP_DIR / "data" / "schema.sql"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "catalogue_objects_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "catalogue_designations_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "telescope_catalog_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "eyepiece_catalog_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "barlow_catalog_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "binocular_catalog_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "filter_catalog_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "reducer_catalog_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "reducer_telescope_compatibility_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "light_pollution_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "object_images_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "object_descriptions_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "object_curiosities_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "cities15000.txt"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "countryInfo.txt"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "admin1CodesASCII.txt"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "skyfield" / "de421.bsp"), "astro_viewer/data/skyfield"),
]

a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["tzdata", "keyring.backends.Windows"],
    hookspath=[str(ROOT / "packaging" / "pyinstaller_hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "astropy.visualization",
        "astropy.visualization.wcsaxes",
        "matplotlib",
        "pytest",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NightScope",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_DIR / "resources" / "icons" / "nightscope.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NightScope",
)
