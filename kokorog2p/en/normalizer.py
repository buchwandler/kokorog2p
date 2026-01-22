"""English text normalization for G2P processing.

This module extracts the normalization logic from the English G2P implementation
to make it testable, observable, and reusable.
"""

import re

from kokorog2p.en.abbreviations import get_expander
from kokorog2p.pipeline.normalizer import NormalizationRule, TextNormalizer

# Number to word conversion for hours/minutes
_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
_TEENS = [
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]


def _number_to_words(n: int) -> str:
    """Convert a number (0-999) to words.

    Args:
        n: Number to convert

    Returns:
        Word representation of the number
    """
    if n == 0:
        return "zero"
    elif n < 10:
        return _ONES[n]
    elif n < 20:
        return _TEENS[n - 10]
    elif n < 100:
        tens_digit = n // 10
        ones_digit = n % 10
        if ones_digit == 0:
            return _TENS[tens_digit]
        else:
            return f"{_TENS[tens_digit]} {_ONES[ones_digit]}"
    elif n < 1000:
        hundreds_digit = n // 100
        remainder = n % 100
        result = f"{_ONES[hundreds_digit]} hundred"
        if remainder > 0:
            result += f" {_number_to_words(remainder)}"
        return result
    else:
        # For numbers >= 1000, just return the number as-is
        # (could be extended to handle thousands, millions, etc.)
        return str(n)


def _normalize_temperature(match: re.Match) -> str:
    """Normalize temperature expressions like 98°F, 37°C, etc.

    Args:
        match: Regex match object containing temperature pattern

    Returns:
        Normalized temperature expression
    """
    number_str = match.group(1)
    number = int(number_str)
    unit = match.group(2).upper()
    period = match.group(3)  # Capture optional period

    # Convert number to words
    if number < 0:
        number_words = f"minus {_number_to_words(abs(number))}"
    else:
        number_words = _number_to_words(number)

    # Map unit to full name
    if unit == "F":
        unit_name = "degrees Fahrenheit"
    elif unit == "C":
        unit_name = "degrees Celsius"
    else:
        # Unknown unit, keep as-is
        return match.group(0)

    return f"{number_words} {unit_name}{period}"


def _normalize_time(match: re.Match) -> str:
    """Normalize time expressions like 3:00, 12:30, etc.

    Args:
        match: Regex match object containing time pattern

    Returns:
        Normalized time expression
    """
    hour = int(match.group(1))
    minute_str = match.group(2)

    # Convert hour to words
    hour_words = _number_to_words(hour)

    # Handle minutes
    if minute_str:
        minute = int(minute_str)
        if minute == 0:
            # "3:00" → "three o'clock"
            return f"{hour_words} o'clock"
        else:
            # "3:30" → "three thirty"
            minute_words = _number_to_words(minute)
            # For minutes < 10, say "oh three" for "03"
            if minute < 10:
                return f"{hour_words} oh {minute_words}"
            else:
                return f"{hour_words} {minute_words}"
    else:
        # Just hour number, no colon (e.g., "3" in "at 3 p.m.")
        # Return as-is (will be handled by number normalization later)
        return match.group(0)


