"""English G2P typography over semantic text owned by Spokenform.

This module extracts the normalization logic from the English G2P implementation
to make it testable, observable, and reusable.
"""

from collections.abc import Iterable, Iterator

from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


class EnglishNormalizer(TextNormalizer):
    """Normalizes English text for G2P processing.

    Handles:
    - Abbreviation expansion (Prof. → Professor, Mon. → Monday, etc.)
    - Apostrophe variants → standard apostrophe (')
    - Quote variants → straight quotes (" and `)
    - Smart backtick/acute handling (inside words → apostrophe, standalone → quote)
    - Ellipsis variants → single ellipsis (…)
    - Dash variants → em dash (—)

    The order of rules is critical for correctness.
    """

    def __init__(
        self,
        track_changes: bool = False,
    ):
        """Initialize the English normalizer.

        Args:
            track_changes: Whether to track normalization changes
        """
        # Semantic expansion is not part of the G2P normalizer.
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize English typography rules in the correct order."""

        # Prepared input owns written-to-spoken semantics; rules are typography-only.

        # Normalize apostrophes FIRST (before quote handling)
        # This ensures contractions are handled correctly
        self.add_rule(
            NormalizationRule(
                name="apostrophe_right_single",
                pattern="\u2019",  # Right single quotation mark (')
                replacement="'",
                description="Normalize right single quote to apostrophe",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_left_single",
                pattern="\u2018",  # Left single quotation mark (')
                replacement="'",
                description="Normalize left single quote to apostrophe",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_modifier_prime",
                pattern="\u02b9",  # Modifier letter prime (ʹ)
                replacement="'",
                description="Normalize modifier prime to apostrophe",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_fullwidth",
                pattern="\uff07",  # Fullwidth apostrophe (＇)
                replacement="'",
                description="Normalize fullwidth apostrophe",
            )
        )

        # Smart backtick/acute/prime handling
        # Normalize to apostrophe ONLY when inside words (contractions)
        # This must happen BEFORE general backtick normalization
        self.add_rule(
            NormalizationRule(
                name="apostrophe_prime_contraction",
                pattern=r"(\w)′(\w)",  # Word + prime + word (U+2032)
                replacement=r"\1'\2",
                description="Normalize prime in contractions (we′re → we're)",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_double_prime_contraction",
                pattern=r"(\w)″(\w)",  # Word + double prime + word (U+2033)
                replacement=r"\1'\2",
                description="Normalize double prime in contractions",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_modifier_acute_contraction",
                pattern=r"(\w)ˊ(\w)",  # Word + modifier acute + word (U+02CA)
                replacement=r"\1'\2",
                description="Normalize modifier acute in contractions",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="backtick_contraction",
                pattern=r"(\w)`(\w)",  # Word + backtick + word
                replacement=r"\1'\2",  # Replace with apostrophe
                description="Normalize backtick in contractions (don`t → don't)",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="acute_contraction",
                pattern=r"(\w)\u00b4(\w)",  # Word + acute + word (´)
                replacement=r"\1'\2",  # Replace with apostrophe
                description="Normalize acute in contractions (don´t → don't)",
            )
        )

        # Normalize quotes
        # Standalone backtick and acute are treated as quotes
        self.add_rule(
            NormalizationRule(
                name="quote_acute_to_backtick",
                pattern="\u00b4",  # Acute accent (´)
                replacement="`",
                description="Normalize standalone acute to backtick",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_double_prime",
                pattern="\u2033",  # Double prime (″)
                replacement='"',
                description="Normalize double prime to quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_fullwidth",
                pattern="\uff02",  # Fullwidth quotation mark (＂)
                replacement='"',
                description="Normalize fullwidth quote",
            )
        )
        # Normalize all directional quotes to curly quotes (preserving directionality)
        # Left/opening quotes → Left curly quote (")
        self.add_rule(
            NormalizationRule(
                name="quote_left_guillemet",
                pattern="\u00ab",  # Left guillemet («)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize left guillemet to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_single_left_angle",
                pattern="\u2039",  # Single left-pointing angle (‹)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize single left angle to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_low_9_single",
                pattern="\u201a",  # Single low-9 quotation mark (‚)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize single low-9 to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_low_9_double",
                pattern="\u201e",  # Double low-9 quotation mark („)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize double low-9 to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_high_reversed_9",
                pattern="\u201f",  # Double high-reversed-9 quotation mark (‟)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize high-reversed-9 to left curly quote",
            )
        )

        # Right/closing quotes → Right curly quote (")
        self.add_rule(
            NormalizationRule(
                name="quote_right_guillemet",
                pattern="\u00bb",  # Right guillemet (»)
                replacement="\u201d",  # Right curly quote (")
                description="Normalize right guillemet to right curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_single_right_angle",
                pattern="\u203a",  # Single right-pointing angle (›)
                replacement="\u201d",  # Right curly quote (")
                description="Normalize single right angle to right curly quote",
            )
        )

        # Note: Existing curly quotes (U+201C, U+201D) are preserved as-is
        # Straight quotes (") remain straight and will be converted by tokenizer

        # Normalize ellipsis
        # Order matters: replace longer sequences first to avoid partial matches
        # Use regex with escaped dots (\.) to match literal dots, not any character
        self.add_rule(
            NormalizationRule(
                name="ellipsis_four_dots",
                pattern=r"\.\.\.\.",  # Four literal dots
                replacement="…",
                description="Normalize four dots to ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_spaced",
                pattern=r"\. \. \.",  # Spaced literal dots
                replacement="…",
                description="Normalize spaced dots to ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_three_dots",
                pattern=r"\.\.\.",  # Three literal dots
                replacement="…",
                description="Normalize three dots to ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_two_dots",
                pattern=r"\.\.",  # Two literal dots
                replacement="…",
                description="Normalize two dots to ellipsis (typo variant)",
            )
        )
        # Clean up spacing around ellipsis
        self.add_rule(
            NormalizationRule(
                name="ellipsis_trim_spaces",
                pattern=r" +… +",
                replacement="…",
                description="Remove spaces around ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_trim_left",
                pattern=" …",
                replacement="…",
                description="Remove space before ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_trim_right",
                pattern="… ",
                replacement="…",
                description="Remove space after ellipsis",
            )
        )

        # Normalize dashes
        # Order matters: do space-surrounded replacements first
        self.add_rule(
            NormalizationRule(
                name="dash_spaced_hyphen",
                pattern=" - ",
                replacement="—",
                description="Normalize spaced hyphen to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_spaced_double",
                pattern=" -- ",
                replacement="—",
                description="Normalize spaced double hyphen to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_double_hyphen",
                pattern="--",
                replacement="—",
                description="Normalize double hyphen to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_en_dash",
                pattern="\u2013",  # En dash (–)
                replacement="—",
                description="Normalize en dash to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_horizontal_bar",
                pattern="\u2015",  # Horizontal bar (―)
                replacement="—",
                description="Normalize horizontal bar to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_figure_dash",
                pattern="\u2012",  # Figure dash (‒)
                replacement="—",
                description="Normalize figure dash to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_minus_sign",
                pattern="\u2212",  # Minus sign (−)
                replacement="—",
                description="Normalize minus sign to em dash",
            )
        )

        # Clean up spacing around dash

        self.add_rule(
            NormalizationRule(
                name="dash_trim_spaces",
                pattern=r" +— +",
                replacement="—",
                description="Remove spaces around dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_trim_left",
                pattern=" —",
                replacement="—",
                description="Remove space before dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_trim_right",
                pattern="— ",
                replacement="—",
                description="Remove space after dash",
            )
        )

        # Note: Single hyphen (-) without spaces is kept for compound words

    def normalize(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> tuple[str, list]:
        """Normalize only English typography and preserve source semantics."""
        del protected_spans
        return super().normalize(text)

    def __call__(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> str:
        result, _ = self.normalize(text, protected_spans=protected_spans)
        return result

    @staticmethod
    def iter_structured_replacements(
        text: str,
        *,
        protected_spans: Iterable[tuple[int, int]] = (),
    ) -> Iterator[TextReplacement]:
        """Return no semantic replacements from the G2P normalizer."""
        del text, protected_spans
        return iter(())

    def normalize_for_g2p(self, text: str) -> str:
        """Apply only English typography after semantic preparation."""
        result, _ = super().normalize(text)
        return result

    def normalize_token(
        self,
        text: str,
        *,
        before: str = "",
        after: str = "",
        apply_rules: bool = True,
    ) -> str:
        """Normalize token typography without re-running English semantics.

        Source-aligned semantic preparation is owned by the full-text/run-level
        path. The legacy semantic arguments remain for API compatibility.

        Args:
            text: Token text to normalize.
            before: Text before the token (for context detection).
            after: Text after the token (for context detection).
            apply_rules: Whether to apply normalization rules.
        Returns:
            Normalized token text.
        """
        if not text:
            return text

        return self._apply_rules(text) if apply_rules else text
