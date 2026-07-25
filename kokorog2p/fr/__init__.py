"""French G2P module for kokorog2p."""

from kokorog2p.fr.g2p import FrenchG2P
from kokorog2p.fr.lexicon import FrenchLexicon

# Optional: NumberConverter requires no external deps
try:
    from kokorog2p.fr.numbers import (
        expand_currency,
        expand_numbers,
        expand_time,
        number_to_french,
    )

    __all__ = [
        "FrenchG2P",
        "FrenchLexicon",
        "expand_currency",
        "expand_numbers",
        "expand_time",
        "number_to_french",
    ]
except ImportError:
    __all__ = ["FrenchG2P", "FrenchLexicon"]
