# crtdl-renderer

Turns a **CRTDL** feasibility query — the JSON a researcher exports from the German
[Forschungsdatenportal Gesundheit (FDPG)](https://forschen-fuer-gesundheit.de/) — into a
document a human can actually read: inclusion and exclusion criteria with German display
names, the boolean structure shown as structure, in Markdown, DOCX, PDF or CSV.

The JSON that travels with a data-use application is machine-readable and, by the format's
own admission, carries only a free-text `description` "to transport additional human-readable
information about the query". Use-&-Access-Committee members are asked to judge a cohort
definition they cannot see. This renders it.

```bash
pip install crtdl-renderer[all]
crtdl-render query.json -f pdf -o out/
```

## What the output looks like

```
Einschlusskriterien
Alle 6 Bedingungen E1–E6 müssen erfüllt sein (mit UND verknüpft).

▎E1  [Person] Alter (424144002, SNOMED CT)
    Wert: ≥ 18 Jahre
 U N D
▎E2  Mindestens eines der folgenden 2 Kriterien (E2a–E2b):
   ▎E2a  [Diagnose] Essentielle (primäre) Hypertonie (I10, ICD-10-GM 2024)
        Zeitraum (Überschneidung): von 01.01.2020 bis 31.12.2024
    O D E R
   ▎E2b  [Diagnose] Hypertensive Herzkrankheit ohne … (I11.9, ICD-10-GM 2024)
```

Every condition is a block on a coloured left rail that thins and lightens with depth; the
operator stands *between* blocks rather than in a column. See [docs/layout.md](docs/layout.md)
for why, and what it replaced.

## Usage

```bash
crtdl-render FILE [-f md|docx|pdf|csv|all] [-o OUTDIR]
                  [--layout cards|table] [--cache PATH] [--online]
```

| Option | Effect |
|---|---|
| `-f` | output format; `csv` emits the FDPG's own committee column set |
| `--layout cards` | nested blocks (default) |
| `--layout table` | flat grid, if a reader prefers one |
| `--cache PATH` | additional terminology cache (see below) |
| `--online` | look up missing German names via FHIR `$lookup`, cache the result |

## German display names

Codes render as `Deutscher Name (Code, System Version)`. Resolution is layered: an optional
bulk cache, then the packaged curated cache, then the display embedded in the export, then the
bare code. Codes whose German name could not be verified are listed in a footnote — the
renderer never invents a translation.

For full coverage, import the FDPG ontology once (no authentication, ~120 MB):

```bash
curl -L -o elastic.zip \
  https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/v4.2.2/elastic.zip
python -m crtdl_renderer.ontology elastic.zip -o ontology_de.json
crtdl-render query.json --cache ontology_de.json -f pdf -o out/
```

That yields ~639,000 names — the same labels the FDPG interface shows. The rule that matters:
German is `display.de || display.original`, never `de` alone, because BfArM systems
(ICD-10-GM, OPS, ATC, Alpha-ID) are natively German and leave `de` empty.
See [docs/terminology.md](docs/terminology.md).

## Semantics

`inclusionCriteria` is CNF (outer AND of inner ORs); `exclusionCriteria` is DNF (outer OR of
inner ANDs); the cohort is inclusion **AND NOT** exclusion. The nesting inverts between the two
sections, which is the format's most dangerous property for a reader, so each section spells
its own rule out in words. Full notes in [docs/format.md](docs/format.md).

## Documentation

- [docs/format.md](docs/format.md) — CRTDL/CCDL structure, boolean semantics, tolerated deviations
- [docs/layout.md](docs/layout.md) — the rendering design and the evidence behind it
- [docs/terminology.md](docs/terminology.md) — German display resolution and the ontology import

## Development

```bash
pip install -e ".[all]"
python tests/test_renderer.py      # assert-based, no framework
```

`examples/` holds queries written for this project; `examples/upstream/` holds 56 real queries
from the MII CRTDL and CCDL specs, TORCH and cctb, redistributed under Apache-2.0 with
attribution (see [examples/upstream/README.md](examples/upstream/README.md)). The test suite
runs against all of them.

## Status

Alpha. Exercised against 56 queries from the CRTDL and CCDL specs, TORCH's test resources and
cctb's CQL corpus. Not yet tested against a production FDPG export — if you have one, a bug
report with it attached is the most useful thing you could send.

## Licence and attribution

Apache License 2.0 — see [LICENSE](LICENSE). Attribution for everything this project builds on
is in [NOTICE](NOTICE): the redistributed MII example queries, the CRTDL/CCDL specifications,
the FDPG ontology, the code systems whose German designations appear in the curated seed
(ICD-10-GM/OPS/ATC from BfArM, LOINC, SNOMED CT, MII Broad Consent, KBV, HL7 FHIR), the
reference implementations consulted for the layout, and the optional runtime dependencies.

The code systems themselves remain under their own terms; this project grants no rights to
them.
