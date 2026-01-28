"""Tests for punctuation handling module.

Tests cover:
1. Unicode normalization
2. Punctuation removal
3. Preserve/restore round-trips
4. Edge cases (multiple punctuation, quotes, ellipses)
5. Kokoro vocabulary compliance
6. Robust whitespace handling for multi-char sequences
"""

import re

import pytest

from kokorog2p.punctuation import (
    KOKORO_PUNCTUATION,
    MarkIndex,
    Position,
    Punctuation,
    filter_punctuation,
    is_kokoro_punctuation,
    normalize_punctuation,
)

# =============================================================================
# Test Kokoro punctuation constants
# =============================================================================


class TestKokoroPunctuation:
    """Test Kokoro punctuation constants."""

    def test_kokoro_punctuation_contains_expected(self):
        """Kokoro vocab should contain standard punctuation."""
        # List each punctuation mark explicitly to avoid string parsing issues
        expected = {
            ";",
            ":",
            ",",
            ".",
            "!",
            "?",
            "\u2014",  # — em-dash
            "\u2026",  # … ellipsis
            '"',
            "(",
            ")",
            "\u201c",  # " left curly quote
            "\u201d",  # " right curly quote
        }
        assert expected == KOKORO_PUNCTUATION

    def test_kokoro_punctuation_size(self):
        """Should have exactly 13 punctuation marks."""
        assert len(KOKORO_PUNCTUATION) == 13  # ;:,.!?—…"()""

    def test_is_kokoro_punctuation(self):
        """Test is_kokoro_punctuation function."""
        # In vocab
        assert is_kokoro_punctuation(".")
        assert is_kokoro_punctuation("!")
        assert is_kokoro_punctuation("?")
        assert is_kokoro_punctuation(",")
        assert is_kokoro_punctuation(";")
        assert is_kokoro_punctuation(":")
        assert is_kokoro_punctuation("—")
        assert is_kokoro_punctuation("…")
        assert is_kokoro_punctuation('"')
        assert is_kokoro_punctuation("(")
        assert is_kokoro_punctuation(")")
        assert is_kokoro_punctuation("\u201c")  # " left curly quote
        assert is_kokoro_punctuation("\u201d")  # " right curly quote
        assert not is_kokoro_punctuation(" ")

        # Not in vocab
        assert not is_kokoro_punctuation("-")
        assert not is_kokoro_punctuation("'")
        assert not is_kokoro_punctuation("~")
        assert not is_kokoro_punctuation("@")
        assert not is_kokoro_punctuation("#")


# =============================================================================
# Test Unicode normalization
# =============================================================================


