"""Czech text normalization for kokorog2p.

This module provides Czech-specific text normalization including:
- Temperature normalization (°C, °F)
- Number-to-words conversion
- Quote normalization
- Abbreviation expansion
"""

import re

from kokorog2p.cs.abbreviations import get_expander
from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer


def czech_number_to_words(n: int) -> str:
    """Convert a number (0-999) to Czech words.

    Args:
        n: Integer from 0 to 999.

    Returns:
        Czech word representation of the number.
    """
    if n == 0:
        return "nula"

    # Ones
    ones = [
        "",
        "jedna",
        "dva",
        "tři",
        "čtyři",
        "pět",
        "šest",
        "sedm",
        "osm",
        "devět",
        "deset",
        "jedenáct",
        "dvanáct",
        "třináct",
        "čtrnáct",
        "patnáct",
        "šestnáct",
        "sedmnáct",
        "osmnáct",
        "devatenáct",
    ]

    if 0 <= n < 20:
        return ones[n]

    # Tens
    tens = [
        "",
        "",
        "dvacet",
        "třicet",
        "čtyřicet",
        "padesát",
        "šedesát",
        "sedmdesát",
        "osmdesát",
        "devadesát",
    ]

    # Hundreds
    hundreds = [
        "",
        "sto",
        "dvě stě",
        "tři sta",
        "čtyři sta",
        "pět set",
        "šest set",
        "sedm set",
        "osm set",
        "devět set",
    ]

    if n < 100:
        tens_digit = n // 10
        ones_digit = n % 10
        if ones_digit == 0:
            return tens[tens_digit]
        else:
            return f"{tens[tens_digit]} {ones[ones_digit]}"

    if n < 1000:
        hundreds_digit = n // 100
        remainder = n % 100

        if remainder == 0:
            return hundreds[hundreds_digit]

        # Build compound number
        if remainder < 20:
            return f"{hundreds[hundreds_digit]} {ones[remainder]}"
        else:
            tens_digit = remainder // 10
            ones_digit = remainder % 10
            if ones_digit == 0:
                return f"{hundreds[hundreds_digit]} {tens[tens_digit]}"
            else:
                return (
                    f"{hundreds[hundreds_digit]} {tens[tens_digit]} {ones[ones_digit]}"
                )

    return str(n)  # Fallback for numbers > 999


def normalize_temperature_czech(match: re.Match) -> str:
    """Normalize temperature expressions to Czech words.

    Converts patterns like "25°C" to "dvacet pět stupňů Celsia"
    and "98°F" to "devadesát osm stupňů Fahrenheita".

    Args:
        match: Regex match object containing the temperature.

    Returns:
        Normalized temperature string in Czech.
    """
    temp_str = match.group(1)
    unit = match.group(2)

    # Handle negative temperatures
    is_negative = temp_str.startswith("-")
    if is_negative:
        temp_str = temp_str[1:]

    # Convert to integer
    try:
        temp = int(temp_str)
    except ValueError:
        return match.group(0)  # Return original if conversion fails

    # Convert number to words
    temp_words = czech_number_to_words(abs(temp))

    # Add "minus" for negative temperatures
    if is_negative:
        temp_words = f"minus {temp_words}"

    # Choose unit name
    unit_name = "Celsia" if unit.upper() == "C" else "Fahrenheita"

    # Czech has complex plural forms for "stupeň" (degree)
    # 1 stupeň, 2-4 stupně, 5+ stupňů
    abs_temp = abs(temp)
    if abs_temp == 1:
        degree_word = "stupeň"
    elif 2 <= abs_temp <= 4:
        degree_word = "stupně"
    else:
        degree_word = "stupňů"

    return f"{temp_words} {degree_word} {unit_name}"


