"""Guard the direct eSpeak ownership boundary."""

from __future__ import annotations

import ast
from pathlib import Path

ESPEAK_DIR = Path("kokorog2p/backends/espeak")
FORBIDDEN_MODULES = {"ctypes", "subprocess", "dlinfo", "espeakng_loader"}


def test_no_low_level_eSpeak_modules_or_imports_remain():
    assert not (ESPEAK_DIR / "api.py").exists()
    for path in ESPEAK_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".", 1)[0] for alias in node.names}
                assert not names & FORBIDDEN_MODULES, path
            elif isinstance(node, ast.ImportFrom):
                module_name = (node.module or "").split(".", 1)[0]
                assert module_name not in FORBIDDEN_MODULES, path


def test_runtime_is_the_only_direct_eSpeak_owner():
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in ESPEAK_DIR.glob("*.py")
    )
    assert "EspeakRuntime" in source
    assert "CDLL" not in source
    assert "espeak_Initialize" not in source
    assert "espeak_TextToPhonemes" not in source
