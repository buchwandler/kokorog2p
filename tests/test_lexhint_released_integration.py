from __future__ import annotations

import os

import pytest
from lexphon import DataStore

from kokorog2p.lexicons.lexphon_backend import LexphonBackend


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("KOKOROG2P_EXTERNAL_LEXPHON_DATA"),
    reason="released Lexphon data is not provisioned",
)
def test_released_lexhint_assets_are_usable() -> None:
    store = DataStore()
    for language in ("ru-ru", "th-th", "vi-vn", "ja-jp", "ko-kr", "pt-br"):
        backend = LexphonBackend(language, ("lexhint",), store=store)
        try:
            assert len(backend) > 0, language
        finally:
            backend.close()
