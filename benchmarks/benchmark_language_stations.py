#!/usr/bin/env python3
"""Cross-language prepared-text G2P station benchmark."""

from __future__ import annotations

import argparse
import functools
import json
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any

try:
    import resource
except ImportError:  # pragma: no cover
    resource = None  # type: ignore[assignment]

from kokorog2p import clear_cache, get_g2p, phonemize_prepared

try:
    from .station_corpora import LANGUAGES, Corpus, get_corpus
except ImportError:
    from station_corpora import LANGUAGES, Corpus, get_corpus

try:
    from lexphon import LexiconNotInstalledError
except ImportError:  # pragma: no cover
    LexiconNotInstalledError = None  # type: ignore[assignment,misc]


PREPARED_BOUNDARIES = {
    "_prepare_span_text": "prepared/coerce_annotations",
    "tokenize_with_offsets": "prepared/build_token_spans",
    "_call_g2p_prepared": "prepared/frontend_call",
    "ensure_gtoken_positions": "prepared/ensure_positions",
    "gtokens_to_tokenspans": "prepared/gtoken_to_spans",
    "_phonemize_token_spans": "prepared/phonemize_token_spans",
    "_build_phoneme_string": "prepared/build_phoneme_string",
    "validate_for_kokoro": "prepared/vocab_validation",
    "phonemes_to_ids": "prepared/ids",
}

FRONTEND_METHODS = {
    "lookup": "frontend/lookup",
    "_word_to_phonemes": "frontend/word_to_phonemes",
    "_phonemize_word": "frontend/phonemize_word",
    "_phonemize_text": "frontend/phonemize_text",
    "_phonemize_internal": "frontend/phonemize_internal",
    "_preprocess": "frontend/preprocess",
    "_tokenize": "frontend/tokenize",
    "_tokenize_simple": "frontend/tokenize_simple",
    "_tokenize_spacy": "frontend/tokenize_spacy",
    "_fallback_or_unknown": "frontend/fallback_or_unknown",
    "_diacritize": "frontend/diacritize",
    "_thai_analysis": "frontend/thai_analysis",
    "_latin_phonemes": "frontend/latin_phonemes",
    "_convert_output": "frontend/convert_output",
    "_phonemize_pyopenjtalk": "frontend/pyopenjtalk",
    "_phonemize_cutlet": "frontend/cutlet",
    "phonemize_word_raw": "frontend/phonemize_word_raw",
    "run_frontend": "frontend/run_frontend",
    "word2ipa": "frontend/word2ipa",
    "py2ipa": "frontend/py2ipa",
    "legacy_call": "frontend/legacy_call",
    "accentuate": "frontend/accentuate",
    "analyze": "frontend/analyze",
    "phonemize_accented": "frontend/phonemize_accented",
    "_word_analysis": "frontend/word_analysis",
    "_alignment": "frontend/alignment",
    "_token": "frontend/token",
    "_tokens_from_alignment": "frontend/tokens_from_alignment",
    "_get_diacritizer": "frontend/get_diacritizer",
}

COMPONENT_METHODS = {
    "__call__",
    "lookup",
    "phonemize",
    "phonemize_many",
    "_backend_phonemize",
    "_backend_word_phonemes",
    "word_phonemes",
    "phonemize_word_raw",
    "run_frontend",
    "pronounce_thai_chunk",
}

COMPONENT_HINTS = (
    "lexicon",
    "fallback",
    "rule",
    "engine",
    "frontend",
    "backend",
    "espeak",
    "phonikud",
    "g2pk",
    "cutlet",
    "pyopenjtalk",
    "pypinyin",
)

LAZY_STATE_ATTRIBUTES = {
    "_phonemizer",
    "_espeak_backend",
    "_fallback",
    "_english_g2p",
    "_foreign_g2p",
    "_g2pk_instance",
    "_pyopenjtalk",
    "_cutlet",
    "_diacritizer",
    "_lexphon",
}


@dataclass
class BenchmarkContext:
    phase: str = "startup"
    run_index: int | None = None
    sentence_index: int | None = None
    input_text: str | None = None

    def update(
        self,
        phase: str,
        *,
        run_index: int | None = None,
        sentence_index: int | None = None,
        input_text: str | None = None,
    ) -> None:
        self.phase = phase
        self.run_index = run_index
        self.sentence_index = sentence_index
        self.input_text = input_text


