"""Release artifact policy tests."""

import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_release_artifacts import (
    check_sdist,
    check_wheel,
    required_wheel_files,
)


def _make_sdist(path: Path, members: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name in members:
            source = path.parent / name.replace("/", "_")
            source.write_text("fixture", encoding="utf-8")
            archive.add(source, arcname=f"kokorog2p-0.0.0/{name}")


def _make_wheel(path: Path, extra: list[str]) -> None:
    metadata_name = "kokorog2p-0.0.0.dist-info/METADATA"
    members = set(required_wheel_files()) | {metadata_name} | set(extra)
    with zipfile.ZipFile(path, "w") as archive:
        for name in members:
            content = (
                "Metadata-Version: 2.1\nRequires-Dist: lexphon>=0.1.0,<0.2\n"
                if name == metadata_name
                else "fixture"
            )
            archive.writestr(name, content)


def test_sdist_requires_notice_and_excludes_canonical_sources(tmp_path: Path) -> None:
    valid = tmp_path / "valid.tar.gz"
    _make_sdist(valid, ["kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md"])
    check_sdist(valid)

    invalid = tmp_path / "invalid.tar.gz"
    _make_sdist(
        invalid,
        [
            "kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md",
            "lexicons/sources/de/crane_wiktionary.tsv",
            "lexicons/sources/de/espeak_de.tsv",
            "lexicons/sources/de/olaph_de.txt",
        ],
    )
    with pytest.raises(SystemExit, match="canonical lexicon sources"):
        check_sdist(invalid)


def test_sdist_requires_third_party_notice(tmp_path: Path) -> None:
    path = tmp_path / "missing-notice.tar.gz"
    _make_sdist(path, ["README.md"])
    with pytest.raises(SystemExit, match="third-party notice"):
        check_sdist(path)


def test_wheel_rejects_migrated_german_payloads(tmp_path: Path) -> None:
    valid = tmp_path / "valid.whl"
    _make_wheel(valid, [])
    check_wheel(valid, require_release_version=False)

    invalid = tmp_path / "invalid.whl"
    _make_wheel(invalid, ["kokorog2p/lexicons/data/de_gold.g2lex"])
    with pytest.raises(SystemExit, match="migrated German assets"):
        check_wheel(invalid, require_release_version=False)


def test_release_artifacts_exclude_swedish_payloads(tmp_path: Path) -> None:
    wheel = tmp_path / "swedish.whl"
    _make_wheel(wheel, ["kokorog2p/lexicons/data/sv_nst.g2lex"])
    with pytest.raises(SystemExit, match="migrated Swedish assets"):
        check_wheel(wheel, require_release_version=False)

    sdist = tmp_path / "swedish.tar.gz"
    _make_sdist(
        sdist,
        [
            "kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md",
            "kokorog2p/lexicons/data/sv_nst.g2lex",
        ],
    )
    with pytest.raises(SystemExit, match="migrated Swedish data"):
        check_sdist(sdist)
