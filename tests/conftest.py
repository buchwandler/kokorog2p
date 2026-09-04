"""Pytest configuration and fixtures for kokorog2p tests."""

import gc
import hashlib
import json
import os
import shutil
from importlib.util import find_spec
from pathlib import Path

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


@pytest.fixture(scope="module", autouse=True)
def _reset_process_state() -> object:
    """Bound process-wide resources to one test module."""
    yield
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def _isolated_lexphon_data_home(tmp_path_factory: pytest.TempPathFactory):
    """Provision a tiny offline Lexphon store for German consumer tests."""
    if os.environ.get("KOKOROG2P_EXTERNAL_LEXPHON_DATA"):
        yield Path(os.environ["LEXPHON_DATA_HOME"])
        return
    import g2lex
    from lexphon import DataStore

    root = tmp_path_factory.mktemp("lexphon")
    release = root / "release"
    store_root = root / "store"
    release.mkdir()
    asset_specs = {
        "gold": {
            "haus": "haʊ̯s",
            "zwei": "ʦvaɪ",
            "fünf": "fʏnf",
            "zeit": "ʦaɪt",
            "die": "diː",
            "collision": "g",
        },
        "crane": {
            "haus": "haʊ̯s",
            "zwei": "ʦvaɪ",
            "fünf": "fʏnf",
            "zeit": "ʦaɪt",
            "collision": "c",
            "die": {"DEFAULT": "diː", "DET": "diː", "PRON": "diː"},
        },
        "espeak": {"haus": "hˈaʊs", "zwei": "ʦvaɪ", "die": "diː", "collision": "e"},
        "olaph": {"haus": "haʊ̯s", "zwei": "ʦvaɪ", "beer": "/beːʁ/", "collision": "o"},
    }
    artifacts = {}
    for name, entries in asset_specs.items():
        source = release / f"{name}.jsonl"
        rows = []
        for word, value in entries.items():
            if isinstance(value, dict):
                rows.append(
                    {"word": word, "kind": "tagged", "items": list(value.items())}
                )
            else:
                rows.append({"word": word, "kind": "scalar", "value": value})
        source.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
        asset = release / f"{name}.g2lex"
        g2lex.pack_file(
            source,
            asset,
            input_format="jsonl",
            source_id=f"de-de:{name}",
            metadata={"pronunciation_alphabet": "ipa"},
        )
        destination = store_root / "assets" / f"{name}.g2lex"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asset, destination)
        artifacts[f"de-de:{name}"] = {
            "id": f"de-de:{name}",
            "language": "de-DE",
            "name": name,
            "display_name": name,
            "kind": "pronunciation",
            "phoneme_encoding": "ipa",
            "data_version": "test-1",
            "release_tag": "data-test-1",
            "asset_path": str(destination.relative_to(store_root)),
            "asset_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "asset_size": destination.stat().st_size,
        }
    previous = os.environ.get("LEXPHON_DATA_HOME")
    os.environ["LEXPHON_DATA_HOME"] = str(store_root)
    DataStore(store_root)._write_index({"schema_version": 1, "artifacts": artifacts})
    yield store_root
    if previous is None:
        os.environ.pop("LEXPHON_DATA_HOME", None)
    else:
        os.environ["LEXPHON_DATA_HOME"] = previous


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


@pytest.fixture(scope="module")
def english_g2p_with_spacy():
    """Create an EnglishG2P with spaCy."""
    _require_spacy_model("en_core_web_sm")
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=True,
        spacy_model="en_core_web_sm",
    )


@pytest.fixture(scope="module")
def english_g2p_with_medium_spacy():
    """Create the medium-model G2P for model compatibility behavior tests."""
    _require_spacy_model("en_core_web_md")
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_spacy=True,
        spacy_model="en_core_web_md",
    )


@pytest.fixture(scope="module")
def english_g2p_full():
    """Create a fully-featured EnglishG2P."""
    pytest.importorskip("espeakng_loader")
    _require_spacy_model("en_core_web_sm")
    from kokorog2p.en import EnglishG2P

    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=True,
        use_spacy=True,
        spacy_model="en_core_web_sm",
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
