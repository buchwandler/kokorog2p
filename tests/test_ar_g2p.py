"""Tests for the native clean-room Arabic frontend."""

from __future__ import annotations

import pytest

from kokorog2p import phonemize
from kokorog2p.ar.diacritizer import (
    ArabicDiacritizerError,
    NoneDiacritizer,
)
from kokorog2p.ar.g2p import ArabicG2P
from kokorog2p.ar.model_profile import (
    clean_espeak_output,
    encode_output,
    validate_nabra_symbols,
)


class FakeBackend:
    def __init__(self, output: str = "a.b̪ˤ[ʕ]{ħ}") -> None:
        self.output = output
        self.calls: list[tuple[str, bool, bool]] = []

    def phonemize(
        self, text: str, *, convert_to_kokoro: bool, remove_punctuation: bool
    ) -> str:
        self.calls.append((text, convert_to_kokoro, remove_punctuation))
        return self.output


class FakeDiacritizer:
    def __init__(self, values: list[str]) -> None:
        self.values = values
        self.received: list[str] = []

    def diacritize_tokens(self, tokens: list[str]) -> list[str]:
        self.received = list(tokens)
        return self.values


def test_clean_espeak_output_has_narrow_cleanup_rules() -> None:
    assert clean_espeak_output("a.b̪ˤ͡ [ʕ] {ħ} .") == "ab ʕ ħ ."
    assert validate_nabra_symbols("ʕ ħ")[0]
    assert encode_output("ʕħ") == [7, 8]


def test_cleanup_preserves_sentence_final_dot_and_reports_unknown_symbols() -> None:
    assert clean_espeak_output("a.b.") == "ab."
    with pytest.raises(ValueError, match="not present"):
        encode_output("§")


def test_none_diacritizer_is_identity() -> None:
    assert NoneDiacritizer().diacritize_tokens(["مَرْحَبًا"]) == ["مَرْحَبًا"]


def test_arabic_g2p_preserves_offsets_and_suppresses_source_spans() -> None:
    g2p = ArabicG2P(diacritizer="none")
    backend = FakeBackend()
    g2p._espeak_backend = backend
    text = "مَرْحَبًا [12] Hello، بِكَ؟"

    tokens = g2p(text)

    assert [
        (token.text, token.get("char_start"), token.get("char_end")) for token in tokens
    ] == [
        ("مَرْحَبًا", 0, 9),
        ("[", 10, 11),
        ("12", 11, 13),
        (
            "]",
            13,
            14,
        ),
        ("Hello", 15, 20),
        ("،", 20, 21),
        ("بِكَ", 22, 26),
        ("؟", 26, 27),
    ]
    assert all(token.get("drop") for token in tokens[1:4])
    assert tokens[4].get("drop") is True
    assert tokens[0].phonemes == "abʕħ"
    assert tokens[5].phonemes == ","
    assert tokens[-1].phonemes == "?"
    assert backend.calls == [
        ("مَرْحَبًا", False, False),
        ("بِكَ", False, False),
    ]
    assert any("ASCII-Latin" in warning for warning in g2p.warnings)


def test_parentheses_are_not_citations() -> None:
    g2p = ArabicG2P(diacritizer="none")
    backend = FakeBackend("a")
    g2p._espeak_backend = backend
    tokens = g2p("(12)")
    assert [token.get("drop") for token in tokens] == [None, None, None]
    assert [token.phonemes for token in tokens] == ["(", "a", ")"]


def test_injected_diacritizer_receives_arabic_words_in_context() -> None:
    adapter = FakeDiacritizer(["مَرْحَبًا", "بِكَ"])
    g2p = ArabicG2P(diacritizer=adapter)
    backend = FakeBackend("a")
    g2p._espeak_backend = backend

    g2p("مرحبا بك")

    assert adapter.received == ["مرحبا", "بك"]
    assert [call[0] for call in backend.calls] == ["مَرْحَبًا", "بِكَ"]


def test_diacritizer_length_mismatch_is_rejected() -> None:
    g2p = ArabicG2P(diacritizer=FakeDiacritizer([]))
    g2p._espeak_backend = FakeBackend("a")
    with pytest.raises(ValueError, match="different number"):
        g2p("مرحبا")


def test_diacritizer_error_type_is_public() -> None:
    assert issubclass(ArabicDiacritizerError, RuntimeError)


def test_public_pipeline_preserves_parentheses_and_drops_citations() -> None:
    g2p = ArabicG2P(diacritizer="none")
    g2p._espeak_backend = FakeBackend("a")
    result = phonemize(
        "مرحبا [12] (بك)",
        language="ar",
        g2p=g2p,
        return_ids=False,
    )
    assert result.phonemes == "a (a)"
    assert "[" not in result.phonemes and "]" not in result.phonemes
    assert any("citation" in warning for warning in result.warnings)
