"""Tests for the English lexicon.

This suite includes:
- Deterministic unit tests using a tiny in-memory lexicon (mini_lexicon)
- A few integration tests using the real shipped dictionaries (us_lexicon/gb_lexicon)
"""

import re

import pytest

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

# =============================================================================
# Deterministic fixture: tiny in-memory lexicon
# =============================================================================


@pytest.fixture
def mini_lexicon():
    """A tiny lexicon with hand-picked entries for deterministic tests.

    We disable dictionary loading to avoid dependence on packaged JSON content.
    """
    lex = Lexicon(british=False, load_gold=False, load_silver=False)

    # Minimal "letter names" for get_NNP / dotted abbreviations
    letters = {
        "A": "ˈA",
        "B": "bˈi",
        "C": "sˈi",
        "U": "jˈu",
        "S": "ˈɛs",
        "X": "ˈɛks",
        "Y": "wˈI",
        "Z": "zˈi",
    }

    lex.golds = {
        # Words for suffix allomorph tests
        "cat": "kæt",  # ends in t -> plural s
        "cap": "kæp",  # ends in p -> plural s
        "buzz": "bʌz",  # ends in z -> plural ᵻz
        "wish": "wɪʃ",  # ends in ʃ -> plural ᵻz
        "judge": "ʤʌʤ",  # ends in ʤ -> plural ᵻz
        "walk": "wɔk",  # ends in k -> -ed t, -ing ɪŋ
        "need": "nid",  # ends in d -> -ed ᵻd
        "wait": "wAt",  # ends in t preceded by A -> US flap in -ed/-ing
        # Symbols / special-case targets
        "percent": "pɚsˈɛnt",
        "and": "ˈænd",
        "plus": "plˈʌs",
        "at": "ˈæt",
        "dot": "dˈɑt",
        "slash": "slˈæʃ",
        "versus": "vˈɜsəs",
        # Normalization targets
        "don't": "dˈont",
        "alpha": "ˈælfə",
        # Proper noun stem false-positive regression setup
        # (These stems being "known" is what used to trigger wrong stemming.)
        "Lo": "lO",
        "Angele": "ˌAˌɛnʤˌiˌiˌɛlˈi",
        # Hyphenated word presence check
        "mother-in-law": "mʌðɚɪnlɔ",
        # Tag-dependent dictionary entry
        "lead": {"VERB": "lˈid", "NOUN": "lˈɛd", "DEFAULT": "lˈid"},
        # Dict entry that selects "None" when ctx.future_vowel is None
        "foo": {"None": "fˈu", "DEFAULT": "fˈo"},
        # Add letters
        **letters,
        # Capitalized variant used in possessive test
        "Cat": "kæt",
    }

    # Silver entry to test fallback + rating=3
    lex.silvers = {
        "silverword": "sˈɪlvɚ",
    }
    return lex


# =============================================================================
# TokenContext
# =============================================================================


class TestTokenContext:
    def test_default_values(self):
        ctx = TokenContext()
        assert ctx.future_vowel is None
        assert ctx.future_to is False

    def test_custom_values(self):
        ctx = TokenContext(future_vowel=True, future_to=True)
        assert ctx.future_vowel is True
        assert ctx.future_to is True


# =============================================================================
# apply_stress
# =============================================================================


