"""Spanish G2P typography over semantics owned by spokenform."""

from __future__ import annotations

from collections.abc import Iterable, Iterator


def get_shared_expander(*args: object, **kwargs: object) -> None:
    del args, kwargs


from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


class SpanishNormalizer(TextNormalizer):
    """Prepare Spanish semantics upstream and retain kokorog2p typography."""

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
    ) -> None:
        """Initialize the Spanish downstream adapter."""
        self.expand_abbreviations = expand_abbreviations
        self.enable_context_detection = enable_context_detection
        self.abbrev_expander = (
            get_shared_expander("es", context=enable_context_detection)
            if expand_abbreviations
            else None
        )
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize Spanish typography rules only."""
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
                name="quote_left_single",
                pattern="\u2018",
                replacement="'",
                description="Normalize left single quotation mark",
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
        """Normalize Spanish typography without semantic expansion."""
        del protected_spans
        return super().normalize(text)

    def __call__(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> str:
        """Normalize Spanish text and discard change tracking."""
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
        """Apply only Spanish typography after semantic preparation."""
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
        """Normalize token typography without re-running Spanish semantics."""
        if not text:
            return text

        del before, after, expand_abbreviations
        return self._apply_rules(text) if apply_rules else text
