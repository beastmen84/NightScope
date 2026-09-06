# Personal Object Images

Import is implemented in source 1.46.12; source 1.46.13 completes lifecycle
hardening in [the approved roadmap](OBJECT_IMAGERY_ROADMAP.md). The complete
feature is available in public Windows 1.46.13. The public Linux package
remains 1.43.0 and does not yet include it. There is no separate backup/export GUI.

## User Contract

Click a picture in either Object Detail branch, or its image-management button.
Choose a JPEG/PNG, inspect its preview and confirm before changing the saved
image. Closing or cancelling changes nothing. Replacement uses the same flow;
reset needs confirmation and returns to the category illustration or Solar
System photograph. M31 and NGC 224, for example, own one shared association.

Images remain local: there is no upload, download or cloud service. Originals
are never changed, moved or removed. Input is capped at 20 MiB, 32 million
pixels and 12,000 pixels per edge; animated PNG, GIF, TIFF and FITS are rejected.
JPEG/PNG recognition uses file contents, not only extensions. Validation happens
before decoding; paths received from QML must be local, not remote URLs or UNC.

The normalized JPEG preserves aspect ratio, applies EXIF orientation, converts
valid colour profiles to sRGB and composites transparency onto a dark matte.
Its longest edge is at most 1,600 pixels; a separate thumbnail is at most 320.
Small pictures are not enlarged. Re-encoding strips EXIF/GPS/comments: the
app-managed copy is for display, not a lossless astrophotography master.

Red Night Vision empties image sources and disables file selection and preview.
The management and reset controls remain accessible. Enabling red mode cancels
an in-flight preview; a late decode cannot make a bright image reappear.

## Ownership And Persistence

- `database/personal_image_repository.py`: schema-27 `PersonalObjectImages`
  stores canonical `object_id`, SHA-256 `image_hash` and UTC `updated_at` only.
  No original path, filename or image bytes are stored in SQLite.
- `services/personal_images.py`: local validation/normalization and managed
  files under `<database directory>/user_images/`. Full images use
  `<hash>.jpg`, thumbnails `<hash>-thumb.jpg`. Exact-name reuse deduplicates
  identical normalized images. Storage rejects redirects outside this directory
  and does not overwrite an existing hash-named file with different bytes.
- `viewmodels/object_image_manager.py`: one background QImage decoder; one
  cancellable generation at a time; temporary preview outside runtime data.
  QML cannot directly write records or choose storage paths.
- `application/dependencies.py`: owns construction. `AppController` resolves
  catalogue aliases, exposes image metadata and publishes changes. Home consumes
  thumbnails; neither image selection nor reset refreshes astronomy/scoring.

Both immutable files are installed before the SQLite association is committed.
A disk or DB failure preserves the previous association. A failure can leave
unreferenced files, but cannot point a successful association at half-written
data. Reset/replacement intentionally keeps old managed files: an older database
backup may still reference them. There is no automatic garbage collection.
Reset is therefore not a secure erasure command or a promise to reclaim space.

Startup reads associations and metadata, not all photographs. Absolute `file:`
URLs are rebuilt from the current database location, so moving the runtime
directory does not preserve stale original paths. The main image is loaded
asynchronously only when visible. A missing thumbnail uses the full image;
missing/undecodable full images fall back to the default, with its correct
category label or scientific credit. The association remains available for
replacement/reset instead of silently losing the user's choice.

## Backup And Restore

The automatic `nightscope.db.backup` contains SQLite, not embedded photographs.
It is a single rotating recovery snapshot, refreshed at initialization; it is
not versioned history and not a substitute for a separate complete backup.
Source 1.46.13 uses SQLite's backup API, including committed WAL transactions,
then validates and flushes the temporary snapshot before atomically replacing the
previous backup. A failed or timed-out copy leaves the previous backup intact
and logs a warning. The copy loop has a ten-second deadline.

Reset/replacement retains old hash-named pictures, so associations from an older
DB backup can still resolve them. Copying only `nightscope.db.backup` to another
machine will not copy those images. Do not manually remove `user_images` while
keeping a database that references it. History retention also means reset does
not immediately reclaim disk space; this is deliberate, not secure erasure.

For a complete manual backup:

1. Close all NightScope instances. Copy the runtime `nightscope.db` and the
   entire adjacent `user_images` directory together to a separate location.
   Also keep `nightscope.db.backup` if recovery of its earlier state is useful.
2. Copy `user_preferences.json` to retain language, appearance and settings.
   Windows portable builds keep these beside the executable. Linux uses the
   XDG data directory for SQLite/images and the XDG configuration directory for
   preferences; see [Runtime data ownership](ARCHITECTURE.md#runtime-data-ownership).
   `NIGHTSCOPE_RUNTIME_DIR`, when explicitly set, takes precedence over both.
3. SQLite sidecars normally disappear after a clean close. If `nightscope.db-wal`
   or `nightscope.db-shm` remain, keep them with that exact database copy. Never
   pair a restored database with sidecars from another database/session.

Restore with NightScope closed into a **clean runtime directory**, using the
same filenames/layout. For rollback, copy the chosen `.db.backup` as
`nightscope.db` together with the retained image directory. Put preferences in
the configuration directory. Keep the source backup intact until the restored
app has been verified. On startup the schema is checked and file URLs are
rebuilt for the new location; test a personal image, its catalogue alias and a
Solar System target. Provider secrets are stored in the OS credential vault and
are not exported by this file copy; reconfigure them on another computer.

Legacy runtime relocation copies managed images before installing its SQLite
snapshot. It verifies full-image filename hashes, rejects redirected paths and
conflicting destination bytes, bounds reads and installs each file atomically.
An interrupted copy can leave unreferenced files for safe retry, not an installed
DB pointing at partial files. It does not merge images from an unrelated legacy
store into an already existing active DB. Corrupt legacy DB bytes are retained
for the established quarantine/recovery flow; locking and disk errors are not
silently converted into raw DB copies.

## Updates, Packaging And Verification

Seed synchronization does not touch the personal table. The schema-26 upgrade
adds it without rebuilding a healthy DB or changing other user data. Keep
`user_images` together with the runtime database when moving data. Backing up
only SQLite cannot recover external photographs on another machine.

The PyInstaller Qt allowlist includes `QtQuick.Dialogs` and its fallback
`Qt.labs.folderlistmodel` dependency; this reuses the existing LGPL-compatible
Qt runtime and does not add Pillow to application dependencies. `user_images`
is ignored by Git and forbidden at any depth in release-bundle audits. Audits
also require the Qt Quick Dialogs and folder-list plugins and supporting libraries
on both target platforms. This is a source packaging contract, not proof that a
new Windows/Linux artifact has passed it.

Regression tests in `test_personal_images.py` exercise bounded decoding,
orientation/privacy, storage failures, interrupted previews, aliases, red mode,
seed/bootstrap preservation and portable paths. Real-QML interaction checks
and the complete source gate are recorded in [Testing](TESTING.md).
`test_personal_image_lifecycle.py` adds WAL snapshots, failure/timeout retention,
old-backup restore after replacement/reset, relocation, Home fallback metadata,
and packaging privacy/plugin tests. Native
desktop selection and packaged-plugin loading must also be checked when the
next distribution is actually built.

API references: [QImageReader](https://doc.qt.io/qt-6/qimagereader.html) and
[Qt Quick FileDialog](https://doc.qt.io/qt-6/qml-qtquick-dialogs-filedialog.html).
