# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [1.1.1] — 2026-07-29

Correctness fixes from a further audit. Two of these made the document describe a cohort the
query did not encode, which is the failure this tool exists to prevent.

### Fixed
- **Nested `reference` filters are refused.** The CCDL forbids them; the parser accepted them
  and the outputs then disagreed — the card layout showed the nested branch while the table,
  the formula and the CSV dropped it, so the document's own „genau einmal referenziert"
  guarantee was false.
- **Empty criterion groups are refused.** An empty inner array is FALSE in the inclusion CNF
  and TRUE in the exclusion DNF. Dropping it turned an unsatisfiable query into a plausible
  one. An empty `inclusionCriteria` is refused for the same reason.
- **A `timeRestriction` with neither bound is refused** instead of vanishing from every format.
- **Attribute-group filters of unrecognised shape are shown** with a warning instead of being
  dropped.
- **The AND between multiple `attributeFilters` is now visible**; a list of them previously
  read exactly like alternatives.
- **Markdown output escapes `<`, `>`, `&`, `*` and `_`**, not just `|`. Terminology text can
  come from a server and must not become live markup.
- **Impossible dates** such as `2021-13-45` are marked rather than formatted as `45.13.2021`.
- **A unit whose display contradicts a curated German rendering is reported** (`a`/`Monat`),
  while legitimate spelling differences (`a`/`Jahre`, `Cel`/`°C`) are not.
- **`--online` writes back only the fetched entries**, merged into the file given by `--cache`,
  instead of rewriting the merged in-memory cache — which folded the packaged seed into the
  user's file and rewrote tens of megabytes per run. An unwritable path warns instead of
  crashing.
- Wrong-typed `termCodes`, `valueFilter` and `attributeFilters` report the offending path.
- The legend now also inspects criteria nested inside reference filters.

### Changed
- `docs/format.md` documents what is refused and why; the previous claim that only a missing
  `inclusionCriteria` is rejected was no longer true.
- Design precedents moved from `docs/layout.md` into `docs/design-decisions.md`, leaving the
  layout document to describe the output rather than its provenance.

## [1.1.0] — 2026-07-29

### Fixed
- **Units are taken from the UCUM `unit.code`, not from `unit.display`.** `display` is free
  text that nothing validates; a file whose code said `mg/dL` while its display said `g/dL`
  previously rendered `g/dL`, misstating a laboratory threshold by a factor of 1000. The code
  now wins and a contradicting display is reported on the criterion.
- **`--online` no longer writes into the packaged terminology cache.** Results are persisted
  only to the file named by `--cache`; without it they live for the run only.
- Removed an unsupported German label for the `Patient` context that overrode the value in the
  export. Curated entries now only cover contexts whose portal name genuinely differs.
- Malformed input (top-level array, criteria that are not lists of lists, non-object criteria)
  reports an actionable error instead of raising `AttributeError`.
- `__version__` is read from the installed package metadata rather than duplicated.

### Added
- **Kodiersysteme appendix** listing every code system with its full URI and versions, so the
  short labels in the criteria stay traceable. Short labels standing for more than one URI —
  such as the current and legacy ICD-10-GM URIs — are flagged.
- The legend now adapts to the document and explains only notation that occurs in it, plus
  the unit rule, the undefined range-boundary semantics and the fact that displays are
  resolved from terminology and may differ from the export.
- End-to-end test suite driving the command line over every bundled query, checking that no
  criterion is lost, that the CSV round-trips, and that the PDF has a usable text layer.

### Changed
- Removed the unused `Row.connector` field; shared the duplicated unresolved-code footnote
  logic across the renderers; declared an explicit ruff rule set.

## [1.0.0] — 2026-07-29

First stable release.

From here the command-line interface and the output structure are considered stable; changes
that would break either get a major version.

**Not yet validated against a production FDPG export.** Every example this was tested against
comes from a specification repository or a reference implementation's test resources. Those
already disagree with the published schema in six documented ways (see `docs/format.md`), so
live exports may well contain a seventh. A bug report with a real query attached is the most
useful contribution right now.

## [0.1.0] — 2026-07-29

Initial packaging of the renderer.

### Added
- Parser for CRTDL and bare CCDL into a typed hierarchical intermediate representation,
  tolerant of the deviations real exports contain (see `docs/format.md`).
- German display-name resolution: layered cache → embedded display → bare code, with an
  importer for the FDPG search ontology (`python -m crtdl_renderer.ontology`) yielding
  ~639,000 names. Unverified labels are flagged in a footnote, never invented.
- Rendering to Markdown, DOCX and PDF in two layouts: `cards` (nested blocks on a left
  accent rail, default) and `table` (flat grid).
- CSV export matching the FDPG's own committee-facing column set, with three corrections to
  the original: the first column is labelled `Kontext` rather than the misleading `Modul`,
  `Verknüpfungsgruppe` names the UND/ODER group explicitly, and criteria inside reference
  conditions get their own rows instead of being dropped.
- Assert-based unit and end-to-end self-checks, run against every bundled query.

### Notes on correctness
- The join between criteria inside a `reference` attribute filter is **OR**. The CCDL does not
  state it; this follows the reference implementation, which unions them.
- Terminology cache keys include the code-system version, because ICD-10-GM and OPS codes are
  reused with different meanings between annual releases.
- German display is `display.de || display.original`; reading `de` alone silently drops every
  BfArM code system.

[1.0.0]: https://github.com/KohlbacherLab/crtdl-renderer/releases/tag/v1.0.0
[0.1.0]: https://github.com/KohlbacherLab/crtdl-renderer/releases/tag/v0.1.0
