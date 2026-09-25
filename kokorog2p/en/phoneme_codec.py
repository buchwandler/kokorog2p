"""English source-phoneme decoding and frontend compatibility profiles."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

from kokorog2p.lexicons.runtime import LexiconHit
from kokorog2p.vocab import get_english_vocab


@dataclass(frozen=True, slots=True)
class EnglishFrontendProfile:
    """Model-facing English realization rules independent of target model version."""

    id: str
    resolve_compound_stress: bool = True
    legacy_flap_token: str | None = "T"
    glottal_rewrite: str | None = "t"


MISAKI_V1 = EnglishFrontendProfile(
    id="hexgrad-misaki-v1",
    resolve_compound_stress=True,
    legacy_flap_token="T",
    glottal_rewrite="t",
)


def selector_candidates(tag: str | None) -> tuple[str, ...]:
    """Return ordered exact and parent selectors for an English POS tag."""
    if tag is None:
        return ()
    if tag == "None":
        return ("None",)
    if tag.startswith("NNP"):
        return (tag, "PROPN", "NOUN")
    if tag.startswith("VB"):
        return (tag, "VERB")
    if tag.startswith("NN"):
        return (tag, "NOUN")
    if tag.startswith(("ADV", "RB")):
        return (tag, "ADV")
    if tag.startswith(("ADJ", "JJ")):
        return (tag, "ADJ")
    parent_map = {
        "DET": ("DET", "ARTICLE"),
        "PRP": ("PRP", "PRON"),
        "PRP$": ("PRP$", "PRON"),
        "AUX": ("AUX", "VERB"),
        "ADP": ("ADP", "PREP"),
        "IN": ("IN", "ADP", "PREP"),
        "TO": ("TO", "PART"),
        "CC": ("CC", "CCONJ"),
        "CONJ": ("CONJ", "CCONJ"),
        "SCONJ": ("SCONJ",),
        "PART": ("PART",),
        "INTJ": ("INTJ",),
        "NUM": ("NUM",),
        "CHARACTER": ("CHARACTER",),
    }
    return parent_map.get(tag, (tag,))


def _source_scalar(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, tuple) and value:
        selected = value[0]
        return selected if isinstance(selected, str) else None
    return None


def _tagged_items(value: object) -> tuple[tuple[object, object], ...] | None:
    items = getattr(value, "items", None)
    if items is None or callable(items):
        return None
    return tuple(items)


def select_source_value(
    value: object, tag: str | None = None
) -> tuple[str | None, str | None]:
    """Select a scalar pronunciation and its selector from a stored value."""
    if isinstance(value, Mapping):
        values = tuple(value.items())
    else:
        values = _tagged_items(value)
    if values is not None:
        for selector in (*selector_candidates(tag), "DEFAULT"):
            for stored_selector, stored_value in values:
                if stored_selector == selector:
                    selected = _source_scalar(stored_value)
                    if selected is not None:
                        return selected, selector
                    break
        return None, None
    selected = _source_scalar(value)
    return selected, None


def _replace_ipa_symbols(value: str, *, british: bool) -> str:
    """Convert standard English IPA spellings to Kokoro's compact inventory."""
    result = unicodedata.normalize("NFC", value)
    result = result.replace("͡", "").replace("͜", "")
    replacements = (
        ("tʃ", "ʧ"),
        ("dʒ", "ʤ"),
        ("eɪ", "A"),
        ("aɪ", "I"),
        ("aʊ", "W"),
        ("ɔɪ", "Y"),
        ("oʊ", "Q" if british else "O"),
        ("əʊ", "Q" if british else "O"),
        ("ɝ", "ɜɹ"),
        ("ɚ", "əɹ"),
    )
    for old, new in replacements:
        result = result.replace(old, new)
    result = result.replace("ɫ", "l").replace("ɻ", "ɹ")
    result = result.replace("ʍ", "w")
    result = result.replace("g", "ɡ").replace("r", "ɹ")
    result = result.replace("ɐ", "ə")
    result = result.replace("e", "ɛ").replace("a", "ɑ").replace("o", "ɔ")
    for separator in ".-/()[]{}~‿|":
        result = result.replace(separator, "")
    result = "".join(char for char in result if not unicodedata.combining(char))
    for modifier in "ʰʷʲ˞ⁿˠˤˀ⁽⁾":
        result = result.replace(modifier, "")
    if not british:
        result = result.replace("ɒ", "ɑ").replace("ː", "")
    return result


def ipa_to_kokoro(value: str, *, british: bool = False) -> str:
    """Decode English IPA into Kokoro's model-facing phoneme alphabet."""
    result = _replace_ipa_symbols(value, british=british)
    result = "".join(char for char in result if not char.isspace())
    invalid = sorted(
        {char for char in result if char not in _english_inventory(british)}
    )
    if invalid:
        raise ValueError(
            f"English IPA contains unsupported symbols: {''.join(invalid)}"
        )
    return result


def _english_inventory(british: bool) -> frozenset[str]:
    return get_english_vocab(british) | frozenset({"T", "ɾ", "ʔ"})


def decode_hit(
    hit: LexiconHit, tag: str | None = None, *, british: bool = False
) -> DecodedPronunciation | None:
    """Select and decode one lexical hit for model-facing use."""
    source, selector = select_source_value(hit.value, tag)
    if source is None:
        return None
    if hit.phoneme_encoding == "kokoro-v1":
        decoded = source
    elif hit.phoneme_encoding == "ipa":
        decoded = ipa_to_kokoro(source, british=british)
    else:
        raise ValueError(
            f"Unsupported English phoneme encoding: {hit.phoneme_encoding!r}"
        )
    if not all(char in _english_inventory(british) for char in decoded):
        raise ValueError(
            f"Decoded English pronunciation is not model-valid: {decoded!r}"
        )
    return DecodedPronunciation(source, decoded, selector, hit.phoneme_encoding)


@dataclass(frozen=True, slots=True)
class DecodedPronunciation:
    source_pronunciation: str
    pronunciation: str
    selector: str | None
    source_encoding: str


__all__ = [
    "MISAKI_V1",
    "DecodedPronunciation",
    "EnglishFrontendProfile",
    "decode_hit",
    "ipa_to_kokoro",
    "select_source_value",
    "selector_candidates",
]
