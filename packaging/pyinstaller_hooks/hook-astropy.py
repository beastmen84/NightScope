"""Collect only the Astropy data and modules exercised by NightScope."""

from PyInstaller.utils.hooks import collect_data_files, copy_metadata, is_module_satisfies


# NightScope only uses Astropy for coordinate/unit parsing. The upstream hook
# collects every Astropy submodule, including optional visualization modules
# that require matplotlib and can fail when pytest is installed in the venv.
datas = collect_data_files("astropy")

ply_files = []
for path, target in collect_data_files("astropy", include_py_files=True):
    if path.endswith(("_parsetab.py", "_lextab.py")):
        ply_files.append((path, target))

datas += ply_files

if is_module_satisfies("astropy >= 5.0"):
    datas += copy_metadata("astropy")
    datas += copy_metadata("numpy")

hiddenimports = [
    "astropy.coordinates",
    "astropy.units",
    "numpy.lib.recfunctions",
]

excludedimports = [
    "matplotlib",
    "pytest",
]
