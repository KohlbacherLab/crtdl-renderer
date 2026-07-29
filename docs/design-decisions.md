# Design decisions

Why the rendering looks the way it does. Kept separate from
[layout.md](layout.md), which describes what the renderer produces.

Each rule follows established practice rather than invention. The precedents are named so that
a future change can weigh what it would be departing from.

| Rule | Precedent |
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

Deliberately not used: **Venn diagrams**, which cannot show more than three sets legibly;
**infix text relying on operator precedence**, which readers routinely misparse; and
**indentation as the only nesting cue**, which is lost to line wrapping and page breaks.

## Deliberately not used

**Venn diagrams** cannot show more than three sets legibly. **Infix text relying on operator
precedence** is routinely misparsed. **Indentation as the only nesting cue** is lost to line
wrapping and page breaks.
