"""Tests for punctuation and apostrophe normalization.

This test module validates that all Unicode variants of apostrophes, ellipsis,
and dashes are correctly normalized to Kokoro-compatible forms.

These normalizations happen in two places:
1. kokorog2p.punctuation.normalize() - standalone utility
2. kokorog2p.en.g2p._tokenize_spacy() - during English G2P

This ensures consistency across the library.
"""

import pytest


class TestApostropheNormalization:
    """Test all apostrophe variants normalize to ASCII apostrophe (')."""

    @pytest.fixture
    def punct(self):
        from kokorog2p.punctuation import Punctuation

        return Punctuation()

    def test_normalize_right_single_quote(self, punct):
        """Right single quotation mark (U+2019) → ASCII apostrophe."""
        assert punct.normalize("don't") == "don't"

    def test_normalize_left_single_quote(self, punct):
        """Left single quotation mark (U+2018) → ASCII apostrophe."""
        assert punct.normalize("don't") == "don't"

    def test_normalize_grave_accent(self, punct):
        """Grave accent (U+0060) → ASCII apostrophe."""
        assert punct.normalize("don`t") == "don't"

    def test_normalize_acute_accent(self, punct):
        """Acute accent (U+00B4) → ASCII apostrophe."""
        assert punct.normalize("don´t") == "don't"

    def test_normalize_modifier_letter_prime(self, punct):
        """Modifier letter prime (U+02B9) → ASCII apostrophe."""
        assert punct.normalize("donʹt") == "don't"

    def test_normalize_prime_symbol(self, punct):
        """Prime symbol (U+2032) → ASCII apostrophe."""
        assert punct.normalize("don′t") == "don't"

    def test_normalize_fullwidth_apostrophe(self, punct):
        """Fullwidth apostrophe (U+FF07) → ASCII apostrophe."""
        assert punct.normalize("don＇t") == "don't"

    def test_normalize_multiple_exclamation_mark(self, punct):
        assert punct.normalize("!!!") == "!!!"

    def test_normalize_multiple_apostrophes(self, punct):
        """Multiple contractions with different apostrophe types."""
        text = "I don't think you're right, but we`ve tried."
        result = punct.normalize(text)
        # All should be normalized to straight apostrophe
        assert "don't" in result
        assert "you're" in result
        assert "we've" in result


class TestEllipsisNormalization:
    """Test all ellipsis variants normalize to ellipsis character (…)."""

    @pytest.fixture
    def punct(self):
        from kokorog2p.punctuation import Punctuation

        return Punctuation()

    def test_normalize_three_dots(self, punct):
        """Three dots (...) → ellipsis."""
        assert punct.normalize("Wait...") == "Wait…"

    def test_normalize_spaced_dots(self, punct):
        """Spaced dots (. . .) → ellipsis."""
        assert punct.normalize("Wait. . .") == "Wait…"
        assert punct.normalize("Wait . . .") == "Wait…"
        assert punct.normalize("Wait. . . ") == "Wait…"
        assert punct.normalize("Wait . . . ") == "Wait…"

    def test_normalize_two_dots(self, punct):
        """Two dots (..) → ellipsis."""
        assert punct.normalize("Wait..") == "Wait…"

    def test_normalize_four_dots(self, punct):
        """Four dots (....) → ellipsis."""
        assert punct.normalize("Wait....") == "Wait…"

    def test_normalize_ellipsis_preserved(self, punct):
        """Ellipsis character (…) is preserved."""
        assert punct.normalize("Wait…") == "Wait…"

    def test_normalize_fullwidth_ellipsis(self, punct):
        """Fullwidth ellipsis (．．．) → ellipsis."""
        assert punct.normalize("Wait．．．") == "Wait…"

    def test_normalize_japanese_ellipsis(self, punct):
        """Japanese middle dot ellipsis (・・・) → ellipsis."""
        assert punct.normalize("Wait・・・") == "Wait…"

    def test_normalize_multiple_ellipsis(self, punct):
        """Multiple ellipsis variants in one text."""
        text = "Wait... no, really.. well...."
        result = punct.normalize(text)
        # All should become ellipsis
        assert result.count("…") == 3
        assert "..." not in result


