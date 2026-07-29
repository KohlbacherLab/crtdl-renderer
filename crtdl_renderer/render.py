# Copyright 2026 Kohlbacher Lab, University of Tübingen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Format-agnostic document model plus the Markdown renderer.

Every output format builds from the same two views of a criteria block:
`criteria_cards()` for the nested block layout and `block_rows()` for the flat
table layout. Both carry the boolean structure explicitly, so the renderers do
not reimplement it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .model import COMPARATORS, CriteriaBlock, Criterion, Query, Unit, ValueFilter

# German rendering for UCUM codes that are unreadable as-is
UCUM_DE = {"a": "Jahr(e)", "mo": "Monat(e)", "wk": "Woche(n)", "d": "Tag(e)",
           "h": "Stunde(n)", "min": "Minute(n)", "Cel": "°C", "kg": "kg", "cm": "cm"}


@dataclass
class Row:
    number: str
    text: str
    constraints: list[str] = field(default_factory=list)
    indent: int = 0
    is_header: bool = False  # group/reference header, not a criterion itself


def _num(x: float | None) -> str:
    if x is None:
        return "?"
    if isinstance(x, int):  # float() would overflow on very large JSON integers
        return str(x)
    return str(int(x)) if float(x).is_integer() else str(x).replace(".", ",")


def _de_date(value: str | None) -> str:
    """ISO date → dd.MM.yyyy, as the FDPG portal shows it. Malformed values
    (real exports contain e.g. „2021-5") are passed through untouched."""
    if not value:
        return ""
    parts = value.split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts) and len(parts[0]) == 4:
        y, m, d = parts
        return f"{int(d):02d}.{int(m):02d}.{y}"
    return value


def _same_unit(display: str, code: str) -> bool:
    """UCUM treats `L` and `l` as the same litre symbol, so `mg/dl` and `mg/dL`
    denote one unit. Anything else that differs is a real disagreement."""
    return display.strip().lower() == code.strip().lower()


def unit_label(u: Unit | None) -> tuple[str, str | None]:
    """Return (label, warning).

    The UCUM `code` is authoritative; `display` is free text that nothing
    validates. A file whose code says `mg/dL` while its display says `g/dL` is
    out by a factor of 1000, and printing the display would silently misstate a
    laboratory threshold. So the code wins and the disagreement is reported.
    """
    if not u:
        return "", None
    code, disp = (u.code or "").strip(), (u.display or "").strip()
    if code in UCUM_DE:            # curated German rendering of a known code
        return UCUM_DE[code], None
    if not code:
        return disp, None
    if not disp or _same_unit(disp, code):
        return code, None
    return code, (f"⚠ Einheit im Export widersprüchlich: UCUM-Code „{code}“, "
                  f"Bezeichnung „{disp}“ — dargestellt wird der Code.")


def _unit(u: Unit | None) -> str:
    label, _ = unit_label(u)
    return f" {label}" if label else ""


def _unit_warnings(vf: ValueFilter | None) -> list[str]:
    if not vf:
        return []
    _, warning = unit_label(vf.unit)
    return [warning] if warning else []


def _value_filter_text(vf: ValueFilter) -> str:
    if vf.kind == "concept":
        return " ODER ".join(c.label for c in vf.concepts)
    if vf.kind == "quantity-comparator":
        sym = COMPARATORS.get(vf.comparator or "", vf.comparator or "?")
        return f"{sym} {_num(vf.value)}{_unit(vf.unit)}"
    if vf.kind == "quantity-range":
        return f"{_num(vf.min_value)} bis {_num(vf.max_value)}{_unit(vf.unit)}"
    return f"⚠ unbekannter Filtertyp „{vf.kind}“ — nicht interpretiert"


def _criterion_text(c: Criterion) -> str:
    text = c.concepts[0].label
    if c.context and c.context.display:
        text = f"[{c.context.display}] {text}"
    return text


