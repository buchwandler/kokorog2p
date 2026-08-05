"""German text normalization for G2P processing."""

from __future__ import annotations

import re

from kokorog2p.de.abbreviations import get_expander
from kokorog2p.de.numbers import expand_structured_numbers
from kokorog2p.de.text_rules import COMPOSITE_ABBREVIATIONS
from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer


class GermanNormalizer(TextNormalizer):
    """Normalize German lexical and structured text before phonemization.

    Structured expressions are classified before the generic abbreviation
    expander. This prevents units from rewriting standalone letters and keeps
    dates, times, decimals, and sentence punctuation distinguishable.
    """

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
    ):
        self.expand_abbreviations = expand_abbreviations
        self.abbrev_expander = (
            get_expander(enable_context_detection=enable_context_detection)
            if expand_abbreviations
            else None
        )
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

    @staticmethod
    def _expand_composites(text: str) -> str:
        for pattern, replacement in COMPOSITE_ABBREVIATIONS:
            text = pattern.sub(replacement, text)
        return text

    @staticmethod
    def _expand_page_label(text: str) -> str:
        return re.sub(r"(?<!\w)S\.(?=\s*\d)", "Seite", text)

    def normalize(self, text: str) -> tuple[str, list]:
        """Normalize semantic forms first, then abbreviations and typography."""

        if not text:
            return text, []
        steps: list = []

        # Composite forms must be recognized before their component Nr./dots.
        if self.expand_abbreviations:
            expanded = self._expand_composites(text)
            text = self._record_change(
                steps,
                "composite_abbreviation",
                text,
                expanded,
                "Expand flexible German composite abbreviations",
            )

        # S. has a numeric guard; consume it while the following value is
        # still numeric, before the numeric pass turns that value into words.
        if self.expand_abbreviations:
            expanded = self._expand_page_label(text)
            text = self._record_change(
                steps,
                "guarded_page_abbreviation",
                text,
                expanded,
                "Expand S. only before a page number",
            )

        expanded = expand_structured_numbers(text)
        text = self._record_change(
            steps,
            "german_structured_numbers",
            text,
            expanded,
            "Normalize German numbers, units, dates, times, currency, and temperature",
        )

        if self.expand_abbreviations and self.abbrev_expander:
            expanded = self.abbrev_expander.expand(text)
            text = self._record_change(
                steps,
                "abbreviation_expansion",
                text,
                expanded,
                "Expand lexical German abbreviations",
            )

        result, rule_steps = super().normalize(text)
        if self.track_changes:
            steps.extend(rule_steps)
        return result, steps

    def __call__(self, text: str) -> str:
        result, _ = self.normalize(text)
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
        """Normalize a single token using lexical rules and typography."""

        if not text:
            return text
        if expand_abbreviations is None:
            expand_abbreviations = self.expand_abbreviations
        result = text
        if expand_abbreviations and self.abbrev_expander:
            entry = self.abbrev_expander.get_abbreviation(result, case_sensitive=True)
            if entry is None:
                entry = self.abbrev_expander.get_abbreviation(
                    result, case_sensitive=False
                )
            if entry is not None:
                if self.abbrev_expander.context_detector:
                    context = self.abbrev_expander.context_detector.detect_context(
                        result, before, after
                    )
                    result = entry.get_expansion(context)
                else:
                    result = entry.expansion
        if apply_rules:
            result = self._apply_rules(result)
        return result