class TestPunctuationNormalization:
    """Test Unicode punctuation normalization."""

    @pytest.fixture
    def punct(self):
        return Punctuation()

    # Dashes
    def test_normalize_en_dash(self, punct):
        """En-dash should become em-dash."""
        assert punct.normalize("Hello–world") == "Hello—world"

    def test_normalize_minus_sign(self, punct):
        """Minus sign should become em-dash."""
        assert punct.normalize("Hello−world") == "Hello—world"

    def test_normalize_horizontal_bar(self, punct):
        """Horizontal bar should become em-dash."""
        assert punct.normalize("Hello―world") == "Hello—world"

    # Ellipsis
    def test_normalize_triple_dots(self, punct):
        """Three dots should become ellipsis."""
        assert punct.normalize("Hello...world") == "Hello…world"
        assert punct.normalize("Hello . . .world") == "Hello…world"
        assert punct.normalize("Hello. . . world") == "Hello…world"

    def test_normalize_spaced_ellipsis_var_whitespace(self, punct):
        """Spaced ellipsis should tolerate tabs/newlines and multiple spaces."""
        assert punct.normalize("Hello .  .\t.  world") == "Hello…world"
        assert punct.normalize("Hello\t.\n.\t.\nworld") == "Hello…world"

    def test_normalize_double_dots(self, punct):
        """Two dots should become ellipsis."""
        assert punct.normalize("Hello..world") == "Hello…world"

    def test_normalize_fullwidth_ellipsis(self, punct):
        """Fullwidth dots should become ellipsis."""
        assert punct.normalize("Hello．．．world") == "Hello…world"

    def test_normalize_japanese_ellipsis(self, punct):
        """Japanese middle dots should become ellipsis."""
        assert punct.normalize("Hello・・・world") == "Hello…world"

    # Hyphens/dashes with variable whitespace
    def test_normalize_spaced_hyphen_var_whitespace(self, punct):
        """Hyphen-as-dash should tolerate tabs/newlines and multiple spaces."""
        assert punct.normalize("Wait   -   now") == "Wait — now"
        assert punct.normalize("Wait\t-\nnow") == "Wait — now"
        assert punct.normalize("Wait \t-- \nnow") == "Wait — now"

    def test_normalize_inword_hyphen_is_preserved(self, punct):
        """In-word hyphens should remain (dictionary entries may contain '-')."""
        assert punct.normalize("mother-in-law") == "mother-in-law"

    # Quotes
    def test_normalize_single_quotes_to_double(self, punct):
        """Single quotes remain as apostrophes (for contractions)."""
        assert punct.normalize("'Hello'") == "'Hello'"

    def test_normalize_curly_single_quotes(self, punct):
        """Curly single quotes normalize to straight apostrophe."""
        assert punct.normalize("'Hello'") == "'Hello'"
        assert punct.normalize("‘Hello’") == "'Hello'"

    def test_normalize_curly_apostrophe_in_word(self, punct):
        assert punct.normalize("don’t") == "don't"

    def test_normalize_guillemets(self, punct):
        """Guillemets should become double quotes."""
        assert punct.normalize("«Hello»") == '"Hello"'

    def test_normalize_japanese_brackets(self, punct):
        """Japanese brackets should become double quotes."""
        assert punct.normalize("「Hello」") == '"Hello"'

    # Fullwidth punctuation
    def test_normalize_fullwidth_semicolon(self, punct):
        """Fullwidth semicolon should become ASCII."""
        assert punct.normalize("Hello；world") == "Hello;world"

    def test_normalize_fullwidth_colon(self, punct):
        """Fullwidth colon should become ASCII."""
        assert punct.normalize("Hello：world") == "Hello:world"

    def test_normalize_fullwidth_comma(self, punct):
        """Fullwidth comma should become ASCII."""
        assert punct.normalize("Hello，world") == "Hello,world"

    def test_normalize_ideographic_comma(self, punct):
        """Ideographic comma should become ASCII."""
        assert punct.normalize("Hello、world") == "Hello,world"

    def test_normalize_fullwidth_period(self, punct):
        """Fullwidth period should become ASCII."""
        assert punct.normalize("Hello．") == "Hello."

    def test_normalize_ideographic_period(self, punct):
        """Ideographic period should become ASCII."""
        assert punct.normalize("Hello。") == "Hello."

    def test_normalize_fullwidth_exclamation(self, punct):
        """Fullwidth exclamation should become ASCII."""
        assert punct.normalize("Hello！") == "Hello!"

    def test_normalize_fullwidth_question(self, punct):
        """Fullwidth question should become ASCII."""
        assert punct.normalize("Hello？") == "Hello?"

    # Spanish punctuation
    def test_normalize_inverted_exclamation(self, punct):
        """Inverted exclamation should become exclamation."""
        assert punct.normalize("¡Hola!") == "!Hola!"

    def test_normalize_inverted_question(self, punct):
        """Inverted question should become question."""
        assert punct.normalize("¿Cómo?") == "?Cómo?"

    # Brackets
    def test_normalize_square_brackets(self, punct):
        """Square brackets should become parentheses."""
        assert punct.normalize("[Hello]") == "(Hello)"

    def test_normalize_curly_brackets(self, punct):
        """Curly brackets should become parentheses."""
        assert punct.normalize("{Hello}") == "(Hello)"

    def test_normalize_fullwidth_parentheses(self, punct):
        """Fullwidth parentheses should become ASCII."""
        assert punct.normalize("（Hello）") == "(Hello)"

    # Combined normalizations
    def test_normalize_complex_text(self, punct):
        """Complex text with multiple normalizations."""
        text = "«Hello»... ¿Cómo estás？ Bien、gracias！"
        expected = '"Hello"… ?Cómo estás? Bien,gracias!'
        assert punct.normalize(text) == expected

    # Removed characters
    def test_normalize_removes_tilde(self, punct):
        """Unsupported separators should not merge words (prefer spacing)."""
        assert punct.normalize("Hello~world") == "Hello world"

    def test_normalize_removes_at_sign(self, punct):
        """Unsupported separators should not merge words (prefer spacing)."""
        assert punct.normalize("Hello@world") == "Hello world"

    def test_normalize_removes_hash(self, punct):
        """Unsupported separators should not merge words (prefer spacing)."""
        assert punct.normalize("Hello#world") == "Hello world"

    def test_normalize_removes_symbols(self, punct):
        """Various symbols should be removed/replaced safely (no word merging)."""
        text = "Hello†‡§¶world"
        result = punct.normalize(text)
        # Ensure symbols are gone and words aren't merged
        assert (
            "†" not in result
            and "‡" not in result
            and "§" not in result
            and "¶" not in result
        )
        assert re.search(r"Hello\s+world", result)


