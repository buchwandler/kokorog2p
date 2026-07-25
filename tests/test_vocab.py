"""Tests for the Kokoro vocabulary module."""

from kokorog2p.vocab import (
    GB_ENGLISH_PHONEMES,
    N_TOKENS,
    PAD_IDX,
    PUNCTUATION,
    UNK_IDX,
    US_ENGLISH_PHONEMES,
    decode,
    encode,
    filter_for_kokoro,
    get_config,
    get_english_vocab,
    get_vocab,
    get_vocab_reverse,
    ids_to_phonemes,
    is_valid_english_phoneme,
    list_tokens,
    phonemes_to_ids,
    validate_for_kokoro,
    vocab_size,
)


class TestVocabLoading:
    """Tests for vocabulary loading from embedded config."""

    def test_get_vocab(self):
        """Test loading vocabulary."""
        vocab = get_vocab()
        assert isinstance(vocab, dict)
        assert len(vocab) > 0
        # Check some known entries
        assert vocab[" "] == 16
        assert vocab["ˈ"] == 156
        assert vocab["."] == 4

    def test_get_vocab_reverse(self):
        """Test loading reverse vocabulary."""
        vocab_rev = get_vocab_reverse()
        assert isinstance(vocab_rev, dict)
        assert vocab_rev[16] == " "
        assert vocab_rev[156] == "ˈ"
        assert vocab_rev[4] == "."

    def test_get_config(self):
        """Test loading full config."""
        config = get_config()
        assert isinstance(config, dict)
        assert "vocab" in config
        assert "n_token" in config
        assert config["n_token"] == 178

    def test_vocab_caching(self):
        """Test that vocab is cached."""
        vocab1 = get_vocab()
        vocab2 = get_vocab()
        assert vocab1 is vocab2  # Same object due to caching


class TestEncodeDecode:
    """Tests for encoding and decoding functions."""

    def test_encode_simple(self):
        """Test encoding simple phonemes."""
        # "h" should map to 50
        ids = encode("h")
        assert ids == [50]

    def test_encode_with_stress(self):
        """Test encoding phonemes with stress."""
        # "ˈ" should map to 156
        ids = encode("ˈ")
        assert ids == [156]

    def test_encode_with_space(self):
        """Test encoding with spaces."""
        ids = encode("h ɛ", add_spaces=True)
        assert 16 in ids  # Space token

        ids_no_space = encode("h ɛ", add_spaces=False)
        assert 16 not in ids_no_space

    def test_decode_simple(self):
        """Test decoding simple indices."""
        text = decode([50])
        assert text == "h"

    def test_decode_with_stress(self):
        """Test decoding indices with stress."""
        text = decode([50, 156, 86, 54, 31])
        assert "h" in text
        assert "ˈ" in text

    def test_encode_decode_roundtrip(self):
        """Test encoding then decoding returns original."""
        original = "hˈɛlO"
        ids = encode(original)
        decoded = decode(ids)
        assert decoded == original

    def test_decode_skips_padding(self):
        """Test that decode skips padding tokens."""
        text = decode([0, 50, 0, 86, 0], skip_special=True)
        assert text == "hɛ"

    def test_decode_keeps_padding(self):
        """Test that decode can keep padding tokens."""
        # PAD_IDX (0) has no mapping, so it's skipped anyway
        text = decode([0, 50, 86], skip_special=False)
        assert "h" in text


class TestValidation:
    """Tests for validation functions."""

    def test_validate_valid_string(self):
        """Test validation of valid phoneme string."""
        is_valid, invalid = validate_for_kokoro("hˈɛlO")
        assert is_valid is True
        assert invalid == []

    def test_validate_invalid_string(self):
        """Test validation of invalid phoneme string."""
        is_valid, invalid = validate_for_kokoro("hˈɛlO§")
        assert is_valid is False
        assert "§" in invalid

    def test_validate_with_space(self):
        """Test validation with space character."""
        is_valid, _invalid = validate_for_kokoro("hˈɛlO wˈɜɹld")
        assert is_valid is True

    def test_validate_with_punctuation(self):
        """Test validation with punctuation."""
        is_valid, _invalid = validate_for_kokoro("hˈɛlO!")
        assert is_valid is True


