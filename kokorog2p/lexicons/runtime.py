"""Read-only runtime access to named and local G2Lex sources."""

from __future__ import annotations

import hashlib
import re
import weakref
from collections import namedtuple
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from types import MappingProxyType, TracebackType
from typing import Any

import g2lex
from lexphon import DataStore, LexiconNotInstalledError

from .registry import (
    FileLexiconSource,
    LexiconSource,
    LexiconSpec,
    NamedLexiconSource,
    get_lexicon_spec,
    normalize_language,
)


@dataclass(slots=True)
class _SharedLexiconResource:
    """One immutable mapping with explicit consumer leases."""

    key: tuple[str, ...]
    handle: Any
    mapping: Mapping[str, object]
    metadata: Mapping[str, object]
    leases: int = 0
    evicted: bool = False
    closed: bool = False

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        close = getattr(self.handle, "close", None)
        if close is not None:
            close()


_RESOURCE_LOCK = RLock()
_RESOURCE_CACHE: dict[tuple[str, ...], _SharedLexiconResource] = {}
_RESOURCE_HITS = 0
_RESOURCE_MISSES = 0
_ResourceCacheInfo = namedtuple("ResourceCacheInfo", "hits misses maxsize currsize")


def _store_key(store: DataStore) -> str:
    return str(store.root.resolve())


def _missing_asset_error(spec: LexiconSpec) -> str:
    return (
        f"Lexicon {spec.id} is not installed.\n"
        "Run:\n"
        f"  lexphon data install {spec.id}\n"
        f"  lexphon data verify {spec.id}"
    )


def _named_metadata(spec: LexiconSpec) -> Mapping[str, object]:
    return MappingProxyType(
        {
            **dict(spec.metadata),
            "id": spec.id,
            "language": spec.language,
            "name": spec.name,
            "rating": spec.rating,
            "kind": spec.kind,
            "phoneme_encoding": spec.phoneme_encoding,
            "source_kind": "named",
            "backend": spec.backend,
        }
    )


