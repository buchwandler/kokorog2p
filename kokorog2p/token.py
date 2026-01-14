"""Token dataclass for G2P processing."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GToken:
    """
    A token representing a word or text unit with optional phoneme information.

    Attributes:
        text: The original text of the token.
        tag: Part-of-speech tag (e.g., 'NN', 'VB', 'JJ').
        whitespace: Trailing whitespace after this token.
        phonemes: The phonemic transcription of the token.
        start_ts: Start timestamp for audio alignment.
        end_ts: End timestamp for audio alignment.
        rating: Quality rating of the phoneme transcription.
        _: Extension dictionary for custom attributes.
    """

    text: str
    tag: str = ""
    whitespace: str = " "
    phonemes: str | None = None
    start_ts: float | None = None
    end_ts: float | None = None
    rating: str | None = None
    _: dict[str, Any] = field(default_factory=dict)

    @property
    def has_phonemes(self) -> bool:
        """Check if this token has phonemes assigned."""
        return self.phonemes is not None and len(self.phonemes) > 0

    @property
    def is_punctuation(self) -> bool:
        """Check if this token is punctuation."""
        return self.tag in (
            ".",
            ",",
            ":",
            ";",
            "!",
            "?",
            "-",
            "'",
            '"',
            "(",
            ")",
            "PUNCT",
        )

    @property
    def is_word(self) -> bool:
        """Check if this token is a word (not punctuation or whitespace)."""
        return bool(self.text.strip()) and not self.is_punctuation

    def get(self, key: str, default: Any = None) -> Any:
        """Get a custom attribute from the extension dict."""
        return self._.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a custom attribute in the extension dict."""
        self._[key] = value

    def copy(self) -> "GToken":
        """Create a shallow copy of this token."""
        return GToken(
            text=self.text,
            tag=self.tag,
            whitespace=self.whitespace,
            phonemes=self.phonemes,
            start_ts=self.start_ts,
            end_ts=self.end_ts,
            rating=self.rating,
            _=dict(self._),
        )

    def __repr__(self) -> str:
        """Return a string representation of the token."""
        if self.phonemes:
            return (
                f"GToken({self.text!r}, tag={self.tag!r}, phonemes={self.phonemes!r})"
            )
        return f"GToken({self.text!r}, tag={self.tag!r})"
