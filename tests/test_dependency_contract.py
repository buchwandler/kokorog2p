"""Regression tests for the released semantic-migration dependency floors."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


def test_migrated_semantic_dependency_floors() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]

    # abbr2words 0.2.9 is the lexical/initialism baseline consumed directly
    # by kokorog2p; Spokenform 0.3.1 is the released semantic adapter
    # baseline for the current migration.
    assert "abbr2words>=0.2.9,<0.3.0" in dependencies
    assert "spokenform>=0.3.1,<0.4.0" in dependencies


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
