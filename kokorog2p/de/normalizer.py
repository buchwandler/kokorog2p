"""German text normalization for G2P processing.

This module provides German-specific text normalization for the G2P pipeline.
"""

import re

from kokorog2p.de.abbreviations import get_expander
from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer

# Number to word conversion for German temperatures
_ONES_DE = [
    "",
    "eins",
    "zwei",
    "drei",
    "vier",
    "fünf",
    "sechs",
    "sieben",
    "acht",
    "neun",
]
_TEENS_DE = [
    "zehn",
    "elf",
    "zwölf",
    "dreizehn",
    "vierzehn",
    "fünfzehn",
    "sechzehn",
    "siebzehn",
    "achtzehn",
    "neunzehn",
]
_TENS_DE = [
    "",
    "",
    "zwanzig",
    "dreißig",
    "vierzig",
    "fünfzig",
    "sechzig",
    "siebzig",
    "achtzig",
    "neunzig",
]


def _number_to_words_de(n: int) -> str:
    """Convert a number to German words.

    Args:
        n: Number to convert

    Returns:
        German word representation of the number
    """
    if n == 0:
        return "null"
    elif n == 1:
        return "ein"  # Use "ein" not "eins" before "Grad"
    elif n < 10:
        return _ONES_DE[n]
    elif n < 20:
        return _TEENS_DE[n - 10]
    elif n < 100:
        tens_digit = n // 10
        ones_digit = n % 10
        if ones_digit == 0:
            return _TENS_DE[tens_digit]
        else:
            # German reverses: 23 = "dreiundzwanzig" (three-and-twenty)
            return f"{_ONES_DE[ones_digit]}und{_TENS_DE[tens_digit]}"
    elif n < 1000:
        hundreds_digit = n // 100
        remainder = n % 100
        if hundreds_digit == 1:
            result = "einhundert"
        else:
            result = f"{_ONES_DE[hundreds_digit]}hundert"
        if remainder > 0:
            result += f"{_number_to_words_de(remainder)}"
        return result
    else:
        return str(n)


def _normalize_temperature_de(match: re.Match) -> str:
    """Normalize temperature expressions for German.

    Args:
        match: Regex match object containing temperature pattern

    Returns:
        Normalized temperature expression
    """
    number_str = match.group(1)
    number = int(number_str)
    unit = match.group(2).upper()

    # Convert number to words
    if number < 0:
        number_words = f"minus {_number_to_words_de(abs(number))}"
    else:
        number_words = _number_to_words_de(number)

    # Map unit to full name (German uses "Grad" = degree)
    if unit == "F":
        unit_name = "Grad Fahrenheit"
    elif unit == "C":
        unit_name = "Grad Celsius"
    else:
        return match.group(0)

    return f"{number_words} {unit_name}"


class GermanNormalizer(TextNormalizer):
    """Normalizes German text for G2P processing.

    Handles:
    - Abbreviation expansion (Prof. → Professor, Mo. → Montag, etc.)
    - Apostrophe variants → standard apostrophe (')
    - Quote variants → straight quotes (" and `)
    - Ellipsis variants → single ellipsis (…)
    - Dash variants → em dash (—)
    - German-specific normalizations (ß handling, etc.)

    The order of rules is critical for correctness.
    """

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
    ):
        """Initialize the German normalizer.

        Args:
            track_changes: Whether to track normalization changes
            expand_abbreviations: Whether to expand abbreviations
            enable_context_detection: Context-aware abbreviation expansion
        """
        self.expand_abbreviations = expand_abbreviations
        self.abbrev_expander = (
            get_expander(enable_context_detection=enable_context_detection)
            if expand_abbreviations
            else None
        )
        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize German normalization rules in the correct order."""

        # Phase 0: Temperature normalization (BEFORE abbreviation expansion)
        self.add_rule(
            NormalizationRule(
                name="temperature_fahrenheit_celsius",
                pattern=r"(-?\d+)\s*°?\s*([FCfc])\b",
                replacement=_normalize_temperature_de,
                description="Temperature: 37°C → siebenunddreißig Grad Celsius",
            )
        )

        # Phase 1: Abbreviation expansion (BEFORE other normalizations)
        # This happens in normalize() method, not as a rule

        # Phase 1: Normalize apostrophes FIRST (before quote handling)
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

        # Phase 2: Normalize quotes
        # Note: We preserve curly quotes (U+201C, U+201D) from source text

        # German-style quotes („ is opening)
        self.add_rule(
            NormalizationRule(
                name="quote_german_low",
                pattern="\u201e",  # Double low-9 quotation mark („)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize German opening quote to left curly quote",
            )
        )

        # Phase 3: Normalize ellipsis
        self.add_rule(
            NormalizationRule(
                name="ellipsis_unicode",
                pattern="\u2026",  # Ellipsis (…)
                replacement="…",
                description="Normalize Unicode ellipsis",
            )
        )

        # Phase 4: Normalize dashes
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

    def normalize(self, text: str) -> tuple[str, list]:
        """Normalize text expanding abbreviations then applying rules.

        Args:
            text: Text to normalize

        Returns:
            Tuple of (normalized_text, list of all normalization steps)
        """
        if not text:
            return text, []

        # Import NormalizationStep here to avoid circular import
        from kokorog2p.pipeline.normalizer import NormalizationStep

        all_steps: list[NormalizationStep] = []

        # Phase 0: Expand abbreviations FIRST
        if self.expand_abbreviations and self.abbrev_expander:
            expanded = self.abbrev_expander.expand(text)
            if expanded != text and self.track_changes:
                # Track abbreviation expansions
                all_steps.append(
                    NormalizationStep(
                        rule_name="abbreviation_expansion",
                        position=0,
                        original=text,
                        normalized=expanded,
                        context="Expand abbreviations to full forms",
                    )
                )
            text = expanded

        # Phase 1+: Apply all other normalization rules
        result, rule_steps = super().normalize(text)

        # Combine all steps
        if self.track_changes:
            all_steps.extend(rule_steps)

        return result, all_steps

    def __call__(self, text: str) -> str:
        """Convenience method to normalize text without tracking.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
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
        """Normalize a single token using the full rule set."""
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
