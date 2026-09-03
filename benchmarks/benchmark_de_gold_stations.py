#!/usr/bin/env python3
"""Diagnostic benchmark for the normalized German Gold KokoroG2P workload."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kokorog2p import clear_cache, get_g2p, phonemize_prepared

_SENTENCE_1 = "Zum vierzehnten Mai zweitausendsechsundzwanzig um achtzehn Uhr zwanzig "
_SENTENCE_1 += "ist das Abendessen geplant."
_SENTENCE_2 = "Für den Auflauf brauchen wir eins Komma fünf Kilogramm Kartoffeln, "
_SENTENCE_2 += "fünfhundert Gramm Quark, zwei Eier, ein Liter Milch und gegebenenfalls "
_SENTENCE_2 += "drei Zentimeter mehr Backpapier."
_SENTENCE_3 = 'Professor Klein sagt: "Bitte stelle die Form auf die zweite Schiene, '
_SENTENCE_3 += "backe alles für fünfundvierzig Minuten und lass es danach eine Minute "
_SENTENCE_3 += 'oder auch zwei Minuten ruhen."'
SENTENCES = (
    _SENTENCE_1,
    _SENTENCE_2,
    _SENTENCE_3,
    "Die Kosten liegen bei zirka zwölf Euro achtzig Cent zuzüglich Pfand.",
)
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*")


@dataclass
class TimerBucket:
    calls: int = 0
    total_ns: int = 0
    max_ns: int = 0
    samples_ns: list[int] = field(default_factory=list)

    def add(self, elapsed_ns: int) -> None:
        self.calls += 1
        self.total_ns += elapsed_ns
        self.max_ns = max(self.max_ns, elapsed_ns)
        self.samples_ns.append(elapsed_ns)

    def summary(self) -> dict[str, Any]:
        values = sorted(self.samples_ns)
        p50 = statistics.median(values) if values else 0
        p95 = (
            values[min(len(values) - 1, int((len(values) - 1) * 0.95))] if values else 0
        )
        return {
            "calls": self.calls,
            "total_ms": self.total_ns / 1_000_000,
            "p50_ms": p50 / 1_000_000,
            "p95_ms": p95 / 1_000_000,
            "max_ms": self.max_ns / 1_000_000,
        }


@dataclass
class Probe:
    timers: dict[str, TimerBucket] = field(
        default_factory=lambda: defaultdict(TimerBucket)
    )
    lexicon_hits: int = 0
    lexicon_misses: int = 0
    fallback_hits: int = 0
    fallback_misses: int = 0
    rules_nonempty: int = 0
    espeak_processes: int = 0
    espeak_process_ns: int = 0
    source_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    source_records: list[dict[str, Any]] = field(default_factory=list)
    slow_tokens: list[tuple[int, str, str]] = field(default_factory=list)

    def time_call(
        self, key: str, token: str, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        started = time.perf_counter_ns()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = time.perf_counter_ns() - started
            self.timers[key].add(elapsed)
            if token:
                self.slow_tokens.append((elapsed, key, token))


def _looks_like_espeak_command(cmd: Any) -> bool:
    if isinstance(cmd, (list, tuple)) and cmd:
        first = str(cmd[0]).lower()
    else:
        first = str(cmd).split(maxsplit=1)[0].lower()
    return "espeak" in Path(first).name.lower()


def _timed_method(
    probe: Probe,
    key: str,
    original: Callable[..., Any],
    token_getter: Callable[[tuple[Any, ...], dict[str, Any]], str] | None = None,
) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        token = token_getter(args, kwargs) if token_getter else ""
        return probe.time_call(key, token, original, *args, **kwargs)

    return wrapper


@contextlib.contextmanager
def instrument(g2p: Any, probe: Probe) -> Iterator[None]:  # noqa: C901
    """Instrument implementation boundaries without changing production code."""
    from kokorog2p import pipeline_api

    restorers: list[Callable[[], None]] = []

    original_run = subprocess.run

    def run_wrapper(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0] if args else kwargs.get("args")
        if not _looks_like_espeak_command(cmd):
            return original_run(*args, **kwargs)
        started = time.perf_counter_ns()
        try:
            return original_run(*args, **kwargs)
        finally:
            elapsed = time.perf_counter_ns() - started
            probe.espeak_processes += 1
            probe.espeak_process_ns += elapsed
            probe.timers["espeak/subprocess.run"].add(elapsed)

    subprocess.run = run_wrapper  # type: ignore[assignment]
    restorers.append(lambda: setattr(subprocess, "run", original_run))

    lexicon = getattr(g2p, "_lexicon", None)
    if lexicon is not None and hasattr(type(lexicon), "lookup"):
        lexicon_cls = type(lexicon)
        lexicon_original = lexicon_cls.lookup

        def lex_lookup(self: Any, word: str, *args: Any, **kwargs: Any) -> Any:
            if self is not lexicon:
                return lexicon_original(self, word, *args, **kwargs)
            started = time.perf_counter_ns()
            try:
                result = lexicon_original(self, word, *args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - started
                probe.timers["gold/lookup"].add(elapsed)
                probe.slow_tokens.append((elapsed, "gold/lookup", word))
            if result:
                probe.lexicon_hits += 1
            else:
                probe.lexicon_misses += 1
            return result

        lexicon_cls.lookup = lex_lookup
        restorers.append(
            lambda cls=lexicon_cls, original=lexicon_original: setattr(
                cls, "lookup", original
            )
        )

    fallback = getattr(g2p, "_fallback", None)
    if callable(fallback):
        fallback_cls = type(fallback)
        fallback_original = fallback_cls.__call__

        def fallback_call(self: Any, word: str, *args: Any, **kwargs: Any) -> Any:
            if self is not fallback:
                return fallback_original(self, word, *args, **kwargs)
            started = time.perf_counter_ns()
            try:
                result = fallback_original(self, word, *args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - started
                probe.timers["german/fallback"].add(elapsed)
                probe.slow_tokens.append((elapsed, "fallback", word))
            if result:
                probe.fallback_hits += 1
            else:
                probe.fallback_misses += 1
            return result

        fallback_cls.__call__ = fallback_call
        restorers.append(
            lambda cls=fallback_cls, original=fallback_original: setattr(
                cls, "__call__", original
            )
        )
        fallback_many_original = getattr(fallback_cls, "phonemize_many", None)
        if fallback_many_original is not None:

            def fallback_many(self: Any, words: Any) -> Any:
                if self is not fallback:
                    return fallback_many_original(self, words)
                started = time.perf_counter_ns()
                try:
                    return fallback_many_original(self, words)
                finally:
                    elapsed = time.perf_counter_ns() - started
                    probe.timers["german/fallback"].add(elapsed)
                    probe.slow_tokens.append((elapsed, "fallback", "<batch>"))

            fallback_cls.phonemize_many = fallback_many
            restorers.append(
                lambda cls=fallback_cls, original=fallback_many_original: setattr(
                    cls, "phonemize_many", original
                )
            )

    g2p_cls = type(g2p)
    if hasattr(g2p_cls, "_word_to_phonemes"):
        rules_original = g2p_cls._word_to_phonemes

        def rules_call(self: Any, word: str, *args: Any, **kwargs: Any) -> Any:
            if self is not g2p:
                return rules_original(self, word, *args, **kwargs)
            started = time.perf_counter_ns()
            try:
                result = rules_original(self, word, *args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - started
                probe.timers["german/rules"].add(elapsed)
                probe.slow_tokens.append((elapsed, "rules", word))
            if result:
                probe.rules_nonempty += 1
            return result

        g2p_cls._word_to_phonemes = rules_call
        restorers.append(
            lambda cls=g2p_cls, original=rules_original: setattr(
                cls, "_word_to_phonemes", original
            )
        )

    # These wrappers are diagnostic only. They expose prepared-adapter boundaries
    # while retaining its exact call order and arguments.
    prepared_boundaries = {
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
    for name, key in prepared_boundaries.items():
        original = getattr(pipeline_api, name, None)
        if original is None:
            continue
        wrapped = _timed_method(probe, key, original)
        setattr(pipeline_api, name, wrapped)
        restorers.append(
            lambda name=name, original=original: setattr(pipeline_api, name, original)
        )

    try:
        yield
    finally:
        for restore in reversed(restorers):
            restore()


def effective_backend_info(g2p: Any) -> dict[str, Any]:
    """Inspect existing backend state without triggering lazy initialization."""
    fallback = getattr(g2p, "_fallback", None)
    if fallback is None:
        return {
            "fallback": None,
            "backend": None,
            "wrapper": None,
            "implementation": "unused",
            "native_error": None,
            "native_error_type": None,
        }
    backend = getattr(fallback, "_backend", None)
    wrapper = getattr(backend, "_phonemizer", None) if backend is not None else None
    native_error = (
        getattr(backend, "native_error", None) if backend is not None else None
    )
    return {
        "fallback": type(fallback).__name__,
        "backend": type(backend).__name__ if backend is not None else None,
        "wrapper": type(wrapper).__name__ if wrapper is not None else None,
        "implementation": (
            "native"
            if wrapper is not None and type(wrapper).__name__ == "Phonemizer"
            else "cli"
            if wrapper is not None
            else "uninitialized"
        ),
        "native_error": native_error,
        "native_error_type": type(native_error).__name__ if native_error else None,
    }


def object_identities(g2p: Any) -> dict[str, int | None]:
    fallback = getattr(g2p, "_fallback", None)
    backend = getattr(fallback, "_backend", None) if fallback is not None else None
    wrapper = getattr(backend, "_phonemizer", None) if backend is not None else None
    return {
        "GermanG2P": id(g2p),
        "GermanLexicon": id(lexicon)
        if (lexicon := getattr(g2p, "_lexicon", None)) is not None
        else None,
        "fallback": id(fallback) if fallback is not None else None,
        "EspeakBackend": id(backend) if backend is not None else None,
        "wrapper": id(wrapper) if wrapper is not None else None,
    }


def phoneme_text_from_tokens(tokens: Any) -> str:
    return "".join(
        (getattr(token, "phonemes", None) or "")
        + (getattr(token, "whitespace", None) or "")
        for token in tokens
    ).strip()


def corpus_words() -> list[str]:
    return [word for sentence in SENTENCES for word in WORD_RE.findall(sentence)]


def timed_ns(fn: Callable[[], Any]) -> tuple[int, Any]:
    started = time.perf_counter_ns()
    result = fn()
    return time.perf_counter_ns() - started, result


def _token_rating(token: Any) -> int:
    getter = getattr(token, "get", None)
    if callable(getter):
        value = getter("rating", 0)
        if value:
            return int(value)
    meta = getattr(token, "meta", None)
    if isinstance(meta, dict):
        return int(meta.get("rating", 0) or 0)
    return 0


def record_sources(probe: Probe, tokens: Any) -> None:
    for token in tokens:
        word = str(getattr(token, "text", ""))
        if not WORD_RE.fullmatch(word):
            continue
        rating = _token_rating(token)
        source = {5: "lexicon", 3: "espeak_fallback", 2: "german_rules"}.get(
            rating, "unresolved"
        )
        probe.source_counts[source] += 1
        probe.source_records.append(
            {
                "token": word,
                "source": source,
                "phonemes": getattr(token, "phonemes", None),
            }
        )


def probe_record(probe: Probe) -> dict[str, Any]:
    return {
        "timers": {
            name: bucket.summary() for name, bucket in sorted(probe.timers.items())
        },
        "lexicon_hits": probe.lexicon_hits,
        "lexicon_misses": probe.lexicon_misses,
        "fallback_hits": probe.fallback_hits,
        "fallback_misses": probe.fallback_misses,
        "rules_nonempty": probe.rules_nonempty,
        "espeak_processes": probe.espeak_processes,
        "espeak_process_ms": probe.espeak_process_ns / 1_000_000,
        "source_counts": dict(probe.source_counts),
        "source_records": probe.source_records,
        "slowest": [
            {"ms": ns / 1_000_000, "station": station, "token": token}
            for ns, station, token in sorted(probe.slow_tokens, reverse=True)[:15]
        ],
    }


def one_run(use_espeak_fallback: bool) -> dict[str, Any]:
    # Each requested run is object-cold. The same object is reused for all sentences.
    clear_cache()
    record: dict[str, Any] = {
        "fallback_enabled": use_espeak_fallback,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "execution": {
            "process_cold": (
                "fresh benchmark process includes imports and interpreter startup"
            ),
            "object_cold": "get_g2p followed by first direct frontend call",
            "warm": "same G2P object reused by prepared frontend call",
        },
        "corpus": {
            "sentences": len(SENTENCES),
            "characters": sum(len(s) for s in SENTENCES),
            "words": len(corpus_words()),
            "unique_casefold_words": len({w.casefold() for w in corpus_words()}),
        },
    }

    create_ns, g2p = timed_ns(
        lambda: get_g2p(
            "de",
            lexicons=("gold",),
            use_spacy=False,
            use_espeak_fallback=use_espeak_fallback,
        )
    )
    record["get_g2p_ms"] = create_ns / 1_000_000
    record["g2p_type"] = type(g2p).__name__
    record["construction"] = {
        "factory/get_g2p": {"calls": 1, "total_ms": record["get_g2p_ms"]},
        "lexicon/open_or_acquire": {"calls": 1, "total_ms": record["get_g2p_ms"]},
        "fallback/object_create": {
            "calls": 1 if getattr(g2p, "_fallback", None) else 0
        },
        "fallback/backend_create": {"calls": 0, "total_ms": 0.0},
        "espeak/wrapper_resolve": {"calls": 0, "total_ms": 0.0},
        "espeak/native_initialize": {"calls": 0, "total_ms": 0.0},
        "espeak/set_voice": {"calls": 0, "total_ms": 0.0},
    }
    record["object_identities_before"] = object_identities(g2p)

    lexicon = getattr(g2p, "_lexicon", None)
    words = corpus_words()
    if lexicon is not None and hasattr(lexicon, "lookup"):
        raw_ns, raw_results = timed_ns(
            lambda: [lexicon.lookup(word, None) for word in words]
        )
        record["raw_gold_lookup_ms"] = raw_ns / 1_000_000
        record["raw_gold_hits"] = sum(bool(value) for value in raw_results)
        record["raw_gold_misses"] = sum(not bool(value) for value in raw_results)

    direct_probe = Probe()
    with instrument(g2p, direct_probe):
        direct_ns, direct_tokens = timed_ns(
            lambda: [g2p(sentence) for sentence in SENTENCES]
        )
    direct_outputs = [phoneme_text_from_tokens(tokens) for tokens in direct_tokens]
    for tokens in direct_tokens:
        record_sources(direct_probe, tokens)
    record["direct_ms"] = direct_ns / 1_000_000
    record["direct_probe"] = probe_record(direct_probe)
    record["object_identities_after_direct"] = object_identities(g2p)
    record["backend_after_direct"] = effective_backend_info(g2p)

    prepared_probe = Probe()
    with instrument(g2p, prepared_probe):
        prepared_ns, prepared_results = timed_ns(
            lambda: [
                phonemize_prepared(
                    sentence,
                    language="de",
                    g2p=g2p,
                    use_spacy=False,
                    return_ids=False,
                )
                for sentence in SENTENCES
            ]
        )
    prepared_outputs = [result.phonemes or "" for result in prepared_results]
    for result in prepared_results:
        record_sources(prepared_probe, result.tokens)
    record["prepared_ms"] = prepared_ns / 1_000_000
    record["prepared_probe"] = probe_record(prepared_probe)
    record["object_identities_after_prepared"] = object_identities(g2p)
    record["backend_after_prepared"] = effective_backend_info(g2p)
    record["direct_output_sha256"] = hashlib.sha256(
        "\n".join(direct_outputs).encode("utf-8")
    ).hexdigest()
    record["prepared_output_sha256"] = hashlib.sha256(
        "\n".join(prepared_outputs).encode("utf-8")
    ).hexdigest()
    record["direct_prepared_equal"] = direct_outputs == prepared_outputs
    identity_snapshots = (
        record["object_identities_before"],
        record["object_identities_after_direct"],
        record["object_identities_after_prepared"],
    )
    record["object_reuse"] = {
        key: len(
            {
                snapshot[key]
                for snapshot in identity_snapshots
                if snapshot[key] is not None
            }
        )
        <= 1
        for key in (
            "GermanG2P",
            "GermanLexicon",
            "fallback",
            "EspeakBackend",
            "wrapper",
        )
    }

    close = getattr(g2p, "close", None)
    if callable(close):
        close()
    return record


def mean_field(records: list[dict[str, Any]], key: str) -> float:
    return statistics.mean(float(record.get(key, 0.0)) for record in records)


def print_human(records: list[dict[str, Any]]) -> None:
    first = records[0]
    print("German Gold G2P benchmark")
    print(
        f"  corpus: {first['corpus']['sentences']} sentences / "
        f"{first['corpus']['words']} words"
    )
    print(f"  fallback: {'on' if first['fallback_enabled'] else 'off'}")
    print(f"  backend: {first['backend_after_prepared']['implementation']}")
    print(f"  runs: {len(records)}")
    print()
    print(f"{'station':34s} {'calls':>7s} {'total ms':>14s} {'p95 ms':>12s}")
    print("-" * 72)
    print(f"{'factory/get_g2p':34s} {1:7d} {mean_field(records, 'get_g2p_ms'):14.3f}")
    if "raw_gold_lookup_ms" in first:
        gold_ms = mean_field(records, "raw_gold_lookup_ms")
        print(f"{'gold/lookup':34s} {len(corpus_words()):7d} {gold_ms:14.3f}")
    for label in ("direct_probe", "prepared_probe"):
        for name, stat in sorted(first[label]["timers"].items()):
            print(
                f"{name:34s} {stat['calls']:7d} {stat['total_ms']:14.3f} "
                f"{stat['p95_ms']:12.3f}"
            )
    direct_ms = mean_field(records, "direct_ms")
    print(f"{'direct/frontend':34s} {len(SENTENCES):7d} {direct_ms:14.3f}")
    prepared_ms = mean_field(records, "prepared_ms")
    print(f"{'prepared/total':34s} {len(SENTENCES):7d} {prepared_ms:14.3f}")
    print()
    probe = first["direct_probe"]
    print("sources:")
    for source in ("lexicon", "espeak_fallback", "german_rules", "unresolved"):
        print(f"  {source:18s}: {probe['source_counts'].get(source, 0)}")
    implementation = first["backend_after_prepared"]["implementation"]
    print(f"espeak/effective_backend: {implementation}")
    print(f"espeak/subprocess_count: {probe['espeak_processes']}")
    print("object reuse:", first["object_reuse"])
    print("direct/prepared output equal:", first["direct_prepared_equal"])
    print("slowest fallback tokens:")
    for item in probe["slowest"]:
        if item["station"] == "fallback":
            print(f"  {item['token']}: {item['ms']:.3f} ms")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fallback", choices=("on", "off"), default="on")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")

    records = [one_run(args.fallback == "on") for _ in range(args.runs)]
    print_human(records)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
