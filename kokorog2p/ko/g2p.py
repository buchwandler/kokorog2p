"""Korean G2P (Grapheme-to-Phoneme) converter.

This module provides Korean text to phoneme conversion using MeCab for morphological
analysis and custom phonological rules based on Korean Standard Pronunciation.

Based on g2pK by kyubyong: https://github.com/kyubyong/g2pK

Copyright 2025 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

from .jamo_to_ipa import jamo_to_ipa


class KoreanG2P(G2PBase):
    """Korean G2P using MeCab and Korean phonological rules.

    This class converts Korean text to phonemes using:
    1. Idiom/abbreviation replacement
    2. English to Hangul conversion
    3. MeCab POS tagging
    4. Number spelling
    5. Hangul decomposition
    6. Phonological rules application
    7. Jamo composition

    Example:
        >>> g2p = KoreanG2P()
        >>> tokens = g2p("안녕하세요")
    """

    def __init__(
        self,
        language: str = "ko",
        use_espeak_fallback: bool = False,
        use_goruut_fallback: bool = False,
        load_silver: bool = True,
        load_gold: bool = True,
        use_dict: bool = True,
        group_vowels: bool = False,
        to_syl: bool = False,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the Korean G2P.

        Args:
            language: Language code (e.g., 'ko', 'ko-kr').
            use_espeak_fallback: Whether to use espeak for unknown words.
                Not typically used for Korean. Defaults to False.
            use_goruut_fallback: Whether to use goruut for unknown words.
                Not typically used for Korean. Defaults to False.
            load_silver: Reserved for API consistency. Korean doesn't use
                dictionary tiers. Defaults to True.
            load_gold: Reserved for API consistency. Korean doesn't use
                dictionary tiers. Defaults to True.
            use_dict: Whether to use MeCab dictionary for POS tagging.
                Defaults to True. If False, skips MeCab annotation.
            group_vowels: If True, merge similar vowels (e.g., ㅐ->ㅔ).
                Defaults to False.
            to_syl: If True, compose jamo back to syllables.
                Defaults to False (returns decomposed jamo).
            **kwargs: Additional arguments.
        """
        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
        self.version = version
        self.load_silver = load_silver
        self.load_gold = load_gold
        self.use_dict = use_dict
        self.group_vowels = group_vowels
        self.to_syl = to_syl
        self._g2pk_instance = None

    @property
    def g2pk(self):
        """Lazy initialization of g2pK backend."""
        if self._g2pk_instance is None:
            from .g2pk import G2p

            self._g2pk_instance = G2p()
        return self._g2pk_instance

    def __call__(self, text: str) -> list[GToken]:
        """Convert Korean text to tokens with phonemes.

        Args:
            text: Input Korean text to convert.

        Returns:
            List of GToken objects with phonemes.
        """
        if not text or not text.strip():
            return []

        # Convert to phonemes using g2pK (returns Hangul in phonetic form)
        hangul_phonemes = self.g2pk(
            text,
            descriptive=False,
            verbose=False,
            group_vowels=self.group_vowels,
            to_syl=self.to_syl,
            use_dict=self.use_dict,
        )

        # Convert jamo to IPA phonemes
        ipa_phonemes = jamo_to_ipa(hangul_phonemes) if hangul_phonemes else None

        # Create a single token with the phoneme string
        token = GToken(
            text=text,
            tag="KO",
            whitespace="",
            phonemes=ipa_phonemes if ipa_phonemes else None,
        )
        token.rating = "ko" if ipa_phonemes else None
        tokens = [token]
        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a Korean word and return its phonetic representation.

        Args:
            word: The word to look up.
            tag: Optional POS tag (not used in Korean G2P).

        Returns:
            Phoneme string or None if empty.
        """
        if not word or not word.strip():
            return None

        # Use g2pK to convert the word (returns Hangul in phonetic form)
        hangul_phonemes = self.g2pk(
            word,
            descriptive=False,
            verbose=False,
            group_vowels=self.group_vowels,
            to_syl=self.to_syl,
            use_dict=self.use_dict,
        )

        # Convert jamo to IPA phonemes
        ipa_phonemes = jamo_to_ipa(hangul_phonemes) if hangul_phonemes else None

        return ipa_phonemes if ipa_phonemes else None

    def _phonemize_internal(self, text: str) -> tuple[str, list[GToken] | None]:
        """Internal phonemization logic.

        Args:
            text: Input text.

        Returns:
            Tuple of (phoneme_string, token_list).
        """
        # Convert to phonemes using g2pK (returns Hangul in phonetic form)
        hangul_phonemes = self.g2pk(
            text,
            descriptive=False,
            verbose=False,
            group_vowels=self.group_vowels,
            to_syl=self.to_syl,
            use_dict=self.use_dict,
        )

        # Convert jamo to IPA phonemes
        ipa_phonemes = jamo_to_ipa(hangul_phonemes) if hangul_phonemes else ""

        # Create a token
        token = GToken(
            text=text,
            tag="KO",
            whitespace="",
            phonemes=ipa_phonemes if ipa_phonemes else None,
        )
        token.rating = "ko" if ipa_phonemes else None

        return ipa_phonemes, [token] if ipa_phonemes else None

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
