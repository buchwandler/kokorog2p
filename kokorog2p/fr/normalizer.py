"""French typography normalization for prepared text."""

from collections.abc import Iterator

from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


class FrenchNormalizer(TextNormalizer):
    """Normalize French typography for G2P processing."""

    def __init__(
        self,
        track_changes: bool = False,
    ):
        """Initialize the French typography normalizer."""
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
    ) -> str:
        """Normalize token typography without re-running French semantics.

        French semantic ownership is source-aligned and run-level. The
        intentionally not used to create a second semantic source of truth.
        """
        if not text:
            return text

        del before, after
        return self._apply_rules(text) if apply_rules else text
