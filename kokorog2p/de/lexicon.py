"""German lexicon for G2P lookup."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

from kokorog2p.lexicons.runtime import SelectedLexicons, open_selected

_EMPTY: Mapping[str, str] = MappingProxyType({})


def clear_lexicon_cache() -> None:
    """Compatibility hook retained for callers of the former JSON cache."""


def lexicon_cache_info():
    """Return compatibility cache statistics for the resource-backed lexicon."""
    from collections import namedtuple

    return namedtuple("LexiconCacheInfo", "hits misses maxsize currsize")(0, 0, 0, 0)


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
        names = (
            ("gold",)
            if lexicons is None and load_gold
            else ()
            if lexicons is None
            else tuple(lexicons)
        )
        self._selected: SelectedLexicons = open_selected("de-de", names)
        self._gold: Mapping[str, object] = self._selected.layer("gold") or _EMPTY
        self._strip_stress = strip_stress
        self.load_silver = False
        self.load_gold = "gold" in names
        self.lexicons = names

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the lexicon."""
        del tag
        value = self._selected.get_hit(word.lower())
        phonemes = value.value if value is not None else None
        if not isinstance(phonemes, str):
            return None
        if self._strip_stress:
            return phonemes.replace("ˈ", "").replace("ˌ", "")
        return phonemes

    def __call__(self, word: str, tag: str | None = None) -> str | None:
        return self.lookup(word, tag)

    def is_known(self, word: str) -> bool:
        return word.lower() in self._selected

    def __len__(self) -> int:
        return len(self._selected)

    def close(self) -> None:
        self._selected.close()

    def __repr__(self) -> str:
        return f"GermanLexicon(entries={len(self)})"
