"""Factory resolution and cache identity tests for spaCy selection."""

import pytest

from kokorog2p import clear_cache, get_g2p
from kokorog2p.spacy_models import (
    SpacyModelResolution,
    SpacyModelResolutionError,
    SpacyModelSize,
)


def _resolution(package: str, *, automatic: bool = True) -> SpacyModelResolution:
    size = SpacyModelSize(package.rsplit("_", 1)[-1])
    return SpacyModelResolution(
        language="en",
        package=package,
        size=size,
        automatic=automatic,
        candidates=(package,),
        checked=(package,),
        errors=(),
        spacy_available=True,
    )


def test_auto_and_explicit_equivalent_models_share_cache_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        "kokorog2p.resolve_spacy_model",
        lambda *_args, **_kwargs: _resolution("en_core_web_lg"),
    )
    clear_cache()

    automatic = get_g2p("en-us", spacy_model="auto", load_silver=False, load_gold=False)
    explicit = get_g2p(
        "en-us",
        spacy_model="en_core_web_lg",
        load_silver=False,
        load_gold=False,
    )

    assert automatic is explicit
    assert automatic.spacy_model == "en_core_web_lg"


def test_different_explicit_models_have_distinct_cache_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        "kokorog2p.resolve_spacy_model",
        lambda _language, **kwargs: _resolution(
            kwargs.get("spacy_model", "en_core_web_sm"), automatic=False
        ),
    )
    clear_cache()

    small = get_g2p(
        "en", spacy_model="en_core_web_sm", load_silver=False, load_gold=False
    )
    large = get_g2p(
        "en", spacy_model="en_core_web_lg", load_silver=False, load_gold=False
    )

    assert small is not large
    assert small.spacy_model == "en_core_web_sm"
    assert large.spacy_model == "en_core_web_lg"


def test_changed_automatic_resolution_changes_identity(monkeypatch) -> None:
    selected = {"package": "en_core_web_sm"}

    def resolve(*_args, **_kwargs):
        return _resolution(selected["package"])

    monkeypatch.setattr("kokorog2p.resolve_spacy_model", resolve)
    clear_cache()
    small = get_g2p("en", load_silver=False, load_gold=False)
    clear_cache()
    selected["package"] = "en_core_web_lg"
    large = get_g2p("en", load_silver=False, load_gold=False)

    assert small is not large


def test_implicit_spacy_resolution_falls_back_when_no_model_is_available(
    monkeypatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise SpacyModelResolutionError(
            "no local model",
            language="en",
            automatic=True,
            candidates=(),
            errors=(),
            spacy_available=False,
        )

    monkeypatch.setattr("kokorog2p.resolve_spacy_model", fail)
    clear_cache()

    g2p = get_g2p(
        "en",
        use_spacy=None,
        use_espeak_fallback=False,
        load_silver=False,
        load_gold=False,
    )

    assert g2p.use_spacy is False
    assert g2p.spacy_model is None


def test_explicit_spacy_requirement_remains_strict(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise SpacyModelResolutionError(
            "no local model",
            language="en",
            automatic=True,
            candidates=(),
            errors=(),
            spacy_available=False,
        )

    monkeypatch.setattr("kokorog2p.resolve_spacy_model", fail)
    clear_cache()

    with pytest.raises(SpacyModelResolutionError, match="no local model"):
        get_g2p(
            "en",
            use_spacy=True,
            load_silver=False,
            load_gold=False,
        )


def test_disabled_spacy_does_not_resolve_or_store_a_model(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("model discovery should be skipped")

    monkeypatch.setattr("kokorog2p.resolve_spacy_model", fail)
    clear_cache()
    g2p = get_g2p(
        "en",
        use_spacy=False,
        spacy_model="en_core_web_lg",
        load_silver=False,
        load_gold=False,
    )

    assert g2p.use_spacy is False
    assert g2p.spacy_model is None


def test_cjk_reserved_spacy_option_does_not_resolve(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("CJK must not discover spaCy models")

    monkeypatch.setattr("kokorog2p.resolve_spacy_model", fail)
    clear_cache()
    g2p = get_g2p("zh", use_spacy=True, load_silver=False, load_gold=False)

    assert g2p.use_spacy is True
    assert g2p.spacy_model is None
