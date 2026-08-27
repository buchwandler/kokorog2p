from kokorog2p.ru import RussianG2P


class FakeAccent:
    name = "fake"

    def accentuate(self, text):
        return text.replace("Елка", "Ёлка").replace("слово", "сло́во")


class FakeEngine:
    def phonemize_marked(self, text):
        return "bˈo"


def test_russian_orchestration_preserves_original_offsets_and_brackets():
    g2p = RussianG2P(accentuator=FakeAccent(), engine=FakeEngine())
    tokens = g2p("Елка [слово]!")
    assert [token.text for token in tokens] == ["Елка", "[", "слово", "]", "!"]
    assert [(token.get("char_start"), token.get("char_end")) for token in tokens] == [
        (0, 4),
        (5, 6),
        (6, 11),
        (11, 12),
        (12, 13),
    ]
    assert tokens[1].phonemes == "("
    assert tokens[2].get("accented_text") == "сло́во"


def test_explicit_stress_path_bypasses_accentuator():
    class FailingAccent:
        def accentuate(self, text):
            raise AssertionError("contextual adapter must not run")

    g2p = RussianG2P(accentuator=FailingAccent(), engine=FakeEngine())
    tokens = g2p.phonemize_accented("за́мок")
    assert tokens[0].get("accented_text") == "за́мок"


def test_latin_policy_preserves_or_drops_source_token():
    g2p = RussianG2P(accentuator="none", engine=FakeEngine(), strict_stress=False)
    assert g2p("hello")[0].get("source_kind") == "LATIN_PRESERVED"
    dropped = RussianG2P(
        accentuator="none",
        engine=FakeEngine(),
        latin_policy="drop",
        strict_stress=False,
    )
    assert dropped("hello")[0].get("drop") is True
