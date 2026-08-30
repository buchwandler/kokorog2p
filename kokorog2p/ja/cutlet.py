"""Japanese romaji conversion using fugashi (MeCab) and custom mappings.

ADAPTED from https://github.com/polm/cutlet/blob/main/cutlet/cutlet.py
Original License: MIT

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import re
import unicodedata
from dataclasses import dataclass

import jaconv
import mojimoji
from fugashi import Tagger

from kokorog2p.lexicons.runtime import SelectedLexicons, open_selected

# Hiragana to IPA mapping
HEPBURN = {
    chr(12353): "a",  # ぁ
    chr(12354): "a",  # あ
    chr(12355): "i",  # ぃ
    chr(12356): "i",  # い
    chr(12357): "ɯ",  # ぅ
    chr(12358): "ɯ",  # う
    chr(12359): "e",  # ぇ
    chr(12360): "e",  # え
    chr(12361): "o",  # ぉ
    chr(12362): "o",  # お
    chr(12363): "ka",  # か
    chr(12364): "ɡa",  # が
    chr(12365): "kʲi",  # き
    chr(12366): "ɡʲi",  # ぎ
    chr(12367): "kɯ",  # く
    chr(12368): "ɡɯ",  # ぐ
    chr(12369): "ke",  # け
    chr(12370): "ɡe",  # げ
    chr(12371): "ko",  # こ
    chr(12372): "ɡo",  # ご
    chr(12373): "sa",  # さ
    chr(12374): "ʣa",  # ざ
    chr(12375): "ɕi",  # し
    chr(12376): "ʥi",  # じ
    chr(12377): "sɨ",  # す
    chr(12378): "zɨ",  # ず
    chr(12379): "se",  # せ
    chr(12380): "ʣe",  # ぜ
    chr(12381): "so",  # そ
    chr(12382): "ʣo",  # ぞ
    chr(12383): "ta",  # た
    chr(12384): "da",  # だ
    chr(12385): "ʨi",  # ち
    chr(12386): "ʥi",  # ぢ
    chr(12388): "ʦɨ",  # つ
    chr(12389): "zɨ",  # づ
    chr(12390): "te",  # て
    chr(12391): "de",  # で
    chr(12392): "to",  # と
    chr(12393): "do",  # ど
    chr(12394): "na",  # な
    chr(12395): "ɲi",  # に
    chr(12396): "nɯ",  # ぬ
    chr(12397): "ne",  # ね
    chr(12398): "no",  # の
    chr(12399): "ha",  # は
    chr(12400): "ba",  # ば
    chr(12401): "pa",  # ぱ
    chr(12402): "çi",  # ひ
    chr(12403): "bʲi",  # び
    chr(12404): "pʲi",  # ぴ
    chr(12405): "ɸɯ",  # ふ
    chr(12406): "bɯ",  # ぶ
    chr(12407): "pɯ",  # ぷ
    chr(12408): "he",  # へ
    chr(12409): "be",  # べ
    chr(12410): "pe",  # ぺ
    chr(12411): "ho",  # ほ
    chr(12412): "bo",  # ぼ
    chr(12413): "po",  # ぽ
    chr(12414): "ma",  # ま
    chr(12415): "mʲi",  # み
    chr(12416): "mɯ",  # む
    chr(12417): "me",  # め
    chr(12418): "mo",  # も
    chr(12419): "ja",  # ゃ
    chr(12420): "ja",  # や
    chr(12421): "jɯ",  # ゅ
    chr(12422): "jɯ",  # ゆ
    chr(12423): "jo",  # ょ
    chr(12424): "jo",  # よ
    chr(12425): "ɾa",  # ら
    chr(12426): "ɾʲi",  # り
    chr(12427): "ɾɯ",  # る
    chr(12428): "ɾe",  # れ
    chr(12429): "ɾo",  # ろ
    chr(12430): "βa",  # ゎ
    chr(12431): "βa",  # わ
    chr(12432): "i",  # ゐ
    chr(12433): "e",  # ゑ
    chr(12434): "o",  # を
    chr(12436): "vɯ",  # ゔ
    chr(12437): "ka",  # ゕ
    chr(12438): "ke",  # ゖ
}

# Add katakana phonetic extensions
HEPBURN.update(
    {
        chr(12535): "va",  # ヷ
        chr(12536): "vʲi",  # ヸ
        chr(12537): "ve",  # ヹ
        chr(12538): "vo",  # ヺ
    }
)

# Add combination characters
HEPBURN.update(
    {
        chr(12356) + chr(12359): "je",  # いぇ
        chr(12358) + chr(12355): "βi",  # うぃ
        chr(12358) + chr(12359): "βe",  # うぇ
        chr(12358) + chr(12361): "βo",  # うぉ
        chr(12365) + chr(12359): "kʲe",  # きぇ
        chr(12365) + chr(12419): "kʲa",  # きゃ
        chr(12365) + chr(12421): "kʲɨ",  # きゅ
        chr(12365) + chr(12423): "kʲo",  # きょ
        chr(12366) + chr(12419): "ɡʲa",  # ぎゃ
        chr(12366) + chr(12421): "ɡʲɨ",  # ぎゅ
        chr(12366) + chr(12423): "ɡʲo",  # ぎょ
        chr(12367) + chr(12353): "kᵝa",  # くぁ
        chr(12367) + chr(12355): "kᵝi",  # くぃ
        chr(12367) + chr(12359): "kᵝe",  # くぇ
        chr(12367) + chr(12361): "kᵝo",  # くぉ
        chr(12368) + chr(12353): "ɡᵝa",  # ぐぁ
        chr(12368) + chr(12355): "ɡᵝi",  # ぐぃ
        chr(12368) + chr(12359): "ɡᵝe",  # ぐぇ
        chr(12368) + chr(12361): "ɡᵝo",  # ぐぉ
        chr(12375) + chr(12359): "ɕe",  # しぇ
        chr(12375) + chr(12419): "ɕa",  # しゃ
        chr(12375) + chr(12421): "ɕɨ",  # しゅ
        chr(12375) + chr(12423): "ɕo",  # しょ
        chr(12376) + chr(12359): "ʥe",  # じぇ
        chr(12376) + chr(12419): "ʥa",  # じゃ
        chr(12376) + chr(12421): "ʥɨ",  # じゅ
        chr(12376) + chr(12423): "ʥo",  # じょ
        chr(12385) + chr(12359): "ʨe",  # ちぇ
        chr(12385) + chr(12419): "ʨa",  # ちゃ
        chr(12385) + chr(12421): "ʨɨ",  # ちゅ
        chr(12385) + chr(12423): "ʨo",  # ちょ
        chr(12386) + chr(12419): "ʥa",  # ぢゃ
        chr(12386) + chr(12421): "ʥɨ",  # ぢゅ
        chr(12386) + chr(12423): "ʥo",  # ぢょ
        chr(12388) + chr(12353): "ʦa",  # つぁ
        chr(12388) + chr(12355): "ʦʲi",  # つぃ
        chr(12388) + chr(12359): "ʦe",  # つぇ
        chr(12388) + chr(12361): "ʦo",  # つぉ
        chr(12390) + chr(12355): "tʲi",  # てぃ
        chr(12390) + chr(12421): "tʲɨ",  # てゅ
        chr(12391) + chr(12355): "dʲi",  # でぃ
        chr(12391) + chr(12421): "dʲɨ",  # でゅ
        chr(12392) + chr(12357): "tɯ",  # とぅ
        chr(12393) + chr(12357): "dɯ",  # どぅ
        chr(12395) + chr(12359): "ɲe",  # にぇ
        chr(12395) + chr(12419): "ɲa",  # にゃ
        chr(12395) + chr(12421): "ɲɨ",  # にゅ
        chr(12395) + chr(12423): "ɲo",  # にょ
        chr(12402) + chr(12359): "çe",  # ひぇ
        chr(12402) + chr(12419): "ça",  # ひゃ
        chr(12402) + chr(12421): "çɨ",  # ひゅ
        chr(12402) + chr(12423): "ço",  # ひょ
        chr(12403) + chr(12419): "bʲa",  # びゃ
        chr(12403) + chr(12421): "bʲɨ",  # びゅ
        chr(12403) + chr(12423): "bʲo",  # びょ
        chr(12404) + chr(12419): "pʲa",  # ぴゃ
        chr(12404) + chr(12421): "pʲɨ",  # ぴゅ
        chr(12404) + chr(12423): "pʲo",  # ぴょ
        chr(12405) + chr(12353): "ɸa",  # ふぁ
        chr(12405) + chr(12355): "ɸʲi",  # ふぃ
        chr(12405) + chr(12359): "ɸe",  # ふぇ
        chr(12405) + chr(12361): "ɸo",  # ふぉ
        chr(12405) + chr(12421): "ɸʲɨ",  # ふゅ
        chr(12405) + chr(12423): "ɸʲo",  # ふょ
        chr(12415) + chr(12419): "mʲa",  # みゃ
        chr(12415) + chr(12421): "mʲɨ",  # みゅ
        chr(12415) + chr(12423): "mʲo",  # みょ
        chr(12426) + chr(12419): "ɾʲa",  # りゃ
        chr(12426) + chr(12421): "ɾʲɨ",  # りゅ
        chr(12426) + chr(12423): "ɾʲo",  # りょ
        chr(12436) + chr(12353): "va",  # ゔぁ
        chr(12436) + chr(12355): "vʲi",  # ゔぃ
        chr(12436) + chr(12359): "ve",  # ゔぇ
        chr(12436) + chr(12361): "vo",  # ゔぉ
        chr(12436) + chr(12421): "bʲɨ",  # ゔゅ
        chr(12436) + chr(12423): "bʲo",  # ゔょ
    }
)

# Add symbols
HEPBURN.update(
    {
        "。": ".",
        "、": ",",
        "？": "?",
        "！": "!",
        "「": chr(8220),
        "」": chr(8221),
        "『": chr(8220),
        "』": chr(8221),
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "《": "(",
        "》": ")",
        "【": "[",
        "】": "]",
        "・": " ",
        "，": ",",
        "～": "—",
        "〜": "—",
        "—": "—",
        "«": chr(8220),
        "»": chr(8221),
        "゚": "",  # combining handakuten by itself, just discard
        "゙": "",  # combining dakuten by itself
    }
)

# Katakana Phonetic Extensions
KATAKANA_PHONETIC_EXT = {
    "ㇰ": "ク",
    "ㇱ": "シ",
    "ㇲ": "ス",
    "ㇳ": "ト",
    "ㇴ": "ヌ",
    "ㇵ": "ハ",
    "ㇶ": "ヒ",
    "ㇷ": "フ",
    "ㇸ": "ヘ",
    "ㇹ": "ホ",
    "ㇺ": "ム",
    "ㇻ": "ラ",
    "ㇼ": "リ",
    "ㇽ": "ル",
    "ㇾ": "レ",
    "ㇿ": "ロ",
}

SUTEGANA = frozenset("ゃゅょぁぃぅぇぉ")
ODORI = frozenset("〃々ゝゞヽ")


def add_dakuten(kk: str) -> str | None:
    """Given a kana (single-character string), add a dakuten."""
    try:
        ii = "かきくけこさしすせそたちつてとはひふへほ".index(kk)
        return "がぎぐげござじずぜぞだぢづでどばびぶべぼ"[ii]
    except ValueError:
        return None


@dataclass
class Word:
    surface: str
    hira: str
    char_type: int


@dataclass
class Token:
    surface: str
    space: bool  # if a space should follow

    def __str__(self) -> str:
        sp = " " if self.space else ""
        return f"{self.surface}{sp}"


class Cutlet:
    """Japanese romaji/IPA converter using MeCab (via fugashi)."""

    def __init__(self, lexicons: tuple[str, ...] = ("words",)) -> None:
        try:
            self.tagger = Tagger()
        except Exception as exc:
            raise RuntimeError(
                "Japanese Cutlet requires a usable MeCab dictionary. "
                "Install `kokorog2p[ja-cutlet]` or install the full-UniDic extra "
                "and run `python -m unidic download`."
            ) from exc
        self.table = dict(HEPBURN)  # make a copy so we can modify it
        self.lexicons = tuple(lexicons)
        self.exceptions = {}
        self._ja_words: SelectedLexicons | None = None
        self.prepared_input = False

    @property
    def ja_words(self) -> SelectedLexicons:
        """Open the packaged membership lexicon on first dictionary use."""
        if self._ja_words is None:
            self._ja_words = open_selected("ja-jp", self.lexicons)
        return self._ja_words

    def __call__(self, text: str) -> tuple[str, None]:
        """Build a complete string from input text."""
        if not text:
            return "", None

        text = self._normalize_text(text)
        words = [
            Word(
                w.surface,
                jaconv.kata2hira(w.feature.pron or w.feature.kana or w.surface),
                6 if w.char_type == 7 or not w.is_unk else w.char_type,
            )
            for w in self.tagger(text)
        ]
        tokens = self._romaji_tokens(words)
        out = "".join(str(tok) for tok in tokens)
        ps = re.sub(r"\s+", " ", out.strip()).replace("(", "«").replace(")", "»")
        ps = re.sub(r'(?<![!",.:;?»—…"]) (?=ʔ)|(?<=ʔ) (?!["«"])', "", ps)
        return ps, None

    def close(self) -> None:
        if self._ja_words is not None:
            self._ja_words.close()

    def _normalize_text(self, text: str) -> str:
        """Given text, normalize variations in Japanese."""
        # perform unicode normalization
        text = re.sub(r"[〜～](?=\d)", "から", text)  # wave dash range
        for k, v in KATAKANA_PHONETIC_EXT.items():
            text = text.replace(k, v)
        text = unicodedata.normalize("NFKC", text)
        # convert all full-width alphanum to half-width
        text = mojimoji.zen_to_han(text, kana=False)
        # replace half-width katakana with full-width
        text = mojimoji.han_to_zen(text, digit=False, ascii=False)
        # Spokenform owns digit-to-spoken conversion; retain only typography.
        return "".join(re.findall(r"\d+|\D+", text))


    def _romaji_tokens(self, words: list[Word]) -> list[Token]:
        """Build a list of tokens from input nodes."""
        groups = []
        i = 0
        while i < len(words):
            z = next(
                (
                    z
                    for z in range(i + 1, len(words))
                    if words[z].char_type != words[i].char_type
                ),
                len(words),
            )
            j = next(
                (
                    j
                    for j in range(z, i, -1)
                    if "".join(w.surface for w in words[i:j]) in self.ja_words
                ),
                None,
            )
            if j is None:
                groups.append([words[i]])
                i += 1
            else:
                groups.append(words[i:j])
                i = j
        words = [
            Word(
                "".join(w.surface for w in g),
                "".join(w.hira for w in g),
                g[0].char_type,
            )
            for g in groups
        ]
        out = []
        for _wi, word in enumerate(words):
            po = out[-1] if out else None
            roma = self._romaji_word(word)
            tok = Token(roma, False)
            # handle punctuation with atypical spacing
            surface = word.surface
            if surface in "「『«" or roma in "([":
                if po:
                    po.space = True
            elif surface in "」』»" or roma in "]).,?!:":
                if po:
                    po.space = False
                tok.space = True
            elif roma == " ":
                tok.space = False
            else:
                tok.space = True
            out.append(tok)
        # remove any leftover sokuon
        for tok in out:
            tok.surface = tok.surface.replace("っ", "")
        return out

    def _romaji_word(self, word: Word) -> str:
        """Return the romaji for a single word (node)."""
        surface = word.surface
        if surface in self.exceptions:
            return self.exceptions[surface]
        if surface.isascii():
            return surface
        if word.char_type == 3:  # symbol
            return "".join(self.table.get(c, c) for c in surface)
        elif word.char_type != 6:
            return ""  # silently fail
        out = ""
        hira = word.hira
        for ki, char in enumerate(hira):
            nk = hira[ki + 1] if ki < len(hira) - 1 else None
            pk = hira[ki - 1] if ki > 0 else None
            out += self._get_single_mapping(pk, char, nk)
        return out

    def _get_single_mapping(self, pk: str | None, kk: str, nk: str | None) -> str:
        """Given a single kana and its neighbors, return the mapped romaji."""
        # handle odoriji
        if kk in ODORI:
            if kk in "ゝヽ":
                return pk if pk else ""
            if kk in "ゞヾ":
                if not pk:
                    return ""
                vv = add_dakuten(pk)
                return self.table[vv] if vv else ""
            return ""
        # handle digraphs
        if pk and (pk + kk) in self.table:
            return self.table[pk + kk]
        if nk and (kk + nk) in self.table:
            return ""
        if nk and nk in SUTEGANA:
            if kk == "っ":
                return ""  # never valid, just ignore
            return self.table[kk][:-1] + self.table[nk]
        if kk in SUTEGANA:
            return ""
        if kk == "ー":  # 長音符
            return "ː"
        if kk == "っ":
            return "ʔ"
        if kk == "ん":
            # https://en.wikipedia.org/wiki/N_(kana)
            tnk = self.table.get(nk)
            if tnk:
                if tnk[0] in "mpb":
                    return "m"
                elif tnk[0] in "kɡ":
                    return "ŋ"
                elif any(tnk.startswith(p) for p in ("ɲ", "ʨ", "ʥ")):
                    return "ɲ"
                elif tnk[0] in "ntdɾz":
                    return "n"
            return "ɴ"
        return self.table.get(kk, "")
