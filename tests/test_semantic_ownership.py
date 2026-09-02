from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1] / "kokorog2p"


def test_kokorog2p_has_no_direct_semantic_backend_imports() -> None:
    prohibited = (
        "from abbr2words",
        "import abbr2words",
        "from cn2an",
        "from num2words",
        "import num2words",
        "from spokenform",
        "import spokenform",
        "prepare_for_kokorog2p",
        "preprocess_multilang",
    )
    offenders = []
    for path in ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in prohibited):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
