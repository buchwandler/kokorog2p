from kokorog2p.en.subtokens import split_english_lexical_token


def test_split_camel_case_and_acronym_boundaries() -> None:
    assert [item.text for item in split_english_lexical_token("CamelCase")] == [
        "Camel",
        "Case",
    ]
    assert [item.text for item in split_english_lexical_token("ABCWord")] == [
        "ABC",
        "Word",
    ]
    assert [item.text for item in split_english_lexical_token("wordABC")] == [
        "word",
        "ABC",
    ]


def test_split_delimiters_and_letter_digit_boundaries() -> None:
    assert [item.text for item in split_english_lexical_token("GitHub-style")] == [
        "Git",
        "Hub",
        "style",
    ]
    actual = [item.text for item in split_english_lexical_token("mixed_letter9_groups")]
    assert actual == [
        "mixed",
        "letter",
        "9",
        "groups",
    ]


def test_subtoken_offsets_are_source_offsets() -> None:
    subtokens = split_english_lexical_token("A-B")
    assert [(item.text, item.start, item.end) for item in subtokens] == [
        ("A", 0, 1),
        ("B", 2, 3),
    ]
