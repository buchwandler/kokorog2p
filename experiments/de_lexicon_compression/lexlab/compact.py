"""Dependency-free deterministic compact representations for P2/P4 experiments."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .decoder import CompressedLexicon
from .model import SourceInfo

COMPACT_SCHEMA = 2


def _source_dict(source: SourceInfo) -> dict[str, Any]:
    value = {
        "source_id": source.source_id,
        "revision": source.revision,
        "sha256": source.sha256,
        "license": source.license,
        "provenance_status": source.provenance_status,
        "parser_version": source.parser_version,
        "view_version": source.view_version,
        "format": source.format,
        "path": Path(source.path).name if source.path else None,
        "size_bytes": source.size_bytes,
    }
    return value


def _bytes(value: dict[str, Any]) -> bytes:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return (encoded + "\n").encode("utf-8")


def _common(compressed: CompressedLexicon, mode: str) -> dict[str, Any]:
    return {
        "schema": COMPACT_SCHEMA,
        "mode": mode,
        "source": _source_dict(compressed.source),
        "metadata": dict(compressed.metadata),
    }
def verify_lookup(asset, source, *, sample_limit: int = 100) -> dict[str, object]:
    source_words = set(source.words)
    asset_words = set(asset.words)
    missing = sorted(source_words - asset_words)
    extra = sorted(asset_words - source_words)
    mismatches = 0
    rows = []
    for word in sorted(source_words & asset_words):
        expected = source.lookup_all(word)
        actual = asset.lookup_all(word)
        if actual != expected:
            mismatches += 1
            if len(rows) < sample_limit:
                rows.append({"word": word, "expected": expected, "actual": actual})
    return {
        "missing_words": missing,
        "extra_words": extra,
        "pronunciation_mismatches": mismatches,
        "variant_count_mismatches": 0,
        "variant_order_mismatches": 0,
        "failures": len(missing) + len(extra) + mismatches,
        "failure_rows": rows,
        "lossless": not (missing or extra or mismatches),
    }



@dataclass(slots=True)
class IdCompressedLexicon:
    source: SourceInfo
    atom_words: tuple[str, ...]
    atom_variants: tuple[tuple[str, ...], ...]
    exceptions: dict[str, tuple[str, ...]]
    derived: dict[str, tuple[int, ...]]
    metadata: dict[str, object]

    def lookup_all(self, word: str) -> tuple[str, ...]:
        if word in self.exceptions:
            return self.exceptions[word]
        try:
            atom_id = self.atom_words.index(word)
        except ValueError:
            atom_id = -1
        if atom_id >= 0:
            return self.atom_variants[atom_id]
        components = self.derived.get(word)
        if components is None:
            return ()
        result = [""]
        for atom_id in components:
            result = [
                prefix + value
                for prefix in result
                for value in self.atom_variants[atom_id]
            ]
        return tuple(result)

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(sorted((*self.atom_words, *self.exceptions, *self.derived)))


def to_id_asset(compressed: CompressedLexicon) -> IdCompressedLexicon:
    words = tuple(sorted(compressed.atoms))
    ids = {word: index for index, word in enumerate(words)}
    return IdCompressedLexicon(
        compressed.source,
        words,
        tuple(compressed.atoms[word] for word in words),
        dict(compressed.exceptions),
        {
            word: tuple(ids[component] for component in components)
            for word, components in sorted(compressed.derived.items())
        },
        {**compressed.metadata, "mode": "exact-multipart-ids"},
    )


def id_asset_dict(compressed: CompressedLexicon) -> dict[str, Any]:
    asset = to_id_asset(compressed)
    return {
        **_common(compressed, "exact-multipart-ids"),
        "atoms": [
            [word, list(values)]
            for word, values in zip(asset.atom_words, asset.atom_variants, strict=True)
        ],
        "exceptions": {
            word: list(values) for word, values in sorted(asset.exceptions.items())
        },
        "derived": {
            word: list(values) for word, values in sorted(asset.derived.items())
        },
    }


def serialize_ids(compressed: CompressedLexicon) -> bytes:
    return _bytes(id_asset_dict(compressed))


def _source(value: dict[str, Any]) -> SourceInfo:
    return SourceInfo(**value)


def deserialize_ids(data: bytes) -> IdCompressedLexicon:
    value = json.loads(data.decode("utf-8"))
    if (
        value.get("schema") != COMPACT_SCHEMA
        or value.get("mode") != "exact-multipart-ids"
    ):
        raise ValueError("not an exact-multipart-ids asset")
    atoms = value.get("atoms", [])
    return IdCompressedLexicon(
        _source(value["source"]),
        tuple(item[0] for item in atoms),
        tuple(tuple(item[1]) for item in atoms),
        {word: tuple(values) for word, values in value.get("exceptions", {}).items()},
        {word: tuple(values) for word, values in value.get("derived", {}).items()},
        dict(value.get("metadata", {})),
    )


@dataclass(slots=True)
class InternedLexicon:
    source: SourceInfo
    ipa_table: tuple[str, ...]
    atom_words: tuple[str, ...]
    atom_variants: tuple[tuple[int, ...], ...]
    exceptions: dict[str, tuple[int, ...]]
    derived: dict[str, tuple[int, ...]]
    metadata: dict[str, object]

    def _variants(self, ids: tuple[int, ...]) -> tuple[str, ...]:
        return tuple(self.ipa_table[index] for index in ids)

    def lookup_all(self, word: str) -> tuple[str, ...]:
        if word in self.exceptions:
            return self._variants(self.exceptions[word])
        try:
            atom_id = self.atom_words.index(word)
        except ValueError:
            atom_id = -1
        if atom_id >= 0:
            return self._variants(self.atom_variants[atom_id])
        components = self.derived.get(word)
        if components is None:
            return ()
        result = [""]
        for atom_id in components:
            result = [
                prefix + value
                for prefix in result
                for value in self._variants(self.atom_variants[atom_id])
            ]
        return tuple(result)

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(sorted((*self.atom_words, *self.exceptions, *self.derived)))


def to_interned_asset(compressed: CompressedLexicon) -> InternedLexicon:
    all_values = {
        value for values in compressed.atoms.values() for value in values
    }
    all_values.update(
        value for values in compressed.exceptions.values() for value in values
    )
    ipa_table = tuple(sorted(all_values))
    ids = {value: index for index, value in enumerate(ipa_table)}
    words = tuple(sorted(compressed.atoms))
    atom_ids = {word: index for index, word in enumerate(words)}
    atom_variants = tuple(
        tuple(ids[value] for value in compressed.atoms[word]) for word in words
    )
    return InternedLexicon(
        compressed.source,
        ipa_table,
        words,
        atom_variants,
        {
            word: tuple(ids[value] for value in values)
            for word, values in sorted(compressed.exceptions.items())
        },
        {
            word: tuple(atom_ids[component] for component in components)
            for word, components in sorted(compressed.derived.items())
        },
        {**compressed.metadata, "mode": "ipa-intern"},
    )


def interned_asset_dict(compressed: CompressedLexicon) -> dict[str, Any]:
    asset = to_interned_asset(compressed)
    return {
        **_common(compressed, "ipa-intern"),
        "ipa": list(asset.ipa_table),
        "atoms": [
            [word, list(values)]
            for word, values in zip(asset.atom_words, asset.atom_variants, strict=True)
        ],
        "exceptions": {
            word: list(values) for word, values in sorted(asset.exceptions.items())
        },
        "derived": {
            word: list(values) for word, values in sorted(asset.derived.items())
        },
    }


def serialize_interned(compressed: CompressedLexicon) -> bytes:
    return _bytes(interned_asset_dict(compressed))


def deserialize_interned(data: bytes) -> InternedLexicon:
    value = json.loads(data.decode("utf-8"))
    if value.get("schema") != COMPACT_SCHEMA or value.get("mode") != "ipa-intern":
        raise ValueError("not an ipa-intern asset")
    atoms = value.get("atoms", [])
    return InternedLexicon(
        _source(value["source"]),
        tuple(value.get("ipa", [])),
        tuple(item[0] for item in atoms),
        tuple(tuple(item[1]) for item in atoms),
        {word: tuple(values) for word, values in value.get("exceptions", {}).items()},
        {word: tuple(values) for word, values in value.get("derived", {}).items()},
        dict(value.get("metadata", {})),
    )


def build_macros(values: list[str], *, max_macros: int = 128) -> tuple[str, ...]:
    counts: Counter[str] = Counter()
    for value in values:
        for length in range(2, min(5, len(value) + 1)):
            counts.update(
                value[index : index + length]
                for index in range(len(value) - length + 1)
            )
    candidates = [
        (count, len(value), value)
        for value, count in counts.items()
        if count > 1
    ]
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return tuple(value for _count, _length, value in candidates[:max_macros])


def encode_macro(value: str, macros: tuple[str, ...]) -> list[list[object]]:
    tokens: list[list[object]] = []
    position = 0
    ordered = sorted(enumerate(macros), key=lambda item: (-len(item[1]), item[0]))
    while position < len(value):
        match = next(
            (
                (index, macro)
                for index, macro in ordered
                if value.startswith(macro, position)
            ),
            None,
        )
        if match is None:
            tokens.append(["s", value[position]])
            position += 1
        else:
            index, macro = match
            tokens.append(["m", index])
            position += len(macro)
    return tokens


def decode_macro(tokens: list[list[object]], macros: tuple[str, ...]) -> str:
    output: list[str] = []
    for kind, value in tokens:
        if kind == "s":
            output.append(str(value))
        elif kind == "m":
            output.append(macros[int(value)])
        else:
            raise ValueError(f"unknown macro token {kind!r}")
    return "".join(output)


def macro_asset_dict(compressed: CompressedLexicon) -> dict[str, Any]:
    interned = to_interned_asset(compressed)
    macros = build_macros(list(interned.ipa_table))
    return {
        **_common(compressed, "ipa-repair-macros"),
        "macros": list(macros),
        "ipa_tokens": [encode_macro(value, macros) for value in interned.ipa_table],
        "atoms": [
            [word, list(values)]
            for word, values in zip(
                interned.atom_words, interned.atom_variants, strict=True
            )
        ],
        "exceptions": {
            word: list(values) for word, values in sorted(interned.exceptions.items())
        },
        "derived": {
            word: list(values) for word, values in sorted(interned.derived.items())
        },
    }


def serialize_macros(compressed: CompressedLexicon) -> bytes:
    return _bytes(macro_asset_dict(compressed))


def deserialize_macros(data: bytes) -> InternedLexicon:
    value = json.loads(data.decode("utf-8"))
    if (
        value.get("schema") != COMPACT_SCHEMA
        or value.get("mode") != "ipa-repair-macros"
    ):
        raise ValueError("not an ipa-repair-macros asset")
    macros = tuple(value.get("macros", []))
    ipa_table = tuple(
        decode_macro(tokens, macros) for tokens in value.get("ipa_tokens", [])
    )
    atoms = value.get("atoms", [])
    return InternedLexicon(
        _source(value["source"]),
        ipa_table,
        tuple(item[0] for item in atoms),
        tuple(tuple(item[1]) for item in atoms),
        {word: tuple(values) for word, values in value.get("exceptions", {}).items()},
        {word: tuple(values) for word, values in value.get("derived", {}).items()},
        dict(value.get("metadata", {})),
    )


def serialize_compact(compressed: CompressedLexicon, mode: str) -> bytes:
    if mode == "exact-multipart-ids":
        return serialize_ids(compressed)
    if mode == "ipa-intern":
        return serialize_interned(compressed)
    if mode == "ipa-repair-macros":
        return serialize_macros(compressed)
    raise ValueError(f"unknown compact mode: {mode}")


def deserialize_compact(data: bytes):
    mode = json.loads(data.decode("utf-8")).get("mode")
    if mode == "exact-multipart-ids":
        return deserialize_ids(data)
    if mode == "ipa-intern":
        return deserialize_interned(data)
    if mode == "ipa-repair-macros":
        return deserialize_macros(data)
    if mode == "front-coded":
        from .p4 import deserialize_front_coded

        return deserialize_front_coded(data)
    raise ValueError(f"unknown compact mode: {mode!r}")
