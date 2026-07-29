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
"""Intermediate representation and parser for CRTDL/CCDL query files.

Boolean semantics (CCDL spec, documentation/Documentation.md):
  inclusionCriteria  : CNF — outer array joined AND, inner array joined OR
  exclusionCriteria  : DNF — outer array joined OR,  inner array joined AND
  cohort = inclusion AND NOT exclusion
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .terminology import Resolver

COMPARATORS = {"gt": ">", "ge": "≥", "lt": "<", "le": "≤", "eq": "=", "ne": "≠"}


class CrtdlParseError(Exception):
    pass


@dataclass
class Concept:
    """A coded concept with its resolved German display."""
    code: str
    system: str
    version: str | None
    raw_display: str
    display: str          # resolved (German where available)
    system_label: str     # short system name for parentheses
    resolution: str       # 'cache' | 'embedded' | 'code'

    @property
    def label(self) -> str:
        """`<display> (<code>, <system> <version>)` — the required rendering form.

        The version belongs in the label: ICD-10-GM/OPS codes are re-used with
        different meanings across annual releases.
        """
        # SNOMED versions are URIs (…/sct/11000274103/version/20220930) — show the
        # last segment only, otherwise the label is mostly boilerplate.
        version = self.version.rsplit("/", 1)[-1] if self.version else None
        system = f"{self.system_label} {version}" if version else self.system_label
        if self.display and self.display != self.code:
            return f"{self.display} ({self.code}, {system})"
        return f"{self.code} ({system})"


@dataclass
class Unit:
    code: str
    display: str

    @property
    def label(self) -> str:
        return self.display or self.code


@dataclass
class ValueFilter:
    kind: str  # 'concept' | 'quantity-comparator' | 'quantity-range'
    concepts: list[Concept] = field(default_factory=list)  # OR-joined
    comparator: str | None = None
    value: float | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: Unit | None = None


@dataclass
class TimeRestriction:
    after: str | None
    before: str | None


@dataclass
class AttributeFilter:
    kind: str  # value-filter kinds + 'reference'
    attribute: Concept | None
    value: ValueFilter | None = None            # for non-reference kinds
    ref_criteria: list[Criterion] = field(default_factory=list)  # for 'reference'


@dataclass
class Criterion:
    context: Concept | None
    concepts: list[Concept]                     # termCodes (synonyms for one concept)
    value_filter: ValueFilter | None = None
    attribute_filters: list[AttributeFilter] = field(default_factory=list)  # AND-joined
    time_restriction: TimeRestriction | None = None

    @property
    def is_consent(self) -> bool:
        return bool(self.context and self.context.code == "Einwilligung")


@dataclass
class CriterionGroup:
    inner_op: str  # 'ODER' (inclusion) | 'UND' (exclusion)
    criteria: list[Criterion]


@dataclass
class CriteriaBlock:
    kind: str      # 'inclusion' | 'exclusion'
    outer_op: str  # 'UND' | 'ODER'
    groups: list[CriterionGroup]


@dataclass
class TokenFilter:
    name: str
    codes: list[Concept]  # OR-joined


@dataclass
class DateFilter:
    name: str
    start: str | None
    end: str | None


@dataclass
class Attribute:
    ref: str
    must_have: bool
    linked_groups: list[str] = field(default_factory=list)


@dataclass
class AttributeGroup:
    id: str
    name: str | None
    group_reference: str
    include_reference_only: bool
    attributes: list[Attribute]
    token_filters: list[TokenFilter]
    date_filters: list[DateFilter]

    @property
    def module_label(self) -> str:
        """German module name derived from the MII KDS profile URL."""
        return _module_label(self.group_reference)


@dataclass
class Query:
    source_name: str
    display: str
    version: str | None          # cohortDefinition (CCDL) version
    crtdl_version: str | None    # CRTDL wrapper version, if the file has one
    inclusion: CriteriaBlock | None
    exclusion: CriteriaBlock | None
    attribute_groups: list[AttributeGroup]
    unresolved: list[Concept] = field(default_factory=list)  # no German display found


_MODULE_LABELS = {
    "modul-labor": "Labor", "modul-person": "Person", "modul-diagnose": "Diagnose",
    "modul-prozedur": "Prozedur", "modul-fall": "Fall", "modul-medikation": "Medikation",
    "modul-consent": "Einwilligung", "modul-biobank": "Biobank",
}


def _module_label(url: str) -> str:
    for key, label in _MODULE_LABELS.items():
        if key in url:
            profile = url.rsplit("/", 1)[-1]
            return f"{label} — {profile}"
    return url.rsplit("/", 1)[-1] or url


class Parser:
    def __init__(self, resolver: Resolver | None = None):
        self.resolver = resolver or Resolver()
        self.unresolved: list[Concept] = []

    # -- concepts ----------------------------------------------------------
    def concept(self, tc: dict[str, Any]) -> Concept:
        code = str(tc.get("code", ""))
        system = tc.get("system", "") or ""
        raw_display = tc.get("display", "") or ""
        version = tc.get("version") or None
        display, source = self.resolver.resolve(system, code, raw_display, version)
        c = Concept(
            code=code, system=system, version=version,
            raw_display=raw_display, display=display,
            system_label=self.resolver.system_label(system), resolution=source,
        )
        # German display is only guaranteed for cache hits and natively German
        # code systems; everything else is shown as-is and flagged in a footnote.
        if source != "cache" and not self.resolver.is_german_system(system):
            self.unresolved.append(c)
        return c

    # -- filters -----------------------------------------------------------
    def value_filter(self, vf: dict[str, Any]) -> ValueFilter:
        kind = vf.get("type", "")
        f = ValueFilter(kind=kind)
        if kind == "concept":
            f.concepts = [self.concept(c) for c in vf.get("selectedConcepts", [])]
        elif kind == "quantity-comparator":
            f.comparator = vf.get("comparator")
            f.value = vf.get("value")
        elif kind == "quantity-range":
            f.min_value = vf.get("minValue")
            f.max_value = vf.get("maxValue")
        # Any other type is kept and flagged in the output rather than rejected:
        # hiding a filter would understate the query, refusing the file helps nobody.
        if vf.get("unit"):
            u = vf["unit"]
            f.unit = Unit(code=u.get("code", ""), display=u.get("display", ""))
        return f

    def attribute_filter(self, af: dict[str, Any]) -> AttributeFilter:
        kind = af.get("type", "")
        attr = self.concept(af["attributeCode"]) if af.get("attributeCode") else None
        if kind == "reference":
            crits = [self.criterion(c) for c in af.get("criteria", [])]
            return AttributeFilter(kind=kind, attribute=attr, ref_criteria=crits)
        return AttributeFilter(kind=kind, attribute=attr, value=self.value_filter(af))

    # -- criteria ----------------------------------------------------------
    def criterion(self, c: dict[str, Any]) -> Criterion:
        ctx = self.concept(c["context"]) if c.get("context") else None
        concepts = [self.concept(tc) for tc in c.get("termCodes", [])]
        if not concepts:
            raise CrtdlParseError("Kriterium ohne termCodes")
        vf = self.value_filter(c["valueFilter"]) if c.get("valueFilter") else None
        afs = [self.attribute_filter(a) for a in c.get("attributeFilters", [])]
        tr = None
        if c.get("timeRestriction"):
            t = c["timeRestriction"]
            tr = TimeRestriction(after=t.get("afterDate"), before=t.get("beforeDate"))
        return Criterion(context=ctx, concepts=concepts, value_filter=vf,
                         attribute_filters=afs, time_restriction=tr)

    def block(self, kind: str, groups_json) -> CriteriaBlock:
        outer_op, inner_op = ("UND", "ODER") if kind == "inclusion" else ("ODER", "UND")
        field = "inclusionCriteria" if kind == "inclusion" else "exclusionCriteria"
        if not isinstance(groups_json, list):
            raise CrtdlParseError(
                f"{field} muss eine Liste von Listen sein, gefunden: "
                f"{type(groups_json).__name__}.")
        groups = []
        for i, grp in enumerate(groups_json):
            if not isinstance(grp, list):
                raise CrtdlParseError(
                    f"{field}[{i}] muss eine Liste von Kriterien sein, gefunden: "
                    f"{type(grp).__name__}. Die äußere Liste enthält Gruppen, "
                    f"die innere die Kriterien.")
            if not grp:
                continue
            for j, c in enumerate(grp):
                if not isinstance(c, dict):
                    raise CrtdlParseError(
                        f"{field}[{i}][{j}] ist kein Kriterium-Objekt, gefunden: "
                        f"{type(c).__name__}.")
            groups.append(CriterionGroup(inner_op=inner_op,
                                         criteria=[self.criterion(c) for c in grp]))
        return CriteriaBlock(kind=kind, outer_op=outer_op, groups=groups)

    # -- data extraction ---------------------------------------------------
    def attribute_group(self, g: dict[str, Any]) -> AttributeGroup:
        tokens, dates = [], []
        for flt in g.get("filter", []):
            kind = flt.get("type")
            # The CRTDL schema allows any string as filter type; classify by the
            # fields actually present rather than trusting `type` alone.
            if kind == "token" or flt.get("codes"):
                tokens.append(TokenFilter(name=flt.get("name", ""),
                                          codes=[self.concept(c) for c in flt.get("codes", [])]))
            elif kind == "date" or flt.get("start") or flt.get("end"):
                dates.append(DateFilter(name=flt.get("name", ""),
                                        start=flt.get("start"), end=flt.get("end")))
        attrs = [Attribute(ref=a.get("attributeRef", ""), must_have=bool(a.get("mustHave")),
                           linked_groups=a.get("linkedGroups", []) or [])
                 for a in g.get("attributes", [])]
        return AttributeGroup(
            id=g.get("id", ""), name=g.get("name"), group_reference=g.get("groupReference", ""),
            include_reference_only=bool(g.get("includeReferenceOnly")),
            attributes=attrs, token_filters=tokens, date_filters=dates,
        )

    # -- entry point -------------------------------------------------------
    def parse(self, data: dict[str, Any], source_name: str = "") -> Query:
        if not isinstance(data, dict):
            raise CrtdlParseError(
                f"Die Datei enthält kein JSON-Objekt, sondern {type(data).__name__}.")
        cohort = data.get("cohortDefinition") or data
        if not isinstance(cohort, dict):
            raise CrtdlParseError(
                f"cohortDefinition muss ein Objekt sein, gefunden: {type(cohort).__name__}.")
        if "inclusionCriteria" not in cohort:
            raise CrtdlParseError(
                "Keine inclusionCriteria gefunden — weder auf oberster Ebene noch in cohortDefinition.")
        # dataExtraction may sit beside cohortDefinition (schema) or inside it (README example)
        extraction = data.get("dataExtraction") or cohort.get("dataExtraction") or {}
        inclusion = self.block("inclusion", cohort["inclusionCriteria"])
        exclusion = None
        if cohort.get("exclusionCriteria"):
            exclusion = self.block("exclusion", cohort["exclusionCriteria"])
        groups = [self.attribute_group(g) for g in extraction.get("attributeGroups", [])]
        crtdl_version = data.get("version") if cohort is not data else None
        query = Query(
            source_name=source_name,
            display=data.get("display") or cohort.get("display") or "",
            version=cohort.get("version"), crtdl_version=crtdl_version,
            inclusion=inclusion, exclusion=exclusion, attribute_groups=groups,
            unresolved=list(self.unresolved),  # snapshot: a Parser may be reused
        )
        self.unresolved.clear()
        return query


def parse_file(path: str | Path, resolver: Resolver | None = None) -> Query:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CrtdlParseError(f"Ungültiges JSON in {p.name}: {e}") from e
    return Parser(resolver).parse(data, source_name=p.name)
