"""Unit tests for the English number-to-words converter.

Tests the NumberConverter routing/format handling:
- cardinals, ordinals, years
- decimals (including leading ".5")
- currency amounts
- grouped thousands regression ("30,000" mid-sentence)
- phone/version/IP-like sequences
- number flags (&, n, a)
- suffix phoneme helpers (-s, -ed, -ing)
"""

import pytest

from kokorog2p.en.numbers import NumberConverter, is_currency_amount, is_digit

# ---------------------------------------------------------------------------
# Stubs: keep tests deterministic and independent of the real lexicon/num2words
# ---------------------------------------------------------------------------

_DIGIT_WORDS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
}


def _fake_num2words(n, to="cardinal", **_kwargs):
    """Deterministic num2words stub for unit tests."""
    # floats used by tests
    if isinstance(n, float):
        if n == 3.14:
            return "three point one four"
        raise ValueError(n)

    # allow strings like "05" if they slip through
    if isinstance(n, str):
        if n.isdigit():
            n = int(n)
        else:
            raise ValueError(n)

    if to == "cardinal":
        if n in _DIGIT_WORDS:
            return _DIGIT_WORDS[n]
        mapping = {
            12: "twelve",
            50: "fifty",
            101: "one hundred and one",
            100: "one hundred",
            1984: "one thousand nine hundred and eighty four",  # not used for year-path
            30000: "thirty thousand",
        }
        if n in mapping:
            return mapping[n]
        raise ValueError(n)

    if to == "ordinal":
        mapping = {1: "first", 2: "second", 3: "third"}
        if n in mapping:
            return mapping[n]
        raise ValueError(n)

    if to == "year":
        mapping = {1984: "nineteen eighty-four"}
        if n in mapping:
            return mapping[n]
        raise ValueError(n)

    raise ValueError(to)


def _lookup(word: str, *_args):
    """Lexicon lookup stub: return the word lowercased as 'phonemes'."""
    return (word.lower(), 4)


def _stem_s(word: str, *_args):
    """Pluralization stub: return the word lowercased as 'phonemes'."""
    return (word.lower(), 4)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def converter():
    """Create a NumberConverter with deterministic stubs."""
    conv = NumberConverter(_lookup, _stem_s)
    conv._num2words = _fake_num2words  # type: ignore[attr-defined]
    return conv


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestEnglishNumberHelpers:
    """Test suite for number helper functions."""

    def test_is_digit(self):
        assert is_digit("0")
        assert is_digit("123")
        assert not is_digit("")
        assert not is_digit("12a")
        assert not is_digit("12.3")
        assert not is_digit("1,000")

    def test_is_currency_amount(self):
        assert is_currency_amount("12")
        assert is_currency_amount("12.50")
        assert is_currency_amount(".50")
        assert is_currency_amount("30,000")
        assert is_currency_amount("30,000.10")
        assert not is_currency_amount("12.3.4")
        assert not is_currency_amount("abc")
        assert not is_currency_amount("12.")
        assert not is_currency_amount(
            "12,34"
        )  # invalid grouping but still split -> not digits


# ---------------------------------------------------------------------------
# Converter tests
# ---------------------------------------------------------------------------


class TestEnglishNumberConverter:
    """Test suite for NumberConverter.convert()."""

    def test_cardinal_basic(self, converter):
        spoken, rating = converter.convert("12")
        assert spoken == "twelve"
        assert rating == 4

    def test_ordinal_suffix(self, converter):
        spoken, rating = converter.convert("1st")
        assert spoken == "first"
        assert rating == 4

    def test_year_conversion_4_digits(self, converter):
        spoken, rating = converter.convert("1984")
        assert spoken == "nineteen eighty four"
        assert rating == 4

    def test_negative_number(self, converter):
        spoken, rating = converter.convert("-5")
        assert spoken == "minus five"
        assert rating == 4

    def test_decimal_leading_point(self, converter):
        spoken, rating = converter.convert(".5")
        assert spoken == "point five"
        assert rating == 4

    def test_decimal_regular(self, converter):
        spoken, rating = converter.convert("3.14")
        assert spoken == "three point one four"
        assert rating == 4

    def test_currency_amount_dollars_cents(self, converter):
        spoken, rating = converter.convert("12.50", currency="$")
        assert spoken == "twelve dollars and fifty cents"
        assert rating == 4

    def test_append_currency_helper(self, converter):
        out = converter.append_currency("twelve", "$")
        assert out == "twelve dollars"

    # -----------------------------------------------------------------------
    # Regression: grouped thousands should NOT be read digit-by-digit mid-sentence
    # -----------------------------------------------------------------------
    def test_grouped_thousands_not_head_reads_as_cardinal(self, converter):
        # Regression for: "30,000" mid-sentence being read as "three zero zero..."
        spoken, rating = converter.convert("30,000", is_head=False)
        assert spoken == "thirty thousand"
        assert rating == 4

    # -----------------------------------------------------------------------
    # Sequence / phone / dotted logic
    # -----------------------------------------------------------------------
    def test_phone_sequence_digit_by_digit_when_not_head(self, converter):
        spoken, _ = converter.convert("12345", is_head=False)
        assert spoken == "one two three four five"

    def test_three_digit_305_becomes_three_o_five(self, converter):
        spoken, _ = converter.convert("305", is_head=False)
        assert spoken == "three o five"

    def test_dotted_sequence_version_style(self, converter):
        spoken, _ = converter.convert("1.02.3", is_head=True)
        # dotted sequence doesn't insert "dot" here; it just emits the parts
        assert spoken == "one zero two three"

    # -----------------------------------------------------------------------
    # num_flags behavior
    # -----------------------------------------------------------------------
    def test_flag_n_contracts_and(self, converter):
        spoken, _ = converter.convert("101", num_flags={"n"})
        # "and" is contracted onto the previous token as "ən"
        assert spoken == "one hundredən one"

    def test_flag_ampersand_keeps_and(self, converter):
        spoken, _ = converter.convert("101", num_flags={"&"})
        assert spoken == "one hundred and one"

    def test_flag_a_turns_leading_one_into_schwa(self, converter):
        spoken, _ = converter.convert("100", num_flags={"a"})
        assert spoken == "ə hundred"

    # -----------------------------------------------------------------------
    # Suffix phoneme helpers
    # -----------------------------------------------------------------------
    def test_add_s_rules(self, converter):
        assert converter._add_s("p") == "ps"  # voiceless stop -> s
        assert converter._add_s("s") == "sᵻz"  # sibilant -> ᵻz
        assert converter._add_s("b") == "bz"  # default -> z

    def test_add_ed_rules(self, converter):
        assert converter._add_ed("p") == "pt"  # voiceless -> t
        assert converter._add_ed("d") == "dᵻd"  # d -> ᵻd
        assert converter._add_ed("t") == "tᵻd"  # t -> ᵻd
        assert converter._add_ed("b") == "bd"  # default -> d

    def test_add_ing_rules(self, converter):
        assert converter._add_ing("tɛst") == "tɛstɪŋ"

    # -----------------------------------------------------------------------
    # Failure cases
    # -----------------------------------------------------------------------
    def test_unparseable_number_returns_none(self, converter):
        spoken, rating = converter.convert("not_a_number")
        assert spoken is None
        assert rating is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
