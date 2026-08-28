"""Named, packaged KokoroG2P lexicons."""

from .registry import (
    LexiconSpec,
    available_lexicons,
    get_lexicon_spec,
    normalize_lexicon_selection,
)
from .runtime import LexiconHit, SelectedLexicons, open_selected

__all__ = [
    "LexiconHit",
    "LexiconSpec",
    "SelectedLexicons",
    "available_lexicons",
    "get_lexicon_spec",
    "normalize_lexicon_selection",
    "open_selected",
]
