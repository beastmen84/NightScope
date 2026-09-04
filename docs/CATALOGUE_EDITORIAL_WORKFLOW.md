# Catalogue Editorial Workflow

This document is the acceptance contract for adding descriptions, observing
guidance, and source-backed curiosities to the catalogue in Italian, English,
and Spanish. Source `1.46.0` established the pipeline and acceptance gates;
sources `1.46.1` and `1.46.2` apply that contract to 75 NGC-only galaxies,
while sources `1.46.3` through `1.46.6` apply the same standard to field-scoped
baseline remediation.

## Baseline And Scope

NightScope's immutable pre-programme identity baseline contains 228 objects:

- 9 Solar System targets;
- 110 Messier targets;
- 109 Caldwell targets.

OpenNGC contributes 7,571 physical NGC targets. Two hundred five resolve to
already curated physical objects, while 7,366 are NGC-only targets. Sources
through `1.46.2` complete 75 of those targets, bringing editorial coverage to
303 physical objects and leaving 7,291 NGC-only targets on the localized
`Work in progress` fallback.

Source `1.46.3` does not alter those coverage counts. It replaces one generic
17-object galaxy observing-note family in the historical baseline and rewrites
four descriptions from two duplicated families, with independent IT/EN/ES
review and direct NASA evidence.

Source `1.46.4` likewise leaves coverage unchanged. It replaces the remaining
formulaic observing guidance for 48 baseline open clusters and rewrites ten
descriptions from four duplicated families. Its object-specific advice covers
field scale, stellar patterns, colour contrast, companions, extinction and the
few cases where a filter belongs to adjacent nebulosity rather than the cluster.

Source `1.46.5` replaces all remaining formulaic observing guidance for 41
baseline globular clusters and rewrites six descriptions from three duplicated
families. The notes distinguish compact and loose concentration, stellar
resolution, extinction, crowded fields, horizon constraints, useful
comparisons, and the choice between framing the halo and examining the core.

Source `1.46.6` replaces all remaining formulaic observing guidance for 20
baseline emission, reflection, and planetary nebulae. The notes distinguish
field scale, surface brightness, mixed reflection/emission components,
filter-versus-unfiltered comparisons, compact shells, and realistic visual
limits without reopening their already distinct descriptions.

Catalogue aliases do not create duplicate editorial work. Content belongs to
the stable physical `object_id`; Messier, Caldwell, NGC, and historical aliases
all render the same physical object's content.

### Baseline identity is not a prose-quality waiver

The baseline hash freezes the 228 stable object identities; it does not declare
every historical sentence compliant with the stricter `1.46.x` editorial
standard, and it does not make that prose immutable.

Before accepting `1.46.2`, all 50 entries added by `1.46.1` were reread in
Italian, English, and Spanish. Their descriptions, observing guidance, and
curiosities remain object-specific and useful. A separate retrospective screen
of the older Solar System/Messier/Caldwell baseline exposed genuine formulaic
debt: 11 connected description families affect 24 objects and 23 observing-note
families affect 177 objects after catalogue IDs, parenthetical aliases, and
measurements are normalized. Historical curiosity texts remain distinct.

After the accepted `1.46.6` remediation, the remaining measured debt is 2
description families affecting 4 objects and 5 observing-note families
affecting 51 objects. These are backlog figures, not a quality waiver for the
remaining prose.

The deterministic audit reports those figures as a warning, not as acceptance
of the repeated prose and not as a failure of later NGC batches. Remediation
must use bounded, reviewed versions with the same three-language and source
requirements; bulk synonym replacement is not an acceptable fix.

## Required Fields

Every completed object needs an Italian canonical record with:

- `short_description`;
- `observing_notes`;
- `best_seen`;
- difficulty guidance for naked eye, binoculars, small, medium, and large
  apertures where applicable;
- one distinct `curiosity_text`;
- visible `source_label`;
- direct HTTPS `source_url`;
- `verified = 1` only after factual and link review.

English and Spanish structured-content overlays must cover every translatable
field. Empty text, source-language leakage, placeholder text, and raw machine
translation are incomplete work.

For the `1.46.x` programme, `object_descriptions_seed.csv` and
`object_curiosities_seed.csv` are the unambiguous Italian editorial sources.
The `objects` sections of `translations/en.json` and `translations/es.json` are
the reviewed overlays consumed at runtime. The historic catalogue seed still
contains English technical values and `Work in progress` placeholders; do not
duplicate new prose into its `descrizione` column. Presentation replaces that
placeholder with the reviewed `short_description` and replaces placeholder
notes with `observing_notes` as soon as a complete editorial record exists.

