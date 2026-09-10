"""Pytest configuration and fixtures for kokorog2p tests."""

import gc
from importlib.util import find_spec

import pytest

# =============================================================================

# Markers

# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "espeak: tests that require espeak-ng to be installed"
    )
    config.addinivalue_line(
        "markers", "spacy: tests that require spaCy to be installed"
    )
    config.addinivalue_line("markers", "slow: tests that are slow to run")
    config.addinivalue_line(
        "markers", "integration: tests requiring explicitly provisioned external data"
    )
    config.addinivalue_line(
        "markers",
        "resource_heavy: tests that intentionally initialize high-memory "
        "optional or native resources",
    )


@pytest.fixture(scope="module", autouse=True)
def _reset_process_state() -> object:
    """Release KokoroG2P resources after each test module."""
    yield

    from kokorog2p import clear_cache

    clear_cache(deep=True)
    gc.collect()


def _require_spacy_model(name: str) -> None:
    """Skip model-backed fixtures when the optional package is absent."""
    pytest.importorskip("spacy")
    if find_spec(name) is None:
        pytest.skip(f"spaCy model {name!r} is not installed")


# =============================================================================
# Espeak Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def has_espeak() -> bool:
    """Check if espeak is available."""
    try:
        from kokorog2p.backends.espeak import EspeakWrapper

        wrapper = EspeakWrapper()
        return wrapper.version is not None
    except (ImportError, OSError, RuntimeError):
        return False


@pytest.fixture(scope="session")
def has_espeak_cli() -> bool:
    """Check if the espeak CLI is available."""
    try:
        from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

        return CliPhonemizer.is_available()
    except (ImportError, OSError):
        return False


@pytest.fixture
def espeak_backend(has_espeak):
    """Create an EspeakBackend instance for testing."""
    if not has_espeak:
        pytest.skip("eSpeak native backend not available")
    from kokorog2p.backends.espeak import EspeakBackend

    return EspeakBackend(language="en-us")


@pytest.fixture
def espeak_backend_cli():
    """Create an EspeakBackend instance for testing."""
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

    if not CliPhonemizer.is_available():
        pytest.skip("espeak CLI not available")

    return EspeakBackend(language="en-us", use_cli=True)


@pytest.fixture
def espeak_backend_gb(has_espeak):
    """Create a British EspeakBackend instance for testing."""
    if not has_espeak:
        pytest.skip("eSpeak native backend not available")
    from kokorog2p.backends.espeak import EspeakBackend

    return EspeakBackend(language="en-gb")


# =============================================================================
# G2P Fixtures
# =============================================================================


@pytest.fixture
def english_g2p_no_espeak():
    """Create an EnglishG2P without espeak fallback."""
    from kokorog2p.en import EnglishG2P

    g2p = EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=False,
    )
    try:
        yield g2p
    finally:
        g2p.close()


@pytest.fixture
def english_g2p_with_espeak(has_espeak):
    """Create an EnglishG2P with espeak fallback."""
    if not has_espeak:
        pytest.skip("eSpeak native backend not available")
    from kokorog2p.en import EnglishG2P

    g2p = EnglishG2P(
        language="en-us",
        use_espeak_fallback=True,
        use_spacy=False,
    )
    try:
        yield g2p
    finally:
        g2p.close()


@pytest.fixture(scope="module")
def english_g2p_with_spacy():
    """Create an EnglishG2P with spaCy."""
    _require_spacy_model("en_core_web_sm")
    from kokorog2p.en import EnglishG2P

    g2p = EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=True,
        spacy_model="en_core_web_sm",
    )
    try:
        yield g2p
    finally:
        g2p.close()


@pytest.fixture(scope="module")
def english_g2p_with_medium_spacy():
    """Create the medium-model G2P for model compatibility behavior tests."""
    _require_spacy_model("en_core_web_md")
    from kokorog2p.en import EnglishG2P

    g2p = EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=True,
        spacy_model="en_core_web_md",
    )
    try:
        yield g2p
    finally:
        g2p.close()


@pytest.fixture(scope="module")
def english_g2p_full(has_espeak):
    """Create a fully-featured EnglishG2P."""
    if not has_espeak:
        pytest.skip("eSpeak native backend not available")
    _require_spacy_model("en_core_web_sm")
    from kokorog2p.en import EnglishG2P

    g2p = EnglishG2P(
        language="en-us",
        use_espeak_fallback=True,
        use_spacy=True,
        spacy_model="en_core_web_sm",
    )
    try:
        yield g2p
    finally:
        g2p.close()


# =============================================================================
# Lexicon Fixtures
# =============================================================================


@pytest.fixture
def us_lexicon():
    """Create a US English lexicon."""
    from kokorog2p.en.lexicon import Lexicon

    lexicon = Lexicon(british=False)
    try:
        yield lexicon
    finally:
        lexicon.close()


@pytest.fixture
def gb_lexicon():
    """Create a British English lexicon."""
    from kokorog2p.en.lexicon import Lexicon

    lexicon = Lexicon(british=True)
    try:
        yield lexicon
    finally:
        lexicon.close()


# =============================================================================
# Sample Data
# =============================================================================


@pytest.fixture
def sample_words() -> list[tuple[str, str]]:
    """Sample words with expected phonemes (US English)."""
    return [
        ("hello", "hˈɛlO"),
        ("world", "wˈɜɹld"),
        ("the", "ðə"),
        ("cat", "kˈæt"),
        ("dog", "dˈɔɡ"),
    ]


@pytest.fixture
def sample_sentences() -> list[str]:
    """Sample sentences for testing."""
    return [
        "Hello world!",
        "The quick brown fox jumps over the lazy dog.",
        "How are you doing today?",
        "I can't believe it's not butter.",
    ]
