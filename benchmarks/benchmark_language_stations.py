#!/usr/bin/env python3
"""Cross-language station profiler for kokorog2p prepared-text G2P.

This benchmark intentionally uses already-speakable text and reuses the same G2P
object for direct and ``phonemize_prepared`` calls.  It is modeled after
``benchmark_de_gold_stations.py``, while making language-specific instrumentation
adaptive so the same harness can be used by every supported frontend.

Run from the repository root, for example::

    python benchmarks/benchmark_language_stations.py --language fr \
        --fallback on --runs 1
    python benchmarks/benchmark_zh_stations.py --fallback on --runs 3
"""

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

try:
    import resource
except ImportError:  # pragma: no cover - Windows has no resource module
    resource = None  # type: ignore[assignment]
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any

from kokorog2p import clear_cache, get_g2p, phonemize_prepared

LANGUAGES: dict[str, dict[str, Any]] = {
    "en-us": {
        "label": "English US",
        "slug": "en_us",
        "sentences": [
            "The quick brown fox jumps over the lazy dog.",
            "Please bring fresh coffee and warm bread to the table.",
            "Every language needs a fast and predictable pronunciation frontend.",
            (
                "Kokoro reads clear prepared text while the benchmark "
                + "watches every station."
            ),
        ],
    },
    "en-gb": {
        "label": "English GB",
        "slug": "en_gb",
        "sentences": [
            "The colour of the theatre curtain is dark blue.",
            "Please bring fresh tea and warm bread to the table.",
            "A careful speaker keeps every syllable clear and steady.",
            (
                "Kokoro reads prepared British English while the benchmark "
                + "watches every station."
            ),
        ],
    },
    "de": {
        "label": "German",
        "slug": "de",
        "sentences": [
            "Der schnelle braune Fuchs springt über den faulen Hund.",
            "Bitte bring frischen Kaffee und warmes Brot an den Tisch.",
            "Eine klare Aussprache macht lange Sätze leichter verständlich.",
            (
                "Kokoro liest vorbereiteten deutschen Text und der Benchmark "
                + "misst jede Station."
            ),
        ],
    },
    "fr": {
        "label": "French",
        "slug": "fr",
        "sentences": [
            "Le renard brun rapide saute par dessus le chien paresseux.",
            "Veuillez apporter du café frais et du pain chaud à la table.",
            "Une prononciation claire rend chaque phrase plus facile à comprendre.",
            (
                "Kokoro lit un texte français préparé pendant que le benchmark "
                + "mesure chaque étape."
            ),
        ],
    },
    "es": {
        "label": "Spanish",
        "slug": "es",
        "sentences": [
            "El zorro marrón rápido salta sobre el perro perezoso.",
            "Trae café fresco y pan caliente a la mesa, por favor.",
            "Una pronunciación clara hace que cada frase sea fácil de entender.",
            "Kokoro lee texto español preparado mientras el benchmark mide cada etapa.",
        ],
    },
    "it": {
        "label": "Italian",
        "slug": "it",
        "sentences": [
            "La volpe marrone veloce salta sopra il cane pigro.",
            "Porta caffè fresco e pane caldo al tavolo, per favore.",
            "Una pronuncia chiara rende ogni frase facile da capire.",
            (
                "Kokoro legge testo italiano preparato mentre il benchmark "
                + "misura ogni fase."
            ),
        ],
    },
    "pt-br": {
        "label": "Portuguese BR",
        "slug": "pt_br",
        "sentences": [
            "A rápida raposa marrom salta sobre o cachorro preguiçoso.",
            "Por favor, traga café fresco e pão quente para a mesa.",
            "Uma pronúncia clara deixa cada frase mais fácil de entender.",
            (
                "Kokoro lê texto brasileiro preparado enquanto o benchmark "
                + "mede cada etapa."
            ),
        ],
    },
    "pt-pt": {
        "label": "Portuguese PT",
        "slug": "pt_pt",
        "sentences": [
            "A rápida raposa castanha salta sobre o cão preguiçoso.",
            "Por favor, traga café fresco e pão quente para a mesa.",
            "Uma pronúncia clara torna cada frase mais fácil de compreender.",
            "Kokoro lê texto europeu preparado enquanto o benchmark mede cada etapa.",
        ],
    },
    "cs": {
        "label": "Czech",
        "slug": "cs",
        "sentences": [
            "Rychlá hnědá liška skáče přes líného psa.",
            "Prosím přines čerstvou kávu a teplý chléb na stůl.",
            "Jasná výslovnost usnadňuje porozumění každé větě.",
            "Kokoro čte připravený český text a benchmark měří každou část.",
        ],
    },
    "vi": {
        "label": "Vietnamese",
        "slug": "vi",
        "sentences": [
            "Con cáo nâu nhanh nhảy qua con chó lười.",
            "Xin mang cà phê mới và bánh mì nóng đến bàn.",
            "Phát âm rõ ràng giúp mọi câu dễ hiểu hơn.",
            "Kokoro đọc văn bản tiếng Việt đã chuẩn bị và phép đo theo dõi từng bước.",
        ],
    },
    "sv-se": {
        "label": "Swedish",
        "slug": "sv",
        "sentences": [
            "Den snabba bruna räven hoppar över den lata hunden.",
            "Ta med färskt kaffe och varmt bröd till bordet.",
            "Ett tydligt uttal gör varje mening lättare att förstå.",
            "Kokoro läser förberedd svensk text medan mätningen följer varje steg.",
        ],
    },
    "ru": {
        "label": "Russian",
        "slug": "ru",
        "sentences": [
            "Быстрая коричневая лиса прыгает через ленивую собаку.",
            "Пожалуйста, принеси свежий кофе и тёплый хлеб к столу.",
            "Чёткое произношение помогает легче понимать каждую фразу.",
            "Кокоро читает подготовленный русский текст, а тест измеряет каждый этап.",
        ],
    },
    "kk": {
        "label": "Kazakh",
        "slug": "kk",
        "sentences": [
            "Жылдам қоңыр түлкі жалқау иттің үстінен секіреді.",
            "Үстелге жаңа кофе мен жылы нан әкеліңіз.",
            "Анық айтылым әр сөйлемді түсінуді жеңілдетеді.",
            "Кокоро дайын қазақ мәтінін оқиды, ал сынақ әр кезеңді өлшейді.",
        ],
    },
    "he": {
        "label": "Hebrew",
        "slug": "he",
        "sentences": [
            "השועל החום המהיר קופץ מעל הכלב העצלן.",
            "בבקשה הבא קפה טרי ולחם חם אל השולחן.",
            "הגייה ברורה מקלה על ההבנה של כל משפט.",
            "קוקורו קורא טקסט עברי מוכן והבדיקה מודדת כל שלב.",
        ],
    },
    "ar": {
        "label": "Arabic",
        "slug": "ar",
        "sentences": [
            "يقفز الثعلب البني السريع فوق الكلب الكسول.",
            "من فضلك أحضر قهوة طازجة وخبزا دافئا إلى الطاولة.",
            "يساعد النطق الواضح على فهم كل جملة بسهولة.",
            "يقرأ كوكورو نصا عربيا جاهزا بينما يقيس الاختبار كل مرحلة.",
        ],
    },
    "zh": {
        "label": "Chinese",
        "slug": "zh",
        "sentences": [
            "敏捷的棕色狐狸跳过懒狗。",
            "请把新鲜咖啡和热面包带到桌上。",
            "清楚的发音让每句话都更容易理解。",
            "可可罗读取准备好的中文文本，基准测试记录每个阶段。",
        ],
    },
    "ja": {
        "label": "Japanese",
        "slug": "ja",
        "sentences": [
            "素早い茶色の狐が怠けた犬を飛び越えます。",
            "新鮮なコーヒーと温かいパンをテーブルに持ってきてください。",
            "明瞭な発音はすべての文を理解しやすくします。",
            "ココロは準備された日本語の文章を読み、ベンチマークが各段階を測ります。",
        ],
    },
    "ko": {
        "label": "Korean",
        "slug": "ko",
        "sentences": [
            "빠른 갈색 여우가 게으른 개를 뛰어넘습니다.",
            "신선한 커피와 따뜻한 빵을 식탁으로 가져오세요.",
            "명확한 발음은 모든 문장을 이해하기 쉽게 만듭니다.",
            "코코로는 준비된 한국어 문장을 읽고 벤치마크는 각 단계를 측정합니다.",
        ],
    },
    "th": {
        "label": "Thai",
        "slug": "th",
        "sentences": [
            "สุนัขจิ้งจอกสีน้ำตาลที่ว่องไวกระโดดข้ามสุนัขขี้เกียจ",
            "กรุณานำกาแฟสดและขนมปังอุ่นมาที่โต๊ะ",
            "การออกเสียงที่ชัดเจนทำให้ทุกประโยคเข้าใจง่ายขึ้น",
            "โคโคโระอ่านข้อความภาษาไทยที่เตรียมไว้และการทดสอบวัดทุกขั้นตอน",
        ],
    },
}

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

