#!/usr/bin/env python3
"""Measure the end-to-end automatic mixed-language phonemization API."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

import kokorog2p
from kokorog2p import clear_cache, phonemize_to_result
from kokorog2p.language_codes import normalize_language_code

CASES = {
    "all-default": "Die Diskussion wird morgen fortgesetzt.",
    "single-foreign": "Du kannst das File öffnen.",
    "mixed-example": (
        "Die Manpowerdiskussion wird gecancelt, du kannst das File downloaden."
    ),
    "repeated-mixed": (
        "File downloaden. File downloaden. Die Manpowerdiskussion wird gecancelt."
    ),
}

CONFIGS = {
    "routing-off-spacy-false-fallback-on": {
        "mode": "off",
        "use_spacy": False,
        "use_espeak_fallback": True,
    },
    "routing-auto-spacy-false-fallback-on": {
        "mode": "auto",
        "use_spacy": False,
        "use_espeak_fallback": True,
    },
    "routing-auto-spacy-none-fallback-on": {
        "mode": "auto",
        "use_spacy": None,
        "use_espeak_fallback": True,
    },
    "routing-auto-spacy-false-fallback-off": {
        "mode": "auto",
        "use_spacy": False,
        "use_espeak_fallback": False,
    },
}

DEFAULT_LANGUAGE = "de-de"
ROUTING_LANGUAGES = ("de-de", "en-us")
STATIONS = (
    "total/phonemize_to_result",
    "factory/default",
    "factory/foreign/en-us",
    "prepared/prepare_span_text",
    "prepared/default_frontend_call",
    "routing/route_languages",
    "routing/decompose_de_en",
    "routing/evidence/de-de",
    "routing/evidence/en-us",
    "routed/frontend_call/de-de",
    "routed/frontend_call/en-us",
    "lexphon/lookup_many",
    "lexphon/provider_batch",
    "spacy/load_model",
    "espeak/subprocess",
)

EXPECTED_ROUTE_SIGNATURE = (
    ("Die", "de-de", "whole-token", 0, 3),
    ("Manpower", "en-us", "compound-root", 4, 12),
    ("diskussion", "de-de", "compound-root", 12, 22),
    ("wird", "de-de", "whole-token", 23, 27),
    ("ge", "de-de", "affix", 28, 30),
    ("cancel", "en-us", "stem", 30, 36),
    ("t", "de-de", "affix", 36, 37),
    ("du", "de-de", "whole-token", 39, 41),
    ("kannst", "de-de", "whole-token", 42, 48),
    ("das", "de-de", "whole-token", 49, 52),
    ("File", "en-us", "whole-token", 53, 57),
    ("download", "en-us", "stem", 58, 66),
    ("en", "de-de", "affix", 66, 68),
)

_FACTORY_OBJECTS: dict[int, object] = {}


class Recorder:
    def __init__(self) -> None:
        self.stations_ms: dict[str, float] = {station: 0.0 for station in STATIONS}
        self.counts: Counter[str] = Counter()
        self.evidence_calls: Counter[str] = Counter()
        self.frontend_calls: Counter[str] = Counter()
        self.factory_calls: Counter[str] = Counter()
        self.route_signature: tuple[tuple[Any, ...], ...] = ()

    def add_time(self, station: str, elapsed_ns: int) -> None:
        self.stations_ms[station] += elapsed_ns / 1_000_000

    def add_factory(self, language: str, elapsed_ns: int, result: object) -> None:
        canonical = normalize_language_code(language)
        station = (
            "factory/default"
            if canonical == DEFAULT_LANGUAGE
            else f"factory/foreign/{canonical}"
        )
        self.add_time(station, elapsed_ns)
        self.counts["factory calls"] += 1
        if id(result) not in _FACTORY_OBJECTS:
            _FACTORY_OBJECTS[id(result)] = result
            factory_key = "default" if canonical == DEFAULT_LANGUAGE else canonical
            self.factory_calls[factory_key] += 1
            self.counts[
                "default frontend constructions"
                if canonical == DEFAULT_LANGUAGE
                else "foreign frontend constructions"
            ] += 1

    def as_dict(
        self, *, case: str, config: str, state: str, total_ms: float
    ) -> dict[str, Any]:
        return {
            "case": case,
            "config": config,
            "state": state,
            "total_ms": total_ms,
            "stations_ms": dict(self.stations_ms),
            "counts": {
                "factory": dict(self.factory_calls),
                "spacy_load_count": self.counts["spaCy model load count"],
                "espeak_subprocess_count": self.counts["eSpeak subprocess count"],
                "evidence_calls": dict(self.evidence_calls),
                "frontend_calls": dict(self.frontend_calls),
                "default_whole_text_frontend_calls": self.counts[
                    "default whole-text frontend calls"
                ],
                "routed_frontend_calls": dict(self.fronts_by_language()),
                "lexphon_lookup_many": self.counts["Lexphon lookup_many calls"],
                "lexphon_provider_batch": self.counts["Lexphon provider batch calls"],
            },
            "route_signature": list(self.route_signature),
        }

    def fronts_by_language(self) -> Counter[str]:
        return Counter(
            {
                language: count
                for language, count in self.frontend_calls.items()
                if language != DEFAULT_LANGUAGE
            }
        )


@contextmanager
def instrument(recorder: Recorder) -> Iterator[None]:
    with ExitStack() as stack:
        original_factory = kokorog2p.get_g2p

        def factory(language: str, **kwargs: Any) -> Any:
            started = time.perf_counter_ns()
            result = original_factory(language, **kwargs)
            recorder.add_factory(language, time.perf_counter_ns() - started, result)
            return result

        stack.callback(setattr, kokorog2p, "get_g2p", original_factory)
        kokorog2p.get_g2p = factory

        import kokorog2p.de.g2p as de_g2p
        import kokorog2p.en.g2p as en_g2p
        from kokorog2p import language_routing, pipeline_api
        from kokorog2p.backends.espeak import cli_wrapper
        from kokorog2p.lexicons.lexphon_backend import LexphonBackend

        def timed(
            module: Any,
            name: str,
            station: str,
            callback: Callable[..., None] | None = None,
        ) -> None:
            original = getattr(module, name)

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                started = time.perf_counter_ns()
                result = original(*args, **kwargs)
                recorder.add_time(station, time.perf_counter_ns() - started)
                if callback is not None:
                    callback(args, result)
                return result

            setattr(module, name, wrapper)
            stack.callback(setattr, module, name, original)

        timed(pipeline_api, "_prepare_span_text", "prepared/prepare_span_text")
        timed(language_routing, "_try_pair_decomposition", "routing/decompose_de_en")
        timed(pipeline_api, "route_languages", "routing/route_languages")

        def prepared_call(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter_ns()
            result = original_prepared_call(*args, **kwargs)
            elapsed = time.perf_counter_ns() - started
            language = normalize_language_code(
                getattr(args[0], "language", DEFAULT_LANGUAGE)
            )
            recorder.frontend_calls[language] += 1
            if language == DEFAULT_LANGUAGE:
                recorder.counts["default whole-text frontend calls"] += 1
                station = "prepared/default_frontend_call"
            else:
                station = f"routed/frontend_call/{language}"
            recorder.add_time(station, elapsed)
            return result

        original_prepared_call = pipeline_api._call_g2p_prepared
        pipeline_api._call_g2p_prepared = prepared_call
        stack.callback(
            setattr, pipeline_api, "_call_g2p_prepared", original_prepared_call
        )

        for cls in (de_g2p.GermanG2P, en_g2p.EnglishG2P):
            original = cls.lexicon_evidence

            def evidence_wrapper(
                self: Any,
                *args: Any,
                _original: Any = original,
                **kwargs: Any,
            ) -> Any:
                started = time.perf_counter_ns()
                result = _original(self, *args, **kwargs)
                language = normalize_language_code(
                    getattr(self, "language", DEFAULT_LANGUAGE)
                )
                recorder.evidence_calls[language] += 1
                recorder.add_time(
                    f"routing/evidence/{language}",
                    time.perf_counter_ns() - started,
                )
                return result

            cls.lexicon_evidence = evidence_wrapper
            stack.callback(setattr, cls, "lexicon_evidence", original)

        original_lookup_many = LexphonBackend.lookup_many

        def lookup_many(self: Any, *args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter_ns()
            result = original_lookup_many(self, *args, **kwargs)
            elapsed = time.perf_counter_ns() - started
            recorder.add_time("lexphon/lookup_many", elapsed)
            recorder.add_time("lexphon/provider_batch", elapsed)
            recorder.counts["Lexphon lookup_many calls"] += 1
            recorder.counts["Lexphon provider batch calls"] += 1
            return result

        LexphonBackend.lookup_many = lookup_many
        stack.callback(setattr, LexphonBackend, "lookup_many", original_lookup_many)

        original_subprocess_run = cli_wrapper.subprocess.run

        def subprocess_run(*args: Any, **kwargs: Any) -> Any:
            command = args[0] if args else kwargs.get("args", ())
            is_espeak = any("espeak" in str(part).lower() for part in command)
            started = time.perf_counter_ns()
            result = original_subprocess_run(*args, **kwargs)
            if is_espeak:
                recorder.add_time("espeak/subprocess", time.perf_counter_ns() - started)
                recorder.counts["eSpeak subprocess count"] += 1
            return result

        cli_wrapper.subprocess.run = subprocess_run
        stack.callback(setattr, cli_wrapper.subprocess, "run", original_subprocess_run)

        for module in (de_g2p, en_g2p):
            original_load = module.load_spacy_model

            def load_spacy(
                *args: Any,
                _original: Any = original_load,
                **kwargs: Any,
            ) -> Any:
                started = time.perf_counter_ns()
                result = _original(*args, **kwargs)
                recorder.add_time("spacy/load_model", time.perf_counter_ns() - started)
                recorder.counts["spaCy model load count"] += 1
                return result

            module.load_spacy_model = load_spacy
            stack.callback(setattr, module, "load_spacy_model", original_load)

        yield


def route_signature(result: Any) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (
            fragment.text,
            fragment.language,
            fragment.kind,
            fragment.char_start,
            fragment.char_end,
        )
        for route in result.language_routes
        for fragment in route.fragments
    )


def run_call(
    case: str,
    config_name: str,
    config: dict[str, Any],
    state: str,
) -> dict[str, Any]:
    if state == "cold":
        clear_cache()
    recorder = Recorder()
    routing = {"mode": config["mode"], "languages": ROUTING_LANGUAGES}
    options = {
        "use_spacy": config["use_spacy"],
        "use_espeak_fallback": config["use_espeak_fallback"],
    }
    with instrument(recorder):
        started = time.perf_counter_ns()
        result = phonemize_to_result(
            CASES[case],
            lang=DEFAULT_LANGUAGE,
            language_routing=routing,
            g2p_options=options,
            return_ids=False,
        )
        total_ms = (time.perf_counter_ns() - started) / 1_000_000
    recorder.add_time("total/phonemize_to_result", int(total_ms * 1_000_000))
    recorder.route_signature = route_signature(result)
    if (
        case == "mixed-example"
        and config_name == "routing-auto-spacy-false-fallback-on"
        and recorder.route_signature != EXPECTED_ROUTE_SIGNATURE
    ):
        raise AssertionError(
            "mixed-example route signature changed:\n"
            f"expected={EXPECTED_ROUTE_SIGNATURE!r}\nactual={recorder.route_signature!r}"
        )
    return recorder.as_dict(
        case=case, config=config_name, state=state, total_ms=total_ms
    )


def run_benchmark() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for config_name, config in CONFIGS.items():
        for case in CASES:
            results.append(run_call(case, config_name, config, "cold"))
            results.append(run_call(case, config_name, config, "warm"))
    return results


def print_report(results: list[dict[str, Any]]) -> None:
    print(
        "case             config                                      state  "
        "total_ms  route_ms  evidence  espeak_proc  spacy_loads  foreign_factory"
    )
    print("-" * 140)
    for result in results:
        counts = result["counts"]
        route_ms = result["stations_ms"]["routing/route_languages"]
        print(
            f"{result['case']:<16} {result['config']:<42} {result['state']:<5} "
            f"{result['total_ms']:>8.2f} {route_ms:>9.2f} "
            f"{sum(counts['evidence_calls'].values()):>8} "
            f"{counts['espeak_subprocess_count']:>12} "
            f"{counts['spacy_load_count']:>11} "
            f"{counts['factory'].get('en-us', 0):>15}"
        )
    slowest = max(results, key=lambda item: item["total_ms"])
    print("\nDetailed stations for slowest case:")
    print(
        json.dumps(
            {
                "case": slowest["case"],
                "config": slowest["config"],
                "state": slowest["state"],
                "stations_ms": slowest["stations_ms"],
                "counts": slowest["counts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional path for the machine-readable report.",
    )
    args = parser.parse_args(argv)
    results = run_benchmark()
    print_report(results)
    if args.json is not None:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
