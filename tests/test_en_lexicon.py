from kokorog2p.en import lexicon as en_lexicon
from kokorog2p.en.lexicon import Lexicon
from kokorog2p.lexicons.runtime import LexiconHit


class FakeSelected:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get_hit(self, word: str) -> LexiconHit | None:
        if word not in self.values:
            return None
        return LexiconHit(
            value=self.values[word],
            name="gold",
            rating=4,
            kind="pronunciation",
            phoneme_encoding="kokoro-v1",
            lexicon_id="en-us:gold",
            metadata={"id": "en-us:gold"},
        )

    def __contains__(self, word: object) -> bool:
        return word in self.values

    def close(self) -> None:
        pass


def test_lookup_uses_one_external_gold_layer(monkeypatch) -> None:
    selected = FakeSelected({"hello": "hɛˈloʊ", "word": "wɝːd"})
    monkeypatch.setattr(en_lexicon, "open_selected", lambda *args, **kwargs: selected)

    lexicon = Lexicon(british=False, lexicons=("gold",))
    assert lexicon.lexicons == ("gold",)
    assert lexicon.lookup("hello") == ("hɛˈloʊ", 4)
    assert lexicon.lookup("missing") == (None, None)
    lexicon.close()


def test_no_lexicon_selection_does_not_require_external_data(monkeypatch) -> None:
    selected = FakeSelected({})
    calls = []
    monkeypatch.setattr(
        en_lexicon,
        "open_selected",
        lambda language, names, **kwargs: calls.append((language, names)) or selected,
    )

    lexicon = Lexicon(lexicons=())
    assert lexicon.lexicons == ()
    assert calls == [("en-us", ())]
    assert lexicon.lookup("missing") == (None, None)
    lexicon.close()


def test_mapping_values_support_tag_selection(monkeypatch) -> None:
    selected = FakeSelected({"read": {"VERB": "ɹiːd", "DEFAULT": "ɹɛd"}})
    monkeypatch.setattr(en_lexicon, "open_selected", lambda *args, **kwargs: selected)

    lexicon = Lexicon(lexicons=("gold",))
    assert lexicon.lookup("read", tag="VBP") == ("ɹiːd", 4)
    assert lexicon.lookup("read", tag="NN") == ("ɹɛd", 4)
    lexicon.close()
