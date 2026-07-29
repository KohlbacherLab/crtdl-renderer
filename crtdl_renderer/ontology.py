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
"""Build a German display cache from an FDPG ontology `elastic.zip` release asset.

    python -m crtdl_renderer.ontology sources/ontology/elastic.zip -o cache.json

The asset (github.com/medizininformatik-initiative/fhir-ontology-generator/releases,
no authentication) holds the same displays the FDPG UI shows. Shards are
Elasticsearch bulk NDJSON: an action line, then a document line.

Display rule, copied from the portal's Display.translate():
`de` wins, but an empty `de` falls back to `original` — BfArM systems
(ICD-10-GM, OPS, ATC, Alpha-ID) are natively German and leave `de` empty.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

from .terminology import Resolver


def _german(display: dict) -> str:
    return (display.get("de") or display.get("original") or "").strip()


def build_cache(zip_path: str | Path) -> dict[str, str]:
    """Map `system|code[|version]` → German display for every ontology entry."""
    cache: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as z:
        shards = [n for n in z.namelist()
                  if n.endswith(".json") and "onto_es__" in n]
        for name in shards:
            with z.open(name) as fh:
                for line in fh:
                    line = line.strip()
                    if not line or b'"index"' in line[:20]:
                        continue  # bulk action line
                    try:
                        doc = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for tc, disp in _entries(doc):
                        text = _german(disp)
                        if not text:
                            continue
                        system = Resolver.canonical_system(tc.get("system", ""))
                        code = tc.get("code")
                        if not (system and code):
                            continue
                        key = f"{system}|{code}"
                        version = tc.get("version")
                        if key not in cache:
                            cache[key] = text
                        elif version and cache[key] != text:
                            # only versions that actually disagree need their own
                            # entry — the resolver falls back to the plain key
                            cache[f"{key}|{version}"] = text
    return cache


def _entries(doc: dict):
    """Yield (termCode, display) pairs from an ontology or codeable_concept doc."""
    disp = doc.get("display") or {}
    for tc in doc.get("termcodes") or []:
        yield tc, disp
    tc = doc.get("termcode")
    if isinstance(tc, dict):
        yield tc, disp
    elif isinstance(tc, str) and doc.get("terminology"):
        yield {"system": doc["terminology"], "code": tc}, disp


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="crtdl-ontology",
        description="Erzeugt einen Cache deutscher Bezeichnungen aus einer "
                    "FDPG-Ontologie (elastic.zip).")
    ap.add_argument("zipfile", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--merge", action="store_true",
                    help="bestehenden Cache ergänzen statt überschreiben "
                         "(kuratierte Einträge gewinnen)")
    args = ap.parse_args(argv)

    cache = build_cache(args.zipfile)
    if args.merge and args.out.exists():
        curated = json.loads(args.out.read_text(encoding="utf-8"))
        cache.update(curated)  # hand-checked entries win over bulk import
    args.out.write_text(
        json.dumps(cache, ensure_ascii=False, sort_keys=True, separators=(",\n", ":")),
        encoding="utf-8")
    print(f"{len(cache)} Einträge → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