## Editorial Standard

### Description

A description should identify what the object physically is and the few facts
that distinguish it: morphology or object class, constellation, relevant
structure, distance/scale only when sourced, and notable relationships. It must
not be a rearranged list of database columns.

### Observing guidance

Observing notes should be practical and conservative. They may use verified
apparent size, magnitude, surface-brightness implications, declination, and
object class, but must distinguish measured data from advice. Avoid promising
visibility from magnitude alone and avoid recommending narrowband filters for
continuum galaxies, clusters, or reflection nebulae without a specific reason.

### Curiosity or fun fact

A curiosity must be object-specific, meaningful, and independently supported.
Acceptable examples include discovery history, a named physical feature, an
unusual stellar population, a well-established interaction, or a scientifically
important observation. Catalogue membership, generic object-class facts, and
templated statements are not fun facts.

If no reliable object-specific fact can be found, leave the entry incomplete.
Never invent one to satisfy a coverage counter.

### Sources

Use the most direct authoritative or scholarly source available. OpenNGC is a
strong identity/measurement source but is not automatically sufficient for a
narrative or historical claim. Prefer observatory, mission, professional
catalogue, peer-reviewed, or institutional pages for curiosities. A secondary
reference is acceptable when the claim is stable, clearly supported, and no
better primary page is available.

Link to the page supporting the actual claim, not a search result or generic
homepage. Record access/review evidence in the batch notes. Multiple claims in
one fact must all be supported by the cited source or be reduced to the
supported claim.

## Three-Language Workflow

Italian remains the canonical structured-content source. For each reviewed
batch:

1. Research and write the Italian entry from the source evidence.
2. Perform a factual review against identity, type, constellation, and source.
3. Produce English and Spanish translations from the reviewed meaning.
4. Edit each language for native astronomical terminology, grammar, units,
   punctuation, and natural phrasing.
5. Compare all three side by side for omitted qualifiers, inverted meaning,
   false precision, and name/alias drift.
6. Run language and structured-content tests before accepting the batch.

Automatic translation may assist a draft but is never the acceptance step.
Names, catalogue identifiers, object classes, filter terms, angular units, and
historical proper nouns require explicit review.

`tools/update_content_translations.py` does not generate or refresh object prose
unless `--draft-editorial` is supplied explicitly. That option only prepares a
working draft; it never records a review or makes a batch acceptable. Existing
reviewed object overlays remain untouched by an ordinary `--refresh` run.

## Batch Strategy

The editorial programme uses the `1.46.x` source series. Version `1.46.0` owns
only the preparatory pipeline. Content starts at `1.46.1` and advances one patch
version per accepted batch. This can legitimately result in many patch versions;
public Windows or Linux bundles may group several source batches and remain a
separate release decision.

Accepted batch ledger:

| Source | Kind | Scope | Cumulative NGC-only | Baseline remediated | Remaining NGC-only |
| --- | --- | --- | ---: | ---: | ---: |
| `1.46.1` | NGC enrichment | 50 varied, well-documented galaxies | 50 | 0 | 7,316 |
| `1.46.2` | NGC enrichment | 25 additional distinctive, strongly sourced galaxies | 75 | 0 | 7,291 |
| `1.46.3` | Baseline remediation | One 17-galaxy observing-note family; four descriptions | 75 | 17 | 7,291 |
| `1.46.4` | Baseline remediation | Remaining formulaic open-cluster notes; ten descriptions | 75 | 65 | 7,291 |
| `1.46.5` | Baseline remediation | Remaining formulaic globular-cluster notes; six descriptions | 75 | 106 | 7,291 |
| `1.46.6` | Baseline remediation | Remaining formulaic nebula and planetary-nebula notes | 75 | 126 | 7,291 |

The next editorial source patch is `1.46.7`; it must define and review its own
bounded manifest rather than extending either accepted set.

Work in bounded batches, each with its own source version and commit. A batch
must be small enough for every source and all three languages to be reviewed.
One hundred objects is a hard ceiling, not a target or minimum; 25 or fewer is
appropriate whenever research depth or language review would otherwise suffer.

Prefer coherent batches such as one object class within a constellation range
or one source collection. Do not batch solely by CSV row count when that mixes
unrelated research contexts.

Each batch must include:

