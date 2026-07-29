# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-07-29

First stable release. Same code as `0.1.0`, promoted after the rendered examples were
published and CI was verified green on Python 3.11–3.13.

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
- 19 assert-based self-checks, run against 57 example queries.

### Notes on correctness
- The join between criteria inside a `reference` attribute filter is **OR**, verified against
  `cctb`'s `ReferenceModifier` rather than inferred from the specification, which is silent.
- Terminology cache keys include the code-system version, because ICD-10-GM and OPS codes are
  reused with different meanings between annual releases.
- German display is `display.de || display.original`; reading `de` alone silently drops every
  BfArM code system.

[1.0.0]: https://github.com/KohlbacherLab/crtdl-renderer/releases/tag/v1.0.0
[0.1.0]: https://github.com/KohlbacherLab/crtdl-renderer/releases/tag/v0.1.0
