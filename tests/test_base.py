"""Tests for G2PBase utilities."""

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken


class DummyG2P(G2PBase):
    """Minimal G2P implementation for base tests."""

    def __init__(self, tokens: list[GToken]):
        super().__init__(language="en-us")
        self._tokens = tokens

    def __call__(self, text: str) -> list[GToken]:
        return list(self._tokens)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        return None


class TestG2PBase:
    """Tests for G2PBase helpers."""

    def test_phonemize_preserves_whitespace(self):
        """phonemize should preserve token whitespace exactly."""
        tokens = [
            GToken(text="Hello", phonemes="h", whitespace="   "),
            GToken(text="world", phonemes="w", whitespace=""),
            GToken(text=".", tag=".", whitespace=""),
        ]
        g2p = DummyG2P(tokens)

        assert g2p.phonemize("ignored") == "h   w."