class TestApplyStress:
    def test_none_input(self):
        assert apply_stress(None, 0) is None
        assert apply_stress("test", None) == "test"
        assert apply_stress(None, None) is None

    @pytest.mark.parametrize(
        "ps,stress,expected",
        [
            ("hˈɛlˌO", -2, "hɛlO"),
            ("kˈæt", -2, "kæt"),
            ("kˌæt", -2, "kæt"),
        ],
    )
    def test_remove_all_stress(self, ps, stress, expected):
        assert apply_stress(ps, stress) == expected

    def test_demote_primary_to_secondary(self):
        out = apply_stress("kˈæt", -1)
        assert out is not None
        assert PRIMARY_STRESS not in out
        assert SECONDARY_STRESS in out

    def test_neutral_demotes_primary_if_present(self):
        out = apply_stress("kˈæt", 0)
        assert out is not None
        assert PRIMARY_STRESS not in out
        assert SECONDARY_STRESS in out

    def test_add_secondary_stress_places_it_before_first_vowel(self):
        out = apply_stress("kæt", 0.5)
        assert out is not None
        # Stress marker should be directly before a vowel (restress behavior)
        assert re.search(
            rf"{re.escape(SECONDARY_STRESS)}[{re.escape(''.join(VOWELS))}]", out
        )

    def test_add_primary_stress_when_forced(self):
        out = apply_stress("kæt", 2)
        assert out is not None
        assert PRIMARY_STRESS in out
        assert re.search(
            rf"{re.escape(PRIMARY_STRESS)}[{re.escape(''.join(VOWELS))}]", out
        )

    def test_promote_secondary_to_primary(self):
        out = apply_stress("kˌæt", 1)
        assert out is not None
        assert PRIMARY_STRESS in out
        assert SECONDARY_STRESS not in out

    def test_no_vowels_does_not_inject_stress(self):
        # If there are no vowels, apply_stress should not add stress markers.
        assert apply_stress("ts", 2) == "ts"
        assert apply_stress("ts", 0.5) == "ts"


# =============================================================================
# stress_weight
# =============================================================================


class TestStressWeight:
    def test_empty_or_none(self):
        assert stress_weight("") == 0
        assert stress_weight(None) == 0

    def test_exact_counting(self):
        # It counts every character; diphthongs count as 2.
        assert stress_weight("kæt") == 3
        assert stress_weight("A") == 2
        assert stress_weight("æ") == 1

    def test_diphthong_heavier_than_monophthong(self):
        assert stress_weight("A") > stress_weight("æ")


# =============================================================================
# is_digit
# =============================================================================


class TestIsDigit:
    def test_digits(self):
        assert is_digit("123") is True
        assert is_digit("0") is True
        assert is_digit("999") is True

    def test_non_digits(self):
        assert is_digit("abc") is False
        assert is_digit("12a") is False
        assert is_digit("") is False

    def test_unicode_digits_are_not_accepted(self):
        # is_digit() is ASCII-only by design (regex [0-9]+)
        assert is_digit("١٢٣") is False


# =============================================================================
# Lexicon: deterministic behavior
# =============================================================================


