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
"""PDF rendering via reportlab (optional dependency)."""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

from .model import Query
from .render import (LEGEND, MUSTHAVE_NOTE, NO_CONSTRAINT, Row, block_formula,
                     criteria_cards,
                     block_intro, block_rows, completeness_note,
                     cohort_rule, criteria_head, group_attributes, group_filters,
                     group_names, group_title, has_must_have, version_line)


def _md_bold(text: str) -> str:
    """`**x**` → reportlab `<b>x</b>`, escaping everything else."""
    parts = text.split("**")
    return "".join(escape(p) if i % 2 == 0 else f"<b>{escape(p)}</b>"
                   for i, p in enumerate(parts))


def _styles():
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    ss = getSampleStyleSheet()
    # left-aligned, letterspaced, grey: a quiet connector, not a banner row
    ss.add(ParagraphStyle("Op", parent=ss["BodyText"], fontSize=7.5, leading=9,
                          textColor="#8a8f96", spaceBefore=0, spaceAfter=0,
                          leftIndent=9, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("Crit", parent=ss["BodyText"], fontSize=9.5, leading=13,
                          spaceBefore=0, spaceAfter=1))
    ss.add(ParagraphStyle("Cons", parent=ss["BodyText"], fontSize=8, leading=11,
                          textColor="#5a616b", leftIndent=10, spaceAfter=0,
                          bulletIndent=2))
    # same size, no hanging indent — for table cells, where the indent would skew
    ss.add(ParagraphStyle("Cell", parent=ss["BodyText"], fontSize=8, leading=11,
                          textColor="#333333"))
    return ss


def _criteria_table(block, rows: list[Row], ss):
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    excl = block.kind == "exclusion"
    data = [criteria_head(block)]
    for r in rows:
        text = escape(r.text)
        crit = Paragraph(f"<b>{text}</b>" if r.is_header else text, ss["Crit"])
        crit.style = crit.style.clone("i", leftIndent=8 * r.indent)
        lines = r.constraints or ([] if r.is_header else [NO_CONSTRAINT])
        cons = Paragraph("<br/>".join(escape(x) for x in lines), ss["Cons"])
        num = Paragraph(f"<b>{escape(r.number)}</b>" if r.is_header
                        else escape(r.number), ss["Crit"])
        data.append([num, crit, cons])
    # A second, non-lexical cue for the exclusion table — but never colour alone:
    # it is always paired with the header wording and the „→ Ausschluss" marker,
    # so the document still reads correctly in greyscale.
    head_bg = colors.HexColor("#8a3b2c" if excl else "#2c5f8a")
    band = colors.HexColor("#faf2f0" if excl else "#f2f6fa")
    t = Table(data, colWidths=[1.6 * cm, 9.4 * cm, 6.6 * cm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), head_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, band]),
    ]))
    return t


def _card_flowables(cards, ss, excl: bool, depth: int = 0, width: float = 17.6):
    """Cards as nested bordered blocks with a coloured left rail that narrows and
    darkens with depth — the device i2b2's printed report, the FDPG editor and
    Glowing Bear all use. The operator is a centred band between blocks."""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    # No background fills and no borders: a filled full-width block reads as a
    # table row no matter what it means. The only structural marks are a left
    # rail and whitespace — „you want to see the data, not the lines around it".
    ramp = (["#8a3b2c", "#b06a5d", "#cfa097"] if excl
            else ["#2c5f8a", "#6d97c2", "#a8c2da"])
    rail = colors.HexColor(ramp[min(depth, 2)])

    out = []
    for i, card in enumerate(cards):
        if card.op:
            out.append(Spacer(1, 7))
            out.append(Paragraph(" ".join(escape(card.op)), ss["Op"]))
            out.append(Spacer(1, 7))
        elif i:
            out.append(Spacer(1, 6))
        body = [Paragraph(f'<b>{escape(card.label)}</b>&nbsp;&nbsp;{escape(card.title)}',
                          ss["Crit"])]
        for line in card.constraints:
            body.append(Paragraph(escape(line), ss["Cons"]))
        if not card.constraints and card.kind == "criterion":
            body.append(Paragraph(NO_CONSTRAINT, ss["Cons"]))
        if card.children:
            body.append(Spacer(1, 5))
            body += _card_flowables(card.children, ss, excl, depth + 1, width - 0.9)
        t = Table([[body]], colWidths=[width * cm])
        t.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, -1), 2.6 - 0.6 * min(depth, 2), rail),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        # no KeepTogether: nested cards live inside a table cell, where a
        # KeepTogether reports infinite height and blows up the layout
        out.append(t)
    return out


