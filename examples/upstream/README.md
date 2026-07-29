# Upstream example queries

These files are **not** original to this project. They are redistributed verbatim as test
fixtures under the Apache License 2.0, a copy of which is in
[`LICENSE-Apache-2.0.txt`](LICENSE-Apache-2.0.txt). Attribution is recorded in the
repository's [`NOTICE`](../../NOTICE).

| Directory | Source | Copyright | Changes |
|---|---|---|---|
| `mii-crtdl/` | [clinical-resource-transfer-definition-language](https://github.com/medizininformatik-initiative/clinical-resource-transfer-definition-language) `example-json/` | Medizininformatik-Initiative | none |
| `mii-ccdl/` | [clinical-cohort-definition-language](https://github.com/medizininformatik-initiative/clinical-cohort-definition-language) `example-json/` | Medizininformatik-Initiative | none |
| `torch/` | [torch](https://github.com/medizininformatik-initiative/torch) `src/test/resources/CRTDL/` | Medizininformatik-Initiative | none |
| `cctb/` | [cctb](https://github.com/medizininformatik-initiative/cctb) (formerly `sq2cql`) `cql/src/test/resources/` | Medizininformatik-Initiative | filenames flattened from nested directories; contents unmodified |

Queries written for this project live one level up, in [`examples/`](..), and are covered by
this repository's own licence.

## Why these particular files

They cover the corners a renderer trips over:

- `mii-ccdl/ccdl-all-properties.json` — the only spec file exercising exclusion criteria,
  reference attribute filters, quantity ranges and time restrictions at once
- `cctb/SpecimenSQTwoReferenceCriteria.json` — two criteria inside one reference filter
- `cctb/test-large-query-more-crit-time-rest-1.json` — four inclusion groups, two exclusion
  groups, OPS codes with time restrictions
- `torch/CRTDL_all_fields_consent.json` — 129 attribute groups and MII Broad Consent codes
- `mii-crtdl/CRTDL_observation.json` — `dataExtraction` nested inside `cohortDefinition`,
  which contradicts the published schema and must still parse
