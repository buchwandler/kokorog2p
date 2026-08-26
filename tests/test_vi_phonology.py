"""Broad Northern Vietnamese phonology tests."""

import pytest

from kokorog2p.vi.model_profile import validate_output
from kokorog2p.vi.phonology import map_coda, map_nucleus, map_onset, syllable_to_phones
from kokorog2p.vi.render import TONE_RENDER, render_syllable
from kokorog2p.vi.syllable import VietnameseTone, parse_syllable


@pytest.mark.parametrize(
    "onset", ["b", "ch", "đ", "gh", "kh", "ng", "nh", "ph", "qu", "th", "tr", "x"]
)
def test_onset_maps_to_supported_abstract_phones(onset: str) -> None:
    word = onset + ("e" if onset in {"gh", "ngh"} else "a")
    syllable = parse_syllable(word)
    phones = map_onset(syllable.onset)
    assert phones
    assert all(isinstance(phone, str) for phone in phones)


@pytest.mark.parametrize(
    "nucleus", ["a", "ă", "â", "e", "ê", "i", "o", "ô", "ơ", "u", "ư", "iê", "uô", "ươ"]
)
def test_nuclei_have_independent_mappings(nucleus: str) -> None:
    assert map_nucleus(nucleus)


def test_medial_and_offglide_are_structural() -> None:
    hoa = parse_syllable("hoa")
    mai = parse_syllable("mai")
    assert hoa.medial == "o"
    assert mai.coda == "i"
    assert "w" in syllable_to_phones(hoa)
    assert "j" in syllable_to_phones(mai)
    assert map_coda("ng") == ("ŋ",)


def test_all_tone_renderings_are_distinct_and_model_valid() -> None:
    rendered = {
        tone: render_syllable(
            parse_syllable(
                {
                    VietnameseTone.NGANG: "ba",
                    VietnameseTone.HUYEN: "bà",
                    VietnameseTone.HOI: "bả",
                    VietnameseTone.NGA: "bã",
                    VietnameseTone.SAC: "bá",
                    VietnameseTone.NANG: "bạ",
                }[tone]
            )
        )
        for tone in VietnameseTone
    }
    assert set(rendered.values()) == {
        "ba" + TONE_RENDER[tone] for tone in VietnameseTone
    }
    for text in rendered.values():
        assert validate_output(text) == (True, [])


def test_curated_gold_cases_match_structural_renderer() -> None:
    import json
    from pathlib import Path

    from kokorog2p.vi.render import render_syllable

    data_path = Path(__file__).parent / "data" / "vi_gold.json"
    cases = json.loads(data_path.read_text(encoding="utf-8"))
    assert len(cases) >= 30
    for case in cases:
        syllable = parse_syllable(case["text"])
        assert syllable.tone.value == case["tone"]
        assert list(syllable_to_phones(syllable)) == case["segments"]
        assert render_syllable(syllable) == case["expected"]
        assert validate_output(case["expected"]) == (True, [])
