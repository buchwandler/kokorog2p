"""Tests for SpeechMarkdown annotations."""

from kokorog2p import get_g2p
from kokorog2p.speechmarkdown import (
    phonemize_with_speechmarkdown,
    process_speechmarkdown,
    remove_speechmarkdown,
)


def test_process_speechmarkdown_ipa_attr():
    text = 'You say, (pecan)[ipa:"pɪˈkɑːn"].'
    clean, tokens, phonemes, languages = process_speechmarkdown(text)
    assert clean == "You say, pecan."
    assert phonemes[2] == "pɪˈkɑːn"
    assert languages == {}


def test_process_speechmarkdown_slash_ipa():
    text = "I say, (pecan)[/ˈpi.kæn/]."
    clean, tokens, phonemes, languages = process_speechmarkdown(text)
    assert clean == "I say, pecan."
    assert phonemes[2] == "ˈpi.kæn"
    assert languages == {}


def test_process_speechmarkdown_lang():
    text = 'In Paris, they pronounce it (Paris)[lang:"fr-FR"].'
    clean, tokens, phonemes, languages = process_speechmarkdown(text)
    assert clean == "In Paris, they pronounce it Paris."
    assert languages[5] == "fr-fr"
    assert phonemes == {}


def test_phonemize_with_speechmarkdown():
    text = '(pecan)[ipa:"pɪˈkɑːn"]'
    result = phonemize_with_speechmarkdown(text, "en-us")
    assert "pɪˈkɑːn" in result


def test_get_g2p_with_speechmarkdown():
    g2p = get_g2p("en-us", markdown_syntax="speechmarkdown")
    result = g2p.phonemize("(pecan)[/ˈpi.kæn/]")
    assert "ˈpi.kæn" in result


def test_remove_speechmarkdown():
    text = "I say, (pecan)[/ˈpi.kæn/]."
    assert remove_speechmarkdown(text) == "I say, pecan."