def _criterion_constraints(c: Criterion) -> list[str]:
    lines: list[str] = []
    if len(c.concepts) > 1:
        syn = "; ".join(x.label for x in c.concepts[1:])
        lines.append(f"Synonyme Codes: {syn}")
    if c.value_filter:
        lines.append(f"Wert: {_value_filter_text(c.value_filter)}")
        lines += _unit_warnings(c.value_filter)
    for af in c.attribute_filters:
        if af.kind == "reference":
            continue  # rendered as nested rows
        name = af.attribute.display if af.attribute else "Attribut"
        lines.append(f"{name}: {_value_filter_text(af.value)}" if af.value else name)
        lines += _unit_warnings(af.value)
    if c.time_restriction:
        # CCDL: an intersection of the criterion's interval with this one suffices.
        # Label and date format follow the FDPG portal („Zeitraum", dd.MM.yyyy).
        tr = c.time_restriction
        a, b = _de_date(tr.after), _de_date(tr.before)
        if a and b:
            lines.append(f"Zeitraum (Überschneidung): von {a} bis {b}")
        elif a:
            lines.append(f"Zeitraum (Überschneidung): ab {a}")
        elif b:
            lines.append(f"Zeitraum (Überschneidung): bis {b}")
    if c.is_consent:
        lines.append("(Einwilligung)")
    return lines


def _ref_rows(c: Criterion, label: str, indent: int) -> list[Row]:
    """Rows for `reference` attribute filters.

    The header spells out the quantifier and the scope instead of hiding them
    behind an arrow. Criteria inside one reference filter are OR-joined; several
    reference filters on the same criterion are AND-joined, like all attribute
    filters. The CCDL does not state the first of these; it follows the reference
    implementation, which unions them.
    """
    rows: list[Row] = []
    refs = [af for af in c.attribute_filters if af.kind == "reference"]
    for r, af in enumerate(refs, 1):
        name = af.attribute.display if af.attribute else "Referenz"
        n = len(af.ref_criteria)
        quant = ("mindestens eine der folgenden Diagnosen/Kriterien" if n > 1
                 else "das folgende Kriterium")
        lead = "" if r == 1 else "zusätzlich (UND): "
        ref_label = f"{label}r{r}"
        rows.append(Row(number=ref_label, indent=indent, is_header=True,
                        text=f"{lead}Referenzbedingung über „{name}“ — es muss {quant} "
                             f"dazu vorliegen:"))
        for k, rc in enumerate(af.ref_criteria, 1):
            text = _criterion_text(rc)
            if k > 1:
                text = f"oder {text}"
            rows.append(Row(number=f"{ref_label}{_letter(k)}",
                            indent=indent + 1, text=text,
                            constraints=_criterion_constraints(rc)))
    return rows


def group_filters(g) -> list[str]:
    """Filter lines of an attribute group, shared by all renderers."""
    lines = [f"{tf.name}: " + " ODER ".join(c.label for c in tf.codes)
             for tf in g.token_filters]
    lines += [f"{df.name}: {_de_date(df.start) or '…'} bis {_de_date(df.end) or '…'}"
              for df in g.date_filters]
    return lines


def group_attributes(g, names: dict[str, str], bold_marker: str = "") -> list[str]:
    """Attribute lines with must-have marker and resolved linkedGroups names."""
    out = []
    for a in g.attributes:
        line = a.ref
        if a.must_have:
            line += f" {bold_marker}(Pflicht){bold_marker}" if bold_marker else " (Pflicht)"
        if a.linked_groups:
            line += " → " + ", ".join(names.get(x, x) for x in a.linked_groups)
        out.append(line)
    return out


MUSTHAVE_NOTE = ("(Pflicht): Fehlt das Attribut bei einer Person, wird diese vollständig "
                 "von der Extraktion ausgeschlossen (mustHave-Regel).")


def version_line(q: Query) -> str:
    parts = [f"CRTDL-Version: {q.crtdl_version}" if q.crtdl_version else "",
             f"CCDL-Version: {q.version}" if q.version else ""]
    return "   ".join(p for p in parts if p)


# Printed even when a criterion has no constraints, so a reader is never left
# guessing whether one was omitted or simply not shown.
NO_CONSTRAINT = "keine Einschränkung"

