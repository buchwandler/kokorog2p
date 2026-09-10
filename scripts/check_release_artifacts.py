"""Check distribution contents and unrelated runtime release gates."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

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
FORBIDDEN_PACKAGE_PREFIXES = ("kokorog2p/lexicons/data/", "lexicons/")


def _normalize_sdist_member(member: str) -> str:
    """Remove an sdist root prefix before checking package-relative paths."""
    for marker in ("kokorog2p/", "lexicons/"):
        index = member.find(marker)
        if index >= 0:
            return member[index:]
    return member


def _forbidden_source_members(members: set[str]) -> list[str]:
    return sorted(
        member
        for member in members
        if any(member.startswith(root) for root in LEGACY_SOURCE_ROOTS)
        and Path(member).suffix in {".json", ".txt", ".dict"}
    )


def _forbidden_lexicon_members(members: set[str]) -> list[str]:
    return sorted(
        member
        for member in members
        if any(member.startswith(prefix) for prefix in FORBIDDEN_PACKAGE_PREFIXES)
    )


def check_wheel(path: Path, *, require_release_version: bool) -> None:
    """Check required package files and reject migrated lexicon payloads."""
    with zipfile.ZipFile(path) as wheel:
        members = set(wheel.namelist())
        metadata_name = next(
            name for name in members if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(wheel.read(metadata_name).decode("utf-8"))

    missing = sorted(STATIC_REQUIRED_WHEEL_FILES - members)
    if missing:
        raise SystemExit(f"{path}: missing required files: {', '.join(missing)}")
    forbidden = _forbidden_lexicon_members(members)
    if forbidden:
        raise SystemExit(
            f"{path}: migrated lexicon payloads are forbidden: {', '.join(forbidden)}"
        )
    requires_dist = tuple(metadata.get_all("Requires-Dist") or ())
    if not any(
        requirement.lower().startswith("lexphon") for requirement in requires_dist
    ):
        raise SystemExit(f"{path}: Lexphon runtime dependency is missing")
    source_payloads = _forbidden_source_members(members)
    if source_payloads:
        raise SystemExit(
            f"{path}: forbidden source resources: {', '.join(source_payloads)}"
        )
    if require_release_version and metadata.get("Version") == "0.0.0":
        raise SystemExit(f"{path}: release artifacts must not use version 0.0.0")


def check_sdist(path: Path, *, require_release_version: bool = False) -> None:
    """Reject migrated lexicon payloads from a source distribution."""
    with tarfile.open(path, "r:gz") as sdist:
        members = {
            _normalize_sdist_member(member.name) for member in sdist.getmembers()
        }
    source_payloads = _forbidden_source_members(members)
    if source_payloads:
        raise SystemExit(
            f"{path}: forbidden source resources: {', '.join(source_payloads)}"
        )

    forbidden = _forbidden_lexicon_members(members)
    if forbidden:
        raise SystemExit(
            f"{path}: migrated lexicon payloads are forbidden: {', '.join(forbidden)}"
        )
    if require_release_version and not any(
        member.endswith("/PKG-INFO") for member in members
    ):
        raise SystemExit(f"{path}: source distribution metadata is missing")


def check_installed(*, require_release_version: bool) -> None:
    """Check package configuration and a no-data runtime path."""
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
    assert available_lexicons("en") == ("gold",)

    g2p = get_g2p(
        "en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    try:
        assert g2p("unlistedword")
    finally:
        g2p.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, help="wheel to inspect")
    parser.add_argument("--sdist", type=Path, help="source distribution to inspect")
    parser.add_argument("--release", action="store_true", help="reject version 0.0.0")
    args = parser.parse_args()
    if args.wheel:
        check_wheel(args.wheel, require_release_version=args.release)
    if args.sdist:
        check_sdist(args.sdist, require_release_version=args.release)
    check_installed(require_release_version=args.release)


if __name__ == "__main__":
    main()
