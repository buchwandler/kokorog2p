"""Legacy CLI eSpeak import path backed by ``espeakng-runtime``."""

from espeakng_runtime import EspeakUnavailableError

from kokorog2p.backends.espeak.compat import CliPhonemizer

EspeakCliError = EspeakUnavailableError

__all__ = ["CliPhonemizer", "EspeakCliError"]
