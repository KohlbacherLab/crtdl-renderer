# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

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