class CzechNormalizer(TextNormalizer):
    """Czech text normalizer with abbreviation expansion."""

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
    ) -> None:
        """Initialize the Czech normalizer.

        Args:
            track_changes: Whether to track normalization changes for debugging.
            expand_abbreviations: Whether to expand abbreviations.
            enable_context_detection: Context-aware abbreviation expansion.
        """
        self.expand_abbreviations = expand_abbreviations
        self.abbrev_expander = (
            get_expander(enable_context_detection=enable_context_detection)
            if expand_abbreviations
            else None
        )

        super().__init__(track_changes=track_changes)

    def _initialize_rules(self) -> None:
        """Initialize Czech-specific normalization rules.

        Order matters:
        1. Temperature (before number normalization)
        2. Apostrophes
        3. Czech quotes („ ")
        4. Ellipsis
        5. Dashes
        """
        # Temperature normalization (must come before other number processing)
        # Matches: 25°C, -10°F, 37°c, etc.
        # NOTE: Cannot use \b at the start due to minus sign
        self.add_rule(
            NormalizationRule(
                name="temperature",
                pattern=r"(-?\d+)\s*°?\s*([CFcf])(?=\s|$|[,.;:!?])",
                replacement=normalize_temperature_czech,
                description="Normalize temperature expressions",
            )
        )

        # Apostrophe normalization
        # Convert curly apostrophes to straight apostrophes
        self.add_rule(
            NormalizationRule(
                name="apostrophe_right",
                pattern="\u2019",  # Right single quotation mark (')
                replacement="'",
                description="Normalize right single quotation mark",
            )
        )

        # Czech quotation marks („ and ")
        # Keep Czech quotes or convert to straight quotes
        self.add_rule(
            NormalizationRule(
                name="quote_czech_left",
                pattern="\u201e",  # Double low-9 quotation mark („)
                replacement='"',
                description="Normalize Czech opening quote",
            )
        )

        self.add_rule(
            NormalizationRule(
                name="quote_czech_right",
                pattern="\u201c",  # Left double quotation mark (")
                replacement='"',
                description="Normalize Czech closing quote",
            )
        )

        # Other curly quotes to straight quotes
        self.add_rule(
            NormalizationRule(
                name="quote_right_double",
                pattern="\u201d",  # Right double quotation mark (")
                replacement='"',
                description="Normalize right double quotation mark",
            )
        )

        self.add_rule(
            NormalizationRule(
                name="quote_left_single",
                pattern="\u2018",  # Left single quotation mark (')
                replacement="'",
                description="Normalize left single quotation mark",
            )
        )

        # Guillemets (also used in Czech)
        # Normalize guillemets to curly quotes (preserving directionality)
        self.add_rule(
            NormalizationRule(
                name="quote_guillemet_left",
                pattern="\u00ab",  # Left guillemet («)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize left guillemet to left curly quote",
            )
        )

        self.add_rule(
            NormalizationRule(
                name="quote_guillemet_right",
                pattern="\u00bb",  # Right guillemet (»)
                replacement="\u201d",  # Right curly quote (")
                description="Normalize right guillemet to right curly quote",
            )
        )

        # Ellipsis normalization
        self.add_rule(
            NormalizationRule(
                name="ellipsis",
                pattern="\u2026",  # Horizontal ellipsis (…)
                replacement="…",
                description="Normalize ellipsis character",
            )
        )

        # Dash normalization (em-dash and en-dash to hyphen)
        self.add_rule(
            NormalizationRule(
                name="dash_em",
                pattern="\u2014",  # Em dash (—)
                replacement="—",
                description="Normalize em-dash",
            )
        )

        self.add_rule(
            NormalizationRule(
                name="dash_en",
                pattern="\u2013",  # En dash (–)
                replacement="—",
                description="Normalize en-dash",
            )
        )

    def normalize(self, text: str) -> tuple[str, list]:
        """Normalize Czech text expanding abbreviations then applying rules.

        Normalization order:
        1. Expand abbreviations (if enabled)
        2. Apply other normalization rules (temperature, quotes, etc.)

        Args:
            text: Input text to normalize.

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
