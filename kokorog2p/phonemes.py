"""Phoneme vocabularies and mappings for Kokoro TTS.

This module defines the phoneme inventories for US and British English,
along with mappings for converting between espeak IPA and Kokoro phonemes.
"""

import re
from typing import Final

# =============================================================================
# Phoneme Vocabularies
# =============================================================================

# Shared phonemes between US and GB (41 total)
# - Stress marks: ˈ ˌ
# - IPA consonants: b d f h j k l m n p s t v w z ɡ ŋ ɹ ʃ ʒ ð θ
# - Consonant clusters: ʤ ʧ
# - IPA vowels: ə i u ɑ ɔ ɛ ɜ ɪ ʊ ʌ
# - Diphthongs: A I W Y (representing eɪ aɪ aʊ ɔɪ)
# - Custom: ᵊ (small schwa)
SHARED_PHONES: Final[frozenset[str]] = frozenset(
    "AIWYbdfhijklmnpstuvwzðŋɑɔəɛɜɡɪɹʃʊʌʒʤʧˈˌθᵊ"
)

# US-only phonemes (5 total)
# - Vowels: æ O ᵻ (O represents oʊ diphthong)
# - Consonants: ɾ (flap/tap), ʔ (glottal stop)
US_ONLY_PHONES: Final[frozenset[str]] = frozenset("Oæɾᵻʔ")

# GB-only phonemes (4 total)
# - Vowels: a Q ɒ (Q represents əʊ diphthong)
# - Other: ː (vowel lengthener)
GB_ONLY_PHONES: Final[frozenset[str]] = frozenset("Qaɒː")

# Complete vocabularies (45 phonemes each)
US_VOCAB: Final[frozenset[str]] = SHARED_PHONES | US_ONLY_PHONES
GB_VOCAB: Final[frozenset[str]] = SHARED_PHONES | GB_ONLY_PHONES

# Japanese phoneme vocabulary (29 characters)
# - Basic vowels: a e i o u
# - Consonants: b d f g h j k m n p r s t w z
# - Special: ɕ (palatal fricative), ɴ (moraic n), ʔ (glottal stop)
# - Affricates: ʥ (voiced affricate), ʦ (voiceless affricate), ʨ (palatal affricate)
# - Length/special: ː (length marker), ᶄ, ᶉ (special markers)
JA_VOCAB: Final[frozenset[str]] = frozenset("abdefghijkmnoprstuwzɕɴʔʥʦʨːᶄᶉ")

# French phoneme vocabulary (35 characters)
# - Basic vowels: a e i o u y
# - Nasal vowels: ɑ̃ ɛ̃ œ̃ ɔ̃ (represented as combining character + ̃)
# - Oral vowels: ɑ ɔ ə ɛ ø œ
# - Consonants: b d f g j k l m n p s t v w z
# - Special: ʁ (uvular fricative), ʃ (sh), ʒ (zh), ɡ (g), ɥ (ɥ)
# Note: Includes punctuation marks: ' , -
FR_VOCAB: Final[frozenset[str]] = frozenset("',-abdefijklmnopstuvwyzøœɑɔəɛɡɥʁʃʒ̃")

# Korean phoneme vocabulary (23 characters)
# - Basic vowels: a e i o u
# - Special vowels: ø (외), ɛ (애/에), ɯ (으), ɰ (의 onset), ʌ (어)
# - Consonants: h j k l m n p s t w
# - Special consonant: ʨ (ㅈ/ㅊ affricate)
# - Modifiers: ʰ (aspiration), ͈ (tenseness)
# Note: Character-based like Japanese - each character represents one phoneme
# Note: Without MeCab, ŋ and ̚ are not produced (simplified phonology)
KO_VOCAB: Final[frozenset[str]] = frozenset("aehijklmnopstuwøɛɯɰʌʨʰ͈")

# Chinese (Mandarin) phoneme vocabulary (59 characters)
# Uses Zhuyin (Bopomofo) notation, NOT IPA
# - Zhuyin initials (21): ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙ
# - Zhuyin finals (16): ㄚㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦㄧㄨㄩ
# - Special finals (17): ㄭ (ii after z/c/s), 十 (iii after zh/ch/sh/r),
#   月 (ve/üe), 万 (wan), 中 (ong), 为 (wei), 压 (ia), 又 (you),
#   外 (wai), 应 (ing), 我 (uo), 王 (uang), 穵 (uar), 要 (iao),
#   言 (ian), 阳 (iang), R (erhua marker)
# - Tone markers (5): 1 (high level), 2 (rising), 3 (dipping), 4 (falling), 5 (neutral)
# - Punctuation: / (word boundary/pause marker)
# Note: Character-based like Japanese/Korean - each character represents one phoneme
# Note: Zhuyin is traditional Chinese phonetic notation used by Kokoro TTS
ZH_VOCAB: Final[frozenset[str]] = frozenset(
    "/12345Rㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙㄚㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦㄧㄨㄩㄭ万中为十压又外应我月王穵要言阳"
)

