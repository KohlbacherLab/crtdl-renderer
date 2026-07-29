# Example queries

`demo_hypertonie_diabetes.json` was written for this project and is covered by the
repository's licence. It is a realistic showcase rather than a minimal case: adults with
hypertension **and** type-2 diabetes, exercising ICD-10-GM, ATC and LOINC codes, a quantity
comparator, a concept attribute filter, time restrictions, an exclusion block with a
two-criterion AND group, consent, and linked attribute groups.

```bash
crtdl-render examples/demo_hypertonie_diabetes.json -f all -o out/
```

Real-world queries from the MII specifications, TORCH and cctb live in
[`upstream/`](upstream/) and are redistributed under Apache-2.0 with attribution.
