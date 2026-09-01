"""Tests for the prepared-text KokoroG2P core contract."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

import pytest

from kokorog2p import (
    TokenAnnotation,
    annotations_for_segment,
    phonemize_prepared,
    phonemize_segments,
)
from kokorog2p.token import GToken
from kokorog2p.tokenization import coerce_token_annotations


@dataclass
class Segment:
    text: str
    char_start: int
    char_end: int


class AnnotatedFakeG2P:
    use_spacy = True
    version = "1.0"

    def __call__(self, text: str) -> list[GToken]:
        assert not self.use_spacy
        token = GToken(text=text, whitespace="", phonemes="base")
        token.set("char_start", 0)
        token.set("char_end", len(text))
        return [token]

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        return "noun" if tag == "NN" else None


def test_prepared_text_does_not_expand_semantics() -> None:
    result = phonemize_prepared("2 kg", language="en-us", use_spacy=False)
    assert result.clean_text == "2 kg"
    assert result.extended_text == "2 kg"


def test_external_annotations_supply_pos_without_spacy() -> None:
    result = phonemize_prepared(
        "record",
        language="en-us",
        annotations=[TokenAnnotation(0, 6, "record", pos="NOUN", tag="NN")],
        g2p=AnnotatedFakeG2P(),
        return_ids=False,
    )
    assert result.phonemes == "noun"
    assert result.tokens[0].meta["tag"] == "NN"


def test_annotation_validation_is_ordered_and_source_aligned() -> None:
    with pytest.raises(ValueError):
        coerce_token_annotations(
            "record this",
            [TokenAnnotation(0, 6, "record"), TokenAnnotation(5, 10, "d thi")],
        )
    with pytest.raises(ValueError):
        coerce_token_annotations("record", [TokenAnnotation(0, 6, "wrong")])


def test_segment_annotations_are_rebased() -> None:
    text = "record this"
    annotations = [TokenAnnotation(0, 6, "record", tag="NN")]
    rebased = annotations_for_segment(0, 6, annotations, clean_text=text)
    assert [(item.start, item.end, item.text) for item in rebased] == [(0, 6, "record")]
    results = phonemize_segments(
        text,
        [Segment("record", 0, 6)],
        annotations=annotations,
        phonemize=phonemize_prepared,
        language="en-us",
        use_spacy=False,
        return_ids=False,
    )
    assert results[0].tokens[0].char_start == 0


def test_prepared_path_has_no_automatic_detector_dependency() -> None:
    result = phonemize_prepared("Hello world", language="en-us", use_spacy=False)
    assert result.phonemes


def test_core_import_and_prepared_path_work_without_spokenform() -> None:
    code = """
import builtins
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'spokenform' or name.startswith('spokenform.'):
        raise ModuleNotFoundError('blocked')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
from kokorog2p import phonemize_prepared
assert phonemize_prepared('Hello world!', language='en-us', use_spacy=False).phonemes
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
