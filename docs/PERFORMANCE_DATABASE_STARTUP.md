# Database Startup Optimization

Included in source 1.47.0 and its local Windows build. The implementation
record below describes the original 1.46.21 source-only work; its version and
distribution statements are historical. Current artifact evidence: `TESTING.md`.

Scope: local database initialization, including the user's subsequent explicit
authorization to reuse unchanged valid backups on 2026-09-19. VERSION remains 1.46.21. No Home,
astronomy, location, network, scheduling, distribution or publication changes.

## Implementation and safety boundary

`bootstrap._seed_builtin_catalogues` contains the original seed calls, in their
original order. Their parsing, validation, merge, repair and customization
implementations are unchanged. `database/seed_cache.py` can skip this group
only when both bundled inputs and the complete relevant database state match a
checkpoint committed with a successful seed operation.

- SHA-256 covers all 15 source CSVs, schema SQL, schema version and an explicit
  seed-logic revision. File modification times and sizes alone are insufficient.
- Complete rows/columns from 17 dependency tables are streamed into the state
  fingerprint, along with SQLite schema definitions. This includes custom rows,
  equipment, aliases, recommendation overrides, images, descriptions and
  curiosities. Same-row-count edits and deletions invalidate the checkpoint.
- A reserved `DataImportLog` entry (`nightscope-builtin-seeds`) stores the
  checkpoint, with its content signature in `source_mtime`. No schema migration,
  external cache file or public database version change is required.
- Cache decisions, seeds and checkpoint writes share the caller's transaction;
  an immediate write transaction is started if necessary. Inputs are checked
  again before saving a new checkpoint. Failures are not committed as successes.
- Missing, invalid, incompatible or unreadable cache/input metadata uses the
  original full seed path. Required source errors still fail normally. Custom
  SQLite triggers disable this optimization so their seed side effects remain.
- Existing integrity checks, corruption quarantine, schema repairs and migrations
  still run. Backups remain protected as described below. Default-profile repair also runs
  every time. GeoNames/MPC keep their separate existing import rules.
- Normal weather/history/profile-selection writes do not invalidate catalogue
  seeds. Changing catalogue preferences or equipment does invalidate them; the
  ordinary seed logic then preserves its existing customization rules.

Maintenance requirement: increment `SEED_REVISION` for any code-only change to
seed behavior (including image retirement/identity correction helpers), and add
every new input file/table dependency to the corresponding fingerprint list.
CSV edits and schema edits invalidate automatically. The cache is not a substitute
for integrity checking or a trust boundary against a deliberately forged DB.

The deliberate storage differences are the additional import-log entry and less
`sqlite_sequence` churn: redundant SQLite UPSERT attempts used to consume allocator
values even without creating records. Actual stored object/equipment/profile IDs,
foreign keys and all business fields must match the unconditional seed path.

## Backup reuse

`database/backup_cache.py` checks the entire database and the existing backup
using SHA-256, not modification times, file sizes, or only catalogue tables.
Both files are held in SQLite read transactions during comparison. In the
ordinary rollback-journal mode, concurrent SQLite writers cannot commit changes
to the file being checked while its read lock is held.

An optional `nightscope.db.backup.state.json` records the source hash and the hash
of the last successfully validated snapshot. The latter is calculated on the
temporary snapshot **before** atomic installation, not by trusting a later read
of a potentially changed destination. The metadata itself is atomically replaced
only after a successful backup; metadata-write failures leave the valid backup
usable and simply require a new full copy at the next start. It contains hashes,
not user records, and is excluded from Git and release-bundle acceptance.

- Matching source and verified backup bytes: reuse, without rewriting either.
- Source changed, backup missing/changed/corrupt, or metadata missing/invalid:
  create the same fully validated, flushed, atomic SQLite snapshot as before.
- Source in WAL mode: always use the full SQLite backup API, including committed
  WAL content and excluding uncommitted transactions. No WAL shortcut is claimed.
- A destination backup with an external WAL is not overwritten underneath it;
  the existing bootstrap warning policy applies, preserving the external files.
- Copy failures retain the prior backup/checkpoint. A redirected backup path is
  rejected; redirected/unwritable optional metadata cannot overwrite another file.

The source integrity check still runs on every start. The unchanged backup's
integrity check need not be repeated because its complete content hash must match
the previously validated copy. Metadata is an optimization, not a trust boundary
against deliberately forged local files.

Bootstrap also avoids rewriting `PRAGMA user_version` when already current. That
redundant assignment changed the file header on every start and would defeat
whole-file equality despite no logical data change. Actual upgrades still set
the version. A regression test verifies byte-identical DB content across complete
unchanged bootstraps and asserts that no snapshot is recreated.

The first adoption may need an additional full backup at the following start:
the seed checkpoint itself initially changes the DB. A pre-migration backup must
not be relabeled as containing those later changes. Ordinary runtime changes,
including weather/history/profile writes, also correctly require a fresh backup.

## Validation