- an exact manifest of physical object IDs and displayed designations;
- source URLs and verification status;
- the Italian seed changes;
- complete English and Spanish overlays;
- automated content tests;
- a short manual review sample covering ordinary, faint, unusually large,
  multi-designation, and southern/northern targets;
- version, changelog, and handoff updates;
- no `dist` regeneration.

Copy `astro_viewer/data/editorial_batches/_batch_template.json` to the matching
`batch_1_46_N.json` file at the start of a batch. `draft` records may plan IDs
and sources, but Italian seeds and EN/ES overlays land only with an `accepted`
manifest. The manifest records exact designations, claim-level evidence,
per-object factual and language review states, visual samples, deferrals, and
any justified similarity waivers.

Use `batch_kind: ngc_enrichment` for new NGC-only content. Use
`batch_kind: baseline_remediation` for corrections to the immutable baseline
and add an exact `fields` list to every object. In remediation batches, source
coverage and similarity screening apply only to those declared fields;
untouched content is not represented as newly reviewed. An accepted enrichment
ID may occur only once, whereas a later remediation may revisit a baseline ID
when a distinct correction is justified.

## Automated Acceptance Gates

Extend tests as coverage grows. At minimum, every accepted batch must prove:

- object IDs exist and resolve to one physical catalogue target;
- there are no duplicate description or curiosity rows;
- all required fields are non-empty in IT, EN, and ES;
- the three languages contain no `Work in progress` fallback for completed IDs;
- source labels are present, URLs are HTTPS, and verified links pass the source
  audit at review time;
- curiosity texts are unique and not near-duplicate templates;
- descriptions and observing notes are neither identical nor near-identical
  parameterized templates across objects;
- object names, aliases, types, and constellations agree with catalogue data;
- Solar safety wording remains exact wherever the Sun is involved;
- editorial content never changes recommendation eligibility, NSOM scores,
  optical selection, visibility, or planner order;
- bootstrap updates built-in rows while preserving user-managed content;
- translation catalogues remain complete and QML detail rendering remains
  unclipped for representative long strings.

The network-free repository audit is part of the standard source gate:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py
```

Before accepting one batch, run its near-duplicate screen and its bounded live
source check:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py `
  --batch astro_viewer\data\editorial_batches\batch_1_46_N.json
.\.venv\Scripts\python.exe astro_viewer\tools\audit_curiosity_sources.py `
  --batch astro_viewer\data\editorial_batches\batch_1_46_N.json
```

Render the manifest's representative Object Detail samples in all three
languages and both visual modes into a temporary directory outside the
repository:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\render_editorial_samples.py `
  --batch astro_viewer\data\editorial_batches\batch_1_46_N.json `
  --output-dir "$env:TEMP\NightScope-editorial-review"
```

The renderer uses an isolated runtime automatically. Review every generated
contact sheet for complete text, language selection, layout integrity, visible
source attribution, and monochromatic Red Night Vision before changing the
manifest's visual states to `accepted`.

When `observing_notes` changes, also render the top of the catalogue detail,
where that field appears, rather than reviewing only the lower description and
curiosity cards:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\render_editorial_samples.py `
  --batch astro_viewer\data\editorial_batches\batch_1_46_N.json `
  --output-dir "$env:TEMP\NightScope-editorial-review-top" `
  --scroll-y 0
```

Similarity checks are screening tools, not proof of quality. Passing a token
threshold does not make templated prose acceptable. The audit also reports
legacy baseline template families as non-failing debt so they remain visible
until deliberately rewritten.

## Review Artifacts

For each version, retain the machine-readable manifest plus a concise review
record containing:

- object count and ID range/list;
- source mix and failed/unavailable sources;
- automated test counts;
- language review status;
- representative Object Detail renders in normal and Red Night Vision modes;
- any entries deliberately deferred and why.

Do not store copied articles, large quotations, credentials, cookies, or
personal data. Keep only NightScope-authored prose, concise provenance, and
links.

## Definition Of Done

An object is complete only when its Italian record, English overlay, Spanish
overlay, observing guidance, distinct source-backed curiosity, provenance, and
tests are all complete. A batch is complete only when every object in its
manifest meets that definition and the full source gate passes.

A baseline-remediation batch is complete when every declared field has source,
factual, three-language, similarity, and relevant visual acceptance. It does
not reopen or silently re-accept undeclared fields.

The catalogue-wide project is complete only when the NGC-only fallback count is
zero in all three languages and a final cross-catalogue, source, translation,
and visual audit passes. Distribution artifacts remain a separate explicitly
requested release activity.