# Methods whose costs are useful on a language frontend.  Missing methods are
# simply ignored, which keeps this benchmark forward-compatible across frontends.
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
        start = time.perf_counter_ns()
        try:
            return fn(*args, **kwargs)
        finally:
            self.record(
                station,
                (time.perf_counter_ns() - start) / 1_000_000.0,
                detail,
            )


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return ordered[index]


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
            detail = _detail_from_args(args, kwargs)
            return self.recorder.call(station, original, *args, detail=detail, **kwargs)

        setattr(module, name, wrapped)
        self._restorers.append(lambda: setattr(module, name, original))
        return True

    def patch_method(self, instance: Any, name: str, station: str) -> bool:
        cls = type(instance)
        key = (cls, name)
        if key in self._class_patches:
            return False

        original_bound = getattr(cls, name, None)
        if not callable(original_bound):
            return False

        had_own = name in cls.__dict__
        own_value = cls.__dict__.get(name)
        recorder = self.recorder

        @functools.wraps(original_bound)
        def wrapped(self_obj: Any, *args: Any, **kwargs: Any) -> Any:
            detail = _detail_from_args(args, kwargs)
            return recorder.call(
                station,
                original_bound,
                self_obj,
                *args,
                detail=detail,
                **kwargs,
            )

        setattr(cls, name, wrapped)

        def restore() -> None:
            if had_own:
                setattr(cls, name, own_value)
            else:
                try:
                    delattr(cls, name)
                except AttributeError:
                    pass

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
                "espeak/subprocess",
                original,
                *args,
                detail=rendered[:120],
                **kwargs,
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
    if value is None or isinstance(value, ModuleType):
        return False
    lowered = attribute.lower()
    class_name = type(value).__name__.lower()
    if not any(hint in lowered or hint in class_name for hint in COMPONENT_HINTS):
        return False
    if any(
        method_name != "__call__" and callable(getattr(value, method_name, None))
        for method_name in COMPONENT_METHODS
    ):
        return True
    return callable(value) and "__call__" in type(value).__dict__


