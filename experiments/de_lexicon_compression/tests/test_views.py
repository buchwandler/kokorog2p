from experiments.de_lexicon_compression.lexlab.kokoro_view import to_kokoro_view


def test_views_are_explicit_and_source_specific():
    assert to_kokoro_view("gruut_espeak", "h a u s") == "haus"
    assert to_kokoro_view("builtin", "h a u s") == "h a u s"
    assert to_kokoro_view("crane_wiktionary", "t͡s aʊ") == "ʦ W"
