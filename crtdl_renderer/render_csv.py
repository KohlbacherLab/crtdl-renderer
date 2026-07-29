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
"""CSV export matching the FDPG's own committee-facing format.

`dataportal-backend` serves a ZIP of German CSVs from
`GET /api/v5/query/data/{id}/crtdl` — this is what a Use-&-Access-Committee
reviewer actually downloads. Reproducing the column set here means the rendered
document and the official artefact use one vocabulary.

Two documented defects of the original are fixed:
  * its first column is headed „Modul" but carries `context.display` — headed
    „Kontext" here;
  * „Verknüpfungsgruppe" means the AND-group in the inclusion file and the
    OR-group in the exclusion file, with nothing saying so — spelled out here.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .model import CriteriaBlock, Query
from .render import (
    _criterion_constraints,
    _de_date,
    _letter,
    block_prefix,
    group_filters,
    group_names,
    group_title,
)

# Column names verbatim from CsvMessages_de.properties, except column 1 (see above).
CRITERIA_HEAD = ["Kontext", "Anzeige", "System", "Code", "Version",
                 "Filter nach Attributen (Attributname: Filter)", "Filter nach Zeitraum",
                 "Verknüpfungsgruppe", "Nr."]
EXTRACTION_HEAD = ["ID", "Modul / Profil", "Merkmalname", "Felder",
                   "Filter nach Kodierung/Name", "Filter nach Zeitraum",
                   "Verknüpft mit (Spalte: ID)", "Nur extrahieren wenn referenziert",
                   "Erforderlich"]


def _row(c, label: str, gruppe: str) -> list[str]:
    tc = c.concepts[0]
    constraints = _criterion_constraints(c)
    attrs = "; ".join(x for x in constraints if not x.startswith("Zeitraum"))
    # keep the „(Überschneidung)" qualifier: an interval overlap suffices, and
    # dropping the word would read as containment
    zeit = "; ".join(x.split(":", 1)[-1].strip() + " (Überschneidung genügt)"
                     for x in constraints if x.startswith("Zeitraum"))
    return [c.context.display if c.context else "", tc.display, tc.system, tc.code,
            tc.version or "", attrs, zeit, gruppe, label]


def _criteria_rows(block: CriteriaBlock) -> list[list[str]]:
    p = block_prefix(block)
    # The rows of one group are joined by the block's INNER operator (OR for the
    # inclusion CNF, AND for the exclusion DNF); the groups themselves are joined
    # by the outer one. Naming only the outer operator here would tell the reader
    # the opposite of what the group means, and the CSV carries no other field
    # that could correct it.
    inner = "ODER" if block.kind == "inclusion" else "UND"
    outer = block.outer_op
    rows = []
    for gi, group in enumerate(block.groups, 1):
        gruppe = (f"{gi} (Kriterien {inner} verknüpft; Gruppen untereinander "
                  f"{outer} verknüpft)" if len(group.criteria) > 1
                  else f"{gi} (Einzelkriterium; Gruppen untereinander "
                       f"{outer} verknüpft)")
        for ci, c in enumerate(group.criteria, 1):
            label = f"{p}{gi}" if len(group.criteria) == 1 else f"{p}{gi}{_letter(ci)}"
            rows.append(_row(c, label, gruppe))
            # Referenced criteria get their own rows — the official flat CSV drops
            # them, which loses a branch of the query.
            refs = [af for af in c.attribute_filters if af.kind == "reference"]
            for r, af in enumerate(refs, 1):
                name = af.attribute.display if af.attribute else "Referenz"
                for k, rc in enumerate(af.ref_criteria, 1):
                    rows.append(_row(rc, f"{label}r{r}{_letter(k)}",
                                     f"{gi} → Referenz „{name}“ von {label} "
                                     f"(Kriterien ODER verknüpft)"))
    return rows


def write_csv(query: Query, outdir: Path, stem: str) -> list[Path]:
    written: list[Path] = []

    def dump(name: str, head: list[str], rows: list[list[str]]) -> None:
        path = outdir / f"{stem}_{name}.csv"
        # utf-8-sig + ';' so Excel opens it correctly on a German locale,
        # matching the FDPG export.
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
            w.writerow(head)
            w.writerows(rows)
        written.append(path)

    if query.inclusion:
        dump("DE_Einschlusskriterien", CRITERIA_HEAD, _criteria_rows(query.inclusion))
    if query.exclusion:
        dump("DE_Ausschlusskriterien", CRITERIA_HEAD, _criteria_rows(query.exclusion))
    if query.attribute_groups:
        names = group_names(query)
        rows = []
        for g in query.attribute_groups:
            rows.append([
                g.id, group_title(g), g.name or "",
                "; ".join(a.ref for a in g.attributes),
                "; ".join(group_filters(g)),
                "; ".join(f"{d.name}: {_de_date(d.start) or '…'} bis "
                          f"{_de_date(d.end) or '…'}" for d in g.date_filters),
                "; ".join(names.get(x, x) for a in g.attributes for x in a.linked_groups),
                "JA" if g.include_reference_only else "",
                "JA" if any(a.must_have for a in g.attributes) else "",
            ])
        dump("DE_Merkmalselektion", EXTRACTION_HEAD, rows)
    return written
