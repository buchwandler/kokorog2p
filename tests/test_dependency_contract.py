"""Regression tests for the released semantic-migration dependency floors."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


def test_migrated_semantic_dependency_floors() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]

    # Spokenform owns written-to-spoken semantics and abbreviation integration.
    # abbr2words may be transitive through Spokenform, but is not a direct
    # kokorog2p runtime dependency. G2Lex is the direct lexicon runtime.
    assert "spokenform>=0.3.4,<0.4.0" in dependencies
    assert "g2lex>=0.1.7,<0.2.0" in dependencies
    assert not any(dependency.startswith("abbr2words") for dependency in dependencies)


def test_thai_dependency_extra_is_optional() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]

    assert extras["th"] == [
        "tltk>=1.10,<2",
        "pythainlp>=5.3,<6",
        "kokorog2p[espeak]",
    ]
    assert "th" in extras["all"][-1]


def test_japanese_dependency_extras_are_separated() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]

    assert extras["ja"] == ["pyopenjtalk>=0.4.1,<0.5"]
    assert "fugashi>=1.3.0" not in extras["ja"]
    assert "unidic-lite>=1.0.8" in extras["ja-cutlet"]
    assert "unidic>=1.1.0" in extras["ja-cutlet-full"]
    assert "unidic-lite>=1.0.8" not in extras["ja-cutlet-full"]


def test_korean_dependency_extras_use_korean_backends() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]

    assert "jamo>=0.4.1" in extras["ko"]
    assert "nltk>=3.8.1" in extras["ko"]
    assert "mecab-python3" not in extras["ko"]
    assert "python-mecab-ko>=1.3.7,<2" in extras["ko-mecab"]
    assert "mecab-python3" not in extras["ko-mecab"]
