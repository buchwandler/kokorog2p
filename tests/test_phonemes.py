"""Tests for phoneme vocabularies and conversion functions."""

from kokorog2p.phonemes import (
    AFFRICATE_EXPANSIONS,
    CONSONANTS,
    DIPHTHONG_EXPANSIONS,
    GB_ONLY_PHONES,
    GB_VOCAB,
    SHARED_PHONES,
    STRESS_MARKS,
    US_ONLY_PHONES,
    US_VOCAB,
    VOWELS,
    from_espeak,
    get_vocab,
    to_espeak,
    validate_phonemes,
)


class TestPhonemeVocabularies:
    """Tests for phoneme vocabulary definitions."""

    def test_shared_phones_count(self):
        """Test shared phones count."""
        assert len(SHARED_PHONES) == 41

    def test_us_only_phones_count(self):
        """Test US-only phones count."""
        assert len(US_ONLY_PHONES) == 5
        assert US_ONLY_PHONES == frozenset("Oæɾᵻʔ")

    def test_gb_only_phones_count(self):
        """Test GB-only phones count."""
        assert len(GB_ONLY_PHONES) == 4
        assert GB_ONLY_PHONES == frozenset("Qaɒː")

    def test_us_vocab_count(self):
        """Test US vocabulary count."""
        assert len(US_VOCAB) == 46

    def test_gb_vocab_count(self):
        """Test GB vocabulary count."""
        assert len(GB_VOCAB) == 45

    def test_vocab_composition(self):
        """Test vocabulary composition."""
        assert US_VOCAB == SHARED_PHONES | US_ONLY_PHONES
        assert GB_VOCAB == SHARED_PHONES | GB_ONLY_PHONES

    def test_us_specific_phonemes(self):
        """Test US-specific phonemes."""
        # O represents oʊ diphthong
        assert "O" in US_VOCAB
        assert "O" not in GB_VOCAB

        # æ for TRAP vowel
        assert "æ" in US_VOCAB
        assert "æ" not in GB_VOCAB

        # ɾ for flap/tap
        assert "ɾ" in US_VOCAB
        assert "ɾ" not in GB_VOCAB

    def test_gb_specific_phonemes(self):
        """Test GB-specific phonemes."""
        # Q represents əʊ diphthong
        assert "Q" in GB_VOCAB
        assert "Q" not in US_VOCAB

        # a for TRAP vowel
        assert "a" in GB_VOCAB
        assert "a" not in US_VOCAB

        # ː for vowel lengthening
        assert "ː" in GB_VOCAB
        assert "ː" not in US_VOCAB


class TestFromEspeak:
    """Tests for espeak to Kokoro conversion."""

    def test_diphthong_conversion(self):
        """Test diphthong conversion."""
        # a^ɪ -> I (eye sound)
        assert "I" in from_espeak("a^ɪ")

        # a^ʊ -> W (ow sound)
        assert "W" in from_espeak("a^ʊ")

        # e^ɪ -> A (ay sound)
        assert "A" in from_espeak("e^ɪ")

        # ɔ^ɪ -> Y (oy sound)
        assert "Y" in from_espeak("ɔ^ɪ")

    def test_affricate_conversion(self):
        """Test affricate conversion."""
        # d^ʒ -> ʤ
        assert "ʤ" in from_espeak("d^ʒ")

        # t^ʃ -> ʧ
        assert "ʧ" in from_espeak("t^ʃ")

    def test_consonant_conversion(self):
        """Test consonant conversion."""
        # r -> ɹ
        assert from_espeak("r") == "ɹ"

    def test_tie_character_removal(self):
        """Test tie character removal."""
        result = from_espeak("t^ʃ")
        assert "^" not in result

    def test_us_specific_conversion(self):
        """Test US-specific conversions."""
        # o^ʊ -> O
        result = from_espeak("o^ʊ", british=False)
        assert "O" in result

        # Remove length markers in US
        result = from_espeak("ɜː", british=False)
        assert "ː" not in result

    def test_gb_specific_conversion(self):
        """Test GB-specific conversions."""
        # ə^ʊ -> Q
        result = from_espeak("ə^ʊ", british=True)
        assert "Q" in result

    def test_us_word_conversion(self):
        """Test US word conversion."""
        result = from_espeak("mˈɜːt^ʃəntʃˌɪp", british=False)
        assert result == "mˈɜɹʧəntʃˌɪp"

    def test_gb_word_conversion(self):
        """Test US word conversion."""
        result = from_espeak("mˈɜːt^ʃəntʃˌɪp", british=True)
        assert result == "mˈɜːʧəntʃˌɪp"