class TestLexiconDeterministic:
    def test_grow_dictionary_adds_case_variants(self):
        d = {"hello": "hɛlO", "World": "wɜːld"}
        grown = Lexicon._grow_dictionary(d)
        # "hello" -> adds "Hello"
        assert "Hello" in grown
        # "World" (Capitalize form) -> adds "world"
        assert "world" in grown
        # originals still present
        assert "hello" in grown and "World" in grown

    def test_get_parent_tag(self):
        assert Lexicon.get_parent_tag("VB") == "VERB"
        assert Lexicon.get_parent_tag("VBD") == "VERB"
        assert Lexicon.get_parent_tag("VBZ") == "VERB"
        assert Lexicon.get_parent_tag("NN") == "NOUN"
        assert Lexicon.get_parent_tag("NNS") == "NOUN"
        assert Lexicon.get_parent_tag("JJ") == "ADJ"
        assert Lexicon.get_parent_tag("RB") == "ADV"
        assert Lexicon.get_parent_tag(None) is None

    def test_numeric_if_needed_unicode_digit(self):
        # Arabic-Indic digit ٣
        assert Lexicon.numeric_if_needed("٣") == "3"
        assert Lexicon.numeric_if_needed("7") == "7"
        assert Lexicon.numeric_if_needed("x") == "x"

    def test_normalize_greek(self, mini_lexicon):
        assert mini_lexicon.normalize_greek("α") == "alpha"
        assert mini_lexicon.normalize_greek("β") == "beta"
        assert mini_lexicon.normalize_greek("fooαbar") == "fooalphabar"

    def test_curly_apostrophe_normalization(self, mini_lexicon):
        ps1, r1 = mini_lexicon("don't")
        ps2, r2 = mini_lexicon("don’t")  # U+2019
        assert (ps1, r1) == (ps2, r2)

    def test_lookup_prefers_gold_over_silver_and_sets_rating(self, mini_lexicon):
        # Gold -> rating 4
        ps, rating = mini_lexicon.lookup("cat")
        assert ps == "kæt"
        assert rating == 4

        # Silver -> rating 3
        ps, rating = mini_lexicon.lookup("silverword")
        assert ps == "sˈɪlvɚ"
        assert rating == 3

    def test_lookup_tagged_dictionary_entry_uses_parent_tag(self, mini_lexicon):
        ps_verb, _ = mini_lexicon.lookup("lead", "VBD")  # parent tag -> VERB
        ps_noun, _ = mini_lexicon.lookup("lead", "NN")  # parent tag -> NOUN
        assert ps_verb == "lˈid"
        assert ps_noun == "lˈɛd"

    def test_lookup_dict_entry_can_select_None_key_when_future_vowel_is_None(
        self, mini_lexicon
    ):
        ctx = TokenContext(future_vowel=None)
        ps, _ = mini_lexicon.lookup("foo", tag="IN", stress=None, ctx=ctx)
        assert ps == "fˈu"

    def test_is_known_edgecases(self, mini_lexicon):
        assert mini_lexicon.is_known("cat") is True
        # All-caps tokens are treated as "known-ish" (acronym heuristic)
        assert mini_lexicon.is_known("HELLO") is True
        assert mini_lexicon.is_known("A") is True  # length 1 -> True
        assert mini_lexicon.is_known("mother-in-law") is True  # explicitly in golds
        assert mini_lexicon.is_known("nope🙂") is False  # invalid ordinal

        # But it still may not have a pronunciation without letters/entries
        ps, rating = mini_lexicon("HELLO")
        assert ps is None and rating is None

        ps, rating = mini_lexicon.lookup("USA", "NNP")
        assert ps is not None
        assert rating == 3

    def test_get_NNP_spells_letters(self, mini_lexicon):
        ps, rating = mini_lexicon.get_NNP("ABC")
        assert ps is not None
        assert rating == 3
        assert PRIMARY_STRESS in ps

    def test_dotted_abbreviation_goes_to_NNP(self, mini_lexicon):
        ps, rating = mini_lexicon.get_special_case("U.S.", None, None, None)
        assert ps is not None
        assert rating == 3

    def test_symbols(self, mini_lexicon):
        ps, _ = mini_lexicon.get_special_case("%", None, None, None)
        assert ps is not None  # % -> percent -> lookup

        ps, _ = mini_lexicon.get_special_case("&", None, None, None)
        assert ps is not None  # & -> and -> lookup

    def test_vs_special_case(self, mini_lexicon):
        ps, _ = mini_lexicon.get_special_case("vs.", "IN", None, None)
        assert ps is not None

    def test_to_and_in_context(self, mini_lexicon):
        # 'to' depends on future_vowel
        ps, _ = mini_lexicon.get_special_case(
            "to", "TO", None, TokenContext(future_vowel=True)
        )
        assert ps == "tʊ"
        ps, _ = mini_lexicon.get_special_case(
            "to", "TO", None, TokenContext(future_vowel=False)
        )
        assert ps == "tə"

        # 'in' adds stress marker depending on tag/context (see implementation)
        ps, _ = mini_lexicon.get_special_case(
            "in", "IN", None, TokenContext(future_vowel=True)
        )
        assert ps == "ɪn"  # stress_mark becomes "" in that branch
        ps, _ = mini_lexicon.get_special_case("in", None, None, None)
        assert ps == "ˈɪn"

    def test_the_context(self, mini_lexicon):
        ps, _ = mini_lexicon.get_special_case(
            "the", "DT", None, TokenContext(future_vowel=True)
        )
        assert ps == "ði"
        ps, _ = mini_lexicon.get_special_case(
            "the", "DT", None, TokenContext(future_vowel=False)
        )
        assert ps == "ðə"

    def test_greek_letter_lookup_via___call__(self, mini_lexicon):
        # α -> alpha -> lookup("alpha")
        ps, rating = mini_lexicon("α")
        assert ps == "ˈælfə"
        assert rating == 4


