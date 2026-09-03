"""Structural tests for cheap and lazy G2P factory construction."""

import g2lex
import pytest

from kokorog2p import clear_cache, get_g2p, phonemize_prepared
from kokorog2p.ru.g2p import RussianG2P
from kokorog2p.spacy_models import SpacyModelResolution, SpacyModelSize


@pytest.mark.parametrize("language", ["en-us", "en-gb", "fr-fr"])
def test_factory_does_not_measure_case_alias_lexicon(
    monkeypatch: pytest.MonkeyPatch,
    language: str,
) -> None:
    def forbidden_len(self: object) -> int:
        raise AssertionError(
            "get_g2p() must not enumerate CaseAliasMapping during construction"
        )

    monkeypatch.setattr(g2lex.CaseAliasMapping, "__len__", forbidden_len)
    clear_cache()

    get_g2p(
        language,
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )


def test_factory_reuses_identical_frontend() -> None:
    clear_cache()
    options = {
        "use_spacy": False,
        "use_espeak_fallback": False,
        "use_goruut_fallback": False,
    }
    first = get_g2p("en-us", **options)
    second = get_g2p("en-us", **options)
    assert second is first


def test_factory_defers_russian_accentuator_and_caches_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeAccent:
        def accentuate(self, text: str) -> str:
            return text

    def fake_make_accentuator(spec: object, **kwargs: object) -> FakeAccent | None:
        del kwargs
        calls.append(str(spec))
        return None if spec == "none" else FakeAccent()

    monkeypatch.setattr("kokorog2p.ru.g2p.make_accentuator", fake_make_accentuator)

    automatic = RussianG2P(
        accentuator="auto",
        engine=object(),
        strict_stress=False,
    )
    assert calls == []
    assert automatic.accentuator is not None
    assert calls == ["auto"]
    _ = automatic.accentuator
    assert calls == ["auto"]

    none = RussianG2P(
        accentuator="none",
        engine=object(),
        strict_stress=False,
    )
    assert calls == ["auto"]
    assert none.accentuator is None
    _ = none.accentuator
    assert calls == ["auto", "none"]


def test_automatic_spacy_factory_resolution_does_not_probe_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def resolve(language: str, **kwargs: object) -> SpacyModelResolution:
        calls.append(kwargs)
        return SpacyModelResolution(
            language="en",
            package="en_core_web_sm",
            size=SpacyModelSize.SM,
            automatic=True,
            candidates=("en_core_web_sm",),
            checked=("en_core_web_sm",),
            errors=(),
            spacy_available=True,
        )

    monkeypatch.setattr("kokorog2p.resolve_spacy_model", resolve)
    monkeypatch.setattr(
        "kokorog2p.en.g2p.load_spacy_model",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("factory must not load spaCy")
        ),
    )
    clear_cache()

    g2p = get_g2p("en-us", use_espeak_fallback=False)

    assert g2p.use_spacy is True
    assert calls == [
        {"spacy_model": None, "spacy_model_size": None, "probe_loadability": False}
    ]


@pytest.mark.parametrize(
    ("language", "attribute"),
    [
        ("ja", "_pyopenjtalk"),
        ("ko", "_g2pk_instance"),
        ("he", "_phonikud"),
        ("kk", "_espeak_backend"),
    ],
)
def test_factory_preserves_lazy_optional_resource(
    language: str,
    attribute: str,
) -> None:
    clear_cache()
    g2p = get_g2p(
        language,
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    assert getattr(g2p, attribute) is None


def test_factory_preserves_lazy_vietnamese_foreign_fallback() -> None:
    clear_cache()
    g2p = get_g2p(
        "vi",
        foreign_fallback="english",
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    assert g2p._foreign_g2p is None


def test_factory_preserves_direct_and_prepared_output() -> None:
    text = "Hello world."
    clear_cache()
    g2p = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    direct = "".join(
        (token.phonemes or "") + token.whitespace for token in g2p(text)
    ).strip()
    prepared = phonemize_prepared(
        text,
        language="en-us",
        g2p=g2p,
        use_spacy=False,
        use_espeak_fallback=False,
        return_ids=False,
        return_phonemes=True,
    ).phonemes
    assert prepared == direct
