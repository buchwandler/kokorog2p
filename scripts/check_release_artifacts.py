"""Check distribution contents and runtime resources for release gates."""

from __future__ import annotations

import argparse
import zipfile
from email.parser import Parser
from pathlib import Path

REQUIRED_WHEEL_FILES = {
    "kokorog2p/data/kokoro_config.json",
    "kokorog2p/data/kokoro_config_v1.1_de.json",
    "kokorog2p/data/kokoro_config_v1.1_zh.json",
    "kokorog2p/en/data/us_gold.json",
    "kokorog2p/en/data/gb_gold.json",
    "kokorog2p/de/data/de_gold.json",
    "kokorog2p/fr/data/fr_gold.json",
    "kokorog2p/ja/data/ja_words.txt",
    "kokorog2p/ko/data/table.csv",
}


def check_wheel(path: Path, *, require_release_version: bool) -> None:
    """Fail if a wheel omits a runtime resource family."""
    with zipfile.ZipFile(path) as wheel:
        members = set(wheel.namelist())
        metadata_name = next(
            name for name in members if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode("utf-8"))
    missing = sorted(REQUIRED_WHEEL_FILES - members)
    if missing:
        raise SystemExit(f"{path}: missing wheel resources: {', '.join(missing)}")
    if require_release_version and metadata.get("Version") == "0.0.0":
        raise SystemExit(f"{path}: release artifacts must not use version 0.0.0")


def check_installed(*, require_release_version: bool) -> None:
    """Load bundled resources and native rule-based language smoke paths."""
    import kokorog2p
    from kokorog2p import get_g2p
    from kokorog2p.data import (
        load_kokoro_config,
        load_kokoro_v11_de_config,
        load_kokoro_v11_zh_config,
    )
    from kokorog2p.de.lexicon import GermanLexicon
    from kokorog2p.en.lexicon import Lexicon
    from kokorog2p.fr.lexicon import FrenchLexicon

    if require_release_version and kokorog2p.__version__ == "0.0.0":
        raise SystemExit("release artifacts must not use version 0.0.0")

    assert load_kokoro_config()["vocab"]
    assert load_kokoro_v11_de_config()["vocab"]
    assert load_kokoro_v11_zh_config()["vocab"]
    assert len(Lexicon(british=False).golds) > 0
    assert len(GermanLexicon()) > 0
    assert len(FrenchLexicon().golds) > 0

    for language, text in (("es", "Hola"), ("it", "Ciao"), ("pt", "Olá")):
        g2p = get_g2p(
            language,
            use_spacy=False,
            use_espeak_fallback=False,
            use_goruut_fallback=False,
            load_gold=False,
            load_silver=False,
        )
        assert g2p(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="wheel to inspect")
    parser.add_argument(
        "--release",
        action="store_true",
        help="reject version 0.0.0 in the installed package",
    )
    args = parser.parse_args()

    if args.wheel:
        check_wheel(args.wheel, require_release_version=args.release)
    check_installed(require_release_version=args.release)


if __name__ == "__main__":
    main()
