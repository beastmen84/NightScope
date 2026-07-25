# OpenNGC source snapshot

`openngc-36cb178a0f69dba8bfc03a99c10512831edf1c6b-ngc.csv.gz`
is a reproducibly compressed copy of OpenNGC's `database_files/NGC.csv` at
commit `36cb178a0f69dba8bfc03a99c10512831edf1c6b` (2026-04-16).

- Upstream: <https://github.com/mattiaverga/OpenNGC>
- Snapshot file:
  <https://github.com/mattiaverga/OpenNGC/blob/36cb178a0f69dba8bfc03a99c10512831edf1c6b/database_files/NGC.csv>
- Uncompressed SHA-256:
  `e4acd595ed13888f888273fc5cb47c7934430a13348a294abdc8879b1d66fef7`
- License: Creative Commons Attribution-ShareAlike 4.0 International
  (`CC-BY-SA-4.0`); the complete text is in `OPENNGC_LICENSE.txt` at the
  repository root and in every portable bundle.

`astro_viewer/tools/update_ngc_catalogue.py` transforms the snapshot into the
generic object and designation seeds. It:

- reads the canonical NGC 1-7840 range;
- excludes the single OpenNGC entry marked `NonEx`;
- preserves all 7,839 usable canonical designations;
- resolves duplicate codes and curated Messier/Caldwell groupings to one
  physical `object_id`;
- creates 7,366 new NGC-only physical targets, disabled for automatic
  recommendations on first run;
- leaves the 205 existing Messier/Caldwell identities and their curated
  defaults untouched;
- uses `Work in progress` for NGC-only editorial descriptions.

Run the offline reproducibility check with:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_ngc_catalogue.py --check
```
