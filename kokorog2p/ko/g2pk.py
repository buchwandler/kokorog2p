"""
https://github.com/kyubyong/g2pK
"""

import os
import re

import nltk
from jamo import h2j
from nltk.corpus import cmudict

# For further info. about cmu dict, consult http://www.speech.cs.cmu.edu/cgi-bin/cmudict.
try:
    nltk.data.find("corpora/cmudict.zip")
except LookupError:
    nltk.download("cmudict")

from .english import convert_eng
from .numerals import convert_num
from .regular import link1, link2, link4
from .special import (
    balb,
    consonant_ui,
    jamo,
    josa_ui,
    jyeo,
    modifying_rieul,
    palatalize,
    rieulbieub,
    rieulgiyeok,
    verb_nieun,
    vowel_ui,
    ye,
)
from .utils import annotate, compose, get_rule_id2text, group, parse_table


class G2p:
    def __init__(self):
        self.mecab = self.get_mecab()
        self.table = parse_table()

        self.cmu = cmudict.dict()  # for English

        self.rule2text = get_rule_id2text()  # for comments of main rules

        # Load idioms from Python data module
        from .data.idioms import IDIOMS

        self.idioms_list = IDIOMS

    def get_mecab(self):
        try:
            if os.name == "nt":
                import MeCab

                return MeCab.Tagger()
            elif os.name == "posix":
                try:
                    import mecab

                    return mecab.MeCab()
                except ImportError:
                    # Try mecab-python3 as fallback
                    import mecab_python3 as mecab

                    return mecab.MeCab()
        except ImportError as e:
            # MeCab not available - will work without POS tagging
            import warnings

            warnings.warn(
                f"MeCab not available: {e}. "
                "Korean G2P will work but without morphological analysis. "
                "Install mecab-python3 for better results: pip install mecab-python3",
                UserWarning,
                stacklevel=2,
            )
            return None

    def idioms(self, string, descriptive=False, verbose=False):
        """Process idioms from IDIOMS list.
        Each tuple in IDIOMS contains (pattern, replacement).
        inp: input string.
        descriptive: not used.
        verbose: boolean.

        >>> idioms("지금 mp3 파일을 다운받고 있어요")
        지금 엠피쓰리 파일을 다운받고 있어요
        """
        out = string

        for str1, str2 in self.idioms_list:
            out = re.sub(str1, str2, out)
        # gloss(verbose, out, string, rule)

        return out

    def __call__(
        self,
        string,
        descriptive=False,
        verbose=False,
        group_vowels=False,
        to_syl=False,
        use_dict=True,
    ):
        """Main function
        string: input string
        descriptive: boolean.
        verbose: boolean
        group_vowels: boolean. If True, the vowels of the
        identical sound are normalized.
        to_syl: boolean. If True, hangul letters or jamo
        are assembled to form syllables.

        For example, given an input string "나의 친구가 mp3 file 3개를 다운받고 있다",
        STEP 1. idioms
        -> 나의 친구가 엠피쓰리 file 3개를 다운받고 있다

        STEP 2. English to Hangul
        -> 나의 친구가 엠피쓰리 파일 3개를 다운받고 있다

        STEP 3. annotate
        -> 나의/J 친구가 엠피쓰리 파일 3개/B를 다운받고 있다

        STEP 4. Spell out arabic numbers
        -> 나의/J 친구가 엠피쓰리 파일 세개/B를 다운받고 있다

        STEP 5. decompose
        -> 나의/J 친구가 엠피쓰리 파일 세개/B를 다운받고 있다

        STEP 6-9. Hangul
        -> 나의 친구가 엠피쓰리 파일 세개를 다운받꼬 읻따
        """
        # 1. idioms
        string = self.idioms(string, descriptive, verbose)

        # 2 English to Hangul
        string = convert_eng(string, self.cmu)

        # 3. annotate
        if use_dict and self.mecab is not None:
            string = annotate(string, self.mecab)

        # 4. Spell out arabic numbers
        string = convert_num(string)

        # 5. decompose
        inp = h2j(string)

        # 6. special
        for func in (
            jyeo,
            ye,
            consonant_ui,
            josa_ui,
            vowel_ui,
            jamo,
            rieulgiyeok,
            rieulbieub,
            verb_nieun,
            balb,
            palatalize,
            modifying_rieul,
        ):
            inp = func(inp, descriptive, verbose)
        inp = re.sub("/[PJEB]", "", inp)

        # 7. regular table: batchim + onset
        for str1, str2, _rule_ids in self.table:
            _inp = inp
            inp = re.sub(str1, str2, inp)

            # if len(rule_ids)>0:
            #     rule = "\n".join(
            #         self.rule2text.get(rule_id, "")
            #         for rule_id in rule_ids
            #     )
            # else:
            #     rule = ""
            # gloss(verbose, inp, _inp, rule)

        # 8 link
        for func in (link1, link2, link4):  # remove link3
            inp = func(inp, descriptive, verbose)

        # 9. postprocessing
        if group_vowels:
            inp = group(inp)

        if to_syl:
            inp = compose(inp)
        # 국어법칙 적용하고 싶지 않을 때 문자들 사이에 ^ 사용.
        inp = inp.replace("^", "")
        return inp


if __name__ == "__main__":
    g2p = G2p()
    g2p("나의 친구가 mp3 file 3개를 다운받고 있다")