class TestNormalizePunctuationFunction:
    """Test the convenience function."""

    def test_normalize_punctuation_function(self):
        """Convenience function should work."""
        assert normalize_punctuation("Hello...world！") == "Hello…world!"


# =============================================================================
# Test punctuation removal
# =============================================================================


class TestPunctuationRemoval:
    """Test punctuation removal."""

    @pytest.fixture
    def punct(self):
        return Punctuation()

    def test_remove_simple(self, punct):
        """Remove simple punctuation."""
        assert punct.remove("Hello, world!") == "Hello world"

    def test_remove_multiple(self, punct):
        """Remove multiple punctuation marks."""
        assert punct.remove("Hello... world?!") == "Hello world"

    def test_remove_leading(self, punct):
        """Remove leading punctuation."""
        assert punct.remove("...Hello world") == "Hello world"

    def test_remove_trailing(self, punct):
        """Remove trailing punctuation."""
        assert punct.remove("Hello world...") == "Hello world"

    def test_remove_list_input(self, punct):
        """Remove from list of texts."""
        texts = ["Hello!", "World?"]
        assert punct.remove(texts) == ["Hello", "World"]

    def test_remove_empty_string(self, punct):
        """Handle empty string."""
        assert punct.remove("") == ""

    def test_remove_only_punctuation(self, punct):
        """Handle string with only punctuation."""
        assert punct.remove("...") == ""

    def test_remove_preserves_internal_spaces(self, punct):
        """Internal spaces should be preserved."""
        assert punct.remove("Hello,  world") == "Hello world"


# =============================================================================
# Test preserve/restore
# =============================================================================


class TestPunctuationPreserve:
    """Test punctuation preservation."""

    @pytest.fixture
    def punct(self):
        return Punctuation()

    def test_preserve_simple(self, punct):
        """Preserve simple comma."""
        text, marks = punct.preserve("Hello, world")
        assert text == ["Hello", "world"]
        assert len(marks) == 1
        assert marks[0].mark == ", "
        assert marks[0].position == Position.MIDDLE

    def test_preserve_end(self, punct):
        """Preserve ending punctuation."""
        text, marks = punct.preserve("Hello world!")
        assert text == ["Hello world"]
        assert len(marks) == 1
        assert marks[0].mark == "!"
        assert marks[0].position == Position.END

    def test_preserve_begin(self, punct):
        """Preserve beginning punctuation."""
        text, marks = punct.preserve('"Hello world"')
        assert "Hello world" in text[0]
        assert any(m.position == Position.BEGIN for m in marks)

    def test_preserve_alone(self, punct):
        """Handle line that is only punctuation."""
        text, marks = punct.preserve("...")
        assert text == []
        assert len(marks) == 1
        assert marks[0].position == Position.ALONE

    def test_preserve_no_punctuation(self, punct):
        """Handle text without punctuation."""
        text, marks = punct.preserve("Hello world")
        assert text == ["Hello world"]
        assert marks == []

    def test_preserve_multiple(self, punct):
        """Preserve multiple punctuation marks."""
        text, marks = punct.preserve("Hello, world!")
        assert len(marks) == 2

    def test_preserve_list_input(self, punct):
        """Preserve from list of texts."""
        text, marks = punct.preserve(["Hello!", "World?"])
        assert "Hello" in text
        assert "World" in text


