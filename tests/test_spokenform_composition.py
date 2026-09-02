"""Optional composition coverage for Spokenform-owned semantic preparation."""

import pytest

from kokorog2p import phonemize_prepared

spokenform = pytest.importorskip("spokenform")
prepare_for_kokorog2p = spokenform.prepare_for_kokorog2p


def test_released_spokenform_prepares_then_core_phonemizes() -> None:
    prepared = prepare_for_kokorog2p(
        "Meet Dr. Smith at 2 kg.", language="en"
    ).spoken_text
    result = phonemize_prepared(prepared, language="en-us", use_spacy=False)

    assert prepared != "Meet Dr. Smith at 2 kg."
    assert result.clean_text == prepared
    assert result.phonemes
