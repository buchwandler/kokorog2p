"""German lexicon for G2P lookup.

Provides dictionary-based phoneme lookup for German words.
"""

import importlib.resources
import json
from functools import lru_cache

from kokorog2p.de import data


@lru_cache(maxsize=1)
def _load_gold_dictionary(load_gold: bool = True) -> dict[str, str]:
    """Load the German gold dictionary.

    Args:
        load_gold: If True, load the dictionary; if False, return empty dict.

    Returns:
        Dictionary mapping lowercase words to IPA phonemes.
    """
    if not load_gold:
        return {}
    files = importlib.resources.files(data)
    with (files / "de_gold.json").open("r", encoding="utf-8") as f:
        return json.load(f)


class GermanLexicon:
    """German pronunciation lexicon.

    Uses a gold dictionary for lookup with optional fallback.

    Example:
        >>> lexicon = GermanLexicon()
        >>> lexicon.lookup("Haus")
        'haʊ̯s'
    """

    def __init__(
        self,
        strip_stress: bool = False,
        load_silver: bool = True,
        load_gold: bool = True,
    ) -> None:
        """Initialize the German lexicon.

        Args:
            strip_stress: If True, remove stress markers from phonemes.
            load_silver: If True, load silver tier dictionary if available.
                Currently German only has gold dictionary, so this parameter
                is reserved for future use and consistency with English.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary.
                Defaults to True for maximum quality and coverage.
                Set to False when ultra-fast initialization is needed.
        """
        self._gold = _load_gold_dictionary(load_gold=load_gold)
        self._strip_stress = strip_stress
        self.load_silver = load_silver
        self.load_gold = load_gold
        # Silver dictionary not yet available for German

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the lexicon.

        Args:
            word: The word to look up.
            tag: Optional POS tag (not used for German).

        Returns:
            IPA phoneme string if found, None otherwise.
        """
        word_lower = word.lower()
        phonemes = self._gold.get(word_lower)

        if phonemes and self._strip_stress:
            # Remove primary and secondary stress markers
            phonemes = phonemes.replace("ˈ", "").replace("ˌ", "")

        return phonemes

    def __call__(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the lexicon.

        Args:
            word: The word to look up.
            tag: Optional POS tag.

        Returns:
            IPA phoneme string if found, None otherwise.
        """
        return self.lookup(word, tag)

    def is_known(self, word: str) -> bool:
        """Check if a word is in the lexicon.

        Args:
            word: The word to check.

        Returns:
            True if the word is in the lexicon.
        """
        return word.lower() in self._gold

    def __len__(self) -> int:
        """Return the number of entries in the lexicon."""
        return len(self._gold)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"GermanLexicon(entries={len(self)})"
