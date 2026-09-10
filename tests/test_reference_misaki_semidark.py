from __future__ import annotations

import pytest

pytestmark = [pytest.mark.reference, pytest.mark.external_reference]


def test_semidark_german_provider_smoke() -> None:
    provider = pytest.importorskip("misaki")
    del provider
    from benchmarks.reference.providers import SemidarkGermanMisakiProvider

    result = SemidarkGermanMisakiProvider().phonemize(
        "Guten Tag!", case_id="smoke", language="de", model="1.0"
    )
    if result.error is not None:
        pytest.skip(result.error.message)
    assert result.phonemes
