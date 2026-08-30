"""Release artifact policy tests."""

import tarfile
from pathlib import Path

import pytest

from scripts.check_release_artifacts import check_sdist


def _make_sdist(path: Path, members: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name in members:
            source = path.parent / name.replace("/", "_")
            source.write_text("fixture", encoding="utf-8")
            archive.add(source, arcname=f"kokorog2p-0.0.0/{name}")


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
        ],
    )
    with pytest.raises(SystemExit, match="canonical lexicon sources"):
        check_sdist(invalid)


def test_sdist_requires_third_party_notice(tmp_path: Path) -> None:
    path = tmp_path / "missing-notice.tar.gz"
    _make_sdist(path, ["README.md"])
    with pytest.raises(SystemExit, match="third-party notice"):
        check_sdist(path)
