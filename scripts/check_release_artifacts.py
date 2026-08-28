"""Check distribution contents and runtime resources for release gates."""

from __future__ import annotations

import argparse
import zipfile
from email.parser import Parser
from importlib.resources import files
from pathlib import Path

REQUIRED_WHEEL_FILES = {
    "kokorog2p/data/kokoro_config.json",
    "kokorog2p/data/kokoro_config_v1.1_de.json",
    "kokorog2p/data/kokoro_config_v1.1_zh.json",
    "kokorog2p/lexicons/data/en_us_gold.g2lex",
    "kokorog2p/lexicons/data/en_us_silver.g2lex",
    "kokorog2p/lexicons/data/en_gb_gold.g2lex",
    "kokorog2p/lexicons/data/en_gb_silver.g2lex",
    "kokorog2p/lexicons/data/de_gold.g2lex",
    "kokorog2p/lexicons/data/fr_gold.g2lex",
    "kokorog2p/lexicons/data/ja_words.g2lex",
    "kokorog2p/ko/data/table.csv",
}
FORBIDDEN_WHEEL_FILES = {
    "kokorog2p/de/data/de_gold.json",
    "kokorog2p/en/data/gb_gold.json",
    "kokorog2p/en/data/gb_silver.json",
    "kokorog2p/en/data/us_gold.json",
    "kokorog2p/en/data/us_silver.json",
    "kokorog2p/fr/data/fr_gold.json",
    "kokorog2p/ja/data/ja_words.txt",
}
ASSET_NAMES = tuple(
    path.split("/")[-1] for path in REQUIRED_WHEEL_FILES if path.endswith(".g2lex")
)


def check_wheel(path: Path, *, require_release_version: bool) -> None:
    """Fail if a wheel omits required resources or ships canonical sources."""
    with zipfile.ZipFile(path) as wheel:
        members = set(wheel.namelist())
        metadata_name = next(
            name for name in members if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode("utf-8"))
    missing = sorted(REQUIRED_WHEEL_FILES - members)
    forbidden = sorted(FORBIDDEN_WHEEL_FILES & members)
    if missing:
        raise SystemExit(f"{path}: missing wheel resources: {', '.join(missing)}")
    if forbidden:
        raise SystemExit(f"{path}: forbidden source resources: {', '.join(forbidden)}")
    if require_release_version and metadata.get("Version") == "0.0.0":
        raise SystemExit(f"{path}: release artifacts must not use version 0.0.0")


def check_installed(*, require_release_version: bool) -> None:
    """Load bundled assets and representative native language paths."""
    import g2lex

    import kokorog2p
    from kokorog2p import available_lexicons, get_g2p
    from kokorog2p.data import (
        load_kokoro_config,
        load_kokoro_v11_de_config,
        load_kokoro_v11_zh_config,
    )

    if require_release_version and kokorog2p.__version__ == "0.0.0":
        raise SystemExit("release artifacts must not use version 0.0.0")
    assert load_kokoro_config()["vocab"]
    assert load_kokoro_v11_de_config()["vocab"]
    assert load_kokoro_v11_zh_config()["vocab"]
    assert available_lexicons("en") == ("gold", "silver")

    for asset_name in ASSET_NAMES:
        resource = files("kokorog2p.lexicons.data").joinpath(asset_name)
        lexicon = g2lex.open_traversable(resource)
        try:
            assert len(lexicon) > 0
        finally:
            lexicon.close()

    options = {"use_spacy": False, "use_espeak_fallback": False}
    english_gold = get_g2p("en-us", lexicons="gold", **options)
    english_stack = get_g2p("en-us", lexicons=("gold", "silver"), **options)
    assert english_gold.lookup("hello")
    assert english_stack.lookup("hello")
    assert get_g2p("de", **options)("Haus")
    assert get_g2p("fr", **options)("Bonjour")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="wheel to inspect")
    parser.add_argument("--release", action="store_true", help="reject version 0.0.0")
    args = parser.parse_args()
    if args.wheel:
        check_wheel(args.wheel, require_release_version=args.release)
    check_installed(require_release_version=args.release)


if __name__ == "__main__":
    main()
