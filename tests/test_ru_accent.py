import sys
import types

import pytest

from kokorog2p.ru.accent import (
    NoAccentAdapter,
    RuAccentAdapter,
    RussianAccentError,
    normalize_explicit_stress,
)


def test_normalize_explicit_stress_accepts_combining_and_legacy_plus():
    assert normalize_explicit_stress("за́мок") == "за́мок"
    assert normalize_explicit_stress("з+амок") == "за́мок"


def test_malformed_stress_is_rejected():
    with pytest.raises(RussianAccentError, match="must follow"):
        normalize_explicit_stress("\u0301слово")


def test_no_accent_adapter_does_not_load_external_package():
    adapter = NoAccentAdapter()
    assert adapter.accentuate("Елка") == "Елка"


def test_ruaccent_adapter_loads_only_on_first_use(monkeypatch):
    calls = []

    class FakeRUAccent:
        def load(self, **kwargs):
            calls.append(("load", kwargs))

        def process_all(self, text):
            return text.replace("Е", "Ё")

    monkeypatch.setitem(
        sys.modules, "ruaccent", types.SimpleNamespace(RUAccent=FakeRUAccent)
    )
    adapter = RuAccentAdapter(model_size="turbo3.1")
    assert not adapter.loaded
    assert adapter.accentuate("Елка") == "Ёлка"
    assert adapter.loaded
    assert calls[0][1]["omograph_model_size"] == "turbo3.1"


def test_missing_ruaccent_error_is_actionable(monkeypatch):
    monkeypatch.delitem(sys.modules, "ruaccent", raising=False)
    adapter = RuAccentAdapter()
    monkeypatch.setattr(
        "kokorog2p.ru.accent.importlib.import_module",
        lambda _: (_ for _ in ()).throw(ImportError()),
    )
    with pytest.raises(RussianAccentError, match=r"pip install.*kokorog2p\[ru\]"):
        adapter.accentuate("слово")
