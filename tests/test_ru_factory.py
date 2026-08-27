from kokorog2p import get_g2p
from kokorog2p.ru import RussianG2P


def test_russian_factory_aliases_are_native_and_lazy():
    for alias in ("ru", "ru-ru", "rus", "russian"):
        assert isinstance(get_g2p(alias), RussianG2P)


def test_russian_factory_cache_distinguishes_options():
    first = get_g2p("ru", accentuator="none", strict_stress=False)
    second = get_g2p("ru-ru", accentuator="none", strict_stress=False)
    assert first is second
    assert first is not get_g2p(
        "ru", accentuator="none", reduction=False, strict_stress=False
    )
