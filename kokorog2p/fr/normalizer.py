"""French text normalization for G2P processing.

This module provides French-specific text normalization for the G2P pipeline.
"""

import re

from kokorog2p.fr.abbreviations import get_expander
from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer

# Number to word conversion for French temperatures
_ONES_FR = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
_TEENS_FR = [
    "dix",
    "onze",
    "douze",
    "treize",
    "quatorze",
    "quinze",
    "seize",
    "dix-sept",
    "dix-huit",
    "dix-neuf",
]
_TENS_FR = [
    "",
    "dix",
    "vingt",
    "trente",
    "quarante",
    "cinquante",
    "soixante",
    "soixante-dix",
    "quatre-vingt",
    "quatre-vingt-dix",
]


def _number_to_words_fr(n: int) -> str:
    """Convert a number to French words.

    Args:
        n: Number to convert

    Returns:
        French word representation of the number
    """
    if n == 0:
        return "zéro"
    elif n == 1:
        return "un"
    elif n < 10:
        return _ONES_FR[n]
    elif n < 20:
        return _TEENS_FR[n - 10]
    elif n < 70:
        tens_digit = n // 10
        ones_digit = n % 10
        if ones_digit == 0:
            return _TENS_FR[tens_digit]
        elif ones_digit == 1 and tens_digit > 1:
            return f"{_TENS_FR[tens_digit]}-et-un"
        else:
            return f"{_TENS_FR[tens_digit]}-{_ONES_FR[ones_digit]}"
    elif n < 80:
        # 70-79: soixante-dix, soixante-et-onze, etc.
        remainder = n - 60
        if remainder < 10:
            return f"soixante-{_ONES_FR[remainder]}"
        else:
            return f"soixante-{_TEENS_FR[remainder - 10]}"
    elif n < 100:
        # 80-99: quatre-vingt, quatre-vingt-un, etc.
        remainder = n - 80
        if remainder == 0:
            return "quatre-vingts"
        elif remainder < 10:
            return f"quatre-vingt-{_ONES_FR[remainder]}"
        else:
            return f"quatre-vingt-{_TEENS_FR[remainder - 10]}"
    elif n < 1000:
        hundreds_digit = n // 100
        remainder = n % 100
        if hundreds_digit == 1:
            result = "cent"
        else:
            result = f"{_ONES_FR[hundreds_digit]}-cent"
        if remainder == 0 and hundreds_digit > 1:
            result += "s"
        elif remainder > 0:
            result += f"-{_number_to_words_fr(remainder)}"
        return result
    else:
        return str(n)


def _normalize_temperature_fr(match: re.Match) -> str:
    """Normalize temperature expressions for French.

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
        number_words = f"moins {_number_to_words_fr(abs(number))}"
    else:
        number_words = _number_to_words_fr(number)

    # Map unit to full name (French uses "degré(s)")
    if unit == "F":
        if abs(number) <= 1:
            unit_name = "degré Fahrenheit"
        else:
            unit_name = "degrés Fahrenheit"
    elif unit == "C":
        if abs(number) <= 1:
            unit_name = "degré Celsius"
        else:
            unit_name = "degrés Celsius"
    else:
        return match.group(0)

    return f"{number_words} {unit_name}"


class FrenchNormalizer(TextNormalizer):
    """Normalizes French text for G2P processing.

    Handles:
    - Abbreviation expansion (M. → monsieur, lun. → lundi, etc.)
    - Temperature normalization (37°C → trente-sept degrés Celsius)
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
    ):
        """Initialize the French normalizer.

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
        """Initialize French normalization rules in the correct order."""

        # Phase 0: Temperature normalization (BEFORE abbreviation expansion)
        self.add_rule(
            NormalizationRule(
                name="temperature_fahrenheit_celsius",
                pattern=r"(-?\d+)\s*°?\s*([FCfc])\b",
                replacement=_normalize_temperature_fr,
                description="Normalize temperature (37°C → trente-sept degrés Celsius)",
            )
        )

        # Phase 1: Abbreviation expansion (BEFORE other normalizations)
        # This happens in normalize() method, not as a rule

        # Phase 2: Normalize apostrophes FIRST (before quote handling)
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

        # Phase 3: Normalize quotes (including French guillemets)
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

        # Phase 4: Normalize ellipsis
        self.add_rule(
            NormalizationRule(
                name="ellipsis_unicode",
                pattern="\u2026",  # Ellipsis (…)
                replacement="…",
                description="Normalize Unicode ellipsis",
            )
        )

        # Phase 5: Normalize dashes
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
