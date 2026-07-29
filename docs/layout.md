# The rendering design

The audience is a Use-&-Access-Committee member or an ethics reviewer holding a printed page.
They cannot hover, expand or toggle. They must reconstruct a nested boolean expression
correctly, once, without training.

## What the document does

**Blocks, not rows.** Each condition is a block on a coloured left rail that thins and lightens
with depth. Containment is shown as containment. There are no fills and no borders — a filled
full-width block reads as a table row whatever it means, and the structural work is done by the
rail plus whitespace.

**The operator stands between blocks.** It joins two things, so it sits between them, small and
letterspaced. It is never a column: in the earlier table layout a `UND` in the connector column
meant "joined to the previous *group*" on one row and "joined to the sibling *criterion*" on the
next — the same glyph in the same position with two different scopes.

**Labels carry membership.** `E2b` announces "group E2, member b". This survives a wrapped line
and a page break, which indentation does not: a continuation line starts at the cell edge and
looks top-level, and a group split across pages loses its header. Inclusion labels are `E*`,
exclusion `A*`, so „Kriterium E2" cannot mean a container in one document and a criterion in
another.

**Each level states its own quantifier.** The section says „Alle 6 Bedingungen E1–E6 müssen
erfüllt sein"; a group says „Mindestens eines der folgenden 2 Kriterien (E2a–E2b):". The
operator is a property of the level, not of every row — ten rows repeating „UND" carry no
information.

**The inner operator appears on the row it governs.** `E2b` reads „oder [Diagnose] …" — no empty
first-operand cell and no inherited-operator convention to learn.

**The negation is structural.** The cohort sentence names both label ranges; the exclusion
section carries its own rule; block rows carry `→ Ausschluss`; and the exclusion table's
repeated header says „Zutreffen führt zum AUSSCHLUSS". Colour is a fourth cue and never the
only one, so the document survives greyscale printing.

**A formula line per section.** `E1 UND (E2a ODER E2b) UND E3` — the one fully rigorous
statement, in the labels the document actually shows, placed *before* the blocks. A test
asserts it covers every leaf exactly once.

## Where each decision came from

Verified from published sources and application source, not from taste.

| Decision | Evidence |
|---|---|
| Quantifier lead-in instead of bare operators | OHDSI CIRCE emits `with all of the following criteria:` / `with any of the following criteria:`; SPIRIT 2013 uses "must comply with all of the following"; GOV.UK bans trailing and/or outright and mandates a clarifying phrase |
| Inner operator as a lowercase lead-in on each member after the first | CIRCE does exactly this: `Type() == 'ALL' ? 'and ' : 'or '`, skipped when `$index() == 0` |
| Uppercase outer operator, lowercase inner | IRS Form 1040 "Qualifying Child" encodes precedence by typographic case, with no parentheses, in a document written for the general public |
| Collapse single-child groups | CIRCE suppresses the header for a one-criterion ANY/ALL group; cBioPortal parenthesises only when a group has more than one child |
| Left accent rail for depth | the FDPG editor's criterion cards, Samply Sample Locator's 2px rail, Samply.Share's 3px rail, Glowing Bear's rail that narrows and darkens per level |
| Negation marked redundantly, never by colour alone | i2b2 marks an inverted panel three times over — gutter `NOT`, balloon `none of these`, background `#FFA4A4` |
| Spell out constraints even at their default | i2b2's printed Query Report prints `Independent of Visit`, `From earliest date available…` regardless |
| Formula line before the blocks, never after | HdR Rn. 296 forbids a sentence continuing after a list; the US Senate manual says "avoid a cut-in followed by flush language"; ISO/IEC Directives 22.3.3 forbids hanging paragraphs because references into them are ambiguous |
| Every leaf referenced exactly once | Salesforce's Actionable-List-Builder invariant; PRESS calls an unreferenced line an "orphan line" and lists it as a search-strategy defect |
| Whitespace before rules; no chartjunk | Butterick, Tufte, and the Gestalt proximity literature |
| Cap depth, prefer breadth | Federal Plain Language Guidelines "Limit levels to three or fewer"; OFR Document Drafting Handbook; HdR Rn. 382 |
| German vocabulary | the FDPG product strings (`UND`, `ODER`, `Einschlusskriterien`, `Ausschlusskriterien`, `verknüpft`). The portal has no "UND-Verknüpfung" or "Kriteriengruppe" wording, so neither does this |
| Dates as `DD.MM.YYYY` | the FDPG interface's own format |

Rejected on evidence: **Venn diagrams** (VQuery users were slower and more error-prone than
with a textual interface, and the form breaks past three sets); **infix text with implied
precedence** (17 of 20 subjects misread precedence in Young & Shneiderman's SQL condition);
**indentation as the only nesting cue** (fails on wrap and page break).

## What is still a table, and why

The extraction table, the legend, and the CSV export. Tabular is right for enumerable facts;
it was wrong for the boolean structure. The `--layout table` flag keeps the old grid for the
criteria if a particular reader wants one.

## Known gaps

- **No worked example.** Both research threads rate a positive plus a near-miss case the
  highest-value remaining addition. Not generated automatically: inventing a clinically
  plausible patient risks fabricating something misleading. It wants human-authored text.
- **`attributeRef` renders verbatim.** `Observation.value` has no German label here; those
  live in the FDPG ontology's `backend.zip` `ui_profile` table, which is not imported yet.
- **Value sets are always inlined.** Both CIRCE and TriNetX push long code lists to an
  appendix. The longest list across the bundled corpus is 2 codes, so the threshold —
  inline up to about 5, reference beyond — is documented rather than implemented.
