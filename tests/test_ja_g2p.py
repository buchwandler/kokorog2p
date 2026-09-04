"""Deterministic and optional integration tests for Japanese G2P."""

from __future__ import annotations

import importlib.resources
import sys
from dataclasses import dataclass

import pytest
from lexphon import LexiconNotInstalledError, PronunciationToken

from kokorog2p.ja import JapaneseG2P
from kokorog2p.vocab import validate_for_kokoro


@dataclass
class FakeJapaneseFrontend:
    records: list[dict[str, object]]

    def run_frontend(self, text: str) -> list[dict[str, object]]:
        return self.records


def record(
    surface: str,
    pron: str,
    mora_size: int,
    *,
    acc: int = 0,
    chain_flag: int = 0,
    pos: str = "名詞",
) -> dict[str, object]:
    return {
        "string": surface,
        "pron": pron,
        "mora_size": mora_size,
        "acc": acc,
        "chain_flag": chain_flag,
        "pos": pos,
    }


def frontend_for(*records: dict[str, object]) -> FakeJapaneseFrontend:
    return FakeJapaneseFrontend(list(records))


class TestJapaneseConstructor:
    def test_default_backend_and_model_version(self) -> None:
        g2p = JapaneseG2P(frontend=frontend_for(record("コンニチハ", "コンニチハ", 5)))
        assert g2p.backend == "pyopenjtalk"
        assert g2p.get_target_model() == "1.0"

    @pytest.mark.parametrize("backend", ["pyopenjtalk", "cutlet"])
    def test_documented_backend_values_are_accepted(self, backend: str) -> None:
        g2p = JapaneseG2P(backend=backend)
        assert g2p.backend == backend

    def test_invalid_backend_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unsupported Japanese backend"):
            JapaneseG2P(backend="typo")

    @pytest.mark.parametrize("legacy_backend", ["pyopenjtalk", "cutlet"])
    def test_legacy_version_backend_selector_is_deprecated(
        self, legacy_backend: str
    ) -> None:
        with pytest.warns(DeprecationWarning, match="backend"):
            g2p = JapaneseG2P(version=legacy_backend)
        assert g2p.backend == legacy_backend
        assert g2p.version == "1.0"

    def test_model_version_is_not_used_as_backend(self) -> None:
        g2p = JapaneseG2P(version="1.1")
        assert g2p.backend == "pyopenjtalk"
        assert g2p.get_target_model() == "1.1"

    def test_conflicting_legacy_and_current_backend_selectors_are_rejected(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="both backend"):
            JapaneseG2P(backend="cutlet", version="pyopenjtalk")


class TestJapaneseMoraMapping:
    @pytest.mark.parametrize(
        ("pron", "expected"),
        [
            ("コンニチハ", ["コ", "ン", "ニ", "チ", "ハ"]),
            ("キャ", ["キャ"]),
            ("スーパー", ["ス", "ー", "パ", "ー"]),
            ("ガッコウ", ["ガ", "ッ", "コ", "ウ"]),
            ("ティッシュ", ["ティ", "ッ", "シュ"]),
        ],
    )
    def test_exact_mora_mapping(self, pron: str, expected: list[str]) -> None:
        assert JapaneseG2P.pron2moras(pron) == expected

    def test_unknown_pronunciation_symbol_is_reported(self) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            JapaneseG2P.pron2moras("コン😀")


