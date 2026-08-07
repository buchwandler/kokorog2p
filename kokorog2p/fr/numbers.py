"""Deprecated French semantic helper compatibility wrappers.

Semantic preparation now belongs to the released :mod:`spokenform` package.
These functions remain importable for the compatible API window, but none is
used by the French G2P hot path.
"""

import re
import warnings
from dataclasses import replace

from spokenform import NumberPolicy, PreparationConfig, prepare_for_kokorog2p


def _get_num2words():
    try:
        from num2words import num2words
    except ImportError:
        return None
    return num2words


NUM2WORDS_AVAILABLE = _get_num2words() is not None


def _warn_deprecated(name: str) -> None:
    warnings.warn(
        f"kokorog2p.fr.numbers.{name} is deprecated; use spokenform instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def _spokenform_replacements(
    text: str,
    *,
    rule: str,
    protected_spans: tuple[tuple[int, int], ...] = (),
):
    config = replace(
        PreparationConfig.for_kokorog2p("fr"),
        expand_abbreviations=False,
        number_policy=NumberPolicy.STRUCTURED_AND_PLAIN,
    )
    prepared = prepare_for_kokorog2p(
        text,
        language="fr",
        config=config,
        protected_spans=protected_spans,
    )
    return [
        item
        for item in prepared.source_replacements
        if item.rule == rule
        and text[item.source_start : item.source_end] == item.source
    ]


def _apply_replacements(text: str, replacements) -> str:
    for item in reversed(replacements):
        text = text[: item.source_start] + item.replacement + text[item.source_end :]
    return text


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
    _warn_deprecated("number_to_french")
    num2words = _get_num2words()
    if num2words is None:
        raise ImportError(
            "num2words is required for number conversion."
            " Install with: pip install num2words"
        )

    if ordinal:
        return num2words(n, lang="fr", to="ordinal")
    return num2words(n, lang="fr")


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
    _warn_deprecated("expand_numbers")
    protected = tuple(
        (match.start(), match.end())
        for match in re.finditer(r"\b\d+\b", text)
        if int(match.group(0)) > max_value
    )
    return _apply_replacements(
        text,
        _spokenform_replacements(text, rule="fr.number", protected_spans=protected),
    )


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
    _warn_deprecated("expand_time")
    return _apply_replacements(text, _spokenform_replacements(text, rule="fr.time"))


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
    _warn_deprecated("expand_currency")
    return _apply_replacements(text, _spokenform_replacements(text, rule="fr.currency"))


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
    _warn_deprecated("expand_ordinal")
    return _apply_replacements(text, _spokenform_replacements(text, rule="fr.ordinal"))


def is_available() -> bool:
    """Check if num2words is available.

    Returns:
        True if num2words is installed.
    """
    _warn_deprecated("is_available")
    return _get_num2words() is not None
