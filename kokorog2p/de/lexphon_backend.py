"""German Lexphon runtime adapter."""

from __future__ import annotations

from collections.abc import Sequence

from lexphon import DataStore, LexiconNotInstalledError, Phonemizer

GERMAN_LEXICON_IDS = {
    "gold": "de-de:gold",
    "crane": "de-de:crane",
    "espeak": "de-de:espeak",
    "olaph": "de-de:olaph",
}
DEFAULT_GERMAN_LEXICONS = ("gold",)


class GermanLexphonBackend:
    """Own a Lexphon phonemizer for the selected German dictionary layers."""

    def __init__(
        self,
        names: Sequence[str],
        *,
        store: DataStore | None = None,
        phonemizer: Phonemizer | None = None,
    ) -> None:
        self.names = tuple(names)
        self.ids = tuple(GERMAN_LEXICON_IDS[name] for name in self.names)
        self._phonemizer = phonemizer
        if self._phonemizer is None and self.ids:
            try:
                self._phonemizer = Phonemizer(
                    "de-DE",
                    lexicons=self.ids,
                    store=store,
                    fallback=None,
                )
            except LexiconNotInstalledError as exc:
                identifier = self.ids[0]
                name = self.names[0]
                raise LexiconNotInstalledError(
                    f"German lexicon {name!r} ({identifier}) is not installed.\n"
                    "Install it with:\n\n"
                    f"    lexphon data install {identifier}\n\n"
                    "or disable dictionary lookup explicitly."
                ) from exc

    def lookup(self, word: str, tag: str | None = None):
        """Return Lexphon's structured lookup result for one German word."""
        if self._phonemizer is None:
            return None
        return self._phonemizer.lookup(word, tag=tag)

    def __len__(self) -> int:
        if self._phonemizer is None:
            return 0
        return sum(len(layer.lexicon) for layer in self._phonemizer.layers)

    def close(self) -> None:
        if self._phonemizer is not None:
            self._phonemizer.close()


__all__ = [
    "DEFAULT_GERMAN_LEXICONS",
    "GERMAN_LEXICON_IDS",
    "GermanLexphonBackend",
]