@dataclass
class Recorder:
    values_ms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    details: dict[str, list[tuple[float, str]]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def record(self, station: str, elapsed_ms: float, detail: str = "") -> None:
        self.values_ms[station].append(elapsed_ms)
        if detail:
            self.details[station].append((elapsed_ms, detail))

    def call(
        self,
        station: str,
        fn: Callable[..., Any],
        *args: Any,
        detail: str = "",
        **kwargs: Any,
    ) -> Any:
        started = time.perf_counter_ns()
        try:
            return fn(*args, **kwargs)
        finally:
            self.record(station, (time.perf_counter_ns() - started) / 1_000_000, detail)


def _stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "calls": 0,
            "total_ms": 0.0,
            "min_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0,
            "max_ms": 0.0,
        }
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return {
        "calls": len(values),
        "total_ms": sum(values),
        "min_ms": ordered[0],
        "median_ms": statistics.median(values),
        "p95_ms": ordered[index],
        "max_ms": ordered[-1],
    }


def _p95(values: list[float]) -> float:
    return float(_stats(values)["p95_ms"])


def _detail_from_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    for value in args:
        if isinstance(value, str) and value:
            return value[:120]
    for key in ("word", "text", "token"):
        value = kwargs.get(key)
        if isinstance(value, str) and value:
            return value[:120]
    return ""


class PatchSet:
    """Install timed wrappers and restore every touched symbol on exit."""

    def __init__(self, recorder: Recorder) -> None:
        self.recorder = recorder
        self._restorers: list[Callable[[], None]] = []
        self._class_patches: set[tuple[type[Any], str]] = set()

    def patch_module_function(self, module: Any, name: str, station: str) -> bool:
        original = getattr(module, name, None)
        if not callable(original):
            return False

        @functools.wraps(original)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return self.recorder.call(
                station,
                original,
                *args,
                detail=_detail_from_args(args, kwargs),
                **kwargs,
            )

        setattr(module, name, wrapped)
        self._restorers.append(lambda: setattr(module, name, original))
        return True

    def patch_method(self, instance: Any, name: str, station: str) -> bool:
        cls = type(instance)
        key = (cls, name)
        if key in self._class_patches:
            return False
        had_own = name in cls.__dict__
        original = getattr(cls, name, None)
        if not callable(original):
            return False

        @functools.wraps(original)
        def wrapped(self_obj: Any, *args: Any, **kwargs: Any) -> Any:
            return self.recorder.call(
                station,
                original,
                self_obj,
                *args,
                detail=_detail_from_args(args, kwargs),
                **kwargs,
            )

        setattr(cls, name, wrapped)

        def restore() -> None:
            if had_own:
                setattr(cls, name, original)
            else:
                delattr(cls, name)

        self._restorers.append(restore)
        self._class_patches.add(key)
        return True

    def close(self) -> None:
        while self._restorers:
            self._restorers.pop()()
        self._class_patches.clear()

    def __enter__(self) -> Any:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class SubprocessProbe:
    """Count and time subprocess eSpeak calls without changing their behavior."""

    def __init__(self, recorder: Recorder) -> None:
        self.recorder = recorder
        self.count = 0
        self.commands: list[str] = []
        self._original: Callable[..., Any] | None = None

    @staticmethod
    def _looks_like_espeak(command: Any) -> bool:
        if isinstance(command, (list, tuple)) and command:
            head = str(command[0]).lower()
        else:
            head = str(command).split(maxsplit=1)[0].lower() if command else ""
        return "espeak" in Path(head).name

    def __enter__(self) -> Any:
        self._original = subprocess.run
        original = self._original

        @functools.wraps(original)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            command = args[0] if args else kwargs.get("args")
            if not self._looks_like_espeak(command):
                return original(*args, **kwargs)
            self.count += 1
            rendered = (
                " ".join(map(str, command))
                if isinstance(command, (list, tuple))
                else str(command)
            )
            self.commands.append(rendered[:240])
            return self.recorder.call(
                "espeak/subprocess", original, *args, detail=rendered[:120], **kwargs
            )

        subprocess.run = wrapped
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._original is not None:
            subprocess.run = self._original


def _component_name(attribute: str, value: Any) -> str:
    clean = attribute.strip("_").replace("_", "-") or type(value).__name__.lower()
    return f"component/{clean}"


def _is_component(attribute: str, value: Any) -> bool:
    if value is None or isinstance(value, (ModuleType, type)):
        return False
    lowered = attribute.lower()
    class_name = type(value).__name__.lower()
    if not any(hint in lowered or hint in class_name for hint in COMPONENT_HINTS):
        return False
    return any(
        callable(getattr(value, method_name, None)) for method_name in COMPONENT_METHODS
    )


