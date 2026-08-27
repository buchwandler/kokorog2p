import sys


def test_importing_russian_frontend_does_not_import_ruaccent():
    import kokorog2p.ru

    assert "ruaccent" not in sys.modules
    assert kokorog2p.ru.RussianG2P is not None