Baseline before edits: 58 database/fixture tests passed in 155.78 s.
The initial focused run passed 53 seed-cache/fixture tests. Additional fault and
transaction tests then exposed two incorrect test-fixture assumptions (the city
fixture's default extra rows and an incomplete invalid-CSV header); both fixtures
were corrected without changing production behavior.

The independent probe loads the original bootstrap directly from Git `db03b1f`,
not a second implementation of the new cache. After the backup extension, all 60
existing functions other than `_build_database` and `_backup_database` are
AST-identical. Fresh databases, a first start on a
copy of the real development DB, and repeat starts match every business row and
schema definition. This includes 7,585 objects, 8,058 designations, 33,775 cities
and 327,374 city aliases. Import telemetry and allocator counters are excluded
from this comparison for the reasons above; focused tests also check the normal
import-log fields. No existing runtime file is used as a writable test target.

Before the backup extension, the first complete suite passed 1,959 tests and ten
subtests; its sole failure was the developer-tooling inventory still expecting
271 Python files instead of 273. The explicit inventory is updated to 275 after
adding both cache modules and their test files. The final gate covers both changes.

Final `tools/run_checks.py --security` passes: **1,989 tests and ten subtests**
in 416.00 s, 87% overall coverage (19,222 / 22,133 statements), 100% seed-cache
and 99% backup-cache statement coverage. This adds 76 cache/backup regression
cases and two bundle-exclusion cases to the existing suite. Ruff, documentation
inventory (275 Python / 36 QML / 17 operational files), import boundaries,
unchanged Bandit baseline, dependency checks and all data/editorial checks pass;
pip-audit reports no known vulnerabilities. Isolated backend, normal QML and
Red Night Vision smokes pass in 18.8 / 19.2 / 18.5 s.
Log: `build/database-startup-20260919/full-source-gate-final.log`.

The real `nightscope.db`, `nightscope.db.backup`, `user_preferences.json` and
`location_cache.json` retain their pre-work SHA-256 values. All active test and
benchmark runtimes are disposable; no real-runtime checkpoint was created.
Source validation and the local commit do not imply a bundle rebuild or public
release.

## Initial seed-only measurements

`build/database-startup-20260919/compare_bootstrap.py` records results in
`bootstrap-comparison.json` and `.log`. It uses temporary databases and a
consistent read-only snapshot of the 62,472,192-byte development database;
repeat-start pairs alternate execution order. No network operation is timed.

| Measurement | Original | Optimized | Interpretation |
| --- | ---: | ---: | --- |
| Seed stage, median of 7 | 0.314 s | 0.147 s | About 53% less time for this stage only |
| Repeat complete DB bootstrap, median of 7 | 5.945 s | 5.877 s | Small difference within substantial timing variability |
| New DB without GeoNames, median of 3 | 2.564 s | 2.659 s | About 0.095 s extra to establish the checkpoint |

Whole-bootstrap repeat ranges overlap: 5.765-6.235 s original versus
5.681-6.602 s optimized. This is **not evidence of a robust end-to-end startup
speedup**, and is not a measurement of splash plus Home readiness. The first
single existing-DB pair was 3.381 s original versus 6.222 s optimized; this
unfavorable observation is retained, not discarded. The subsequent three-pair
stage probe measured source integrity at 2.21-2.29 s and the unconditional
backup at 3.02-3.34 s. Establishing the seed checkpoint added 0.146-0.182 s to
the seed stage. These stage results locate the cost without attributing the
single first-start outlier entirely to the cache.

The same probe measured Python allocation peaks of about 15.0 MiB for full
seeding versus 0.40 MiB for the cache check (three repetitions). This is only
that stage's traced Python allocations, not total process RSS or native memory.
Evidence: `bootstrap-stages.json` and `bootstrap-stages.log` in the same folder.

## Combined seed and backup measurements

The repeated Git-baseline comparison is recorded separately in
`bootstrap-comparison-with-backup-reuse.json` and `.log`. On seven alternating
pairs, complete DB bootstrap medians are **5.645 s original versus 2.544 s
optimized**, about 3.10 s / 55% less time in this local, unchanged-DB scenario.
The first optimized repetition still creates its backup (5.465 s); the following
six reuse it and range from 2.493 to 2.570 s. The original range is 5.516-6.157 s.
All business rows/schema still match the original Git bootstrap.

The first existing-DB pair is 6.058 versus 6.032 s; it cannot reuse a checkpoint
yet. New-database medians without GeoNames are 2.418 versus 2.538 s (three pairs),
about 0.12 s extra to establish seed metadata. No first-install speedup is claimed.
Seed-only medians in this rerun are 0.294 versus 0.142 s. These timings exclude
Python import/QML/Home startup and are not predictions for the user's Xeon.

## Limits

This primarily benefits repeat starts with unchanged seed inputs and catalogue
state. A new installation, an update to seed inputs, repairs or catalogue edits
still perform the full seed work and additionally establish a checkpoint. It does
not remove the source integrity check or necessary backups, and does not optimize
Home calculations. Local bootstrap measurements are not whole-application startup
measurements and cannot predict the reported user's Xeon timings.
