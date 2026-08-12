"""German text normalization for G2P processing."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import replace

from abbr2words import get_shared_expander
from spokenform import PreparationConfig, prepare_for_kokorog2p
from spokenform import iter_structured_replacements as spokenform_iter

from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer
from kokorog2p.types import TextReplacement


def _restore_german_currency_minor_unit(source: str, replacement: str) -> str:
    """Keep the reviewed German currency wording when upstream omits cents."""

    match = re.fullmatch(
        r"(?P<number>[+\-]?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*"
        r"(?P<currency>EUR|€|\$|£|CHF)",
        source.strip(),
        re.IGNORECASE,
    )
    if match is None or "," not in match.group("number"):
        return replacement
    if int(match.group("number").rsplit(",", 1)[1]) == 0:
        return replacement
    minor_unit = {
        "EUR": "Cent",
        "€": "Cent",
        "$": "Cent",
        "£": "Pence",
        "CHF": "Rappen",
    }.get(match.group("currency").upper(), "")
    if minor_unit and not replacement.rstrip().endswith(minor_unit):
        return f"{replacement.rstrip()} {minor_unit}"
    return replacement


def _compatibility_spoken_text(prepared: object, spoken_text: str) -> str:
    """Apply only the narrow German currency compatibility suffix."""

    replacements = getattr(prepared, "source_replacements", ())
    result = spoken_text
    for item in sorted(
        replacements,
        key=lambda replacement: int(getattr(replacement, "output_start", 0)),
        reverse=True,
    ):
        if getattr(item, "rule", None) != "de.currency":
            continue
        original = str(getattr(item, "replacement", ""))
        repaired = _restore_german_currency_minor_unit(
            str(getattr(item, "source", "")), original
        )
        start = int(getattr(item, "output_start", -1))
        end = int(getattr(item, "output_end", -1))
        if repaired != original and 0 <= start <= end <= len(result):
            if result[start:end] == original:
                result = result[:start] + repaired + result[end:]
    return result


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
        self.enable_context_detection = enable_context_detection
        self.abbrev_expander = (
            get_shared_expander("de", context=enable_context_detection)
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

    def normalize(self, text: str) -> tuple[str, list]:
        """Normalize German text through spokenform, then apply G2P typography."""

        if not text:
            return text, []
        steps: list = []

        config = replace(
            PreparationConfig.for_kokorog2p("de"),
            expand_abbreviations=self.expand_abbreviations,
            context=self.enable_context_detection,
        )
        prepared = prepare_for_kokorog2p(text, language="de", config=config)
        for replacement in prepared.source_replacements:
            rule_name = (
                "german_structured_numbers"
                if replacement.kind == "structured"
                else "abbreviation_expansion"
                if replacement.kind == "abbreviation"
                else replacement.rule or replacement.kind
            )
            if self.track_changes:
                from kokorog2p.pipeline.normalizer import NormalizationStep

                steps.append(
                    NormalizationStep(
                        rule_name=rule_name,
                        position=replacement.source_start,
                        original=replacement.source,
                        normalized=replacement.replacement,
                        context=replacement.kind,
                    )
                )

        result, rule_steps = super().normalize(
            _compatibility_spoken_text(prepared, prepared.spoken_text)
        )
        if self.track_changes:
            steps.extend(rule_steps)
        return result, steps

    def __call__(self, text: str) -> str:
        result, _ = self.normalize(text)
        return result

    @staticmethod
    def iter_structured_replacements(text: str) -> Iterator[TextReplacement]:
        """Return spokenform source-aligned replacements for German forms."""

        return iter(
            TextReplacement(
                start=item.start,
                end=item.end,
                text=item.text,
                kind=item.kind,
            )
            for item in spokenform_iter(text, language="de")
        )

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
