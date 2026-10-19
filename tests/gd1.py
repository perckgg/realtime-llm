"""Import GD1 (legacy/) modules in tests, to compare ports against the original.

GD1's code imports itself as `src.*` relative to legacy/, so legacy/ goes on
sys.path for the duration of the import only.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

LEGACY = Path(__file__).resolve().parents[1] / "legacy"


def gd1(module: str) -> ModuleType:
    sys.path.insert(0, str(LEGACY))
    try:
        return importlib.import_module(module)
    finally:
        sys.path.remove(str(LEGACY))
