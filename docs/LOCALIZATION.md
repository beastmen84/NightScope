# NightScope Localization

NightScope discovers languages from files. The runtime, sidebar and packaging do
not contain a hard-coded list of supported language codes.

The source tree currently ships complete packs for Italian (`it`), English
(`en`), and Spanish for Spain (`es`).

Italian is the canonical UI source and fallback language. Historical structured
CSV data can legitimately mix Italian and English between fields; the content
generator records the actual source language per field instead of assigning one
language to an entire section. A runtime language pack is made of:

- `<code>.json`: language metadata, locale formats and structured editorial
  content;
- `<code>.ts`: Qt Linguist messages extracted from QML and Python;
- `<code>.qm`: compiled runtime catalogue generated from the TS file.

PyInstaller packages the complete `astro_viewer/translations` directory. Adding
a language does not require changes to QML, Python, the sidebar or the spec file.

## Runtime Contract

`TranslationManager` discovers every JSON file with `schema_version: 1`. Each
file declares:

```json
{
  "schema_version": 1,
  "language": {
    "code": "fr",
    "label": "Francais",
    "locale": "fr_FR",
    "source": false
  },
  "formats": {
    "date": "dd/MM/yyyy",
    "date_time": "dd/MM/yyyy HH:mm"
  },
  "content": {}
}
```

`label` should be the language name written in that language. An optional
`translation_code` can be added when the external translation provider expects
a code different from the runtime code.

Exactly one pack must set `source: true`, currently `it`. The selected code is
stored in `user_preferences.json`. Switching language reloads the Qt translator,
locale and structured content, then emits presentation-only signals. Astronomy,
weather, equipment, scoring and NSOM are not recomputed.

The normal GUI entry point installs that saved language before creating its
startup splash. A genuinely new runtime, with no database or preferences yet,
uses fixed English onboarding copy for the first-use setup. Every later launch
uses the selected Italian, English, or Spanish pack for the routine database,
service, and interface progress. These routine strings follow the same reviewed
Qt catalogue workflow as other Python presentation copy.

Python presentation strings remain lazy through `tr()`, `content_text()` and the
locale-aware date/number helpers. Services consume canonical values; rendering
happens only at the Qt/QML boundary. User-entered names, notes and observation
log text are never translated.

Database-backed Messier and Caldwell catalogue rows use the
`catalogue_objects` structured-content section. Synthetic Solar System rows
instead retain their lazy `tr()` names and `objects` descriptions through the
catalogue read-model; rebinding them to `catalogue_objects` would discard the
English and Spanish presentation because that section has no synthetic rows.

## Add A Language

To add French without changing application code:

1. Add `astro_viewer/translations/fr.json` with the metadata above.
2. Populate structured seed content:

   ```powershell
   .\.venv\Scripts\python.exe tools\update_content_translations.py fr
   ```

3. Extract all QML and Python messages. This creates or updates `fr.ts`:

   ```powershell
   .\tools\update_translations.ps1 -UpdateOnly
   ```

4. Populate unfinished TS messages, then review the generated language:

   ```powershell
   .\.venv\Scripts\python.exe tools\update_ts_translations.py fr
   ```

5. Compile and validate every discovered pack:

   ```powershell
   .\tools\update_translations.ps1 -CompileOnly
   .\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py
   ```

The files that belong in source control are `fr.json`, `fr.ts` and the generated
`fr.qm`. The JSON and TS files can also be translated manually; compilation
rejects empty, unfinished or placeholder-incompatible entries.

The update tools preserve existing reviewed translations. Use `--refresh` only
when intentionally replacing all generated text, because it can overwrite
editorial corrections.

Reviewed TS corrections can be stored in
`tools/translation_reviews/<code>.json`. The optional `translations` object
applies a correction to a source message globally; `contexts` applies it only
inside a named Qt context. `update_ts_translations.py` applies this overlay
after generation and fails on malformed placeholders or stale review entries,
so editorial terminology remains reproducible instead of depending on manual
edits to generated XML.

The current tree contains reviewed overlays for both `en` and `es`. The English
overlay protects provider-account instructions and reviewed UI terminology;
the broader Spanish overlay owns the complete Spanish UI review. Reviewed
English structured-content corrections live in deterministic overrides and
targeted replacements in `tools/update_content_translations.py`. Tests require
both TS overlays and the structured-content curation to remain applicable and
idempotent after catalogue regeneration.

