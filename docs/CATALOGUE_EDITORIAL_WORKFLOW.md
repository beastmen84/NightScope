# Catalogue Editorial Workflow

This document is the acceptance contract for adding descriptions, observing
guidance, and source-backed curiosities to the catalogue in Italian, English,
and Spanish. It defines the next work stream; source `1.45.7` does not add the
missing editorial entries.

## Baseline And Scope

NightScope currently has complete editorial content for 228 curated objects:

- 9 Solar System targets;
- 110 Messier targets;
- 109 Caldwell targets.

OpenNGC contributes 7,571 physical NGC targets. Two hundred five resolve to
already curated physical objects, while 7,366 are NGC-only targets. Those
NGC-only objects intentionally use a localized `Work in progress` fallback.
They are the main scope of the future content stream.

Catalogue aliases do not create duplicate editorial work. Content belongs to
the stable physical `object_id`; Messier, Caldwell, NGC, and historical aliases
all render the same physical object's content.

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

## Batch Strategy

Work in bounded batches, each with its own source version and commit. A batch
should be small enough for every source and all three languages to be reviewed;
roughly 50 to 100 objects is a sensible initial ceiling, adjusted downward for
poorly documented targets.

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

## Automated Acceptance Gates

Extend tests as coverage grows. At minimum, every accepted batch must prove:

- object IDs exist and resolve to one physical catalogue target;
- there are no duplicate description or curiosity rows;
- all required fields are non-empty in IT, EN, and ES;
- the three languages contain no `Work in progress` fallback for completed IDs;
- source labels are present, URLs are HTTPS, and verified links pass the source
  audit at review time;
- curiosity texts are unique and not near-duplicate templates;
- descriptions and observing notes are not identical across objects;
- object names, aliases, types, and constellations agree with catalogue data;
- Solar safety wording remains exact wherever the Sun is involved;
- editorial content never changes recommendation eligibility, NSOM scores,
  optical selection, visibility, or planner order;
- bootstrap updates built-in rows while preserving user-managed content;
- translation catalogues remain complete and QML detail rendering remains
  unclipped for representative long strings.

Similarity checks are screening tools, not proof of quality. Passing a token
threshold does not make templated prose acceptable.

## Review Artifacts

For each version, retain a concise batch record containing:

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

The catalogue-wide project is complete only when the NGC-only fallback count is
zero in all three languages and a final cross-catalogue, source, translation,
and visual audit passes. Distribution artifacts remain a separate explicitly
requested release activity.
