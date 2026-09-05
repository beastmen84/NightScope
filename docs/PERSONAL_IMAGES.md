# Personal Object Images

Implemented in source 1.46.12. Backup/restore hardening is the 1.46.13 step in
[the approved roadmap](OBJECT_IMAGERY_ROADMAP.md); no new bundle is implied.

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

## Updates, Packaging And Verification

Seed synchronization does not touch the personal table. The schema-26 upgrade
adds it without rebuilding a healthy DB or changing other user data. Keep
`user_images` together with the runtime database when moving data. Backing up
only SQLite cannot recover external photographs on another machine.

The PyInstaller Qt allowlist includes `QtQuick.Dialogs` and its fallback
`Qt.labs.folderlistmodel` dependency; this reuses the existing LGPL-compatible
Qt runtime and does not add Pillow to application dependencies. `user_images`
is ignored by Git and forbidden in release-bundle audits.

Regression tests in `test_personal_images.py` exercise bounded decoding,
orientation/privacy, storage failures, interrupted previews, aliases, red mode,
seed/bootstrap preservation and portable paths. Real-QML interaction checks
and the complete source gate are recorded in [Testing](TESTING.md). Native
desktop selection and packaged-plugin loading must also be checked when the
next distribution is actually built.

API references: [QImageReader](https://doc.qt.io/qt-6/qimagereader.html) and
[Qt Quick FileDialog](https://doc.qt.io/qt-6/qml-qtquick-dialogs-filedialog.html).
