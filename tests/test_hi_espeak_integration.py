"""Integration coverage for the real eSpeak-NG Hindi voice."""

import pytest

from kokorog2p import phonemize_prepared
from kokorog2p.vocab import validate_for_kokoro


@pytest.mark.espeak
def test_hindi_espeak_corpus_is_kokoro_v1_compatible(has_espeak: bool) -> None:
    if not has_espeak:
        pytest.skip("eSpeak-NG is not available")

    corpus = [
        "नमस्ते दुनिया",
        "यह एक परीक्षण है",
        "भारत एक विशाल देश है",
        "कृपया ध्यान दें",
        "हिंदी भाषा बहुत सुंदर है",
        "फ़िल्म ज़िंदगी ख़ुशी ग़ज़ल क़लम",
        "क्षेत्र ज्ञान श्रद्धा",
    ]
    for text in corpus:
        result = phonemize_prepared(
            text,
            language="hi",
            return_ids=True,
        )
        assert result.phonemes
        assert result.token_ids
        assert validate_for_kokoro(result.phonemes, model="1.0")[0] is True
