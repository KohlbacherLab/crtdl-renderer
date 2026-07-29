# Rendered output

Committed so the result can be judged without installing anything. Regenerate with:

```bash
crtdl-render ../demo_hypertonie_diabetes.json -f all --cache ontology_de.json -o .
crtdl-render ../upstream/mii-ccdl/ccdl-all-properties.json -f all --cache ontology_de.json -o .
```

These were produced with the full FDPG ontology cache (see
[docs/terminology.md](../../docs/terminology.md)), which is why nearly every code carries a
German name. Without `--cache` the renderer falls back to the display embedded in the export
and lists the unresolved codes in a footnote.

| File | What it shows |
|---|---|
| `preview-demo.png`, `preview-nested.png` | page 1 of the two PDFs, for the README |
| `demo_hypertonie_diabetes.*` | a query written for this project: ICD-10-GM, ATC and LOINC codes, a quantity comparator, a concept attribute filter, time restrictions, consent, an exclusion block with a two-criterion AND group, linked attribute groups |
| `ccdl-all-properties.*` | the MII CCDL specification's own example — three nesting levels including a reference condition, plus the awkward inputs described below |

## Why `ccdl-all-properties` is the useful one

It is the only published example exercising exclusion criteria, reference attribute filters,
quantity ranges and time restrictions at once, and it contains several things a renderer has
to survive:

- a whole `$lookup?system=…` URL used as a `system` value
- an empty `system` on one concept
- the legacy `…/dimdi/icd-10-gm` URI
- `display` values identical to the code (`"F00"`), so there is nothing to expand
- `icd-o-3` and `mii.abide` as bare, non-canonical system strings

The rendered footnote lists exactly which of those could not be resolved to a verified German
name, rather than silently showing whatever the file contained.

## Provenance

`ccdl-all-properties.json` comes from the
[MII CCDL specification](https://github.com/medizininformatik-initiative/clinical-cohort-definition-language)
and is redistributed under Apache-2.0; the rendered files here are derived from it. See
[NOTICE](../../NOTICE). `demo_hypertonie_diabetes.json` was written for this project.
