import g2lex
import pytest

from kokorog2p.en.lexicon import Lexicon
from kokorog2p.lexicons.runtime import LexiconHit, open_selected


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


def test_selected_candidates_preserve_layer_precedence_over_casing():
    from kokorog2p.lexicons.runtime import SelectedLexicons

    selected = SelectedLexicons.__new__(SelectedLexicons)
    selected._closed = False
    selected._specs = (
        type(
            "Spec",
            (),
            {
                "name": "gold",
                "id": "de-de:gold",
                "rating": 1,
                "kind": "pronunciation",
                "phoneme_encoding": "ipa",
                "metadata": {},
            },
        )(),
        type(
            "Spec",
            (),
            {
                "name": "crane",
                "id": "de-de:crane",
                "rating": 1,
                "kind": "pronunciation",
                "phoneme_encoding": "ipa",
                "metadata": {},
            },
        )(),
    )
    selected._layered = g2lex.LayeredLexicon(
        (
            g2lex.LexiconLayer("gold", {"haus": "GOLD"}, {}),
            g2lex.LexiconLayer("crane", {"Haus": "CRANE"}, {}),
        )
    )
    try:
        assert selected.get_hit_candidates(("Haus", "haus", "HAUS")).value == "GOLD"
    finally:
        selected._layered.close()
        selected._closed = True


@pytest.mark.parametrize(
    ("word", "first", "second"),
    (
        ("ab", "gold", "espeak"),
        ("a", "gold", "olaph"),
        ("2.", "espeak", "olaph"),
        ("2.", "crane", "espeak"),
    ),
)
def test_german_precedence_follows_explicit_order(word, first, second) -> None:
    with open_selected("de-de", (first, second)) as selected:
        hit = selected.get_hit(word)
        assert hit is not None
        assert hit.name == first

    with open_selected("de-de", (second, first)) as selected:
        hit = selected.get_hit(word)
        assert hit is not None
        assert hit.name == second
