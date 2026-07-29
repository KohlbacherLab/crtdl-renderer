# German display names

Codes render as `Deutscher Name (Code, System Version)` — for example
`Essentielle (primäre) Hypertonie (I10, ICD-10-GM 2024)`.

The version belongs in the label: ICD-10-GM and OPS codes are reused with different meanings
across annual releases, so `I10, ICD-10-GM 2024` and `I10, ICD-10-GM 2019` are not
interchangeable claims.

## Resolution order

1. **Bulk cache** supplied with `--cache` — normally the imported FDPG ontology.
2. **Packaged curated cache** (`crtdl_renderer/terminology_de.json`) — small, hand-checked,
   wins over the bulk import on conflict.
3. **The `display` embedded in the export** — an empty string counts as missing.
4. **The bare code.**
5. Optionally `--online`: a FHIR `CodeSystem/$lookup` with `displayLanguage=de-DE`. Results are
   written back to the file given with `--cache`; without `--cache` they are held in memory for
   the run only. The packaged curated cache is never modified.

Every code whose display did not come from a verified German source, and whose system is not
natively German, is listed in a footnote at the end of the document. The renderer never
invents a translation — an unverified label is shown as-is and flagged.

## Importing the FDPG ontology

The authoritative source is the ontology the portal itself uses. No authentication, ~120 MB:

```bash
curl -L -o elastic.zip \
  https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/v4.2.2/elastic.zip
python -m crtdl_renderer.ontology elastic.zip -o ontology_de.json
```

About 639,000 entries, ~53 MB. Pass it with `--cache ontology_de.json`.

### The rule that matters

**German is `display.de || display.original`, never `de` alone.**

The generator only translates three systems — SNOMED CT, LOINC and Orphanet — because the
others are already German. BfArM systems carry their German name in `display.original` and
leave `de` an **empty string**:

```json
{"terminology": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "termcode": "E11.9",
 "display": {"original": "Diabetes mellitus, Typ 2: Ohne Komplikationen", "en": "", "de": ""}}
```

Reading only `de` would silently drop ICD-10-GM, OPS, ATC and Alpha-ID — precisely the German
code systems. This is the same rule the portal's own `Display.translate()` applies: match the
language by primary subtag, treat an empty string as missing, fall back to `original`.

Measured coverage in v4.2.2: SNOMED CT 182,226 of 428,713 entries have a non-empty `de`;
LOINC 17,575 of 59,471; Orphanet 11,239 of 11,239; every BfArM system 0 — all German in
`original`.

## Cache keys

`system|code|version`, with `system|code` as the version-less fallback. The importer writes a
versioned key only when that version's name actually differs, which roughly halves the file.

System URIs are canonicalised before lookup: `https` → `http`, trailing slashes stripped, and
`…/$lookup?system=X&code=Y` wrappers unwrapped, because real exports put whole `$lookup` URLs
in the `system` field. Cache keys are canonicalised on load too, so a file written with
`https://` still matches.

## Terminology servers — what actually works

| Server | Reality |
|---|---|
| MII Ontoserver (`ontoserver.mii-termserv.de`) | requires a mutual-TLS client certificate |
| BfArM (`terminologien.bfarm.de`) | a FHIR *package registry*, no `$lookup`; packages need a token after accepting download conditions |
| `tx.fhir.org/r4` | public; German LOINC works via `displayLanguage=de-DE`; has no ICD-10-GM, OPS, ATC, and no German SNOMED edition |

Hence the ontology import rather than live lookup. `--online` targets `tx.fhir.org` and is a
supplement, not a substitute.

## Contexts

`context.display` in an export is sometimes the English code while the portal shows German —
`Procedure` → „Prozedur", `Specimen` → „Bioprobe". The curated seed corrects the ones that
differ, taken from the `context` table in the ontology's `backend.zip`.

## Attribution

The curated seed contains short official designations from ICD-10-GM, OPS and ATC (BfArM),
LOINC (Regenstrief Institute), SNOMED CT (SNOMED International), the MII Broad Consent value
set, KBV's Diagnosesicherheit code system and HL7 FHIR's administrative-gender. They are
included as interoperability data; the code systems remain under their own terms. See
[NOTICE](../NOTICE).
