"""Dependency-free compatibility tests for SSMD and phrasplit-shaped objects."""

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec

import pytest

from kokorog2p.integrations import (
    overrides_for_segment,
    overrides_from_ssmd,
    phonemize_segments,
)
from kokorog2p.types import OverrideSpan, PhonemizeResult


@dataclass
class AnnotationSpan:
    char_start: int
    char_end: int
    attrs: dict[str, str]
    kind: str | None = None
    node_id: str | None = None


@dataclass
class SplitSegment:
    text: str
    char_start: int
    char_end: int
    sentence_index: int = 0


def test_ssmd_ph_attribute_is_normalized_and_dispatch_metadata_is_removed():
    attrs = {"ph": "wɜːd", "tag": "pronunciation", "rating": "5"}
    converted = overrides_from_ssmd([AnnotationSpan(0, 4, attrs)])

    assert converted == [OverrideSpan(0, 4, {"ph": "wɜːd", "rating": "5"})]
    assert attrs == {"ph": "wɜːd", "tag": "pronunciation", "rating": "5"}


def test_ssmd_ipa_and_language_alias_are_normalized():
    converted = overrides_from_ssmd(
        [AnnotationSpan(0, 7, {"ipa": "təˈmeɪtoʊ", "language": "en-US"})]
    )

    assert converted == [OverrideSpan(0, 7, {"ph": "təˈmeɪtoʊ", "lang": "en-US"})]


@pytest.mark.parametrize("attrs", [{"sampa": "t@meItoU"}, {"alphabet": "x-sampa"}])
def test_ssmd_xsampa_is_rejected_instead_of_treated_as_ipa(attrs):
    with pytest.raises(ValueError, match="X-SAMPA"):
        overrides_from_ssmd([AnnotationSpan(0, 7, attrs)])


def test_ssmd_xsampa_convert_mode_is_explicitly_unavailable():
    with pytest.raises(ValueError, match="conversion is not available"):
        overrides_from_ssmd(
            [AnnotationSpan(0, 7, {"sampa": "t@meItoU"})], xsampa="convert"
        )


def test_ssmd_adapter_validates_document_bounds_and_adjacent_spans():
    spans = [
        AnnotationSpan(0, 3, {"ph": "wʌn"}),
        AnnotationSpan(3, 6, {"ipa": "tuː"}),
    ]

    assert overrides_from_ssmd(spans, text_length=6) == [
        OverrideSpan(0, 3, {"ph": "wʌn"}),
        OverrideSpan(3, 6, {"ph": "tuː"}),
    ]
    with pytest.raises(ValueError, match="exceeds text length"):
        overrides_from_ssmd([AnnotationSpan(0, 7, {"ph": "too long"})], text_length=6)


def test_document_spans_are_intersected_and_rebased_for_each_segment():
    clean_text = "one one"
    segments = [SplitSegment("one", 0, 3), SplitSegment("one", 4, 7)]
    document_overrides = [AnnotationSpan(0, 7, {"ph": "wʌn"})]

    assert overrides_for_segment(0, 3, document_overrides) == [
        OverrideSpan(0, 3, {"ph": "wʌn"})
    ]
    assert overrides_for_segment(4, 7, document_overrides) == [
        OverrideSpan(0, 3, {"ph": "wʌn"})
    ]
    assert all(clean_text[s.char_start : s.char_end] == s.text for s in segments)


def test_rebasing_preserves_whitespace_gaps_and_does_not_search_text():
    overrides = [AnnotationSpan(2, 9, {"lang": "fr"})]

    assert overrides_for_segment(0, 5, overrides) == [
        OverrideSpan(2, 5, {"lang": "fr"})
    ]
    assert overrides_for_segment(6, 11, overrides) == [
        OverrideSpan(0, 3, {"lang": "fr"})
    ]


def test_phonemize_segments_validates_exact_slices_and_passes_local_overrides():
    calls: list[tuple[str, list[OverrideSpan]]] = []

    def fake_phonemize(text: str, *, overrides: list[OverrideSpan], **_kwargs):
        calls.append((text, overrides))
        return PhonemizeResult(clean_text=text, tokens=[])

    results = phonemize_segments(
        "one two",
        [SplitSegment("one", 0, 3), SplitSegment("two", 4, 7)],
        [AnnotationSpan(0, 7, {"ph": "test"})],
        phonemize=fake_phonemize,
    )

    assert [result.clean_text for result in results] == ["one", "two"]
    assert calls == [
        ("one", [OverrideSpan(0, 3, {"ph": "test"})]),
        ("two", [OverrideSpan(0, 3, {"ph": "test"})]),
    ]
    with pytest.raises(ValueError, match="does not match"):
        phonemize_segments(
            "one two",
            [SplitSegment("wrong", 0, 3)],
            phonemize=fake_phonemize,
        )


def test_numeric_dotted_units_remain_one_normalized_offset_span():
    from kokorog2p import phonemize
    from kokorog2p.de.g2p import GermanG2P

    source = "1 ltr. Milch und danach 2 Min. ruhen."
    segments = [SplitSegment(source, 0, len(source))]
    g2p = GermanG2P(
        use_lexicon=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    results = phonemize_segments(
        source,
        segments,
        phonemize=phonemize,
        language="de",
        g2p=g2p,
        return_ids=False,
    )

    assert results[0].extended_text == "ein Liter Milch und danach zwei Minuten ruhen."
    unit = next(token for token in results[0].tokens if token.text == "1 ltr.")
    assert source[unit.char_start : unit.char_end] == "1 ltr."
    assert unit.extended_text == "ein Liter"


def test_installed_phrasplit_and_ssmd_pipeline_uses_clean_text_coordinates():
    if find_spec("phrasplit") is None or find_spec("ssmd") is None:
        pytest.skip("phrasplit and ssmd are optional integration dependencies")

    import phrasplit
    import ssmd

    phrasplit_version = tuple(int(part) for part in version("phrasplit").split(".")[:3])
    assert phrasplit_version >= (0, 3, 4)
    try:
        ssmd_version = version("ssmd")
    except PackageNotFoundError:
        pytest.skip("ssmd import is available without distribution metadata")
    if ssmd_version != "0.8.0":
        pytest.skip(f"SSMD compatibility target is 0.8.0, found {ssmd_version}")

    source = "---\ntitle: demo\n---\nSay [tomato]{ipa='təˈmeɪtoʊ'}. Next."
    parsed = ssmd.parse_spans(source)
    overrides = overrides_from_ssmd(parsed.annotations)
    segments = phrasplit.split_with_offsets(
        parsed.clean_text, mode="sentence", language="en", use_spacy=None
    )

    from kokorog2p import get_g2p, phonemize

    g2p = get_g2p(
        "en-us",
        use_spacy=None,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    results = []
    for segment in segments:
        assert parsed.clean_text[segment.char_start : segment.char_end] == segment.text
        results.append(
            phonemize(
                segment.text,
                g2p=g2p,
                overrides=overrides_for_segment(
                    segment.char_start, segment.char_end, overrides
                ),
                use_spacy=None,
            )
        )

    assert len(results) == len(segments)
    assert any(
        token.meta.get("ph") == "təˈmeɪtoʊ"
        for result in results
        for token in result.tokens
    )
