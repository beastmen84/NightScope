# Editorial Batch Records

This directory separates editorial acceptance evidence from runtime content.
Italian remains canonical in `object_descriptions_seed.csv` and
`object_curiosities_seed.csv`; reviewed English and Spanish prose remains in the
structured `translations/en.json` and `translations/es.json` overlays.

`baseline_1_45_22.json` freezes only the identity set of the 228 entries reviewed
before the NGC programme. It deliberately does not freeze wording, so a specific
correction can still be reviewed and committed without rewriting history.

Copy `_batch_template.json` to `batch_1_46_N.json` for each new batch. A manifest
is accepted only when:

- it contains 1 to 100 NGC-only physical `object_id` values and their complete
  designation sets;
- every factual claim has direct HTTPS evidence with an access date;
- factual, Italian, English, and Spanish review states are `accepted`;
- at least five representative objects, or every object in a smaller batch,
  passed normal and Red Night Vision visual review;
- its Italian seeds and EN/ES overlays are complete;
- the static and near-duplicate audits pass.

Draft manifests may be committed for planning, but their IDs must not be added
to canonical seeds until the batch is accepted. Machine translation is only a
draft aid and never changes a review state.

Run the network-free repository audit with:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py
```

For the batch under review, include similarity screening and then verify only
its evidence URLs:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py `
  --batch astro_viewer\data\editorial_batches\batch_1_46_N.json
.\.venv\Scripts\python.exe astro_viewer\tools\audit_curiosity_sources.py `
  --batch astro_viewer\data\editorial_batches\batch_1_46_N.json
```

The URL audit is review-time evidence because remote availability can change;
the network-free audit belongs to every normal source gate.
