from collections.abc import Callable

import pytest

from kokorog2p import get_g2p, phonemize, tokenize
from kokorog2p.types import PhonemizeResult, TokenSpan

# Optional convenience wrappers (skip tests if not present)
try:
    from kokorog2p import phoneme_ids, phonemes
except Exception:  # pragma: no cover
    phonemes = None
    phoneme_ids = None

# Deprecated APIs (adjust module paths if needed)
try:
    from kokorog2p.pipeline_api import phonemize_to_result, tokenize_with_offsets
except Exception:  # pragma: no cover
    phonemize_to_result = None
    tokenize_with_offsets = None

phonemes: Callable[..., str] | None
phoneme_ids: Callable[..., list[int]] | None
phonemize_to_result: Callable[..., PhonemizeResult] | None
tokenize_with_offsets: Callable[..., list[TokenSpan]] | None


def test_phonemize_returns_result_shape():
    r = phonemize(
        "Hello world!", language="en-us", return_ids=True, return_phonemes=True
    )
    assert r.clean_text is not None
    assert isinstance(r.tokens, list)
    assert (r.phonemes is None) or isinstance(r.phonemes, str)
    assert (r.token_ids is None) or isinstance(r.token_ids, list)
    assert isinstance(r.warnings, list)


def test_tokenize_matches_phonemize_tokens_text_and_offsets():
    text = "Hello world!"
    toks = tokenize(text, language="en-us", keep_punct=True)
    r = phonemize(text, language="en-us", return_ids=False, return_phonemes=False)

    assert len(toks) == len(r.tokens)
    for a, b in zip(toks, r.tokens, strict=False):
        assert a.text == b.text
        assert a.char_start == b.char_start
        assert a.char_end == b.char_end


def test_cached_g2p_instance_is_used_and_outputs_match():
    text = "Hello world!"
    g2p = get_g2p(language="en-us")

    r1 = phonemize(
        text, language="en-us", g2p=g2p, return_ids=True, return_phonemes=True
    )
    r2 = phonemize(text, language="en-us", return_ids=True, return_phonemes=True)

    # The caching use-case: providing g2p should not change results.
    assert r1.phonemes == r2.phonemes
    assert r1.token_ids == r2.token_ids

    # Ensure we got *some* output (helps catch miswiring)
    assert r1.phonemes is not None and len(r1.phonemes) > 0
    assert r1.token_ids is None or len(r1.token_ids) > 0


@pytest.mark.skipif(phonemes is None, reason="phonemes() wrapper not available")
def test_phonemes_wrapper_matches_result():
    text = "Hello world!"
    r = phonemize(text, language="en-us", return_ids=False, return_phonemes=True)
    assert phonemes is not None
    s = phonemes(text, language="en-us")
    assert r.phonemes is not None
    assert s == r.phonemes


@pytest.mark.skipif(phoneme_ids is None, reason="phoneme_ids() wrapper not available")
def test_phoneme_ids_wrapper_matches_result():
    text = "Hello world!"
    r = phonemize(text, language="en-us", return_ids=True, return_phonemes=False)
    assert phoneme_ids is not None
    ids = phoneme_ids(text, language="en-us")
    assert r.token_ids is not None
    assert ids == r.token_ids


def test_phonemize():
    text = "Hello . . . world!"
    result = phonemize(text, alignment="span")
    assert result.clean_text == "Hello…world!"
    assert "…" in result.phonemes
    result = phonemize(text, alignment="legacy")
    assert result.clean_text == "Hello…world!"
    assert "…" in result.phonemes
