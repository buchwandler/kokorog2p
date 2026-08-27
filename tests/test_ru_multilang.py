from kokorog2p.multilang import _detect_script_language


def test_cyrillic_fast_path_requires_allowed_russian():
    assert _detect_script_language("Привет", ["en", "ru"]) == "ru"
    assert _detect_script_language("Привет", ["en"]) is None
