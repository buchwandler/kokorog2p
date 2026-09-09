"""Read-only runtime access to externally provisioned G2Lex assets."""

from __future__ import annotations

import weakref
from collections import namedtuple
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from threading import RLock
from types import TracebackType
from typing import Any

import g2lex
from lexphon import DataStore, LexiconNotInstalledError

from .registry import LexiconSpec, get_lexicon_spec, normalize_language


@dataclass(slots=True)
class _SharedLexiconResource:
    """One immutable external mapping with explicit consumer leases."""

    key: tuple[str, str]
    handle: Any
    mapping: Mapping[str, object]
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
_RESOURCE_CACHE: dict[tuple[str, str], _SharedLexiconResource] = {}
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


def _acquire_resource(spec: LexiconSpec, store: DataStore) -> _SharedLexiconResource:
    """Acquire a lease on an externally installed lexicon."""
    global _RESOURCE_HITS, _RESOURCE_MISSES
    if spec.backend != "lexphon":
        raise ValueError(f"lexicon {spec.id!r} is not externally Lexphon-backed")

    key = (_store_key(store), spec.id)
    with _RESOURCE_LOCK:
        resource = _RESOURCE_CACHE.get(key)
        if resource is None:
            _RESOURCE_MISSES += 1
            try:
                path = store.path(spec.id)
            except LexiconNotInstalledError as exc:
                raise LexiconNotInstalledError(_missing_asset_error(spec)) from exc
            handle = g2lex.open(path)
            resource = _SharedLexiconResource(key, handle, handle)
            _RESOURCE_CACHE[key] = resource
        else:
            _RESOURCE_HITS += 1
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
    """Return diagnostics for the shared external resource pool."""
    with _RESOURCE_LOCK:
        return _ResourceCacheInfo(
            _RESOURCE_HITS, _RESOURCE_MISSES, None, len(_RESOURCE_CACHE)
        )


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


class SelectedLexicons:
    """An ordered collection of lazy external G2Lex mappings."""

    def __init__(
        self,
        language: str,
        names: Sequence[str],
        *,
        store: DataStore | None = None,
    ) -> None:
        self.language = normalize_language(language)
        self.names = tuple(names)
        self.store = DataStore() if store is None else store
        self._specs: tuple[LexiconSpec, ...] = tuple(
            get_lexicon_spec(self.language, name) for name in self.names
        )
        self._layers: dict[str, Mapping[str, object]] = {}
        layer_records: list[g2lex.LexiconLayer] = []
        resources: list[_SharedLexiconResource] = []
        try:
            for spec in self._specs:
                resource = _acquire_resource(spec, self.store)
                resources.append(resource)
                self._layers[spec.name] = resource.mapping
                layer_records.append(
                    g2lex.LexiconLayer(
                        spec.name,
                        resource.mapping,
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
            _release_resources(tuple(reversed(resources)))
            raise
        self._resources = tuple(resources)
        self._layered = g2lex.LayeredLexicon(layer_records)
        self._closed = False
        self._finalizer = weakref.finalize(self, _release_resources, self._resources)

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

    def lookup_hit(self, word: str) -> LexiconHit | None:
        """Return only an exact hit from the configured selected stack."""
        return self.get_hit(word)

    def get_hit_candidates(self, words: Sequence[str]) -> LexiconHit | None:
        """Search selected layers for the first matching candidate."""
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


__all__ = [
    "LexiconHit",
    "SelectedLexicons",
    "clear_resource_cache",
    "open_selected",
    "resource_cache_info",
]
