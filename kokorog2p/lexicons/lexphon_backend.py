"""Lazy KokoroG2P integration with Lexphon 0.2."""

from __future__ import annotations

from collections.abc import Sequence

from lexphon import DataStore, LexiconNotInstalledError, Phonemizer, PronunciationToken
from lexphon.profiles import LanguageProfile, ProfileRegistry

from kokorog2p.base import FallbackProvider
from kokorog2p.language_codes import normalize_language_code
from kokorog2p.lexicons.evidence import evidence_from_lexphon_token
from kokorog2p.lexicons.registry import get_lexicon_spec


def provider_metadata(token: PronunciationToken) -> dict[str, object]:
    """Serialize Lexphon provider provenance for token diagnostics."""
    variant = token.variants[0] if token.variants else None
    return {
        "pronunciation_source": "provider",
        "pronunciation_provider": token.provider,
        "pronunciation_requested_language": token.requested_language,
        "pronunciation_source_ipa": (
            variant.source_pronunciation if variant is not None else None
        ),
        "pronunciation_language_markers": [
            {"language": marker.language, "ipa_offset": marker.ipa_offset}
            for marker in (variant.language_markers if variant is not None else ())
        ],
    }


_LEXPHON_LANGUAGE_ALIASES = {
    "de-de": "de-de",
    "en-us": "en-us",
    "en-gb": "en-gb",
    "fr-fr": "fr-fr",
    "sv-se": "sv-se",
    "ru-ru": "ru",
    "th-th": "th",
    "vi-vn": "vi",
    "ja-jp": "ja",
    "ko-kr": "ko",
    "pt-br": "pt",
    "pt-pt": "pt-PT",
    "cs-cz": "cs-cz",
}


def to_lexphon_language(language: str) -> str:
    """Map a canonical Kokoro language to Lexphon's language profile."""
    canonical = normalize_language_code(language)
    return _LEXPHON_LANGUAGE_ALIASES.get(canonical, canonical)


def _lexphon_profiles(language: str) -> ProfileRegistry | None:
    """Provide the regional Portuguese profile required by released Lexphon data."""
    if language != "pt-pt":
        return None
    return ProfileRegistry(
        (
            LanguageProfile(
                language="pt-PT",
                aliases=("pt-pt",),
                default_lexicons=(),
                case_candidates=("exact", "lower"),
                unicode_normalization="NFC",
                apostrophe_normalization="ascii",
            ),
        )
    )


def _lexphon_ids(language: str, names: Sequence[str]) -> tuple[str, ...]:
    """Resolve selected logical lexicon names through the central registry."""
    ids: list[str] = []
    for name in names:
        spec = get_lexicon_spec(language, name)
        if spec.backend != "lexphon":
            raise ValueError(f"lexicon {name!r} for {language!r} is not Lexphon-backed")
        ids.append(spec.id)
    return tuple(ids)


class LexphonBackend:
    """Lazy application adapter around :class:`lexphon.Phonemizer`."""

    def __init__(
        self,
        language: str,
        names: Sequence[str] = (),
        *,
        fallback_provider: FallbackProvider = None,
        store: DataStore | None = None,
        phonemizer: Phonemizer | None = None,
    ) -> None:
        self.language = normalize_language_code(language)
        self.names = tuple(names)
        self.ids = _lexphon_ids(self.language, self.names)
        self.fallback_provider = fallback_provider
        self.store = store
        self._phonemizer = phonemizer
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("Lexphon backend is closed")

    def _engine(self) -> Phonemizer | None:
        self._ensure_open()
        if self._phonemizer is None and (
            self.ids or self.fallback_provider is not None
        ):
            lexphon_language = to_lexphon_language(self.language)
            try:
                self._phonemizer = Phonemizer(
                    lexphon_language,
                    lexicons=list(self.ids),
                    store=self.store,
                    fallback=self.fallback_provider,
                    profiles=_lexphon_profiles(self.language),
                )
            except LexiconNotInstalledError as exc:
                if not self.ids:
                    raise
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

    def lookup_lexicon_token(
        self, word: str, tag: str | None = None
    ) -> PronunciationToken | None:
        """Look up only in explicitly selected lexical layers."""
        engine = self._engine()
        return None if engine is None else engine.lookup_lexicon(word, tag=tag)

    def lookup_token(
        self, word: str, tag: str | None = None
    ) -> PronunciationToken | None:
        """Look up selected lexical layers and the configured provider."""
        engine = self._engine()
        return None if engine is None else engine.lookup(word, tag=tag)

    def lookup(self, word: str, tag: str | None = None) -> PronunciationToken | None:
        """Compatibility alias for full pronunciation lookup."""
        return self.lookup_token(word, tag)

    def lookup_many(
        self, words: Sequence[str], *, tag: str | None = None
    ) -> tuple[PronunciationToken | None, ...]:
        """Look up a sequence while preserving Lexphon's batch semantics."""
        engine = self._engine()
        if engine is None:
            return tuple(None for _ in words)
        return engine.lookup_many(words, tag=tag)

    def lookup_prefixes(
        self, text: str, *, position: int = 0, tag: str | None = None
    ) -> tuple[PronunciationToken, ...]:
        """Look up lexical prefixes without invoking the provider."""
        engine = self._engine()
        return (
            ()
            if engine is None
            else engine.lookup_prefixes(text, position=position, tag=tag)
        )

    def lexicon_evidence(self, word: str, tag: str | None = None):
        """Return evidence from selected Lexphon layers without fallback."""
        token = self.lookup_lexicon_token(word, tag)
        return evidence_from_lexphon_token(
            language=self.language,
            token=token,
            selected_lexicons=self.ids,
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


__all__ = ["LexphonBackend", "provider_metadata", "to_lexphon_language"]
