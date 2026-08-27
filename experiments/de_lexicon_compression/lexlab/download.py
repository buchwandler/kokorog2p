"""Explicit, pinned source downloads."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

from .sources import SourceSpec

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "kokorog2p" / "experiments" / "de-lexicons"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_url(spec: SourceSpec) -> str:
    if not spec.revision or not spec.filename:
        raise ValueError(f"{spec.source_id} has no immutable download coordinates")
    return f"https://huggingface.co/{spec.values['repo_type']}s/{spec.values['repo_id']}/raw/{spec.revision}/{spec.filename}"


def destination(spec: SourceSpec, root: Path | None = None) -> Path:
    cache = root or DEFAULT_CACHE_DIR
    if not spec.filename:
        raise ValueError(f"{spec.source_id} has no filename")
    return cache / spec.source_id / (spec.revision or "unversioned") / spec.filename


def download_source(
    spec: SourceSpec, *, cache_dir: Path | None = None, force: bool = False
) -> Path:
    """Download one pinned file, verify it, and atomically install it."""
    target = destination(spec, cache_dir)
    expected = str(spec.values.get("sha256", ""))
    if target.is_file() and not force:
        if expected and sha256_file(target) != expected:
            raise ValueError(f"Checksum mismatch for cached {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        urllib.request.urlretrieve(source_url(spec), temporary)
        actual = sha256_file(temporary)
        if expected and actual != expected:
            raise ValueError(f"Checksum mismatch: expected {expected}, got {actual}")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