LEGEND = [
    ("E1, E2 …", "Einschlussbedingung; alle müssen erfüllt sein"),
    ("A1, A2 …", "Ausschlussbedingung; eine genügt für den Ausschluss"),
    ("E2a, E2b …", "Kriterien innerhalb der Bedingung E2"),
    ("E4r1a …", "Kriterium einer Referenzbedingung von E4"),
    ("Name (Code, System Version)", "Bezeichnung, Code und Kodiersystem des Konzepts; "
                                    "die vollständige System-URI steht unter „Kodiersysteme“"),
    ("x bis y", "Wertebereich; die CCDL legt nicht fest, ob die Grenzen "
                "eingeschlossen sind — hier unverändert wiedergegeben"),
    ("Einheiten", "dargestellt wird der UCUM-Code aus dem Export, nicht die freie "
                  "Bezeichnung; Abweichungen zwischen beiden werden am Kriterium vermerkt"),
    ("Bezeichnungen", "aus der FDPG-Terminologie aufgelöst und können daher von den im "
                      "Export enthaltenen Bezeichnungen abweichen; Codes und Systeme "
                      "stammen unverändert aus dem Export"),
    ("→ Ausschluss", "Zutreffen dieser Bedingung schließt die Person aus"),
]


def legend_for(q: Query) -> list[tuple[str, str]]:
    """Only the notation this document actually uses.

    A static legend explains `E4r1a` in a query with no reference conditions,
    which sends the reader looking for something that is not there.
    """
    def crits():
        for block in (q.inclusion, q.exclusion):
            if block:
                for g in block.groups:
                    yield from g.criteria

    has_groups = any(len(g.criteria) > 1
                     for b in (q.inclusion, q.exclusion) if b for g in b.groups)
    has_refs = any(af.kind == "reference" for c in crits() for af in c.attribute_filters)
    filters = [c.value_filter for c in crits() if c.value_filter]
    filters += [af.value for c in crits() for af in c.attribute_filters if af.value]
    has_units = any(f.unit for f in filters)
    has_range = any(f.kind == "quantity-range" for f in filters)

    rows = []
    if q.inclusion:
        rows.append(("E1, E2 …", "Einschlussbedingung; alle müssen erfüllt sein"))
    if q.exclusion:
        rows.append(("A1, A2 …", "Ausschlussbedingung; eine genügt für den Ausschluss"))
    if has_groups:
        rows.append(("E2a, E2b …", "Kriterien innerhalb der Bedingung E2"))
    if has_refs:
        rows.append(("E4r1a …", "Kriterium einer Referenzbedingung von E4"))
    rows.append(("Name (Code, System Version)",
                 "Bezeichnung, Code und Kodiersystem des Konzepts; die vollständige "
                 "System-URI steht unter „Kodiersysteme“"))
    if has_range:
        rows.append(("x bis y", "Wertebereich; die CCDL legt nicht fest, ob die Grenzen "
                                "eingeschlossen sind — hier unverändert wiedergegeben"))
    if has_units:
        rows.append(("Einheiten", "dargestellt wird der UCUM-Code aus dem Export, nicht die "
                                  "freie Bezeichnung; Abweichungen zwischen beiden werden am "
                                  "Kriterium vermerkt"))
    rows.append(("Bezeichnungen",
                 "aus der FDPG-Terminologie aufgelöst und können daher von den im Export "
                 "enthaltenen Bezeichnungen abweichen; Codes und Systeme stammen "
                 "unverändert aus dem Export"))
    if q.exclusion:
        rows.append(("→ Ausschluss", "Zutreffen dieser Bedingung schließt die Person aus"))
    return rows


UNRESOLVED_NOTE = ("Für folgende Codes lag keine geprüfte deutsche Bezeichnung vor; "
                   "angezeigt wird die im Export enthaltene Bezeichnung: ")


