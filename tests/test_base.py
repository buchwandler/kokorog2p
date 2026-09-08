"""Tests for G2PBase utilities."""
import pytest

from kokorog2p.base import G2PBase, resolve_fallback_provider
from kokorog2p.token import GToken


def test_resolve_fallback_provider() -> None:
    assert (
        resolve_fallback_provider(use_espeak_fallback=True, use_goruut_fallback=False)
        == "espeak"
    )
    assert (
        resolve_fallback_provider(use_espeak_fallback=False, use_goruut_fallback=True)
        == "goruut"
    )
    assert (
        resolve_fallback_provider(use_espeak_fallback=False, use_goruut_fallback=False)
        is None
    )

    with pytest.raises(ValueError, match="Cannot use both espeak and goruut"):
        resolve_fallback_provider(use_espeak_fallback=True, use_goruut_fallback=True)
    assert (
        DummyG2P(
            [], use_espeak_fallback=False, use_goruut_fallback=True
        ).fallback_provider
        == "goruut"
    )


class DummyG2P(G2PBase):
    """Minimal G2P implementation for base tests."""

    def __init__(
        self,
        tokens: list[GToken],
        *,
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
    ):
        super().__init__(
            language="en-us",
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
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
