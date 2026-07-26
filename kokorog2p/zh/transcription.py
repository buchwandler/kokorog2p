"""Pinyin to IPA transcription for Chinese.

ADAPTED from https://github.com/stefantaubert/pinyin-to-ipa/blob/master/src/pinyin_to_ipa/transcription.py
Original License: MIT

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import itertools
from collections.abc import Generator

from ordered_set import OrderedSet
from pypinyin.contrib.tone_convert import to_finals, to_initials, to_normal, to_tone3

# References:
# https://en.wikipedia.org/wiki/Help:IPA/Mandarin
# https://en.wikipedia.org/wiki/Standard_Chinese_phonology
# https://en.wikipedia.org/wiki/Pinyin
# https://de.wikipedia.org/wiki/Pinyin
# Duanmu, San. 2007. The Phonology of Standard Chinese. 2nd ed.
# Oxford ; New York: Oxford University Press.
# Lin, Yen-Hwei. 2007. The Sounds of Chinese.
# Cambridge, UK ; New York: Cambridge University Press.


INITIAL_MAPPING: dict[str, list[tuple[str, ...]]] = {
    "b": [("p",)],
    "c": [("ʦʰ",)],  # tsʰ
    "ch": [("\uab67ʰ",)],  # ʈʂʰ
    "d": [("t",)],
    "f": [("f",)],
    "g": [("k",)],
    "h": [("x",), ("h",)],
    "j": [("ʨ",)],
    "k": [("kʰ",)],
    "l": [("l",)],
    "m": [("m",)],
    "n": [("n",)],
    "p": [("pʰ",)],
    "q": [("ʨʰ",)],
    "r": [("ɻ",), ("ʐ",)],
    "s": [("s",)],
    "sh": [("ʂ",)],
    "t": [("tʰ",)],
    "x": [("ɕ",)],
    "z": [("ʦ",)],
    "zh": [("\uab67",)],  # tʂ
    # w and y only occur in non-strict initials
    # "w": [("w",)],
    # "y": [("j",), ("ɥ",)],
}

INITIALS = INITIAL_MAPPING.keys()

# Note: Syllabic consonants may also arise as a result of weak syllable reduction.
# Syllabic nasal consonants are also heard in certain interjections;
# pronunciations of such words include [m], [n], [ŋ], [hm], [hŋ].
SYLLABIC_CONSONANT_MAPPINGS: dict[str, list[tuple[str, ...]]] = {
    "hm": [("h", "m0")],
    "hng": [("h", "ŋ0")],
    "m": [("m0",)],
    "n": [("n0",)],
    "ng": [("ŋ0",)],
}

SYLLABIC_CONSONANTS = SYLLABIC_CONSONANT_MAPPINGS.keys()

INTERJECTION_MAPPINGS: dict[str, list[tuple[str, ...]]] = {
    "io": [("j", "ɔ0")],  # /
    "ê": [("ɛ0",)],  # /
    # Note: In a small number of independent words or morphemes pronounced [ɚ] or [aɚ̯],
    # written in pinyin as er (with some tone), such as 二 èr "two", 耳 ěr "ear",
    # and 儿 (traditional 兒) ér "son". Similar to the sound in bar in English.
    # Can also be pronounced [ɚ] depending on the speaker.
    # Duanmu (2007, p. 40)
    "er": [("ɚ0",), ("aɚ̯0",)],  # ɑɻ
    "o": [("ɔ0",)],  # ɔ
}

INTERJECTIONS = INTERJECTION_MAPPINGS.keys()


# Duanmu (2000, p. 37) and Lin (2007, p. 68f)
# Diphtongs from Duanmu (2007, p. 40): au, əu, əi, ai
# Diphthongs from Lin (2007, p. 68f): au̯, ou̯, ei̯, ai̯
FINAL_MAPPING: dict[str, list[tuple[str, ...]]] = {
    "a": [("a0",)],  # /
    "ai": [("ai̯0",)],  # aɪ̯
    "an": [("a0", "n")],  # an
    "ang": [("a0", "ŋ")],  # ɑŋ
    "ao": [("au̯0",)],  # ɑʊ̯
    "e": [("ɤ0",)],  # ɯ̯ʌ
    "ei": [("ei̯0",)],  # eɪ̯
    "en": [("ə0", "n")],  # ən
    "eng": [("ə0", "ŋ")],  # əŋ
    "i": [("i0",)],  # i
    "ia": [("j", "a0")],  # i̯ɑ
    "ian": [("j", "ɛ0", "n")],  # iɛn
    "iang": [("j", "a0", "ŋ")],  # i̯ɑŋ
    "iao": [("j", "au̯0")],  # i̯ɑʊ̯
    "ie": [("j", "e0")],  # iɛ
    "in": [("i0", "n")],  # in
    # "iu": [("j", "ou̯0")], # i̯ɤʊ̯
    "iou": [("j", "ou̯0")],  # i̯ɤʊ̯
    "ing": [("i0", "ŋ")],  # iŋ
    "iong": [("j", "ʊ0", "ŋ")],  # i̯ʊŋ
    "ong": [("ʊ0", "ŋ")],  # ʊŋ
    "ou": [("ou̯0",)],  # ɤʊ̯
    "u": [("u0",)],  # u
    # "ui": [("w", "ei̯0")], # u̯eɪ̯
    "uei": [("w", "ei̯0")],  # u̯eɪ̯
    "ua": [("w", "a0")],  # u̯ɑ
    "uai": [("w", "ai̯0")],  # u̯aɪ̯
    "uan": [("w", "a0", "n")],  # u̯an
    # "un": [("w", "ə0", "n")], # u̯ən
    "uen": [("w", "ə0", "n")],  # u̯ən
    "uang": [("w", "a0", "ŋ")],  # u̯ɑŋ
    "ueng": [("w", "ə0", "ŋ")],  # /
    # see: https://en.wikipedia.org/wiki/Pinyin "Finals beginning with u- (w-)"
    "uo": [("w", "o0")],  # u̯ɔ
    # Normally uo is written as o after b, p, m, or f
    # other cases (lo, yo) also considered as [wo]
    "o": [("w", "o0")],  # u̯ɔ
    # Note: Normally ü is written as u after j, q, or x
    #       (the /u/ phoneme never occurs in these positions)
    #       pypinyin returns u as ü after (y), j, q, or x
    "ü": [("y0",)],  # u after y, j, q, or x ; # y
    "üe": [("ɥ", "e0")],  # ue after y, j, q, or x ; # y̯œ
    "üan": [("ɥ", "ɛ0", "n")],  # uan after y, j, q, or x ; # /
    "ün": [("y0", "n")],  # un after y, j, q, or x
}

FINALS = FINAL_MAPPING.keys()

# Note: [ɻ̩ ~ ʐ̩], an apical retroflex voiced continuant
#       in zhi, chi, shi, ri ([ʈʂɻ̩ ʈʂʰɻ̩ ʂɻ̩ ɻɻ̩]).
# Duanmu (2007, p. 34f)
# Lin (2007, p. 72)
FINAL_MAPPING_AFTER_ZH_CH_SH_R: dict[str, list[tuple[str, ...]]] = {
    "i": [("ɻ̩0",), ("ʐ̩0",)],  # ʅ
}

# Note: [ɹ̩ ~ z̩], a laminal denti-alveolar voiced continuant,
#       in zi, ci, si ([tsɹ̩ tsʰɹ̩ sɹ̩]);
# Duanmu (2007, p. 34f)
# Lin (2007, p. 72)
FINAL_MAPPING_AFTER_Z_C_S: dict[str, list[tuple[str, ...]]] = {
    "i": [("ɹ̩0",), ("z̩0",)],  # ɿ
}

TONE_MAPPING = {
    1: "˥",  # ā
    2: "˧˥",  # á
    3: "˧˩˧",  # ǎ
    4: "˥˩",  # à
    5: "",  # a
}


def get_tone(pinyin: str) -> int:
    """Get the tone number from a pinyin string."""
    pinyin_tone3 = to_tone3(pinyin, neutral_tone_with_five=True, v_to_u=True)
    if len(pinyin_tone3) == 0:
        raise ValueError("Parameter 'pinyin': Tone couldn't be detected!")

    tone_nr_str = pinyin_tone3[-1]

    try:
        tone_nr = int(tone_nr_str)
    except ValueError as error:
        raise ValueError(
            f"Parameter 'pinyin': Tone '{tone_nr_str}' couldn't be detected!"
        ) from error

    # Note: in case to_tone3 returns other values than expected
    if tone_nr not in TONE_MAPPING:
        raise ValueError(
            f"Parameter 'pinyin': Tone '{tone_nr_str}' couldn't be detected!"
        )

    return tone_nr


def get_syllabic_consonant(normal_pinyin: str) -> str | None:
    """Check if the pinyin is a syllabic consonant."""
    if normal_pinyin in SYLLABIC_CONSONANTS:
        return normal_pinyin
    return None


def get_interjection(normal_pinyin: str) -> str | None:
    """Check if the pinyin is an interjection."""
    if normal_pinyin in INTERJECTIONS:
        return normal_pinyin
    return None


def get_initials(normal_pinyin: str) -> str | None:
    """Get the initial consonant from pinyin."""
    if normal_pinyin in SYLLABIC_CONSONANTS:
        return None

    if normal_pinyin in INTERJECTIONS:
        return None

    pinyin_initial = to_initials(normal_pinyin, strict=True)

    if pinyin_initial == "":
        return None

    # in case pypinyin returns unexpected result
    if pinyin_initial not in INITIAL_MAPPING:
        raise ValueError(
            f"Parameter 'normal_pinyin': "
            f"Initial '{pinyin_initial}' couldn't be detected!"
        )

    return pinyin_initial


def get_finals(normal_pinyin: str) -> str | None:
    """Get the final from pinyin."""
    if normal_pinyin in SYLLABIC_CONSONANTS:
        return None

    if normal_pinyin in INTERJECTIONS:
        return None

    pinyin_final = to_finals(normal_pinyin, strict=True, v_to_u=True)

    if pinyin_final == "":
        raise ValueError("Parameter 'normal_pinyin': Final couldn't be detected!")

    # in case pypinyin returns unexpected result
    if pinyin_final not in FINAL_MAPPING:
        raise ValueError(
            f"Parameter 'normal_pinyin': Final '{pinyin_final}' couldn't be detected!"
        )

    return pinyin_final


def apply_tone(
    variants: list[tuple[str, ...]], tone: int
) -> Generator[tuple[str, ...], None, None]:
    """Apply tone markers to IPA variants."""
    tone_ipa = TONE_MAPPING[tone]
    yield from (
        tuple(phoneme.replace("0", tone_ipa) for phoneme in variant)
        for variant in variants
    )


def pinyin_to_ipa(pinyin: str) -> OrderedSet[tuple[str, ...]]:
    """Convert pinyin to IPA transcription.

    Args:
        pinyin: Pinyin string with tone marker.

    Returns:
        OrderedSet of possible IPA transcriptions.
    """
    tone_nr = get_tone(pinyin)
    pinyin_normal = to_normal(pinyin)

    interjection = get_interjection(pinyin_normal)
    if interjection is not None:
        interjection_ipa_mapping = INTERJECTION_MAPPINGS[pinyin_normal]
        interjection_ipa = OrderedSet(apply_tone(interjection_ipa_mapping, tone_nr))
        return interjection_ipa

    syllabic_consonant = get_syllabic_consonant(pinyin_normal)
    if syllabic_consonant is not None:
        syllabic_consonant_ipa_mapping = SYLLABIC_CONSONANT_MAPPINGS[syllabic_consonant]
        syllabic_consonant_ipa = OrderedSet(
            apply_tone(syllabic_consonant_ipa_mapping, tone_nr)
        )
        return syllabic_consonant_ipa

    parts = []
    pinyin_initial = get_initials(pinyin_normal)
    pinyin_final = get_finals(pinyin_normal)
    assert pinyin_final is not None

    if pinyin_initial is not None:
        initial_phonemes = INITIAL_MAPPING[pinyin_initial]
        parts.append(initial_phonemes)

    final_phonemes: list[tuple[str, ...]]
    if (
        pinyin_initial in {"zh", "ch", "sh", "r"}
        and pinyin_final in FINAL_MAPPING_AFTER_ZH_CH_SH_R
    ):
        final_phonemes = FINAL_MAPPING_AFTER_ZH_CH_SH_R[pinyin_final]
    elif (
        pinyin_initial in {"z", "c", "s"} and pinyin_final in FINAL_MAPPING_AFTER_Z_C_S
    ):
        final_phonemes = FINAL_MAPPING_AFTER_Z_C_S[pinyin_final]
    else:
        final_phonemes = FINAL_MAPPING[pinyin_final]

    final_phonemes = list(apply_tone(final_phonemes, tone_nr))
    parts.append(final_phonemes)

    assert len(parts) >= 1

    all_syllable_combinations = OrderedSet(
        tuple(itertools.chain.from_iterable(combination))
        for combination in itertools.product(*parts)
    )

    return all_syllable_combinations
