# Object Imagery Redesign

Approved: 2026-09-05. Baseline source: `1.46.10`, commit `1892652`.

## Product Contract

- Keep the nine NASA/JPL Solar System photographs as body-specific defaults.
- Remove the 219 distributed Messier/Caldwell survey cutouts. All deep-sky
  catalogues use the same type-based illustration policy, without depending
  on catalogue membership, object popularity or editorial completion.
- Label generated artwork as a category illustration, never an observation
  of the selected target. A generic galaxy symbol does not assert that the
  selected galaxy has the illustrated morphology. Unknown types use a neutral
  category rather than an invented astronomical classification.
- Allow one local personal image per physical object, with preview, replacement
  and restoration of its default. Canonical object IDs, not translated names
  or individual catalogue aliases, own personal-image associations.
- Import an app-managed copy, not a fragile reference to the original file.
  Personal images remain local, separate from shipped resources and built-in
  seeds. Read associations on startup; load bounded images when needed.
- Keep Red Night Vision's no-photograph/no-image-loading contract. Image
  management must remain accessible without exposing a bright picture.
- Protect personal files and associations through updates and backup/restore;
  do not silently overwrite originals, clean user directories, or package
  runtime pictures in releases.

## Versioned Steps

1. `1.46.11`: category artwork, shared type resolver, deep-sky asset retirement,
   conservative legacy-record migration, source/UI/documentation checks.
2. `1.46.12`: local personal-image import/preview/replace/reset and immediate
   UI refresh, isolated storage and canonical IDs, validation and persistence.
3. `1.46.13`: backup/restore integration and end-to-end upgrade, packaging,
   language, normal/red and failure-path verification of the complete feature.

Each step needs its own source version, changelog/handoff and local commit
after the complete source gate. No new editorial content is part of this
series. Source validation is not a distribution rebuild or public release;
do not wait for remote GitHub runs. Linux/artifact builds remain separate.

## Step 1 Design

`services/object_imagery.py` owns the deterministic catalogue-type mapping and
metadata-only resolution. It performs no filesystem, Qt or astronomy work.
The application workflow and controller presentation use the same resolver.
Only Solar System records remain in the distributed image seed; type defaults
do not require thousands of database rows.

Known retired rows are identified by object ID, exact distributed path and
known license together. Custom rows are not deleted merely because they have
a Messier/Caldwell ID. The physical file removal applies only to the tracked
source cutouts, not arbitrary runtime folders or a user's portable dist.

The 16 illustration families are galaxy, galaxy system, open cluster,
globular cluster, generic nebula, emission nebula, reflection nebula, dark
nebula, planetary nebula, nebula with cluster, supernova remnant, asterism,
Milky Way star cloud, star, optical double and unclassified object. The
taxonomy is illustrative and separate from scientific classification/scoring.

## Step 1 Status

All 16 final illustrations are installed in
`astro_viewer/resources/images/categories/`. The user explicitly approved
Python resizing/compression: the 512-pixel RGB JPEG family totals 614,168 bytes,
with no cropping or generative alteration during normalization. The 219 old
tracked photographs (15,235,688 bytes) are removed and recoverable from Git
history; all nine Solar System photos retain their previous bytes. The asset
saving is 14,621,520 bytes, not a measured compressed-release size.

Prompt provenance and original/final SHA-256 records are in
`docs/IMAGE_GENERATION_PROMPTS.md` and `docs/IMAGE_ASSET_MANIFEST.json`.
The original PNG copies remain in ignored
`build/object-imagery-1.46.11/originals/`; they are not shipped.

Real-QML checks cover 24 detail scenes across IT/EN/ES, catalogue/observing
branches, normal/red/restored modes, with correct labels and no hidden-branch
image loading. A disposable upgrade of the complete historical 231-row image
seed preserves a custom image, custom editorial text and all 33 other tables.
All 48 normal/red/restored Home thumbnail states also pass. The complete
security/coverage gate passes with 1,407 tests and 10 subtests, 86% coverage,
and all three source smoke checks; see `docs/TESTING.md`. Step 1 is complete
as source version `1.46.11`, with its own local commit.
Personal-image import and backup/restore are not implemented in this step.
The current Windows dist remains the unchanged 1.46.10 bundle from `ae34df5`.

## Step 2 Status

Source 1.46.12 completes local import/preview/replace/reset in both detail
branches, including Solar System targets. Schema 27 owns canonical associations;
immutable normalized JPEGs/thumbnails stay beside the runtime DB, with no source
path dependency or automatic image deletion. Details, privacy limits, red mode
and failure semantics are in [Personal images](PERSONAL_IMAGES.md).

The complete security/coverage source gate passes (1,429 tests, 10 subtests,
86% coverage), plus 2,088 compiled strings per language, 35-file QML lint,
36 real-QML scenes repeated through the file picker, and six red pixel audits.
This step has its own local commit. Step 3 still owns backup/restore hardening
and final integration checks; no dist has been rebuilt.