class TestFiltering:
    """Tests for filtering functions."""

    def test_filter_removes_invalid(self):
        """Test that filter removes invalid characters."""
        result = filter_for_kokoro("hˈɛlO§")
        assert result == "hˈɛlO"
        assert "§" not in result

    def test_filter_with_replacement(self):
        """Test filtering with replacement character."""
        result = filter_for_kokoro("hˈɛlO§", replacement="?")
        assert "?" in result

    def test_filter_keeps_valid(self):
        """Test that filter keeps valid characters."""
        original = "hˈɛlO wˈɜɹld!"
        result = filter_for_kokoro(original)
        assert result == original


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_phonemes_to_ids(self):
        """Test phonemes_to_ids function."""
        ids = phonemes_to_ids("hˈɛlO")
        assert isinstance(ids, list)
        assert all(isinstance(i, int) for i in ids)

    def test_ids_to_phonemes(self):
        """Test ids_to_phonemes function."""
        ids = [50, 156, 86, 54, 31]
        text = ids_to_phonemes(ids)
        assert isinstance(text, str)

    def test_roundtrip(self):
        """Test roundtrip conversion."""
        original = "hˈɛlO wˈɜɹld"
        ids = phonemes_to_ids(original)
        recovered = ids_to_phonemes(ids)
        assert recovered == original


class TestEnglishVocab:
    """Tests for English-specific vocabulary sets."""

    def test_us_english_phonemes(self):
        """Test US English phoneme set."""
        assert "O" in US_ENGLISH_PHONEMES  # US diphthong
        assert "æ" in US_ENGLISH_PHONEMES  # TRAP vowel
        assert "ɾ" in US_ENGLISH_PHONEMES  # Flap

    def test_gb_english_phonemes(self):
        """Test GB English phoneme set."""
        assert "Q" in GB_ENGLISH_PHONEMES  # GB diphthong
        assert "a" in GB_ENGLISH_PHONEMES  # TRAP vowel
        assert "ː" in GB_ENGLISH_PHONEMES  # Length mark

    def test_get_english_vocab_us(self):
        """Test getting US vocabulary."""
        vocab = get_english_vocab(british=False)
        assert vocab == US_ENGLISH_PHONEMES

    def test_get_english_vocab_gb(self):
        """Test getting GB vocabulary."""
        vocab = get_english_vocab(british=True)
        assert vocab == GB_ENGLISH_PHONEMES

    def test_is_valid_english_phoneme(self):
        """Test phoneme validation."""
        assert is_valid_english_phoneme("h", british=False) is True
        assert is_valid_english_phoneme("O", british=False) is True
        assert is_valid_english_phoneme("Q", british=True) is True
        assert is_valid_english_phoneme(" ") is True
        assert is_valid_english_phoneme(".", british=False) is True


class TestPunctuation:
    """Tests for punctuation set."""

    def test_punctuation_set(self):
        """Test punctuation set contents."""
        assert "." in PUNCTUATION
        assert "," in PUNCTUATION
        assert "!" in PUNCTUATION
        assert "?" in PUNCTUATION
        assert "—" in PUNCTUATION


class TestConstants:
    """Tests for vocabulary constants."""

    def test_n_tokens(self):
        """Test N_TOKENS constant."""
        assert N_TOKENS == 178

    def test_pad_idx(self):
        """Test PAD_IDX constant."""
        assert PAD_IDX == 0

    def test_unk_idx(self):
        """Test UNK_IDX constant."""
        assert UNK_IDX == 0

    def test_vocab_size(self):
        """Test vocab_size function."""
        assert vocab_size() == 178

    def test_list_tokens(self):
        """Test list_tokens function."""
        tokens = list_tokens()
        assert isinstance(tokens, list)
        assert len(tokens) == N_TOKENS
