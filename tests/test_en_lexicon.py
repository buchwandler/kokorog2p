"""Tests for the English lexicon."""

from kokorog2p.en.lexicon import (
    CONSONANTS,
    DIPHTHONGS,
    PRIMARY_STRESS,
    SECONDARY_STRESS,
    VOWELS,
    Lexicon,
    TokenContext,
    apply_stress,
    is_digit,
    stress_weight,
)


class TestTokenContext:
    """Tests for TokenContext dataclass."""

    def test_default_values(self):
        """Test default context values."""
        ctx = TokenContext()
        assert ctx.future_vowel is None
        assert ctx.future_to is False

    def test_custom_values(self):
        """Test context with custom values."""
        ctx = TokenContext(future_vowel=True, future_to=True)
        assert ctx.future_vowel is True
        assert ctx.future_to is True


class TestApplyStress:
    """Tests for apply_stress function."""

    def test_none_input(self):
        """Test with None input."""
        assert apply_stress(None, 0) is None
        assert apply_stress("test", None) == "test"
        assert apply_stress(None, None) is None

    def test_remove_all_stress(self):
        """Test removing all stress markers."""
        result = apply_stress("hˈɛlˌO", -2)
        assert result is not None
        assert PRIMARY_STRESS not in result
        assert SECONDARY_STRESS not in result

    def test_demote_stress(self):
        """Test demoting primary to secondary stress."""
        result = apply_stress("hˈɛlO", -1)
        assert result is not None
        assert PRIMARY_STRESS not in result
        assert SECONDARY_STRESS in result

    def test_neutral_with_primary(self):
        """Test neutral stress with existing primary."""
        result = apply_stress("hˈɛlO", 0)
        assert result is not None
        # Should demote primary to secondary
        assert SECONDARY_STRESS in result

    def test_add_secondary_stress(self):
        """Test adding secondary stress to unstressed word."""
        result = apply_stress("hɛlO", 0.5)
        assert result is not None
        assert SECONDARY_STRESS in result


class TestStressWeight:
    """Tests for stress_weight function."""

    def test_empty_string(self):
        """Test empty string."""
        assert stress_weight("") == 0
        assert stress_weight(None) == 0

    def test_simple_word(self):
        """Test simple word weight."""
        # Single vowel
        weight = stress_weight("kæt")
        assert weight >= 1

    def test_diphthong_weight(self):
        """Test diphthong weighting."""
        # Diphthongs count as 2
        diphthong_weight = stress_weight("A")  # eɪ sound
        monophthong_weight = stress_weight("æ")
        assert diphthong_weight > monophthong_weight


class TestIsDigit:
    """Tests for is_digit function."""

    def test_digits(self):
        """Test digit recognition."""
        assert is_digit("123") is True
        assert is_digit("0") is True
        assert is_digit("999") is True

    def test_non_digits(self):
        """Test non-digit strings."""
        assert is_digit("abc") is False
        assert is_digit("12a") is False
        assert is_digit("") is False