def _instrument_frontend(patches: PatchSet, g2p: Any) -> None:
    for method_name, station in FRONTEND_METHODS.items():
        patches.patch_method(g2p, method_name, station)


def _instrument_components(
    patches: PatchSet,
    g2p: Any,
    known_components: dict[str, Any],
) -> None:
    for attribute, value in vars(g2p).items():
        if not _is_component(attribute, value):
            continue
        known_components[attribute] = value
        prefix = _component_name(attribute, value)
        for method_name in COMPONENT_METHODS:
            station = f"{prefix}/{method_name.lstrip('_')}"
            patches.patch_method(value, method_name, station)


def _instrument_prepared_pipeline(patches: PatchSet) -> None:
    from kokorog2p import pipeline_api

    for function_name, station in PREPARED_BOUNDARIES.items():
        patches.patch_module_function(pipeline_api, function_name, station)


def _token_phoneme_string(tokens: list[Any]) -> str:
    return "".join(
        (getattr(token, "phonemes", None) or "")
        + (getattr(token, "whitespace", None) or "")
        for token in tokens
    ).strip()


def _normalise_benchmark_output(value: str) -> str:
    """Compare station outputs independent of token-boundary whitespace."""
    value = " ".join(value.split())
    return re.sub(r"\s*([,.!?;:，。！？；：])\s*", r"\1", value)


def _rss_mib() -> float | None:
    if resource is None:
        return None
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / (1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0)


