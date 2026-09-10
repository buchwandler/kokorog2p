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
    class Selected:
        def __init__(self, order: tuple[str, ...]) -> None:
            self.order = order

        def lookup(self, lookup_word: str) -> LexiconHit | None:
            if lookup_word != word:
                return None
            name = self.order[0]
            return LexiconHit(
                f"pronunciation-{name}",
                name,
                9,
                "pronunciation",
                "kokoro-v1",
                f"de-de:{name}",
                {},
            )

    for order in ((first, second), (second, first)):
        lexicon = GermanLexicon.__new__(GermanLexicon)
        lexicon._backend = Selected(order)
        hit = lexicon._backend.lookup(word)
        assert hit is not None
        assert hit.lexicon_id == f"de-de:{order[0]}"
