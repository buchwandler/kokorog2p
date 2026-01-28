"""Kokoro TTS vocabulary and token-to-index mapping.

This module provides the official Kokoro-82M vocabulary mapping from
phonemes/punctuation to token indices used by the model.

The vocabulary is loaded from the embedded Kokoro model config and provides:
- Token to index mapping (for encoding)
- Index to token mapping (for decoding)
- Validation of phoneme strings against the model vocabulary
"""

from functools import lru_cache
from typing import Final

from kokorog2p.data import get_kokoro_vocab, load_kokoro_config

# =============================================================================
# Load vocabulary from embedded config
# =============================================================================


@lru_cache(maxsize=1)
def _load_vocab() -> dict[str, int]:
    """Load and cache the Kokoro vocabulary."""
    return get_kokoro_vocab()


@lru_cache(maxsize=1)
def _load_vocab_reverse() -> dict[int, str]:
    """Load and cache the reverse vocabulary mapping."""
    return {v: k for k, v in _load_vocab().items()}


@lru_cache(maxsize=1)
def _load_vocab_v11_zh() -> dict[str, int]:
    """Load and cache the Kokoro v1.1-zh vocabulary."""
    from kokorog2p.data import get_kokoro_v11_zh_vocab

    return get_kokoro_v11_zh_vocab()


@lru_cache(maxsize=1)
def _load_vocab_reverse_v11_zh() -> dict[int, str]:
    """Load and cache the reverse v1.1-zh vocabulary mapping."""
    return {v: k for k, v in _load_vocab_v11_zh().items()}


@lru_cache(maxsize=1)
def _load_vocab_v11_de() -> dict[str, int]:
    """Load and cache the Kokoro v1.1-de vocabulary."""
    from kokorog2p.data import get_kokoro_v11_de_vocab

    return get_kokoro_v11_de_vocab()


@lru_cache(maxsize=1)
def _load_vocab_reverse_v11_de() -> dict[int, str]:
    """Load and cache the reverse v1.1-de vocabulary mapping."""
    return {v: k for k, v in _load_vocab_v11_de().items()}


@lru_cache(maxsize=1)
def _load_config() -> dict:
    """Load and cache the full Kokoro config."""
    return load_kokoro_config()


# =============================================================================
# Vocabulary accessors (lazy loading)
# =============================================================================


def get_vocab(model: str = "1.0") -> dict[str, int]:
    """Get the Kokoro vocabulary mapping (token -> index).

    Args:
        model: Model variant to load vocab for:
            - "1.0": Base multilingual Kokoro model (default)
            - "1.1": Chinese-specific Kokoro v1.1 model with Zhuyin

    Returns:
        Dictionary mapping tokens to their indices.
    """
    if model == "1.1":
        return _load_vocab_v11_zh()
    elif model == "1.1-zh":
        return _load_vocab_v11_zh()
    elif model == "1.1-de":
        return _load_vocab_v11_de()
    return _load_vocab()


def get_vocab_reverse(model: str = "1.0") -> dict[int, str]:
    """Get the reverse Kokoro vocabulary mapping (index -> token).

    Args:
        model: Model variant to load vocab for (same options as get_vocab).

    Returns:
        Dictionary mapping indices to their tokens.
    """
    if model == "1.1":
        return _load_vocab_reverse_v11_zh()
    elif model == "1.1-zh":
        return _load_vocab_reverse_v11_zh()
    elif model == "1.1-de":
        return _load_vocab_reverse_v11_de()
    return _load_vocab_reverse()


def get_config() -> dict:
    """Get the full Kokoro model configuration.

    Returns:
        Dictionary containing the full model config.
    """
    return _load_config()


# =============================================================================
# Constants (computed from config)
# =============================================================================

# Special token indices
PAD_IDX: Final[int] = 0
UNK_IDX: Final[int] = 0  # Unknown tokens map to padding

# Model configuration
N_TOKENS: Final[int] = 178  # Total vocabulary size (from config.n_token)


# =============================================================================
# English-specific subsets
# =============================================================================

# Phonemes used in US English
US_ENGLISH_PHONEMES: Final[frozenset[str]] = frozenset(
    [
        # Vowels
        "A",
        "I",
        "O",
        "W",
        "Y",  # Diphthongs
        "i",
        "u",
        "æ",
        "ɑ",
        "ɔ",
        "ə",
        "ɛ",
        "ɜ",
        "ɪ",
        "ʊ",
        "ʌ",
        "ᵻ",
        "ᵊ",
        # Consonants
        "b",
        "d",
        "f",
        "h",
        "j",
        "k",
        "l",
        "m",
        "n",
        "p",
        "s",
        "t",
        "v",
        "w",
        "z",
        "ð",
        "θ",
        "ŋ",
        "ɡ",
        "ɹ",
        "ɾ",
        "ʃ",
        "ʒ",
        "ʤ",
        "ʧ",
        # Stress
        "ˈ",
        "ˌ",
    ]
)

# Phonemes used in British English
GB_ENGLISH_PHONEMES: Final[frozenset[str]] = frozenset(
    [
        # Vowels
        "A",
        "I",
        "Q",
        "W",
        "Y",  # Diphthongs (Q instead of O)
        "a",
        "i",
        "u",
        "ɑ",
        "ɒ",
        "ɔ",
        "ə",
        "ɛ",
        "ɜ",
        "ɪ",
        "ʊ",
        "ʌ",
        "ᵊ",
        # Consonants
        "b",
        "d",
        "f",
        "h",
        "j",
        "k",
        "l",
        "m",
        "n",
        "p",
        "s",
        "t",
        "v",
        "w",
        "z",
        "ð",
        "θ",
        "ŋ",
        "ɡ",
        "ɹ",
        "ʃ",
        "ʒ",
        "ʤ",
        "ʧ",
        # Stress and length
        "ˈ",
        "ˌ",
        "ː",
    ]
)

