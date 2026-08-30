"""Named, packaged KokoroG2P lexicons."""

from .registry import (
    LexiconSpec,
    available_lexicons,
    get_lexicon_spec,
    normalize_lexicon_selection,
)
from .runtime import (
    LexiconHit,
    SelectedLexicons,
    clear_resource_cache,
    open_selected,
    resource_cache_info,
)

__all__ = [
    "LexiconHit",
    "LexiconSpec",
    "SelectedLexicons",
    "available_lexicons",
    "clear_resource_cache",
    "get_lexicon_spec",
    "normalize_lexicon_selection",
    "open_selected",
    "resource_cache_info",
]
