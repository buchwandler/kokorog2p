import pytest

from kokorog2p.ru.alignment import RussianAlignmentError, align_accented_text


def test_alignment_maps_inserted_acute_and_yo_to_original_spans():
    source = "Елка и ёлка"
    alignment = align_accented_text(source, "Е́лка и ё́лка", adapter_name="fake")
    assert alignment.accented_for_source(0, 4) == "Е́лка"
    assert alignment.accented_for_source(7, 11) == "ё́лка"


def test_alignment_preserves_punctuation_quotes_and_latin():
    source = '"Привет", world!'
    accented = '"При́вет", world!'
    alignment = align_accented_text(source, accented)
    assert alignment.accented_for_source(0, 8) == '"При́вет"'


def test_alignment_rejects_normal_character_rewrites_with_diagnostics():
    with pytest.raises(RussianAlignmentError, match="adapter='fake'.*source excerpt"):
        align_accented_text("слово", "слова", adapter_name="fake")
