"""Portuguese G2P typography with semantic preparation delegated to spokenform."""

from collections.abc import Iterable, Iterator
from dataclasses import replace

from abbr2words import get_shared_expander
from spokenform import PreparationConfig, prepare_for_kokorog2p
from spokenform import iter_structured_replacements as spokenform_iter

from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


def _semantic_locale(dialect: str) -> str:
    """Map the public Portuguese dialect selector to spokenform's locale."""
    return "pt-pt" if dialect == "pt" else "pt-br"


class PortugueseNormalizer(TextNormalizer):
    """Prepare Portuguese semantics upstream and retain kokorog2p typography."""

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        dialect: str = "br",
    ) -> None:
        """Initialize the Portuguese downstream adapter.

        ``dialect`` remains a compatibility argument: ``br`` selects Brazilian
        Portuguese (``pt-br``), while ``pt`` selects European Portuguese
        (``pt-pt``) for spokenform semantic preparation.
        """
        self.expand_abbreviations = expand_abbreviations
        self.enable_context_detection = enable_context_detection
        self.dialect = dialect
        # Keep the compatibility attribute used by callers and the G2P
        # alignment guard, but never use it for semantic expansion here.
        self.abbrev_expander = (
            get_shared_expander("pt", context=enable_context_detection)
            if expand_abbreviations
            else None
        )
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize Portuguese typography rules only."""
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
        """Prepare Portuguese semantics with spokenform, then apply typography."""
        if not text:
            return text, []

        from kokorog2p.pipeline.normalizer import NormalizationStep

        locale = _semantic_locale(self.dialect)
        config = replace(
            PreparationConfig.for_kokorog2p(locale),
            expand_abbreviations=self.expand_abbreviations,
            context=self.enable_context_detection,
        )
        prepared = prepare_for_kokorog2p(
            text,
            language=locale,
            config=config,
            protected_spans=protected_spans,
        )

        steps: list[NormalizationStep] = []
        if self.track_changes:
            for replacement in prepared.source_replacements:
                steps.append(
                    NormalizationStep(
                        rule_name=replacement.rule or replacement.kind,
                        position=replacement.source_start,
                        original=replacement.source,
                        normalized=replacement.replacement,
                        context=replacement.kind,
                    )
                )

        result, rule_steps = super().normalize(prepared.spoken_text)
        if self.track_changes:
            steps.extend(rule_steps)
        return result, steps

    def __call__(
        self,
        text: str,
        *,
        protected_spans: tuple[tuple[int, int], ...] = (),
    ) -> str:
        """Normalize Portuguese text without tracking change details."""
        result, _ = self.normalize(text, protected_spans=protected_spans)
        return result

    @staticmethod
    def iter_structured_replacements(
        text: str,
        *,
        protected_spans: Iterable[tuple[int, int]] = (),
        dialect: str = "br",
    ) -> Iterator[TextReplacement]:
        """Return spokenform source-aligned Portuguese replacements.

        The compatibility helper defaults to Brazilian Portuguese. The
        run-level pipeline supplies its dialect explicitly through the
        normalizer and centralized spokenform adapter.
        """
        locale = _semantic_locale(dialect)
        return iter(
            TextReplacement(
                start=item.start,
                end=item.end,
                text=item.text,
                kind=item.kind,
            )
            for item in spokenform_iter(
                text,
                language=locale,
                protected_ranges=protected_spans,
            )
        )

    def normalize_for_g2p(self, text: str) -> str:
        """Apply only Portuguese typography after semantic preparation."""
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
        """Normalize token typography without re-running Portuguese semantics."""
        if not text:
            return text

        del before, after, expand_abbreviations
        return self._apply_rules(text) if apply_rules else text
