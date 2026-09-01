"""French G2P typography over semantics owned by spokenform."""

from collections.abc import Iterator


def get_shared_expander(*args: object, **kwargs: object) -> None:
    del args, kwargs


from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


class FrenchNormalizer(TextNormalizer):
    """Normalizes French text for G2P processing.

    Semantic expansion is provided by ``spokenform``. This adapter retains:
    - Apostrophe variants → standard apostrophe (')
    - Quote variants → straight quotes (" and `)
    - Ellipsis variants → single ellipsis (…)
    - Dash variants → em dash (—)
    - French-specific normalizations (guillemets, etc.)

    The order of rules is critical for correctness.
    """

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        expand_nums: bool = True,
    ):
        """Initialize the French normalizer.

        Args:
            track_changes: Whether to track normalization changes
            expand_abbreviations: Whether to expand abbreviations
            enable_context_detection: Context-aware abbreviation expansion.
            expand_nums: Whether plain and structured numeric semantics should be
                prepared by spokenform. ``False`` deliberately selects the
                upstream ``NONE`` policy so ordinary numbers are not expanded.
        """
        self.expand_abbreviations = expand_abbreviations
        self.enable_context_detection = enable_context_detection
        self.expand_nums = expand_nums
        self.abbrev_expander = (
            get_shared_expander("fr", context=enable_context_detection)
            if expand_abbreviations
            else None
        )
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize French normalization rules in the correct order."""

        # Typography only: semantic replacements are source-aligned upstream.
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

        # Normalize quotes (including French guillemets)
        self.add_rule(
            NormalizationRule(
                name="quote_double_left",
                pattern="\u201c",  # Left double quotation mark (")
                replacement='"',
                description="Normalize left double quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_double_right",
                pattern="\u201d",  # Right double quotation mark (")
                replacement='"',
                description="Normalize right double quote",
            )
        )

        # French guillemets (« and »)
        # Normalize French guillemets to curly quotes (preserving directionality)
        self.add_rule(
            NormalizationRule(
                name="quote_guillemet_left",
                pattern="\u00ab",  # Left guillemet («)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize French opening quote to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_guillemet_right",
                pattern="\u00bb",  # Right guillemet (»)
                replacement="\u201d",  # Right curly quote (")
                description="Normalize French closing quote to right curly quote",
            )
        )

        # Normalize ellipsis
        self.add_rule(
            NormalizationRule(
                name="ellipsis_unicode",
                pattern="\u2026",  # Ellipsis (…)
                replacement="…",
                description="Normalize Unicode ellipsis",
            )
        )

        # Normalize dashes
        self.add_rule(
            NormalizationRule(
                name="dash_en_to_em",
                pattern="\u2013",  # En dash (–)
                replacement="—",
                description="Normalize en dash to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_em_unicode",
                pattern="\u2014",  # Em dash (—)
                replacement="—",
                description="Normalize em dash",
            )
        )

    def normalize(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> tuple[str, list]:
        """Normalize French typography without semantic expansion."""
        del protected_spans
        return super().normalize(text)

    def __call__(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> str:
        """Convenience method to normalize text without tracking.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        result, _ = self.normalize(text, protected_spans=protected_spans)
        return result

    @staticmethod
    def iter_structured_replacements(text: str) -> Iterator[TextReplacement]:
        """Return no semantic replacements from the G2P normalizer."""
        del text
        return iter(())

    def normalize_for_g2p(self, text: str) -> str:
        """Apply only French typography after semantic preparation."""

        result, _ = super().normalize(text)
        return result

    def normalize_token(
        self,
        text: str,
        *,
        before: str = "",
        after: str = "",
        apply_rules: bool = True,
        expand_abbreviations: bool | None = None,
    ) -> str:
        """Normalize token typography without re-running French semantics.

        French semantic ownership is source-aligned and run-level. The
        ``expand_abbreviations`` argument remains for API compatibility but is
        intentionally not used to create a second semantic source of truth.
        """
        if not text:
            return text

        del before, after, expand_abbreviations
        return self._apply_rules(text) if apply_rules else text