def _acquire_resource(spec: LexiconSpec, store: DataStore) -> _SharedLexiconResource:
    """Acquire a lease on an externally installed named lexicon."""
    global _RESOURCE_HITS, _RESOURCE_MISSES
    if spec.backend != "lexphon":
        raise ValueError(f"lexicon {spec.id!r} is not externally Lexphon-backed")

    key = ("lexphon", _store_key(store), spec.id)
    with _RESOURCE_LOCK:
        resource = _RESOURCE_CACHE.get(key)
        if resource is None:
            _RESOURCE_MISSES += 1
            try:
                path = store.path(spec.id)
            except LexiconNotInstalledError as exc:
                raise LexiconNotInstalledError(_missing_asset_error(spec)) from exc
            handle = g2lex.open(path)
            resource = _SharedLexiconResource(
                key, handle, handle, _named_metadata(spec)
            )
            _RESOURCE_CACHE[key] = resource
        else:
            _RESOURCE_HITS += 1
        resource.leases += 1
        return resource


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_sha256(value: str, *, label: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(f"{label} must be a 64-character SHA-256 hex digest")
    return normalized


def _source_metadata(
    path: Path,
    language: str,
    manifest: Mapping[str, object],
    content_sha256: str,
) -> Mapping[str, object]:
    requested_language = normalize_language(language)
    declared_language = manifest.get("language") or manifest.get("locale")
    if not isinstance(declared_language, str) or not declared_language.strip():
        raise ValueError(
            f"G2Lex file {path} has no language metadata; "
            "include a language in its manifest"
        )
    source_language = normalize_language(declared_language)
    if source_language != requested_language:
        raise ValueError(
            "G2Lex language metadata conflicts with the request:\n"
            f"  language: {source_language}\n"
            f"  request:  {requested_language}"
        )

    encoding = manifest.get("phoneme_encoding")
    if not isinstance(encoding, str) or not encoding.strip():
        raise ValueError(
            f"G2Lex file {path} has no phoneme_encoding metadata; declare its encoding"
        )

    source_info = manifest.get("source")
    source_info = source_info if isinstance(source_info, Mapping) else {}
    display_name = manifest.get("display_name") or manifest.get("name") or path.name
    source_id = (
        manifest.get("id")
        or manifest.get("asset_id")
        or source_info.get("source_id")
        or f"file:{content_sha256[:16]}"
    )
    logical_sha256 = manifest.get("logical_sha256")
    if logical_sha256 is not None:
        logical_sha256 = _normalize_sha256(
            str(logical_sha256), label=f"G2Lex logical_sha256 in {path}"
        )

    return MappingProxyType(
        {
            **dict(manifest),
            "id": str(source_id),
            "name": str(display_name),
            "display_name": str(display_name),
            "language": source_language,
            "phoneme_encoding": encoding.strip().lower(),
            "kind": str(manifest.get("kind", "pronunciation")),
            "rating": manifest.get("rating"),
            "source_kind": "file",
            "path": str(path),
            "resolved_path": str(path),
            "sha256": f"sha256:{content_sha256}",
            "logical_sha256": logical_sha256,
            "entry_count": manifest.get("entry_count"),
        }
    )


def _acquire_file_resource(
    language: str, source: FileLexiconSource
) -> _SharedLexiconResource:
    """Open and validate one local file, reusing only its exact content identity."""
    global _RESOURCE_HITS, _RESOURCE_MISSES
    raw_path = Path(source.path).expanduser()
    try:
        path = raw_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Configured G2Lex file does not exist: {raw_path}"
        ) from exc
    if not path.is_file():
        raise ValueError(f"Configured G2Lex path is not a file: {path}")

    content_sha256 = _file_sha256(path)
    if source.sha256 is not None:
        expected = _normalize_sha256(source.sha256, label="expected G2Lex sha256")
        if expected != content_sha256:
            raise ValueError(
                "Configured G2Lex file content hash does not match its pin.\n"
                f"  path:     {path}\n"
                f"  expected: sha256:{expected}\n"
                f"  actual:   sha256:{content_sha256}"
            )

    key = ("file", str(path), content_sha256)
    with _RESOURCE_LOCK:
        resource = _RESOURCE_CACHE.get(key)
        if resource is None:
            _RESOURCE_MISSES += 1
            try:
                handle = g2lex.open(path)
            except Exception as exc:
                raise ValueError(f"Invalid G2Lex file {path}: {exc}") from exc
            try:
                if _file_sha256(path) != content_sha256:
                    raise ValueError(
                        f"G2Lex file changed while it was being opened: {path}"
                    )
                manifest = getattr(handle, "metadata", None)
                if not isinstance(manifest, Mapping):
                    raise TypeError(
                        f"G2Lex file {path} has no readable manifest metadata"
                    )
                metadata = _source_metadata(path, language, manifest, content_sha256)
                resource = _SharedLexiconResource(key, handle, handle, metadata)
            except Exception:
                close = getattr(handle, "close", None)
                if close is not None:
                    close()
                raise
            _RESOURCE_CACHE[key] = resource
        else:
            _RESOURCE_HITS += 1

        if source.logical_sha256 is not None:
            expected_logical = _normalize_sha256(
                source.logical_sha256, label="expected G2Lex logical_sha256"
            )
            actual_logical = resource.metadata.get("logical_sha256")
            if actual_logical != expected_logical:
                raise ValueError(
                    "Configured G2Lex logical hash does not match its pin.\n"
                    f"  path:     {path}\n"
                    f"  expected: {expected_logical}\n"
                    f"  actual:   {actual_logical or 'unavailable'}"
                )
        resource.leases += 1
        return resource