def _walk_objects(root: Any, *, max_depth: int = 2) -> Iterable[tuple[str, Any]]:
    seen: set[int] = set()

    def visit(path: str, value: Any, depth: int) -> Iterable[tuple[str, Any]]:
        if (
            id(value) in seen
            or depth > max_depth
            or isinstance(
                value, (str, bytes, int, float, bool, type(None), ModuleType, type)
            )
        ):
            return
        seen.add(id(value))
        yield path, value
        try:
            fields = vars(value)
        except TypeError:
            return
        for attribute, child in fields.items():
            if attribute in LAZY_STATE_ATTRIBUTES or _is_component(attribute, child):
                yield from visit(f"{path}.{attribute}", child, depth + 1)

    yield from visit("G2P", root, 0)


def _instrument_frontend(patches: PatchSet, g2p: Any) -> None:
    for method_name, station in FRONTEND_METHODS.items():
        patches.patch_method(g2p, method_name, station)


def _instrument_components(
    patches: PatchSet, g2p: Any, known_components: dict[str, Any]
) -> None:
    for path, obj in _walk_objects(g2p):
        if path != "G2P":
            known_components[path] = obj
        for method_name in COMPONENT_METHODS:
            patches.patch_method(
                obj,
                method_name,
                f"{_component_name(path, obj)}/{method_name.lstrip('_')}",
            )


def _lazy_state(obj: object, *, depth: int = 2) -> dict[str, str]:
    """Return bounded state for known lazy component attributes."""
    result: dict[str, str] = {}
    for path, current in _walk_objects(obj, max_depth=depth):
        try:
            fields = vars(current)
        except TypeError:
            fields = {}
        for attribute in LAZY_STATE_ATTRIBUTES:
            state_path = f"{path}.{attribute}" if path != "G2P" else attribute
            if attribute not in fields:
                result[state_path] = "absent"
            else:
                value = fields[attribute]
                result[state_path] = (
                    "none" if value is None else f"present:{type(value).__name__}"
                )
    return dict(sorted(result.items()))


def _snapshot_components(g2p: Any) -> dict[str, int]:
    return {
        path: id(value)
        for path, value in _walk_objects(g2p)
        if path == "G2P" or _is_component(path.rsplit(".", 1)[-1], value)
    }


def _merge_reuse(before: dict[str, int], after: dict[str, int]) -> dict[str, bool]:
    return {
        key: key in before and key in after and before[key] == after[key]
        for key in sorted(set(before) | set(after))
    }


def _rss_mib() -> float | None:
    if resource is None:
        return None
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0)


def _normalise_benchmark_output(value: str) -> str:
    value = " ".join(value.split())
    return re.sub(r"\s*([,.!?;:，。！？；：])\s*", r"\1", value)


def _token_phoneme_string(tokens: list[Any]) -> str:
    return "".join(
        (getattr(token, "phonemes", None) or "")
        + (getattr(token, "whitespace", None) or "")
        for token in tokens
    ).strip()


def _count_word_tokens(tokens: list[Any]) -> int:
    count = 0
    for token in tokens:
        try:
            if token.is_word:
                count += 1
                continue
        except Exception:
            pass
        text = str(getattr(token, "text", "") or "")
        if text and any(ch.isalnum() for ch in text):
            count += 1
    return count


def _normalise_source_name(value: Any) -> str | None:
    if hasattr(value, "value"):
        value = value.value
    if not isinstance(value, str):
        return None
    value = value.strip().lower().replace(" ", "_")
    return value or None


KNOWN_SOURCE_NAMES = {
    "lexicon",
    "rules",
    "native_rules",
    "espeak",
    "espeak_fallback",
    "goruut",
    "fallback",
    "language_backend",
}


def _source_for_token(token: Any, language: str) -> str:
    try:
        if token.is_punctuation:
            return "punctuation"
    except Exception:
        pass

    extension = getattr(token, "_", None)
    if isinstance(extension, dict):
        for key in ("source", "phoneme_source", "g2p_source"):
            source = _normalise_source_name(extension.get(key))
            if source:
                return source
        rating = extension.get("rating")
    else:
        rating = None

    if language == "de" and isinstance(rating, (int, float)):
        return {5: "lexicon", 3: "espeak_fallback", 2: "german_rules"}.get(
            int(rating), "resolved"
        )
    source = _normalise_source_name(rating)
    if source in KNOWN_SOURCE_NAMES:
        return source

    rating = getattr(token, "rating", None)
    if language == "de" and isinstance(rating, (int, float)):
        return {5: "lexicon", 3: "espeak_fallback", 2: "german_rules"}.get(
            int(rating), "resolved"
        )
    source = _normalise_source_name(rating)
    if source in KNOWN_SOURCE_NAMES:
        return source
    return "resolved" if getattr(token, "phonemes", None) else "unresolved"


