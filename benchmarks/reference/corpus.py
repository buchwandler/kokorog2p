"""Reviewed and generated reference benchmark corpora."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import Corpus, CorpusCase

DATA_DIR = Path(__file__).with_name("data")


def _corpus_path(name: str) -> Path:
    aliases = {
        "reviewed": "en_us_v1.json",
        "en-us": "en_us_v1.json",
        "en-gb": "en_gb_v1.json",
        "de": "de_semidark_v1.json",
        "german": "de_semidark_v1.json",
    }
    filename = aliases.get(name, name if name.endswith(".json") else f"{name}.json")
    path = DATA_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"unknown reference corpus: {name}")
    return path


def load_case_data(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_corpus(name: str) -> Corpus:
    payload = load_case_data(_corpus_path(name))
    cases = tuple(
        CorpusCase(
            id=item["id"],
            text=item["text"],
            policy=item.get("policy", "diagnostic"),
            tags=tuple(item.get("tags", ())),
        )
        for item in payload["cases"]
    )
    return Corpus(
        id=payload.get("id", Path(name).stem),
        cases=cases,
        revision=str(payload.get("revision", "1")),
        generated=bool(payload.get("generated", False)),
        metadata=payload.get("metadata", {}),
    )


def filter_cases(
    corpus: Corpus,
    *,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
    limit: int | None = None,
) -> Corpus:
    cases = [
        case
        for case in corpus.cases
        if (case_ids is None or case.id in case_ids)
        and (tags is None or tags.intersection(case.tags))
    ]
    if limit is not None:
        cases = cases[:limit]
    return Corpus(
        corpus.id, tuple(cases), corpus.revision, corpus.generated, corpus.metadata
    )
