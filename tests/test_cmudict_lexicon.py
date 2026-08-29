from kokorog2p import available_lexicons
from kokorog2p.en.arpabet import arpabet_to_kokoro


def test_cmudict_is_not_selectable_without_pinned_source_and_provenance() -> None:
    assert "cmudict" not in available_lexicons("en-us")


def test_cmudict_decoder_preserves_deterministic_variants_after_lookup() -> None:
    variants = ("HH AH0 L OW1", "HH EH1 L OW0")
    assert tuple(arpabet_to_kokoro(variant) for variant in variants) == (
        "həlˈO",
        "hˈɛlO",
    )