# Italian phoneme vocabulary (30 characters)
# - Basic vowels: a e i o u (always pronounced clearly, no reduction)
# - Consonants: b d f k l m n p r s t v z
# - Palatals: ɲ (gn as in "gnocchi"), ʎ (gli as in "famiglia")
# - Fricatives: ʃ (sc before e/i as in "pesce")
# - Affricates: ʦ (z voiceless), ʣ (z voiced), ʧ (c/ci voiceless), ʤ (g/gi voiced)
# - Special: ɡ (IPA g, U+0261), j (semivowel as in "ieri"), w (semivowel as in "uomo")
# - Stress marks: ˈ (primary stress)
# - Gemination: ː (length marker for double consonants)
# Note: Italian has predictable stress, but stress marks help with exceptions
# Note: All 5 vowels are always pronounced fully (no schwa reduction like English)
IT_VOCAB: Final[frozenset[str]] = frozenset("abedfijklmnoprstuvwzɡɲʃʎʦʣʧʤˈː")

# Spanish Phoneme Vocabulary (30 phonemes)
# - Vowels: a, e, i, o, u (5 pure vowels, always pronounced clearly)
# - Basic consonants: b, d, f, k, l, m, n, p, s, t, ɡ (IPA g)
# - Palatals: ɲ (ñ "niño"), ʎ (ll "lluvia"), ʧ (ch "chico")
# - Jota: x (j/g before e/i as in "jamón", "gente")
# - Theta: θ (z/c before e/i in European Spanish, "zapato", "cielo")
# - Taps/Trills: ɾ (single r, "pero"), r (rr or initial r, "perro", "rosa")
# - Approximants: β (soft b/v), ð (soft d), ɣ (soft g) - allophonic variants
# - Semivowels: j (y as in "yo"), w (u in diphthongs, "agua")
# - Stress: ˈ (primary stress marker)
# Note: Spanish has predictable stress rules, but accents mark exceptions (café, música)
# Note: For simplification, we use standard /b d g/ and soft variants are contextual
ES_VOCAB: Final[frozenset[str]] = frozenset("abdefijklmnoprstuwxβðɣɡɲɾʎʧθˈ")

# Brazilian Portuguese Phoneme Vocabulary (40 phonemes)
# - Oral vowels: a, e, ɛ, i, o, ɔ, u (7 vowels, e/o have open/closed variants)
# - Nasal vowels: ã, ẽ, ĩ, õ, ũ (5 nasal vowels - precomposed forms)
# - Basic consonants: b, d, f, k, l, m, n, p, s, t, v, z, ɡ (IPA g)
# - Palatals: ɲ (nh as in "ninho"), ʎ (lh as in "filho"), ʃ (x/ch as in "xadrez", "chá")
# - Affricates: ʤ (d+i in some dialects: "dia" → ʤia), ʧ (t+i: "tia" → ʧia)
# - Liquids: ɾ (single r: "caro"), r (strong r at start or rr: "rosa", "carro")
# - Fricative: ʒ (j/g+e/i: "já", "gente")
# - Semivowels: j (i in diphthongs: "pai"), w (u in diphthongs: "mau")
# - Nasalization: ̃ (combining tilde for composing nasal vowels)
# - Stress: ˈ (primary stress marker)
# Note: Brazilian Portuguese has rich vowel system with oral/nasal distinction
# Note: Affricate ization of /t d/ before /i/ is characteristic of Brazilian Portuguese
# Note: Final /r/ varies by dialect (ɾ, x, ʁ, h) - we use standard ɾ
PT_BR_VOCAB: Final[frozenset[str]] = frozenset("abdefijklmnoprstuvwzãẽĩõũɔɛɡɲɾʃʎʒʤʧˈ̃")

# =============================================================================
# IPA to Kokoro Mappings (for espeak conversion)
# =============================================================================

