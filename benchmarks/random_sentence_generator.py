#!/usr/bin/env python3
"""Random sentence generator for English synthetic test cases.

Generates test sentences covering:
- Quotes, contractions, and punctuation
- Abbreviations (titles, places, dates, measurements)
- Numbers (cardinals, ordinals, decimals, fractions)
"""

import json
import random
import string
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_WORDS_PATH = Path(__file__).parent / "data" / "en_us_words.json"


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
        language: str = "en",
        g2p: Callable[[str], list[Any]] | None = None,
        words_path: str | Path | None = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.language = language
        self.g2p = g2p
        self.words_path = self._resolve_words_path(language, words_path)
        self.words_data = self._load_words_data(self.words_path)

    @staticmethod
    def _resolve_words_path(language: str, words_path: str | Path | None) -> Path:
        if words_path:
            return Path(words_path)
        normalized = (language or "en").lower()
        if normalized in {"en", "en-us", "en_us"}:
            base = "en_us"
        elif normalized in {"en-gb", "en_gb"}:
            base = "en_gb"
        else:
            base = normalized.split("-")[0]
        candidate = Path(__file__).parent / "data" / f"{base}_words.json"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(
            f"No words file for language '{language}' at {candidate}"
        )

    def _load_words_data(self, words_path: Path) -> dict[str, Any]:
        with open(words_path, encoding="utf-8") as handle:
            data = json.load(handle)
        self._validate_words_data(data, words_path)
        return data

    @staticmethod
    def _validate_words_data(data: dict[str, Any], words_path: Path) -> None:
        required_lists = [
            "templates",
            "subjects_base",
            "subjects_3s",
            "verbs_base",
            "verbs_3s",
            "objects",
            "places",
            "times",
            "adverbs",
            "aux_base",
            "base_words",
            "punctuation",
            "contractions",
            "informal_contractions",
        ]
        required_dicts = [
            "apostrophes",
            "quote_pairs",
            "punctuation_variants",
            "dash_variants",
            "abbreviations",
            "number_formats",
        ]
        missing_lists = [
            key
            for key in required_lists
            if key not in data or not isinstance(data[key], list) or not data[key]
        ]
        missing_dicts = [
            key
            for key in required_dicts
            if key not in data or not isinstance(data[key], dict) or not data[key]
        ]
        if missing_lists or missing_dicts:
            missing = missing_lists + missing_dicts
            missing_list = ", ".join(missing)
            raise ValueError(f"Missing or empty keys in {words_path}: {missing_list}")

        formatter = string.Formatter()
        template_fields: set[str] = set()
        for template in data.get("templates", []):
            if not isinstance(template, str):
                raise ValueError(f"Invalid template in {words_path}: {template}")
            for _, field_name, _, _ in formatter.parse(template):
                if field_name:
                    template_fields.add(field_name)

        missing_template_fields = [
            field
            for field in template_fields
            if field not in data or not isinstance(data[field], list) or not data[field]
        ]
        if missing_template_fields:
            missing_list = ", ".join(missing_template_fields)
            raise ValueError(
                f"Missing or empty template fields in {words_path}: {missing_list}"
            )

    def _get_list(self, key: str) -> list[Any]:
        value = self.words_data.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"Missing or empty '{key}' in {self.words_path}")
        return value

    def _get_dict(self, key: str) -> dict[str, Any]:
        value = self.words_data.get(key)
        if not isinstance(value, dict) or not value:
            raise ValueError(f"Missing or empty '{key}' in {self.words_path}")
        return value

    def _choose_word(self, key: str) -> str:
        return self.rng.choice(self._get_list(key))

    def _render_template(self, template: str) -> str:
        formatter = string.Formatter()
        values: dict[str, str] = {}
        for _, field_name, _, _ in formatter.parse(template):
            if field_name and field_name not in values:
                values[field_name] = self._choose_word(field_name)
        return template.format_map(values)

    def _choose_end_punctuation(self) -> str:
        options = self.words_data.get("end_punctuation")
        if options:
            return self.rng.choice(options)
        return "."

    def _random_word(self) -> str:
        return self._choose_word("base_words")

    def _random_words(self, count: int) -> list[str]:
        return [self._random_word() for _ in range(count)]

    def generate_simple_sentence(self) -> TestCase:
        template = self._choose_word("templates")
        text = self._render_template(template).strip()
        if text and text[-1] not in ".!?":
            text = f"{text}{self._choose_end_punctuation()}"
        if text:
            text = text[0].upper() + text[1:]
        return TestCase(
            text=text,
            category="simple_sentences",
            params={"template": template},
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def _apply_apostrophe(self, contraction: str, apostrophe_type: str) -> str:
        apostrophes = self._get_dict("apostrophes")
        if apostrophe_type not in apostrophes:
            apostrophe_type = (
                "standard" if "standard" in apostrophes else next(iter(apostrophes))
            )
        apostrophe = apostrophes[apostrophe_type]
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
        contractions_list = self._get_list("contractions")
        informal_list = self._get_list("informal_contractions")
        all_contractions = contractions_list + informal_list
        contractions = self.rng.sample(
            all_contractions, min(num_contractions, len(all_contractions))
        )
        contractions = [
            self._apply_apostrophe(c, apostrophe_type) for c in contractions
        ]
        apostrophes = self._get_dict("apostrophes")
        if apostrophe_type not in apostrophes:
            apostrophe_type = (
                "standard" if "standard" in apostrophes else next(iter(apostrophes))
            )

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
                "apostrophe_char": apostrophes[apostrophe_type],
            },
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_quote_test(self, quote_type: str = "ascii_double") -> TestCase:
        quote_pairs = self._get_dict("quote_pairs")
        if quote_type not in quote_pairs:
            quote_type = (
                "ascii_double"
                if "ascii_double" in quote_pairs
                else next(iter(quote_pairs))
            )
        left_quote, right_quote = quote_pairs[quote_type]
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
        punctuation = self._get_list("punctuation")
        punct_variants = self._get_dict("punctuation_variants")
        if punct_type is None:
            punct = self.rng.choice(punctuation)
            variant_name = "standard"
        elif punct_type in punct_variants:
            punct = punct_variants[punct_type]
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
        quote_pairs = self._get_dict("quote_pairs")
        quote_keys = list(quote_pairs.keys())
        outer_type = self.rng.choice(quote_keys)
        inner_type = self.rng.choice(quote_keys)
        outer_left, outer_right = quote_pairs[outer_type]
        inner_left, inner_right = quote_pairs[inner_type]
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
        quote_pairs = self._get_dict("quote_pairs")
        if quote_type not in quote_pairs:
            quote_type = (
                "ascii_double"
                if "ascii_double" in quote_pairs
                else next(iter(quote_pairs))
            )
        left_quote, right_quote = quote_pairs[quote_type]
        contractions_list = self._get_list("contractions")
        contraction = self.rng.choice(contractions_list)
        contraction = self._apply_apostrophe(contraction, apostrophe_type)
        words = self._random_words(self.rng.randint(1, 3))
        quoted = f"{contraction} {' '.join(words)}"
        intro = self.rng.choice(["She said", "He asked", "They replied"])
        text = f"{intro}, {left_quote}{quoted}{right_quote}."
        apostrophes = self._get_dict("apostrophes")
        if apostrophe_type not in apostrophes:
            apostrophe_type = (
                "standard" if "standard" in apostrophes else next(iter(apostrophes))
            )
        return TestCase(
            text=text,
            category="quotes_and_contractions",
            params={
                "apostrophe_type": apostrophe_type,
                "quote_type": quote_type,
                "apostrophe_char": apostrophes[apostrophe_type],
            },
            expected_phonemes=self._generate_expected_phonemes(text),
        )

    def generate_complex_mixed_test(self) -> TestCase:
        apostrophes = self._get_dict("apostrophes")
        quote_pairs = self._get_dict("quote_pairs")
        punctuation = self._get_list("punctuation")
        punct_variants = self._get_dict("punctuation_variants")
        contractions_list = self._get_list("contractions")

        apostrophe_type = self.rng.choice(list(apostrophes.keys()))
        quote_type = self.rng.choice(list(quote_pairs.keys()))
        punct = self.rng.choice(punctuation + list(punct_variants.values()))
        left_quote, right_quote = quote_pairs[quote_type]
        contraction1 = self._apply_apostrophe(
            self.rng.choice(contractions_list), apostrophe_type
        )
        contraction2 = self._apply_apostrophe(
            self.rng.choice(contractions_list),
            self.rng.choice(list(apostrophes.keys())),
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
        quote_pairs = self._get_dict("quote_pairs")
        punctuation = self._get_list("punctuation")
        punct_variants = self._get_dict("punctuation_variants")
        quote_type = self.rng.choice(list(quote_pairs.keys()))
        left_quote, right_quote = quote_pairs[quote_type]
        punct = self.rng.choice(punctuation + list(punct_variants.values()))
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
        dash_variants = self._get_dict("dash_variants")
        if dash_type is None:
            dash_type = self.rng.choice(list(dash_variants.keys()))
        elif dash_type not in dash_variants:
            dash_type = (
                "em_dash" if "em_dash" in dash_variants else next(iter(dash_variants))
            )

        dash = dash_variants[dash_type]
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
        abbreviations = self._get_dict("abbreviations")
        if abbrev_category is None or abbrev_category not in abbreviations:
            abbrev_category = self.rng.choice(list(abbreviations.keys()))

        abbrev = self.rng.choice(abbreviations[abbrev_category])
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
        number_formats = self._get_dict("number_formats")
        if number_format is None or number_format not in number_formats:
            number_format = self.rng.choice(list(number_formats.keys()))

        number: str | int = self.rng.choice(number_formats[number_format])
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
        abbreviations = self._get_dict("abbreviations")
        number_formats = self._get_dict("number_formats")

        abbrev_cat = self.rng.choice(list(abbreviations.keys()))
        abbrev = self.rng.choice(abbreviations[abbrev_cat])

        number_format = self.rng.choice(list(number_formats.keys()))
        number: str | int = self.rng.choice(number_formats[number_format])

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
        self,
        total: int = 1000,
        distribution: dict[str, int] | None = None,
        simple: bool = False,
    ) -> list[TestCase]:
        if simple:
            return [self.generate_simple_sentence() for _ in range(total)]
        if distribution is None:
            # Default proportions (percentages)
            default_proportions = {
                "simple_sentences": 0.05,  # 5%
                "apostrophe_variants": 0.13,  # 13%
                "quote_combinations": 0.10,  # 10%
                "punctuation_detection": 0.08,  # 8%
                "quotes_and_contractions": 0.10,  # 10%
                "nested_quotes": 0.04,  # 4%
                "punctuation_adjacent_quotes": 0.04,  # 4%
                "dash_variants": 0.10,  # 10%
                "complex_mixed": 0.10,  # 10%
                "abbreviations": 0.13,  # 13%
                "numbers": 0.09,  # 9%
                "mixed_abbrev_numbers": 0.04,  # 4%
            }
            # Scale proportions to actual counts
            distribution = {k: int(v * total) for k, v in default_proportions.items()}

        test_cases = []

        apostrophes = self._get_dict("apostrophes")
        quote_pairs = self._get_dict("quote_pairs")
        punctuation = self._get_list("punctuation")
        punct_variants = self._get_dict("punctuation_variants")
        dash_variants = self._get_dict("dash_variants")
        abbreviations = self._get_dict("abbreviations")
        number_formats = self._get_dict("number_formats")

        for _ in range(distribution.get("simple_sentences", 0)):
            test_cases.append(self.generate_simple_sentence())

        for _ in range(distribution.get("apostrophe_variants", 0)):
            apostrophe_type = self.rng.choice(list(apostrophes.keys()))
            num_contractions = self.rng.randint(1, 3)
            test_cases.append(
                self.generate_contraction_test(apostrophe_type, num_contractions)
            )

        for _ in range(distribution.get("quote_combinations", 0)):
            quote_type = self.rng.choice(list(quote_pairs.keys()))
            test_cases.append(self.generate_quote_test(quote_type))

        for _ in range(distribution.get("punctuation_detection", 0)):
            if self.rng.random() < 0.5:
                punct_type = self.rng.choice(list(punct_variants.keys()))
            else:
                punct_type = self.rng.choice(punctuation)
            test_cases.append(self.generate_punctuation_test(punct_type))

        for _ in range(distribution.get("quotes_and_contractions", 0)):
            apostrophe_type = self.rng.choice(list(apostrophes.keys()))
            quote_type = self.rng.choice(list(quote_pairs.keys()))
            test_cases.append(
                self.generate_quote_with_contraction_test(apostrophe_type, quote_type)
            )

        for _ in range(distribution.get("nested_quotes", 0)):
            test_cases.append(self.generate_nested_quote_test())

        for _ in range(distribution.get("punctuation_adjacent_quotes", 0)):
            test_cases.append(self.generate_punctuation_adjacent_quote_test())

        for _ in range(distribution.get("dash_variants", 0)):
            dash_type = self.rng.choice(list(dash_variants.keys()))
            test_cases.append(self.generate_dash_test(dash_type))

        for _ in range(distribution.get("complex_mixed", 0)):
            test_cases.append(self.generate_complex_mixed_test())

        for _ in range(distribution.get("abbreviations", 0)):
            abbrev_cat = self.rng.choice(list(abbreviations.keys()))
            test_cases.append(self.generate_abbreviation_test(abbrev_cat))

        for _ in range(distribution.get("numbers", 0)):
            number_format = self.rng.choice(list(number_formats.keys()))
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
