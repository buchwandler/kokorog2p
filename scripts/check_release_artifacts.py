"""Check distribution contents and runtime resources for release gates."""

from __future__ import annotations

import argparse
import zipfile
from email.parser import Parser
from importlib.resources import files
from pathlib import Path

from kokorog2p.lexicons.registry import iter_lexicon_specs

STATIC_REQUIRED_WHEEL_FILES = {
    "kokorog2p/data/kokoro_config.json",
    "kokorog2p/data/kokoro_config_v1.1_de.json",
    "kokorog2p/data/kokoro_config_v1.1_zh.json",
    "kokorog2p/ko/data/table.csv",
}
LEGACY_SOURCE_ROOTS = (
    "kokorog2p/de/data/",
    "kokorog2p/en/data/",
    "kokorog2p/fr/data/",
    "kokorog2p/ja/data/",
)


def required_wheel_files() -> set[str]:
    return STATIC_REQUIRED_WHEEL_FILES | {
        f"kokorog2p/lexicons/data/{spec.resource}" for spec in iter_lexicon_specs()
    }


def asset_names() -> tuple[str, ...]:
    return tuple(spec.resource for spec in iter_lexicon_specs())


def check_wheel(path: Path, *, require_release_version: bool) -> None:
    """Fail if a wheel omits required resources or ships canonical sources."""
    with zipfile.ZipFile(path) as wheel:
        members = set(wheel.namelist())
        metadata_name = next(
            name for name in members if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode("utf-8"))
    required = required_wheel_files()
    missing = sorted(required - members)
    forbidden = sorted(
        member
        for member in members
        if any(member.startswith(root) for root in LEGACY_SOURCE_ROOTS)
        and Path(member).suffix in {".json", ".txt", ".dict"}
    )
    unknown_assets = sorted(
        member
        for member in members
        if member.startswith("kokorog2p/lexicons/data/")
        and member.endswith(".g2lex")
        and member not in required
    )
    if missing:
        raise SystemExit(f"{path}: missing wheel resources: {', '.join(missing)}")
    if forbidden:
        raise SystemExit(f"{path}: forbidden source resources: {', '.join(forbidden)}")
    if unknown_assets:
        raise SystemExit(f"{path}: unknown lexicon assets: {', '.join(unknown_assets)}")
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

    for asset_name in asset_names():
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
