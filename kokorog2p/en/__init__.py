"""English G2P module for kokorog2p."""

from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.en.lexicon import Lexicon

# Aliases for consistency with other language modules
EnglishLexicon = Lexicon

# Optional: NumberConverter requires num2words
try:
    from kokorog2p.en.numbers import NumberConverter

    # Alias for consistency with other language modules
    EnglishNumberConverter = NumberConverter

    __all__ = [
        "EnglishG2P",
        "EnglishLexicon",
        "EnglishNumberConverter",
        "Lexicon",
        "NumberConverter",
    ]
except ImportError:
    __all__ = ["EnglishG2P", "EnglishLexicon", "Lexicon"]
