"""Tests for offset-aware tokenization."""

from kokorog2p import get_g2p, reset_abbreviations
from kokorog2p.token import GToken
from kokorog2p.tokenization import (
    ensure_gtoken_positions,
    gtoken_to_tokenspan,
    gtokens_to_tokenspans,
    tokenize_with_offsets,
)


class TestTokenizeWithOffsets:
    """Tests for tokenize_with_offsets function."""

    def test_simple_sentence(self):
        """Test simple sentence tokenization."""
        tokens = tokenize_with_offsets("Hello world!")
        assert len(tokens) == 3
        assert tokens[0].text == "Hello"
        assert tokens[0].char_start == 0
        assert tokens[0].char_end == 5
        assert tokens[1].text == "world"
        assert tokens[1].char_start == 6
        assert tokens[1].char_end == 11
        assert tokens[2].text == "!"
        assert tokens[2].char_start == 11
        assert tokens[2].char_end == 12

    def test_without_punctuation(self):
        """Test tokenization without punctuation."""
        tokens = tokenize_with_offsets("Hello world!", keep_punct=False)
        assert len(tokens) == 2
        assert tokens[0].text == "Hello"
        assert tokens[1].text == "world"

    def test_contractions(self):
        """Test contraction handling."""
        tokens = tokenize_with_offsets("I don't know")
        # Should keep "don't" as single token
        assert any(t.text == "don't" for t in tokens)

    def test_abbreviation_preserved(self):
        """Test abbreviations with periods are not split."""
        tokens = tokenize_with_offsets("Hello Mr. Smith", lang="en-us")
        assert [t.text for t in tokens] == ["Hello", "Mr.", "Smith"]
        assert tokens[1].char_start == 6
        assert tokens[1].char_end == 9

    def test_abbreviation_update_reflects_in_tokenization(self):
        """Custom abbreviations should merge without restarting."""
        reset_abbreviations()
        g2p = get_g2p("en-us", use_spacy=False)
        g2p.add_abbreviation("X.Y.", "Ex Why")

        tokens = tokenize_with_offsets("X.Y.", lang="en-us")
        assert [t.text for t in tokens] == ["X.Y."]
        assert tokens[0].char_start == 0
        assert tokens[0].char_end == 4

        reset_abbreviations()

    def test_duplicate_words(self):
        """Test that duplicate words get different offsets."""
        tokens = tokenize_with_offsets("the the cat")
        word_tokens = [t for t in tokens if t.text == "the"]
        assert len(word_tokens) == 2
        assert word_tokens[0].char_start == 0
        assert word_tokens[0].char_end == 3
        assert word_tokens[1].char_start == 4
        assert word_tokens[1].char_end == 7

    def test_punctuation_adjacent(self):
        """Test punctuation adjacent to words."""
        tokens = tokenize_with_offsets("Hello, world!")
        assert len(tokens) == 4
        # "Hello", ",", "world", "!"
        assert tokens[0].text == "Hello"
        assert tokens[0].char_end == 5
        assert tokens[1].text == ","
        assert tokens[1].char_start == 5
        assert tokens[1].char_end == 6

    def test_empty_string(self):
        """Test empty string."""
        tokens = tokenize_with_offsets("")
        assert len(tokens) == 0

    def test_whitespace_only(self):
        """Test whitespace-only string."""
        tokens = tokenize_with_offsets("   ")
        assert len(tokens) == 0


class TestGtokensToTokenspans:
    """Tests for gtokens_to_tokenspans function."""

    def test_simple_conversion(self):
        """Test simple GToken to TokenSpan conversion."""
        gtokens = [
            GToken(text="Hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        clean_text = "Hello world"

        token_spans = gtokens_to_tokenspans(gtokens, clean_text)

        assert len(token_spans) == 2
        assert token_spans[0].text == "Hello"
        assert token_spans[0].char_start == 0
        assert token_spans[0].char_end == 5
        assert token_spans[0].meta.get("phonemes") == "hɛloʊ"
        assert token_spans[1].text == "world"
        assert token_spans[1].char_start == 6
        assert token_spans[1].char_end == 11
        assert token_spans[1].meta.get("phonemes") == "wɝld"

    def test_with_punctuation(self):
        """Test conversion with punctuation tokens."""
        gtokens = [
            GToken(text="Hello", phonemes="hɛloʊ"),
            GToken(text=",", tag=","),
            GToken(text="world", phonemes="wɝld"),
            GToken(text="!", tag="!"),
        ]
        clean_text = "Hello, world!"

        token_spans = gtokens_to_tokenspans(gtokens, clean_text)

        assert len(token_spans) == 4
        assert token_spans[1].text == ","
        assert token_spans[1].char_start == 5
        assert token_spans[3].text == "!"
        assert token_spans[3].char_start == 12

    def test_with_metadata(self):
        """Test that GToken metadata is preserved."""
        gtoken = GToken(text="test", phonemes="tɛst", rating="4", tag="NN")
        gtokens = [gtoken]
        clean_text = "test"

        token_spans = gtokens_to_tokenspans(gtokens, clean_text)

        assert token_spans[0].meta.get("phonemes") == "tɛst"
        assert token_spans[0].meta.get("rating") == "4"
        assert token_spans[0].meta.get("tag") == "NN"

    def test_duplicate_words_different_offsets(self):
        """Test that duplicate words are assigned different offsets."""
        gtokens = [
            GToken(text="the", phonemes="ðə"),
            GToken(text="the", phonemes="ði"),
            GToken(text="end", phonemes="ɛnd"),
        ]
        clean_text = "the the end"

        token_spans = gtokens_to_tokenspans(gtokens, clean_text)

        assert len(token_spans) == 3
        assert token_spans[0].char_start == 0
        assert token_spans[0].char_end == 3
        assert token_spans[1].char_start == 4
        assert token_spans[1].char_end == 7
        assert token_spans[2].char_start == 8
        assert token_spans[2].char_end == 11

    def test_empty_gtokens(self):
        """Test with empty GToken list."""
        token_spans = gtokens_to_tokenspans([], "Hello")
        assert len(token_spans) == 0


class TestGtokenToTokenspan:
    """Tests for single-token conversion."""

    def test_gtoken_to_tokenspan_with_current_pos(self):
        """Token conversion should respect current position."""
        token = GToken(text="the", phonemes="ðə")
        span = gtoken_to_tokenspan(token, "the the", current_pos=4)
        assert span.char_start == 4
        assert span.char_end == 7


class TestEnsureGtokenPositions:
    """Tests for ensure_gtoken_positions."""

    def test_positions_skip_whitespace(self):
        """Position inference should skip whitespace consistently."""
        gtokens = [GToken(text="Hello"), GToken(text="world")]
        ensure_gtoken_positions(gtokens, "Hello   world")
        assert gtokens[0].get("char_start") == 0
        assert gtokens[0].get("char_end") == 5
        assert gtokens[1].get("char_start") == 8
        assert gtokens[1].get("char_end") == 13
