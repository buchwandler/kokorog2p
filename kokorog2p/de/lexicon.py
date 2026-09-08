"""German lexicon backed by explicitly provisioned Lexphon data."""

from __future__ import annotations

from collections.abc import Sequence

from lexphon import DataStore, PronunciationToken

from kokorog2p.base import FallbackProvider
from kokorog2p.lexicons.registry import normalize_lexicon_selection

from .lexphon_backend import GermanLexphonBackend


class GermanLexicon:
    """German pronunciation lexicon backed by Lexphon's local data store."""

    def __init__(
        self,
        strip_stress: bool = False,
        load_silver: bool | None = None,
        load_gold: bool | None = None,
        lexicons: Sequence[str] | None = None,
        *,
        fallback_provider: FallbackProvider = None,
        store: DataStore | None = None,
    ) -> None:
        """Initialize the German lexicon without installing or downloading data."""
        names = normalize_lexicon_selection(
            "de-de",
            lexicons,
            load_gold=load_gold,
            load_silver=load_silver,
        )
        self._backend = GermanLexphonBackend(
            names, fallback_provider=fallback_provider, store=store
        )
        self._strip_stress = strip_stress
        self.load_silver = "silver" in names
        self.load_gold = "gold" in names
        self.lexicons = names

    def lookup_token(
        self, word: str, tag: str | None = None
    ) -> PronunciationToken | None:
        """Return the structured selected Lexphon result for a word."""
        lookup = getattr(self._backend, "lookup_lexicon_token", None)
        if lookup is None:
            lookup = getattr(self._backend, "lookup_token", self._backend.lookup)
        return lookup(word, _normalize_german_lexicon_tag(tag))

    def pronounce_token(
        self, word: str, tag: str | None = None
    ) -> PronunciationToken | None:
        """Return the selected-lexicon or provider pronunciation token."""
        lookup = getattr(self._backend, "lookup_token", self._backend.lookup)
        return lookup(word, _normalize_german_lexicon_tag(tag))

    def pronounce_many(
        self, words: Sequence[str], tag: str | None = None
    ) -> tuple[PronunciationToken | None, ...]:
        """Batch full pronunciation lookup with one normalized German tag."""
        lookup_many = getattr(self._backend, "lookup_many", None)
        if lookup_many is not None:
            return lookup_many(
                words, tag=_normalize_german_lexicon_tag(tag)
            )
        return tuple(self.pronounce_token(word, tag) for word in words)
    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using Lexphon's ordered layers and German tag mapping."""
        value = self.lookup_token(word, tag)
        if isinstance(value, str):
            phonemes = value
        else:
            if value is None or not value.known:
                return None
            phonemes = value.pronunciation
            if phonemes is None:
                return None
        if self._strip_stress:
            phonemes = phonemes.replace("ˈ", "").replace("ˌ", "")
        return phonemes

    def __call__(self, word: str, tag: str | None = None) -> str | None:
        return self.lookup(word, tag)

    def is_known(self, word: str) -> bool:
        """Return whether Lexphon has a pronunciation for ``word``."""
        token = self.lookup_token(word)
        return token is not None and token.known

    def __len__(self) -> int:
        return len(self._backend)

    def close(self) -> None:
        self._backend.close()

    def __repr__(self) -> str:
        return f"GermanLexicon(entries={len(self)})"


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


__all__ = ["GermanLexicon"]
