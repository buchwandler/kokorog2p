"""SpeechMarkdown annotation support for kokorog2p.

This module parses SpeechMarkdown annotations like:
- (word)[ipa:"pɪˈkɑːn"]
- (word)[/ˈpi.kæn/]
- (word)[lang:"fr-FR"]

Annotations are converted to SSMD under the hood so both formats can be used
in the same text.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from kokorog2p.attr_parser import parse_attributes
from kokorog2p.ssmd import (
    phonemize_with_ssmd,
    preprocess_ssmd,
    remove_ssmd,
)

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase


SPEECHMARKDOWN_REGEX = re.compile(r"\(([^)]+)\)\[([^\]]+)\]")
# Legacy regex for backward compatibility (only colon-separated)
SPEECHMARKDOWN_ATTR_REGEX = re.compile(r"(\w+)\s*:\s*\"([^\"]*)\"")


def _convert_speechmarkdown_to_ssmd(text: str) -> str:
    def replace_match(match: re.Match[str]) -> str:
        word = match.group(1)
        raw_attrs = match.group(2).strip()
        ph_value: str | None = None
        lang_value: str | None = None

        if raw_attrs.startswith("/") and raw_attrs.endswith("/") and len(raw_attrs) > 1:
            # Shorthand IPA: (word)[/phonemes/]
            ph_value = raw_attrs.strip("/")
        else:
            # Convert SpeechMarkdown colon syntax to equals syntax for parsing
            # ipa:"value" -> ipa="value"
            normalized_attrs = raw_attrs.replace(":", "=")
            attrs, _warnings = parse_attributes(normalized_attrs)

            if "ipa" in attrs:
                ph_value = attrs["ipa"]
            if "lang" in attrs:
                lang_value = attrs["lang"].lower().replace("_", "-")

        parts: list[str] = []
        if ph_value is not None:
            parts.append(f'ph="{ph_value}"')
        if lang_value is not None:
            parts.append(f'lang="{lang_value}"')

        if not parts:
            return word

        return f"[{word}]{{{' '.join(parts)}}}"

    return SPEECHMARKDOWN_REGEX.sub(replace_match, text)


def process_speechmarkdown(
    text: str,
) -> tuple[str, list[str], dict[int, str], dict[int, str]]:
    """Preprocess text with SpeechMarkdown annotations.

    Returns the same tuple as preprocess_ssmd and supports SSMD input as well.
    """
    converted = _convert_speechmarkdown_to_ssmd(text)
    clean_text, tokens, phoneme_features, language_features = preprocess_ssmd(converted)
    return clean_text, tokens, phoneme_features, language_features


def phonemize_with_speechmarkdown(
    text: str,
    language: str = "en-us",
    g2p: G2PBase | None = None,
    g2p_factory: Callable[[str], G2PBase] | None = None,
) -> str:
    """Phonemize text with SpeechMarkdown and SSMD annotations."""
    converted = _convert_speechmarkdown_to_ssmd(text)
    return phonemize_with_ssmd(
        converted,
        language=language,
        g2p=g2p,
        g2p_factory=g2p_factory,
    )


def remove_speechmarkdown(text: str) -> str:
    """Remove SpeechMarkdown annotations, keeping only words."""
    converted = _convert_speechmarkdown_to_ssmd(text)
    return remove_ssmd(converted)


__all__ = [
    "SPEECHMARKDOWN_REGEX",
    "SPEECHMARKDOWN_ATTR_REGEX",
    "process_speechmarkdown",
    "phonemize_with_speechmarkdown",
    "remove_speechmarkdown",
]