# Common punctuation in English text
PUNCTUATION: Final[frozenset[str]] = frozenset(
    [
        ";",
        ":",
        ",",
        ".",
        "!",
        "?",
        "—",
        "…",
        '"',
        "(",
        ")",
        """, """,
    ]
)


# =============================================================================
# Encoding/Decoding Functions
# =============================================================================


def encode(text: str, add_spaces: bool = True, model: str = "1.0") -> list[int]:
    """Convert a phoneme string to token indices.

    Args:
        text: Phoneme string to encode.
        add_spaces: Whether to include space tokens (default True).
        model: Model variant to encode for (default: "1.0").

    Returns:
        List of token indices.

    Example:
        >>> encode("hˈɛlO")
        [50, 156, 86, 54, 31]
    """
    vocab = get_vocab(model=model)
    indices = []
    for char in text:
        if char == " " and not add_spaces:
            continue
        idx = vocab.get(char, UNK_IDX)
        if idx != UNK_IDX or char == " ":
            indices.append(idx)
    return indices


def decode(indices: list[int], skip_special: bool = True, model: str = "1.0") -> str:
    """Convert token indices back to a phoneme string.

    Args:
        indices: List of token indices.
        skip_special: Whether to skip padding/unknown tokens.
        model: Model variant to decode from (default: "1.0").

    Returns:
        Phoneme string.

    Example:
        >>> decode([50, 156, 86, 54, 31])
        'hˈɛlO'
    """
    vocab_reverse = get_vocab_reverse(model=model)
    chars = []
    for idx in indices:
        if skip_special and idx == PAD_IDX:
            continue
        char = vocab_reverse.get(idx)
        if char is not None:
            chars.append(char)
    return "".join(chars)


def validate_for_kokoro(text: str, model: str = "1.0") -> tuple[bool, list[str]]:
    """Validate that all characters in text are in Kokoro vocabulary.

    Args:
        text: Phoneme string to validate.
        model: Model variant to validate against:
            - "1.0": Base multilingual model (default)
            - "1.1": Chinese-specific model with Zhuyin

    Returns:
        Tuple of (is_valid, list_of_invalid_chars).

    Example:
        >>> validate_for_kokoro("hˈɛlO")
        (True, [])
        >>> validate_for_kokoro("hˈɛlO§")
        (False, ['§'])
        >>> validate_for_kokoro("ㄋㄧ2ㄏㄠ3", model="1.1")
        (True, [])
    """
    vocab = get_vocab(model=model)
    invalid = []
    for char in text:
        if char not in vocab:
            invalid.append(char)
    return len(invalid) == 0, invalid


def filter_for_kokoro(text: str, replacement: str = "", model: str = "1.0") -> str:
    """Remove characters not in Kokoro vocabulary.

    Args:
        text: Phoneme string to filter.
        replacement: String to replace invalid characters with.
        model: Model variant to filter for (same options as validate_for_kokoro).

    Returns:
        Filtered phoneme string.

    Example:
        >>> filter_for_kokoro("hˈɛlO§")
        'hˈɛlO'
    """
    vocab = get_vocab(model=model)
    return "".join(char if char in vocab else replacement for char in text)


# =============================================================================
# Utility Functions
# =============================================================================


def get_english_vocab(british: bool = False) -> frozenset[str]:
    """Get the phoneme vocabulary for English.

    Args:
        british: Whether to get British or US vocabulary.

    Returns:
        Frozen set of valid phonemes.
    """
    return GB_ENGLISH_PHONEMES if british else US_ENGLISH_PHONEMES


def is_valid_english_phoneme(char: str, british: bool = False) -> bool:
    """Check if a character is a valid English phoneme.

    Args:
        char: Single character to check.
        british: Whether to check against British or US vocabulary.

    Returns:
        True if the character is a valid English phoneme.
    """
    vocab = GB_ENGLISH_PHONEMES if british else US_ENGLISH_PHONEMES
    return char in vocab or char in PUNCTUATION or char == " "


def phonemes_to_ids(phonemes: str, model: str = "1.0") -> list[int]:
    """Convert phoneme string to model input IDs.

    This is the main function used to prepare text for the Kokoro model.

    Args:
        phonemes: Phoneme string from G2P conversion.
        model: Model variant to encode for (default: "1.0").

    Returns:
        List of token IDs ready for model input.

    Example:
        >>> phonemes_to_ids("hˈɛlO wˈɜɹld!")
        [50, 156, 86, 54, 31, 16, 65, 156, 87, 123, 54, 46, 5]
    """
    return encode(phonemes, add_spaces=True, model=model)


def ids_to_phonemes(ids: list[int], model: str = "1.0") -> str:
    """Convert model output IDs back to phoneme string.

    Args:
        ids: List of token IDs from model.
        model: Model variant to decode from (default: "1.0").

    Returns:
        Phoneme string.

    Example:
        >>> ids_to_phonemes([50, 156, 86, 54, 31])
        'hˈɛlO'
    """
    return decode(ids, skip_special=True, model=model)


# =============================================================================
# Vocabulary info
# =============================================================================


def vocab_size() -> int:
    """Get the vocabulary size.

    Returns:
        Number of tokens in the vocabulary.
    """
    return N_TOKENS


def list_tokens() -> list[str]:
    """List all tokens in the vocabulary.

    Returns:
        List of all tokens sorted by their index.
    """
    vocab_reverse = get_vocab_reverse()
    return [vocab_reverse.get(i, "") for i in range(N_TOKENS)]