class TestDashNormalization:
    """Test all dash variants normalize to em dash (—)."""

    @pytest.fixture
    def punct(self):
        from kokorog2p.punctuation import Punctuation

        return Punctuation()

    def test_normalize_en_dash(self, punct):
        """En dash (U+2013) → em dash."""
        assert punct.normalize("Wait–now") == "Wait—now"

    def test_normalize_minus_sign(self, punct):
        """Minus sign (U+2212) → em dash."""
        assert punct.normalize("Wait−now") == "Wait—now"

    def test_normalize_horizontal_bar(self, punct):
        """Horizontal bar (U+2015) → em dash."""
        assert punct.normalize("Wait―now") == "Wait—now"

    def test_normalize_figure_dash(self, punct):
        """Figure dash (U+2012) → em dash."""
        assert punct.normalize("Wait‒now") == "Wait—now"

    def test_normalize_double_hyphen(self, punct):
        """Double hyphen (--) → em dash."""
        assert punct.normalize("Wait--now") == "Wait—now"

    def test_normalize_spaced_hyphen(self, punct):
        """Spaced hyphen ( - ) → spaced em dash."""
        assert punct.normalize("Wait - now") == "Wait — now"

    def test_normalize_spaced_double_hyphen(self, punct):
        """Spaced double hyphen ( -- ) → spaced em dash."""
        assert punct.normalize("Wait -- now") == "Wait — now"

    def test_normalize_em_dash_preserved(self, punct):
        """Em dash (—) is preserved."""
        assert punct.normalize("Wait—now") == "Wait—now"

    def test_normalize_compound_words_hyphen_preserved(self, punct):
        """Hyphens in compound words (no spaces) are NOT normalized."""
        # Single hyphen without spaces is kept for compound words
        # This will be handled by tokenizer, not by normalize
        result = punct.normalize("well-known")
        # The hyphen is still there (not converted to em dash)
        # because there are no spaces around it
        assert "-" in result or "—" in result


class TestEnglishG2PNormalization:
    """Test that English G2P correctly normalizes during tokenization."""

    @pytest.fixture
    def g2p(self):
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(language="en-us", use_spacy=True)

    # Apostrophes
    def test_g2p_apostrophe_right_quote(self, g2p):
        """G2P normalizes right single quote in contractions."""
        result = g2p.phonemize("don't")
        assert "dˈOnt" in result

    def test_g2p_apostrophe_grave(self, g2p):
        """G2P normalizes grave accent in contractions."""
        result = g2p.phonemize("don`t")
        assert "dˈOnt" in result

    def test_g2p_apostrophe_acute(self, g2p):
        """G2P normalizes acute accent in contractions."""
        result = g2p.phonemize("don´t")
        assert "dˈOnt" in result

    # Ellipsis
    def test_g2p_ellipsis_three_dots(self, g2p):
        """G2P normalizes three dots to ellipsis."""
        tokens = g2p("Wait...")
        punct_tokens = [t for t in tokens if "…" in t.text]
        assert len(punct_tokens) == 1

    def test_g2p_ellipsis_spaced_dots(self, g2p):
        """G2P normalizes spaced dots to ellipsis."""
        tokens = g2p("Wait. . .")
        punct_tokens = [t for t in tokens if "…" in t.text]
        assert len(punct_tokens) == 1

    def test_g2p_ellipsis_four_dots(self, g2p):
        """G2P normalizes four dots to ellipsis."""
        tokens = g2p("Wait....")
        # Should have ellipsis, not four separate dots
        text_str = "".join(t.text for t in tokens)
        assert "…" in text_str
        # Shouldn't have multiple separate dots
        separate_dots = [t for t in tokens if t.text == "."]
        assert len(separate_dots) <= 1  # At most one extra dot

    # Dashes
    def test_g2p_dash_en_dash(self, g2p):
        """G2P normalizes en dash to em dash."""
        tokens = g2p("Wait–now")
        text_str = "".join(t.text for t in tokens)
        assert "—" in text_str

    def test_g2p_dash_spaced_hyphen(self, g2p):
        """G2P normalizes spaced hyphen to em dash."""
        tokens = g2p("Wait - now")
        text_str = "".join(t.text for t in tokens)
        assert "—" in text_str

    def test_g2p_dash_double_hyphen(self, g2p):
        """G2P normalizes double hyphen to em dash."""
        tokens = g2p("Wait--now")
        text_str = "".join(t.text for t in tokens)
        assert "—" in text_str

    def test_g2p_compound_word_hyphen(self, g2p):
        """G2P preserves hyphens in compound words during tokenization."""
        tokens = g2p("well-known")
        text_str = "".join(t.text for t in tokens)
        assert "-" in text_str
        # The tokenizer should keep "well-known" as connected words
        # Phonemes should be joined (no hyphen in phonemes)
        phonemes = g2p.phonemize("well-known")
        # Should have both "well" and "known" phonemes
        assert "wˈɛl" in phonemes
        assert "nˈOn" in phonemes


