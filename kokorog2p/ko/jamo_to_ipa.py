"""Korean Jamo to IPA conversion.

This module converts Korean jamo (consonants and vowels) to IPA phonemes
for use with Kokoro TTS.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

# Jamo consonants (초성/종성 - onset/coda)
JAMO_CONSONANTS_TO_IPA = {
    # Basic consonants
    "ㄱ": "k",  # 기역
    "ㄲ": "k͈",  # 쌍기역 (tensed k)
    "ㄴ": "n",  # 니은
    "ㄷ": "t",  # 디귿
    "ㄸ": "t͈",  # 쌍디귿 (tensed t)
    "ㄹ": "l",  # 리을 (can also be r in onset)
    "ㅁ": "m",  # 미음
    "ㅂ": "p",  # 비읍
    "ㅃ": "p͈",  # 쌍비읍 (tensed p)
    "ㅅ": "s",  # 시옷
    "ㅆ": "s͈",  # 쌍시옷 (tensed s)
    "ㅇ": "",  # 이응 (silent in onset, ŋ in coda)
    "ㅈ": "ʨ",  # 지읒 (alveolo-palatal affricate)
    "ㅉ": "ʨ͈",  # 쌍지읒 (tensed)
    "ㅊ": "ʨʰ",  # 치읓 (aspirated)
    "ㅋ": "kʰ",  # 키읔 (aspirated)
    "ㅌ": "tʰ",  # 티읕 (aspirated)
    "ㅍ": "pʰ",  # 피읖 (aspirated)
    "ㅎ": "h",  # 히읗
    # Jamo modern (U+1100-11FF range - combining jamo)
    "ᄀ": "k",
    "ᄁ": "k͈",
    "ᄂ": "n",
    "ᄃ": "t",
    "ᄄ": "t͈",
    "ᄅ": "l",
    "ᄆ": "m",
    "ᄇ": "p",
    "ᄈ": "p͈",
    "ᄉ": "s",
    "ᄊ": "s͈",
    "ᄋ": "",
    "ᄌ": "ʨ",
    "ᄍ": "ʨ͈",
    "ᄎ": "ʨʰ",
    "ᄏ": "kʰ",
    "ᄐ": "tʰ",
    "ᄑ": "pʰ",
    "ᄒ": "h",
    # Coda consonants (different pronunciation)
    "ᆨ": "k̚",  # unreleased k
    "ᆩ": "k̚",
    "ᆫ": "n",
    "ᆬ": "n",
    "ᆭ": "n",
    "ᆮ": "t̚",  # unreleased t
    "ᆯ": "l",
    "ᆰ": "l",
    "ᆱ": "l",
    "ᆲ": "l",
    "ᆳ": "l",
    "ᆴ": "l",
    "ᆵ": "l",
    "ᆶ": "l",
    "ᆷ": "m",
    "ᆸ": "p̚",  # unreleased p
    "ᆹ": "p̚",
    "ᆺ": "t̚",
    "ᆻ": "t̚",
    "ᆼ": "ŋ",
    "ᆽ": "t̚",
    "ᆾ": "t̚",
    "ᆿ": "k̚",
    "ᇀ": "t̚",
    "ᇁ": "p̚",
    "ᇂ": "t̚",
}

# Jamo vowels (중성 - nucleus)
JAMO_VOWELS_TO_IPA = {
    # Basic vowels
    "ㅏ": "a",  # 아
    "ㅐ": "ɛ",  # 애
    "ㅑ": "ja",  # 야
    "ㅒ": "jɛ",  # 얘
    "ㅓ": "ʌ",  # 어
    "ㅔ": "e",  # 에
    "ㅕ": "jʌ",  # 여
    "ㅖ": "je",  # 예
    "ㅗ": "o",  # 오
    "ㅘ": "wa",  # 와
    "ㅙ": "wɛ",  # 왜
    "ㅚ": "ø",  # 외 (or we)
    "ㅛ": "jo",  # 요
    "ㅜ": "u",  # 우
    "ㅝ": "wʌ",  # 워
    "ㅞ": "we",  # 웨
    "ㅟ": "wi",  # 위
    "ㅠ": "ju",  # 유
    "ㅡ": "ɯ",  # 으
    "ㅢ": "ɰi",  # 의
    "ㅣ": "i",  # 이
    # Jamo modern (U+1100-11FF range - combining jamo)
    "ᅡ": "a",
    "ᅢ": "ɛ",
    "ᅣ": "ja",
    "ᅤ": "jɛ",
    "ᅥ": "ʌ",
    "ᅦ": "e",
    "ᅧ": "jʌ",
    "ᅨ": "je",
    "ᅩ": "o",
    "ᅪ": "wa",
    "ᅫ": "wɛ",
    "ᅬ": "ø",
    "ᅭ": "jo",
    "ᅮ": "u",
    "ᅯ": "wʌ",
    "ᅰ": "we",
    "ᅱ": "wi",
    "ᅲ": "ju",
    "ᅳ": "ɯ",
    "ᅴ": "ɰi",
    "ᅵ": "i",
}


def to_positional_jamo(text: str) -> str:
    """Convert Hangul syllables to positional Unicode Jamo.

    Compatibility Jamo input is retained as-is because it does not encode
    onset and coda roles. Callers that need unambiguous conversion should
    pass composed Hangul or positional Jamo.
    """
    from jamo import h2j

    return h2j(text)



def jamo_to_ipa(text: str) -> str:
    """Convert composed or positional Korean Jamo to IPA-like phonemes.

    Positional Jamo is required to distinguish onset and coda consonants.
    In particular, final ㅇ maps to ``ŋ`` and final stops retain their
    unreleased-stop symbols.
    """
    positional = to_positional_jamo(text)

    result = []
    for char in positional:
        if char in JAMO_CONSONANTS_TO_IPA:
            ipa = JAMO_CONSONANTS_TO_IPA[char]
            if ipa:
                result.append(ipa)
        elif char in JAMO_VOWELS_TO_IPA:
            result.append(JAMO_VOWELS_TO_IPA[char])
        else:
            result.append(char)

    return "".join(result)
