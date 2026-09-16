"""Legacy native eSpeak import path backed by ``espeakng-runtime``."""

from kokorog2p.backends.espeak.compat import EspeakWrapper, Phonemizer

__all__ = ["EspeakWrapper", "Phonemizer"]
