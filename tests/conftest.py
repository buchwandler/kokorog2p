"""Pytest configuration and fixtures for kokorog2p tests."""

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
    except (ImportError, OSError):
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
def espeak_backend():
    """Create an EspeakBackend instance for testing."""
    pytest.importorskip("espeakng_loader")
    from kokorog2p.backends.espeak import EspeakBackend

    return EspeakBackend(language="en-us")


@pytest.fixture
def espeak_backend_cli():
    """Create an EspeakBackend instance for testing."""
    pytest.importorskip("espeakng_loader")
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

    if not CliPhonemizer.is_available():
        pytest.skip("espeak CLI not available")

    return EspeakBackend(language="en-us", use_cli=True)


@pytest.fixture
def espeak_backend_gb():
    """Create a British EspeakBackend instance for testing."""
    pytest.importorskip("espeakng_loader")
    from kokorog2p.backends.espeak import EspeakBackend

    return EspeakBackend(language="en-gb")


# =============================================================================
# G2P Fixtures
# =============================================================================


@pytest.fixture
def english_g2p_no_espeak():
    """Create an EnglishG2P without espeak fallback."""
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=False,
    )


@pytest.fixture
def english_g2p_with_espeak():
    """Create an EnglishG2P with espeak fallback."""
    pytest.importorskip("espeakng_loader")
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=True,
        use_spacy=False,
    )


@pytest.fixture
def english_g2p_with_spacy():
    """Create an EnglishG2P with spaCy."""
    pytest.importorskip("spacy")
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=True,
    )


@pytest.fixture
def english_g2p_full():
    """Create a fully-featured EnglishG2P."""
    pytest.importorskip("espeakng_loader")
    pytest.importorskip("spacy")
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=True,
        use_spacy=True,
    )


# =============================================================================
# Lexicon Fixtures
# =============================================================================


@pytest.fixture
def us_lexicon():
    """Create a US English lexicon."""
    from kokorog2p.en.lexicon import Lexicon

    return Lexicon(british=False)


@pytest.fixture
def gb_lexicon():
    """Create a British English lexicon."""
    from kokorog2p.en.lexicon import Lexicon

    return Lexicon(british=True)


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
