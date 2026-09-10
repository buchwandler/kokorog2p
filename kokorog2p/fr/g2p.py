"""French G2P (Grapheme-to-Phoneme) converter.

A Grapheme-to-Phoneme engine for French, designed for Kokoro TTS models.

Based on misaki French implementation, adapted for kokorog2p architecture.
"""

import re
import unicodedata

from lexphon import DataStore, ProviderError

from kokorog2p._optional import load_spacy_model
from kokorog2p.base import G2PBase
from kokorog2p.fr.lexicon import FrenchLexicon, TokenContext
from kokorog2p.fr.normalizer import FrenchNormalizer
from kokorog2p.lexicons.evidence import LexiconEvidence
from kokorog2p.lexicons.lexphon_backend import LexphonBackend, provider_metadata
from kokorog2p.phonemes import from_espeak, from_goruut
from kokorog2p.pipeline.tokenizer import RegexTokenizer, SpacyTokenizer
from kokorog2p.spacy_models import resolve_spacy_model
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions


def normalize_french_provider_ipa(phonemes: str) -> str:
    """Normalize clean provider IPA for the French target inventory."""
    for old, new in {"ʀ": "ʁ", "r": "ʁ", "ɹ": "ʁ", "g": "ɡ"}.items():
        phonemes = phonemes.replace(old, new)
    return phonemes.replace("ˈ", "").replace("ˌ", "")


