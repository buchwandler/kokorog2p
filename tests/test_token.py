"""Tests for the GToken dataclass."""

from kokorog2p.token import GToken


class TestGToken:
    """Tests for the GToken dataclass."""

    def test_basic_creation(self):
        """Test basic token creation."""
        token = GToken(text="hello")
        assert token.text == "hello"
        assert token.tag == ""
        assert token.whitespace == " "
        assert token.phonemes is None
        assert token.start_ts is None
        assert token.end_ts is None
        assert token._ == {}

    def test_full_creation(self):
        """Test token creation with all fields."""
        token = GToken(
            text="hello",
            tag="NN",
            whitespace="",
            phonemes="hˈɛlO",
            start_ts=0.0,
            end_ts=1.0,
            _={"rating": 4},
        )
        assert token.text == "hello"
        assert token.tag == "NN"
        assert token.whitespace == ""
        assert token.phonemes == "hˈɛlO"
        assert token.start_ts == 0.0
        assert token.end_ts == 1.0
        assert token._["rating"] == 4

    def test_has_phonemes(self):
        """Test has_phonemes property."""
        token1 = GToken(text="hello")
        assert token1.has_phonemes is False

        token2 = GToken(text="hello", phonemes="")
        assert token2.has_phonemes is False

        token3 = GToken(text="hello", phonemes="hˈɛlO")
        assert token3.has_phonemes is True

    def test_is_punctuation(self):
        """Test is_punctuation property."""
        assert GToken(text=".", tag=".").is_punctuation is True
        assert GToken(text=",", tag=",").is_punctuation is True
        assert GToken(text="!", tag="!").is_punctuation is True
        assert GToken(text="!", tag="PUNCT").is_punctuation is True
        assert GToken(text="hello", tag="NN").is_punctuation is False

    def test_is_word(self):
        """Test is_word property."""
        assert GToken(text="hello", tag="NN").is_word is True
        assert GToken(text=".", tag=".").is_word is False
        assert GToken(text=" ", tag="").is_word is False
        assert GToken(text="", tag="").is_word is False

    def test_get_set(self):
        """Test get and set methods for extension dict."""
        token = GToken(text="hello")

        # Test get with default
        assert token.get("rating") is None
        assert token.get("rating", 0) == 0

        # Test set
        token.set("rating", 4)
        assert token.get("rating") == 4
        assert token._["rating"] == 4

    def test_copy(self):
        """Test token copy method."""
        original = GToken(
            text="hello",
            tag="NN",
            phonemes="hˈɛlO",
            rating="espeak",
            _={"rating": 4},
        )

        copy = original.copy()

        # Check values are equal
        assert copy.text == original.text
        assert copy.tag == original.tag
        assert copy.phonemes == original.phonemes
        assert copy.rating == original.rating
        assert copy._["rating"] == 4

        # Check it's a different object
        assert copy is not original
        assert copy._ is not original._

        # Modifying copy shouldn't affect original
        copy.phonemes = "different"
        copy._["rating"] = 5
        assert original.phonemes == "hˈɛlO"
        assert original._["rating"] == 4

    def test_repr(self):
        """Test string representation."""
        token1 = GToken(text="hello", tag="NN")
        assert "GToken" in repr(token1)
        assert "hello" in repr(token1)

        token2 = GToken(text="hello", tag="NN", phonemes="hˈɛlO")
        assert "phonemes" in repr(token2)
        assert "hˈɛlO" in repr(token2)

    def test_default_empty_dict(self):
        """Test that _ defaults to an empty dict."""
        token = GToken(text="test")
        assert token._ == {}
        assert isinstance(token._, dict)