def _release_resource(resource: _SharedLexiconResource) -> None:
    with _RESOURCE_LOCK:
        if resource.leases <= 0:
            raise RuntimeError(f"resource lease underflow for {resource.key!r}")
        resource.leases -= 1
        if resource.leases == 0 and resource.evicted:
            resource.close()


def _release_resources(resources: tuple[_SharedLexiconResource, ...]) -> None:
    for resource in resources:
        _release_resource(resource)


def clear_resource_cache() -> None:
    """Evict shared resources while retaining resources leased by live consumers."""
    with _RESOURCE_LOCK:
        resources = tuple(_RESOURCE_CACHE.values())
        _RESOURCE_CACHE.clear()
        for resource in resources:
            resource.evicted = True
            if resource.leases == 0:
                resource.close()


def resource_cache_info():
    """Return diagnostics for the shared lexicon resource pool."""
    with _RESOURCE_LOCK:
        return _ResourceCacheInfo(
            _RESOURCE_HITS, _RESOURCE_MISSES, None, len(_RESOURCE_CACHE)
        )


@dataclass(frozen=True, slots=True)
class LexiconHit:
    """A selected value plus pronunciation source metadata."""

    value: object
    name: str
    rating: int | None
    kind: str
    phoneme_encoding: str
    lexicon_id: str
    metadata: Mapping[str, object]
    source_kind: str = "named"
    source_path: str | None = None
    sha256: str | None = None
    logical_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class _SelectedLayer:
    key: str
    name: str
    lexicon_id: str
    rating: int | None
    kind: str
    phoneme_encoding: str
    source_kind: str
    source_path: str | None
    sha256: str | None
    logical_sha256: str | None
    metadata: Mapping[str, object]


