from pathlib import Path

EXAMPLES = Path(__file__).parents[1] / "examples"
PROHIBITED_EXAMPLE_MARKERS = (
    "preprocess_multilang",
    ".add_abbreviation(",
    ".remove_abbreviation(",
    ".has_abbreviation(",
    ".list_abbreviations(",
    "reset_abbreviations",
    "expand_nums",
    "expand_abbreviations",
    "enable_context_detection",
    "input_mode=",
    "migrated_semantics",
)


def test_executable_examples_use_the_v09_contract() -> None:
    offenders = []
    for path in sorted(EXAMPLES.glob("**/*.py")):
        text = path.read_text(encoding="utf-8")
        for marker in PROHIBITED_EXAMPLE_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(EXAMPLES)}: {marker}")
    assert offenders == []


def test_examples_are_python_files() -> None:
    assert list(EXAMPLES.glob("**/*.py"))
