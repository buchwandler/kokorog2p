"""Thai prepared-text normalization contract tests."""

from kokorog2p.th.normalizer import ThaiNormalizer


def test_thai_semantic_forms_are_preserved() -> None:
    normalizer = ThaiNormalizer()
    for text in ("๑๒๓", "21", "2.05", "฿20", "โทร 0812345678", "12:05"):
        assert normalizer(text) == text


def test_punctuation_accents_and_combining_marks() -> None:
    normalizer = ThaiNormalizer()
    result = normalizer("“Café”… ก่ก่ก่ 😊")
    assert "Cafe" in result
    assert "…" in result
    assert "ก่" in result
    assert "😊" not in result
    assert any(
        item["kind"] == "TH_UNSUPPORTED_SOURCE_SYMBOL"
        for item in normalizer.diagnostics
    )


def test_structured_replacements_are_not_part_of_the_core() -> None:
    assert list(ThaiNormalizer().iter_structured_replacements("ราคา ๒๐ บาท")) == []
