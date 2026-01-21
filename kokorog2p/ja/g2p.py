"""Japanese G2P (Grapheme-to-Phoneme) converter.

This module provides Japanese text to phoneme conversion using
pyopenjtalk or cutlet for analysis and custom IPA mapping.

Based on misaki's Japanese implementation.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

# Katakana to phoneme mapping
M2P = {
    chr(12449): "a",  # ァ
    chr(12450): "a",  # ア
    chr(12451): "i",  # ィ
    chr(12452): "i",  # イ
    chr(12453): "u",  # ゥ
    chr(12454): "u",  # ウ
    chr(12455): "e",  # ェ
    chr(12456): "e",  # エ
    chr(12457): "o",  # ォ
    chr(12458): "o",  # オ
    chr(12459): "ka",  # カ
    chr(12460): "ga",  # ガ
    chr(12461): "ki",  # キ
    chr(12462): "gi",  # ギ
    chr(12463): "ku",  # ク
    chr(12464): "gu",  # グ
    chr(12465): "ke",  # ケ
    chr(12466): "ge",  # ゲ
    chr(12467): "ko",  # コ
    chr(12468): "go",  # ゴ
    chr(12469): "sa",  # サ
    chr(12470): "za",  # ザ
    chr(12471): "ɕi",  # シ
    chr(12472): "ʥi",  # ジ
    chr(12473): "su",  # ス
    chr(12474): "zu",  # ズ
    chr(12475): "se",  # セ
    chr(12476): "ze",  # ゼ
    chr(12477): "so",  # ソ
    chr(12478): "zo",  # ゾ
    chr(12479): "ta",  # タ
    chr(12480): "da",  # ダ
    chr(12481): "ʨi",  # チ
    chr(12482): "ʥi",  # ヂ
    chr(12484): "ʦu",  # ツ
    chr(12485): "zu",  # ヅ
    chr(12486): "te",  # テ
    chr(12487): "de",  # デ
    chr(12488): "to",  # ト
    chr(12489): "do",  # ド
    chr(12490): "na",  # ナ
    chr(12491): "ni",  # ニ
    chr(12492): "nu",  # ヌ
    chr(12493): "ne",  # ネ
    chr(12494): "no",  # ノ
    chr(12495): "ha",  # ハ
    chr(12496): "ba",  # バ
    chr(12497): "pa",  # パ
    chr(12498): "hi",  # ヒ
    chr(12499): "bi",  # ビ
    chr(12500): "pi",  # ピ
    chr(12501): "fu",  # フ
    chr(12502): "bu",  # ブ
    chr(12503): "pu",  # プ
    chr(12504): "he",  # ヘ
    chr(12505): "be",  # ベ
    chr(12506): "pe",  # ペ
    chr(12507): "ho",  # ホ
    chr(12508): "bo",  # ボ
    chr(12509): "po",  # ポ
    chr(12510): "ma",  # マ
    chr(12511): "mi",  # ミ
    chr(12512): "mu",  # ム
    chr(12513): "me",  # メ
    chr(12514): "mo",  # モ
    chr(12515): "ja",  # ャ
    chr(12516): "ja",  # ヤ
    chr(12517): "ju",  # ュ
    chr(12518): "ju",  # ユ
    chr(12519): "jo",  # ョ
    chr(12520): "jo",  # ヨ
    chr(12521): "ra",  # ラ
    chr(12522): "ri",  # リ
    chr(12523): "ru",  # ル
    chr(12524): "re",  # レ
    chr(12525): "ro",  # ロ
    chr(12526): "wa",  # ヮ
    chr(12527): "wa",  # ワ
    chr(12528): "i",  # ヰ
    chr(12529): "e",  # ヱ
    chr(12530): "o",  # ヲ
    chr(12532): "vu",  # ヴ
    chr(12533): "ka",  # ヵ
    chr(12534): "ke",  # ヶ
    chr(12535): "va",  # ヷ
    chr(12536): "vi",  # ヸ
    chr(12537): "ve",  # ヹ
    chr(12538): "vo",  # ヺ
}

# Add combination characters
M2P.update(
    {
        chr(12452) + chr(12455): "je",  # イェ
        chr(12454) + chr(12451): "wi",  # ウィ
        chr(12454) + chr(12453): "wu",  # ウゥ
        chr(12454) + chr(12455): "we",  # ウェ
        chr(12454) + chr(12457): "wo",  # ウォ
        chr(12461) + chr(12451): "ᶄi",  # キィ
        chr(12461) + chr(12455): "ᶄe",  # キェ
        chr(12461) + chr(12515): "ᶄa",  # キャ
        chr(12461) + chr(12517): "ᶄu",  # キュ
        chr(12461) + chr(12519): "ᶄo",  # キョ
        chr(12462) + chr(12451): "ᶃi",  # ギィ
        chr(12462) + chr(12455): "ᶃe",  # ギェ
        chr(12462) + chr(12515): "ᶃa",  # ギャ
        chr(12462) + chr(12517): "ᶃu",  # ギュ
        chr(12462) + chr(12519): "ᶃo",  # ギョ
        chr(12463) + chr(12449): "Ka",  # クァ
        chr(12463) + chr(12451): "Ki",  # クィ
        chr(12463) + chr(12453): "Ku",  # クゥ
        chr(12463) + chr(12455): "Ke",  # クェ
        chr(12463) + chr(12457): "Ko",  # クォ
        chr(12463) + chr(12526): "Ka",  # クヮ
        chr(12464) + chr(12449): "Ga",  # グァ
        chr(12464) + chr(12451): "Gi",  # グィ
        chr(12464) + chr(12453): "Gu",  # グゥ
        chr(12464) + chr(12455): "Ge",  # グェ
        chr(12464) + chr(12457): "Go",  # グォ
        chr(12464) + chr(12526): "Ga",  # グヮ
        chr(12471) + chr(12455): "ɕe",  # シェ
        chr(12471) + chr(12515): "ɕa",  # シャ
        chr(12471) + chr(12517): "ɕu",  # シュ
        chr(12471) + chr(12519): "ɕo",  # ショ
        chr(12472) + chr(12455): "ʥe",  # ジェ
        chr(12472) + chr(12515): "ʥa",  # ジャ
        chr(12472) + chr(12517): "ʥu",  # ジュ
        chr(12472) + chr(12519): "ʥo",  # ジョ
        chr(12473) + chr(12451): "si",  # スィ
        chr(12474) + chr(12451): "zi",  # ズィ
        chr(12481) + chr(12455): "ʨe",  # チェ
        chr(12481) + chr(12515): "ʨa",  # チャ
        chr(12481) + chr(12517): "ʨu",  # チュ
        chr(12481) + chr(12519): "ʨo",  # チョ
        chr(12482) + chr(12455): "ʥe",  # ヂェ
        chr(12482) + chr(12515): "ʥa",  # ヂャ
        chr(12482) + chr(12517): "ʥu",  # ヂュ
        chr(12482) + chr(12519): "ʥo",  # ヂョ
        chr(12484) + chr(12449): "ʦa",  # ツァ
        chr(12484) + chr(12451): "ʦi",  # ツィ
        chr(12484) + chr(12455): "ʦe",  # ツェ
        chr(12484) + chr(12457): "ʦo",  # ツォ
        chr(12486) + chr(12451): "ti",  # ティ
        chr(12486) + chr(12455): "ƫe",  # テェ
        chr(12486) + chr(12515): "ƫa",  # テャ
        chr(12486) + chr(12517): "ƫu",  # テュ
        chr(12486) + chr(12519): "ƫo",  # テョ
        chr(12487) + chr(12451): "di",  # ディ
        chr(12487) + chr(12455): "ᶁe",  # デェ
        chr(12487) + chr(12515): "ᶁa",  # デャ
        chr(12487) + chr(12517): "ᶁu",  # デュ
        chr(12487) + chr(12519): "ᶁo",  # デョ
        chr(12488) + chr(12453): "tu",  # トゥ
        chr(12489) + chr(12453): "du",  # ドゥ
        chr(12491) + chr(12451): "ɲi",  # ニィ
        chr(12491) + chr(12455): "ɲe",  # ニェ
        chr(12491) + chr(12515): "ɲa",  # ニャ
        chr(12491) + chr(12517): "ɲu",  # ニュ
        chr(12491) + chr(12519): "ɲo",  # ニョ
        chr(12498) + chr(12451): "çi",  # ヒィ
        chr(12498) + chr(12455): "çe",  # ヒェ
        chr(12498) + chr(12515): "ça",  # ヒャ
        chr(12498) + chr(12517): "çu",  # ヒュ
        chr(12498) + chr(12519): "ço",  # ヒョ
        chr(12499) + chr(12451): "ᶀi",  # ビィ
        chr(12499) + chr(12455): "ᶀe",  # ビェ
        chr(12499) + chr(12515): "ᶀa",  # ビャ
        chr(12499) + chr(12517): "ᶀu",  # ビュ
        chr(12499) + chr(12519): "ᶀo",  # ビョ
        chr(12500) + chr(12451): "ᶈi",  # ピィ
        chr(12500) + chr(12455): "ᶈe",  # ピェ
        chr(12500) + chr(12515): "ᶈa",  # ピャ
        chr(12500) + chr(12517): "ᶈu",  # ピュ
        chr(12500) + chr(12519): "ᶈo",  # ピョ
        chr(12501) + chr(12449): "fa",  # ファ
        chr(12501) + chr(12451): "fi",  # フィ
        chr(12501) + chr(12455): "fe",  # フェ
        chr(12501) + chr(12457): "fo",  # フォ
        chr(12511) + chr(12451): "ᶆi",  # ミィ
        chr(12511) + chr(12455): "ᶆe",  # ミェ
        chr(12511) + chr(12515): "ᶆa",  # ミャ
        chr(12511) + chr(12517): "ᶆu",  # ミュ
        chr(12511) + chr(12519): "ᶆo",  # ミョ
        chr(12522) + chr(12451): "ᶉi",  # リィ
        chr(12522) + chr(12455): "ᶉe",  # リェ
        chr(12522) + chr(12515): "ᶉa",  # リャ
        chr(12522) + chr(12517): "ᶉu",  # リュ
        chr(12522) + chr(12519): "ᶉo",  # リョ
        chr(12532) + chr(12449): "va",  # ヴァ
        chr(12532) + chr(12451): "vi",  # ヴィ
        chr(12532) + chr(12455): "ve",  # ヴェ
        chr(12532) + chr(12457): "vo",  # ヴォ
        chr(12532) + chr(12515): "ᶀa",  # ヴャ
        chr(12532) + chr(12517): "ᶀu",  # ヴュ
        chr(12532) + chr(12519): "ᶀo",  # ヴョ
    }
)

# Special characters
M2P["ッ"] = "ʔ"
M2P["ン"] = "ɴ"
M2P["ー"] = "ː"

# Punctuation mapping
PUNCT_MAP = {
    "«": '"',
    "»": '"',
    "、": ",",
    "。": ".",
    "〈": '"',
    "〉": '"',
    "《": '"',
    "》": '"',
    "「": '"',
    "」": '"',
    "『": '"',
    "』": '"',
    "【": '"',
    "】": '"',
    "！": "!",
    "（": "(",
    "）": ")",
    "：": ":",
    "；": ";",
    "？": "?",
}

PUNCT_VALUES = frozenset('!"(),.:;?—""…')
PUNCT_STARTS = frozenset('("')
PUNCT_STOPS = frozenset('!),.:;?"')
TAILS = frozenset([v[-1] for v in M2P.values()])
VOWELS = frozenset("aeiou")


class JapaneseG2P(G2PBase):
    """Japanese G2P using pyopenjtalk or cutlet.

    Example:
        >>> g2p = JapaneseG2P()
        >>> tokens = g2p("こんにちは")
    """

    def __init__(
        self,
        language: str = "ja",
        use_espeak_fallback: bool = True,
        backend: str = "pyopenjtalk",
        unk: str = "",
        load_silver: bool = True,
        load_gold: bool = True,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the Japanese G2P.

        Args:
            language: Language code (e.g., 'ja', 'ja-jp').
            use_espeak_fallback: Whether to use espeak for unknown words.
            backend: Backend to use ("pyopenjtalk" or "cutlet").
            unk: Unknown token placeholder.
            load_silver: If True, load silver tier dictionary if available.
                Currently Japanese doesn't use dictionary system, so this
                parameter is reserved for future use and consistency.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary if available.
                Currently Japanese doesn't use dictionary system, so this
                parameter is reserved for future use and consistency.
                Defaults to True for consistency.
            version: Model version ("1.0" for base, "1.1" for multilingual).
                Default: "1.0".
            **kwargs: Additional arguments.
        """
        super().__init__(language=language, use_espeak_fallback=use_espeak_fallback)
        self.backend = backend
        self.version = version
        self.unk = unk
        self.load_silver = load_silver
        self.load_gold = load_gold
        self._pyopenjtalk = None
        self._cutlet = None

    @property
    def pyopenjtalk(self):
        """Lazy import of pyopenjtalk."""
        if self._pyopenjtalk is None:
            import pyopenjtalk

            self._pyopenjtalk = pyopenjtalk
        return self._pyopenjtalk

    @property
    def cutlet(self):
        """Lazy initialization of Cutlet backend."""
        if self._cutlet is None and self.backend == "cutlet":
            from kokorog2p.ja.cutlet import Cutlet

            self._cutlet = Cutlet()
        return self._cutlet

    @staticmethod
    def pron2moras(pron: str) -> list[str]:
        """Convert pronunciation to mora list."""
        moras = []
        for k in pron:
            if k not in M2P:
                continue
            if moras and moras[-1] + k in M2P:
                moras[-1] += k
            else:
                moras.append(k)
        return moras

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes.
        """
        if not text or not text.strip():
            return []

        # Phonemize using the internal method
        phonemes, tokens = self._phonemize_internal(text)

        if tokens:
            ensure_gtoken_positions(tokens, text)
            return tokens

        # Create a single token if no detailed tokens
        token = GToken(
            text=text,
            tag="X",
            whitespace="",
            phonemes=phonemes if phonemes else None,
        )
        token.rating = "ja" if phonemes else None
        tokens = [token]
        ensure_gtoken_positions(tokens, text)
        return tokens

    def _phonemize_internal(self, text: str) -> tuple[str, list[GToken] | None]:
        """Internal phonemization logic.

        Args:
            text: Input text.

        Returns:
            Tuple of (phoneme_string, token_list).
        """
        if self.cutlet is not None:
            return self.cutlet(text)

        # Use pyopenjtalk
        return self._phonemize_pyopenjtalk(text)

    def _phonemize_pyopenjtalk(self, text: str) -> tuple[str, list[GToken] | None]:
        """Phonemize using pyopenjtalk."""
        tokens = []
        last_a, _last_p = 0, ""
        acc, mcount = None, 0

        for word in self.pyopenjtalk.run_frontend(text):
            pron, mora_size = word["pron"], word["mora_size"]
            moras = []
            if mora_size > 0:
                moras = self.pron2moras(pron)

            chain_flag = (
                mora_size > 0
                and tokens
                and tokens[-1].get("mora_size", 0) > 0
                and (word["chain_flag"] == 1 or (moras and moras[0] == "ー"))
            )

            if not chain_flag:
                acc, mcount = None, 0
            acc = word["acc"] if acc is None else acc

            accents = []
            for _ in moras:
                mcount += 1
                if acc == 0:
                    accents.append(0 if mcount == 1 else (1 if last_a == 0 else 2))
                elif acc == mcount:
                    accents.append(3)
                elif 1 < mcount < acc:
                    accents.append(1 if last_a == 0 else 2)
                else:
                    accents.append(0)
                last_a = accents[-1] if accents else 0

            surface = word["string"]
            if surface in PUNCT_MAP:
                surface = PUNCT_MAP[surface]

            whitespace, phonemes, pitch = "", None, None
            if moras:
                phonemes, pitch = "", ""
                for m, a in zip(moras, accents, strict=False):
                    ps = M2P.get(m, "")
                    phonemes += ps
                    pitch += ("_" if a == 0 else ("^" if a == 3 else "-")) * len(ps)
            elif surface and all(s in PUNCT_VALUES for s in surface):
                phonemes = surface
                if surface[-1] in PUNCT_STOPS:
                    whitespace = " "
                    if tokens:
                        tokens[-1].whitespace = ""
                elif (
                    surface[-1] in PUNCT_STARTS and tokens and not tokens[-1].whitespace
                ):
                    tokens[-1].whitespace = " "

            if (
                tokens
                and phonemes is None
                and surface == "・"
                or (surface and not surface.strip())
            ):
                tokens[-1].whitespace = " "
                continue

            tk = GToken(
                text=surface,
                tag=word["pos"],
                whitespace=whitespace,
                phonemes=phonemes,
            )
            # Store extra data in extension dict
            tk._["pron"] = pron
            tk._["acc"] = word["acc"]
            tk._["mora_size"] = mora_size
            tk._["chain_flag"] = chain_flag
            tk._["moras"] = moras
            tk._["accents"] = accents
            tk._["pitch"] = pitch
            tokens.append(tk)

        # Build result string
        result, pitch_str = "", ""
        for tk in tokens:
            if tk.phonemes is None:
                result += self.unk + tk.whitespace
                pitch_str += "j" * len(self.unk + tk.whitespace)
                continue

            if (
                tk.get("mora_size")
                and not tk.get("chain_flag")
                and result
                and result[-1] in TAILS
                and tk.get("moras")
                and tk.get("moras")[0] != "ン"
            ):
                result += " "
                pitch_str += "j"

            result += tk.phonemes + tk.whitespace
            tk_pitch = tk.get("pitch")
            pitch_str += (
                ("j" * len(tk.phonemes)) if tk_pitch is None else tk_pitch
            ) + "j" * len(tk.whitespace)

        if tokens and tokens[-1].whitespace and result.endswith(tokens[-1].whitespace):
            result = result[: -len(tokens[-1].whitespace)]
            pitch_str = pitch_str[: len(result)]

        return result + pitch_str, tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word's phonemes.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for Japanese).

        Returns:
            Phoneme string or None.
        """
        if not word:
            return None
        result, _ = self._phonemize_internal(word)
        return result if result else None

    def phonemize(self, text: str) -> str:
        """Convert text to phonemes.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string.
        """
        result, _ = self._phonemize_internal(text)
        return result

    def __repr__(self) -> str:
        return f"JapaneseG2P(language={self.language!r}, backend={self.backend!r})"

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
