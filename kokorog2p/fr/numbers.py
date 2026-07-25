"""French number to words conversion using num2words."""

import re
from collections.abc import Callable

# Try to import num2words
_num2words_fn: Callable[..., str] | None = None
try:
    from num2words import num2words as _n2w

    _num2words_fn = _n2w
    NUM2WORDS_AVAILABLE = True
except ImportError:
    NUM2WORDS_AVAILABLE = False


def number_to_french(n: int, ordinal: bool = False) -> str:
    """Convert a number to French words using num2words.

    Args:
        n: Integer to convert.
        ordinal: If True, return ordinal form (premier, deuxième, etc.)

    Returns:
        French word representation.

    Raises:
        ImportError: If num2words is not installed.

    Example:
        >>> number_to_french(42)
        'quarante-deux'
        >>> number_to_french(1, ordinal=True)
        'premier'
    """
    if _num2words_fn is None:
        raise ImportError(
            "num2words is required for number conversion. "
            "Install with: pip install num2words"
        )

    if ordinal:
        return _num2words_fn(n, lang="fr", to="ordinal")
    return _num2words_fn(n, lang="fr")


def expand_numbers(text: str, max_value: int = 1000000) -> str:
    """Expand numbers in text to French words.

    Args:
        text: Text containing numbers.
        max_value: Maximum value to expand (larger numbers kept as-is).

    Returns:
        Text with numbers expanded.

    Example:
        >>> expand_numbers("J'ai 3 pommes et 42 oranges.")
        "J'ai trois pommes et quarante-deux oranges."
    """
    if not NUM2WORDS_AVAILABLE:
        return text

    def replace_match(match: re.Match[str]) -> str:
        num = int(match.group(0))
        if num <= max_value:
            return number_to_french(num)
        return match.group(0)

    return re.sub(r"\b\d+\b", replace_match, text)


def expand_time(text: str) -> str:
    """Expand time expressions like 14h30.

    Args:
        text: Text containing time expressions.

    Returns:
        Text with times expanded.

    Example:
        >>> expand_time("Le rendez-vous est à 14h30.")
        'Le rendez-vous est à quatorze heures trente.'
    """
    if not NUM2WORDS_AVAILABLE:
        return text

    def replace_time(match: re.Match[str]) -> str:
        hours = int(match.group(1))
        minutes = match.group(2)
        result = number_to_french(hours) + " heure"
        if hours > 1:
            result += "s"
        if minutes:
            mins = int(minutes)
            if mins > 0:
                result += " " + number_to_french(mins)
        return result

    return re.sub(r"\b(\d{1,2})h(\d{2})?\b", replace_time, text)


def expand_currency(text: str) -> str:
    """Expand currency amounts.

    Args:
        text: Text containing currency amounts.

    Returns:
        Text with currency expanded.

    Example:
        >>> expand_currency("Ça coûte 5€.")
        'Ça coûte cinq euros.'
    """
    if not NUM2WORDS_AVAILABLE:
        return text

    # Euro
    text = re.sub(
        r"(\d+)\s*€",
        lambda m: (
            number_to_french(int(m.group(1)))
            + (" euro" if int(m.group(1)) == 1 else " euros")
        ),
        text,
    )

    # Dollar
    text = re.sub(
        r"\$\s*(\d+)",
        lambda m: (
            number_to_french(int(m.group(1)))
            + (" dollar" if int(m.group(1)) == 1 else " dollars")
        ),
        text,
    )

    return text


def expand_ordinal(text: str) -> str:
    """Expand ordinal numbers like 1er, 2ème, etc.

    Args:
        text: Text containing ordinal numbers.

    Returns:
        Text with ordinals expanded.

    Example:
        >>> expand_ordinal("Le 1er janvier")
        'Le premier janvier'
    """
    if not NUM2WORDS_AVAILABLE:
        return text

    # Match patterns like 1er, 1ère, 2e, 2ème, 2nd, 2nde, etc.
    def replace_ordinal(match: re.Match[str]) -> str:
        num = int(match.group(1))
        suffix = match.group(2).lower()

        # Handle feminine forms
        if suffix in ("ère", "re", "nde"):
            # For feminine, we need to modify the output
            ordinal = number_to_french(num, ordinal=True)
            # Convert masculine to feminine
            if ordinal.endswith("premier"):
                ordinal = ordinal[:-7] + "première"
            elif ordinal.endswith("second"):
                ordinal = ordinal[:-6] + "seconde"
            return ordinal

        return number_to_french(num, ordinal=True)

    # Match ordinal patterns
    text = re.sub(
        r"\b(\d+)(er|ère|re|e|ème|nd|nde)\b",
        replace_ordinal,
        text,
        flags=re.IGNORECASE,
    )

    return text


def is_available() -> bool:
    """Check if num2words is available.

    Returns:
        True if num2words is installed.
    """
    return NUM2WORDS_AVAILABLE
