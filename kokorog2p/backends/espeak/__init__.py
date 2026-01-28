"""Espeak-ng backend for phonemization.

This package provides espeak-ng integration for converting text to phonemes.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

from kokorog2p.backends.espeak.backend import EspeakBackend
from kokorog2p.backends.espeak.voice import Voice, EspeakVoice
from kokorog2p.backends.espeak.wrapper import Phonemizer, EspeakWrapper
from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

__all__ = [
    "EspeakBackend",
    "EspeakWrapper",
    "EspeakVoice",
    "Phonemizer",
    "CliPhonemizer",
    "Voice",
]
