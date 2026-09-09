import pytest

from kokorog2p.de import GermanLexicon
from kokorog2p.en.lexicon import Lexicon
from kokorog2p.lexicons.runtime import LexiconHit


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


@pytest.mark.parametrize(
    ("word", "first", "second"),
    (
        ("collision", "gold", "espeak"),
        ("collision", "gold", "olaph"),
        ("collision", "espeak", "olaph"),
        ("collision", "crane", "espeak"),
    ),
)
def test_german_precedence_follows_explicit_order(word, first, second) -> None:
    lexicon = GermanLexicon(lexicons=(first, second))
    try:
        hit = lexicon._backend.lookup(word)
        assert hit is not None
        assert hit.lexicon_id == f"de-de:{first}"
    finally:
        lexicon.close()

    lexicon = GermanLexicon(lexicons=(second, first))
    try:
        hit = lexicon._backend.lookup(word)
        assert hit is not None
        assert hit.lexicon_id == f"de-de:{second}"
    finally:
        lexicon.close()
