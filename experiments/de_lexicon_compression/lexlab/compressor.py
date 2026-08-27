"""Build exact atom/exception compositions from one source at a time."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from .composition import CompositionMetrics, SearchLimitError, exact_composition
from .decoder import CompressedLexicon
from .model import ParsedLexicon


@dataclass(slots=True)
class CompressionResult:
    compressed: CompressedLexicon
    metrics: CompositionMetrics
    failures: list[dict[str, object]] = field(default_factory=list)
    component_usage: list[dict[str, object]] = field(default_factory=list)
    derivation_depth: list[dict[str, object]] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def derived_words(self) -> int:
        return len(self.compressed.derived)


def compress_lexicon(
    source: ParsedLexicon,
    *,
    mode: str = "exact-multipart",
    max_states: int = 100_000,
) -> CompressionResult:
    if mode not in {"baseline", "exact-two-part", "exact-multipart"}:
        raise ValueError(f"unknown compression mode: {mode}")
    started = perf_counter()
    direct: dict[str, tuple[str, ...]] = {}
    derived: dict[str, tuple[str, ...]] = {}
    metrics = CompositionMetrics()
    failures: list[dict[str, object]] = []
    depths: list[dict[str, object]] = []
    if mode == "baseline":
        direct = {word: source.lookup_all(word) for word in sorted(source.words)}
        compressed = CompressedLexicon(
            source.source,
            {},
            direct,
            {},
            {"mode": mode, "lossless_contract": "source-semantic"},
        )
        return CompressionResult(
            compressed, metrics, failures, [], depths, perf_counter() - started
        )
    for word in sorted(source.words, key=lambda value: (len(value), value)):
        expected = source.lookup_all(word)
        try:
            segmentation, candidate = exact_composition(
                word,
                expected,
                direct,
                mode=mode,
                max_states=max_states,
                metrics=metrics,
            )
        except SearchLimitError:
            segmentation, candidate = None, ()
            failures.append(
                {
                    "source": source.source.source_id,
                    "word": word,
                    "variant_index": "",
                    "expected": "",
                    "candidate": "",
                    "components": "",
                    "reason": "SEARCH_LIMIT",
                }
            )
        if segmentation is not None and candidate == expected:
            derived[word] = segmentation.components
            depths.append(
                {
                    "word": word,
                    "components": "|".join(segmentation.components),
                    "depth": len(segmentation.components),
                }
            )
        else:
            direct[word] = expected
            if segmentation is None:
                reason = "NO_ORTHOGRAPHIC_SEGMENTATION"
            elif not candidate:
                reason = "NO_PHONE_PREFIX_MATCH"
            else:
                reason = "VARIANT_TUPLE_MISMATCH"
            if not any(item.get("word") == word for item in failures):
                failures.extend(
                    {
                        "source": source.source.source_id,
                        "word": word,
                        "variant_index": index,
                        "expected": value,
                        "candidate": candidate[index] if index < len(candidate) else "",
                        "components": "|".join(segmentation.components)
                        if segmentation
                        else "",
                        "reason": reason,
                    }
                    for index, value in enumerate(expected)
                )
    used = {component for components in derived.values() for component in components}
    atoms = {word: direct.pop(word) for word in sorted(used)}
    exceptions = {word: direct[word] for word in sorted(direct)}
    usage = []
    for atom, values in atoms.items():
        uses = [word for word, components in derived.items() if atom in components]
        usage.append(
            {
                "atom": atom,
                "pronunciation_variant_count": len(values),
                "derived_word_uses": len(uses),
                "derived_variant_uses": len(uses),
                "estimated_rows_saved": len(uses),
                "estimated_bytes_saved": 0,
            }
        )
    compressed = CompressedLexicon(
        source.source,
        atoms,
        exceptions,
        derived,
        {"mode": mode, "lossless_contract": "source-semantic"},
    )
    return CompressionResult(
        compressed, metrics, failures, usage, depths, perf_counter() - started
    )