# Espeak to Kokoro phoneme mappings
# Sorted by length (descending) to ensure longest matches first
# Note: espeak uses Unicode combining tie (U+0361: ͡) for affricates/diphthongs
_ESPEAK_MAPPINGS: Final[dict[str, str]] = {
    # Remove nasalization
    "\u0303": "",
    # Diphthongs (with Unicode tie U+0361)
    "a͡ɪ": "I",  # aɪ -> I (eye sound)
    "a͡ʊ": "W",  # aʊ -> W (ow sound)
    "e͡ɪ": "A",  # eɪ -> A (ay sound)
    "ɔ͡ɪ": "Y",  # ɔɪ -> Y (oy sound)
    # Affricates (with Unicode tie U+0361)
    "d͡ʒ": "ʤ",  # dʒ -> ʤ (j sound)
    "t͡ʃ": "ʧ",  # tʃ -> ʧ (ch sound)
    # Diphthongs (with ASCII caret fallback)
    "a^ɪ": "I",  # aɪ -> I (eye sound)
    "a^ʊ": "W",  # aʊ -> W (ow sound)
    "e^ɪ": "A",  # eɪ -> A (ay sound)
    "ɔ^ɪ": "Y",  # ɔɪ -> Y (oy sound)
    # Affricates (with ASCII caret fallback)
    "d^ʒ": "ʤ",  # dʒ -> ʤ (j sound)
    "t^ʃ": "ʧ",  # tʃ -> ʧ (ch sound)
    # Consonants
    "r": "ɹ",  # r -> ɹ
    "x": "k",  # velar fricative -> k
    "ç": "k",  # palatal fricative -> k
    "ɬ": "l",  # lateral fricative -> l
    # Glottal stop with syllabic n - keep ʔ (valid US phoneme)
    "ʔn\u0329": "ʔn",  # ʔn̩ -> ʔn (syllabic n marker removed)
    "ʔˌn\u0329": "ʔn",  # ʔˌn̩ -> ʔn (with secondary stress)
    # Vowels - rhotacized schwa combinations (must come before plain ɚ)
    "ɚɹ": "əɹ",  # rhotacized schwa + r -> schwa + r (avoid double r)
    "ɚ": "əɹ",  # rhotacized schwa -> schwa + r
    "e": "A",  # plain e -> A
    "ɐ": "ə",  # near-open central -> schwa
    # Note: ə͡l -> ᵊl is handled conditionally in from_espeak()
    # (only after consonants, not after vowels)
    # Palatalization (remove, except before O/Q)
    "ʲO": "jO",
    "ʲQ": "jQ",
    "ʲo": "jo",
    "ʲə": "jə",
    "ʲ": "",
}

# Pre-sorted mappings for replacement (longest first)
FROM_ESPEAK: Final[list[tuple[str, str]]] = sorted(
    _ESPEAK_MAPPINGS.items(), key=lambda kv: -len(kv[0])
)

# =============================================================================
# IPA to Kokoro Mappings (for goruut conversion)
# =============================================================================

# Goruut to Kokoro phoneme mappings
# Goruut outputs standard IPA without tie characters for diphthongs/affricates
_GORUUT_MAPPINGS: Final[dict[str, str]] = {
    # Diphthongs (no tie character in goruut output)
    "eɪ": "A",  # eɪ -> A (ay sound, as in "say")
    "aɪ": "I",  # aɪ -> I (eye sound, as in "my")
    "aʊ": "W",  # aʊ -> W (ow sound, as in "now")
    "ɔɪ": "Y",  # ɔɪ -> Y (oy sound, as in "boy")
    "oʊ": "O",  # oʊ -> O (oh sound US, as in "go")
    "əʊ": "Q",  # əʊ -> Q (oh sound GB, as in "go")
    # Affricates (no tie character in goruut output)
    "tʃ": "ʧ",  # tʃ -> ʧ (ch sound)
    "dʒ": "ʤ",  # dʒ -> ʤ (j sound)
    # Consonants
    "g": "ɡ",  # ASCII g (U+0067) -> IPA ɡ (U+0261)
    "r": "ɹ",  # r -> ɹ
    # Vowels
    "ɐ": "ə",  # near-open central -> schwa
}

# Pre-sorted mappings for replacement (longest first)
FROM_GORUUT: Final[list[tuple[str, str]]] = sorted(
    _GORUUT_MAPPINGS.items(), key=lambda kv: -len(kv[0])
)

