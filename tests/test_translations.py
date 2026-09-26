import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "custom_components" / "akce_na_jidlo"


def keys(data, prefix=""):
    out = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        out |= keys(value, path) if isinstance(value, dict) else {path}
    return out


def test_translations_have_same_keys():
    base = keys(json.loads((ROOT / "strings.json").read_text(encoding="utf-8")))
    for lang in ("cs", "sk", "en"):
        data = json.loads((ROOT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
        assert keys(data) == base, lang


def test_config_fields_translated():
    from akce_na_jidlo import const

    data = json.loads((ROOT / "translations" / "cs.json").read_text(encoding="utf-8"))
    fields = data["options"]["step"]["init"]["data"]
    for name in dir(const):
        if name.startswith("CONF_") and name != "CONF_COUNTRY":
            assert getattr(const, name) in fields, name
