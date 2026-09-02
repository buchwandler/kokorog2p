"""
https://github.com/kyubyong/g2pK
"""

import re
import warnings

from jamo import h2j

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
from .utils import annotate, compose, group, parse_table


class _MecabKoAdapter:
    """Adapt mecab-ko's raw Tagger output to the g2pkc ``pos`` API."""

    def __init__(self, tagger):
        self.tagger = tagger

    def pos(self, text):
        tokens = []
        for line in self.tagger.parse(text).splitlines():
            if not line or line == "EOS" or "\t" not in line:
                continue
            surface, features = line.split("\t", 1)
            tokens.append((surface, features.split(",", 1)[0]))
        return tokens


class G2p:
    def __init__(self, morphology: str = "auto", morphology_backend: str = "auto"):
        self.mecab = self.get_mecab(
            morphology=morphology, morphology_backend=morphology_backend
        )
        self.table = parse_table()

    def get_mecab(self, morphology="auto", morphology_backend="auto"):
        if morphology == "off":
            return None
        if morphology_backend in ("auto", "python-mecab-ko"):
            try:
                from mecab import MeCab

                return MeCab()
            except ImportError as exc:
                python_mecab_error = exc
        else:
            python_mecab_error = None

        if morphology_backend in ("auto", "mecab-ko"):
            try:
                from mecab_ko import Tagger

                return _MecabKoAdapter(Tagger())
            except ImportError as exc:
                mecab_ko_error = exc
        else:
            mecab_ko_error = None

        if morphology == "required":
            raise ImportError(
                "Korean morphology requires python-mecab-ko or mecab-ko. "
                "Install python-mecab-ko with: python -m pip install python-mecab-ko"
            ) from (python_mecab_error or mecab_ko_error)

        warnings.warn(
            "Korean morphology is unavailable; using morphology-free G2P. "
            "Install python-mecab-ko for Korean POS tagging.",
            UserWarning,
            stacklevel=2,
        )
        return None

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

        The caller must provide prepared, speakable text.
        """
        # 3. annotate
        if use_dict and self.mecab is not None:
            string = annotate(string, self.mecab)

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
