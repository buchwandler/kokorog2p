"""Shared model-facing English realization helpers."""

from __future__ import annotations

from collections.abc import Sequence

from kokorog2p.en.lexicon import PRIMARY_STRESS, SECONDARY_STRESS, stress_weight
from kokorog2p.en.phoneme_codec import MISAKI_V1, EnglishFrontendProfile
from kokorog2p.en.subtokens import EnglishSubtoken
from kokorog2p.vocab import get_english_vocab

_FINAL_PROFILE_SYMBOLS = frozenset({"T"})


def _demote_primary_stress(phonemes: str) -> str:
    return phonemes.replace(PRIMARY_STRESS, SECONDARY_STRESS, 1)


def resolve_compound_stress(
    tokens: Sequence[EnglishSubtoken],
    *,
    british: bool = False,
    profile: EnglishFrontendProfile = MISAKI_V1,
) -> None:
    """Balance primary stress across realized lexical compound subtokens."""
    if not profile.resolve_compound_stress or len(tokens) < 2:
        return
    stressed = [
        (index, token)
        for index, token in enumerate(tokens)
        if token.phonemes and PRIMARY_STRESS in token.phonemes
    ]
    if len(stressed) < 2:
        return

    candidates = stressed
    if tokens[0].is_letter_name and len(candidates) > 1:
        candidates = [item for item in candidates if item[0] != 0]
    anchor_index, _ = max(
        candidates,
        key=lambda item: (stress_weight(item[1].phonemes), -item[0]),
    )
    for index, token in stressed:
        if index != anchor_index and token.phonemes is not None:
            token.phonemes = _demote_primary_stress(token.phonemes)


def finalize_english_phonemes(
    phonemes: str,
    *,
    profile: EnglishFrontendProfile = MISAKI_V1,
) -> str:
    """Apply the selected legacy frontend's final model-facing rewrites."""
    result = phonemes
    if profile.legacy_flap_token is not None:
        result = result.replace("ɾ", profile.legacy_flap_token)
    if profile.glottal_rewrite is not None:
        result = result.replace("ʔ", profile.glottal_rewrite)
    return result


def validate_final_english_phonemes(phonemes: str, *, british: bool = False) -> bool:
    """Check final English output against the target model's English inventory."""
    vocabulary = get_english_vocab(british) | _FINAL_PROFILE_SYMBOLS
    return all(char in vocabulary or char.isspace() for char in phonemes)


__all__ = [
    "finalize_english_phonemes",
    "resolve_compound_stress",
    "validate_final_english_phonemes",
]
