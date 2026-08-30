"""German lexicon for G2P lookup."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

import g2lex

from kokorog2p.lexicons.runtime import SelectedLexicons, open_selected

_EMPTY: Mapping[str, str] = MappingProxyType({})


def clear_lexicon_cache() -> None:
    """Compatibility hook retained for callers of the former JSON cache."""


def lexicon_cache_info():
    """Return compatibility cache statistics for the resource-backed lexicon."""
    from collections import namedtuple

    return namedtuple("LexiconCacheInfo", "hits misses maxsize currsize")(0, 0, 0, 0)


def _lookup_spellings(word: str) -> tuple[str, ...]:
    """Return deterministic German spelling candidates without casefolding."""
    lowercase = word.lower()
    candidates = (word, lowercase, lowercase.capitalize(), word.upper())
    return tuple(dict.fromkeys(candidates))

class GermanLexicon:
    """German pronunciation lexicon backed by a lazy G2Lex asset."""

    def __init__(
        self,
        strip_stress: bool = False,
        load_silver: bool = True,
        load_gold: bool = True,
        lexicons: Sequence[str] | None = None,
    ) -> None:
        """Initialize the German lexicon."""
        del load_silver
        if lexicons is None:
            names = ("gold",) if load_gold else ()
        elif isinstance(lexicons, str):
            names = (lexicons,)
        else:
            names = tuple(lexicons)
        self._selected: SelectedLexicons = open_selected("de-de", names)
        self._gold: Mapping[str, object] = self._selected.layer("gold") or _EMPTY
        self._strip_stress = strip_stress
        self.load_silver = False
        self.load_gold = "gold" in names
        self.lexicons = names

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using selected-layer and German casing precedence."""
        hit = self._selected.get_hit_candidates(_lookup_spellings(word))
        if hit is None:
            return None
        phonemes = g2lex.first_pronunciation(hit.value, tag=tag)
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
