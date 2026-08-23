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
