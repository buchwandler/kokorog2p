"""Czech typography normalization for prepared text."""

from collections.abc import Iterable, Iterator

from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


class CzechNormalizer(TextNormalizer):
    """Prepare Czech semantics upstream and retain Czech typography."""

    def __init__(
        self,
        track_changes: bool = False,
    ) -> None:
        """Initialize the Czech downstream adapter.

        ``abbrev_expander`` remains available for callers that inspect or
        temporarily toggle the historical compatibility surface. Semantic
        expansion itself is owned by the shared Spokenform preparation pipeline.
        """
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize Czech typography rules only."""
        self.add_rule(
            NormalizationRule(
                name="apostrophe_right",
                pattern="\u2019",
                replacement="'",
                description="Normalize right single quotation mark",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_czech_left",
                pattern="\u201e",
                replacement='"',
                description="Normalize Czech opening quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_czech_right",
                pattern="\u201c",
                replacement='"',
                description="Normalize Czech closing quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_right_double",
                pattern="\u201d",
                replacement='"',
                description="Normalize right double quotation mark",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_left_single",
                pattern="\u2018",
                replacement="'",
                description="Normalize left single quotation mark",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_guillemet_left",
                pattern="\u00ab",
                replacement="\u201c",
                description="Normalize left guillemet to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_guillemet_right",
                pattern="\u00bb",
                replacement="\u201d",
                description="Normalize right guillemet to right curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis",
                pattern="\u2026",
                replacement="…",
                description="Normalize ellipsis character",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_em",
                pattern="\u2014",
                replacement="—",
                description="Normalize em-dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_en",
                pattern="\u2013",
                replacement="—",
                description="Normalize en-dash",
            )
        )

    def normalize(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> tuple[str, list]:
        """Normalize Czech typography without semantic expansion."""
        del protected_spans
        return super().normalize(text)

    def __call__(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> str:
        """Normalize Czech text without tracking change details."""
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
        """Apply only Czech typography after semantic preparation."""
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
        """Normalize token typography without re-running Czech semantics."""
        if not text:
            return text

        del before, after
        return self._apply_rules(text) if apply_rules else text
