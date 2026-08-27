from kokorog2p.ru.model_profile import model_profile_vocab
from kokorog2p.vocab import get_vocab


def test_russian_profile_does_not_mutate_or_replace_stock_mapping():
    stock = get_vocab("1.0")
    profile = model_profile_vocab()
    assert profile == stock
    profile["§"] = 999
    assert "§" not in get_vocab("1.0")