def _factory_options(spec: dict[str, Any], fallback_on: bool) -> dict[str, Any]:
    options: dict[str, Any] = {
        "use_spacy": False,
        "use_espeak_fallback": fallback_on,
        "use_goruut_fallback": False,
    }
    options.update(spec.get("g2p_options", {}))
    return options


def _factory_probe(language: str, fallback_on: bool) -> dict[str, Any]:
    """Measure factory construction without importing optional implementations."""
    options = _factory_options(LANGUAGES[language], fallback_on)
    context = BenchmarkContext()
    start_rss = _rss_mib()
    modules_before = set(sys.modules)
    try:
        clear_cache()
        context.update("factory/get_g2p")
        factory_start = time.perf_counter_ns()
        frontend = get_g2p(language, **options)
        factory_construct_ms = (time.perf_counter_ns() - factory_start) / 1_000_000
        after_factory_rss = _rss_mib()
        state_after_factory = _lazy_state(frontend)
        cached_start = time.perf_counter_ns()
        cached = get_g2p(language, **options)
        factory_cache_hit_ms = (time.perf_counter_ns() - cached_start) / 1_000_000
        sentence = LANGUAGES[language]["sentences"][0]

        context.update("factory/direct-first", input_text=sentence)
        started = time.perf_counter_ns()
        direct_first = frontend(sentence)
        direct_first_ms = (time.perf_counter_ns() - started) / 1_000_000
        context.update("factory/direct-warm", input_text=sentence)
        started = time.perf_counter_ns()
        frontend(sentence)
        direct_warm_ms = (time.perf_counter_ns() - started) / 1_000_000
        context.update("factory/prepared-first", input_text=sentence)
        started = time.perf_counter_ns()
        prepared_first = phonemize_prepared(
            sentence,
            language,
            return_ids=False,
            return_phonemes=True,
            g2p=frontend,
            **options,
        )
        prepared_first_ms = (time.perf_counter_ns() - started) / 1_000_000
        context.update("factory/prepared-warm", input_text=sentence)
        started = time.perf_counter_ns()
        phonemize_prepared(
            sentence,
            language,
            return_ids=False,
            return_phonemes=True,
            g2p=frontend,
            **options,
        )
        prepared_warm_ms = (time.perf_counter_ns() - started) / 1_000_000
        modules_after = set(sys.modules)
        return {
            "status": "ok",
            "factory_construct_ms": factory_construct_ms,
            "factory_cache_hit_ms": factory_cache_hit_ms,
            "direct_first_ms": direct_first_ms,
            "direct_warm_ms": direct_warm_ms,
            "prepared_first_ms": prepared_first_ms,
            "prepared_warm_ms": prepared_warm_ms,
            "rss_delta_factory_mib": None
            if start_rss is None or after_factory_rss is None
            else max(0.0, after_factory_rss - start_rss),
            "factory_object_reused": cached is frontend,
            "heavy_backend_created_during_factory": any(
                value.startswith("present:") and key not in {"_lexphon"}
                for key, value in state_after_factory.items()
            ),
            "lazy_state_after_factory": state_after_factory,
            "lazy_state_after_direct": _lazy_state(frontend),
            "new_modules_during_factory": sorted(modules_after - modules_before),
            "output_equal": _normalise_benchmark_output(
                _token_phoneme_string(direct_first)
            )
            == _normalise_benchmark_output(prepared_first.phonemes or ""),
        }
    except (ImportError, ModuleNotFoundError) as exc:
        return {
            "status": "unavailable",
            "error": _error_payload(exc),
            "phase": context.phase,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "error": _error_payload(exc),
            "phase": context.phase,
        }


