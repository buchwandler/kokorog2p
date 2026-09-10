"""Validated committed reference golden loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import load_corpus
from .registry import get_reference_golden_path, get_reference_metadata
from .types import (
    Corpus,
    CorpusCase,
    EncodingAnalysis,
    ErrorInfo,
    ReferenceMetadata,
    ReferenceOutput,
)

KNOWN_GOLDEN_SCHEMAS = {1, 2}


@dataclass(frozen=True)
class GoldenReference:
    metadata: ReferenceMetadata
    corpus: Corpus
    outputs: tuple[ReferenceOutput, ...]
    schema_version: int


def _encoding(payload: dict[str, Any] | None) -> EncodingAnalysis | None:
    if payload is None:
        return None
    return EncodingAnalysis(
        valid=bool(payload["valid"]),
        invalid_symbols=tuple(payload.get("invalid_symbols", ())),
        token_ids=tuple(payload.get("token_ids", ())),
        decoded=str(payload.get("decoded", "")),
        encoding_loss=bool(payload["encoding_loss"]),
    )


def _metadata(payload: dict[str, Any]) -> ReferenceMetadata:
    try:
        return ReferenceMetadata(
            provider_id=str(payload["provider_id"]),
            repository=str(payload["repository"]),
            commit=str(payload["commit"]),
            package_version=str(payload["package_version"]),
            frontend=str(payload["frontend"]),
            configuration=payload.get("configuration", {}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid golden reference metadata: {exc}") from exc


def _output(payload: dict[str, Any]) -> ReferenceOutput:
    error_payload = payload.get("error")
    error = None
    if error_payload is not None:
        error = ErrorInfo(
            str(error_payload["type"]),
            str(error_payload["message"]),
            error_payload.get("phase"),
        )
    return ReferenceOutput(
        case_id=str(payload["case_id"]),
        input_text=str(payload["input_text"]),
        normalized_text=payload.get("normalized_text"),
        phonemes=str(payload.get("phonemes", "")),
        error=error,
        encoding=_encoding(payload.get("encoding")),
    )


def _expected_corpus(reference_id: str) -> Corpus:
    aliases = {
        "hexgrad-en-us-v1": "en-us",
        "hexgrad-en-gb-v1": "en-gb",
        "semidark-de-v1": "de",
    }
    try:
        return load_corpus(aliases[reference_id])
    except KeyError as exc:
        raise ValueError(f"no corpus mapping for reference {reference_id}") from exc


def validate_reference_golden(
    payload: dict[str, Any], reference_id: str
) -> GoldenReference:
    """Validate complete golden identity before any case filtering is applied."""
    try:
        schema_version = int(payload["schema_version"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("golden has no valid schema_version") from exc
    if schema_version not in KNOWN_GOLDEN_SCHEMAS:
        raise ValueError(f"unsupported reference golden schema: {schema_version}")

    expected_metadata = get_reference_metadata(reference_id)
    metadata = _metadata(payload.get("reference", {}))
    if metadata.to_dict() != expected_metadata.to_dict():
        raise ValueError(
            f"golden metadata does not match pinned reference {reference_id}"
        )

    expected_corpus = _expected_corpus(reference_id)
    corpus_payload = payload.get("corpus", {})
    corpus_cases = corpus_payload.get("cases", [])
    try:
        corpus = Corpus(
            id=str(corpus_payload["id"]),
            cases=tuple(
                CorpusCase(
                    id=str(item["id"]),
                    text=str(item["text"]),
                    policy=item.get("policy", "diagnostic"),
                    tags=tuple(item.get("tags", ())),
                )
                for item in corpus_cases
            ),
            revision=str(corpus_payload.get("revision", "1")),
            generated=bool(corpus_payload.get("generated", False)),
            metadata=corpus_payload.get("metadata", {}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid golden corpus: {exc}") from exc
    if corpus.to_dict() != expected_corpus.to_dict():
        raise ValueError(f"golden corpus identity does not match {reference_id}")

    try:
        outputs = tuple(_output(item) for item in payload["cases"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid golden cases: {exc}") from exc
    output_ids = [output.case_id for output in outputs]
    if len(output_ids) != len(set(output_ids)):
        raise ValueError("golden case IDs must be unique")
    expected_ids = {case.id for case in expected_corpus.cases}
    if set(output_ids) != expected_ids:
        raise ValueError(
            f"golden case IDs do not match corpus: "
            f"missing={sorted(expected_ids - set(output_ids))}, "
            f"extra={sorted(set(output_ids) - expected_ids)}"
        )
    expected_inputs = {case.id: case.text for case in expected_corpus.cases}
    for output in outputs:
        if output.input_text != expected_inputs[output.case_id]:
            raise ValueError(f"golden input differs for case {output.case_id}")
        if output.error is not None:
            raise ValueError(
                f"golden contains reference error for case {output.case_id}"
            )
    return GoldenReference(metadata, expected_corpus, outputs, schema_version)


def load_reference_golden(
    reference_id: str, path: str | Path | None = None
) -> GoldenReference:
    golden_path = (
        Path(path) if path is not None else get_reference_golden_path(reference_id)
    )
    try:
        payload = json.loads(golden_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read reference golden {golden_path}: {exc}") from exc
    return validate_reference_golden(payload, reference_id)


def select_reference_outputs(
    golden: GoldenReference, case_ids: set[str] | None = None
) -> tuple[ReferenceOutput, ...]:
    if case_ids is None:
        return golden.outputs
    return tuple(output for output in golden.outputs if output.case_id in case_ids)
