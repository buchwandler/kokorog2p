"""German lexicon for G2P lookup."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

import g2lex

from kokorog2p.lexicons.registry import normalize_lexicon_selection
from kokorog2p.lexicons.runtime import SelectedLexicons, open_selected

_EMPTY: Mapping[str, str] = MappingProxyType({})


def clear_lexicon_cache() -> None:
    """Compatibility wrapper for the shared G2Lex resource cache."""
    from kokorog2p.lexicons.runtime import clear_resource_cache

    clear_resource_cache()


def lexicon_cache_info():
    """Return diagnostics for the shared resource-backed lexicon cache."""
    from kokorog2p.lexicons.runtime import resource_cache_info

    return resource_cache_info()


def _lookup_spellings(word: str) -> tuple[str, ...]:
    """Return deterministic German spelling candidates without casefolding."""
    lowercase = word.lower()
    candidates = (word, lowercase, lowercase.capitalize(), word.upper())
    return tuple(dict.fromkeys(candidates))


_UNIVERSAL_POS = frozenset(
    {
        "ADJ",
        "ADP",
        "ADV",
        "AUX",
        "CCONJ",
        "DET",
        "INTJ",
        "NOUN",
        "NUM",
        "PART",
        "PRON",
        "PROPN",
        "SCONJ",
        "VERB",
        "X",
    }
)
_GERMAN_STTS_TO_POS = {
    "ART": "DET",
    "PDS": "PRON",
    "PDAT": "PRON",
    "PIS": "PRON",
    "PIAT": "PRON",
    "PIDAT": "PRON",
    "PPER": "PRON",
    "PPOSS": "PRON",
    "PPOSAT": "PRON",
    "PRELS": "PRON",
    "PRELAT": "PRON",
    "PRF": "PRON",
    "NN": "NOUN",
    "NE": "PROPN",
    "VVFIN": "VERB",
    "VVINF": "VERB",
    "VVIZU": "VERB",
    "VAFIN": "AUX",
    "VAINF": "AUX",
    "VMFIN": "AUX",
}


def _normalize_german_lexicon_tag(tag: str | None) -> str | None:
    if tag is None:
        return None
    normalized = tag.upper()
    if normalized in _UNIVERSAL_POS:
        return normalized
    return _GERMAN_STTS_TO_POS.get(normalized, normalized)


class GermanLexicon:
    """German pronunciation lexicon backed by a lazy G2Lex asset."""

    def __init__(
        self,
        strip_stress: bool = False,
        load_silver: bool | None = None,
        load_gold: bool | None = None,
        lexicons: Sequence[str] | None = None,
    ) -> None:
        """Initialize the German lexicon."""
        names = normalize_lexicon_selection(
            "de-de",
            lexicons,
            load_gold=load_gold,
            load_silver=load_silver,
        )
        self._selected: SelectedLexicons = open_selected("de-de", names)
        self._gold: Mapping[str, object] = self._selected.layer("gold") or _EMPTY
        self._strip_stress = strip_stress
        self.load_silver = "silver" in names
        self.load_gold = "gold" in names
        self.lexicons = names

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using selected-layer and German casing precedence."""
        hit = self._selected.get_hit_candidates(_lookup_spellings(word))
        if hit is None:
            return None
        phonemes = g2lex.first_pronunciation(
            hit.value, tag=_normalize_german_lexicon_tag(tag)
        )
        if phonemes is None:
            return None
        if self._strip_stress:
            phonemes = phonemes.replace("ˈ", "").replace("ˌ", "")
        return phonemes

    def __call__(self, word: str, tag: str | None = None) -> str | None:
        return self.lookup(word, tag)

    def is_known(self, word: str) -> bool:
        return self._selected.get_hit_candidates(_lookup_spellings(word)) is not None

    def __len__(self) -> int:
        return len(self._selected)

    def close(self) -> None:
        self._selected.close()

    def __repr__(self) -> str:
        return f"GermanLexicon(entries={len(self)})"
