"""Korean resource, representation, and model-contract regressions."""

import importlib.resources

import pytest

from kokorog2p.ko import KoreanG2P
from kokorog2p.ko.jamo_to_ipa import jamo_to_ipa
from kokorog2p.ko.model_profile import KOKORO_V1_VOICE, encode_for_model, model_vocab


def test_korean_rule_table_is_packaged() -> None:
    resource = importlib.resources.files("kokorog2p.ko.data").joinpath("table.csv")
    assert resource.is_file()
    assert resource.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize(
    ("text", "ending"),
    [("강", "ŋ"), ("안녕", "ŋ"), ("국", "k̚"), ("밥", "p̚"), ("옷", "t̚")],
)
def test_jamo_to_ipa_preserves_coda_classes(text: str, ending: str) -> None:
    assert jamo_to_ipa(text).endswith(ending) or ending in jamo_to_ipa(text)


@pytest.mark.parametrize("text", ["강", "안녕", "국", "밥", "옷", "강", "국"])
def test_model_output_matches_kokoro_v1_vocab(text: str) -> None:
    output = KoreanG2P(use_dict=False).phonemize(text)
    assert set(output) <= model_vocab()
    assert encode_for_model(output) == output


def test_model_output_uses_explicit_lossy_symbols() -> None:
    assert encode_for_model("k͈uk̚") == "kuk"
    with pytest.raises(ValueError, match="does not support"):
        encode_for_model("§")


def test_default_korean_voice_is_jf_alpha() -> None:
    assert KoreanG2P(use_dict=False).voice == KOKORO_V1_VOICE == "jf_alpha"


def test_korean_morphology_off_is_deterministic() -> None:
    g2p = KoreanG2P(morphology="off")
    assert g2p.g2pk.mecab is None
    assert g2p.phonemize("안녕하세요")


def test_pure_hangul_does_not_load_cmudict() -> None:
    g2p = KoreanG2P(use_dict=False)
    assert g2p.phonemize("안녕하세요")
    assert g2p.g2pk._cmu is None


def test_unknown_korean_options_are_rejected() -> None:
    with pytest.raises(TypeError, match="Unsupported KoreanG2P options"):
        KoreanG2P(use_dict=False, use_mecab=True)


def test_factory_forwards_korean_voice() -> None:
    from kokorog2p import clear_cache, get_g2p

    clear_cache()
    assert get_g2p("ko", voice="jf_alpha").voice == "jf_alpha"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("학교", "학꾜"),
        ("국밥", "국빱"),
        ("굳이", "구지"),
        ("옷이", "오시"),
        ("놓고", "노코"),
        ("신라", "실라"),
        ("12시 12분", "열두시 십이분"),
        ("1개", "한개"),
        ("2명", "두명"),
        ("3마리", "세마리"),
    ],
    ids=lambda case: case[0],
)
def test_g2pkc_intermediate_regressions(source: str, expected: str) -> None:
    g2p = KoreanG2P(use_dict=False, output="jamo", to_syl=True)
    assert g2p.phonemize(source) == expected


def test_korean_semantic_fallback_preserves_source_coordinates() -> None:
    from kokorog2p.pipeline_api import _spokenform_replacements_for_run

    source = "prefix 20°C and ₩5000"
    replacements = _spokenform_replacements_for_run(source, "ko")
    assert [(item.start, item.end) for item in replacements] == [
        (7, 11),
        (16, 21),
    ]
    assert [item.text for item in replacements] == ["섭씨 20도", "5000원"]
