from __future__ import annotations

from pathlib import Path

import pytest
from lexphon import DataStore, LexiconNotInstalledError

from kokorog2p.lexicons.lexphon_backend import LexphonBackend


class _FakePhonemizer:
    def __init__(self) -> None:
        self.closed = False
        self.layers = ()

    def lookup(self, word: str, *, tag: str | None = None):
        return (word, tag)

    def lookup_prefixes(self, text: str, *, position: int = 0, tag: str | None = None):
        return (text[position:], tag)

    def close(self) -> None:
        self.closed = True


def test_backend_keeps_phonemizer_lazy() -> None:
    fake = _FakePhonemizer()
    backend = LexphonBackend("ru-ru", ("lexhint",), phonemizer=fake)  # type: ignore[arg-type]
    assert backend.ids == ("ru:lexhint",)
    assert backend.lookup("слово") == ("слово", None)
    assert backend.lookup_prefixes("слово", position=1) == ("лово", None)
    backend.close()
    assert fake.closed


def test_backend_does_not_open_missing_data_until_lookup(tmp_path: Path) -> None:
    backend = LexphonBackend("th-th", ("lexhint",), store=DataStore(tmp_path / "store"))
    try:
        with pytest.raises(LexiconNotInstalledError) as error:
            backend.lookup("ไทย")
        message = str(error.value)
        assert "th:lexhint" in message
        assert "lexphon data install th:lexhint" in message
        assert "lexphon data verify th:lexhint" in message
    finally:
        backend.close()
