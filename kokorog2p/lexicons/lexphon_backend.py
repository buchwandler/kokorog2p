"""Lazy KokoroG2P integration with provisioned Lexphon lexica."""

from __future__ import annotations

from collections.abc import Sequence

from lexphon import DataStore, LexiconNotInstalledError, Phonemizer, PronunciationToken

LEXPHON_LANGUAGE_BY_KOKORO = {
    "ru-ru": "ru",
    "th-th": "th",
    "vi-vn": "vi",
    "ja-jp": "ja",
    "ko-kr": "ko",
    "pt-br": "pt",
    "pt-pt": "pt",
    "sv-se": "sv",
}

LEXPHON_IDS = {
    "ru-ru": {"lexhint": "ru:lexhint"},
    "th-th": {"lexhint": "th:lexhint"},
    "vi-vn": {"lexhint": "vi:lexhint"},
    "ja-jp": {"lexhint": "ja:lexhint"},
    "ko-kr": {"lexhint": "ko:lexhint"},
    "pt-br": {"lexhint": "pt:lexhint"},
    "sv-se": {"nst": "sv-se:nst"},
    "pt-pt": {"lexhint": "pt:lexhint"},
}


class LexphonBackend:
    """Lazy application adapter around :class:`lexphon.Phonemizer`.

    DataStore and Phonemizer construction are deferred until the first lookup.
    Lexphon is always called with an explicit local lexicon selection and no
    fallback, so this adapter never downloads data or silently invokes eSpeak.
    """

    def __init__(
        self,
        language: str,
        names: Sequence[str],
        *,
        store: DataStore | None = None,
        phonemizer: Phonemizer | None = None,
    ) -> None:
        self.language = language.lower().replace("_", "-")
        if self.language not in LEXPHON_LANGUAGE_BY_KOKORO:
            raise ValueError(f"Lexphon is not configured for {language!r}")
        self.names = tuple(names)
        try:
            self.ids = tuple(LEXPHON_IDS[self.language][name] for name in self.names)
        except KeyError as exc:
            raise ValueError(
                f"Unknown Lexphon lexicon {exc.args[0]!r} for {language!r}"
            ) from exc
        self.store = store
        self._phonemizer = phonemizer
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("Lexphon backend is closed")

    def _engine(self) -> Phonemizer | None:
        self._ensure_open()
        if self._phonemizer is None and self.ids:
            lexphon_language = LEXPHON_LANGUAGE_BY_KOKORO[self.language]
            try:
                self._phonemizer = Phonemizer(
                    lexphon_language,
                    lexicons=self.ids,
                    store=self.store,
                    fallback=None,
                )
            except LexiconNotInstalledError as exc:
                identifier = self.ids[0]
                name = self.names[0]
                raise LexiconNotInstalledError(
                    f"{self.language} lexicon {name!r} "
                    f"({identifier}) is not installed.\n"
                    "Install it with:\n\n"
                    f"    lexphon data install {identifier}\n"
                    f"    lexphon data verify {identifier}\n"
                ) from exc
        return self._phonemizer

    def lookup(self, word: str, tag: str | None = None) -> PronunciationToken | None:
        engine = self._engine()
        return None if engine is None else engine.lookup(word, tag=tag)

    def lookup_prefixes(
        self, text: str, *, position: int = 0, tag: str | None = None
    ) -> tuple[PronunciationToken, ...]:
        engine = self._engine()
        return (
            ()
            if engine is None
            else engine.lookup_prefixes(text, position=position, tag=tag)
        )

    def __len__(self) -> int:
        engine = self._engine()
        return (
            0 if engine is None else sum(len(layer.lexicon) for layer in engine.layers)
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._phonemizer is not None:
            self._phonemizer.close()
            self._phonemizer = None


__all__ = [
    "LEXPHON_IDS",
    "LEXPHON_LANGUAGE_BY_KOKORO",
    "LexphonBackend",
]
