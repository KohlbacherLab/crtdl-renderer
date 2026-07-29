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
"""CLI: crtdl-render FILE [-f md|docx|pdf|all] [-o OUTDIR] [--online]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .model import CrtdlParseError, parse_file
from .render import render_markdown
from .terminology import Resolver


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="crtdl-render",
        description="Rendert FDPG-CRTDL-Anfragen als Tabellen (MD/DOCX/PDF) "
                    "mit deutschen Code-Bezeichnungen.")
    ap.add_argument("file", type=Path, help="CRTDL- oder CCDL-JSON-Datei")
    ap.add_argument("-f", "--format", choices=["md", "docx", "pdf", "csv", "all"],
                    default="md",
                    help="csv erzeugt die Spalten des offiziellen FDPG-Exports "
                         "(DE_Einschlusskriterien / DE_Ausschlusskriterien / "
                         "DE_Merkmalselektion)")
    ap.add_argument("-o", "--outdir", type=Path, default=Path("."))
    ap.add_argument("--online", action="store_true",
                    help="fehlende deutsche Bezeichnungen per FHIR $lookup nachschlagen")
    ap.add_argument("--layout", choices=["cards", "table"], default="cards",
                    help="cards: verschachtelte Blöcke mit Akzentleiste (Standard); "
                         "table: flache Tabelle")
    ap.add_argument("--cache", type=Path, default=None,
                    help="zusätzlicher Terminologie-Cache (JSON), z. B. aus "
                         "`python -m crtdl_renderer.ontology elastic.zip -o cache.json`")
    args = ap.parse_args(argv)

    resolver = Resolver(cache_path=args.cache, online=args.online)
    try:
        query = parse_file(args.file, resolver)
    except (CrtdlParseError, FileNotFoundError) as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    resolver.save_cache()

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = args.file.stem
    formats = ["md", "docx", "pdf", "csv"] if args.format == "all" else [args.format]
    for fmt in formats:
        if fmt == "csv":
            from .render_csv import write_csv
            for path in write_csv(query, args.outdir, stem):
                print(path)
            continue
        out = args.outdir / f"{stem}.{fmt}"
        if fmt == "md":
            out.write_text(render_markdown(query, layout=args.layout), encoding="utf-8")
        elif fmt == "docx":
            from .render_docx import render_docx
            render_docx(query, out, layout=args.layout)
        elif fmt == "pdf":
            from .render_pdf import render_pdf
            render_pdf(query, out, layout=args.layout)
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
