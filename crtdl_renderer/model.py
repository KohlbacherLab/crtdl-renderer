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
    unknown_filters: list[str] = field(default_factory=list)

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
            selected = vf.get("selectedConcepts")
            if not isinstance(selected, list) or not selected:
                raise CrtdlParseError(
                    "Ein Filter vom Typ „concept\u201c benötigt eine nicht-leere Liste "
                    "„selectedConcepts\u201c.")
            for c in selected:
                if not isinstance(c, dict):
                    raise CrtdlParseError(
                        f"selectedConcepts enthält kein Objekt, sondern "
                        f"{type(c).__name__}.")
            f.concepts = [self.concept(c) for c in selected]
        elif kind == "quantity-comparator":
            comparator, value = vf.get("comparator"), vf.get("value")
            if comparator not in COMPARATORS:
                raise CrtdlParseError(
                    f"Unbekannter Vergleichsoperator {comparator!r}; zulässig sind "
                    f"{', '.join(COMPARATORS)}.")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise CrtdlParseError(
                    f"quantity-comparator benötigt einen numerischen Wert, gefunden: "
                    f"{type(value).__name__}.")
            f.comparator, f.value = comparator, value
        elif kind == "quantity-range":
            lo, hi = vf.get("minValue"), vf.get("maxValue")
            for name, v in (("minValue", lo), ("maxValue", hi)):
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    raise CrtdlParseError(
                        f"quantity-range benötigt einen numerischen {name}, gefunden: "
                        f"{type(v).__name__}.")
            f.min_value, f.max_value = lo, hi
        # Any other type is kept and flagged in the output rather than rejected:
        # hiding a filter would understate the query, refusing the file helps nobody.
        if vf.get("unit"):
            u = vf["unit"]
            f.unit = Unit(code=u.get("code", ""), display=u.get("display", ""))
        return f

    def attribute_filter(self, af: dict[str, Any],
                         in_reference: bool = False) -> AttributeFilter:
        kind = af.get("type", "")
        attr = self.concept(af["attributeCode"]) if af.get("attributeCode") else None
        if kind == "reference":
            if in_reference:
                raise CrtdlParseError(
                    "Ein Referenzfilter darf laut CCDL keinen weiteren Referenzfilter "
                    "enthalten. Eine solche Verschachtelung ließe sich nicht in allen "
                    "Ausgabeformaten vollständig darstellen.")
            criteria = af.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                raise CrtdlParseError(
                    "Ein Referenzfilter benötigt eine nicht-leere Liste \u201ecriteria\u201c.")
            for c in criteria:
                if not isinstance(c, dict):
                    raise CrtdlParseError(
                        f"Referenzkriterium ist kein Objekt, gefunden: {type(c).__name__}.")
            crits = [self.criterion(c, in_reference=True) for c in criteria]
            return AttributeFilter(kind=kind, attribute=attr, ref_criteria=crits)
        return AttributeFilter(kind=kind, attribute=attr, value=self.value_filter(af))

    # -- criteria ----------------------------------------------------------
    def criterion(self, c: dict[str, Any], in_reference: bool = False) -> Criterion:
        ctx = self.concept(c["context"]) if isinstance(c.get("context"), dict) else None
        raw_codes = c.get("termCodes")
        if not isinstance(raw_codes, list) or not raw_codes:
            raise CrtdlParseError("Kriterium ohne termCodes.")
        for tc in raw_codes:
            if not isinstance(tc, dict):
                raise CrtdlParseError(
                    f"termCode ist kein Objekt, gefunden: {type(tc).__name__}.")
        concepts = [self.concept(tc) for tc in raw_codes]
        vf = None
        if c.get("valueFilter") is not None:
            if not isinstance(c["valueFilter"], dict):
                raise CrtdlParseError(
                    f"valueFilter muss ein Objekt sein, gefunden: "
                    f"{type(c['valueFilter']).__name__}.")
            vf = self.value_filter(c["valueFilter"])
        raw_afs = c.get("attributeFilters") or []
        if not isinstance(raw_afs, list):
            raise CrtdlParseError(
                f"attributeFilters muss eine Liste sein, gefunden: {type(raw_afs).__name__}.")
        for a in raw_afs:
            if not isinstance(a, dict):
                raise CrtdlParseError(
                    f"attributeFilter ist kein Objekt, gefunden: {type(a).__name__}.")
        afs = [self.attribute_filter(a, in_reference=in_reference) for a in raw_afs]
        tr = None
        if c.get("timeRestriction") is not None:
            t = c["timeRestriction"]
            if not isinstance(t, dict):
                raise CrtdlParseError(
                    f"timeRestriction muss ein Objekt sein, gefunden: "
                    f"{type(t).__name__}.")
            for key in ("afterDate", "beforeDate"):
                if key in t and t[key] is not None and not isinstance(t[key], str):
                    raise CrtdlParseError(
                        f"timeRestriction.{key} muss eine Zeichenkette sein, gefunden: "
                        f"{type(t[key]).__name__}.")
            if not (t.get("afterDate") or t.get("beforeDate")):
                raise CrtdlParseError(
                    "timeRestriction benötigt afterDate oder beforeDate; ohne beide wäre "
                    "die Einschränkung wirkungslos und würde im Dokument fehlen.")
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
                # An empty inner array is not a no-op: in the inclusion CNF it is an
                # empty disjunction (FALSE, so nobody matches), in the exclusion DNF an
                # empty conjunction (TRUE, so everybody is excluded). Dropping it would
                # present a cohort the query does not describe.
                raise CrtdlParseError(
                    f"{field}[{i}] ist leer. Eine leere Gruppe verändert die Bedeutung "
                    f"der Anfrage (Einschluss: niemand erfüllt sie; Ausschluss: alle "
                    f"werden ausgeschlossen) und wird nicht stillschweigend übergangen.")
            for j, c in enumerate(grp):
                if not isinstance(c, dict):
                    raise CrtdlParseError(
                        f"{field}[{i}][{j}] ist kein Kriterium-Objekt, gefunden: "
                        f"{type(c).__name__}.")
            groups.append(CriterionGroup(inner_op=inner_op,
                                         criteria=[self.criterion(c) for c in grp]))
        return CriteriaBlock(kind=kind, outer_op=outer_op, groups=groups)

    # -- data extraction ---------------------------------------------------
    @staticmethod
    def _flag(value: Any, name: str) -> bool:
        """Booleans only: the string "false" is truthy and would invert the flag."""
        if value is None:
            return False
        if not isinstance(value, bool):
            raise CrtdlParseError(
                f"{name} muss true oder false sein, gefunden: {type(value).__name__}.")
        return value

    def attribute_group(self, g: dict[str, Any]) -> AttributeGroup:
        tokens, dates, unknown = [], [], []
        for flt in g.get("filter", []):
            kind = flt.get("type")
            # An explicit type wins; only an absent one is inferred from the payload,
            # so a `date` filter carrying stray `codes` is not silently retyped.
            if kind == "date":
                dates.append(DateFilter(name=flt.get("name", ""),
                                        start=flt.get("start"), end=flt.get("end")))
                continue
            if kind == "token" or (not kind and flt.get("codes")):
                tokens.append(TokenFilter(name=flt.get("name", ""),
                                          codes=[self.concept(c) for c in flt.get("codes", [])]))
            elif not kind and (flt.get("start") or flt.get("end")):
                dates.append(DateFilter(name=flt.get("name", ""),
                                        start=flt.get("start"), end=flt.get("end")))
            else:
                unknown.append(f"{flt.get('name') or '?'} (Typ „{kind or '?'}“)")
        attrs = []
        for a in g.get("attributes", []):
            must = a.get("mustHave")
            if not isinstance(must, bool):
                # "false" is a non-empty string and would become True
                raise CrtdlParseError(
                    f"attributeRef {a.get('attributeRef')!r}: mustHave muss true oder "
                    f"false sein, gefunden: {type(must).__name__}.")
            linked = a.get("linkedGroups") or []
            if not isinstance(linked, list) or any(not isinstance(x, str) for x in linked):
                raise CrtdlParseError(
                    f"attributeRef {a.get('attributeRef')!r}: linkedGroups muss eine "
                    f"Liste von Gruppen-IDs sein.")
            attrs.append(Attribute(ref=a.get("attributeRef", ""), must_have=must,
                                   linked_groups=linked))
        return AttributeGroup(
            id=g.get("id", ""), name=g.get("name"), group_reference=g.get("groupReference", ""),
            include_reference_only=self._flag(g.get("includeReferenceOnly"),
                                              "includeReferenceOnly"),
            attributes=attrs, token_filters=tokens, date_filters=dates,
            unknown_filters=unknown,
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
                "Keine inclusionCriteria gefunden — weder auf oberster Ebene noch in "
                "cohortDefinition.")
        if not cohort["inclusionCriteria"]:
            raise CrtdlParseError(
                "inclusionCriteria ist leer; die CCDL verlangt mindestens eine Bedingung.")
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
