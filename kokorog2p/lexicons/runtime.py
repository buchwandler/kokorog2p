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

from .registry import LexiconSpec, get_lexicon_spec, normalize_language


@dataclass(frozen=True, slots=True)
class LexiconHit:
    value: object
    name: str
    rating: int | None


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
        handles: list[Any] = []
        try:
            data = files("kokorog2p.lexicons.data")
            for spec in self._specs:
                handle = g2lex.open_traversable(data.joinpath(spec.resource))
                handles.append(handle)
                self._layers[spec.name] = (
                    g2lex.CaseAliasMapping(handle) if spec.case_aliases else handle
                )
        except Exception:
            _close_handles(tuple(handles))
            raise
        self._handles = tuple(handles)
        self._closed = False
        self._finalizer = weakref.finalize(self, _close_handles, self._handles)

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("selected lexicons are closed")

    def get_hit(self, word: str) -> LexiconHit | None:
        """Return the first matching value according to configured precedence."""
        self._ensure_open()
        missing = object()
        for spec in self._specs:
            value = self._layers[spec.name].get(word, missing)
            if value is not missing:
                return LexiconHit(value, spec.name, spec.rating)
        return None

    def layer(self, name: str) -> Mapping[str, object] | None:
        """Return one selected lazy mapping, or ``None`` when not selected."""
        self._ensure_open()
        return self._layers.get(name)

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and self.get_hit(word) is not None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._finalizer()
        self._finalizer.detach()
        self._layers.clear()

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


def validate_runtime_parity(
    records: list[dict[str, Any]], root: Path
) -> list[dict[str, Any]]:
    """Compare every canonical source entry through the packaged runtime layer."""
    results: list[dict[str, Any]] = []
    for record in records:
        identifier = str(record["id"])
        source = root / str(record["source"])
        parsed = g2lex.read_typed_lexicon(
            source, format=str(record["source_format"]), source_id=identifier
        )
        names = (str(record["name"]),)
        if record["language"].startswith("en-") and record["name"] == "gold":
            names = ("gold", "silver")
        selected = open_selected(str(record["language"]), names)
        missing = unexpected = mismatches = 0
        try:
            layer = selected.layer(str(record["name"]))
            for word, expected in parsed.entries.items():
                lookup_word = word.lower() if record["language"] == "de-de" else word
                actual = layer.get(lookup_word) if layer is not None else None
                if actual is None and expected is not None:
                    missing += 1
                elif actual != expected:
                    mismatches += 1
            if record["kind"] == "membership":
                for word in parsed.entries:
                    if word not in selected:
                        missing += 1
        finally:
            selected.close()
        if record["language"].startswith("en-") and record["name"] == "gold":
            collisions = 0
            selected = open_selected(str(record["language"]), ("gold", "silver"))
            try:
                for word in parsed.entries:
                    hit = selected.get_hit(word)
                    if hit is None:
                        missing += 1
                    elif hit.name != "gold":
                        collisions += 1
            finally:
                selected.close()
            unexpected = collisions
        results.append(
            {
                "id": identifier,
                "missing_keys": missing,
                "unexpected_semantic_hits": unexpected,
                "value_mismatches": mismatches,
                "ok": not (missing or unexpected or mismatches),
                "errors": []
                if not (missing or unexpected or mismatches)
                else [
                    f"missing={missing} unexpected={unexpected} mismatches={mismatches}"
                ],
            }
        )
    return results


__all__ = [
    "LexiconHit",
    "SelectedLexicons",
    "open_selected",
]
