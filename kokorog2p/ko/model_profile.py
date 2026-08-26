"""Kokoro 82M v1.0 output contract for Korean phonemization."""

from typing import Final

from kokorog2p.vocab import get_vocab

KOKORO_V1_MODEL: Final[str] = "1.0"
KOKORO_V1_VOICE: Final[str] = "jf_alpha"
KOKORO_V1_TOKENIZER_URL: Final[str] = (
    "https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/blob/main/tokenizer.json"
)

# These symbols are meaningful in the linguistic IPA-like representation but
# have no token in Kokoro 82M v1.0. The Japanese voice receives the closest
# supported segmental representation instead.
_LOSSY_SYMBOLS: Final[dict[str, str]] = {"͈": "", "̚": ""}


def model_vocab() -> frozenset[str]:
    """Return the exact character vocabulary used by the bundled v1.0 config."""
    return frozenset(get_vocab(model=KOKORO_V1_MODEL))


def encode_for_model(phonemes: str) -> str:
    """Convert IPA-like Korean output into Kokoro v1.0 model symbols.

    Known Korean prosodic markers absent from the selected tokenizer are
    handled explicitly. Any other unsupported symbol raises instead of being
    silently discarded.
    """
    encoded = "".join(_LOSSY_SYMBOLS.get(char, char) for char in phonemes)
    vocab = model_vocab()
    invalid = sorted({char for char in encoded if char not in vocab})
    if invalid:
        raise ValueError(
            "Kokoro 82M v1.0 tokenizer does not support Korean output symbols: "
            + "".join(invalid)
        )
    return encoded
