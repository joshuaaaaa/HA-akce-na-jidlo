"""Načte čisté moduly integrace bez nutnosti instalovat Home Assistant."""

import importlib
import sys
import types
from pathlib import Path

PKG = "akce_na_jidlo"
PATH = Path(__file__).resolve().parent.parent / "custom_components" / PKG

if PKG not in sys.modules:
    package = types.ModuleType(PKG)
    package.__path__ = [str(PATH)]
    sys.modules[PKG] = package
    for module in ("const", "kupi", "generic", "search", "stores"):
        importlib.import_module(f"{PKG}.{module}")