The Italian and English object catalogues received a full editorial pass in
source version `1.34.3`. Regression tests protect the corrected object
classifications, reflection-nebula filter guidance, Italian angular decimal
formatting, and known English calques. Similar observing instructions are not
rewritten solely to make them look unique when the shared guidance is
technically appropriate.

### Technical Terminology

Technical UI copy is translated by domain meaning, not word by word. Product
names, standards and established loanwords remain unchanged when that is how
camera and astronomy documentation identifies them. Persisted codes such as
`ROLLING`, `GLOBAL`, `COLOR` and `MONO` remain language-neutral; only their
presentation labels are localized.

The Cameras glossary currently protects these representative terms:

| Concept | Italian source | English | Spanish (`es_ES`) |
| --- | --- | --- | --- |
| Sensor identifier | Modello sensore | Sensor model | Modelo del sensor |
| Sensor construction | Tecnologia sensore | Sensor technology | Tecnología del sensor |
| Color/mono selection | Modalità colore | Color mode | Modo de color |
| Pixel spacing | Passo pixel | Pixel size | Tamaño de píxel |
| Image dimensions | Risoluzione orizzontale/verticale | Horizontal/vertical resolution | Resolución horizontal/vertical |
| Full-resolution frame rate | FPS a piena risoluzione | Max FPS at full resolution | FPS máx. a resolución completa |
| Cooling capacity | ΔT massimo sotto ambiente | Max ΔT below ambient | ΔT máx. por debajo del ambiente |
| Sensor readout | Rolling shutter / Global shutter | Rolling shutter / Global shutter | Rolling shutter / Obturador global |
| Camera interface | Baionetta | Lens mount | Montura del objetivo |
| Long exposure mode | Modalità Bulb | Bulb mode | Modo Bulb |

Exact EN/ES translations and known bad literal renderings are regression-tested.
New equipment fields must extend both translation-review overlays and the
technical terminology test before their generated catalogues are committed.

### Machine-Translation Provider

The maintenance scripts use `tools/translation_provider.py`, a small
timeout-bounded adapter around the public Google Translate mobile HTML response.
It uses the runtime `requests` dependency, needs no NightScope or provider
account, and is not imported by the application. It replaced the
`deep-translator` developer dependency after a dependency audit flagged
`PYSEC-2022-252`.

This endpoint is a best-effort maintenance aid, not a stable contracted API.
Network errors, response-shape changes and input-size violations fail explicitly
instead of producing an empty translation. Mocked tests own deterministic
coverage; a live probe is optional. Every generated translation must still be
reviewed for astronomy terminology, placeholders, tone and UI fit before it is
committed.

## Add Translatable Text

- QML: wrap the complete sentence in `qsTr()`. Use `%1`, `%2`, and `.arg()`;
  do not concatenate translated sentence fragments.
- Python: use a literal `tr("Testo italiano", value=value)`. The extraction tool
  rejects dynamic source strings.
- Seed/editorial content: keep the canonical value in its CSV and expose the
  field through `source_content()` in `tools/update_content_translations.py`;
  declare its real language through `source_language()`. Never infer the source
  language from the section or from the requested output language.
- Domain codes and persisted values remain stable and untranslated. Add a
  presentation label instead of branching on translated text.
- Derived labels, such as catalogue designation plus object name, are composed
  at presentation time and are not duplicated in language JSON files.

## Validation

The localization tests verify language discovery, symmetric complete TS
catalogues, compiled QM assets, structured seed coverage, placeholder parity,
runtime switching, preference preservation, locale formatting, third-language
discovery, presentation-only refresh and packaging. They also reject raw static
QML text (including labels inside JavaScript objects), translated sentence
concatenation, derived catalogue fields, zero-width spaces and regressions in
reviewed astronomy terminology. Localized filter choices are verified after
rendering so their order follows the displayed language.

Before a release run:

The TS updater remains required even when no messages are unfinished because it
reapplies the reviewed overlays before the catalogues are compiled.

```powershell
.\.venv\Scripts\python.exe tools\update_content_translations.py
.\tools\update_translations.ps1 -UpdateOnly
.\.venv\Scripts\python.exe tools\update_ts_translations.py
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q -n 4 astro_viewer\tests
```
