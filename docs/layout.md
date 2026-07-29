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
letterspaced. It is never a column, because a single operator column has to mean "joined to the
previous group" on one row and "joined to the sibling criterion" on the next — one glyph, one
position, two scopes.

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


## What is still a table, and why

The extraction table, the code-system appendix, the legend and the CSV export. Tabular suits
enumerable facts; it does not suit boolean structure. `--layout table` renders the criteria as
a grid too, for readers who prefer one.

## Known gaps

- **No worked example.** A qualifying case plus a near-miss would help a lay reader most, but
  it is not generated: inventing a clinically plausible patient risks fabricating something
  misleading. It needs human-authored text.
- **`attributeRef` renders verbatim.** `Observation.value` has no German label here; those
  live in the FDPG ontology's `backend.zip` `ui_profile` table, which is not imported yet.
- **Value sets are always inlined.** Long code lists belong in an appendix. The longest list
  in the bundled corpus is two codes, so the threshold — inline up to about five, reference
  beyond — is documented rather than implemented.

The precedents these rules follow are recorded in [design-decisions.md](design-decisions.md).
