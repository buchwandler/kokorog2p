from __future__ import annotations

import pytest

from kokorog2p.zh.g2p import ChineseG2P


def test_chinese_prepared_input_does_not_use_legacy_numeric_conversion() -> None:
    g2p = ChineseG2P.__new__(ChineseG2P)
    g2p._kokorog2p_prepared_input = True
    g2p.version = "1.0"
    g2p.unk = ""
    g2p.map_punctuation = lambda text: text
    g2p.legacy_call = lambda text: text
    assert g2p._phonemize_internal("１２") == ("１２", None)


def test_japanese_cutlet_prepared_input_keeps_digits_as_digits() -> None:
    Cutlet = pytest.importorskip("kokorog2p.ja.cutlet").Cutlet
    cutlet = Cutlet.__new__(Cutlet)
    cutlet.prepared_input = True
    assert cutlet._normalize_text("１２３") == "123"
