# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).parent
APP_DIR = ROOT / "astro_viewer"

datas = [
    (str(APP_DIR / "app" / "ui"), "astro_viewer/app/ui"),
    (str(APP_DIR / "resources"), "astro_viewer/resources"),
    (str(APP_DIR / "data" / "schema.sql"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "messier_seed.csv"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "nightscope.db"), "astro_viewer/data"),
    (str(APP_DIR / "data" / "skyfield" / "de421.bsp"), "astro_viewer/data/skyfield"),
]

a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["tzdata"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
