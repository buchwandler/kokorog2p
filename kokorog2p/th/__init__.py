"""Thai frontend for KokoroG2P."""

from typing import Any

from .g2p import ThaiAnalysis, ThaiG2P, ThaiG2PError
from .normalizer import ThaiNormalizer


def phonemize_th(text: str, **kwargs: Any) -> str:
    """Convenience wrapper for Thai phonemization."""
    return ThaiG2P(**kwargs).phonemize(text)


__all__ = ["ThaiAnalysis", "ThaiG2P", "ThaiG2PError", "ThaiNormalizer", "phonemize_th"]
