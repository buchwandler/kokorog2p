"""German final-phoneme vowel profile for relative stress processing."""

from typing import Final

# These are the symbols emitted after German IPA/Kokoro normalization. The
# compact Kokoro diphthong symbols are included alongside IPA-like vowels.
GERMAN_VOWELS: Final[frozenset[str]] = frozenset("aɑeɛiɪoɔøœuʊyəɜɐIWAOQY")


__all__ = ["GERMAN_VOWELS"]
