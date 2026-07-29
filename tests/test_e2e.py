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
"""End-to-end checks: drive the installed command line over every bundled query
and inspect the artefacts it produces.

`python tests/test_e2e.py` — DOCX and PDF cases are skipped when the optional
dependencies are absent, so the suite still runs on a bare install.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crtdl_renderer.model import parse_file
from crtdl_renderer.render import leaf_labels

EXAMPLES = sorted((ROOT / "examples").rglob("*.json"))

try:
    import docx  # noqa: F401
    HAVE_DOCX = True
except ImportError:
    HAVE_DOCX = False
try:
    import reportlab  # noqa: F401
    HAVE_PDF = True
except ImportError:
    HAVE_PDF = False


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "crtdl_renderer.cli", *args],
                          cwd=ROOT, capture_output=True, text=True)


def test_cli_renders_every_example_in_every_available_format():
    formats = ["md", "csv"] + (["docx"] if HAVE_DOCX else []) + (["pdf"] if HAVE_PDF else [])
    with tempfile.TemporaryDirectory() as tmp:
        for src in EXAMPLES:
            for fmt in formats:
                r = _run(str(src), "-f", fmt, "-o", tmp)
                assert r.returncode == 0, f"{src.name} [{fmt}]: {r.stderr.strip()[:300]}"
        produced = list(Path(tmp).iterdir())
    assert len(produced) >= len(EXAMPLES), "expected at least one artefact per query"


def test_every_criterion_reaches_the_markdown():
    """No criterion may be silently dropped between JSON and document."""
    with tempfile.TemporaryDirectory() as tmp:
        for src in EXAMPLES:
            assert _run(str(src), "-f", "md", "-o", tmp).returncode == 0
            md = (Path(tmp) / f"{src.stem}.md").read_text(encoding="utf-8")
            q = parse_file(src)
            for block in (q.inclusion, q.exclusion):
                if not block:
                    continue
                for label in leaf_labels(block):
                    assert label in md, f"{src.name}: {label} missing from the document"
                for group in block.groups:
                    for crit in group.criteria:
                        assert crit.concepts[0].code in md, \
                            f"{src.name}: code {crit.concepts[0].code} missing"


def test_csv_round_trips_the_criteria():
    """Every criterion of a section appears as exactly one CSV row, labelled."""
    with tempfile.TemporaryDirectory() as tmp:
        for src in EXAMPLES:
            assert _run(str(src), "-f", "csv", "-o", tmp).returncode == 0
            q = parse_file(src)
            for block, name in ((q.inclusion, "DE_Einschlusskriterien"),
                                (q.exclusion, "DE_Ausschlusskriterien")):
                if not block:
                    continue
                path = Path(tmp) / f"{src.stem}_{name}.csv"
                assert path.exists(), f"{src.name}: {name}.csv not written"
                with path.open(encoding="utf-8-sig") as fh:
                    rows = list(csv.reader(fh, delimiter=";"))
                assert [r[-1] for r in rows[1:]] == leaf_labels(block), src.name


def test_both_layouts_carry_the_same_criteria():
    """`--layout table` is a presentation choice, not a different document."""
    src = ROOT / "examples" / "demo_hypertonie_diabetes.json"
    with tempfile.TemporaryDirectory() as tmp:
        out = {}
        for layout in ("cards", "table"):
            d = Path(tmp) / layout
            assert _run(str(src), "-f", "md", "--layout", layout, "-o", str(d)).returncode == 0
            out[layout] = (d / f"{src.stem}.md").read_text(encoding="utf-8")
    q = parse_file(src)
    for block in (q.inclusion, q.exclusion):
        for label in leaf_labels(block):
            assert label in out["cards"] and label in out["table"], label


def test_pdf_is_a_readable_pdf_with_extractable_text():
    if not HAVE_PDF:
        print("  (übersprungen: reportlab fehlt)")
        return
    try:
        import pypdf
    except ImportError:
        print("  (übersprungen: pypdf fehlt)")
        return
    src = ROOT / "examples" / "demo_hypertonie_diabetes.json"
    with tempfile.TemporaryDirectory() as tmp:
        assert _run(str(src), "-f", "pdf", "-o", tmp).returncode == 0
        pdf = Path(tmp) / f"{src.stem}.pdf"
        assert pdf.read_bytes().startswith(b"%PDF-"), "not a PDF"
        reader = pypdf.PdfReader(pdf)
        assert len(reader.pages) >= 1
        text = "\n".join(p.extract_text() for p in reader.pages)
    for expected in ("Einschlusskriterien", "Ausschlusskriterien", "Kodiersysteme",
                     "Lesehilfe", "E1", "A1"):
        assert expected in text, f"{expected!r} missing from the PDF text layer"


def test_docx_opens_and_contains_the_sections():
    if not HAVE_DOCX:
        print("  (übersprungen: python-docx fehlt)")
        return
    import docx as _docx
    src = ROOT / "examples" / "demo_hypertonie_diabetes.json"
    with tempfile.TemporaryDirectory() as tmp:
        assert _run(str(src), "-f", "docx", "-o", tmp).returncode == 0
        d = _docx.Document(Path(tmp) / f"{src.stem}.docx")
    text = "\n".join(p.text for p in d.paragraphs)
    for expected in ("Kohortendefinition", "Einschlusskriterien", "Ausschlusskriterien"):
        assert expected in text, f"{expected!r} missing from the DOCX"


def test_cli_rejects_a_non_query_file_with_a_message():
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "not-a-query.json"
        bad.write_text(json.dumps({"version": "1", "dataExtraction": {}}), encoding="utf-8")
        r = _run(str(bad), "-o", tmp)
    assert r.returncode != 0 and "inclusionCriteria" in r.stderr


def test_cli_reports_malformed_json_without_a_traceback():
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "broken.json"
        bad.write_text("{ not json", encoding="utf-8")
        r = _run(str(bad), "-o", tmp)
    assert r.returncode != 0
    assert "Traceback" not in r.stderr, "internal error leaked to the user"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} end-to-end checks passed")