class TestJapaneseFrontendMapping:
    def test_mora_metadata_mismatch_is_reported(self) -> None:
        frontend = frontend_for(record("テスト", "テスト", 99))
        g2p = JapaneseG2P(frontend=frontend)
        with pytest.raises(ValueError, match="mora count mismatch"):
            g2p.phonemize("テスト")

    def test_frontend_unknown_symbol_is_reported(self) -> None:
        frontend = frontend_for(record("未知", "コン😀", 2))
        g2p = JapaneseG2P(frontend=frontend)
        with pytest.raises(ValueError, match="Unsupported Japanese pronunciation"):
            g2p.phonemize("未知")

    @pytest.mark.parametrize("pron", ["デス’", "’デス"])
    def test_frontend_boundary_quote_is_ignored(self, pron: str) -> None:
        frontend = frontend_for(record("デス", pron, 2))
        g2p = JapaneseG2P(frontend=frontend)

        assert g2p.phonemize("デス")

    def test_internal_quote_is_still_reported(self) -> None:
        frontend = frontend_for(record("デス", "デ’ス", 2))
        g2p = JapaneseG2P(frontend=frontend)
        with pytest.raises(ValueError, match="Unsupported Japanese pronunciation"):
            g2p.phonemize("デス")

    def test_leading_whitespace_does_not_index_empty_tokens(self) -> None:
        frontend = frontend_for(
            record(" ", "", 0, pos="記号"),
            record("コンニチハ", "コンニチハ", 5),
        )
        tokens = JapaneseG2P(frontend=frontend)(" コンニチハ")
        assert tokens

    def test_leading_punctuation_does_not_index_empty_tokens(self) -> None:
        frontend = frontend_for(
            record("、", "", 0, pos="記号"),
            record("コンニチハ", "コンニチハ", 5),
        )
        tokens = JapaneseG2P(frontend=frontend)("、コンニチハ")
        assert tokens

    def test_model_input_has_equal_base_and_pitch_channels(self) -> None:
        frontend = frontend_for(record("コンニチハ", "コンニチハ", 5, acc=2))
        result = JapaneseG2P(frontend=frontend).phonemize("コンニチハ")
        assert len(result) % 2 == 0
        midpoint = len(result) // 2
        base, pitch = result[:midpoint], result[midpoint:]
        assert base
        assert len(base) == len(pitch)

    def test_generated_token_phonemes_are_in_kokoro_vocabulary(self) -> None:
        frontend = frontend_for(record("コンニチハ", "コンニチハ", 5))
        tokens = JapaneseG2P(frontend=frontend)("コンニチハ")
        for token in tokens:
            if token.phonemes:
                valid, invalid = validate_for_kokoro(token.phonemes)
                assert valid, invalid

    def test_missing_pyopenjtalk_has_actionable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "pyopenjtalk", None)
        with pytest.raises(ImportError, match=r"kokorog2p\[ja\]"):
            JapaneseG2P().phonemize("こんにちは")


@pytest.mark.skipif(
    not all(
        importlib.util.find_spec(module) is not None
        for module in ("fugashi", "jaconv", "mojimoji")
    ),
    reason="Cutlet dependencies are not installed",
)
def test_cutlet_smoke() -> None:
    g2p = JapaneseG2P(backend="cutlet")
    try:
        result = g2p.phonemize("こんにちは")
    except RuntimeError as exc:
        pytest.skip(f"Cutlet dictionary is not installed: {exc}")
    assert result


def test_cutlet_uses_lexhint_for_known_word_grouping() -> None:
    from kokorog2p.ja.cutlet import HEPBURN, Cutlet, Word

    class FakeLexphon:
        def __init__(self) -> None:
            self.lookups: list[str] = []

        def lookup(self, word: str) -> PronunciationToken | None:
            self.lookups.append(word)
            if word == "東京大学":
                return PronunciationToken(
                    text=word,
                    pronunciation="toːkjoː daigaku",
                    source="lexicon",
                    lexicon_id="ja:lexhint",
                    matched_key=word,
                    source_encoding="ipa",
                    variants=("toːkjoː daigaku",),
                )
            return None

    fake = FakeLexphon()
    cutlet = object.__new__(Cutlet)
    cutlet.table = dict(HEPBURN)
    cutlet.exceptions = {}
    cutlet._lexphon = fake  # type: ignore[assignment]
    tokens = cutlet._romaji_tokens(
        [
            Word("東京", "とうきょう", 6),
            Word("大学", "だいがく", 6),
        ]
    )
    assert "東京大学" in fake.lookups
    assert len(tokens) == 1


def test_cutlet_lexhint_missing_data_is_actionable() -> None:
    from kokorog2p.ja.cutlet import Cutlet, Word

    class MissingLexphon:
        def lookup(self, word: str) -> None:
            raise LexiconNotInstalledError("missing ja:lexhint")

    cutlet = object.__new__(Cutlet)
    cutlet.table = {}
    cutlet.exceptions = {}
    cutlet._lexphon = MissingLexphon()  # type: ignore[assignment]
    with pytest.raises(LexiconNotInstalledError, match="ja:lexhint"):
        cutlet._romaji_tokens([Word("東京", "とうきょう", 6)])


def test_japanese_word_list_resource_is_absent() -> None:
    resource = importlib.resources.files("kokorog2p.lexicons.data").joinpath(
        "ja_words.g2lex"
    )
    assert not resource.is_file()
    assert (
        not importlib.resources.files("kokorog2p.ja.data")
        .joinpath("ja_words.txt")
        .is_file()
    )
