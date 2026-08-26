"""Offline and optional-dependency tests for Arabic support."""

from __future__ import annotations

import builtins
import sys
import types

import pytest

from kokorog2p.ar.diacritizer import (
    ArabicDiacritizerDataError,
    ArabicDiacritizerDependencyError,
    CamelMLEDiacritizer,
)


def test_camel_adapter_constructor_does_not_import_camel_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fail_if_camel(name: str, *args: object, **kwargs: object):
        if name.startswith("camel_tools"):
            raise AssertionError("CAMeL imported during adapter construction")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_if_camel)
    adapter = CamelMLEDiacritizer()
    assert adapter._disambiguator is None


def test_missing_camel_package_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fail_if_camel(name: str, *args: object, **kwargs: object):
        if name.startswith("camel_tools"):
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_if_camel)
    with pytest.raises(ArabicDiacritizerDependencyError, match="not installed"):
        CamelMLEDiacritizer().diacritize_tokens(["مرحبا"])


def test_missing_camel_data_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingDataMLE:
        @staticmethod
        def pretrained() -> object:
            raise FileNotFoundError("database missing")

    camel_tools = types.ModuleType("camel_tools")
    disambig = types.ModuleType("camel_tools.disambig")
    mle = types.ModuleType("camel_tools.disambig.mle")
    mle.MLEDisambiguator = MissingDataMLE  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "camel_tools", camel_tools)
    monkeypatch.setitem(sys.modules, "camel_tools.disambig", disambig)
    monkeypatch.setitem(sys.modules, "camel_tools.disambig.mle", mle)

    with pytest.raises(ArabicDiacritizerDataError, match="does not download"):
        CamelMLEDiacritizer().diacritize_tokens(["مرحبا"])