class TestToEspeak:
    """Tests for Kokoro to espeak conversion."""

    def test_diphthong_expansion(self):
        """Test diphthong expansion."""
        assert to_espeak("A") == "eɪ"
        assert to_espeak("I") == "aɪ"
        assert to_espeak("O") == "oʊ"
        assert to_espeak("Q") == "əʊ"
        assert to_espeak("W") == "aʊ"
        assert to_espeak("Y") == "ɔɪ"

    def test_affricate_expansion(self):
        """Test affricate expansion."""
        assert to_espeak("ʤ") == "dʒ"
        assert to_espeak("ʧ") == "tʃ"

    def test_small_schwa_expansion(self):
        """Test small schwa expansion."""
        assert to_espeak("ᵊ") == "ə"

    def test_complex_phoneme_string(self):
        """Test conversion of complex phoneme string."""
        result = to_espeak("hˈɛlO")
        assert "hˈɛloʊ" == result


class TestValidatePhonemes:
    """Tests for phoneme validation."""

    def test_valid_us_phonemes(self):
        """Test valid US phonemes."""
        assert validate_phonemes("hˈɛlO", british=False) is True
        assert validate_phonemes("wˈɜɹld", british=False) is True
        assert validate_phonemes("kˈæt", british=False) is True

    def test_valid_gb_phonemes(self):
        """Test valid GB phonemes."""
        assert validate_phonemes("hˈɛlQ", british=True) is True
        assert validate_phonemes("kˈat", british=True) is True

    def test_invalid_phonemes(self):
        """Test invalid phonemes."""
        # US phonemes in GB context
        assert validate_phonemes("kˈæt", british=True) is False

        # GB phonemes in US context
        assert validate_phonemes("hˈɛlQ", british=False) is False

    def test_empty_string(self):
        """Test empty string validation."""
        assert validate_phonemes("", british=False) is True
        assert validate_phonemes("", british=True) is True


class TestGetVocab:
    """Tests for get_vocab function."""

    def test_get_us_vocab(self):
        """Test getting US vocabulary."""
        vocab = get_vocab(british=False)
        assert vocab == US_VOCAB

    def test_get_gb_vocab(self):
        """Test getting GB vocabulary."""
        vocab = get_vocab(british=True)
        assert vocab == GB_VOCAB


class TestPhonemeCategories:
    """Tests for phoneme category sets."""

    def test_vowels_set(self):
        """Test vowels set contains expected phonemes."""
        assert "a" in VOWELS
        assert "i" in VOWELS
        assert "u" in VOWELS
        assert "ə" in VOWELS
        assert "A" in VOWELS  # Diphthong
        assert "O" in VOWELS  # Diphthong

    def test_consonants_set(self):
        """Test consonants set contains expected phonemes."""
        assert "b" in CONSONANTS
        assert "d" in CONSONANTS
        assert "k" in CONSONANTS
        assert "ʃ" in CONSONANTS
        assert "ʧ" in CONSONANTS

    def test_stress_marks_set(self):
        """Test stress marks set."""
        assert "ˈ" in STRESS_MARKS  # Primary stress
        assert "ˌ" in STRESS_MARKS  # Secondary stress
        assert len(STRESS_MARKS) == 2

    def test_no_overlap_vowels_consonants(self):
        """Test vowels and consonants don't overlap."""
        overlap = VOWELS & CONSONANTS
        assert len(overlap) == 0


class TestDiphthongAffricateMappings:
    """Tests for diphthong and affricate mappings."""

    def test_diphthong_expansions(self):
        """Test diphthong expansion mapping."""
        assert DIPHTHONG_EXPANSIONS["A"] == "eɪ"
        assert DIPHTHONG_EXPANSIONS["I"] == "aɪ"
        assert DIPHTHONG_EXPANSIONS["O"] == "oʊ"
        assert DIPHTHONG_EXPANSIONS["Q"] == "əʊ"
        assert DIPHTHONG_EXPANSIONS["W"] == "aʊ"
        assert DIPHTHONG_EXPANSIONS["Y"] == "ɔɪ"

    def test_affricate_expansions(self):
        """Test affricate expansion mapping."""
        assert AFFRICATE_EXPANSIONS["ʤ"] == "dʒ"
        assert AFFRICATE_EXPANSIONS["ʧ"] == "tʃ"
