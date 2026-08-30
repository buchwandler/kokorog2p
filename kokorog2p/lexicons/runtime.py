"""Lazy, resource-owned runtime access to packaged G2Lex assets."""

from __future__ import annotations

import weakref
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Any

import g2lex

_SUPPORTED_ENCODINGS = frozenset({"kokoro-v1", "ipa", "none"})
from .registry import LexiconSpec, get_lexicon_spec, normalize_language


@dataclass(frozen=True, slots=True)
class LexiconHit:
    """A selected value plus the metadata needed by its consumer."""

    value: object
    name: str
    rating: int | None
    kind: str
    phoneme_encoding: str
    lexicon_id: str
    metadata: Mapping[str, object]


def _close_handles(handles: tuple[Any, ...]) -> None:
    for handle in handles:
        handle.close()


class SelectedLexicons:
    """An ordered collection of lazy G2Lex mappings with source identity."""

    def __init__(self, language: str, names: Sequence[str]) -> None:
        self.language = normalize_language(language)
        self.names = tuple(names)
        self._specs: tuple[LexiconSpec, ...] = tuple(
            get_lexicon_spec(self.language, name) for name in self.names
        )
        self._layers: dict[str, Mapping[str, object]] = {}
        layer_records: list[g2lex.LexiconLayer] = []
        handles: list[Any] = []
        try:
            data = files("kokorog2p.lexicons.data")
            for spec in self._specs:
                if spec.phoneme_encoding not in _SUPPORTED_ENCODINGS:
                    raise ValueError(
                        "No runtime decoder registered for "
                        f"encoding {spec.phoneme_encoding!r} "
                        f"({spec.id})"
                    )
                handle = g2lex.open_traversable(data.joinpath(spec.resource))
                handles.append(handle)
                mapping: Mapping[str, object] = (
                    g2lex.CaseAliasMapping(handle) if spec.case_aliases else handle
                )
                self._layers[spec.name] = mapping
                layer_records.append(
                    g2lex.LexiconLayer(
                        spec.name,
                        mapping,
                        {
                            **dict(spec.metadata),
                            "id": spec.id,
                            "rating": spec.rating,
                            "kind": spec.kind,
                            "phoneme_encoding": spec.phoneme_encoding,
                        },
                    )
                )
        except Exception:
            _close_handles(tuple(handles))
            raise
        self._handles = tuple(handles)
        self._layered = g2lex.LayeredLexicon(layer_records)
        self._closed = False
        self._finalizer = weakref.finalize(self, _close_handles, self._handles)

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("selected lexicons are closed")

    def get_hit(self, word: str) -> LexiconHit | None:
        """Return the first matching value according to configured precedence."""
        self._ensure_open()
        hit = self._layered.get_hit(word)
        if hit is None:
            return None
        metadata = dict(hit.metadata)
        spec = self._specs[hit.index]
        return LexiconHit(
            hit.value,
            hit.name,
            spec.rating,
            spec.kind,
            spec.phoneme_encoding,
            spec.id,
            metadata,
        )

    def get_hit_candidates(self, words: Sequence[str]) -> LexiconHit | None:
        """Search selected layers first, then candidate spellings upstream."""
        self._ensure_open()
        hit = self._layered.get_hit_candidates(words)
        if hit is None:
            return None
        metadata = dict(hit.metadata)
        spec = self._specs[hit.index]
        return LexiconHit(
            hit.value,
            hit.name,
            spec.rating,
            spec.kind,
            spec.phoneme_encoding,
            spec.id,
            metadata,
        )

    def layer(self, name: str) -> Mapping[str, object] | None:
        """Return one selected lazy mapping, or ``None`` when not selected."""
        self._ensure_open()
        return self._layers.get(name)

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and self.get_hit(word) is not None

    def __len__(self) -> int:
        self._ensure_open()
        return len(self._layered)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._layered.close()
        self._layers.clear()
        self._finalizer.detach()

    def __enter__(self) -> SelectedLexicons:  # noqa: PYI034
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def open_selected(language: str, names: Sequence[str]) -> SelectedLexicons:
    """Open the named registry layers in exactly the supplied order."""
    return SelectedLexicons(language, names)


