"""Independent Thai normalization contract tests."""

from kokorog2p.th.normalizer import ThaiNormalizer


def test_thai_digits_and_cardinals() -> None:
    normalizer = ThaiNormalizer()
    assert normalizer("๑๒๓") == "หนึ่งร้อยยี่สิบสาม"
    assert normalizer("21") == "ยี่สิบเอ็ด"


def test_decimal_zeroes_and_ranges() -> None:
    normalizer = ThaiNormalizer()
    assert normalizer("2.05") == "สอง จุด ศูนย์ ห้า"
    assert normalizer("3-5") == "สาม ถึง ห้า"


def test_laughter_and_quantity_context() -> None:
    normalizer = ThaiNormalizer()
    assert normalizer("555") == "ฮ่า ฮ่า ฮ่า"
    assert normalizer("555 คน") == "ห้าร้อยห้าสิบห้า คน"


def test_currency_math_and_repetition() -> None:
    normalizer = ThaiNormalizer()
    assert normalizer("฿20") == "ยี่สิบ บาท"
    assert normalizer("50% + 2 = 52") == "ห้าสิบ เปอร์เซ็นต์ บวก สอง เท่ากับ ห้าสิบสอง"
    assert normalizer("เร็วๆ") == "เร็ว เร็ว"


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


def test_p1_identifier_time_and_address_forms() -> None:
    normalizer = ThaiNormalizer()
    assert normalizer("โทร 0812345678") == "โทร ศูนย์ แปด หนึ่ง สอง สาม สี่ ห้า หก เจ็ด แปด"
    assert normalizer("12:05") == "สิบสอง นาฬิกา ศูนย์ ห้า นาที"
    assert normalizer("บ้าน 12/4") == "บ้าน หนึ่ง สอง ขีด สี่"


def test_structured_replacement_is_source_aligned() -> None:
    normalizer = ThaiNormalizer()
    replacements = list(normalizer.iter_structured_replacements("ราคา ๒๐ บาท"))
    assert len(replacements) == 1
    assert replacements[0].start == len("ราคา ")
    assert replacements[0].end == len("ราคา ๒๐ บาท")
    assert "ยี่สิบ" in replacements[0].text