def render_pdf(q: Query, path: str | Path, today: date | None = None,
               layout: str = "cards") -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    ss = _styles()
    stamp = (today or date.today()).isoformat()
    story = [Paragraph(escape(f"Machbarkeitsanfrage: {q.display or q.source_name}"),
                       ss["Title"]),
             Paragraph(escape(f"Quelle: {q.source_name} — Erstellt: {stamp}"
                              + (f" — {version_line(q)}" if version_line(q) else "")),
                       ss["Italic"]),
             Spacer(1, 12)]

    story.append(Paragraph(_md_bold(cohort_rule(q)), ss["BodyText"]))
    story.append(Spacer(1, 6))
    for block, title in ((q.inclusion, "Einschlusskriterien"),
                         (q.exclusion, "Ausschlusskriterien")):
        if not block:
            continue
        story.append(Paragraph(title, ss["Heading2"]))
        story.append(Paragraph(_md_bold(block_intro(block)), ss["BodyText"]))
        story.append(Paragraph(escape(f"Formale Struktur: {block_formula(block)} — "
                                      f"{completeness_note(block)}"), ss["Cell"]))
        story.append(Spacer(1, 4))
        if layout == "table":
            story.append(_criteria_table(block, block_rows(block), ss))
        else:
            story += _card_flowables(criteria_cards(block), ss,
                                     block.kind == "exclusion")
        story.append(Spacer(1, 10))

    if q.attribute_groups:
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        story.append(Paragraph("Datenextraktion", ss["Heading2"]))
        data = [["Modul / Profil", "Filter", "Attribut"]]
        names = group_names(q)
        # One row per attribute: reportlab cannot split a single row across
        # pages, and groups with ~100 attributes would overflow otherwise.
        for g in q.attribute_groups:
            filters = group_filters(g)
            attrs = group_attributes(g, names) or ["—"]
            for i, attr in enumerate(attrs):
                data.append([
                    Paragraph(escape(group_title(g)), ss["Crit"]) if i == 0 else "",
                    Paragraph("<br/>".join(escape(x) for x in filters) or "—", ss["Cell"])
                    if i == 0 else "",
                    Paragraph(escape(attr), ss["Cell"]),
                ])
        t = Table(data, colWidths=[6 * cm, 6 * cm, 5.6 * cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
        if has_must_have(q):
            story.append(Spacer(1, 4))
            story.append(Paragraph(escape(MUSTHAVE_NOTE), ss["Cell"]))

    from reportlab.lib import colors as _c
    from reportlab.platypus import Table as _T, TableStyle as _TS
    story.append(Spacer(1, 10))
    story.append(Paragraph("Lesehilfe", ss["Heading2"]))
    legend = _T([["Notation", "Bedeutung"]]
                + [[Paragraph(escape(s), ss["Cell"]), Paragraph(escape(m), ss["Cell"])]
                   for s, m in LEGEND],
                colWidths=[5 * cm, 12.6 * cm], repeatRows=1)
    legend.setStyle(_TS([
        ("BACKGROUND", (0, 0), (-1, 0), _c.HexColor("#555555")),
        ("TEXTCOLOR", (0, 0), (-1, 0), _c.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, _c.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(legend)

    if q.unresolved:
        seen = set()
        items = []
        for c in q.unresolved:
            key = f"{c.system}|{c.code}"
            if key not in seen:
                seen.add(key)
                items.append(f"{c.code} ({c.system_label})")
        story.append(Spacer(1, 10))
        story.append(Paragraph(escape(
            "Für folgende Codes lag keine geprüfte deutsche Bezeichnung vor; angezeigt wird "
            "die im Export enthaltene Bezeichnung: " + ", ".join(items)), ss["Italic"]))

    SimpleDocTemplate(str(path), pagesize=A4,
                      leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                      topMargin=1.5 * cm, bottomMargin=1.5 * cm).build(story)
