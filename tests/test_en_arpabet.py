import pytest

from kokorog2p.en.arpabet import arpabet_to_kokoro

SUPPORTED_SYMBOLS = (
    "B",
    "CH",
    "D",
    "DH",
    "F",
    "G",
    "HH",
    "JH",
    "K",
    "L",
    "M",
    "N",
    "NG",
    "P",
    "R",
    "S",
    "SH",
    "T",
    "TH",
    "V",
    "W",
    "Y",
    "Z",
    "ZH",
    "AA",
    "AE",
    "AH",
    "AO",
    "AW",
    "AY",
    "EH",
    "ER",
    "EY",
    "IH",
    "IY",
    "OW",
    "OY",
    "UH",
    "UW",
)


@pytest.mark.parametrize("symbol", SUPPORTED_SYMBOLS)
def test_supported_arpabet_symbols_convert(symbol: str) -> None:
    assert arpabet_to_kokoro(f"{symbol}1")


def test_stress_markers_are_preserved() -> None:
    assert arpabet_to_kokoro("HH AH0 L OW1") == "həlˈO"
    assert arpabet_to_kokoro("K AH2 T") == "kˌət"


@pytest.mark.parametrize("pronunciation", ["", "NOPE", "AA3", "aa1", "AA?"])
def test_unknown_arpabet_fails_closed(pronunciation: str) -> None:
    with pytest.raises(ValueError):
        arpabet_to_kokoro(pronunciation)