class FrenchG2P(G2PBase):
    """French G2P converter using dictionary lookup with fallback options.

    This class provides grapheme-to-phoneme conversion for French text,
    using a gold dictionary with espeak-ng or goruut as fallback for OOV words.

    Example:
        >>> g2p = FrenchG2P()
        >>> tokens = g2p("Bonjour, comment allez-vous?")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    # Punctuation normalization map
    _PUNCT_MAP = {
        chr(171): '"',  # «
        chr(187): '"',  # »
        chr(8216): "'",  # '
        chr(8217): "'",  # '
        chr(8220): '"',  # "
        chr(8221): '"',  # "
        chr(8212): "-",  # —
        chr(8211): "-",  # –
        chr(8230): "...",  # …
    }

    def __init__(
        self,
        language: str = "fr-fr",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_cli: bool = False,
        use_spacy: bool = True,
        spacy_model: str | None = None,
        unk: str = "?",
        lexicons: tuple[str, ...] | None = None,
        store: DataStore | None = None,
        version: str = "1.0",
    ) -> None:
        """Initialize the French G2P converter.

        Args:
            language: Language code (default: 'fr-fr').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_cli: Retained for direct backend compatibility. It does not select
                the Lexphon-owned native fallback provider.
            use_spacy: Whether to use spaCy for tokenization and POS tagging.
            spacy_model: spaCy French model package to load when use_spacy=True
                (e.g., "fr_core_news_sm", "fr_core_news_md", "fr_core_news_lg").
            unk: Character to use for unknown words when fallback is disabled.

        Raises:
            ValueError: If both use_espeak_fallback and use_goruut_fallback are True.
        """

        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
        )

        self.version = version
        self.unk = unk
        if use_spacy and (spacy_model is None or spacy_model.lower() == "auto"):
            spacy_model = resolve_spacy_model(
                language,
                spacy_model=spacy_model,
            ).package
        self.use_spacy = use_spacy
        self.spacy_model = spacy_model

        # Initialize normalizer
        self._normalizer = FrenchNormalizer()

        # Initialize lexicon
        self.lexicon = FrenchLexicon(lexicons=lexicons, store=store)

        # Initialize fallback (lazy)
        self._fallback: LexphonBackend | None = None

        # Initialize spaCy (lazy)
        self._nlp: object | None = None

        # Initialize tokenizers (lazy)
        self._regex_tokenizer: RegexTokenizer | None = None
        self._spacy_tokenizer: SpacyTokenizer | None = None

    @property
    def fallback(self) -> LexphonBackend | None:
        """Lazily initialize the Lexphon provider adapter."""
        if self._fallback is None and self.fallback_provider is not None:
            self._fallback = LexphonBackend(
                self.language, fallback_provider=self.fallback_provider
            )
        return self._fallback

    def _fallback_result(
        self, word: str
    ) -> tuple[str | None, int, dict[str, object] | None]:
        backend = self.fallback
        if backend is None:
            return None, 0, None
        try:
            token = backend.lookup_token(word)
        except ProviderError:
            if self.strict:
                raise
            return None, 0, None
        if token is None or not token.known or token.pronunciation is None:
            return None, 0, None
        metadata = provider_metadata(token)
        if token.provider == "espeak":
            ipa = from_espeak(token.pronunciation)
        elif token.provider == "goruut":
            ipa = from_goruut(token.pronunciation)
        else:
            return None, 0, None
        return normalize_french_provider_ipa(ipa), 3, metadata

    @property
    def nlp(self) -> object:
        """Lazily initialize spaCy."""
        if self._nlp is None:
            self._nlp = load_spacy_model(self.spacy_model, enable=["tok2vec", "tagger"])
        return self._nlp

    @property
    def regex_tokenizer(self) -> RegexTokenizer:
        """Lazily initialize the regex tokenizer."""
        if self._regex_tokenizer is None:
            self._regex_tokenizer = RegexTokenizer(
                track_positions=True,
                use_bracket_matching=True,
                lang=self.language,
            )
        return self._regex_tokenizer

    @property
    def spacy_tokenizer(self) -> SpacyTokenizer:
        """Lazily initialize the spaCy tokenizer."""
        if self._spacy_tokenizer is None:
            self._spacy_tokenizer = SpacyTokenizer(
                nlp=self.nlp,
                track_positions=True,
                use_bracket_matching=True,
                lang=self.language,
            )
        return self._spacy_tokenizer

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text.strip():
            return []

        # Preprocess
        text = self._preprocess(text)

        # Tokenize
        if self.use_spacy:
            tokens = self._tokenize_spacy(text)
        else:
            tokens = self._tokenize_simple(text)

        # Process tokens
        ctx = TokenContext()
        for token in tokens:
            # Skip tokens that already have phonemes (punctuation)
            if token.phonemes is not None:
                continue

            # Try lexicon lookup
            ps, rating = self.lexicon(token.text, token.tag, ctx)

            if ps is not None:
                token.phonemes = ps
                token.set("rating", rating)
            elif self.fallback is not None:
                # Try espeak fallback
                ps, rating, metadata = self._fallback_result(token.text)
                if ps is not None:
                    token.phonemes = ps
                    token.set("rating", rating)
                    if metadata is not None:
                        for key, value in metadata.items():
                            token.set(key, value)

        # Handle remaining unknown words
        for token in tokens:
            if token.phonemes is None and token.is_word:
                token.phonemes = self.unk

        ensure_gtoken_positions(tokens, text)
        return tokens

    def _preprocess(self, text: str) -> str:
        """Preprocess text before G2P conversion.

        Args:
            text: Raw input text.

        Returns:
            Preprocessed text.
        """
        # Normalize Unicode
        text = unicodedata.normalize("NFC", text)

        # Prepared input already owns written-to-spoken semantics; retain only
        # the G2P typography layer in that mode.
        if getattr(self, "_kokorog2p_prepared_input", False):
            text = self._normalizer.normalize_for_g2p(text)
        else:
            text = self._normalizer(text)

        # Normalize punctuation (keep for legacy compatibility)
        for old, new in self._PUNCT_MAP.items():
            text = text.replace(old, new)

        # Remove non-breaking spaces
        text = text.replace("\u00a0", " ")
        text = text.replace("\u202f", " ")

        # Collapse multiple spaces
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _tokenize_spacy(self, text: str) -> list[GToken]:
        """Tokenize text using spaCy.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        processing_tokens = self.spacy_tokenizer.tokenize(text)
        tokens: list[GToken] = []

        for ptoken in processing_tokens:
            token = ptoken.to_gtoken()

            # Handle punctuation
            if ptoken.text and not any(c.isalnum() for c in ptoken.text):
                token.phonemes = self._get_punct_phonemes(ptoken.text)
                token.set("rating", 4)

            tokens.append(token)

        return tokens

    def _tokenize_simple(self, text: str) -> list[GToken]:
        """Simple tokenization without spaCy.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        processing_tokens = self.regex_tokenizer.tokenize(text)
        tokens: list[GToken] = []

        for ptoken in processing_tokens:
            token = ptoken.to_gtoken()

            # Handle punctuation
            if ptoken.text and not any(c.isalnum() for c in ptoken.text):
                token.phonemes = self._get_punct_phonemes(ptoken.text)
                token.set("rating", 4)

            tokens.append(token)

        return tokens

    @staticmethod
    def _get_punct_phonemes(text: str) -> str:
        """Get phonemes for punctuation tokens."""
        # Keep common punctuation
        puncts = frozenset(";:,.!?-\"'()[]—…")
        return "".join("—" if c == "-" else c for c in text if c in puncts)

    def close(self) -> None:
        self.lexicon.close()
        if self._fallback is not None:
            self._fallback.close()
        super().close()

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        Args:
            word: The word to look up.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if not found.
        """
        ps, _ = self.lexicon(word, tag, None)
        return ps

    def lexicon_evidence(
        self, word: str, tag: str | None = None
    ) -> LexiconEvidence | None:
        """Return evidence from the exact configured French G2Lex stack."""
        hit = self.lexicon.lookup_hit(word)
        if hit is None:
            return None
        kind = hit.kind if hit.kind in {"pronunciation", "membership"} else "membership"
        return LexiconEvidence(
            language=self.language,
            lexicon_id=hit.lexicon_id,
            pronunciation=self.lexicon.pronunciation_from_hit(hit, tag),
            kind=kind,
            lexicon_name=hit.name,
            rating=hit.rating,
            phoneme_encoding=hit.phoneme_encoding,
            metadata=hit.metadata,
        )

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