class SelectedLexicons:
    """An ordered collection of lazy named or local G2Lex mappings."""

    def __init__(
        self,
        language: str,
        names: Sequence[str] | None = None,
        *,
        sources: Sequence[LexiconSource] | None = None,
        store: DataStore | None = None,
    ) -> None:
        if sources is not None and names is not None:
            raise ValueError("pass either names or sources, not both")
        selected_sources: tuple[LexiconSource, ...]
        if sources is None:
            selected_sources = tuple(NamedLexiconSource(name) for name in (names or ()))
        else:
            selected_sources = tuple(sources)

        self.language = normalize_language(language)
        self.sources = selected_sources
        self.names = tuple(
            source.name
            for source in selected_sources
            if isinstance(source, NamedLexiconSource)
        )
        self.store = DataStore() if store is None else store
        self._layers: dict[str, Mapping[str, object]] = {}
        self._closed = False
        layer_records: list[g2lex.LexiconLayer] = []
        layer_info: list[_SelectedLayer] = []
        resources: list[_SharedLexiconResource] = []
        seen: set[tuple[str, ...]] = set()
        try:
            for source in selected_sources:
                if isinstance(source, NamedLexiconSource):
                    if not source.name or not isinstance(source.name, str):
                        raise ValueError(
                            "named lexicon source name must be a non-empty string"
                        )
                    spec = get_lexicon_spec(self.language, source.name)
                    duplicate_key = ("named", spec.id)
                    if duplicate_key in seen:
                        raise ValueError(f"duplicate lexicon source: {source.name}")
                    resource = _acquire_resource(spec, self.store)
                    metadata = resource.metadata
                    key = spec.name
                elif isinstance(source, FileLexiconSource):
                    resource = _acquire_file_resource(self.language, source)
                    metadata = resource.metadata
                    duplicate_key = ("file", str(metadata["sha256"]))
                    if duplicate_key in seen:
                        _release_resource(resource)
                        raise ValueError(
                            f"duplicate G2Lex file source: {metadata['path']}"
                        )
                    key = f"file:{str(metadata['sha256'])[-12:]}"
                else:
                    raise TypeError(
                        f"unsupported lexicon source type: {type(source).__name__}"
                    )

                if duplicate_key in seen:
                    _release_resource(resource)
                    raise ValueError(f"duplicate lexicon source: {key}")
                seen.add(duplicate_key)
                resources.append(resource)
                layer_records.append(
                    g2lex.LexiconLayer(key, resource.mapping, metadata)
                )
                self._layers[key] = resource.mapping
                rating = metadata.get("rating")
                layer_info.append(
                    _SelectedLayer(
                        key=key,
                        name=str(
                            metadata.get("display_name", metadata.get("name", key))
                        ),
                        lexicon_id=str(metadata.get("id", key)),
                        rating=rating if isinstance(rating, int) else None,
                        kind=str(metadata.get("kind", "pronunciation")),
                        phoneme_encoding=str(metadata.get("phoneme_encoding", "")),
                        source_kind=str(metadata.get("source_kind", "named")),
                        source_path=(
                            str(metadata["path"])
                            if metadata.get("path") is not None
                            else None
                        ),
                        sha256=(
                            str(metadata["sha256"])
                            if metadata.get("sha256") is not None
                            else None
                        ),
                        logical_sha256=(
                            str(metadata["logical_sha256"])
                            if metadata.get("logical_sha256") is not None
                            else None
                        ),
                        metadata=metadata,
                    )
                )
        except Exception:
            _release_resources(tuple(reversed(resources)))
            raise

        self._resources = tuple(resources)
        self._layer_info = tuple(layer_info)
        self._layered = g2lex.LayeredLexicon(layer_records)
        self._finalizer = weakref.finalize(self, _release_resources, self._resources)

    def _ensure_open(self) -> None:
        if self._closed:
            raise ValueError("selected lexicons are closed")

    def _hit(self, hit: Any) -> LexiconHit:
        info = self._layer_info[hit.index]
        return LexiconHit(
            value=hit.value,
            name=info.name,
            rating=info.rating,
            kind=info.kind,
            phoneme_encoding=info.phoneme_encoding,
            lexicon_id=info.lexicon_id,
            metadata=dict(info.metadata),
            source_kind=info.source_kind,
            source_path=info.source_path,
            sha256=info.sha256,
            logical_sha256=info.logical_sha256,
        )

    def get_hit(self, word: str) -> LexiconHit | None:
        """Return the first matching value according to configured precedence."""
        self._ensure_open()
        hit = self._layered.get_hit(word)
        return None if hit is None else self._hit(hit)

    def lookup_hit(self, word: str) -> LexiconHit | None:
        """Return only an exact hit from the configured selected stack."""
        return self.get_hit(word)

    def get_hit_candidates(self, words: Sequence[str]) -> LexiconHit | None:
        """Search selected layers for the first matching candidate."""
        self._ensure_open()
        hit = self._layered.get_hit_candidates(words)
        return None if hit is None else self._hit(hit)

    def layer(self, name: str) -> Mapping[str, object] | None:
        """Return one selected mapping by layer key or display name."""
        self._ensure_open()
        if name in self._layers:
            return self._layers[name]
        for info in self._layer_info:
            if info.name == name:
                return self._layers[info.key]
        return None

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and self.get_hit(word) is not None

    def __len__(self) -> int:
        self._ensure_open()
        return len(self._layered)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._layers.clear()
        self._finalizer()

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


def open_selected(
    language: str,
    names: Sequence[str],
    *,
    store: DataStore | None = None,
) -> SelectedLexicons:
    """Open the named externally provisioned lexicons in supplied order."""
    return SelectedLexicons(language, names, store=store)


def open_sources(
    language: str,
    sources: Sequence[LexiconSource],
    *,
    store: DataStore | None = None,
) -> SelectedLexicons:
    """Open named and local G2Lex sources in their supplied precedence order."""
    return SelectedLexicons(language, sources=sources, store=store)


__all__ = [
    "LexiconHit",
    "SelectedLexicons",
    "clear_resource_cache",
    "open_selected",
    "open_sources",
    "resource_cache_info",
]
