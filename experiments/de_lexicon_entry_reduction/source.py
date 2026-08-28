"""Adapters for canonical experiment sources."""

from __future__ import annotations

from pathlib import Path

from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon
from experiments.de_lexicon_compression.lexlab.sources import load_source


def load_canonical_source(
    source_id: str = "builtin",
    *,
    data_root: Path | None = None,
    path: Path | None = None,
) -> ParsedLexicon:
    """Load a source through the existing canonical parser and semantic model."""

    return load_source(source_id, data_root=data_root, path=path).runtime_unique()