class EnglishNormalizer(TextNormalizer):
    """Normalizes English text for G2P processing.

    Handles:
    - Abbreviation expansion (Prof. → Professor, Mon. → Monday, etc.)
    - Apostrophe variants → standard apostrophe (')
    - Quote variants → straight quotes (" and `)
    - Smart backtick/acute handling (inside words → apostrophe, standalone → quote)
    - Ellipsis variants → single ellipsis (…)
    - Dash variants → em dash (—)

    The order of rules is critical for correctness.
    """

    def __init__(
        self,
        track_changes: bool = False,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
    ):
        """Initialize the English normalizer.

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
        """Initialize English normalization rules in the correct order."""

        # Phase 0: Time normalization (BEFORE abbreviation expansion)
        # Convert time patterns like "3:00" to "three o'clock"
        self.add_rule(
            NormalizationRule(
                name="time_with_minutes",
                pattern=r"\b(\d{1,2}):(\d{2})\b",
                replacement=_normalize_time,
                description="Time: 3:00 → three o'clock, 12:30 → twelve thirty",
            )
        )

        # Temperature normalization (98°F → ninety eight degrees Fahrenheit)
        # Pattern now handles optional period after F/C to prevent "C." from being
        # expanded to "circa" by abbreviation expander. The period is captured
        # and preserved in the output.
        self.add_rule(
            NormalizationRule(
                name="temperature_fahrenheit_celsius",
                pattern=r"(-?\d+)\s*°?\s*([FCfc])(\.?)(?=\s|[,;:!?]|$)",
                replacement=_normalize_temperature,
                description="Temperature: 98°F → ninety eight degrees Fahrenheit",
            )
        )

        # Phase 1: Abbreviation expansion (BEFORE other normalizations)
        # This happens first so that expanded text goes through normal processing
        # NOTE: This is handled separately in normalize() method, not as a rule

        # Phase 2: Normalize apostrophes FIRST (before quote handling)
        # This ensures contractions are handled correctly
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
        self.add_rule(
            NormalizationRule(
                name="apostrophe_modifier_prime",
                pattern="\u02b9",  # Modifier letter prime (ʹ)
                replacement="'",
                description="Normalize modifier prime to apostrophe",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_fullwidth",
                pattern="\uff07",  # Fullwidth apostrophe (＇)
                replacement="'",
                description="Normalize fullwidth apostrophe",
            )
        )

        # Phase 3: Smart backtick/acute/prime handling
        # Normalize to apostrophe ONLY when inside words (contractions)
        # This must happen BEFORE general backtick normalization
        self.add_rule(
            NormalizationRule(
                name="apostrophe_prime_contraction",
                pattern=r"(\w)′(\w)",  # Word + prime + word (U+2032)
                replacement=r"\1'\2",
                description="Normalize prime in contractions (we′re → we're)",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_double_prime_contraction",
                pattern=r"(\w)″(\w)",  # Word + double prime + word (U+2033)
                replacement=r"\1'\2",
                description="Normalize double prime in contractions",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="apostrophe_modifier_acute_contraction",
                pattern=r"(\w)ˊ(\w)",  # Word + modifier acute + word (U+02CA)
                replacement=r"\1'\2",
                description="Normalize modifier acute in contractions",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="backtick_contraction",
                pattern=r"(\w)`(\w)",  # Word + backtick + word
                replacement=r"\1'\2",  # Replace with apostrophe
                description="Normalize backtick in contractions (don`t → don't)",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="acute_contraction",
                pattern=r"(\w)\u00b4(\w)",  # Word + acute + word (´)
                replacement=r"\1'\2",  # Replace with apostrophe
                description="Normalize acute in contractions (don´t → don't)",
            )
        )

        # Phase 4: Normalize quotes
        # Standalone backtick and acute are treated as quotes
        self.add_rule(
            NormalizationRule(
                name="quote_acute_to_backtick",
                pattern="\u00b4",  # Acute accent (´)
                replacement="`",
                description="Normalize standalone acute to backtick",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_double_prime",
                pattern="\u2033",  # Double prime (″)
                replacement='"',
                description="Normalize double prime to quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_fullwidth",
                pattern="\uff02",  # Fullwidth quotation mark (＂)
                replacement='"',
                description="Normalize fullwidth quote",
            )
        )
        # Normalize all directional quotes to curly quotes (preserving directionality)
        # Left/opening quotes → Left curly quote (")
        self.add_rule(
            NormalizationRule(
                name="quote_left_guillemet",
                pattern="\u00ab",  # Left guillemet («)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize left guillemet to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_single_left_angle",
                pattern="\u2039",  # Single left-pointing angle (‹)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize single left angle to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_low_9_single",
                pattern="\u201a",  # Single low-9 quotation mark (‚)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize single low-9 to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_low_9_double",
                pattern="\u201e",  # Double low-9 quotation mark („)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize double low-9 to left curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_high_reversed_9",
                pattern="\u201f",  # Double high-reversed-9 quotation mark (‟)
                replacement="\u201c",  # Left curly quote (")
                description="Normalize high-reversed-9 to left curly quote",
            )
        )

        # Right/closing quotes → Right curly quote (")
        self.add_rule(
            NormalizationRule(
                name="quote_right_guillemet",
                pattern="\u00bb",  # Right guillemet (»)
                replacement="\u201d",  # Right curly quote (")
                description="Normalize right guillemet to right curly quote",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="quote_single_right_angle",
                pattern="\u203a",  # Single right-pointing angle (›)
                replacement="\u201d",  # Right curly quote (")
                description="Normalize single right angle to right curly quote",
            )
        )

        # Note: Existing curly quotes (U+201C, U+201D) are preserved as-is
        # Straight quotes (") remain straight and will be converted by tokenizer

        # Phase 5: Normalize ellipsis
        # Order matters: replace longer sequences first to avoid partial matches
        # Use regex with escaped dots (\.) to match literal dots, not any character
        self.add_rule(
            NormalizationRule(
                name="ellipsis_four_dots",
                pattern=r"\.\.\.\.",  # Four literal dots
                replacement="…",
                description="Normalize four dots to ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_spaced",
                pattern=r"\. \. \.",  # Spaced literal dots
                replacement="…",
                description="Normalize spaced dots to ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_three_dots",
                pattern=r"\.\.\.",  # Three literal dots
                replacement="…",
                description="Normalize three dots to ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_two_dots",
                pattern=r"\.\.",  # Two literal dots
                replacement="…",
                description="Normalize two dots to ellipsis (typo variant)",
            )
        )
        # Clean up spacing around ellipsis
        self.add_rule(
            NormalizationRule(
                name="ellipsis_trim_spaces",
                pattern=r" +… +",
                replacement="…",
                description="Remove spaces around ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_trim_left",
                pattern=" …",
                replacement="…",
                description="Remove space before ellipsis",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="ellipsis_trim_right",
                pattern="… ",
                replacement="…",
                description="Remove space after ellipsis",
            )
        )

        # Phase 6: Normalize dashes
        # Order matters: do space-surrounded replacements first
        self.add_rule(
            NormalizationRule(
                name="dash_spaced_hyphen",
                pattern=" - ",
                replacement="—",
                description="Normalize spaced hyphen to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_spaced_double",
                pattern=" -- ",
                replacement="—",
                description="Normalize spaced double hyphen to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_double_hyphen",
                pattern="--",
                replacement="—",
                description="Normalize double hyphen to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_en_dash",
                pattern="\u2013",  # En dash (–)
                replacement="—",
                description="Normalize en dash to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_horizontal_bar",
                pattern="\u2015",  # Horizontal bar (―)
                replacement="—",
                description="Normalize horizontal bar to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_figure_dash",
                pattern="\u2012",  # Figure dash (‒)
                replacement="—",
                description="Normalize figure dash to em dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_minus_sign",
                pattern="\u2212",  # Minus sign (−)
                replacement="—",
                description="Normalize minus sign to em dash",
            )
        )

        # Clean up spacing around dash

        self.add_rule(
            NormalizationRule(
                name="dash_trim_spaces",
                pattern=r" +— +",
                replacement="—",
                description="Remove spaces around dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_trim_left",
                pattern=" —",
                replacement="—",
                description="Remove space before dash",
            )
        )
        self.add_rule(
            NormalizationRule(
                name="dash_trim_right",
                pattern="— ",
                replacement="—",
                description="Remove space after dash",
            )
        )

        # Note: Single hyphen (-) without spaces is kept for compound words

    def normalize(self, text: str) -> tuple[str, list]:
        """Normalize text by applying rules, with careful ordering.

        The order is critical:
        1. Time/temperature patterns (to prevent "C." → "circa")
        2. Abbreviation expansion
        3. All other normalization rules

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

        # Phase 0: Apply time and temperature rules FIRST
        # This prevents "37°C." from being expanded to "37°circa"
        # (where "C." matches the circa abbreviation)
        time_temp_rules = []
        other_rules = []

        for rule in self._rules:
            if rule.name in ("time_with_minutes", "temperature_fahrenheit_celsius"):
                time_temp_rules.append(rule)
            else:
                other_rules.append(rule)

        # Apply time/temperature rules first
        for rule in time_temp_rules:
            result, steps = rule.apply(text, track_changes=self.track_changes)
            all_steps.extend(steps)
            text = result

        # Phase 1: Expand abbreviations
        if self.expand_abbreviations and self.abbrev_expander:
            expanded = self.abbrev_expander.expand(text)
            if expanded != text and self.track_changes:
                # Track abbreviation expansions
                # Find all changes (this is a simplified approach)
                # In a more sophisticated version, we could track individual expansions
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

        # Phase 2: Apply all other normalization rules
        for rule in other_rules:
            result, steps = rule.apply(text, track_changes=self.track_changes)
            all_steps.extend(steps)
            text = result

        return text, all_steps

    def normalize_token(
        self,
        text: str,
        *,
        before: str = "",
        after: str = "",
        apply_rules: bool = True,
        expand_abbreviations: bool | None = None,
    ) -> str:
        """Normalize a single token using the full rule set.

        Args:
            text: Token text to normalize.
            before: Text before the token (for context detection).
            after: Text after the token (for context detection).
            apply_rules: Whether to apply normalization rules.
            expand_abbreviations: Override abbreviation expansion.

        Returns:
            Normalized token text.
        """
        if not text:
            return text

        if expand_abbreviations is None:
            expand_abbreviations = self.expand_abbreviations

        result = text

        if apply_rules:
            time_temp_rules = [
                rule
                for rule in self._rules
                if rule.name in ("time_with_minutes", "temperature_fahrenheit_celsius")
            ]
            result = self._apply_rules(result, time_temp_rules)

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
            other_rules = [
                rule
                for rule in self._rules
                if rule.name
                not in ("time_with_minutes", "temperature_fahrenheit_celsius")
            ]
            result = self._apply_rules(result, other_rules)

        return result

    def add_abbreviation(
        self,
        abbreviation: str,
        expansion: str | dict[str, str],
        description: str = "",
        case_sensitive: bool = False,
    ) -> None:
        """Add or update a custom abbreviation.

        This method allows users to add custom abbreviations or override existing ones.

        Args:
            abbreviation: The abbreviation string (e.g., "Dr.", "Tech.")
            expansion: Either a simple string expansion or a dict mapping context
                names to expansions. For dict, use context names like:
                "default", "title", "place", "time", "academic", "religious"
            description: Optional description of the abbreviation
            case_sensitive: Whether matching should be case-sensitive

        Examples:
            >>> normalizer = EnglishNormalizer()
            >>> # Simple expansion
            >>> normalizer.add_abbreviation("Tech.", "Technology")
            >>> # Context-aware expansion
            >>> normalizer.add_abbreviation(
            ...     "Dr.",
            ...     {"default": "Drive", "title": "Doctor"},
            ...     "Doctor or Drive (context-dependent)"
            ... )
        """
        if not self.expand_abbreviations or not self.abbrev_expander:
            raise RuntimeError(
                "Cannot add abbreviations when expand_abbreviations is disabled. "
                "Create EnglishNormalizer with expand_abbreviations=True."
            )
        self.abbrev_expander.add_custom_abbreviation(
            abbreviation, expansion, description, case_sensitive
        )

    def remove_abbreviation(
        self, abbreviation: str, case_sensitive: bool = False
    ) -> bool:
        """Remove an abbreviation.

        Args:
            abbreviation: The abbreviation to remove (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            True if the abbreviation was found and removed, False otherwise

        Example:
            >>> normalizer = EnglishNormalizer()
            >>> normalizer.remove_abbreviation("Dr.")
            True
        """
        if not self.expand_abbreviations or not self.abbrev_expander:
            raise RuntimeError(
                "Cannot remove abbreviations when expand_abbreviations is disabled. "
                "Create EnglishNormalizer with expand_abbreviations=True."
            )
        return self.abbrev_expander.remove_abbreviation(abbreviation, case_sensitive)

    def has_abbreviation(self, abbreviation: str, case_sensitive: bool = False) -> bool:
        """Check if an abbreviation exists.

        Args:
            abbreviation: The abbreviation to check (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            True if the abbreviation exists, False otherwise

        Example:
            >>> normalizer = EnglishNormalizer()
            >>> normalizer.has_abbreviation("Dr.")
            True
        """
        if not self.expand_abbreviations or not self.abbrev_expander:
            return False
        return self.abbrev_expander.has_abbreviation(abbreviation, case_sensitive)

    def list_abbreviations(self) -> list[str]:
        """Get a list of all registered abbreviations.

        Returns:
            List of abbreviation strings

        Example:
            >>> normalizer = EnglishNormalizer()
            >>> abbrevs = normalizer.list_abbreviations()
            >>> "Dr." in abbrevs
            True
        """
        if not self.expand_abbreviations or not self.abbrev_expander:
            return []
        return self.abbrev_expander.get_abbreviations_list()
