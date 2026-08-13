"""Regression tests for the released semantic-migration dependency floors."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib


def test_migrated_semantic_dependency_floors() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]

    # abbr2words 0.2.7 is the lexical/initialism baseline consumed by
    # Spokenform 0.2.5. Spokenform 0.2.5 is the semantic baseline for the
    # PolyNorm/Proteno-informed structured adapter contract used downstream.
    assert "abbr2words>=0.2.7,<0.3.0" in dependencies
    assert "spokenform>=0.2.5,<0.3.0" in dependencies