def _error_payload(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def _classify_failure(exc: BaseException) -> tuple[str, int]:
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "unavailable", 2
    if LexiconNotInstalledError is not None and isinstance(
        exc, LexiconNotInstalledError
    ):
        return "unavailable", 2
    return "failed", 1


def _factory_probe_main(language: str, fallback_on: bool) -> int:
    payload = _factory_probe(language, fallback_on)
    print("__KOKOROG2P_FACTORY_PROBE__" + json.dumps(payload, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


def _run_cold_factory_probe(language: str, fallback_on: bool) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--factory-probe",
        "--language",
        language,
        "--fallback",
        "on" if fallback_on else "off",
    ]
    started = time.perf_counter_ns()
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    process_cold_ms = (time.perf_counter_ns() - started) / 1_000_000
    marker = "__KOKOROG2P_FACTORY_PROBE__"
    payload: dict[str, Any] = {
        "status": "failed",
        "error": {
            "type": "FactoryProbeError",
            "message": "factory probe produced no report",
        },
    }
    for line in result.stdout.splitlines():
        if line.startswith(marker):
            payload = json.loads(line[len(marker) :])
    payload["process_cold_ms"] = process_cold_ms
    payload["probe_exit_code"] = result.returncode
    if result.returncode and "stderr" not in payload:
        payload["stderr"] = result.stderr.strip()
        payload["stdout_tail"] = result.stdout[-1000:]
    return payload


def _factory_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [result for result in results if result.get("status") == "ok"]
    if not successful:
        return results[0] if results else {"status": "unavailable"}
    summary: dict[str, Any] = {"status": "ok"}
    for key in (
        "process_cold_ms",
        "factory_construct_ms",
        "factory_cache_hit_ms",
        "direct_first_ms",
        "direct_warm_ms",
        "prepared_first_ms",
        "prepared_warm_ms",
        "rss_delta_factory_mib",
    ):
        values = [result[key] for result in successful if result.get(key) is not None]
        summary[key] = statistics.median(values) if values else None
    summary["factory_object_reused"] = all(
        result.get("factory_object_reused", False) for result in successful
    )
    summary["heavy_backend_created_during_factory"] = any(
        result.get("heavy_backend_created_during_factory", False)
        for result in successful
    )
    summary["output_equal"] = all(
        result.get("output_equal", False) for result in successful
    )
    summary["lazy_state_after_factory"] = successful[-1].get(
        "lazy_state_after_factory", {}
    )
    summary["lazy_state_after_direct"] = successful[-1].get(
        "lazy_state_after_direct", {}
    )
    return summary


@dataclass
class RunResult:
    output_equal: bool
    source_counts: Counter[str]
    word_count: int
    phoneme_chars: int
    reuse: dict[str, bool]
    components: dict[str, str]


def _run_shape(
    language: str,
    fallback_on: bool,
    recorder: Recorder,
    g2p: Any,
    corpus: Corpus,
    call_shape: str,
    context: BenchmarkContext,
    run_index: int,
) -> RunResult:

    inputs: list[tuple[str, str]] = []
    if call_shape in {"sentences", "both"}:
        inputs.extend(("sentence", sentence) for sentence in corpus.sentences)
    if call_shape in {"paragraph", "both"}:
        inputs.append(("paragraph", corpus.text))
    direct_outputs: dict[str, list[str]] = defaultdict(list)
    prepared_outputs: dict[str, list[str]] = defaultdict(list)
    source_counts: Counter[str] = Counter()
    word_count = 0
    phoneme_chars = 0
    known_components: dict[str, Any] = {}

    with PatchSet(recorder) as patches:
        _instrument_frontend(patches, g2p)
        _instrument_components(patches, g2p, known_components)
        _instrument_prepared_pipeline(patches)
        before = _snapshot_components(g2p)
        for input_index, (shape, text) in enumerate(inputs, start=1):
            station_suffix = f"/{shape}"
            context.update(
                f"direct/{shape}",
                run_index=run_index,
                sentence_index=input_index if shape == "sentence" else None,
                input_text=text,
            )
            tokens = recorder.call(
                "direct" + station_suffix, g2p, text, detail=text[:120]
            )
            direct_output = _token_phoneme_string(tokens)
            direct_outputs[shape].append(direct_output)
            word_count += _count_word_tokens(tokens)
            phoneme_chars += len(direct_output)
            source_counts.update(
                _source_for_token(token, language)
                for token in tokens
                if not getattr(token, "is_punctuation", False)
            )
            _instrument_components(patches, g2p, known_components)
            context.update(
                f"prepared/{shape}",
                run_index=run_index,
                sentence_index=input_index if shape == "sentence" else None,
                input_text=text,
            )
            result = recorder.call(
                "prepared" + station_suffix,
                phonemize_prepared,
                text,
                language,
                return_ids=False,
                return_phonemes=True,
                g2p=g2p,
                use_spacy=False,
                use_espeak_fallback=fallback_on,
                detail=text[:120],
            )
            prepared_outputs[shape].append(result.phonemes or "")
            _instrument_components(patches, g2p, known_components)
        after = _snapshot_components(g2p)
    reuse = _merge_reuse(before, after)
    components = {
        path: type(value).__name__ for path, value in sorted(known_components.items())
    }
    output_equal = all(
        _normalise_benchmark_output(direct) == _normalise_benchmark_output(prepared)
        for shape in direct_outputs
        for direct, prepared in zip(
            direct_outputs[shape], prepared_outputs[shape], strict=True
        )
    )
    return RunResult(
        output_equal, source_counts, word_count, phoneme_chars, reuse, components
    )


def _instrument_prepared_pipeline(patches: PatchSet) -> None:
    from kokorog2p import pipeline_api

    for function_name, station in PREPARED_BOUNDARIES.items():
        patches.patch_module_function(pipeline_api, function_name, station)


def _run_once(
    language: str,
    fallback_on: bool,
    recorder: Recorder,
    subprocess_probe: SubprocessProbe,
    corpus: Corpus | None = None,
    call_shape: str = "sentences",
    context: BenchmarkContext | None = None,
    run_index: int = 1,
) -> RunResult:
    del subprocess_probe
    spec = LANGUAGES[language]
    corpus = corpus or get_corpus(language)
    context = context or BenchmarkContext()
    clear_cache()
    options = _factory_options(spec, fallback_on)
    context.update("factory/get_g2p", run_index=run_index)
    g2p = recorder.call(
        "factory/get_g2p", get_g2p, language, detail=language, **options
    )
    return _run_shape(
        language, fallback_on, recorder, g2p, corpus, call_shape, context, run_index
    )


def _backend_summary(components: dict[str, str], subprocess_count: int) -> str:
    if subprocess_count:
        return "subprocess"
    if any("espeak" in name.lower() for name in components.values()):
        return "native/in-process"
    return "not observed"


def _station_metrics(name: str, values: list[float], corpus: Corpus) -> dict[str, Any]:
    summary = _stats(values)
    input_chars = (
        corpus.input_chars
        if name.endswith("/paragraph")
        else sum(map(len, corpus.sentences))
    )
    input_bytes = (
        len(corpus.text.encode("utf-8"))
        if name.endswith("/paragraph")
        else sum(len(sentence.encode("utf-8")) for sentence in corpus.sentences)
    )
    total_input_chars = input_chars * int(summary["calls"])
    total_input_bytes = input_bytes * int(summary["calls"])
    total_ms = float(summary["total_ms"])
    summary.update(
        {
            "input_chars": total_input_chars,
            "input_utf8_bytes": total_input_bytes,
            "ms_per_1k_input_chars": (total_ms * 1000 / total_input_chars)
            if total_input_chars
            else 0.0,
            "input_chars_per_second": (total_input_chars * 1000 / total_ms)
            if total_ms
            else 0.0,
        }
    )
    return summary


def _json_payload(
    language: str,
    fallback_on: bool,
    runs: int,
    recorder: Recorder,
    results: list[RunResult],
    subprocess_probe: SubprocessProbe,
    factory_results: list[dict[str, Any]],
    corpus: Corpus | None = None,
    call_shape: str = "sentences",
) -> dict[str, Any]:
    corpus = corpus or get_corpus(language)
    source_counts: Counter[str] = Counter()
    for result in results:
        source_counts.update(result.source_counts)
    stations = {
        name: _station_metrics(name, values, corpus)
        for name, values in recorder.values_ms.items()
    }
    output_equal = all(result.output_equal for result in results)
    sentence_chars = sum(map(len, corpus.sentences))
    sentence_bytes = sum(len(sentence.encode("utf-8")) for sentence in corpus.sentences)
    chars_per_run = (
        corpus.input_chars
        if call_shape == "paragraph"
        else sentence_chars
        if call_shape == "sentences"
        else corpus.input_chars + sentence_chars
    )
    bytes_per_run = (
        corpus.input_utf8_bytes
        if call_shape == "paragraph"
        else sentence_bytes
        if call_shape == "sentences"
        else corpus.input_utf8_bytes + sentence_bytes
    )
    total_direct_ms = sum(
        sum(values)
        for name, values in recorder.values_ms.items()
        if name.startswith("direct/")
    )
    total_word_count = sum(result.word_count for result in results)
    total_phoneme_chars = sum(result.phoneme_chars for result in results)
    total_input_chars = chars_per_run * runs
    input_chars_per_second = (
        total_input_chars * 1000 / total_direct_ms if total_direct_ms else 0.0
    )
    normalized = {
        "ms_per_1k_input_chars": total_direct_ms * 1000 / total_input_chars
        if total_input_chars
        else 0.0,
        "input_chars_per_second": input_chars_per_second,
        "word_like_tokens_per_second": total_word_count * 1000 / total_direct_ms
        if total_direct_ms
        else 0.0,
        "phoneme_chars_per_second": total_phoneme_chars * 1000 / total_direct_ms
        if total_direct_ms
        else 0.0,
    }
    return {
        "schema_version": 2,
        "status": "ok" if output_equal else "failed",
        "language": language,
        "label": LANGUAGES[language]["label"],
        "fallback": fallback_on,
        "runs": runs,
        "corpus": {
            "profile": corpus.name,
            "base_sentence_count": corpus.base_sentence_count,
            "sentence_count": len(corpus.sentences),
            "input_chars": corpus.input_chars,
            "input_utf8_bytes": corpus.input_utf8_bytes,
            "call_shape": call_shape,
        },
        "stations": stations,
        "sources": dict(source_counts),
        "word_like_frontend_tokens": total_word_count,
        "workload": {
            "input_chars": total_input_chars,
            "input_utf8_bytes": bytes_per_run * runs,
            "sentence_count": len(corpus.sentences),
            "word_like_frontend_tokens": total_word_count,
            "phoneme_chars": total_phoneme_chars,
        },
        "normalized": normalized,
        "phoneme_chars": total_phoneme_chars,
        "espeak_subprocess_count": subprocess_probe.count,
        "output_equal": output_equal,
        "object_reuse": {
            key: all(result.reuse.get(key, False) for result in results)
            for key in sorted({key for result in results for key in result.reuse})
        },
        "components": {
            key: value for result in results for key, value in result.components.items()
        },
        "factory": factory_results,
        "factory_summary": _factory_summary(factory_results),
    }


def _failure_payload(
    language: str,
    fallback_on: bool,
    runs: int,
    corpus: Corpus,
    context: BenchmarkContext,
    exc: BaseException,
    recorder: Recorder,
    factory_results: list[dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    status, code = _classify_failure(exc)
    payload: dict[str, Any] = {
        "schema_version": 2,
        "status": status,
        "language": language,
        "label": LANGUAGES[language]["label"],
        "fallback": fallback_on,
        "runs_requested": runs,
        "corpus": {
            "profile": corpus.name,
            "base_sentence_count": corpus.base_sentence_count,
            "sentence_count": len(corpus.sentences),
            "input_chars": corpus.input_chars,
            "input_utf8_bytes": corpus.input_utf8_bytes,
        },
        "phase": context.phase,
        "run_index": context.run_index,
        "sentence_index": context.sentence_index,
        "input_preview": (context.input_text or "")[:240],
        "error": _error_payload(exc),
        "stations": {
            name: _station_metrics(name, values, corpus)
            for name, values in recorder.values_ms.items()
        },
    }
    if factory_results:
        payload["factory"] = factory_results
        payload["factory_summary"] = _factory_summary(factory_results)
    return payload, code


def _print_table(recorder: Recorder) -> None:
    print()
    print(
        f"{'station':<38} {'calls':>8} {'total ms':>14} "
        f"{'median ms':>14} {'p95 ms':>12}"
    )
    print("-" * 96)
    for station in sorted(recorder.values_ms):
        summary = _stats(recorder.values_ms[station])
        print(
            f"{station:<38} {summary['calls']:>8d} "
            f"{summary['total_ms']:>14.3f} "
            f"{summary['median_ms']:>14.3f} {summary['p95_ms']:>12.3f}"
        )


def _print_slowest(recorder: Recorder, limit: int) -> None:
    candidates = [
        (elapsed, station, detail)
        for station, details in recorder.details.items()
        if "fallback" in station
        or "backend" in station
        or "phonemize_word" in station
        or station == "espeak/subprocess"
        for elapsed, detail in details
    ]
    candidates.sort(reverse=True)
    print("slowest fallback/backend calls:")
    if not candidates:
        print("  (none observed)")
    for elapsed, station, detail in candidates[:limit]:
        print(f"  {elapsed:10.3f} ms  {station:<34} {detail}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser(default_language: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile kokorog2p G2P stations for one supported language."
    )
    parser.add_argument(
        "--language", choices=sorted(LANGUAGES), default=default_language or "en-us"
    )
    parser.add_argument("--fallback", choices=("on", "off"), default="on")
    parser.add_argument(
        "--runs", type=int, default=1, help="Number of object-cold benchmark runs."
    )
    parser.add_argument("--slowest", type=int, default=10)
    parser.add_argument(
        "--json", type=Path, help="Optional path for machine-readable results."
    )
    parser.add_argument("--corpus", choices=("smoke", "scaled"), default="smoke")
    parser.add_argument("--target-chars", type=int, default=2000)
    parser.add_argument(
        "--call-shape", choices=("sentences", "paragraph", "both"), default="sentences"
    )
    parser.add_argument("--factory-probe", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None, *, default_language: str | None = None) -> int:
    args = build_parser(default_language).parse_args(argv)
    if args.factory_probe:
        return _factory_probe_main(args.language, args.fallback == "on")
    if args.runs < 1:
        raise SystemExit("--runs must be at least one")
    if args.slowest < 0:
        raise SystemExit("--slowest must be non-negative")
    language = args.language
    fallback_on = args.fallback == "on"
    corpus = get_corpus(language, profile=args.corpus, target_chars=args.target_chars)
    recorder = Recorder()
    results: list[RunResult] = []
    factory_results: list[dict[str, Any]] = []
    context = BenchmarkContext()
    print(f"{LANGUAGES[language]['label']} G2P station benchmark")
    print(f"  corpus profile: {corpus.name}")
    print(f"  base sentences: {corpus.base_sentence_count}")
    print(f"  expanded sentences: {len(corpus.sentences)}")
    print(f"  input chars: {corpus.input_chars}")
    print(f"  input UTF-8 bytes: {corpus.input_utf8_bytes}")
    print(f"  call shape: {args.call_shape}")
    print(f"  fallback: {args.fallback}")
    print("  backend: native/default")
    print(f"  runs: {args.runs}")

    exit_code = 0
    try:
        with SubprocessProbe(recorder) as subprocess_probe:
            for run_index in range(1, args.runs + 1):
                context.update("factory/get_g2p", run_index=run_index)
                results.append(
                    _run_once(
                        language,
                        fallback_on,
                        recorder,
                        subprocess_probe,
                        corpus,
                        args.call_shape,
                        context,
                        run_index,
                    )
                )
                factory_results.append(_run_cold_factory_probe(language, fallback_on))
    except BaseException as exc:
        status, exit_code = _classify_failure(exc)
        del status
        payload, _ = _failure_payload(
            language,
            fallback_on,
            args.runs,
            corpus,
            context,
            exc,
            recorder,
            factory_results,
        )
        print(
            f"ERROR while benchmarking {language!r}: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        if args.json:
            _write_json(args.json, payload)
        return exit_code

    payload = _json_payload(
        language,
        fallback_on,
        args.runs,
        recorder,
        results,
        subprocess_probe,
        factory_results,
        corpus,
        args.call_shape,
    )
    equal = payload["output_equal"]
    print(f"  word-like frontend tokens: {payload['word_like_frontend_tokens']}")
    print(f"  phoneme chars: {payload['phoneme_chars']}")
    _print_table(recorder)
    print("\nsources:")
    for source, count in sorted(payload["sources"].items()):
        print(f"  {source:<24}: {count}")
    components = payload["components"]
    print(
        "espeak/effective_backend:",
        _backend_summary(components, subprocess_probe.count),
    )
    print("espeak/subprocess_count:", subprocess_probe.count)
    print("object reuse:", payload["object_reuse"])
    print("direct/prepared output equal:", equal)
    _print_slowest(recorder, args.slowest)
    factory = payload["factory_summary"]
    print("\nfactory summary:")
    if factory.get("status") != "ok":
        print(f"  status: {factory.get('status')}: {factory.get('error', '')}")
    else:
        print(
            "  language process_cold_ms factory_construct_ms "
            "factory_cache_hit_ms direct_first_ms direct_warm_ms "
            "prepared_first_ms prepared_warm_ms"
        )
        print(
            f"  {language:<8} "
            f"{factory['process_cold_ms']:>15.3f} "
            f"{factory['factory_construct_ms']:>19.3f} "
            f"{factory['factory_cache_hit_ms']:>19.3f} "
            f"{factory['direct_first_ms']:>15.3f} "
            f"{factory['direct_warm_ms']:>14.3f} "
            f"{factory['prepared_first_ms']:>17.3f} "
            f"{factory['prepared_warm_ms']:>16.3f}"
        )
    if not equal:
        exit_code = 3
    if args.json:
        _write_json(args.json, payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