def unresolved_codes(q: Query, code_format: str = "{code}") -> list[str]:
    """De-duplicated `code (system)` entries for the footnote, in first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for c in q.unresolved:
        key = f"{c.system}|{c.code}"
        if key not in seen:
            seen.add(key)
            out.append(f"{code_format.format(code=c.code)} ({c.system_label})")
    return out


def _walk_concepts(q: Query):
    """Every Concept anywhere in the query, so the appendix can be complete."""
    def from_criterion(c):
        if c.context:
            yield c.context
        yield from c.concepts
        if c.value_filter:
            yield from c.value_filter.concepts
        for af in c.attribute_filters:
            if af.attribute:
                yield af.attribute
            if af.value:
                yield from af.value.concepts
            for rc in af.ref_criteria:
                yield from from_criterion(rc)
    for block in (q.inclusion, q.exclusion):
        if block:
            for group in block.groups:
                for c in group.criteria:
                    yield from from_criterion(c)
    for g in q.attribute_groups:
        for tf in g.token_filters:
            yield from tf.codes


def code_systems(q: Query) -> list[tuple[str, str, str, bool]]:
    """(short label, full URI, versions, ambiguous) for every system used.

    The criteria lines carry a short label like „ICD-10-GM"; two different URIs
    can share one — `…/bfarm/icd-10-gm` and the legacy `…/dimdi/icd-10-gm` do.
    Without this table the exact system is unrecoverable from the document, and
    that difference is exactly the kind of thing an audit needs to see.
    """
    seen: dict[str, tuple[str, set[str]]] = {}
    for c in _walk_concepts(q):
        uri = c.system or "(ohne System)"
        label, versions = seen.setdefault(uri, (c.system_label, set()))
        if c.version:
            versions.add(c.version)
    by_label: dict[str, int] = {}
    for label, _ in seen.values():
        by_label[label] = by_label.get(label, 0) + 1
    return sorted(
        (label, uri, ", ".join(sorted(v)) or "—", by_label[label] > 1)
        for uri, (label, v) in seen.items())


def leaf_labels(block: CriteriaBlock) -> list[str]:
    """Every criterion label the table shows, including reference sub-criteria."""
    return [r.number for r in block_rows(block) if not r.is_header]


def completeness_note(block: CriteriaBlock) -> str:
    """States that the formula references every criterion of the block, which the
    generated output guarantees by construction."""
    return (f"Alle {len(leaf_labels(block))} Kriterien dieses Abschnitts sind in der "
            f"formalen Struktur genau einmal referenziert.")


def cohort_rule(q: Query) -> str:
    """One plain-language sentence naming both label ranges and the negation.

    Stated with the same labels the criteria carry, so the negation survives a
    reader who jumps straight to a block.
    """
    inc = f"**alle Einschlussbedingungen ({block_labels(q.inclusion)})** erfüllt" \
        if q.inclusion else ""
    if q.exclusion:
        exc = (f"**keine der Ausschlussbedingungen ({block_labels(q.exclusion)})** "
               f"zutrifft")
        return (f"Eine Person gehört zur Kohorte, wenn {inc} sind **und** {exc}.")
    return f"Eine Person gehört zur Kohorte, wenn {inc} sind."


def has_must_have(q: Query) -> bool:
    return any(a.must_have for g in q.attribute_groups for a in g.attributes)


def group_names(q: Query) -> dict[str, str]:
    return {g.id: (g.name or g.module_label) for g in q.attribute_groups if g.id}


def group_title(g) -> str:
    title = g.name or g.module_label
    return f"{title} (nur als Referenz)" if g.include_reference_only else title


_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def _letter(i: int) -> str:
    """1→a, 2→b, … 27→aa (groups never get this large in practice)."""
    return _ALPHABET[(i - 1) % 26] * (1 + (i - 1) // 26)


def block_prefix(block: CriteriaBlock) -> str:
    return "E" if block.kind == "inclusion" else "A"


def block_labels(block: CriteriaBlock) -> str:
    """`E1–E6`, or `E1` when there is a single group."""
    p = block_prefix(block)
    n = len(block.groups)
    return f"{p}1" if n <= 1 else f"{p}1–{p}{n}"


def block_intro(block: CriteriaBlock) -> str:
    """States the outer rule once, in words, including the negation for exclusions.

    The operator is a property of the section, not of every row — repeating
    „UND" on ten rows carries no information, and the CNF/DNF inversion between
    the two sections is invisible unless it is spelled out here.
    """
    labels = block_labels(block)
    n = len(block.groups)
    # Vocabulary follows the FDPG product strings (UND / ODER, „verknüpft"); the
    # portal has no „UND-Verknüpfung"/„Kriteriengruppe" wording, so neither do we.
    if block.kind == "inclusion":
        if n <= 1:
            return f"**Die folgende Bedingung {labels} muss erfüllt sein.**"
        return (f"**Alle {n} Bedingungen {labels} müssen erfüllt sein** "
                f"(mit UND verknüpft).")
    if n <= 1:
        return (f"**Trifft die folgende Bedingung {labels} zu, wird die Person "
                f"ausgeschlossen.**")
    return (f"**Trifft mindestens eine der {n} Bedingungen {labels} zu, wird die Person "
            f"ausgeschlossen** (mit ODER verknüpft).")


def group_quantifier(group, prefix: str, gi: int) -> str:
    """Header sentence of a multi-criterion group, naming its own members."""
    n = len(group.criteria)
    members = f"{prefix}{gi}{_letter(1)}–{prefix}{gi}{_letter(n)}"
    if group.inner_op == "ODER":
        return f"Mindestens eines der folgenden {n} Kriterien ({members}):"
    return f"Alle folgenden {n} Kriterien ({members}) gemeinsam:"


@dataclass
class Card:
    """A block in the card layout: either a criterion or a group container.

    The operator lives *between* cards rather than in a column, so it cannot be
    read as belonging to one side of the pair.
    """
    label: str
    title: str
    constraints: list[str] = field(default_factory=list)
    children: list[Card] = field(default_factory=list)
    op: str = ""        # operator joining this card to the previous sibling
    level: int = 0
    kind: str = "criterion"   # 'criterion' | 'group' | 'reference'


def _criterion_card(c: Criterion, label: str, level: int, op: str = "") -> Card:
    card = Card(label=label, title=_criterion_text(c),
                constraints=_criterion_constraints(c), op=op, level=level)
    refs = [af for af in c.attribute_filters if af.kind == "reference"]
    for r, af in enumerate(refs, 1):
        name = af.attribute.display if af.attribute else "Referenz"
        n = len(af.ref_criteria)
        quant = ("mindestens eines der folgenden Kriterien" if n > 1
                 else "das folgende Kriterium")
        ref = Card(label=f"{label}r{r}",
                   title=f"Referenzbedingung über „{name}“ — es muss {quant} dazu vorliegen:",
                   op="UND" if r > 1 else "", level=level + 1, kind="reference")
        for k, rc in enumerate(af.ref_criteria, 1):
            ref.children.append(_criterion_card(rc, f"{label}r{r}{_letter(k)}",
                                                level + 2, "ODER" if k > 1 else ""))
        card.children.append(ref)
    return card


def criteria_cards(block: CriteriaBlock) -> list[Card]:
    """The block's groups as a card tree; `op` carries the operator that joins
    each card to its predecessor."""
    p = block_prefix(block)
    excl = block.kind == "exclusion"
    cards: list[Card] = []
    for gi, group in enumerate(block.groups, 1):
        outer = block.outer_op if gi > 1 else ""
        if len(group.criteria) == 1:
            card = _criterion_card(group.criteria[0], f"{p}{gi}", 0, outer)
            if excl:
                card.title += " → Ausschluss"
            cards.append(card)
        else:
            head = group_quantifier(group, p, gi)
            if excl:
                head = head.rstrip(":") + " → Ausschluss:"
            g = Card(label=f"{p}{gi}", title=head, op=outer, level=0, kind="group")
            for ci, c in enumerate(group.criteria, 1):
                g.children.append(_criterion_card(
                    c, f"{p}{gi}{_letter(ci)}", 1, group.inner_op if ci > 1 else ""))
            cards.append(g)
    return cards


def _criterion_formula(c: Criterion, label: str) -> str:
    """A criterion plus its reference sub-blocks, e.g. `E4 UND (E4r1a ODER E4r1b)`.

    Reference criteria must appear: a cross-check that silently omits a branch is
    worse than no cross-check.
    """
    parts = [label]
    refs = [af for af in c.attribute_filters if af.kind == "reference"]
    for r, af in enumerate(refs, 1):
        n = len(af.ref_criteria)
        inner = " ODER ".join(f"{label}r{r}{_letter(k)}" for k in range(1, n + 1))
        parts.append(inner if n == 1 else f"({inner})")
    return " UND ".join(parts)


def block_formula(block: CriteriaBlock) -> str:
    """Parenthesised audit form over the same labels, e.g. `E1 UND (E2a ODER E2b)`.

    The one fully rigorous statement in the document, written in the labels the
    table actually shows. Every leaf appears exactly once (see `formula_labels`).
    """
    p = block_prefix(block)
    parts = []
    for gi, group in enumerate(block.groups, 1):
        if len(group.criteria) == 1:
            f = _criterion_formula(group.criteria[0], f"{p}{gi}")
            parts.append(f if " " not in f else f"({f})")
        else:
            inner = f" {group.inner_op} ".join(
                _criterion_formula(c, f"{p}{gi}{_letter(ci)}")
                for ci, c in enumerate(group.criteria, 1))
            parts.append(f"({inner})")
    return f" {block.outer_op} ".join(parts)


def formula_labels(block: CriteriaBlock) -> list[str]:
    """Every label appearing in the formula — used to assert that it covers all
    leaves exactly once."""
    import re
    # longest alternative first: E4r1a must not be truncated to E4r
    return re.findall(r"[EA]\d+r\d+[a-z]|[EA]\d+[a-z]|[EA]\d+", block_formula(block))


def block_rows(block: CriteriaBlock) -> list[Row]:
    """One row per criterion; group membership carried by the label, not indentation.

    A label like `E2b` identifies its group even when the row wraps or a page
    break separates it from its header — which is exactly where indentation fails.

    Exclusion blocks additionally carry „→ Ausschluss" on the block-level row.
    Note the marker sits at *block* scope: in the CCDL an exclusion criterion is a
    positive condition whose fulfilment excludes the person, so negating the
    individual criterion text (ATLAS-style „having no …") would invert the query.
    """
    p = block_prefix(block)
    excl = block.kind == "exclusion"
    rows: list[Row] = []
    for gi, group in enumerate(block.groups, 1):
        if len(group.criteria) == 1:
            c = group.criteria[0]
            label = f"{p}{gi}"
            text = _criterion_text(c)
            if excl:
                text += " → Ausschluss"
            rows.append(Row(number=label, indent=0,
                            text=text, constraints=_criterion_constraints(c)))
            rows += _ref_rows(c, label, indent=1)
        else:
            head = group_quantifier(group, p, gi)
            if excl:
                head = head.rstrip(":") + " → Ausschluss:"
            rows.append(Row(number=f"{p}{gi}", indent=0, is_header=True,
                            text=head))
            for ci, c in enumerate(group.criteria, 1):
                label = f"{p}{gi}{_letter(ci)}"
                text = _criterion_text(c)
                if ci > 1:  # inner operator visible on the row it applies to
                    text = f"{group.inner_op.lower()} {text}"
                rows.append(Row(number=label, indent=1, text=text,
                                constraints=_criterion_constraints(c)))
                rows += _ref_rows(c, label, indent=2)
    return rows


# ---------------------------------------------------------------- markdown

_INDENT = "&emsp;&emsp;"


def _esc(text: str) -> str:
    """Pipes inside code displays would otherwise break the GFM table."""
    return text.replace("|", "\\|")


def criteria_head(block: CriteriaBlock) -> list[str]:
    """Column headers. The middle one names the section's effect, because in a
    paginated PDF the repeated header row is the only context a reader gets on
    page 2 of a long table."""
    what = ("Bedingung — Zutreffen führt zum AUSSCHLUSS" if block.kind == "exclusion"
            else "Bedingung — muss erfüllt sein")
    return ["Nr.", what, "Einschränkungen"]


def _md_table(block: CriteriaBlock, rows: list[Row]) -> str:
    head = criteria_head(block)
    out = [f"| {head[0]} | {head[1]} | {head[2]} |", "|---|---|---|"]
    for r in rows:
        text = _esc(r.text)
        # group headers are set apart typographically, not just by wording
        crit = _INDENT * r.indent + (f"**{text}**" if r.is_header else text)
        cons = "<br>".join(_esc(x) for x in r.constraints) or (
            "" if r.is_header else NO_CONSTRAINT)
        out.append(f"| {r.number} | {crit} | {cons} |")
    return "\n".join(out)


def _md_cards(cards: list[Card], depth: int = 0) -> list[str]:
    """Cards as nested blockquotes — Markdown's blockquote *is* a left accent
    rail, and it nests, which is what shows depth.

    Every line inside a subtree stays `>`-prefixed, including the blank spacer
    lines: an unprefixed blank line would close the quote and restart the rail.
    """
    out: list[str] = []
    rail = "> " * (depth + 1)
    for i, card in enumerate(cards):
        if card.op and depth == 0:
            # top level: each card is its own quote block, operator stands between
            out += ["", f"**{card.op}**", ""]
        elif card.op:
            out += [f"{rail}", f"{rail}**{card.op}**", f"{rail}"]
        elif i and depth:
            out.append(f"{rail}")
        sep = " · " if card.kind != "criterion" else " "
        out.append(f"{rail}**{card.label}**{sep}{_esc(card.title)}")
        for line in card.constraints:
            out.append(f"{rail}↳ {_esc(line)}")
        if card.children:
            out.append(f"{rail}")
            out += _md_cards(card.children, depth + 1)
    if depth == 0:
        out.append("")
    return out


def render_markdown(q: Query, today: date | None = None, layout: str = "cards") -> str:
    """`today` is injectable so golden-file tests stay deterministic.

    `layout='cards'` (default) renders the boolean hierarchy as nested blocks —
    the shape i2b2's printed report, CIRCE and the FDPG editor all use.
    `layout='table'` keeps the flat grid.
    """
    parts = [f"# Machbarkeitsanfrage: {q.display or q.source_name}", ""]
    meta = [f"**Quelle:** `{q.source_name}`" if q.source_name else "",
            f"**Erstellt:** {(today or date.today()).isoformat()}",
            f"**CRTDL-Version:** {q.crtdl_version}" if q.crtdl_version else "",
            f"**CCDL-Version:** {q.version}" if q.version else ""]
    parts.append("  \n".join(x for x in meta if x))
    parts.append("")

    parts.append("## Kohortendefinition\n")
    parts.append(cohort_rule(q) + "\n")

    for block, title in ((q.inclusion, "Einschlusskriterien"),
                         (q.exclusion, "Ausschlusskriterien")):
        if not block:
            continue
        parts.append(f"### {title}\n")
        parts.append(block_intro(block) + "\n")
        # Before the criteria, not after: trailing material below a list is
        # ambiguous about whether it applies to the last item or to all of them.
        parts.append(f"*Formale Struktur:* `{block_formula(block)}`  \n"
                     f"<sub>{completeness_note(block)}</sub>\n")
        if layout == "table":
            parts.append(_md_table(block, block_rows(block)))
        else:
            parts += _md_cards(criteria_cards(block))
        parts.append("")

    if q.attribute_groups:
        parts.append("## Datenextraktion\n")
        parts.append("| Modul / Profil | Filter | Attribute |")
        parts.append("|---|---|---|")
        names = group_names(q)
        for g in q.attribute_groups:
            filters = "<br>".join(_esc(x) for x in group_filters(g)) or "—"
            attrs = "<br>".join(_esc(x) for x in group_attributes(g, names, "**")) or "—"
            parts.append(f"| {_esc(group_title(g))} | {filters} | {attrs} |")
        parts.append("")
        if has_must_have(q):
            parts.append(f"> **{MUSTHAVE_NOTE}**\n")

    parts.append("## Kodiersysteme\n")
    parts.append("| Kurzform | System-URI | Version(en) |")
    parts.append("|---|---|---|")
    for label, uri, versions, ambiguous in code_systems(q):
        mark = " ⚠" if ambiguous else ""
        parts.append(f"| {_esc(label)}{mark} | `{_esc(uri)}` | {_esc(versions)} |")
    if any(a for *_, a in code_systems(q)):
        parts.append("")
        parts.append("> ⚠ Diese Kurzform steht im Dokument für mehr als eine System-URI. "
                     "Die Kriterien nennen nur die Kurzform; maßgeblich ist die URI aus dem "
                     "Export.")
    parts.append("")

    parts.append("## Lesehilfe\n")
    parts.append("| Notation | Bedeutung |")
    parts.append("|---|---|")
    for sym, meaning in legend_for(q):
        parts.append(f"| `{sym}` | {meaning} |")
    parts.append("")

    if q.unresolved:
        items = unresolved_codes(q, "`{code}`")
        parts.append(f"---\n*{UNRESOLVED_NOTE}"
                     + ", ".join(items) + "*")
    return "\n".join(parts) + "\n"