class TestPunctuationRestore:
    """Test punctuation restoration."""

    @pytest.fixture
    def punct(self):
        return Punctuation()

    def test_restore_simple_end(self, punct):
        """Restore ending punctuation."""
        text, marks = punct.preserve("Hello world!")
        restored = punct.restore(["həˈloʊ wˈɜːld"], marks)
        assert restored == ["həˈloʊ wˈɜːld!"]

    def test_restore_middle(self, punct):
        """Restore middle punctuation."""
        text, marks = punct.preserve("Hello, world")
        restored = punct.restore(["həˈloʊ", "wˈɜːld"], marks)
        assert "həˈloʊ, wˈɜːld" in " ".join(restored)

    def test_restore_multiple(self, punct):
        """Restore multiple punctuation marks."""
        text, marks = punct.preserve("Hello, world!")
        restored = punct.restore(["həˈloʊ", "wˈɜːld"], marks)
        result = "".join(restored)
        assert "," in result
        assert "!" in result

    def test_restore_alone(self, punct):
        """Restore punctuation-only line."""
        text, marks = punct.preserve("...")
        restored = punct.restore([], marks)
        assert "..." in "".join(restored)

    def test_restore_does_not_mutate_marks(self, punct):
        """restore() should not mutate the caller's marks list."""
        chunks, marks = punct.preserve("Hello, world!")
        marks_copy = list(marks)

        _ = punct.restore(["H", "W"], marks)

        assert marks == marks_copy


class TestPreserveRestoreRoundTrip:
    """Test full round-trip preserve/restore cycles."""

    @pytest.fixture
    def punct(self):
        return Punctuation()

    @pytest.mark.parametrize(
        "input_text",
        [
            "Hello, world!",
            '"Hello," she said.',
            "Wait... what?!",
            "One, two, three.",
            "(Hello)",
            "Hello—world",
            "Test…",
        ],
    )
    def test_roundtrip_preserves_punctuation(self, punct, input_text):
        """Round-trip should preserve all punctuation."""
        # Preserve
        chunks, marks = punct.preserve(input_text)

        # "Phonemize" (just uppercase for test)
        phonemized = [c.upper() for c in chunks]

        # Restore
        restored = punct.restore(phonemized, marks)
        result = "".join(restored)

        # Check all punctuation is present
        for char in input_text:
            if char in KOKORO_PUNCTUATION and char != " ":
                assert char in result, f"Missing '{char}' in '{result}'"


# =============================================================================
# Test edge cases
# =============================================================================


class TestPunctuationEdgeCases:
    """Test edge cases for punctuation handling."""

    @pytest.fixture
    def punct(self):
        return Punctuation()

    # Multiple consecutive punctuation
    def test_multiple_exclamation(self, punct):
        """Handle multiple exclamation marks."""
        result = punct.normalize("Hello!!!")
        assert result == "Hello!!!"

    def test_interrobang(self, punct):
        """Handle interrobang-style endings."""
        result = punct.normalize("What?!")
        assert result == "What?!"

    def test_ellipsis_with_more(self, punct):
        """Handle ellipsis followed by more dots."""
        result = punct.normalize("Wait....")
        assert "…" in result

    # Quotes
    def test_nested_quotes(self, punct):
        """Handle nested quotes."""
        text = '"She said, "Hello""'
        result = punct.normalize(text)
        assert result.count('"') >= 2

    def test_unmatched_quotes(self, punct):
        """Handle unmatched quotes."""
        result = punct.normalize('"Hello')
        assert '"' in result

    def test_apostrophe_in_word(self, punct):
        """Apostrophe in contraction is normalized to straight apostrophe."""
        result = punct.normalize("don't")
        assert result == "don't"

    # Mixed scripts
    def test_mixed_cjk_punctuation(self, punct):
        """Handle mixed CJK and Western punctuation."""
        result = punct.normalize("Hello。World！")
        assert result == "Hello.World!"

    def test_chinese_punctuation_full(self, punct):
        """Handle full Chinese punctuation."""
        text = "你好，世界！"
        result = punct.normalize(text)
        assert "," in result
        assert "!" in result

    # Spacing issues
    def test_multiple_spaces_around_punctuation(self, punct):
        """Handle multiple spaces around punctuation."""
        text, marks = punct.preserve("Hello  ,  world")
        assert len(marks) >= 1

    def test_no_space_after_punctuation(self, punct):
        """Handle no space after punctuation."""
        text, marks = punct.preserve("Hello,world")
        assert "Hello" in text or "Hello" in text[0]

    # Empty and whitespace
    def test_empty_string(self, punct):
        """Handle empty string."""
        assert punct.normalize("") == ""
        assert punct.remove("") == ""
        text, marks = punct.preserve("")
        assert text == []
        assert marks == []

    def test_whitespace_only(self, punct):
        """Handle whitespace-only string."""
        assert punct.normalize("   ") == "   "
        assert punct.remove("   ") == ""

    # Special Unicode
    def test_zero_width_characters(self, punct):
        """Handle zero-width characters."""
        text = "Hello\u200bworld"  # Zero-width space
        result = punct.normalize(text)
        assert "Hello" in result

    def test_combining_characters(self, punct):
        """Handle combining characters."""
        text = "café"  # e with combining acute
        result = punct.normalize(text)
        assert "caf" in result


