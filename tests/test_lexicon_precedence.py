import g2lex

from kokorog2p.en.lexicon import Lexicon
from kokorog2p.lexicons.runtime import LexiconHit


def test_layered_lexicon_first_matching_layer_wins() -> None:
    first = g2lex.LexiconLayer("fixture", {"collision": "from-first"}, {"rating": 9})
    second = g2lex.LexiconLayer(
        "alternate", {"collision": "from-second"}, {"rating": 1}
    )
    layered = g2lex.LayeredLexicon((first, second))
    try:
        assert layered.get_hit("collision").value == "from-first"
    finally:
        layered.close()


def test_english_delegates_precedence_to_selected_stack() -> None:
    class Selected:
        def get_hit(self, word: str) -> LexiconHit | None:
            if word == "collision":
                return LexiconHit(
                    "from-fixture",
                    "fixture",
                    9,
                    "pronunciation",
                    "kokoro-v1",
                    "en-us:fixture",
                    {},
                )
            return None

    lexicon = Lexicon.__new__(Lexicon)
    lexicon._selected = Selected()
    hit = lexicon._get_hit("collision")
    assert hit is not None
    assert hit.name == "fixture"
    assert hit.value == "from-fixture"
