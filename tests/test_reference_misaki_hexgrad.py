from __future__ import annotations

import pytest

pytestmark = [pytest.mark.reference, pytest.mark.external_reference]


def test_hexgrad_english_provider_smoke() -> None:
    provider = pytest.importorskip("misaki")
    del provider
    from benchmarks.reference.providers import HexgradEnglishMisakiProvider

    result = HexgradEnglishMisakiProvider().phonemize(
        "Hello, world!", case_id="smoke", language="en-us", model="1.0"
    )
    if result.error is not None:
        pytest.skip(result.error.message)
    assert result.phonemes