# =============================================================================
# Test filter_punctuation function
# =============================================================================


class TestFilterPunctuation:
    """Test filter_punctuation function."""

    def test_filter_keeps_valid(self):
        """Should keep Kokoro-valid punctuation."""
        text = "Hello, world!"
        result = filter_punctuation(text)
        assert result == "Hello, world!"

    def test_filter_removes_invalid(self):
        """Should remove invalid punctuation."""
        text = "Hello~world!"
        result = filter_punctuation(text)
        # Unsupported punctuation should not merge words
        assert result == "Hello world!"

    def test_filter_normalizes_first(self):
        """Should normalize before filtering."""
        text = "Hello！"  # Fullwidth
        result = filter_punctuation(text)
        assert result == "Hello!"

    def test_filter_keeps_apostrophe(self):
        """Apostrophes should be preserved for contractions."""
        assert filter_punctuation("don't!") == "don't!"
        assert filter_punctuation("don’t!") == "don't!"

    def test_filter_keeps_inword_hyphen(self):
        """In-word hyphen should be preserved for lexicon lookups (mother-in-law)."""
        assert filter_punctuation("mother-in-law") == "mother-in-law"

    def test_filter_keeps_dash_as_em_dash_when_spaced(self):
        """A spaced hyphen is treated as a dash and normalized to em-dash."""
        # normalize(): " - " -> " — "
        assert filter_punctuation("wait - now") == "wait — now"

    def test_filter_complex(self):
        """Complex case with normalize and filter."""
        text = "Hello... @world！ [test]"
        result = filter_punctuation(text)
        assert "…" in result
        assert "@" not in result
        assert "!" in result


# =============================================================================
# Test custom marks
# =============================================================================


class TestCustomMarks:
    """Test custom punctuation mark configuration."""

    def test_custom_marks_string(self):
        """Custom marks as string."""
        punct = Punctuation(marks=".,")
        text, marks = punct.preserve("Hello, world!")
        # Only comma should be captured, not !
        comma_marks = [m for m in marks if "," in m.mark]
        assert len(comma_marks) == 1

    def test_custom_marks_regex(self):
        """Custom marks as regex."""
        pattern = re.compile(r"[.!?]+")
        punct = Punctuation(marks=pattern)
        text, marks = punct.preserve("Hello! World?")
        assert len(marks) >= 2

    def test_default_marks(self):
        """Default marks should match Kokoro vocab."""
        punct = Punctuation()
        default = punct.default_marks()
        for char in default:
            assert char in KOKORO_PUNCTUATION or char == "-"


# =============================================================================
# Test Position enum
# =============================================================================


class TestPositionEnum:
    """Test Position enum."""

    def test_position_values(self):
        """Position values should be single characters."""
        assert Position.BEGIN.value == "B"
        assert Position.END.value == "E"
        assert Position.MIDDLE.value == "I"
        assert Position.ALONE.value == "A"


# =============================================================================
# Test MarkIndex dataclass
# =============================================================================


class TestMarkIndex:
    """Test MarkIndex dataclass."""

    def test_markindex_creation(self):
        """MarkIndex should be creatable."""
        mark = MarkIndex(index=0, mark=",", position=Position.MIDDLE)
        assert mark.index == 0
        assert mark.mark == ","
        assert mark.position == Position.MIDDLE

    def test_markindex_frozen(self):
        """MarkIndex should be immutable."""
        from dataclasses import FrozenInstanceError

        mark = MarkIndex(index=0, mark=",", position=Position.MIDDLE)
        with pytest.raises(FrozenInstanceError):
            mark.index = 1  # type: ignore[misc]