def _consumer_decode_parity(
    layer: Mapping[str, object],
    *,
    language: str,
    phoneme_encoding: str,
) -> dict[str, Any]:
    """Validate packaged values through the registered consumer decoder."""
    result: dict[str, Any] = {
        "decoded_entries": 0,
        "invalid_first_pronunciations": 0,
        "empty_first_pronunciations": 0,
        "unsupported_source_sequences": {},
        "target_vocabulary_violations": 0,
        "ok": True,
        "errors": [],
    }
    if phoneme_encoding != "ipa" or normalize_language(language) != "de-de":
        return result
    from kokorog2p.de.g2p import normalize_internal
    from kokorog2p.vocab import get_vocab

    target = set(get_vocab())
    unsupported: dict[str, int] = {}
    errors: list[str] = []
    for word, value in layer.items():
        variants = tuple(g2lex.pronunciation_variants(value))
        if not variants:
            result["empty_first_pronunciations"] += 1
            errors.append(f"{word}: no pronunciation variants")
            continue
        result["decoded_entries"] += 1
        first = normalize_internal(
            str(variants[0]), vocabulary=target, use_tie_replacement=True
        )
        if first.unsupported:
            result["invalid_first_pronunciations"] += 1
            for sequence in first.unsupported:
                unsupported[sequence] = unsupported.get(sequence, 0) + 1
        if not first.value:
            result["empty_first_pronunciations"] += 1
        if not first.valid:
            errors.append(f"{word}: invalid first pronunciation")
        if any(char not in target for char in first.value):
            result["target_vocabulary_violations"] += 1
    result["unsupported_source_sequences"] = dict(sorted(unsupported.items()))
    result["errors"] = errors[:20]
    result["ok"] = not (
        result["invalid_first_pronunciations"]
        or result["empty_first_pronunciations"]
        or result["target_vocabulary_violations"]
    )
    return result


def validate_runtime_parity(
    records: list[dict[str, Any]], root: Path
) -> list[dict[str, Any]]:
    """Report exact storage parity and complete consumer decoding parity."""
    results: list[dict[str, Any]] = []
    for record in records:
        identifier = str(record["id"])
        source = root / str(record["source"])
        parsed = g2lex.read_typed_lexicon(
            source, format=str(record["source_format"]), source_id=identifier
        )
        selected = open_selected(str(record["language"]), (str(record["name"]),))
        missing = mismatches = 0
        consumer: dict[str, Any] = {"ok": True, "skipped": True}
        try:
            layer = selected.layer(str(record["name"]))
            for word, expected in parsed.entries.items():
                actual = layer.get(word) if layer is not None else None
                if actual is None and expected is not None:
                    missing += 1
                elif actual != expected:
                    mismatches += 1
            if layer is not None:
                consumer = _consumer_decode_parity(
                    layer,
                    language=str(record["language"]),
                    phoneme_encoding=str(record["phoneme_encoding"]),
                )
        finally:
            selected.close()
        storage_ok = not (missing or mismatches)
        errors = [] if storage_ok else [f"missing={missing} mismatches={mismatches}"]
        if not consumer.get("ok", True):
            errors.extend(str(error) for error in consumer.get("errors", ()))
        results.append(
            {
                "id": identifier,
                "missing_keys": missing,
                "unexpected_semantic_hits": 0,
                "value_mismatches": mismatches,
                "storage_parity": "exact" if storage_ok else "failed",
                "consumer_parity": consumer,
                "ok": storage_ok and bool(consumer.get("ok", True)),
                "errors": errors,
            }
        )
    return results


__all__ = [
    "LexiconHit",
    "SelectedLexicons",
    "open_selected",
]