# =============================================================================
# Suffix handling (deterministic)
# =============================================================================


class TestSuffixesDeterministic:
    def test__s_allomorphs(self, mini_lexicon):
        # voiceless end -> s
        assert mini_lexicon._s("kæp").endswith("s")
        # sibilant end -> ᵻz (US)
        assert mini_lexicon._s("bʌz").endswith("ᵻz")
        assert mini_lexicon._s("wɪʃ").endswith("ᵻz")
        assert mini_lexicon._s("ʤʌʤ").endswith("ᵻz")
        # default -> z
        assert mini_lexicon._s("kæb").endswith("z")

    def test_stem_s_regular_plural(self, mini_lexicon):
        ps, rating = mini_lexicon.stem_s("cats", "NNS", None, None)
        assert ps == "kæts"
        assert rating == 4

    def test_stem_s_possessive_allowed_even_when_capitalized(self, mini_lexicon):
        ps, rating = mini_lexicon.stem_s("Cat's", None, None, None)
        assert ps is not None and rating is not None
        assert ps.endswith("s")  # Cat -> kæt -> kæts

    def test_stem_s_regression_los_angeles_should_not_stem(self, mini_lexicon):
        # This reproduces the old failure mode:
        # "Los" -> stem "Lo" (known) and add /z/
        # "Angeles" -> stem "Angele" (known) and add /z/
        #
        # After the fix, stem_s should refuse to stem capitalized tokens without POS,
        # and should refuse for proper nouns.
        assert mini_lexicon.stem_s("Los", None, 0, None) == (None, None)
        assert mini_lexicon.stem_s("Angeles", None, 0, None) == (None, None)
        assert mini_lexicon.stem_s("Los", "NNP", 0, None) == (None, None)
        assert mini_lexicon.stem_s("Angeles", "NNP", 0, None) == (None, None)
        assert mini_lexicon.stem_s("Los", "PROPN", 0, None) == (None, None)
        assert mini_lexicon.stem_s("Angeles", "PROPN", 0, None) == (None, None)

    def test__ed_variants(self, mini_lexicon):
        # voiceless ending -> t
        assert mini_lexicon._ed("wɔk").endswith("t")
        # ending d -> ᵻd
        assert mini_lexicon._ed("nid").endswith("ᵻd")
        # US flap case: ...At + ed -> ...Aɾᵻd
        assert mini_lexicon._ed("wAt").endswith("ɾᵻd")

    def test_stem_ed_regular(self, mini_lexicon):
        ps, rating = mini_lexicon.stem_ed("walked", "VBD", None, None)
        assert ps == "wɔkt"
        assert rating == 4

    def test__ing_variants(self, mini_lexicon):
        assert mini_lexicon._ing("wɔk") == "wɔkɪŋ"
        # US flap case: ...At + ing -> ...Aɾɪŋ
        assert mini_lexicon._ing("wAt") == "wAɾɪŋ"

    def test_stem_ing_regular(self, mini_lexicon):
        ps, rating = mini_lexicon.stem_ing("walking", "VBG", None, None)
        assert ps == "wˌɔkɪŋ"
        assert rating == 4

    def test_get_word_lowercasing_path_for_plural(self, mini_lexicon):
        # "Cats" isn't in golds, but lowercasing+stem_s
        # should still succeed with tag NNS.
        ps, rating = mini_lexicon.get_word("Cats", "NNS", None, None)
        assert ps is not None and rating is not None
        assert ps.endswith("s")


# =============================================================================
# Lexicon: number detection
# =============================================================================


class TestNumberDetection:
    def test_is_number_more_cases(self):
        assert Lexicon.is_number("123", True) is True
        assert Lexicon.is_number("12,345", True) is True
        assert Lexicon.is_number("3.1415", True) is True
        assert Lexicon.is_number("-100", True) is True
        assert Lexicon.is_number("-100", False) is False
        assert Lexicon.is_number("1st", True) is True
        assert Lexicon.is_number("2nd", True) is True
        assert Lexicon.is_number("100th", True) is True
        assert Lexicon.is_number("hello", True) is False


