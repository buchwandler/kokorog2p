"""Chinese G2P (Grapheme-to-Phoneme) converter.

This module provides Chinese text to phoneme conversion using pypinyin
for pinyin extraction and custom IPA mapping for phoneme generation.

Based on misaki's Chinese implementation.

Copyright 2025 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import re

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions


class ChineseG2P(G2PBase):
    """Chinese G2P using pypinyin and IPA transcription.

    This class converts Chinese text to IPA phonemes using:
    1. Jieba for word segmentation
    2. pypinyin for pinyin extraction
    3. Custom pinyin-to-IPA mapping

    Example:
        >>> g2p = ChineseG2P()
        >>> tokens = g2p("你好世界")
    """

    def __init__(
        self,
        language: str = "zh",
        use_espeak_fallback: bool = True,
        version: str = "1.1",
        unk: str = "",
        en_callable=None,
        load_silver: bool = True,
        load_gold: bool = True,
        **kwargs,
    ) -> None:
        """Initialize the Chinese G2P.

        Args:
            language: Language code (e.g., 'zh', 'zh-cn').
            use_espeak_fallback: Whether to use espeak for English words.
            version: Version of the G2P ("1.0" for base model,
                "1.1" for ZHFrontend multilingual). Default: "1.1".
            unk: Unknown token placeholder.
            en_callable: Callable for English word phonemization.
            load_silver: If True, load silver tier dictionary if available.
                Currently Chinese uses pypinyin system, so this parameter
                is reserved for future use and consistency.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary if available.
                Currently Chinese uses pypinyin system, so this parameter
                is reserved for future use and consistency.
                Defaults to True for consistency.
            **kwargs: Additional arguments.
        """
        super().__init__(language=language, use_espeak_fallback=use_espeak_fallback)
        self.version = version
        self.unk = unk
        self.en_callable = en_callable
        self.load_silver = load_silver
        self.load_gold = load_gold
        self._frontend = None
        self._jieba = None
        self._cn2an = None
        self._pypinyin = None
        self._transcription = None

    @property
    def frontend(self):
        """Lazy initialization of ZHFrontend for version 1.1."""
        if self._frontend is None and self.version == "1.1":
            from kokorog2p.zh.frontend import ZHFrontend

            self._frontend = ZHFrontend(unk=self.unk)
        return self._frontend

    @property
    def jieba(self):
        """Lazy import of jieba."""
        if self._jieba is None:
            import jieba

            self._jieba = jieba
        return self._jieba

    @property
    def cn2an(self):
        """Lazy import of cn2an."""
        if self._cn2an is None:
            import cn2an

            self._cn2an = cn2an
        return self._cn2an

    @property
    def pypinyin(self):
        """Lazy import of pypinyin."""
        if self._pypinyin is None:
            from pypinyin import Style, lazy_pinyin

            self._pypinyin = {"lazy_pinyin": lazy_pinyin, "Style": Style}
        return self._pypinyin

    @property
    def transcription(self):
        """Lazy import of transcription module."""
        if self._transcription is None:
            from kokorog2p.zh.transcription import pinyin_to_ipa

            self._transcription = pinyin_to_ipa
        return self._transcription

    @staticmethod
    def retone(p: str) -> str:
        """Convert tone markers to simpler format."""
        p = p.replace("˧˩˧", "↓")  # third tone
        p = p.replace("˧˥", "↗")  # second tone
        p = p.replace("˥˩", "↘")  # fourth tone
        p = p.replace("˥", "→")  # first tone
        p = p.replace(chr(635) + chr(809), "ɨ").replace(chr(633) + chr(809), "ɨ")
        return p

    def py2ipa(self, py: str) -> str:
        """Convert pinyin to IPA."""
        return "".join(self.retone(p) for p in self.transcription(py)[0])

    def word2ipa(self, w: str) -> str:
        """Convert a Chinese word to IPA via pinyin."""
        lazy_pinyin = self.pypinyin["lazy_pinyin"]
        Style = self.pypinyin["Style"]
        pinyins = lazy_pinyin(w, style=Style.TONE3, neutral_tone_with_five=True)
        return "".join(self.py2ipa(py) for py in pinyins)

    @staticmethod
    def map_punctuation(text: str) -> str:
        """Convert Chinese punctuation to ASCII equivalents."""
        text = text.replace("、", ", ").replace("，", ", ")
        text = text.replace("。", ". ").replace("．", ". ")
        text = text.replace("！", "! ")
        text = text.replace("：", ": ")
        text = text.replace("；", "; ")
        text = text.replace("？", "? ")
        text = text.replace("«", ' "').replace("»", '" ')
        text = text.replace("《", ' "').replace("》", '" ')
        text = text.replace("「", ' "').replace("」", '" ')
        text = text.replace("【", ' "').replace("】", '" ')
        text = text.replace("（", " (").replace("）", ") ")
        return text.strip()

    def legacy_call(self, text: str) -> str:
        """Legacy phonemization using jieba and pypinyin directly."""
        is_zh = bool(re.match(r"[\u4E00-\u9FFF]", text[0])) if text else False
        result = ""
        for segment in re.findall(r"[\u4E00-\u9FFF]+|[^\u4E00-\u9FFF]+", text):
            if is_zh:
                words = self.jieba.lcut(segment, cut_all=False)
                segment = " ".join(self.word2ipa(w) for w in words)
            result += segment
            is_zh = not is_zh
        return result.replace(chr(815), "")

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
        phonemes, _ = self._phonemize_internal(text)

        # Create a single token for now (Chinese segmentation is complex)
        # The frontend returns detailed tokens if needed
        token = GToken(
            text=text,
            tag="X",
            whitespace="",
            phonemes=phonemes if phonemes else None,
        )
        token.rating = "zh" if phonemes else None
        tokens = [token]
        ensure_gtoken_positions(tokens, text)
        return tokens

    def _phonemize_internal(
        self, text: str, en_callable=None
    ) -> tuple[str, list | None]:
        """Internal phonemization logic.

        Args:
            text: Input text.
            en_callable: Optional callable for English words.

        Returns:
            Tuple of (phoneme_string, token_list).
        """
        if not text.strip():
            return "", None

        # Convert Arabic numerals to Chinese
        text = self.cn2an.transform(text, "an2cn")

        # Map punctuation
        text = self.map_punctuation(text)

        if self.version == "1.0":
            return self.legacy_call(text), None

        # Use ZHFrontend for version 1.1
        en_callable = self.en_callable if en_callable is None else en_callable
        segments = []
        for en, zh in re.findall(
            r"([A-Za-z \'-]*[A-Za-z][A-Za-z \'-]*)|([^A-Za-z]+)", text
        ):
            en, zh = en.strip(), zh.strip()
            if zh:
                result, _ = self.frontend(zh)
                segments.append(result)
            elif en_callable is None:
                segments.append(self.unk if self.unk else "")
            else:
                segments.append(en_callable(en))

        return " ".join(segments), None

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word's phonemes.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for Chinese).

        Returns:
            Phoneme string or None.
        """
        if not word:
            return None
        return self.word2ipa(word)

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
        return f"ChineseG2P(language={self.language!r}, version={self.version!r})"

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: "1.1" for version 1.1, "1.0" otherwise.
        """
        return self.version
