from pathlib import Path


def test_russian_runtime_has_no_removed_special_imports() -> None:
    root = Path(__file__).parents[1] / "kokorog2p" / "ru"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "ruaccent" not in source
    assert "RussianEspeak" not in source
