"""Offline tests for ranked spaCy model selection."""

import pytest

from kokorog2p.spacy_models import (
    SpacyModelResolutionError,
    SpacyModelSize,
    candidate_spacy_models,
    normalize_spacy_language,
    resolve_spacy_model,
)


def _resolver(
    language: str,
    installed: set[str],
    *,
    loader=None,
    **kwargs,
):
    return resolve_spacy_model(
        language,
        package_checker=installed.__contains__,
        loader=loader or (lambda _name: object()),
        **kwargs,
    )


def test_language_normalization_and_candidate_order() -> None:
    assert normalize_spacy_language("EN_us") == "en"
    assert candidate_spacy_models("fr") == (
        "fr_core_news_trf",
        "fr_core_news_lg",
        "fr_core_news_md",
        "fr_core_news_sm",
    )


def test_automatic_selection_prefers_lg_over_md_and_sm() -> None:
    result = _resolver(
        "en-us",
        {"en_core_web_sm", "en_core_web_md", "en_core_web_lg"},
    )

    assert result.package == "en_core_web_lg"
    assert result.size is SpacyModelSize.LG
    assert result.automatic is True
    assert result.diagnostics["package"] == "en_core_web_lg"


def test_automatic_selection_prefers_transformer() -> None:
    result = _resolver(
        "en",
        {
            "en_core_web_sm",
            "en_core_web_md",
            "en_core_web_lg",
            "en_core_web_trf",
        },
    )

    assert result.package == "en_core_web_trf"


def test_french_small_model_is_selected_when_it_is_the_only_candidate() -> None:
    result = _resolver("fr", {"fr_core_news_sm"})
    assert result.package == "fr_core_news_sm"


def test_explicit_model_is_strict_and_wins_over_larger_installed_models() -> None:
    loaded: list[str] = []
    result = _resolver(
        "en",
        {"en_core_web_sm", "en_core_web_lg"},
        loader=loaded.append,
        spacy_model="en_core_web_sm",
    )

    assert result.package == "en_core_web_sm"
    assert result.automatic is False
    assert loaded == []


def test_exact_size_does_not_fall_back() -> None:
    with pytest.raises(SpacyModelResolutionError, match="en_core_web_lg") as caught:
        _resolver("en", {"en_core_web_sm"}, spacy_model_size="lg")

    assert caught.value.automatic is False
    assert caught.value.candidates == ("en_core_web_lg",)


def test_cross_language_model_is_rejected() -> None:
    with pytest.raises(SpacyModelResolutionError, match="en_core_web_sm"):
        _resolver("de", {"en_core_web_sm"}, spacy_model="en_core_web_sm")


def test_unloadable_automatic_candidate_falls_back() -> None:
    attempts: list[str] = []

    def loader(name: str) -> object:
        attempts.append(name)
        if name == "en_core_web_lg":
            raise OSError("broken model")
        return object()

    result = _resolver(
        "en",
        {"en_core_web_lg", "en_core_web_sm"},
        loader=loader,
    )

    assert result.package == "en_core_web_sm"
    assert attempts == ["en_core_web_lg", "en_core_web_sm"]
    assert dict(result.errors)["en_core_web_lg"].startswith("OSError")


def test_automatic_error_has_diagnostics_and_install_examples() -> None:
    with pytest.raises(SpacyModelResolutionError) as caught:
        _resolver("de", set())

    message = str(caught.value)
    assert "language 'de'" in message
    assert "de_core_news_trf" in message
    assert "Candidate diagnostics" in message
    assert "python -m spacy download de_core_news_sm" in message
