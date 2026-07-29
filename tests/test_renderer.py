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
"""Self-check: `python tests/test_renderer.py` (assert-based, no framework)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crtdl_renderer.model import CrtdlParseError, Parser, parse_file
from crtdl_renderer.render import (
    block_formula,
    block_intro,
    block_rows,
    cohort_rule,
    criteria_head,
    formula_labels,
    leaf_labels,
    render_markdown,
)
from crtdl_renderer.terminology import Resolver

EX = ROOT / "examples"


def _all_examples():
    """Own examples plus the redistributed upstream corpora."""
    return sorted(EX.rglob("*.json"))


def _q(inc, exc=None):
    data = {"version": "v", "inclusionCriteria": inc}
    if exc:
        data["exclusionCriteria"] = exc
    return Parser(Resolver()).parse(data, "test.json")


def _c(code):
    return {"context": {"code": "Diagnose", "system": "fdpg.mii.cds", "display": "Diagnose"},
            "termCodes": [{"code": code, "system": "http://fhir.de/CodeSystem/bfarm/icd-10-gm",
                           "display": f"Krankheit {code}"}]}


def test_cnf_dnf_operators():
    """Inclusion is CNF (outer AND / inner OR), exclusion is DNF (mirrored)."""
    q = _q([[_c("A")], [_c("B"), _c("C")]], [[_c("X")], [_c("Y"), _c("Z")]])
    assert q.inclusion.outer_op == "UND" and q.inclusion.groups[1].inner_op == "ODER"
    assert q.exclusion.outer_op == "ODER" and q.exclusion.groups[1].inner_op == "UND"
    # inclusion labels are E*, exclusion labels A* — separate namespaces
    assert block_formula(q.inclusion) == "E1 UND (E2a ODER E2b)"
    assert block_formula(q.exclusion) == "A1 ODER (A2a UND A2b)"


def test_grouping_is_unambiguous():
    """[[A,B],[C,D]] and [[A],[B,C,D]] must not render identically."""
    a = block_formula(_q([[_c("A"), _c("B")], [_c("C"), _c("D")]]).inclusion)
    b = block_formula(_q([[_c("A")], [_c("B"), _c("C"), _c("D")]]).inclusion)
    assert a == "(E1a ODER E1b) UND (E2a ODER E2b)"
    assert b == "E1 UND (E2a ODER E2b ODER E2c)"
    assert a != b


def test_labels_identify_their_group_without_indentation():
    """A row label must state its group membership on its own — indentation is
    lost to wrapping and page breaks."""
    rows = block_rows(_q([[_c("A")], [_c("B"), _c("C")]]).inclusion)
    assert [r.number for r in rows] == ["E1", "E2", "E2a", "E2b"]
    assert rows[1].is_header and "Mindestens eines" in rows[1].text
    # the inner operator appears on the row it governs, not in a separate column
    assert rows[3].text.startswith("oder ")


def test_formula_covers_every_leaf_exactly_once():
    """Salesforce's Actionable-List-Builder invariant, and the defence against
    PRESS's „orphan line" defect: a cross-check that silently omits a branch is
    worse than no cross-check."""
    for path in (EX / "upstream" / "mii-ccdl" / "ccdl-all-properties.json", EX / "demo_hypertonie_diabetes.json",
                 EX / "upstream" / "cctb" / "SpecimenSQTwoReferenceCriteria.json"):
        q = parse_file(path)
        for block in (q.inclusion, q.exclusion):
            if not block:
                continue
            leaves = leaf_labels(block)
            used = formula_labels(block)
            assert sorted(used) == sorted(leaves), (path.name, used, leaves)
            assert len(set(used)) == len(used), "label used twice"


def test_exclusion_rows_are_self_describing():
    """A reader landing mid-table after a page break must still see that these
    criteria EXCLUDE. The marker sits at block scope: an exclusion criterion is a
    positive condition, so negating the criterion text itself would invert it."""
    q = _q([[_c("A")]], [[_c("X")], [_c("Y"), _c("Z")]])
    rows = block_rows(q.exclusion)
    assert rows[0].text.endswith("→ Ausschluss")          # single-criterion block
    assert rows[1].is_header and "→ Ausschluss:" in rows[1].text  # group header
    # members carry no marker — alone they do not cause exclusion
    assert "Ausschluss" not in rows[2].text and "Ausschluss" not in rows[3].text
    # the repeated table header is the page-break-proof cue
    assert "AUSSCHLUSS" in criteria_head(q.exclusion)[1]
    assert "erfüllt sein" in criteria_head(q.inclusion)[1]


def test_exclusion_intro_states_the_negation():
    """The cohort-level NOT must survive a reader who only looks at one section."""
    q = _q([[_c("A")]], [[_c("X")], [_c("Y"), _c("Z")]])
    intro = block_intro(q.exclusion)
    assert "ausgeschlossen" in intro and "A1–A2" in intro
    assert "keine der Ausschlussbedingungen" in cohort_rule(q)


def test_indentation_reflects_hierarchy():
    rows = block_rows(_q([[_c("A")], [_c("B"), _c("C")]]).inclusion)
    assert [r.indent for r in rows] == [0, 0, 1, 1]


def test_resolver_layers_and_version_keys():
    r = Resolver()
    assert r.resolve("http://hl7.org/fhir/administrative-gender", "female", "Female") == \
        ("Weiblich", "cache")
    # https:// keys in the cache file must match http://-canonicalised lookups
    kbv = "https://fhir.kbv.de/CodeSystem/KBV_CS_SFHIR_ICD_DIAGNOSESICHERHEIT"
    assert r.resolve(kbv, "G", "gesicherte Diagnose") == ("Gesicherte Diagnose", "cache")
    assert r.resolve("http://example.org/x", "42", "Widget") == ("Widget", "embedded")
    assert r.resolve("http://example.org/x", "42", "") == ("42", "code")
    # version-specific entry wins, version-less entry is the fallback
    r.cache["http://s|c|2024"] = "Neu"
    r.cache["http://s|c"] = "Alt"
    assert r.resolve("http://s", "c", "", "2024")[0] == "Neu"
    assert r.resolve("http://s", "c", "", "2023")[0] == "Alt"


def test_system_canonicalisation():
    weird = "https://fhir.loinc.org/CodeSystem/$lookup?system=http://loinc.org&code=LL2191-6"
    assert Resolver.canonical_system(weird) == "http://loinc.org"
    assert Resolver.system_label(weird) == "LOINC"
    # a percent-encoded https inner system must also normalise
    nested = ("https://tx.example/CodeSystem/$lookup?system=https%3A%2F%2Ffhir.kbv.de"
              "%2FCodeSystem%2FKBV_CS_SFHIR_ICD_DIAGNOSESICHERHEIT&code=G")
    assert Resolver().resolve(nested, "G", "Confirmed") == ("Gesicherte Diagnose", "cache")
    assert Resolver.system_label("http://fhir.de/CodeSystem/dimdi/icd-10-gm") == "ICD-10-GM"
    assert Resolver.system_label("") == "ohne System"


def test_rejects_file_without_inclusion_criteria():
    try:
        Parser(Resolver()).parse({"version": "v", "dataExtraction": {}}, "x.json")
    except CrtdlParseError:
        return
    raise AssertionError("expected CrtdlParseError")


def test_markdown_deterministic_and_escaped():
    q = parse_file(EX / "demo_hypertonie_diabetes.json")
    md1 = render_markdown(q, today=date(2026, 1, 1))
    md2 = render_markdown(q, today=date(2026, 1, 1))
    assert md1 == md2
    assert "**Erstellt:** 2026-01-01" in md1
    assert "keine der Ausschlussbedingungen" in md1  # negation stated in plain language
    # the code-system version is part of the label — ICD-10-GM codes shift between releases
    assert "Essentielle (primäre) Hypertonie (I10, ICD-10-GM 2024)" in md1
    # curated seed wins over the English display embedded in the export
    assert "[Person]" in md1  # context "Patient" → German "Person"
    # every table row must have exactly as many unescaped pipes as its header
    for line in md1.splitlines():
        if line.startswith("|"):
            assert line.count("|") - line.count("\\|") in (3, 4, 5), line


def test_degenerate_inputs_render_without_crashing():
    """Valid-but-unusual shapes must produce output, not exceptions."""
    bare = {"termCodes": [{"code": "X", "system": "", "display": ""}]}
    cases = {
        "kein context": [[bare]],
        "Menge ohne Einheit": [[{**bare, "valueFilter": {
            "type": "quantity-comparator", "comparator": "ne", "value": 3.5}}]],
        "Bereich ohne Einheit": [[{**bare, "valueFilter": {
            "type": "quantity-range", "minValue": 1, "maxValue": 2}}]],
        "verschachtelte Referenz": [[{**bare, "attributeFilters": [{
            "type": "reference",
            "attributeCode": {"code": "r", "system": "s", "display": "Ref"},
            "criteria": [bare]}]}]],
    }
    for name, inc in cases.items():
        md = render_markdown(_q(inc), today=date(2026, 1, 1))
        assert "Einschlusskriterien" in md, name

    # an unknown filter type is surfaced, never silently dropped or fatal
    md = render_markdown(_q([[{**bare, "valueFilter": {"type": "bogus"}}]]),
                         today=date(2026, 1, 1))
    assert "unbekannter Filtertyp" in md


def test_uri_version_is_shortened_in_label():
    q = _q([[{"context": {"code": "Specimen", "system": "fdpg.mii.cds", "display": "Bioprobe"},
              "termCodes": [{"code": "119364003", "system": "http://snomed.info/sct",
                             "version": "http://snomed.info/sct/900000000000207008/version/20220930",
                             "display": "Serumprobe"}]}]])
    assert q.inclusion.groups[0].criteria[0].concepts[0].label == \
        "Serumprobe (119364003, SNOMED CT 20220930)"


def test_multiple_reference_filters_keep_and_semantics():
    """attributeFilters are AND-joined, so a second reference block must say so
    and carry its own number prefix."""
    def ref(attr, code):
        return {"type": "reference",
                "attributeCode": {"code": attr, "system": "mii.abide", "display": attr},
                "criteria": [_c(code)]}
    crit = {**_c("M"), "attributeFilters": [ref("a", "X"), ref("b", "Y")]}
    rows = block_rows(_q([[crit]]).inclusion)
    assert [r.number for r in rows] == ["E1", "E1r1", "E1r1a", "E1r2", "E1r2a"]
    # the second reference block states that it applies in addition to the first
    assert "zusätzlich (UND)" in rows[3].text
    assert rows[1].is_header and rows[3].is_header


def test_huge_integer_quantity_does_not_crash():
    huge = int("1" + "0" * 400)
    md = render_markdown(_q([[{**_c("A"), "valueFilter": {
        "type": "quantity-comparator", "comparator": "gt", "value": huge}}]]),
        today=date(2026, 1, 1))
    assert str(huge) in md


def test_parser_reuse_does_not_leak_unresolved_codes():
    p = Parser(Resolver())
    foreign = {"context": {"code": "Diagnose", "system": "fdpg.mii.cds", "display": "Diagnose"},
               "termCodes": [{"code": "OLD", "system": "http://unknown", "display": "Alt"}]}
    first = p.parse({"version": "v", "inclusionCriteria": [[foreign]]}, "a.json")
    second = p.parse({"version": "v", "inclusionCriteria": [[_c("NEU")]]}, "b.json")
    assert [c.code for c in first.unresolved] == ["OLD"]
    assert second.unresolved == []


def test_ontology_import_prefers_de_but_falls_back_to_original():
    """BfArM systems carry German in `original` with an empty `de` — the rule
    is `de || original`, so reading only `de` would drop ICD-10-GM/OPS/ATC."""
    import io
    import json as _json
    import zipfile

    from crtdl_renderer.ontology import build_cache

    docs = [
        {"terminology": "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "termcode": "I10",
         "display": {"original": "Essentielle (primäre) Hypertonie", "de": "", "en": ""}},
        {"termcodes": [{"system": "http://snomed.info/sct", "code": "73211009",
                        "version": "2025"}],
         "display": {"original": "Diabetes mellitus", "de": "Diabetes mellitus (DE)",
                     "en": "Diabetes mellitus"}},
        {"termcodes": [{"system": "https://example.org/x/", "code": "1"}],
         "display": {"original": "", "de": "", "en": "only english"}},
    ]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        lines = []
        for d in docs:
            lines.append(_json.dumps({"index": {"_index": "ontology", "_id": "x"}}))
            lines.append(_json.dumps(d, ensure_ascii=False))
        z.writestr("elastic/onto_es__ontology_0.json", "\n".join(lines))
    buf.seek(0)

    cache = build_cache(buf)
    assert cache["http://fhir.de/CodeSystem/bfarm/icd-10-gm|I10"] == \
        "Essentielle (primäre) Hypertonie"
    assert cache["http://snomed.info/sct|73211009"] == "Diabetes mellitus (DE)"
    assert "http://snomed.info/sct|73211009|2025" not in cache  # no redundant version key
    assert "http://example.org/x|1" not in cache  # neither de nor original → skipped


def test_csv_export_covers_every_criterion():
    """The official FDPG CSV is flat and drops reference sub-criteria; ours must
    carry every leaf the document shows, with the same labels."""
    import csv as _csv
    import tempfile

    from crtdl_renderer.render_csv import write_csv

    q = parse_file(EX / "upstream" / "mii-ccdl" / "ccdl-all-properties.json")
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_csv(q, Path(tmp), "t")
        inc = next(p for p in paths if "Einschluss" in p.name)
        with inc.open(encoding="utf-8-sig") as fh:
            rows = list(_csv.reader(fh, delimiter=";"))
    assert rows[0][0] == "Kontext"  # not the original's mislabelled „Modul"
    labels = [r[-1] for r in rows[1:]]
    assert labels == leaf_labels(q.inclusion)


def test_csv_names_the_operator_that_joins_the_rows():
    """The rows of one group are joined by the block's INNER operator — OR for the
    inclusion CNF, AND for the exclusion DNF. Naming the outer operator here would
    tell the reader the opposite, and the CSV has no other field to correct it."""
    from crtdl_renderer.render_csv import _criteria_rows

    q = _q([[_c("A"), _c("B")]], [[_c("X"), _c("Y")]])
    inc = _criteria_rows(q.inclusion)[0][-2]
    exc = _criteria_rows(q.exclusion)[0][-2]
    assert "Kriterien ODER verknüpft" in inc and "Gruppen untereinander UND" in inc
    assert "Kriterien UND verknüpft" in exc and "Gruppen untereinander ODER" in exc


def test_csv_keeps_the_interval_overlap_qualifier():
    from crtdl_renderer.render_csv import _criteria_rows

    crit = {**_c("A"), "timeRestriction": {"afterDate": "2020-01-01",
                                           "beforeDate": "2020-12-31"}}
    row = _criteria_rows(_q([[crit]]).inclusion)[0]
    assert "Überschneidung" in row[6], row[6]


def test_unit_comes_from_the_ucum_code_not_the_display():
    """`unit.display` is free text nothing validates. A file whose code says
    mg/dL while its display says g/dL is out by a factor of 1000; printing the
    display would silently misstate a laboratory threshold."""
    def lab(code, disp):
        return {"context": {"code": "Laboruntersuchung", "system": "fdpg.mii.cds",
                            "display": "Labor"},
                "termCodes": [{"code": "2160-0", "system": "http://loinc.org",
                               "display": "Kreatinin"}],
                "valueFilter": {"type": "quantity-range", "minValue": 3, "maxValue": 15,
                                "unit": {"code": code, "display": disp}}}

    def lines(code, disp):
        return block_rows(_q([[lab(code, disp)]]).inclusion)[0].constraints

    # mg/dl vs mg/dL is the same unit in UCUM (L and l both mean litre)
    assert lines("mg/dL", "mg/dl") == ["Wert: 3 bis 15 mg/dL"]
    # a contradicting display must not win, and must be reported
    contradiction = lines("mg/dL", "g/dL")
    assert contradiction[0] == "Wert: 3 bis 15 mg/dL"
    assert "widersprüchlich" in contradiction[1] and "g/dL" in contradiction[1]
    # a cryptic UCUM code still gets its curated German rendering
    assert lines("Cel", "") == ["Wert: 3 bis 15 °C"]


def test_malformed_structure_raises_a_readable_error():
    """Wrong-typed JSON must produce an actionable message, not a traceback."""
    cases = {
        "top-level array": [],
        "criteria not a list": {"version": "v", "inclusionCriteria": {"a": 1}},
        "groups not nested": {"version": "v", "inclusionCriteria": [{"code": "x"}]},
        "criterion is a string": {"version": "v", "inclusionCriteria": [["x"]]},
        # an empty inner array is FALSE in the inclusion CNF — dropping it would
        # present a cohort the query does not describe
        "empty group": {"version": "v", "inclusionCriteria": [[], [_c("A")]]},
        "no criteria at all": {"version": "v", "inclusionCriteria": []},
        "time restriction without bounds": {"version": "v", "inclusionCriteria": [
            [{**_c("A"), "timeRestriction": {}}]]},
        "unknown comparator": {"version": "v", "inclusionCriteria": [[{
            **_c("A"), "valueFilter": {"type": "quantity-comparator",
                                       "comparator": "gte", "value": 5}}]]},
        "comparator without a value": {"version": "v", "inclusionCriteria": [[{
            **_c("A"), "valueFilter": {"type": "quantity-comparator",
                                       "comparator": "gt"}}]]},
        "empty selectedConcepts": {"version": "v", "inclusionCriteria": [[{
            **_c("A"), "valueFilter": {"type": "concept", "selectedConcepts": []}}]]},
        "timeRestriction not an object": {"version": "v", "inclusionCriteria": [[{
            **_c("A"), "timeRestriction": "2024-01-01"}]]},
        "afterDate not a string": {"version": "v", "inclusionCriteria": [[{
            **_c("A"), "timeRestriction": {"afterDate": 1}}]]},
        # "false" is a non-empty string: bool() would turn it into True
        "mustHave as a string": {"version": "v", "inclusionCriteria": [[_c("A")]],
            "dataExtraction": {"attributeGroups": [{"id": "g", "groupReference": "p",
                "attributes": [{"attributeRef": "a", "mustHave": "false"}]}]}},
        "linkedGroups as a string": {"version": "v", "inclusionCriteria": [[_c("A")]],
            "dataExtraction": {"attributeGroups": [{"id": "g", "groupReference": "p",
                "attributes": [{"attributeRef": "a", "mustHave": False,
                                "linkedGroups": "xy"}]}]}},
        "nested reference filter": {"version": "v", "inclusionCriteria": [[{
            **_c("A"), "attributeFilters": [{
                "type": "reference",
                "attributeCode": {"code": "r", "system": "s", "display": "R"},
                "criteria": [{**_c("B"), "attributeFilters": [{
                    "type": "reference",
                    "attributeCode": {"code": "r2", "system": "s", "display": "R2"},
                    "criteria": [_c("C")]}]}]}]}]]},
    }
    for name, bad in cases.items():
        try:
            Parser(Resolver()).parse(bad, "t.json")
        except CrtdlParseError:
            continue
        except Exception as exc:
            raise AssertionError(f"{name}: {type(exc).__name__} instead of "
                                 f"CrtdlParseError") from exc
        raise AssertionError(f"{name}: no error raised")


def test_online_lookups_never_touch_the_packaged_cache():
    """The shipped curated cache is content, not scratch space: without an
    explicit --cache there is nowhere to persist, so nothing is written."""
    from crtdl_renderer.terminology import DEFAULT_CACHE

    before = DEFAULT_CACHE.read_bytes()
    r = Resolver()
    assert r.cache_path is None
    r.cache["http://example.org|x"] = "Neu"
    r._dirty = True
    r.save_cache()
    assert DEFAULT_CACHE.read_bytes() == before, "packaged cache was modified"


def test_all_examples_render():
    for f in _all_examples():
        md = render_markdown(parse_file(f), today=date(2026, 1, 1))
        assert "Einschlusskriterien" in md, f.name


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed")
