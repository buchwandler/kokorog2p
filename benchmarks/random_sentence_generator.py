#!/usr/bin/env python3
"""Random sentence generator for English quote/contraction/punctuation testing."""

import random
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
    "curly_double": ("“", "”"),
    "curly_single": ("‘", "’"),
    "mixed_left_curly": ("“", '"'),
    "mixed_right_curly": ('"', "”"),
    "guillemets": ("«", "»"),
    "single_low_high": ("‚", "’"),
    "double_low_high": ("„", "“"),
    "asian_corner": ("「", "」"),
    "fullwidth": ("＂", "＂"),
    "grave_acute": ("`", "´"),
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


@dataclass
class TestCase:
    text: str
    category: str
    params: dict[str, Any]


class SentenceGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def _random_word(self) -> str:
        return self.rng.choice(BASE_WORDS)

    def _random_words(self, count: int) -> list[str]:
        return [self._random_word() for _ in range(count)]

    def _apply_apostrophe(self, contraction: str, apostrophe_type: str) -> str:
        if apostrophe_type not in APOSTROPHES:
            apostrophe_type = "standard"
        apostrophe = APOSTROPHES[apostrophe_type]
        result = contraction.replace("'", apostrophe)
        result = result.replace("’", apostrophe)
        result = result.replace("`", apostrophe)
        return result

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
        )

    def generate_dash_test(self, dash_type: str | None = None) -> TestCase:
        """Generate test case with dash variants.

        All dash variants should normalize to em dash (—) in the output.
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
        )

    def generate_batch(
        self, total: int = 1000, distribution: dict[str, int] | None = None
    ) -> list[TestCase]:
        if distribution is None:
            # Default proportions (percentages)
            default_proportions = {
                "apostrophe_variants": 0.20,  # 20%
                "quote_combinations": 0.15,  # 15%
                "punctuation_detection": 0.10,  # 10%
                "quotes_and_contractions": 0.15,  # 15%
                "nested_quotes": 0.05,  # 5%
                "punctuation_adjacent_quotes": 0.05,  # 5%
                "dash_variants": 0.15,  # 15%
                "complex_mixed": 0.15,  # 15%
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

        self.rng.shuffle(test_cases)
        return test_cases[:total]


if __name__ == "__main__":
    import time
    from collections import Counter

    # Import G2P to show expected phonemes
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
    gen = SentenceGenerator(seed=seed)

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
        ("complex_mixed", gen.generate_complex_mixed_test()),
    ]

    for i, (category, test_case) in enumerate(samples, 1):
        print(f"{i}. {category}")
        print(f"   Text: {test_case.text}")

        # Show expected phonemes if G2P available
        if has_g2p:
            tokens = g2p(test_case.text)
            phonemes = " ".join(t.phonemes for t in tokens if t.phonemes)
            print(f"   Expected phonemes: {phonemes}")

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
        print()

    print("\nGenerating batch of 100 test cases...")
    batch = gen.generate_batch(100)
    print(f"Generated {len(batch)} test cases")

    dist = Counter(t.category for t in batch)
    print("\nCategory distribution:")
    for category, count in sorted(dist.items()):
        print(f"  {category}: {count}")
