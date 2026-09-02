"""German G2P typography over semantic text owned by Spokenform."""

from __future__ import annotations

from collections.abc import Iterator

from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


class GermanNormalizer(TextNormalizer):
    """Normalize German lexical and structured text before phonemization.

    Structured expressions are classified before the generic abbreviation
    expander. This prevents units from rewriting standalone letters and keeps
    dates, times, decimals, and sentence punctuation distinguishable.
    """

    def __init__(
        self,
        track_changes: bool = False,
    ):
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize typography rules after semantic normalization."""

        self.add_rule(
            NormalizationRule(
                name="apostrophe_right_single",
                pattern="\u2019",
                replacement="'",
                description="Normalize right single quote to apostrophe",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_left_single",
                pattern="\u2018",
                replacement="'",
                description="Normalize left single quote to apostrophe",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_german_low",
                pattern="\u201e",
                replacement="\u201c",
                description="Normalize German opening quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_unicode",
                pattern="\u2026",
                replacement="…",
                description="Normalize Unicode ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_en_to_em",
                pattern="\u2013",
                replacement="—",
                description="Normalize en dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_em_unicode",
                pattern="\u2014",
                replacement="—",
                description="Normalize em dash",
            )
        )

    def _record_change(
        self, steps: list, name: str, original: str, normalized: str, context: str
    ) -> str:
        if original != normalized and self.track_changes:
            from kokorog2p.pipeline.normalizer import NormalizationStep

            steps.append(
                NormalizationStep(
                    rule_name=name,
                    position=0,
                    original=original,
                    normalized=normalized,
                    context=context,
                )
            )
        return normalized

    def normalize(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> tuple[str, list]:
        """Normalize German typography without semantic expansion."""
        del protected_spans
        return super().normalize(text)

    def __call__(self, text: str) -> str:
        result, _ = self.normalize(text)
        return result

    @staticmethod
    def iter_structured_replacements(text: str) -> Iterator[TextReplacement]:
        """Return no semantic replacements from the G2P normalizer."""
        del text
        return iter(())

    def normalize_for_g2p(self, text: str) -> str:
        """Apply only typography after semantic preparation already occurred."""

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
        """Normalize a token using intrinsic typography rules."""
        del before, after
        if not text:
            return text
        return self._apply_rules(text) if apply_rules else text