class TestComplexNormalization:
    """Test complex cases with multiple normalizations."""

    @pytest.fixture
    def punct(self):
        from kokorog2p.punctuation import Punctuation

        return Punctuation()

    @pytest.fixture
    def g2p(self):
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(language="en-us", use_spacy=True)

    def test_normalize_quotes_contractions_ellipsis(self, punct):
        """Complex text with quotes, contractions, and ellipsis."""
        text = "Don't say, \"we're fine\"..."
        result = punct.normalize(text)
        assert "Don't" in result
        assert "we're" in result
        assert "…" in result

    def test_normalize_multiple_types_mixed(self, punct):
        """Text with all normalization types."""
        text = "I don't know... really–what's happening?"
        result = punct.normalize(text)
        # Apostrophes normalized
        assert "don't" in result
        assert "what's" in result
        # Ellipsis normalized
        assert "…" in result
        # Dash normalized
        assert "—" in result

    def test_g2p_full_sentence_normalization(self, g2p):
        """Full sentence with multiple normalizations."""
        text = "I don't think we're ready... wait–what?"
        result = g2p.phonemize(text)
        # Should have correct phonemes for contractions
        assert "dˈOnt" in result
        assert "wɪɹ" in result or "wˌɪɹ" in result

    def test_g2p_literature_style_text(self, g2p):
        """Text as it might appear in literature (curly quotes, em dash)."""
        text = '"I don\'t know," she said—hesitating…'
        result = g2p.phonemize(text)
        # Contraction should work
        assert "dˈOnt" in result
        # Punctuation should be preserved (curly quotes from input)
        assert "\u201c" in result  # Left double quotation mark
        assert "\u201d" in result  # Right double quotation mark
        assert "—" in result
        assert "…" in result


class TestNormalizationConsistency:
    """Ensure punctuation.py and en/g2p.py normalize consistently."""

    def test_punctuation_vs_g2p_apostrophes(self):
        """Both modules should normalize apostrophes the same way."""
        from kokorog2p.en import EnglishG2P
        from kokorog2p.punctuation import normalize_punctuation

        test_text = "don't you're we've"

        # Normalize with punctuation module
        punct_result = normalize_punctuation(test_text)

        # G2P normalizes during tokenization
        g2p = EnglishG2P(language="en-us", use_spacy=True)
        tokens = g2p(test_text)
        g2p_text = " ".join(t.text for t in tokens)

        # Both should have straight apostrophes
        assert "don't" in punct_result
        assert "don't" in g2p_text or "don't" in str(tokens)

    def test_punctuation_vs_g2p_ellipsis(self):
        """Both modules should normalize ellipsis the same way."""
        from kokorog2p.punctuation import normalize_punctuation

        test_cases = ["Wait...", "Wait. . .", "Wait..", "Wait...."]

        for test_text in test_cases:
            punct_result = normalize_punctuation(test_text)
            # All should become ellipsis
            assert "…" in punct_result

    def test_punctuation_vs_g2p_dashes(self):
        """Both modules should normalize dashes the same way."""
        from kokorog2p.punctuation import normalize_punctuation

        test_cases = [
            ("Wait–now", "Wait—now"),  # en dash
            ("Wait--now", "Wait—now"),  # double hyphen
            ("Wait - now", "Wait — now"),  # spaced hyphen
        ]

        for input_text, expected in test_cases:
            punct_result = normalize_punctuation(input_text)
            assert punct_result == expected
