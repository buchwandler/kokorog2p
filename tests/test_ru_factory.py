from kokorog2p import get_g2p
from kokorog2p.ru import RussianG2P


def test_russian_factory_aliases_are_native_and_lazy() -> None:
    for alias in ("ru", "ru-ru", "rus", "russian"):
        g2p = get_g2p(alias)
        assert isinstance(g2p, RussianG2P)
        assert g2p._lexphon is not None
        assert g2p._lexphon._phonemizer is None


def test_russian_factory_cache_distinguishes_store_identity() -> None:
    first = get_g2p("ru", store=object())
    second = get_g2p("ru", store=object())
    assert first is not second
