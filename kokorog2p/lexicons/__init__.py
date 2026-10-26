"""Named, externally provisioned KokoroG2P lexicons."""

from .evidence import LexiconEvidence

from .registry import (
    FileLexiconSource,
    LexiconSource,
    LexiconSpec,
    NamedLexiconSource,
    available_lexicons,
    get_lexicon_spec,
    normalize_lexicon_selection,
)
from .runtime import (
    LexiconHit,
    SelectedLexicons,
    clear_resource_cache,
    open_selected,
    open_sources,
    resource_cache_info,
)

__all__ = [
    "FileLexiconSource",
    "LexiconEvidence",
    "LexiconHit",
    "LexiconSource",
    "LexiconSpec",
    "NamedLexiconSource",
    "SelectedLexicons",
    "available_lexicons",
    "clear_resource_cache",
    "get_lexicon_spec",
    "normalize_lexicon_selection",
    "open_selected",
    "open_sources",
    "resource_cache_info",
]
