# The CRTDL / CCDL format

## What the two are

**CRTDL** (Clinical Resource Transfer Definition Language) is the container: a cohort
definition plus a data-extraction definition. **CCDL** (Clinical Cohort Definition Language,
formerly "Structured Query") is the cohort part — the inclusion and exclusion criteria this
renderer's main output describes.

- CRTDL: <https://github.com/medizininformatik-initiative/clinical-resource-transfer-definition-language>
- CCDL: <https://github.com/medizininformatik-initiative/clinical-cohort-definition-language>

```json
{
  "version": "<uri>",
  "display": "<name>",
  "cohortDefinition": { "version": "...", "inclusionCriteria": [...], "exclusionCriteria": [...] },
  "dataExtraction": { "attributeGroups": [...] }
}
```

## Boolean semantics — and the inversion

Straight from the CCDL schema's own descriptions:

| Field | Outer array | Inner array | Normal form |
|---|---|---|---|
| `inclusionCriteria` | **AND** | **OR** | CNF |
| `exclusionCriteria` | **OR** | **AND** | DNF |

The cohort is `inclusion AND NOT exclusion`.

**The nesting inverts between the two sections.** `[[A],[B,C]]` means `A AND (B OR C)` under
inclusion and `A OR (B AND C)` under exclusion. The same JSON shape means opposite things
depending on which key it sits under, and the FDPG interface does not draw the difference —
its operator switches are fixed by column, not chosen. This is the single most dangerous
property of the format for a human reader, so every rendered section states its own rule in
words rather than relying on the reader to remember which side they are on.

Implicit operators that also have to be rendered:

| Element | Join |
|---|---|
| multiple `termCodes` on one criterion | synonyms for one concept, not alternatives |
| `valueFilter.selectedConcepts` | OR |
| multiple `attributeFilters` | AND |
| `attributeFilter` of type `reference`, its `criteria[]` | OR — see below |
| `filter` codes in an attribute group | OR |

### The reference-filter join

The specification does not say how the criteria inside a `reference` attribute filter combine.
It is **OR**: a match on any one referenced criterion satisfies the filter. This follows the
reference translator (`cctb`), which unions them.

### Time restrictions are intersections

`timeRestriction` gives `afterDate` and/or `beforeDate`. The schema states that an
*intersection* of the criterion's interval with this one suffices — not containment. Rendered
as „Zeitraum (Überschneidung)" so the weaker condition is not overstated.

## Criterion shape

```json
{
  "context":   { "code": "...", "system": "fdpg.mii.cds", "version": "...", "display": "..." },
  "termCodes": [ { "code": "...", "system": "...", "version": "...", "display": "..." } ],
  "valueFilter":      { "type": "concept | quantity-comparator | quantity-range", ... },
  "attributeFilters": [ { "type": "... | reference", "attributeCode": {...}, ... } ],
  "timeRestriction":  { "afterDate": "...", "beforeDate": "..." }
}
```

Comparators: `gt` >, `lt` <, `ge` ≥, `le` ≤, `eq` =, `ne` ≠.

A criterion is identified by the **pair** (context, termCode), not the term code alone — the
same code appears in several MII KDS modules with different meanings.

## Deviations tolerated by the parser

Real files disagree with the published schema. All of these parse:

| Deviation | Where it occurs |
|---|---|
| `dataExtraction` nested inside `cohortDefinition` | the CRTDL spec's own examples, and TORCH's docs |
| bare CCDL with `inclusionCriteria` at top level | cctb's corpus |
| legacy system URI `…/dimdi/icd-10-gm` | `ccdl-all-properties.json` |
| a whole `$lookup?system=…` URL in the `system` field | `ccdl-all-properties.json` |
| empty `system`, empty `display` | `ccdl-all-properties.json` |
| malformed dates such as `"2021-5"` | `CRTDL_Diagnosis_linked_with_Encounter.json` |
| unknown `valueFilter.type` | surfaced in the output as „⚠ unbekannter Filtertyp", never dropped |
| `filter.type` absent or unexpected | classified by which fields are present |

The CRTDL schema also `$ref`s `#/definitions/cohortDefinition` while the CCDL schema uses
`$defs` at its root, so the published pair cannot resolve as-is. Parsing is therefore lenient
about *presentation* — missing versions, odd system strings, unexpected displays — but strict
about anything that would change what the cohort means.

### Rejected input

A file is refused, with the offending path named, when:

| Condition | Why |
|---|---|
| no `inclusionCriteria` anywhere, or an empty one | the CCDL requires at least one condition |
| an empty inner array | an empty disjunction is FALSE in the inclusion CNF and an empty conjunction is TRUE in the exclusion DNF; dropping it would present a different cohort |
| a `reference` filter inside a `reference` filter | forbidden by the CCDL, and not representable in every output format |
| a `reference` filter with no `criteria` | it would constrain nothing |
| a `timeRestriction` with neither `afterDate` nor `beforeDate` | invalid per the schema, and it would silently vanish from the document |
| a criterion without `termCodes` | there is no concept to render |
| wrong types — root not an object, criteria not lists of lists, a criterion that is not an object, `termCodes`/`valueFilter`/`attributeFilters` of the wrong shape | the structure cannot be interpreted; guessing would be worse than refusing |

Anything the renderer cannot interpret but *can* still show — an unknown `valueFilter.type`, an
attribute-group filter of unrecognised shape, a unit whose display contradicts its code, a
malformed date — is rendered with a visible warning rather than dropped.

## Consent

Consent is not a separate field. It arrives as ordinary inclusion criteria whose
`context.code` is `Einwilligung`, carrying MII Broad Consent OIDs under
`urn:oid:2.16.840.1.113883.3.1937.777.24.5.3`. TORCH skips consent enforcement entirely when
none are present. The renderer marks such criteria so a reader can tell a consent gate from a
clinical criterion.

## Data extraction

`attributeGroups` name an MII KDS profile via `groupReference`, list `attributes` with a
`mustHave` flag, and may carry `token` and `date` filters. `mustHave` is severe: a patient
lacking a resource with all must-have attributes populated is dropped from the extraction
entirely, which the rendered document states rather than leaving to the reader.
`includeReferenceOnly` marks a group that is only materialised when reached by reference.