# =============================================================================
# Kokoro to IPA Mappings (for external use)
# =============================================================================

# Kokoro diphthong expansions to standard IPA
DIPHTHONG_EXPANSIONS: Final[dict[str, str]] = {
    "A": "eɪ",  # ay
    "I": "aɪ",  # eye
    "O": "oʊ",  # oh (US)
    "Q": "əʊ",  # oh (GB)
    "W": "aʊ",  # ow
    "Y": "ɔɪ",  # oy
}

# Affricate expansions
AFFRICATE_EXPANSIONS: Final[dict[str, str]] = {
    "ʤ": "dʒ",
    "ʧ": "tʃ",
}


# =============================================================================
# Conversion Functions
# =============================================================================


def from_espeak(phonemes: str, british: bool = False) -> str:
    """
    Convert espeak IPA output to Kokoro phonemes.

    Args:
        phonemes: The espeak phoneme string (with tie character ^ or ͡).
        british: Whether to use British English mappings.

    Returns:
        Kokoro-compatible phoneme string.

    Example:
        >>> from_espeak("mˈɜːt͡ʃənt͡ʃˌɪp", british=False)
        'mˈɜɹʧəntʃˌɪp'
    """
    result = phonemes

    # Apply standard mappings
    for old, new in FROM_ESPEAK:
        result = result.replace(old, new)

    # Handle syllabic consonants (U+0329 combining mark)
    result = re.sub(r"(\S)\u0329", r"ᵊ\1", result)
    result = result.replace(chr(809), "")

    # Handle syllabic l: ə͡l -> ᵊl only after consonants (not after vowels)
    # This prevents "material" (vowel + ə͡l) from becoming "materiᵊl"
    # while "little" (consonant + ə͡l) correctly becomes "littᵊl"
    _consonants_pattern = r"[bdfhjklmnpstvwzðŋɡɹɾʃʒʤʧθʔ]"
    result = re.sub(f"({_consonants_pattern})ə͡l", r"\1ᵊl", result)
    result = re.sub(f"({_consonants_pattern})ə\\^l", r"\1ᵊl", result)

    # Apply dialect-specific mappings
    if british:
        result = result.replace("e͡ə", "ɛː")
        result = result.replace("e^ə", "ɛː")
        result = result.replace("iə", "ɪə")
        result = result.replace("ə͡ʊ", "Q")
        result = result.replace("ə^ʊ", "Q")
    else:
        result = result.replace("o͡ʊ", "O")
        result = result.replace("o^ʊ", "O")
        result = result.replace("ɜːɹ", "ɜɹ")
        result = result.replace("ɜː", "ɜɹ")
        result = result.replace("ɪə", "iə")
        result = result.replace("ː", "")

    # ps = ps.replace('o', 'ɔ') # for espeak < 1.52
    # Remove tie characters (both Unicode and ASCII)
    result = result.replace("͡", "").replace("^", "")

    return result


def from_goruut(phonemes: str, british: bool = False) -> str:
    """
    Convert goruut/pygoruut IPA output to Kokoro phonemes.

    Goruut outputs standard IPA without tie characters for diphthongs
    and affricates, which requires different handling than espeak.

    Args:
        phonemes: The goruut phoneme string (standard IPA).
        british: Whether to use British English mappings.

    Returns:
        Kokoro-compatible phoneme string.

    Example:
        >>> from_goruut("həlˈoʊ wˈɜɹld", british=False)
        'həlˈO wˈɜɹld'
        >>> from_goruut("sˈeɪ", british=False)
        'sˈA'
    """
    result = phonemes

    # Apply standard mappings (longest first to handle diphthongs before monophthongs)
    for old, new in FROM_GORUUT:
        result = result.replace(old, new)

    # Apply dialect-specific mappings
    if british:
        # British uses Q for GOAT vowel, already handled in FROM_GORUUT
        # Keep length marks for British
        pass
    else:
        # US English: remove length marks
        result = result.replace("ː", "")

    return result


def to_espeak(phonemes: str) -> str:
    """
    Convert Kokoro phonemes to standard IPA (espeak-compatible).

    Args:
        phonemes: Kokoro phoneme string.

    Returns:
        Standard IPA phoneme string.

    Example:
        >>> to_espeak("hˈA")
        'hˈeɪ'
    """
    result = phonemes

    # Expand affricates
    for kokoro, ipa in AFFRICATE_EXPANSIONS.items():
        result = result.replace(kokoro, ipa)

    # Expand diphthongs
    for kokoro, ipa in DIPHTHONG_EXPANSIONS.items():
        result = result.replace(kokoro, ipa)

    # Replace small schwa
    result = result.replace("ᵊ", "ə")

    return result


