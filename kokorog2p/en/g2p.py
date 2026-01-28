"""English G2P (Grapheme-to-Phoneme) converter."""

from kokorog2p.base import G2PBase
from kokorog2p.en.fallback import EspeakFallback, GoruutFallback
from kokorog2p.en.lexicon import Lexicon, TokenContext
from kokorog2p.en.normalizer import EnglishNormalizer
from kokorog2p.pipeline.models import PhonemeSource, ProcessedText
from kokorog2p.pipeline.tokenizer import RegexTokenizer, SpacyTokenizer
from kokorog2p.token import GToken


class EnglishG2P(G2PBase):
    """English G2P converter using dictionary lookup with fallback options.

    This class provides grapheme-to-phoneme conversion for English text,
    using a tiered dictionary system (gold/silver) with espeak-ng or goruut
    as fallback for out-of-vocabulary words.

    Example:
        >>> g2p = EnglishG2P(language="en-us")
        >>> tokens = g2p("Hello world!")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    def __init__(
        self,
        language: str = "en-us",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_cli: bool = False,
        use_spacy: bool = True,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        phoneme_quotes: str = "curly",
        unk: str = "❓",
        load_silver: bool = True,
        load_gold: bool = True,
        strict: bool = True,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the English G2P converter.

        Args:
            language: Language code ('en-us' or 'en-gb').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_cli: Whether to use the espeak CLI instead of the library.
            use_spacy: Whether to use spaCy for tokenization and POS tagging.
            expand_abbreviations: Whether to expand common abbreviations.
            enable_context_detection: Context-aware abbreviation expansion.
            phoneme_quotes: Quote style in phoneme output:
                - "curly": Use directional quotes " and " (default)
                - "ascii": Use ASCII double quote "
                - "none": Strip quotes from phoneme output
            unk: Character to use for unknown words when fallback is disabled.
            load_silver: If True, load silver tier dictionary (~100k extra entries).
                Defaults to True for backward compatibility and maximum coverage.
                Set to False to save memory (~22-31 MB) and initialization time.
            load_gold: If True, load gold tier dictionary (~170k common words).
                Defaults to True for maximum quality and coverage.
                Set to False when only silver tier or no dictionaries needed.
            strict: If True (default), raise exceptions when backend initialization
                or phonemization fails. If False, log errors and return empty results.
                Note: This only affects fallback backends (espeak/goruut), not
                the primary dictionary lookups.
            version: Model version ("1.0" for multilingual model, "1.1" for
            Chinese model).
                Defaults to "1.0".
            **kwargs: Additional arguments for future compatibility.

        Raises:
            ValueError: If both use_espeak_fallback and use_goruut_fallback are True.
        """
        # Validate phoneme_quotes parameter
        if phoneme_quotes not in ("curly", "ascii", "none"):
            raise ValueError(
                f"phoneme_quotes must be 'curly', 'ascii', or 'none', "
                f"got {phoneme_quotes!r}"
            )

        # Validate mutual exclusion
        if use_espeak_fallback and use_goruut_fallback:
            raise ValueError(
                "Cannot use both espeak and goruut fallback simultaneously. "
                "Please set only one of use_espeak_fallback or "
                "use_goruut_fallback to True."
            )

        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            strict=strict,
        )

        self.version = version
        self.unk = unk
        self.use_spacy = use_spacy
        self.expand_abbreviations = expand_abbreviations
        self.enable_context_detection = enable_context_detection
        self.phoneme_quotes = phoneme_quotes

        # Initialize lexicon
        self.lexicon = Lexicon(
            british=self.is_british, load_silver=load_silver, load_gold=load_gold
        )

        # Initialize fallback (lazy)
        self._fallback: EspeakFallback | GoruutFallback | None = None

        # Initialize spaCy (lazy)
        self._nlp: object | None = None

        # Initialize pipeline components (lazy)
        self._normalizer: EnglishNormalizer | None = None
        self._regex_tokenizer: RegexTokenizer | None = None
        self._spacy_tokenizer: SpacyTokenizer | None = None

    @property
    def fallback(self) -> EspeakFallback | GoruutFallback | None:
        """Lazily initialize the appropriate fallback."""
        if self._fallback is None:
            if self.use_goruut_fallback:
                self._fallback = GoruutFallback(british=self.is_british)
            elif self.use_espeak_fallback:
                self._fallback = EspeakFallback(
                    british=self.is_british, use_cli=self.use_cli
                )
        return self._fallback

    @property
    def nlp(self) -> object:
        """Lazily initialize spaCy with custom tokenizer rules for contractions."""
        if self._nlp is None:
            import spacy

            name = "en_core_web_sm"
            if not spacy.util.is_package(name):
                spacy.cli.download(name)  # type: ignore[attr-defined]
            self._nlp = spacy.load(name, enable=["tok2vec", "tagger"])

            # Add tokenizer exceptions for contractions in our lexicon
            # This prevents spaCy from splitting contractions
            # like "don't" -> "do" + "n't"
            self._add_contraction_exceptions()

        return self._nlp

    @property
    def normalizer(self) -> EnglishNormalizer:
        """Lazily initialize the English text normalizer."""
        if self._normalizer is None:
            self._normalizer = EnglishNormalizer(
                track_changes=False,
                expand_abbreviations=self.expand_abbreviations,
                enable_context_detection=self.enable_context_detection,
            )
        return self._normalizer

    @property
    def regex_tokenizer(self) -> RegexTokenizer:
        """Lazily initialize the regex tokenizer."""
        if self._regex_tokenizer is None:
            self._regex_tokenizer = RegexTokenizer(
                track_positions=True,
                use_bracket_matching=True,
                phoneme_quotes=self.phoneme_quotes,
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
                phoneme_quotes=self.phoneme_quotes,
                lang=self.language,
            )
        return self._spacy_tokenizer

    def _add_contraction_exceptions(self) -> None:
        """Add tokenizer exceptions for contractions found in the lexicon.

        This tells spaCy to treat contractions as single tokens instead of
        splitting them, which allows us to look them up correctly in the lexicon.

        Uses the gold lexicon to identify words that:
        1. Contain apostrophes (formal contractions: don't, can't, etc.)
        2. Are informal contractions that spaCy tends to split (gonna, gotta, etc.)
        """
        # Get all words from lexicon that should be preserved as single tokens
        contractions = set()

        # Strategy 1: Add all words with apostrophes (formal contractions)
        # Include ALL words with apostrophes, regardless of phoneme quality
        for word in self.lexicon.golds.keys():
            if "'" in word:
                contractions.add(word)
                # Also add case variations
                contractions.add(word.capitalize())
                contractions.add(word.upper())

        if self.lexicon.silvers:
            for word in self.lexicon.silvers.keys():
                if "'" in word:
                    contractions.add(word)
                    contractions.add(word.capitalize())
                    contractions.add(word.upper())

        # Strategy 2: Add informal contractions from gold lexicon
        # Use a curated list of common informal contractions that spaCy splits
        # These are validated to exist in gold lexicon with good ratings
        informal_contractions = [
            "gonna",
            "wanna",
            "gotta",
            "kinda",
            "sorta",
            "outta",
            "lemme",
            "gimme",
            "dunno",
            "hafta",
            "woulda",
            "coulda",
            "shoulda",
            "musta",
            "oughta",
            "lotsa",
            "whaddya",
            "whatcha",
            "betcha",
            "gotcha",
            "wontcha",
            "dontcha",
            "didntcha",
        ]

        for word in informal_contractions:
            # Verify it exists in gold lexicon with good quality (rating 4)
            phoneme, rating = self.lexicon.lookup(word)
            if phoneme and rating == 4:
                contractions.add(word)
                contractions.add(word.capitalize())
                contractions.add(word.upper())

        # Strategy 3: Add common contraction patterns (for cases with poor
        # lexicon entries)
        # This catches cases like "should've", "would've" that may have
        # poor lexicon entries
        bases = ["should", "would", "could", "might", "must", "ought"]
        for base in bases:
            for suffix in ["'ve", "'d", "'ll", "n't"]:
                contractions.add(base + suffix)
                contractions.add(base.capitalize() + suffix)

        # Add special cases
        contractions.update(["y'all", "Y'all", "ain't", "Ain't"])

        # Add all identified words as spaCy tokenizer exceptions
        for contraction in contractions:
            # Normalize apostrophes before adding exception
            normalized = contraction.replace("\u2019", "'")
            normalized = normalized.replace("\u2018", "'")
            normalized = normalized.replace("`", "'")
            normalized = normalized.replace("\u00b4", "'")

            # Add as a special case (single token)
            self._nlp.tokenizer.add_special_case(normalized, [{"ORTH": normalized}])  # type: ignore

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text.strip():
            return []

        # Tokenize
        if self.use_spacy:
            tokens = self._tokenize_spacy(text)
        else:
            tokens = self._tokenize_simple(text)

        # Process tokens in reverse order for context
        ctx = TokenContext()
        for i in range(len(tokens) - 1, -1, -1):
            token = tokens[i]

            # Skip tokens that already have phonemes (punctuation)
            if token.phonemes is not None:
                ctx = self._update_context(ctx, token.phonemes, token)
                continue

            # Try lexicon lookup
            ps, rating = self.lexicon(token.text, token.tag, None, ctx)

            if ps is not None:
                token.phonemes = ps
                token.set("rating", rating)
            elif self.fallback is not None:
                # Try espeak fallback
                ps, rating = self.fallback(token.text)
                if ps is not None:
                    token.phonemes = ps
                    token.set("rating", rating)

            # Update context
            ctx = self._update_context(ctx, token.phonemes, token)

        # Handle remaining unknown words
        for token in tokens:
            if token.phonemes is None:
                token.phonemes = self.unk

        # Strip whitespace around punctuation for phoneme output
        self._strip_punctuation(tokens)

        return tokens

    def process_with_debug(self, text: str) -> ProcessedText:
        """Process text with full debugging information.

        This method provides detailed provenance tracking showing:
        - All normalization steps applied
        - Token positions in original text
        - Phoneme source (gold/silver/espeak/etc.) for each token
        - Quote nesting depths

        Args:
            text: Input text to process

        Returns:
            ProcessedText object with full debugging information

        Example:
            >>> g2p = EnglishG2P()
            >>> result = g2p.process_with_debug("I'm here")
            >>> print(result.render_debug())
        """
        if not text.strip():
            return ProcessedText(
                original=text,
                normalized=text,
                tokens=[],
                normalization_log=[],
            )

        # Create normalizer with tracking enabled
        normalizer = EnglishNormalizer(track_changes=True)
        normalized_text, norm_steps = normalizer.normalize(text)

        # Tokenize
        if self.use_spacy:
            processing_tokens = self.spacy_tokenizer.tokenize(normalized_text)
        else:
            processing_tokens = self.regex_tokenizer.tokenize(normalized_text)

        # Process tokens for phonemization (reuse existing logic)
        ctx = TokenContext()
        for i in range(len(processing_tokens) - 1, -1, -1):
            token = processing_tokens[i]

            # Skip if already has phoneme (punctuation)
            if token.phoneme is not None:
                ctx = self._update_context(ctx, token.phoneme, None)
                continue

            # Check if this is punctuation by content
            is_punct = (
                token.text
                and not any(c.isalnum() for c in token.text)
                and "'" not in token.text
            )

            if is_punct:
                token.phoneme = (
                    token.text if token.text in '.,;:!?-—…"\u201c\u201d' else ""
                )
                token.phoneme_source = PhonemeSource.PUNCTUATION
                token.phoneme_rating = 4
                ctx = self._update_context(ctx, token.phoneme, None)
                continue

            # Try lexicon lookup
            ps, rating = self.lexicon(token.text, token.pos_tag, None, ctx)

            if ps is not None:
                token.phoneme = ps
                token.phoneme_source = PhonemeSource.from_rating(rating)
                token.phoneme_rating = rating
            elif self.fallback is not None:
                # Try fallback
                ps, rating = self.fallback(token.text)
                if ps is not None:
                    token.phoneme = ps
                    if self.use_goruut_fallback:
                        token.phoneme_source = PhonemeSource.GORUUT
                    else:
                        token.phoneme_source = PhonemeSource.ESPEAK
                    token.phoneme_rating = rating

            # Update context
            ctx = self._update_context(ctx, token.phoneme, None)

        # Handle remaining unknown words
        for token in processing_tokens:
            if token.phoneme is None:
                token.phoneme = self.unk
                token.phoneme_source = PhonemeSource.UNKNOWN

        return ProcessedText(
            original=text,
            normalized=normalized_text,
            tokens=processing_tokens,
            normalization_log=norm_steps,
        )

    def _tokenize_spacy(self, text: str) -> list[GToken]:
        """Tokenize text using spaCy with custom contraction handling.

        Now uses the pipeline normalizer and tokenizer for consistency.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        # Normalize text
        normalized_text = self.normalizer(text)

        # Tokenize using spaCy tokenizer
        processing_tokens = self.spacy_tokenizer.tokenize(normalized_text)

        # Convert ProcessingToken to GToken and handle punctuation
        tokens: list[GToken] = []
        for ptoken in processing_tokens:
            gtoken = ptoken.to_gtoken()

            # Handle punctuation
            has_alnum = any(c.isalnum() for c in ptoken.text)
            is_punct_tag = ptoken.pos_tag in (
                ".",
                ",",
                "-LRB-",
                "-RRB-",
                "``",
                '""',
                "''",
                ":",
                "$",
                "#",
                "NFP",
            )
            is_punct_text = ptoken.text and not has_alnum

            if is_punct_text or (is_punct_tag and not has_alnum):
                gtoken.phonemes = self._get_punct_phonemes(ptoken.text, ptoken.pos_tag)
                gtoken.set("rating", 4)

            tokens.append(gtoken)

        return tokens

    def _tokenize_simple(self, text: str) -> list[GToken]:
        """Simple tokenization without spaCy.

        Now uses the pipeline normalizer and regex tokenizer for consistency.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        # Normalize text
        normalized_text = self.normalizer(text)

        # Tokenize using regex tokenizer
        processing_tokens = self.regex_tokenizer.tokenize(normalized_text)

        # Convert ProcessingToken to GToken and handle punctuation
        tokens: list[GToken] = []
        for ptoken in processing_tokens:
            gtoken = ptoken.to_gtoken()
            gtoken.tag = ""  # No POS tags in simple tokenizer

            # Handle punctuation (but not contractions with apostrophes)
            if not ptoken.text.isalnum() and "'" not in ptoken.text:
                # Assign phoneme for known punctuation using the same method
                # as the spacy tokenizer for consistency
                gtoken.phonemes = self._get_punct_phonemes(ptoken.text, "")
                gtoken.set("rating", 4)

            tokens.append(gtoken)

        return tokens

    def _get_punct_phonemes(self, text: str, tag: str) -> str:
        """Get phonemes for punctuation tokens.

        For quotes, we use the text itself (which has been converted to curly
        quotes by the tokenizer) rather than relying on spaCy tags which can
        be unreliable for simple alternating quotes.

        The quote characters in the output can be controlled via the
        phoneme_quotes parameter.
        """
        # For non-quote punctuation tags, use the tag mapping
        punct_map = {
            "-LRB-": "(",
            "-RRB-": ")",
        }
        if tag in punct_map:
            return punct_map[tag]

        # Apply quote normalization based on phoneme_quotes setting
        if self.phoneme_quotes == "ascii":
            # Convert curly quotes to ASCII double quotes
            text = text.replace("\u201c", '"').replace("\u201d", '"')
        elif self.phoneme_quotes == "none":
            # Remove all quote characters
            text = text.replace("\u201c", "").replace("\u201d", "").replace('"', "")
        # else: "curly" - keep as-is (default, backward compatible)

        # For all other punctuation (including quotes), use the text itself
        # The tokenizer has already converted quotes to curly quotes with
        # correct directionality (unless phoneme_quotes changes them above)
        puncts = frozenset(';:,.!?—…"""`\u201c\u201d')
        return "".join(c for c in text if c in puncts)

    @staticmethod
    def _strip_punctuation(tokens: list[GToken]) -> None:
        """Remove whitespace around punctuation tokens in phoneme output.

        This removes spaces around punctuation like commas and periods
        in phoneme output.

        Args:
            tokens: List of GToken objects to modify in-place
        """
        for i, token in enumerate(tokens):
            if token.text in [
                ",",
                "—",
                "…",
            ]:
                # Remove trailing whitespace from previous token
                if i > 0:
                    tokens[i - 1].whitespace = ""
                # Remove trailing whitespace from em dash itself
                token.whitespace = ""

    def _update_context(
        self, ctx: TokenContext, phonemes: str | None, token: GToken | None
    ) -> TokenContext:
        """Update context based on processed token."""
        from kokorog2p.en.lexicon import CONSONANTS, VOWELS

        non_quote_puncts = frozenset(";:,.!?—…")

        future_vowel = ctx.future_vowel
        if phonemes:
            for c in phonemes:
                if c in VOWELS:
                    future_vowel = True
                    break
                elif c in CONSONANTS:
                    future_vowel = False
                    break
                elif c in non_quote_puncts:
                    future_vowel = None
                    break

        future_to = (
            token.text.lower() in ("to",) and token.tag in ("TO", "IN", "")
            if token is not None
            else False
        )

        return TokenContext(future_vowel=future_vowel, future_to=future_to)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        Args:
            word: The word to look up.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if not found.
        """
        ps, _ = self.lexicon(word, tag, None, None)
        return ps

    def add_abbreviation(
        self,
        abbreviation: str,
        expansion: str | dict[str, str],
        description: str = "",
        case_sensitive: bool = False,
    ) -> None:
        """Add or update a custom abbreviation.

        This method allows users to add custom abbreviations or override existing ones.
        Changes persist across all uses of this G2P instance and affect the singleton
        abbreviation expander (shared across all instances).

        Args:
            abbreviation: The abbreviation string (e.g., "Dr.", "Tech.")
            expansion: Either a simple string expansion or a dict mapping context
                names to expansions. For dict, use context names like:
                "default", "title", "place", "time", "academic", "religious"
            description: Optional description of the abbreviation
            case_sensitive: Whether matching should be case-sensitive

        Examples:
            >>> g2p = get_g2p("en-us")
            >>> # Simple expansion
            >>> g2p.add_abbreviation("Tech.", "Technology")
            >>> # Context-aware expansion
            >>> g2p.add_abbreviation(
            ...     "Dr.",
            ...     {"default": "Drive", "title": "Doctor"},
            ...     "Doctor or Drive (context-dependent)"
            ... )
            >>> g2p.phonemize("I live on Main Dr.")
            'aɪ lˈɪv ɒn mˈeɪn dɹˈaɪv.'
        """
        self.normalizer.add_abbreviation(
            abbreviation, expansion, description, case_sensitive
        )

    def remove_abbreviation(
        self, abbreviation: str, case_sensitive: bool = False
    ) -> bool:
        """Remove an abbreviation.

        Args:
            abbreviation: The abbreviation to remove (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            True if the abbreviation was found and removed, False otherwise

        Example:
            >>> g2p = get_g2p("en-us")
            >>> g2p.remove_abbreviation("Dr.")
            True
            >>> # Now "Dr." won't be expanded
            >>> g2p.phonemize("Dr. Smith")
            'd r. smˈɪθ'
        """
        return self.normalizer.remove_abbreviation(abbreviation, case_sensitive)

    def has_abbreviation(self, abbreviation: str, case_sensitive: bool = False) -> bool:
        """Check if an abbreviation exists.

        Args:
            abbreviation: The abbreviation to check (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            True if the abbreviation exists, False otherwise

        Example:
            >>> g2p = get_g2p("en-us")
            >>> g2p.has_abbreviation("Dr.")
            True
        """
        return self.normalizer.has_abbreviation(abbreviation, case_sensitive)

    def list_abbreviations(self) -> list[str]:
        """Get a list of all registered abbreviations.

        Returns:
            List of abbreviation strings

        Example:
            >>> g2p = get_g2p("en-us")
            >>> abbrevs = g2p.list_abbreviations()
            >>> "Dr." in abbrevs
            True
        """
        return self.normalizer.list_abbreviations()

    def __repr__(self) -> str:
        return f"EnglishG2P(language={self.language!r}, version={self.version!r})"

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
