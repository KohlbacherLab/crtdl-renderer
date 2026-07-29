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
"""Layered German display-name resolution for coded concepts.

Order: local cache file -> display embedded in the query -> the bare code.
Optional online mode fills cache misses via FHIR CodeSystem/$lookup
(displayLanguage=de-DE) and persists them back into the cache file.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_CACHE = Path(__file__).with_name("terminology_de.json")

SYSTEM_LABELS = {
    "http://fhir.de/CodeSystem/bfarm/icd-10-gm": "ICD-10-GM",
    "http://fhir.de/CodeSystem/dimdi/icd-10-gm": "ICD-10-GM",
    "http://fhir.de/CodeSystem/bfarm/ops": "OPS",
    "http://fhir.de/CodeSystem/dimdi/ops": "OPS",
    "http://fhir.de/CodeSystem/bfarm/atc": "ATC",
    "http://fhir.de/CodeSystem/dimdi/atc": "ATC",
    "http://loinc.org": "LOINC",
    "http://snomed.info/sct": "SNOMED CT",
    "http://unitsofmeasure.org": "UCUM",
    "http://hl7.org/fhir/administrative-gender": "AdministrativeGender",
    "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3": "MII-Consent",
    "fdpg.mii.cds": "FDPG",
    "http://terminology.hl7.org/CodeSystem/icd-o-3": "ICD-O-3",
    "icd-o-3": "ICD-O-3",
}

# Systems whose official displays are German already — embedded displays trustworthy.
GERMAN_NATIVE_SYSTEMS = {
    "http://fhir.de/CodeSystem/bfarm/icd-10-gm", "http://fhir.de/CodeSystem/dimdi/icd-10-gm",
    "http://fhir.de/CodeSystem/bfarm/ops", "http://fhir.de/CodeSystem/dimdi/ops",
    "http://fhir.de/CodeSystem/bfarm/atc", "http://fhir.de/CodeSystem/dimdi/atc",
    "urn:oid:2.16.840.1.113883.3.1937.777.24.5.3", "fdpg.mii.cds",
}


class Resolver:
    def __init__(self, cache_path: str | Path | None = None,
                 online: bool = False,
                 tx_base: str = "https://tx.fhir.org/r4"):
        """`cache_path` is an *additional* cache (e.g. a bulk FDPG-ontology
        import via `python -m crtdl_renderer.ontology`); the packaged curated
        entries are layered on top of it and win on conflict."""
        self.cache_path = DEFAULT_CACHE
        self.online = online
        self.tx_base = tx_base
        self._dirty = False
        self.cache: dict[str, str] = {}
        for path in ([cache_path] if cache_path else []) + [DEFAULT_CACHE]:
            try:
                raw = json.loads(Path(path).read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            # keys are canonicalised on load so a cache written with e.g.
            # `https://…` still matches a lookup canonicalised to `http://…`
            for key, value in raw.items():
                system, _, rest = key.partition("|")
                self.cache[f"{self.canonical_system(system)}|{rest}"] = value

    @classmethod
    def canonical_system(cls, system: str) -> str:
        """Normalise system URI variants so cache lookups don't miss."""
        s = (system or "").strip().rstrip("/")
        if s.startswith("https://"):
            s = "http://" + s[len("https://"):]
        # FDPG exports occasionally put a whole $lookup URL in `system`
        if "$lookup" in s and "system=" in s:
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(s).query)
            if q.get("system"):
                # parse_qs already percent-decodes; re-canonicalise the inner URI
                return cls.canonical_system(q["system"][0])
        return s

    @classmethod
    def system_label(cls, system: str) -> str:
        s = cls.canonical_system(system)
        if s in SYSTEM_LABELS:
            return SYSTEM_LABELS[s]
        if not s:
            return "ohne System"
        if s.startswith("urn:oid:"):
            return f"OID {s[len('urn:oid:'):]}"
        return s.rsplit("/", 1)[-1] or s

    @classmethod
    def is_german_system(cls, system: str) -> bool:
        return cls.canonical_system(system) in GERMAN_NATIVE_SYSTEMS

    def resolve(self, system: str, code: str, embedded_display: str,
                version: str | None = None) -> tuple[str, str]:
        """Return (display, source) with source in {'cache', 'embedded', 'code'}.

        Cache keys are version-aware (`system|code|version`) so that e.g. two
        ICD-10-GM releases cannot overwrite each other; a version-less entry
        acts as the fallback for any version.
        """
        sys_c = self.canonical_system(system)
        keys = [f"{sys_c}|{code}|{version}"] if version else []
        keys.append(f"{sys_c}|{code}")
        for key in keys:
            if key in self.cache:
                return self.cache[key], "cache"
        if self.online:
            hit = self._lookup_online(sys_c, code, version)
            if hit:
                self.cache[keys[0]] = hit
                self._dirty = True
                return hit, "cache"
        if embedded_display:
            return embedded_display, "embedded"
        return code, "code"

    def _lookup_online(self, system: str, code: str,
                       version: str | None = None) -> str | None:
        if not system.startswith(("http://", "https://", "urn:")):
            return None
        query = {"system": system, "code": code, "displayLanguage": "de-DE"}
        if version:
            query["version"] = version
        params = urllib.parse.urlencode(query)
        url = f"{self.tx_base}/CodeSystem/$lookup?{params}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/fhir+json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
        except Exception:
            return None
        display = None
        for p in data.get("parameter", []):
            if p.get("name") == "display":
                display = p.get("valueString")
            if (p.get("name") == "designation"):
                lang = use = value = None
                for part in p.get("part", []):
                    if part.get("name") == "language":
                        lang = part.get("valueCode")
                    elif part.get("name") == "value":
                        value = part.get("valueString")
                if value and lang and lang.startswith("de"):
                    return value
        return display

    def save_cache(self) -> None:
        if self._dirty:
            self.cache_path.write_text(
                json.dumps(self.cache, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8")
            self._dirty = False
