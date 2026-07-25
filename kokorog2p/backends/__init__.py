"""Backends for phonemization."""

from kokorog2p.backends.espeak import EspeakWrapper, EspeakBackend

# GoruutBackend is optional - only import if pygoruut is installed
try:
    from kokorog2p.backends.goruut import GoruutBackend

    __all__ = ["EspeakBackend", "EspeakWrapper", "GoruutBackend"]
except ImportError:
    __all__ = ["EspeakBackend", "EspeakWrapper"]
