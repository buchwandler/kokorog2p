"""Tests for Japanese benchmark contracts that do not require native backends."""

from benchmarks.benchmark_ja_comparison import create_g2p
from scripts.compare_ja_frontends import compare


def test_comparison_uses_distinct_backend_selector(monkeypatch) -> None:
    selected = []

    class FakeJapaneseG2P:
        def __init__(self, **kwargs):
            selected.append(kwargs["backend"])

    monkeypatch.setattr("kokorog2p.ja.JapaneseG2P", FakeJapaneseG2P)
    create_g2p({"backend": "pyopenjtalk"})
    create_g2p({"backend": "cutlet"})
    assert selected == ["pyopenjtalk", "cutlet"]


def test_frontend_comparison_classifies_model_input_changes() -> None:
    reference = {
        "environment": {"label": "upstream"},
        "rows": [
            {"text": "今日は", "frontend": [{"pron": "キョウ"}], "model_input": "abc"}
        ],
    }
    candidate = {
        "environment": {"label": "plus"},
        "rows": [
            {"text": "今日は", "frontend": [{"pron": "キョー"}], "model_input": "def"}
        ],
    }
    result = compare(reference, candidate)
    assert result["differences"] == [
        {
            "text": "今日は",
            "frontend_changed": True,
            "model_input_changed": True,
            "classification": "model_input_changed",
        }
    ]
