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
"""Renderer für FDPG-CRTDL-Machbarkeitsanfragen (Python ≥ 3.11)."""
from .model import CrtdlParseError, Query, parse_file
from .render import render_markdown
from .terminology import Resolver

__all__ = ["CrtdlParseError", "Query", "Resolver", "parse_file", "render_markdown"]
__version__ = "0.1.0"