# =============================================================================
# Integration tests (real dictionaries)
# =============================================================================


class TestLexiconIntegration:
    def test_creation_us(self, us_lexicon):
        assert us_lexicon.british is False

    def test_creation_gb(self, gb_lexicon):
        assert gb_lexicon.british is True

    def test_lookup_common_word(self, us_lexicon):
        ps, rating = us_lexicon.lookup("hello")
        assert isinstance(ps, str) and ps
        assert rating in (3, 4)

    def test_callable_interface(self, us_lexicon):
        ps, rating = us_lexicon("hello")
        assert ps is not None
        assert rating is not None

    def test_unknown_word_returns_none(self, us_lexicon):
        ps, rating = us_lexicon("xyzqwertyuiop")
        assert ps is None or rating is None

    def test_special_case_the(self, us_lexicon):
        ctx_vowel = TokenContext(future_vowel=True)
        ps_vowel, _ = us_lexicon.get_special_case("the", "DT", None, ctx_vowel)
        assert ps_vowel == "ði"

        ctx_consonant = TokenContext(future_vowel=False)
        ps_cons, _ = us_lexicon.get_special_case("the", "DT", None, ctx_consonant)
        assert ps_cons == "ðə"

    @pytest.mark.parametrize("word", ["read", "reread", "wound"])
    def test_homographs_vbp_falls_back_to_default_present_us(self, us_lexicon, word):
        ps_default, _ = us_lexicon.lookup(word)
        ps_vbp, _ = us_lexicon.lookup(word, "VBP")  # spaCy present tense tag
        ps_vbd, _ = us_lexicon.lookup(word, "VBD")
        ps_vbn, _ = us_lexicon.lookup(word, "VBN")

        assert ps_default is not None
        assert ps_vbp == ps_default  # present tense must match DEFAULT

        assert ps_vbd is not None and ps_vbn is not None
        assert ps_vbd == ps_vbn  # past == past participle for these entries
        assert ps_vbp != ps_vbd  # present must differ from past

        entry = us_lexicon.golds.get(word)
        assert isinstance(entry, dict)
        if "VBP" in entry:
            assert entry["VBP"] == entry["DEFAULT"]

    @pytest.mark.parametrize("word", ["read", "reread", "wound"])
    def test_homographs_vbp_falls_back_to_default_present_gb(self, gb_lexicon, word):
        ps_default, _ = gb_lexicon.lookup(word)
        ps_vbp, _ = gb_lexicon.lookup(word, "VBP")  # spaCy present tense tag
        ps_vbd, _ = gb_lexicon.lookup(word, "VBD")
        ps_vbn, _ = gb_lexicon.lookup(word, "VBN")

        assert ps_default is not None
        assert ps_vbp == ps_default  # present tense must match DEFAULT

        assert ps_vbd is not None and ps_vbn is not None
        assert ps_vbd == ps_vbn  # past == past participle for these entries
        assert ps_vbp != ps_vbd  # present must differ from past

        entry = gb_lexicon.golds.get(word)
        assert isinstance(entry, dict)
        if "VBP" in entry:
            assert entry["VBP"] == entry["DEFAULT"]


# =============================================================================
# Constants
# =============================================================================


class TestConstants:
    def test_consonants(self):
        assert "b" in CONSONANTS
        assert "d" in CONSONANTS
        assert "ʃ" in CONSONANTS
        assert "a" not in CONSONANTS

    def test_vowels(self):
        assert "a" in VOWELS
        assert "i" in VOWELS
        assert "A" in VOWELS
        assert "b" not in VOWELS

    def test_diphthongs(self):
        assert "A" in DIPHTHONGS
        assert "I" in DIPHTHONGS
        assert "O" in DIPHTHONGS
        assert "a" not in DIPHTHONGS

    def test_stress_markers(self):
        assert PRIMARY_STRESS == "ˈ"
        assert SECONDARY_STRESS == "ˌ"

    def test_vowels_and_consonants_disjoint(self):
        assert CONSONANTS.isdisjoint(VOWELS)