class TestLexicon:
    """Tests for the Lexicon class."""

    def test_creation_us(self, us_lexicon):
        """Test US lexicon creation."""
        assert us_lexicon.british is False

    def test_creation_gb(self, gb_lexicon):
        """Test GB lexicon creation."""
        assert gb_lexicon.british is True

    def test_lookup_common_word(self, us_lexicon):
        """Test looking up a common word."""
        ps, rating = us_lexicon.lookup("hello")
        assert ps is not None
        assert rating is not None
        assert isinstance(ps, str)
        assert len(ps) > 0

    def test_lookup_the_with_context(self, us_lexicon):
        """Test 'the' pronunciation depends on context."""
        # Before vowel: "ði"
        ctx_vowel = TokenContext(future_vowel=True)
        ps_vowel, _ = us_lexicon.get_special_case("the", "DT", None, ctx_vowel)
        assert ps_vowel == "ði"

        # Before consonant: "ðə"
        ctx_consonant = TokenContext(future_vowel=False)
        ps_consonant, _ = us_lexicon.get_special_case("the", "DT", None, ctx_consonant)
        assert ps_consonant == "ðə"

    def test_lookup_a_article(self, us_lexicon):
        """Test 'a' pronunciation."""
        ps, rating = us_lexicon.get_special_case("a", "DT", None, None)
        assert ps == "ɐ"

        ps, rating = us_lexicon.get_special_case("a", None, None, None)
        assert ps == "ˈA"

        ps2, rating2 = us_lexicon.get_special_case("A", None, None, None)
        assert ps2 == "ˈA"

    def test_suffix_s(self, us_lexicon):
        """Test -s suffix handling."""
        # cats -> cat + s
        ps, rating = us_lexicon.stem_s("cats", "NNS", None, None)
        assert ps is not None
        assert ps.endswith("s")

    def test_suffix_ed(self, us_lexicon):
        """Test -ed suffix handling."""
        # walked -> walk + ed
        ps, rating = us_lexicon.stem_ed("walked", "VBD", None, None)
        assert ps is not None
        # Should end with t (voiceless ending)
        assert "t" in ps[-3:]

    def test_suffix_ing(self, us_lexicon):
        """Test -ing suffix handling."""
        # walking -> walk + ing
        ps, rating = us_lexicon.stem_ing("walking", "VBG", None, None)
        assert ps is not None
        assert ps.endswith("ɪŋ")

    def test_is_known(self, us_lexicon):
        """Test is_known method."""
        assert us_lexicon.is_known("hello") is True
        assert us_lexicon.is_known("the") is True
        # Unknown gibberish
        assert us_lexicon.is_known("xyzqwerty") is False

    def test_get_parent_tag(self, us_lexicon):
        """Test POS tag parent mapping."""
        assert Lexicon.get_parent_tag("VB") == "VERB"
        assert Lexicon.get_parent_tag("VBD") == "VERB"
        assert Lexicon.get_parent_tag("VBZ") == "VERB"
        assert Lexicon.get_parent_tag("NN") == "NOUN"
        assert Lexicon.get_parent_tag("NNS") == "NOUN"
        assert Lexicon.get_parent_tag("JJ") == "ADJ"
        assert Lexicon.get_parent_tag("RB") == "ADV"
        assert Lexicon.get_parent_tag(None) is None

    def test_callable_interface(self, us_lexicon):
        """Test calling lexicon directly."""
        ps, rating = us_lexicon("hello")
        assert ps is not None
        assert rating is not None

    def test_unknown_word(self, us_lexicon):
        """Test unknown word returns None."""
        # Use a truly unknown word (gibberish)
        ps, rating = us_lexicon("xyzqwertyuiop")
        assert ps is None or rating is None

    def test_symbol_lookup(self, us_lexicon):
        """Test symbol lookup."""
        ps, rating = us_lexicon.get_special_case("%", None, None, None)
        # % should map to "percent"
        assert ps is not None

    def test_get_NNP(self, us_lexicon):
        """Test proper noun spelling pronunciation."""
        # NNP should spell out letters
        ps, rating = us_lexicon.get_NNP("ABC")
        assert ps is not None
        assert rating == 3

    def test_is_number(self, us_lexicon):
        """Test number detection."""
        assert Lexicon.is_number("123", True) is True
        assert Lexicon.is_number("12,345", True) is True
        assert Lexicon.is_number("-100", True) is True
        assert Lexicon.is_number("-100", False) is False  # minus only at head
        assert Lexicon.is_number("hello", True) is False
        assert Lexicon.is_number("1st", True) is True
        assert Lexicon.is_number("2nd", True) is True


class TestLexiconDifferences:
    """Tests for US vs GB lexicon differences."""

    def test_different_vocabularies(self, us_lexicon, gb_lexicon):
        """Test that US and GB use different phoneme sets."""
        # The word "cat" has different vowels in US vs GB
        us_ps, _ = us_lexicon("cat")
        gb_ps, _ = gb_lexicon("cat")

        if us_ps and gb_ps:
            # US uses æ, GB uses a
            # At least one should have the dialect-specific vowel
            assert "æ" in us_ps or "a" in gb_ps


class TestConstants:
    """Tests for lexicon constants."""

    def test_consonants(self):
        """Test consonants set."""
        assert "b" in CONSONANTS
        assert "d" in CONSONANTS
        assert "ʃ" in CONSONANTS
        assert "a" not in CONSONANTS

    def test_vowels(self):
        """Test vowels set."""
        assert "a" in VOWELS
        assert "i" in VOWELS
        assert "A" in VOWELS  # diphthong
        assert "b" not in VOWELS

    def test_diphthongs(self):
        """Test diphthongs set."""
        assert "A" in DIPHTHONGS
        assert "I" in DIPHTHONGS
        assert "O" in DIPHTHONGS
        assert "a" not in DIPHTHONGS

    def test_stress_markers(self):
        """Test stress marker constants."""
        assert PRIMARY_STRESS == "ˈ"
        assert SECONDARY_STRESS == "ˌ"
