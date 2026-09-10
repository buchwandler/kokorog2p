"""Direct tests for wheel and source-distribution payload gates."""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.check_release_artifacts import check_sdist, check_wheel

WHEEL_MEMBERS = {
    "kokorog2p/data/kokoro_config.json",
    "kokorog2p/data/kokoro_config_v1.1_de.json",
    "kokorog2p/data/kokoro_config_v1.1_zh.json",
    "kokorog2p/ko/data/table.csv",
    "kokorog2p-0.9.4.dist-info/METADATA",
}


def _write_wheel(path: Path, extra: str | None = None) -> None:
    members = WHEEL_MEMBERS | ({extra} if extra else set())
    with zipfile.ZipFile(path, "w") as wheel:
        for member in members:
            content = (
                "Metadata-Version: 2.1\nName: kokorog2p\nVersion: 0.9.4\n"
                "Requires-Dist: lexphon>=0.2.2,<0.3\n"
                if member.endswith("METADATA")
                else "content"
            )
            wheel.writestr(member, content)


def _write_sdist(path: Path, member: str) -> None:
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(f"kokorog2p-0.9.4/{member}")
        payload = b"forbidden"
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def test_wheel_gate_rejects_forbidden_lexicon_payload(tmp_path: Path) -> None:
    wheel = tmp_path / "kokorog2p.whl"
    _write_wheel(wheel, "kokorog2p/lexicons/data/generated.g2lex")

    with pytest.raises(SystemExit, match="migrated lexicon payloads are forbidden"):
        check_wheel(wheel, require_release_version=True)


def test_sdist_gate_normalizes_prefixed_lexicon_root(tmp_path: Path) -> None:
    sdist = tmp_path / "kokorog2p.tar.gz"
    _write_sdist(sdist, "kokorog2p/lexicons/data/generated.g2lex")

    with pytest.raises(SystemExit, match="migrated lexicon payloads are forbidden"):
        check_sdist(sdist, require_release_version=True)
