"""Regression tests for context-guarded abbreviation handling."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

import pytest

from kokorog2p.abbreviation_utils import (
    get_abbreviation_entries,
    merge_abbreviation_tokens,
)
from kokorog2p.en.abbreviations import (
    EnglishAbbreviationExpander,
    get_expander,
    reset_expander,
)
from kokorog2p.pipeline.abbreviations import (
    AbbreviationEntry,
    abbreviation_guards_match,
)
from kokorog2p.pipeline.models import ProcessingToken
from kokorog2p.pipeline.tokenizer import RegexTokenizer
from kokorog2p.tokenization import tokenize_with_offsets

FOLLOWED_BY_NUMBER = ("no.", "vol.", "pg.", "pp.", "ch.", "fig.")
PRECEDED_BY_NUMBER_DOTTED = (
    "in.",
    "ft.",
    "yd.",
    "mi.",
    "oz.",
    "lb.",
    "lbs.",
    "gal.",
    "qt.",
    "pt.",
    "tsp.",
    "tbsp.",
    "hr.",
    "hrs.",
    "sec.",
)
PRECEDED_BY_NUMBER_PLAIN = ("mm", "cm", "km", "mg", "kg")
PRECEDED_BY_NUMBER = PRECEDED_BY_NUMBER_DOTTED + PRECEDED_BY_NUMBER_PLAIN
ALL_GUARDED = FOLLOWED_BY_NUMBER + PRECEDED_BY_NUMBER


@pytest.fixture(autouse=True)
def _reset_shared_expander() -> Iterator[None]:
    """Prevent singleton abbreviation state from leaking between tests."""
    reset_expander()
    yield
    reset_expander()


def _regex_tokens(text: str) -> list:
    return RegexTokenizer(lang="en-us").tokenize(text)


def _offset_tokens(text: str) -> list:
    return tokenize_with_offsets(text, lang="en-us")


TOKENIZERS: tuple[tuple[str, Callable[[str], list]], ...] = (
    ("regex", _regex_tokens),
    ("offset", _offset_tokens),
)


class TestGuardInventory:
    """The tokenizer inventory must retain guarded definitions."""

    def test_all_guarded_entries_are_known_and_expected(self):
        expander = EnglishAbbreviationExpander()
        guarded = {
            entry.abbreviation
            for entry in expander.entries.values()
            if entry.only_if_preceded_by or entry.only_if_followed_by
        }

        assert guarded == set(ALL_GUARDED)

    def test_public_inventory_does_not_drop_guarded_entries(self):
        expander = EnglishAbbreviationExpander()
        public_entries = set(get_abbreviation_entries("en-us"))
        complete_entries = {
            (entry.abbreviation, entry.case_sensitive)
            for entry in expander.entries.values()
        }

        assert public_entries == complete_entries
        assert {(abbr, False) for abbr in ALL_GUARDED} <= public_entries

    def test_guarded_inventory_updates_with_shared_expander(self):
        entry = AbbreviationEntry(
            abbreviation="Ref.",
            expansion="Reference",
            only_if_followed_by=r"[ \t]+\d",
        )
        get_expander().add_abbreviation(entry)

        assert ("Ref.", False) in get_abbreviation_entries("en-us")
        assert [token.text for token in _regex_tokens("Ref. 8")] == ["Ref.", "8"]
        assert [token.text for token in _regex_tokens("A ref.")][-2:] == [
            "ref",
            ".",
        ]


class TestMergeWithoutSourceText:
    """Merging fails closed only for entries that require context."""

    @staticmethod
    def _merge(tokens):
        return merge_abbreviation_tokens(
            tokens,
            "en-us",
            is_break=lambda _prev, current, last_end: current.char_start != last_end,
            build_token=lambda start, end, text: ProcessingToken(
                text=text,
                char_start=start.char_start,
                char_end=end.char_end,
            ),
        )

    def test_guarded_entry_is_not_merged_without_source_text(self):
        tokens = [
            ProcessingToken(text="in", char_start=0, char_end=2),
            ProcessingToken(text=".", char_start=2, char_end=3),
        ]

        assert [token.text for token in self._merge(tokens)] == ["in", "."]

    def test_unguarded_entry_still_merges_without_source_text(self):
        tokens = [
            ProcessingToken(text="Mr", char_start=0, char_end=2),
            ProcessingToken(text=".", char_start=2, char_end=3),
        ]

        assert [token.text for token in self._merge(tokens)] == ["Mr."]


class TestGuardMatcher:
    """The shared matcher supports string and compiled regex guards."""

    def test_string_guards_match_at_exact_offsets(self):
        entry = AbbreviationEntry(
            abbreviation="in.",
            expansion="inch",
            only_if_preceded_by=r"(?:^|[^\w.])\d[ \t]*\Z",
        )
        text = "Use 5 in."
        start = text.index("in.")

        assert abbreviation_guards_match(entry, text, start, start + 3)

    def test_compiled_guards_match_at_exact_offsets(self):
        entry = AbbreviationEntry(
            abbreviation="No.",
            expansion="Number",
            only_if_followed_by=re.compile(r"[ \t]+\d"),
        )
        text = "No. 7"

        assert abbreviation_guards_match(entry, text, 0, 3)

    @pytest.mark.parametrize(("start", "end"), [(-1, 2), (3, 2), (0, 99)])
    def test_invalid_offsets_fail_closed(self, start, end):
        entry = AbbreviationEntry(
            abbreviation="No.",
            expansion="Number",
            only_if_followed_by=r"[ \t]+\d",
        )

        assert not abbreviation_guards_match(entry, "No. 7", start, end)


@pytest.mark.parametrize(("tokenizer_name", "tokenize"), TOKENIZERS)
class TestFollowedByNumberMerging:
    """Reference abbreviations merge only before same-line numbers."""

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    @pytest.mark.parametrize("spacing", [" ", "\t", "   "])
    def test_valid_context_merges(
        self, tokenizer_name, tokenize, abbreviation, spacing
    ):
        del tokenizer_name
        tokens = tokenize(f"{abbreviation}{spacing}7")

        assert tokens[0].text == abbreviation
        assert tokens[0].char_start == 0
        assert tokens[0].char_end == len(abbreviation)

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    def test_adjacent_number_without_separator_does_not_merge(
        self, tokenizer_name, tokenize, abbreviation
    ):
        del tokenizer_name
        tokens = tokenize(f"{abbreviation}7")

        assert [token.text for token in tokens] == [abbreviation[:-1], ".", "7"]

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    def test_sentence_final_context_does_not_merge(
        self, tokenizer_name, tokenize, abbreviation
    ):
        del tokenizer_name
        text = f"The answer was {abbreviation}"
        tokens = tokenize(text)

        assert [token.text for token in tokens[-2:]] == [abbreviation[:-1], "."]
        assert tokens[-2].char_start == text.index(abbreviation)
        assert tokens[-1].char_start == len(text) - 1
        assert tokens[-1].char_end == len(text)

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    def test_newline_before_number_does_not_merge(
        self, tokenizer_name, tokenize, abbreviation
    ):
        del tokenizer_name
        tokens = tokenize(f"{abbreviation}\n7")

        assert [token.text for token in tokens[:2]] == [abbreviation[:-1], "."]
        assert tokens[-1].text == "7"


@pytest.mark.parametrize(("tokenizer_name", "tokenize"), TOKENIZERS)
class TestPrecededByNumberMerging:
    """Dotted unit abbreviations merge only after a numeric value."""

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER_DOTTED)
    @pytest.mark.parametrize("value", ["5", "10.0", "30,000", "30,000.10", ".5"])
    def test_valid_context_merges(self, tokenizer_name, tokenize, abbreviation, value):
        del tokenizer_name
        text = f"{value} {abbreviation}"
        tokens = tokenize(text)

        assert tokens[-1].text == abbreviation
        assert tokens[-1].char_start == len(value) + 1
        assert tokens[-1].char_end == len(text)

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER_DOTTED)
    def test_non_numeric_context_does_not_merge(
        self, tokenizer_name, tokenize, abbreviation
    ):
        del tokenizer_name
        text = f"Word {abbreviation}"
        tokens = tokenize(text)

        assert [token.text for token in tokens[-2:]] == [abbreviation[:-1], "."]

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER_DOTTED)
    def test_word_attached_digit_does_not_satisfy_guard(
        self, tokenizer_name, tokenize, abbreviation
    ):
        del tokenizer_name
        text = f"ModelX5 {abbreviation}"
        tokens = tokenize(text)

        assert [token.text for token in tokens[-2:]] == [abbreviation[:-1], "."]

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER_DOTTED)
    def test_number_on_previous_line_does_not_satisfy_guard(
        self, tokenizer_name, tokenize, abbreviation
    ):
        del tokenizer_name
        tokens = tokenize(f"5\n{abbreviation}")

        assert [token.text for token in tokens[-2:]] == [abbreviation[:-1], "."]


class TestGuardedMergingWithoutTrackedPositions:
    """Guard evaluation remains correct when token positions are disabled."""

    @pytest.fixture
    def tokenizer(self):
        return RegexTokenizer(lang="en-us", track_positions=False)

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("5 in.", ["5", "in."]),
            ("wandering around in.", ["wandering", "around", "in", "."]),
            ("No. 7", ["No.", "7"]),
            ("The answer was no.", ["The", "answer", "was", "no", "."]),
        ],
    )
    def test_context_is_inferred_from_source_text(self, tokenizer, text, expected):
        assert [token.text for token in tokenizer.tokenize(text)] == expected


class TestNormalizerGuardHardening:
    """Normalizer guards reject cross-token and cross-line false positives."""

    @pytest.fixture
    def expander(self):
        return EnglishAbbreviationExpander()

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER)
    def test_valid_integer_unit_expands(self, expander, abbreviation):
        entry = expander.get_abbreviation(abbreviation)
        assert entry is not None

        assert expander.expand(f"5 {abbreviation}") == f"5 {entry.expansion}"

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER)
    def test_word_attached_digit_is_not_a_unit_context(self, expander, abbreviation):
        text = f"ModelX5 {abbreviation}"

        assert expander.expand(text) == text

    @pytest.mark.parametrize("abbreviation", PRECEDED_BY_NUMBER)
    def test_previous_line_number_is_not_a_unit_context(self, expander, abbreviation):
        text = f"5\n{abbreviation}"

        assert expander.expand(text) == text

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    def test_next_line_number_is_not_a_reference_context(self, expander, abbreviation):
        text = f"{abbreviation}\n7"

        assert expander.expand(text) == text

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    def test_adjacent_number_is_not_a_reference_context(self, expander, abbreviation):
        text = f"{abbreviation}7"

        assert expander.expand(text) == text

    @pytest.mark.parametrize("abbreviation", FOLLOWED_BY_NUMBER)
    @pytest.mark.parametrize("spacing", [" ", "\t", "   "])
    def test_same_line_number_is_a_reference_context(
        self, expander, abbreviation, spacing
    ):
        entry = expander.get_abbreviation(abbreviation)
        assert entry is not None

        assert expander.expand(f"{abbreviation}{spacing}7") == (
            f"{entry.expansion}{spacing}7"
        )

    @pytest.mark.parametrize(
        "value",
        ["5", "10.0", "30,000", "30,000.10", ".5"],
    )
    @pytest.mark.parametrize("abbreviation", ["in.", "ft.", "kg"])
    def test_supported_numeric_forms_expand(self, expander, value, abbreviation):
        entry = expander.get_abbreviation(abbreviation)
        assert entry is not None

        assert expander.expand(f"{value} {abbreviation}") == (
            f"{value} {entry.expansion}"
        )

    @pytest.mark.parametrize(
        "text",
        [
            "Literally because the thing was so big, and because multiple intel "
            "sources suggested it would be difficult to move around in.",
            "wandering around in.",
            "Wizard of Oz.",
            "Ft. Lauderdale",
            "The answer was no.",
        ],
    )
    def test_reported_and_related_false_contexts_remain_unchanged(self, expander, text):
        assert expander.expand(text) == text


class TestOffsetNumericConsistency:
    """Offset tokenization preserves the numeric forms used by regex G2P."""

    @pytest.mark.parametrize(
        "value",
        [".02", "3.14", "30,000", "30,000.10", "1.02.3"],
    )
    @pytest.mark.parametrize("keep_punct", [True, False])
    def test_numeric_token_is_preserved_with_offsets(self, value, keep_punct):
        tokens = tokenize_with_offsets(value, keep_punct=keep_punct)

        assert [token.text for token in tokens] == [value]
        assert tokens[0].char_start == 0
        assert tokens[0].char_end == len(value)