def validate_phonemes(phonemes: str, british: bool = False) -> bool:
    """
    Check if all phonemes in a string are valid Kokoro phonemes.

    Args:
        phonemes: Phoneme string to validate.
        british: Whether to validate against British or US vocabulary.

    Returns:
        True if all phonemes are valid.
    """
    vocab = GB_VOCAB if british else US_VOCAB
    return all(p in vocab for p in phonemes if p.strip())


def get_vocab(british: bool = False) -> frozenset[str]:
    """
    Get the phoneme vocabulary for a dialect.

    Args:
        british: Whether to get British or US vocabulary.

    Returns:
        Frozen set of valid phonemes.
    """
    return GB_VOCAB if british else US_VOCAB


# =============================================================================
# Phoneme Categories (for analysis)
# =============================================================================

VOWELS: Final[frozenset[str]] = frozenset("AIWYOQaiuəɐɑɒɔɛɜɚɪʊʌæᵻᵊ")
CONSONANTS: Final[frozenset[str]] = frozenset("bdfhjklmnpstvwzðŋɡɹɾʃʒʤʧθ")
STRESS_MARKS: Final[frozenset[str]] = frozenset("ˈˌ")
MODIFIERS: Final[frozenset[str]] = frozenset("ː")

# Phoneme descriptions for documentation
PHONEME_DESCRIPTIONS: Final[dict[str, str]] = {
    # Stress
    "ˈ": "primary stress",
    "ˌ": "secondary stress",
    # Vowels - Monophthongs
    "æ": "TRAP vowel (US: ash)",
    "a": "TRAP vowel (GB: ash)",
    "ɑ": "PALM/LOT vowel (spa)",
    "ɒ": "LOT vowel (GB: on)",
    "ə": "schwa (banana)",
    "ᵊ": "reduced schwa (pixel)",
    "ɚ": "rhotacized schwa (butter)",
    "ɛ": "DRESS vowel (bed)",
    "ɜ": "NURSE vowel (her)",
    "ɪ": "KIT vowel (bit)",
    "i": "FLEECE vowel (bee)",
    "ʊ": "FOOT vowel (put)",
    "u": "GOOSE vowel (boot)",
    "ʌ": "STRUT vowel (cup)",
    "ɔ": "THOUGHT vowel (law)",
    "ᵻ": "reduced vowel (boxes)",
    # Vowels - Diphthongs (Kokoro notation)
    "A": "FACE diphthong [eɪ] (say)",
    "I": "PRICE diphthong [aɪ] (my)",
    "O": "GOAT diphthong US [oʊ] (go)",
    "Q": "GOAT diphthong GB [əʊ] (go)",
    "W": "MOUTH diphthong [aʊ] (now)",
    "Y": "CHOICE diphthong [ɔɪ] (boy)",
    # Consonants - Stops
    "p": "voiceless bilabial stop",
    "b": "voiced bilabial stop",
    "t": "voiceless alveolar stop",
    "d": "voiced alveolar stop",
    "k": "voiceless velar stop",
    "ɡ": "voiced velar stop",
    "ɾ": "alveolar tap (US: butter)",
    # Consonants - Fricatives
    "f": "voiceless labiodental fricative",
    "v": "voiced labiodental fricative",
    "θ": "voiceless dental fricative (thin)",
    "ð": "voiced dental fricative (this)",
    "s": "voiceless alveolar fricative",
    "z": "voiced alveolar fricative",
    "ʃ": "voiceless postalveolar fricative (ship)",
    "ʒ": "voiced postalveolar fricative (vision)",
    "h": "voiceless glottal fricative",
    # Consonants - Affricates (Kokoro notation)
    "ʧ": "voiceless postalveolar affricate [tʃ] (church)",
    "ʤ": "voiced postalveolar affricate [dʒ] (judge)",
    # Consonants - Nasals
    "m": "bilabial nasal",
    "n": "alveolar nasal",
    "ŋ": "velar nasal (sing)",
    # Consonants - Approximants
    "l": "alveolar lateral approximant",
    "ɹ": "alveolar approximant (red)",
    "w": "labio-velar approximant",
    "j": "palatal approximant (yes)",
    # Modifiers
    "ː": "length mark (GB)",
}
