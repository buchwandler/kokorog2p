"""Compatibility facade for the shared Lexphon backend."""

from __future__ import annotations

from collections.abc import Sequence

from lexphon import DataStore, Phonemizer

from kokorog2p.base import FallbackProvider
from kokorog2p.lexicons.lexphon_backend import LexphonBackend

DEFAULT_GERMAN_LEXICONS = ("gold",)


class GermanLexphonBackend(LexphonBackend):
    """Keep the historical German adapter name over the common backend."""

    def __init__(
        self,
        names: Sequence[str],
        *,
        fallback_provider: FallbackProvider = None,
        store: DataStore | None = None,
        phonemizer: Phonemizer | None = None,
    ) -> None:
        super().__init__(
            "de-de",
            names,
            fallback_provider=fallback_provider,
            store=store,
            phonemizer=phonemizer,
        )


__all__ = ["DEFAULT_GERMAN_LEXICONS", "GermanLexphonBackend"]