def _factory_probe(language: str, fallback_on: bool) -> dict[str, Any]:
    """Measure factory construction and first use inside the probe process."""
    options = _factory_options(LANGUAGES[language], fallback_on)
    counters = {
        "CaseAliasMapping __iter__ calls during factory": 0,
        "spaCy loads during factory": 0,
        "eSpeak backend creations during factory": 0,
        "language-engine creations during factory": 0,
    }
    restorers: list[Callable[[], None]] = []
    start_rss = _rss_mib()
    try:
        import g2lex

        from kokorog2p.backends.espeak import EspeakBackend
        from kokorog2p.th import g2p as thai_g2p

        original_iter = g2lex.CaseAliasMapping.__iter__

        def counted_iter(self: Any):
            counters["CaseAliasMapping __iter__ calls during factory"] += 1
            yield from original_iter(self)

        g2lex.CaseAliasMapping.__iter__ = counted_iter
        restorers.append(
            lambda: setattr(g2lex.CaseAliasMapping, "__iter__", original_iter)
        )

        def count_init(key: str, cls: type[Any]) -> None:
            original_init = cls.__init__

            def wrapped(self: Any, *args: Any, **kwargs: Any) -> None:
                counters[key] += 1
                original_init(self, *args, **kwargs)

            cls.__init__ = wrapped
            restorers.append(lambda: setattr(cls, "__init__", original_init))

        count_init(
            "eSpeak backend creations during factory",
            EspeakBackend,
        )
        count_init("language-engine creations during factory", thai_g2p.ThaiEngine)

        try:
            import spacy

            original_load = spacy.load

            def counted_load(*args: Any, **kwargs: Any) -> Any:
                counters["spaCy loads during factory"] += 1
                return original_load(*args, **kwargs)

            spacy.load = counted_load
            restorers.append(lambda: setattr(spacy, "load", original_load))
        except ImportError:
            pass

        clear_cache()
        factory_start = time.perf_counter_ns()
        frontend = get_g2p(language, **options)
        factory_construct_ms = (time.perf_counter_ns() - factory_start) / 1_000_000.0
        end_rss = _rss_mib()
        factory_counters = counters.copy()
        cached_start = time.perf_counter_ns()
        cached = get_g2p(language, **options)
        factory_cached_ms = (time.perf_counter_ns() - cached_start) / 1_000_000.0
        sentence = LANGUAGES[language]["sentences"][0]
        first_start = time.perf_counter_ns()
        direct = frontend(sentence)
        first_phonemize_ms = (time.perf_counter_ns() - first_start) / 1_000_000.0
        second_start = time.perf_counter_ns()
        prepared = phonemize_prepared(
            sentence,
            language,
            return_ids=False,
            return_phonemes=True,
            g2p=frontend,
            **options,
        )
        second_phonemize_ms = (time.perf_counter_ns() - second_start) / 1_000_000.0
        return {
            "status": "ok",
            "factory_construct_ms": factory_construct_ms,
            "factory_cached_ms": factory_cached_ms,
            "first_phonemize_ms": first_phonemize_ms,
            "second_phonemize_ms": second_phonemize_ms,
            "optional_backend_created_during_factory": any(
                factory_counters[name] > 0
                for name in (
                    "eSpeak backend creations during factory",
                    "language-engine creations during factory",
                )
            ),
            "rss_delta_factory_mib": (
                None
                if start_rss is None or end_rss is None
                else max(0.0, end_rss - start_rss)
            ),
            "counters": factory_counters,
            "object_reuse": cached is frontend,
            "output_equal": _normalise_benchmark_output(_token_phoneme_string(direct))
            == _normalise_benchmark_output(prepared.phonemes or ""),
        }
    except (ImportError, ModuleNotFoundError) as exc:
        return {"status": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:
        return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        while restorers:
            restorers.pop()()


def _factory_probe_main(language: str, fallback_on: bool) -> int:
    payload = _factory_probe(language, fallback_on)
    print("__KOKOROG2P_FACTORY_PROBE__" + json.dumps(payload, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


def _run_cold_factory_probe(language: str, fallback_on: bool) -> dict[str, Any]:
    """Run the factory probe in a fresh process, including import startup time."""
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
    cold_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    marker = "__KOKOROG2P_FACTORY_PROBE__"
    payload: dict[str, Any] = {"status": "failed", "error": result.stderr.strip()}
    for line in result.stdout.splitlines():
        if line.startswith(marker):
            payload = json.loads(line[len(marker) :])
    payload["factory_cold_ms"] = cold_ms
    payload["probe_exit_code"] = result.returncode
    return payload


def _factory_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [result for result in results if result.get("status") == "ok"]
    if not successful:
        return results[0] if results else {"status": "unavailable"}
    summary: dict[str, Any] = {
        "status": "ok",
        "factory_cold_ms": statistics.median(
            result["factory_cold_ms"] for result in successful
        ),
        "factory_cached_ms": statistics.median(
            result["factory_cached_ms"] for result in successful
        ),
        "first_phonemize_ms": statistics.median(
            result["first_phonemize_ms"] for result in successful
        ),
        "second_phonemize_ms": statistics.median(
            result["second_phonemize_ms"] for result in successful
        ),
        "optional_backend_created_during_factory": any(
            result["optional_backend_created_during_factory"] for result in successful
        ),
        "rss_delta_factory_mib": (
            statistics.median(
                result["rss_delta_factory_mib"]
                for result in successful
                if result["rss_delta_factory_mib"] is not None
            )
            if any(result["rss_delta_factory_mib"] is not None for result in successful)
            else None
        ),
        "output_equal": all(result["output_equal"] for result in successful),
        "object_reuse": all(result["object_reuse"] for result in successful),
    }
    for key in successful[0].get("counters", {}):
        summary[key] = sum(result["counters"].get(key, 0) for result in successful)
    return summary


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
    if value is None:
        return None
    if hasattr(value, "value"):
        value = value.value
    if not isinstance(value, str):
        return None
    value = value.strip().lower().replace(" ", "_")
    return value or None


def _source_for_token(token: Any, language: str) -> str:
    try:
        if token.is_punctuation:
            return "punctuation"
    except Exception:
        pass

    source = _normalise_source_name(getattr(token, "rating", None))
    if source:
        return source

    extension = getattr(token, "_", None)
    if isinstance(extension, dict):
        for key in ("source", "phoneme_source", "g2p_source"):
            source = _normalise_source_name(extension.get(key))
            if source:
                return source

        rating = extension.get("rating")
        if language == "de" and isinstance(rating, (int, float)):
            # Preserve the German benchmark's historical source convention.
            return {
                5: "lexicon",
                3: "espeak_fallback",
                2: "german_rules",
            }.get(int(rating), "resolved")
        source = _normalise_source_name(rating)
        if source:
            return source

    if getattr(token, "phonemes", None):
        return "resolved"
    return "unresolved"


def _snapshot_components(g2p: Any) -> dict[str, int]:
    result = {"G2P": id(g2p)}
    for attribute, value in vars(g2p).items():
        if _is_component(attribute, value):
            result[attribute] = id(value)
    return result


def _merge_reuse(
    before: dict[str, int],
    after: dict[str, int],
) -> dict[str, bool]:
    keys = sorted(set(before) | set(after))
    return {
        key: key in before and key in after and before[key] == after[key]
        for key in keys
    }


def _backend_summary(
    components: dict[str, str],
    subprocess_count: int,
) -> str:
    if subprocess_count:
        return "subprocess"
    names = list(components.values())
    if any("espeak" in name.lower() for name in names):
        return "native/in-process"
    return "not observed"


@dataclass
class RunResult:
    direct_outputs: list[str]
    prepared_outputs: list[str]
    source_counts: Counter[str]
    word_count: int
    reuse: dict[str, bool]
    components: dict[str, str]


def _factory_options(
    spec: dict[str, Any],
    fallback_on: bool,
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "use_spacy": False,
        "use_espeak_fallback": fallback_on,
        "use_goruut_fallback": False,
    }
    options.update(spec.get("g2p_options", {}))
    return options


def _run_once(
    language: str,
    fallback_on: bool,
    recorder: Recorder,
    subprocess_probe: SubprocessProbe,
) -> RunResult:
    spec = LANGUAGES[language]
    clear_cache()

    options = _factory_options(spec, fallback_on)
    g2p = recorder.call(
        "factory/get_g2p",
        get_g2p,
        language,
        detail=language,
        **options,
    )

    known_components: dict[str, Any] = {}
    direct_outputs: list[str] = []
    prepared_outputs: list[str] = []
    source_counts: Counter[str] = Counter()
    word_count = 0

    with PatchSet(recorder) as patches:
        _instrument_frontend(patches, g2p)
        _instrument_components(patches, g2p, known_components)
        _instrument_prepared_pipeline(patches)

        before = _snapshot_components(g2p)

        for sentence in spec["sentences"]:
            tokens = recorder.call(
                "direct/frontend",
                g2p,
                sentence,
                detail=sentence[:120],
            )
            direct_outputs.append(_token_phoneme_string(tokens))
            word_count += _count_word_tokens(tokens)
            source_counts.update(
                _source_for_token(token, language)
                for token in tokens
                if not getattr(token, "is_punctuation", False)
            )
            # Capture lazily created fallbacks/backends for subsequent calls.
            _instrument_components(patches, g2p, known_components)

        middle = _snapshot_components(g2p)

        for sentence in spec["sentences"]:
            result = recorder.call(
                "prepared/total",
                phonemize_prepared,
                sentence,
                language,
                return_ids=False,
                return_phonemes=True,
                g2p=g2p,
                use_spacy=False,
                use_espeak_fallback=fallback_on,
                detail=sentence[:120],
            )
            prepared_outputs.append(result.phonemes or "")
            _instrument_components(patches, g2p, known_components)

        after = _snapshot_components(g2p)

    reuse = _merge_reuse(middle or before, after)
    components = {
        attribute: type(value).__name__
        for attribute, value in sorted(known_components.items())
    }
    return RunResult(
        direct_outputs=direct_outputs,
        prepared_outputs=prepared_outputs,
        source_counts=source_counts,
        word_count=word_count,
        reuse=reuse,
        components=components,
    )


def _station_sort_key(name: str) -> tuple[int, str]:
    if name == "factory/get_g2p":
        return (0, name)
    if "lexicon" in name or "fallback" in name:
        return (1, name)
    if name.startswith("frontend/"):
        return (2, name)
    if name.startswith(("component/", "espeak/")):
        return (3, name)
    if name.startswith("prepared/") and name != "prepared/total":
        return (4, name)
    if name == "direct/frontend":
        return (5, name)
    if name == "prepared/total":
        return (6, name)
    return (7, name)


def _print_table(recorder: Recorder) -> None:
    print()
    print(f"{'station':<38} {'calls':>8} {'total ms':>14} {'p95 ms':>12}")
    print("-" * 78)
    for station in sorted(recorder.values_ms, key=_station_sort_key):
        values = recorder.values_ms[station]
        print(
            f"{station:<38} {len(values):>8d} "
            f"{sum(values):>14.3f} {_p95(values):>12.3f}"
        )


def _print_slowest(recorder: Recorder, limit: int) -> None:
    candidates: list[tuple[float, str, str]] = []
    for station, details in recorder.details.items():
        if (
            "fallback" in station
            or "backend" in station
            or "phonemize_word" in station
            or station == "espeak/subprocess"
        ):
            for elapsed, detail in details:
                candidates.append((elapsed, station, detail))
    candidates.sort(reverse=True)
    print("slowest fallback/backend calls:")
    if not candidates:
        print("  (none observed)")
        return
    for elapsed, station, detail in candidates[:limit]:
        print(f"  {elapsed:10.3f} ms  {station:<34} {detail}")


def _json_payload(
    language: str,
    fallback_on: bool,
    runs: int,
    recorder: Recorder,
    results: list[RunResult],
    subprocess_probe: SubprocessProbe,
    factory_results: list[dict[str, Any]],
) -> dict[str, Any]:
    source_counts: Counter[str] = Counter()
    for result in results:
        source_counts.update(result.source_counts)
    stations = {
        name: {
            "calls": len(values),
            "total_ms": sum(values),
            "p95_ms": _p95(values),
        }
        for name, values in recorder.values_ms.items()
    }
    return {
        "language": language,
        "label": LANGUAGES[language]["label"],
        "fallback": fallback_on,
        "runs": runs,
        "stations": stations,
        "sources": dict(source_counts),
        "espeak_subprocess_count": subprocess_probe.count,
        "output_equal": all(
            _normalise_benchmark_output(result.direct_outputs[index])
            == _normalise_benchmark_output(result.prepared_outputs[index])
            for result in results
            for index in range(len(result.direct_outputs))
        ),
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


def build_parser(default_language: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile kokorog2p G2P stations for one supported language."
    )
    parser.add_argument(
        "--language",
        choices=sorted(LANGUAGES),
        default=default_language or "en-us",
        help="Canonical language target.",
    )
    parser.add_argument(
        "--fallback",
        choices=("on", "off"),
        default="on",
        help="Enable or disable eSpeak fallback where the frontend supports it.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of object-cold benchmark runs.",
    )
    parser.add_argument(
        "--slowest",
        type=int,
        default=10,
        help="Number of slow fallback/backend calls to print.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional path for machine-readable aggregate results.",
    )
    parser.add_argument(
        "--factory-probe",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    default_language: str | None = None,
) -> int:
    args = build_parser(default_language).parse_args(argv)
    if args.factory_probe:
        return _factory_probe_main(args.language, args.fallback == "on")
    if args.runs < 1:
        raise SystemExit("--runs must be at least one")
    if args.slowest < 0:
        raise SystemExit("--slowest must be non-negative")

    language = args.language
    fallback_on = args.fallback == "on"
    spec = LANGUAGES[language]
    recorder = Recorder()
    results: list[RunResult] = []

    factory_results: list[dict[str, Any]] = []
    print(f"{spec['label']} G2P station benchmark")
    print(f"  corpus: {len(spec['sentences'])} sentences")
    print(f"  fallback: {args.fallback}")
    print("  backend: native/default")
    print(f"  runs: {args.runs}")

    try:
        with SubprocessProbe(recorder) as subprocess_probe:
            for _ in range(args.runs):
                results.append(
                    _run_once(
                        language,
                        fallback_on,
                        recorder,
                        subprocess_probe,
                    )
                )
                factory_results.append(_run_cold_factory_probe(language, fallback_on))
    except (ImportError, ModuleNotFoundError) as exc:
        print(
            f"ERROR: optional dependency required by {language!r} is missing: {exc}",
            file=sys.stderr,
        )
        print(
            "Install the repository benchmark dependencies, usually "
            '`python -m pip install -e ".[all,dev]"`.',
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        print(
            f"ERROR while benchmarking {language!r}: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    corpus_words = results[0].word_count if results else 0
    print(f"  word-like frontend tokens: {corpus_words}")

    _print_table(recorder)

    sources: Counter[str] = Counter()
    for result in results:
        sources.update(result.source_counts)

    print()
    print("sources:")
    for source, count in sorted(sources.items()):
        print(f"  {source:<24}: {count}")

    components = {
        key: value for result in results for key, value in result.components.items()
    }
    print(
        "espeak/effective_backend:",
        _backend_summary(
            components,
            subprocess_probe.count,
        ),
    )
    print("espeak/subprocess_count:", subprocess_probe.count)

    reuse_keys = sorted({key for result in results for key in result.reuse})
    reuse = {
        key: all(result.reuse.get(key, False) for result in results)
        for key in reuse_keys
    }
    print("object reuse:", reuse)

    equal = all(
        _normalise_benchmark_output(result.direct_outputs[index])
        == _normalise_benchmark_output(result.prepared_outputs[index])
        for result in results
        for index in range(len(result.direct_outputs))
    )
    print("direct/prepared output equal:", equal)
    _print_slowest(recorder, args.slowest)

    factory = _factory_summary(factory_results)
    print()
    print("factory summary:")
    if factory.get("status") != "ok":
        print(f"  status: {factory.get('status')}: {factory.get('error', '')}")
    else:
        print(
            "  language factory_cold_ms factory_cached_ms first_phonemize_ms "
            "second_phonemize_ms optional_backend_created_during_factory "
            "rss_delta_factory_mib"
        )
        print(
            f"  {language:<8} {factory['factory_cold_ms']:>15.3f} "
            f"{factory['factory_cached_ms']:>17.3f} "
            f"{factory['first_phonemize_ms']:>18.3f} "
            f"{factory['second_phonemize_ms']:>19.3f} "
            f"{factory['optional_backend_created_during_factory']!s:>34} "
            f"{factory['rss_delta_factory_mib']!s:>21}"
        )

    if not equal:
        print()
        print("output mismatches:")
        for run_index, result in enumerate(results, start=1):
            for sentence_index, (direct, prepared) in enumerate(
                zip(result.direct_outputs, result.prepared_outputs, strict=True),
                start=1,
            ):
                if direct != prepared:
                    print(
                        f"  run {run_index}, sentence {sentence_index}:\n"
                        f"    direct  : {direct}\n"
                        f"    prepared: {prepared}"
                    )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                _json_payload(
                    language,
                    fallback_on,
                    args.runs,
                    recorder,
                    results,
                    subprocess_probe,
                    factory_results,
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    return 0 if equal else 3


if __name__ == "__main__":
    raise SystemExit(main())
