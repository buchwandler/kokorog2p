#!/usr/bin/env python3
"""Random sentence generator for English synthetic test cases.

Generates test sentences covering:
- Quotes, contractions, and punctuation
- Abbreviations (titles, places, dates, measurements)
- Numbers (cardinals, ordinals, decimals, fractions)
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

CONTRACTIONS = [
    "don't",
    "can't",
    "won't",
    "I'm",
    "we're",
    "they're",
    "you're",
    "she's",
    "he's",
    "it's",
    "that's",
    "what's",
    "who's",
    "there's",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "hasn't",
    "haven't",
    "hadn't",
    "doesn't",
    "didn't",
    "wouldn't",
    "shouldn't",
    "couldn't",
    "I've",
    "we've",
    "you've",
    "they've",
    "I'd",
    "we'd",
    "you'd",
    "they'd",
    "he'd",
    "she'd",
    "I'll",
    "we'll",
    "you'll",
    "they'll",
    "he'll",
    "she'll",
    "it'll",
    "that'll",
]

INFORMAL_CONTRACTIONS = [
    "gonna",
    "wanna",
    "gotta",
    "kinda",
    "sorta",
    "outta",
    "lemme",
    "gimme",
    "dunno",
    "hafta",
    "lotsa",
]

APOSTROPHES = {
    "standard": "'",
    "right_quote": "’",
    "left_quote": "‘",
    "grave": "`",
    "acute": "´",
    "modifier": "ʹ",
    "prime": "′",
    "fullwidth": "＇",
}

QUOTE_PAIRS = {
    "ascii_double": ('"', '"'),
    "curly_double": ("\u201c", "\u201d"),
    "curly_single": ("\u2018", "\u2019"),
    "guillemets": ("«", "»"),
    "single_low_high": ("\u201a", "\u2019"),
    "double_low_high": ("\u201e", "\u201d"),
    "asian_corner": ("「", "」"),
    "fullwidth": ("＂", "＂"),
    "prime_double": ("″", "″"),
}

PUNCTUATION = [";", ":", ",", ".", "!", "?", "—", "…"]

PUNCTUATION_VARIANTS = {
    "ellipsis_dots": "...",
    "ellipsis_spaced": ". . .",
    "ellipsis_four": "....",
    "ellipsis_two": "..",
    "ellipsis_char": "…",
    "hyphen": "-",
    "en_dash": "–",
    "em_dash": "—",
    "double_hyphen": "--",
    "horizontal_bar": "―",
    "figure_dash": "‒",
    "minus_sign": "−",
    "double_exclaim": "!!",
    "triple_exclaim": "!!!",
    "double_question": "??",
    "interrobang": "?!",
    "reverse_interrobang": "!?",
}

# Dash variants - all should normalize to em dash in vocab
DASH_VARIANTS = {
    "hyphen": "-",  # U+002D (hyphen-minus)
    "en_dash": "–",  # U+2013
    "em_dash": "—",  # U+2014
    "double_hyphen": "--",  # Two hyphens (common in typing)
    "horizontal_bar": "―",  # U+2015
    "figure_dash": "‒",  # U+2012
    "minus_sign": "−",  # U+2212
}

BASE_WORDS = [
    "hello",
    "world",
    "test",
    "example",
    "simple",
    "word",
    "great",
    "quick",
    "brown",
    "fox",
    "jumps",
    "over",
    "lazy",
    "dog",
    "the",
    "and",
    "but",
    "or",
    "so",
    "yet",
    "for",
    "nor",
    "said",
    "asked",
    "replied",
    "think",
    "know",
    "see",
    "go",
    "come",
    "take",
    "make",
    "get",
    "give",
    "tell",
    "work",
    "call",
    "try",
    "feel",
    "leave",
    "put",
    "mean",
    "keep",
    "let",
    "begin",
    "seem",
    "help",
    "show",
    "hear",
    "play",
    "run",
    "move",
    "like",
    "live",
    "believe",
    "bring",
    "write",
]

# Abbreviations (from kokorog2p/en/abbreviations.py)
ABBREVIATIONS: dict[str, list[str]] = {
    "titles": ["Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Rev."],
    "places": ["St.", "Ave.", "Rd.", "Blvd.", "Ln.", "Ct."],
    "days": ["Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.", "Sun."],
    "months": [
        "Jan.",
        "Feb.",
        "Mar.",
        "Apr.",
        "Jun.",
        "Jul.",
        "Aug.",
        "Sep.",
        "Oct.",
        "Nov.",
        "Dec.",
    ],
    "time": ["A.M.", "P.M.", "EST", "PST", "GMT"],
    "academic": ["Ph.D.", "M.D.", "B.A.", "M.A.", "B.S.", "M.S."],
    "common": ["etc.", "vs.", "e.g.", "i.e.", "no.", "vol.", "pg.", "approx."],
    "measurements": ["in.", "ft.", "mi.", "oz.", "lb.", "gal."],
    "directional": ["N.", "S.", "E.", "W.", "NE.", "NW.", "SE.", "SW."],
}

# Number formats to test
NUMBER_FORMATS: dict[str, list[str | int]] = {
    "cardinal": [0, 1, 5, 10, 42, 100, 1000, 2024],
    "ordinal_suffix": ["1st", "2nd", "3rd", "4th", "21st", "42nd", "100th"],
    "decimal": ["3.14", "0.5", "99.99", "1.0"],
    "percentage": ["50%", "100%", "33.3%", "0.1%"],
    "fraction": ["1/2", "3/4", "2/3", "1/4"],
    "currency": ["$5", "$1.99", "$1000", "$0.99"],
    "year": [1984, 2000, 2024, 1776],
    "phone": ["555-1234", "555-0100"],
    "time": ["3:00", "12:30", "9:45"],
}


@dataclass
class TestCase:
    text: str
    category: str
    params: dict[str, Any]
    expected_phonemes: str = ""


class SentenceGenerator:
    def __init__(
        self,
        seed: int = 42,
        g2p: Callable[[str], list[Any]] | None = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.g2p = g2p

    def _random_word(self) -> str:
        return self.rng.choice(BASE_WORDS)

    def _random_words(self, count: int) -> list[str]:
        return [self._random_word() for _ in range(count)]

    def _apply_apostrophe(self, contraction: str, apostrophe_type: str) -> str:
        if apostrophe_type not in APOSTROPHES:
            apostrophe_type = "standard"
        apostrophe = APOSTROPHES[apostrophe_type]
        result = contraction.replace("'", apostrophe)
        result = result.replace("'", apostrophe)
        result = result.replace("`", apostrophe)
        return result

    def _generate_expected_phonemes(self, text: str) -> str:
        """Generate expected phonemes for a given text.

        Args:
            text: Input text

        Returns:
            Expected phonemes with proper formatting
            (no spaces around punctuation/quotes)
        """
        if self.g2p is None:
            return ""

        import re

        tokens = self.g2p(text)
        phonemes = " ".join(t.phonemes for t in tokens if t.phonemes)

        # Remove spaces around punctuation
        phonemes = phonemes.replace(" , ", ",").replace(" .", ".")
        phonemes = phonemes.replace(" !", "!").replace(" ?", "?")
        phonemes = phonemes.replace(" ;", ";").replace(" :", ":")
        phonemes = phonemes.replace(" …", "…").replace(" … ", "…").replace("… ", "…")
        phonemes = phonemes.replace(" — ", "—").replace(" – ", "–")
        phonemes = phonemes.replace(" —", "—").replace(" –", "–")
        phonemes = phonemes.replace("— ", "—").replace("– ", "–")

        # Remove spaces after opening quotes and before closing quotes (all types)
        # Remove space after any quote-like character
        phonemes = re.sub(
            r'(["\'\u201c\u201d\u2018\u2019\u201a\u201e«»「」＂″‚„]) ',
            r"\1",
            phonemes,
        )
        # Remove space before any quote-like character
        phonemes = re.sub(
            r' (["\'\u201c\u201d\u2018\u2019\u201a\u201e«»「」＂″‚„])',
            r"\1",
            phonemes,
        )

        return phonemes

    def generate_contraction_test(
        self, apostrophe_type: str = "standard", num_contractions: int = 1
    ) -> TestCase:
        contractions = self.rng.sample(
            CONTRACTIONS + INFORMAL_CONTRACTIONS,
            min(num_contractions, len(CONTRACTIONS) + len(INFORMAL_CONTRACTIONS)),
        )
        contractions = [
            self._apply_apostrophe(c, apostrophe_type) for c in contractions
        ]

        if num_contractions == 1:
            words = self._random_words(2)
            text = f"{contractions[0].capitalize()} {words[0]} {words[1]}."
        else:
            words = self._random_words(num_contractions + 1)
            parts = []
            for i, contr in enumerate(contractions):
                parts.append(contr if i > 0 else contr.capitalize())
                parts.append(words[i])
            parts.append(words[-1])
            text = " ".join(parts) + "."

        return TestCase(
            text=text,
            category="apostrophe_variants",
            params={
                "apostrophe_type": apostrophe_type,
                "num_contractions": num_contractions,
                "apostrophe_char": APOSTROPHES[apostrophe_type],
            },
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_quote_test(self, quote_type: str = "ascii_double") -> TestCase:
        if quote_type not in QUOTE_PAIRS:
            quote_type = "ascii_double"
        left_quote, right_quote = QUOTE_PAIRS[quote_type]
        words = self._random_words(self.rng.randint(1, 4))
        quoted_text = " ".join(words)
        intro = self.rng.choice(["She said", "He asked", "They replied", "I think"])
        text = f"{intro}, {left_quote}{quoted_text}{right_quote}."
        return TestCase(
            text=text,
            category="quote_combinations",
            params={
                "quote_type": quote_type,
                "left_quote": left_quote,
                "right_quote": right_quote,
            },
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_punctuation_test(self, punct_type: str | None = None) -> TestCase:
        if punct_type is None:
            punct = self.rng.choice(PUNCTUATION)
            variant_name = "standard"
        elif punct_type in PUNCTUATION_VARIANTS:
            punct = PUNCTUATION_VARIANTS[punct_type]
            variant_name = punct_type
        else:
            punct = punct_type
            variant_name = "custom"

        words = self._random_words(self.rng.randint(3, 6))

        if punct in (",", ";", ":"):
            mid = len(words) // 2
            text = " ".join(words[:mid]) + punct + " " + " ".join(words[mid:]) + "."
        elif punct in ("—", "–", "-", "--", "―", "‒", "−"):
            mid = len(words) // 2
            text = (
                " ".join(words[:mid]) + " " + punct + " " + " ".join(words[mid:]) + "."
            )
        elif punct in ("…", "...", ". . .", "....", ".."):
            if self.rng.random() < 0.5:
                text = " ".join(words) + punct
            else:
                mid = len(words) // 2
                text = " ".join(words[:mid]) + punct + " " + " ".join(words[mid:]) + "."
        else:
            text = " ".join(words) + punct

        return TestCase(
            text=text.capitalize(),
            category="punctuation_detection",
            params={"punctuation": punct, "variant_name": variant_name},
            expected_phonemes=self._generate_expected_phonemes(text.capitalize()),
        )

    def generate_nested_quote_test(self) -> TestCase:
        outer_type = self.rng.choice(list(QUOTE_PAIRS.keys()))
        inner_type = self.rng.choice(["curly_single", "ascii_double", "curly_double"])
        outer_left, outer_right = QUOTE_PAIRS[outer_type]
        inner_left, inner_right = QUOTE_PAIRS[inner_type]
        inner_words = self._random_words(2)
        outer_words = self._random_words(2)
        inner_text = " ".join(inner_words)
        outer_start = " ".join(outer_words[:1])
        outer_end = " ".join(outer_words[1:])
        quoted = f"{outer_start} {inner_left}{inner_text}{inner_right} {outer_end}"
        text = f"She said, {outer_left}{quoted}{outer_right}."
        return TestCase(
            text=text,
            category="nested_quotes",
            params={"outer_quote_type": outer_type, "inner_quote_type": inner_type},
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_quote_with_contraction_test(
        self, apostrophe_type: str = "standard", quote_type: str = "ascii_double"
    ) -> TestCase:
        left_quote, right_quote = QUOTE_PAIRS.get(
            quote_type, QUOTE_PAIRS["ascii_double"]
        )
        contraction = self.rng.choice(CONTRACTIONS)
        contraction = self._apply_apostrophe(contraction, apostrophe_type)
        words = self._random_words(self.rng.randint(1, 3))
        quoted = f"{contraction} {' '.join(words)}"
        intro = self.rng.choice(["She said", "He asked", "They replied"])
        text = f"{intro}, {left_quote}{quoted}{right_quote}."
        return TestCase(
            text=text,
            category="quotes_and_contractions",
            params={
                "apostrophe_type": apostrophe_type,
                "quote_type": quote_type,
                "apostrophe_char": APOSTROPHES[apostrophe_type],
            },
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_complex_mixed_test(self) -> TestCase:
        apostrophe_type = self.rng.choice(list(APOSTROPHES.keys()))
        quote_type = self.rng.choice(list(QUOTE_PAIRS.keys()))
        punct = self.rng.choice(PUNCTUATION + list(PUNCTUATION_VARIANTS.values()))
        left_quote, right_quote = QUOTE_PAIRS[quote_type]
        contraction1 = self._apply_apostrophe(
            self.rng.choice(CONTRACTIONS), apostrophe_type
        )
        contraction2 = self._apply_apostrophe(
            self.rng.choice(CONTRACTIONS), self.rng.choice(list(APOSTROPHES.keys()))
        )
        words1 = self._random_words(2)
        words2 = self._random_words(2)
        quoted = f"{contraction1} {words1[0]}"
        text = (
            f"{contraction2.capitalize()} {words1[1]}, "
            f"{left_quote}{quoted}{right_quote} "
            f"{words2[0]} {words2[1]}{punct}"
        )
        return TestCase(
            text=text,
            category="complex_mixed",
            params={
                "apostrophe_types": [apostrophe_type],
                "quote_type": quote_type,
                "punctuation": punct,
            },
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_punctuation_adjacent_quote_test(self) -> TestCase:
        quote_type = self.rng.choice(list(QUOTE_PAIRS.keys()))
        left_quote, right_quote = QUOTE_PAIRS[quote_type]
        punct = self.rng.choice(["!", "?", ".", ",", "…", "...", ". . .", "—", "--"])
        words = self._random_words(3)
        quoted_words = self._random_words(2)
        quoted = " ".join(quoted_words)
        if self.rng.random() < 0.5:
            text = (
                f"{' '.join(words[:2])}, "
                f"{left_quote}{quoted}{punct}{right_quote} {words[2]}."
            )
        else:
            text = (
                f"{' '.join(words[:2])}, "
                f"{left_quote}{quoted}{right_quote}{punct} {words[2]}."
            )
        return TestCase(
            text=text.capitalize(),
            category="punctuation_adjacent_quotes",
            params={"quote_type": quote_type, "punctuation": punct},
            expected_phonemes=self._generate_expected_phonemes(text.capitalize()),
        )

    def generate_dash_test(self, dash_type: str | None = None) -> TestCase:
        """Generate test case with dash variants.

        All dash variants should normalize to em dash in the output.
        """
        if dash_type is None:
            dash_type = self.rng.choice(list(DASH_VARIANTS.keys()))
        elif dash_type not in DASH_VARIANTS:
            dash_type = "em_dash"

        dash = DASH_VARIANTS[dash_type]
        words = self._random_words(self.rng.randint(4, 7))

        # Create sentence with dash in middle or at end
        if self.rng.random() < 0.7:
            # Dash in middle (interrupter or parenthetical)
            mid = len(words) // 2
            text = f"{' '.join(words[:mid])}{dash}{' '.join(words[mid:])}."
        else:
            # Dash at end (abrupt ending)
            text = f"{' '.join(words)}{dash}"

        return TestCase(
            text=text.capitalize(),
            category="dash_variants",
            params={
                "dash_type": dash_type,
                "dash_char": dash,
            },
            expected_phonemes=self._generate_expected_phonemes(text.capitalize()),
        )

    def generate_abbreviation_test(
        self, abbrev_category: str | None = None
    ) -> TestCase:
        """Generate test case with abbreviations.

        Args:
            abbrev_category: Category of abbreviation (titles, places, days,
                           months, etc.). If None, randomly selects a category.

        Returns:
            TestCase with abbreviation.
        """
        if abbrev_category is None or abbrev_category not in ABBREVIATIONS:
            abbrev_category = self.rng.choice(list(ABBREVIATIONS.keys()))

        abbrev = self.rng.choice(ABBREVIATIONS[abbrev_category])
        words = self._random_words(self.rng.randint(2, 5))

        # Create different sentence patterns
        pattern = self.rng.choice(["start", "middle", "end"])

        if pattern == "start":
            text = f"{abbrev} {' '.join(words)}."
        elif pattern == "middle":
            mid = len(words) // 2
            text = f"{' '.join(words[:mid])} {abbrev} {' '.join(words[mid:])}."
        else:  # end
            text = f"{' '.join(words)} {abbrev}"

        return TestCase(
            text=text.capitalize(),
            category="abbreviations",
            params={
                "abbrev_category": abbrev_category,
                "abbreviation": abbrev,
                "position": pattern,
            },
            expected_phonemes=self._generate_expected_phonemes(text.capitalize()),
        )

    def generate_number_test(self, number_format: str | None = None) -> TestCase:
        """Generate test case with numbers in various formats.

        Args:
            number_format: Type of number (cardinal, ordinal_suffix, decimal, etc.)
                          If None, randomly selects a format.

        Returns:
            TestCase with numbers.
        """
        if number_format is None or number_format not in NUMBER_FORMATS:
            number_format = self.rng.choice(list(NUMBER_FORMATS.keys()))

        number: str | int = self.rng.choice(NUMBER_FORMATS[number_format])
        words = self._random_words(self.rng.randint(2, 4))

        # Create different sentence patterns
        pattern = self.rng.choice(["start", "middle", "end"])

        if pattern == "start":
            text = f"{number} {' '.join(words)}."
        elif pattern == "middle":
            mid = len(words) // 2
            text = f"{' '.join(words[:mid])} {number} {' '.join(words[mid:])}."
        else:  # end
            text = f"{' '.join(words)} {number}."

        return TestCase(
            text=text.capitalize(),
            category="numbers",
            params={
                "number_format": number_format,
                "number": str(number),
                "position": pattern,
            },
            expected_phonemes=self._generate_expected_phonemes(text.capitalize()),
        )

    def generate_mixed_abbrev_number_test(self) -> TestCase:
        """Generate test case with both abbreviations and numbers."""
        abbrev_cat = self.rng.choice(list(ABBREVIATIONS.keys()))
        abbrev = self.rng.choice(ABBREVIATIONS[abbrev_cat])

        number_format = self.rng.choice(list(NUMBER_FORMATS.keys()))
        number: str | int = self.rng.choice(NUMBER_FORMATS[number_format])

        words = self._random_words(self.rng.randint(1, 3))

        # Mix abbreviation and number
        if self.rng.random() < 0.5:
            text = f"{abbrev} {' '.join(words)} {number}."
        else:
            text = f"{number} {' '.join(words)} {abbrev}"

        return TestCase(
            text=text.capitalize(),
            category="mixed_abbrev_numbers",
            params={
                "abbrev_category": abbrev_cat,
                "abbreviation": abbrev,
                "number_format": number_format,
                "number": str(number),
            },
            expected_phonemes=self._generate_expected_phonemes(text.capitalize()),
        )

    def generate_batch(
        self, total: int = 1000, distribution: dict[str, int] | None = None
    ) -> list[TestCase]:
        if distribution is None:
            # Default proportions (percentages)
            default_proportions = {
                "apostrophe_variants": 0.15,  # 15%
                "quote_combinations": 0.10,  # 10%
                "punctuation_detection": 0.08,  # 8%
                "quotes_and_contractions": 0.10,  # 10%
                "nested_quotes": 0.04,  # 4%
                "punctuation_adjacent_quotes": 0.04,  # 4%
                "dash_variants": 0.10,  # 10%
                "complex_mixed": 0.10,  # 10%
                "abbreviations": 0.15,  # 15% - NEW
                "numbers": 0.10,  # 10% - NEW
                "mixed_abbrev_numbers": 0.04,  # 4% - NEW
            }
            # Scale proportions to actual counts
            distribution = {k: int(v * total) for k, v in default_proportions.items()}

        test_cases = []

        for _ in range(distribution.get("apostrophe_variants", 0)):
            apostrophe_type = self.rng.choice(list(APOSTROPHES.keys()))
            num_contractions = self.rng.randint(1, 3)
            test_cases.append(
                self.generate_contraction_test(apostrophe_type, num_contractions)
            )

        for _ in range(distribution.get("quote_combinations", 0)):
            quote_type = self.rng.choice(list(QUOTE_PAIRS.keys()))
            test_cases.append(self.generate_quote_test(quote_type))

        for _ in range(distribution.get("punctuation_detection", 0)):
            if self.rng.random() < 0.5:
                punct_type = self.rng.choice(list(PUNCTUATION_VARIANTS.keys()))
            else:
                punct_type = self.rng.choice(PUNCTUATION)
            test_cases.append(self.generate_punctuation_test(punct_type))

        for _ in range(distribution.get("quotes_and_contractions", 0)):
            apostrophe_type = self.rng.choice(list(APOSTROPHES.keys()))
            quote_type = self.rng.choice(list(QUOTE_PAIRS.keys()))
            test_cases.append(
                self.generate_quote_with_contraction_test(apostrophe_type, quote_type)
            )

        for _ in range(distribution.get("nested_quotes", 0)):
            test_cases.append(self.generate_nested_quote_test())

        for _ in range(distribution.get("punctuation_adjacent_quotes", 0)):
            test_cases.append(self.generate_punctuation_adjacent_quote_test())

        for _ in range(distribution.get("dash_variants", 0)):
            dash_type = self.rng.choice(list(DASH_VARIANTS.keys()))
            test_cases.append(self.generate_dash_test(dash_type))

        for _ in range(distribution.get("complex_mixed", 0)):
            test_cases.append(self.generate_complex_mixed_test())

        for _ in range(distribution.get("abbreviations", 0)):
            abbrev_cat = self.rng.choice(list(ABBREVIATIONS.keys()))
            test_cases.append(self.generate_abbreviation_test(abbrev_cat))

        for _ in range(distribution.get("numbers", 0)):
            number_format = self.rng.choice(list(NUMBER_FORMATS.keys()))
            test_cases.append(self.generate_number_test(number_format))

        for _ in range(distribution.get("mixed_abbrev_numbers", 0)):
            test_cases.append(self.generate_mixed_abbrev_number_test())

        self.rng.shuffle(test_cases)
        return test_cases[:total]


if __name__ == "__main__":
    import time
    from collections import Counter

    # Import G2P to show expected phonemes
    g2p: Callable[[str], list[Any]] | None = None
    try:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from kokorog2p.en import EnglishG2P

        g2p = EnglishG2P(language="en-us", use_espeak_fallback=True, use_spacy=True)
        has_g2p = True
    except ImportError:
        has_g2p = False
        print("Note: kokorog2p not available, showing text only (not phonemes)\n")

    # Use time-based seed for different examples on each run
    seed = int(time.time() * 1000) % 1000000
    print(f"Using random seed: {seed}\n")
    gen = SentenceGenerator(seed=seed, g2p=g2p)

    print("=== Sample Generated Test Cases ===\n")

    # Generate sample test cases from each category
    samples = [
        ("apostrophe_variants", gen.generate_contraction_test("right_quote", 2)),
        ("quote_combinations", gen.generate_quote_test("curly_double")),
        ("punctuation_detection", gen.generate_punctuation_test("ellipsis_spaced")),
        (
            "quotes_and_contractions",
            gen.generate_quote_with_contraction_test("grave", "curly_double"),
        ),
        ("nested_quotes", gen.generate_nested_quote_test()),
        ("dash_variants", gen.generate_dash_test("en_dash")),
        ("abbreviations", gen.generate_abbreviation_test()),
        ("numbers", gen.generate_number_test()),
        ("mixed_abbrev_numbers", gen.generate_mixed_abbrev_number_test()),
        ("complex_mixed", gen.generate_complex_mixed_test()),
    ]

    for i, (category, test_case) in enumerate(samples, 1):
        print(f"{i}. {category}")
        print(f"   Text: {test_case.text}")

        # Show expected phonemes if available
        if test_case.expected_phonemes:
            print(f"   Expected phonemes: {test_case.expected_phonemes}")

        # Show key parameters
        if "apostrophe_char" in test_case.params:
            apos_char = repr(test_case.params["apostrophe_char"])
            apos_type = test_case.params.get("apostrophe_type", "unknown")
            print(f"   Apostrophe used: {apos_char} ({apos_type})")
        if "quote_type" in test_case.params:
            print(f"   Quote type: {test_case.params['quote_type']}")
        if "punctuation" in test_case.params:
            print(f"   Punctuation: {repr(test_case.params['punctuation'])}")
        if "dash_char" in test_case.params:
            dash_char = repr(test_case.params["dash_char"])
            dash_type = test_case.params["dash_type"]
            print(f"   Dash used: {dash_char} ({dash_type})")
        if "abbreviation" in test_case.params:
            abbrev = test_case.params["abbreviation"]
            abbrev_cat = test_case.params["abbrev_category"]
            print(f"   Abbreviation: {abbrev} ({abbrev_cat})")
        if "number" in test_case.params:
            num = test_case.params["number"]
            num_fmt = test_case.params["number_format"]
            print(f"   Number: {num} ({num_fmt})")
        print()

    print("\nGenerating batch of 100 test cases...")
    batch = gen.generate_batch(100)
    print(f"Generated {len(batch)} test cases")

    dist = Counter(t.category for t in batch)
    print("\nCategory distribution:")
    for category, count in sorted(dist.items()):
        print(f"  {category}: {count}")
