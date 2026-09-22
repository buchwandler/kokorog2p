from kokorog2p.en.phoneme_codec import MISAKI_V1, EnglishFrontendProfile
from kokorog2p.en.realization import (
    finalize_english_phonemes,
    validate_final_english_phonemes,
)


def test_misaki_v1_finalization_rewrites_flap_and_glottal() -> None:
    assert finalize_english_phonemes("ɹɾʔ", profile=MISAKI_V1) == "ɹTt"


def test_finalization_profile_can_disable_legacy_rewrites() -> None:
    profile = EnglishFrontendProfile(
        "modern",
        legacy_flap_token=None,
        glottal_rewrite=None,
    )
    assert finalize_english_phonemes("ɹɾʔ", profile=profile) == "ɹɾʔ"


def test_final_output_validation_includes_legacy_flap_token() -> None:
    assert validate_final_english_phonemes("ˈlOɹdT")
    assert not validate_final_english_phonemes("Q")
    assert validate_final_english_phonemes("Q", british=True)
