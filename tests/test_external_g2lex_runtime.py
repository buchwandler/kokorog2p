from pathlib import Path

import pytest
from lexphon.errors import LexiconNotInstalledError

from kokorog2p.lexicons import runtime


class FakeStore:
    def __init__(self, root: Path, available: bool = True) -> None:
        self.root = root
        self.available = available

    def path(self, identifier: str) -> Path:
        if not self.available:
            raise LexiconNotInstalledError(identifier)
        return self.root / f"{identifier.replace(':', '_')}.g2lex"


class FakeLexicon(dict):
    def __init__(self) -> None:
        super().__init__({"hello": "hɛˈloʊ"})
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_external_runtime_opens_read_only_and_keys_cache_by_store(
    monkeypatch, tmp_path
) -> None:
    runtime.clear_resource_cache()
    handles = []

    def fake_open(path):
        handle = FakeLexicon()
        handles.append(handle)
        return handle

    monkeypatch.setattr(runtime.g2lex, "open", fake_open)
    first_store = FakeStore(tmp_path / "one")
    second_store = FakeStore(tmp_path / "two")

    first = runtime.open_selected("en-us", ("gold",), store=first_store)
    second = runtime.open_selected("en-us", ("gold",), store=second_store)
    assert first.get_hit("hello").lexicon_id == "en-us:gold"
    assert second.get_hit("hello").lexicon_id == "en-us:gold"
    assert len(handles) == 2
    assert runtime.resource_cache_info().currsize == 2
    first.close()
    second.close()
    runtime.clear_resource_cache()
    assert all(handle.closed for handle in handles)


def test_missing_external_asset_is_actionable(tmp_path) -> None:
    with pytest.raises(
        LexiconNotInstalledError,
        match="lexphon data install en-us:gold",
    ):
        runtime.open_selected(
            "en-us", ("gold",), store=FakeStore(tmp_path, available=False)
        )
