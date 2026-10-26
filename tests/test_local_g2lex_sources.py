import hashlib
import json
from pathlib import Path

import g2lex
import pytest

from kokorog2p import TokenAnnotation, get_g2p, phonemize_prepared
from kokorog2p.en.lexicon import Lexicon
from kokorog2p.lexicons import (
    FileLexiconSource,
    NamedLexiconSource,
    clear_resource_cache,
    open_sources,
    resource_cache_info,
    runtime,
)


class FakeStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, identifier: str) -> Path:
        return self.root / f"{identifier.replace(':', '_')}.g2lex"


def _write_g2lex(
    tmp_path: Path,
    name: str,
    entries: dict[str, object],
    *,
    language: str = "en-us",
    encoding: str = "ipa",
) -> Path:
    source = tmp_path / f"{name}.json"
    output = tmp_path / f"{name}.g2lex"
    source.write_text(json.dumps(entries), encoding="utf-8")
    g2lex.pack_file(
        source,
        output,
        input_format="kokoro-json",
        metadata={
            "id": f"fixture:{name}",
            "name": name,
            "language": language,
            "phoneme_encoding": encoding,
        },
    )
    return output


@pytest.fixture(autouse=True)
def _clear_runtime_cache():
    clear_resource_cache()
    yield
    clear_resource_cache()


def test_local_file_opens_with_content_and_manifest_provenance(tmp_path: Path) -> None:
    path = _write_g2lex(tmp_path, "local", {"hello": "hɛˈloʊ"})

    with open_sources("en-US", (FileLexiconSource(path),)) as selected:
        hit = selected.get_hit("hello")
        assert hit is not None
        assert hit.value == "hɛˈloʊ"
        assert hit.name == "local"
        assert hit.lexicon_id == "fixture:local"
        assert hit.source_kind == "file"
        assert hit.source_path == str(path.resolve())
        assert hit.sha256 == f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        assert hit.logical_sha256
        assert hit.phoneme_encoding == "ipa"
        assert hit.metadata["language"] == "en-us"


def test_local_file_precedes_named_stack_and_named_stack_remains_ordered(
    tmp_path: Path,
) -> None:
    local = _write_g2lex(tmp_path, "local", {"collision": "local", "local_only": "l"})
    store_root = tmp_path / "store"
    store_root.mkdir()
    _write_g2lex(
        store_root,
        "en-us_gold",
        {"collision": "named", "named_only": "named"},
    )
    store = FakeStore(store_root)

    with open_sources(
        "en-us",
        (FileLexiconSource(local), NamedLexiconSource("gold")),
        store=store,
    ) as selected:
        assert selected.get_hit("collision").value == "local"
        assert selected.get_hit("collision").source_kind == "file"
        assert selected.get_hit("named_only").value == "named"
        assert selected.get_hit("named_only").source_kind == "named"

    first = _write_g2lex(tmp_path, "first", {"collision": "first"})
    second = _write_g2lex(tmp_path, "second", {"collision": "second"})
    with open_sources(
        "en-us", (FileLexiconSource(first), FileLexiconSource(second))
    ) as selected:
        assert selected.get_hit("collision").value == "first"


def test_name_only_open_selected_remains_compatible(tmp_path: Path) -> None:
    store_root = tmp_path / "store"
    store_root.mkdir()
    _write_g2lex(store_root, "en-us_gold", {"hello": "named"})

    with runtime.open_selected(
        "en-us", ("gold",), store=FakeStore(store_root)
    ) as selected:
        assert selected.names == ("gold",)
        assert selected.get_hit("hello").value == "named"
        assert selected.get_hit("hello").source_kind == "named"


def test_exact_english_tag_selects_vbn_before_parent_and_default(
    tmp_path: Path,
) -> None:
    path = _write_g2lex(
        tmp_path,
        "read",
        {
            "read": {
                "DEFAULT": "riːd",
                "VERB": "riːd",
                "VB": "riːd",
                "VBD": "rɛd",
                "VBN": "rɛd",
            }
        },
    )
    lexicon = Lexicon(lexicons=(), g2lex_files=(FileLexiconSource(path),))
    try:
        assert lexicon.lookup("read", "VBN")[0] == "ɹɛd"
        assert lexicon.lookup("read", "VB")[0] == "ɹid"
    finally:
        lexicon.close()


def test_prepared_annotations_keep_exact_tag_for_local_lexicon(tmp_path: Path) -> None:
    path = _write_g2lex(
        tmp_path,
        "prepared-read",
        {"read": {"DEFAULT": "riːd", "VERB": "riːd", "VBN": "rɛd"}},
    )
    g2p = get_g2p(
        "en-us",
        lexicons=(),
        g2lex_files=(FileLexiconSource(path),),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    try:
        result = phonemize_prepared(
            "had read",
            language="en-us",
            annotations=[
                TokenAnnotation(
                    4,
                    8,
                    "read",
                    pos="VERB",
                    tag="VBN",
                    lemma="read",
                    morph="VerbForm=Part",
                )
            ],
            g2p=g2p,
            return_ids=False,
        )
        read_token = next(token for token in result.tokens if token.text == "read")
        assert read_token.meta["phonemes"] == "ɹɛd"
        assert read_token.meta["pronunciation_source"] == "local-g2lex"
        source_details = read_token.meta["pronunciation_source_details"]
        assert source_details["source_path"] == str(path.resolve())
        assert source_details["sha256"] == (
            f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        )
    finally:
        g2p.close()


def test_file_hash_pin_and_logical_hash_are_verified(tmp_path: Path) -> None:
    path = _write_g2lex(tmp_path, "pinned", {"hello": "hɛˈloʊ"})
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    with g2lex.open(path) as handle:
        logical_hash = str(handle.metadata["logical_sha256"])

    with open_sources(
        "en-us",
        (
            FileLexiconSource(
                path,
                sha256=f"sha256:{content_hash}",
                logical_sha256=logical_hash,
            ),
        ),
    ) as selected:
        assert selected.get_hit("hello") is not None

    with pytest.raises(ValueError, match="content hash does not match"):
        open_sources("en-us", (FileLexiconSource(path, sha256="0" * 64),))

    with pytest.raises(ValueError, match="logical hash does not match"):
        open_sources("en-us", (FileLexiconSource(path, logical_sha256="0" * 64),))


def test_file_change_at_same_path_gets_a_fresh_resource(tmp_path: Path) -> None:
    path = _write_g2lex(tmp_path, "mutable", {"word": "first"})
    first = open_sources("en-us", (FileLexiconSource(path),))
    try:
        original_hash = first.get_hit("word").sha256
        _write_g2lex(tmp_path, "replacement", {"word": "second"})
        replacement = tmp_path / "replacement.g2lex"
        replacement.replace(path)
        with open_sources("en-us", (FileLexiconSource(path),)) as second:
            assert second.get_hit("word").value == "second"
            assert second.get_hit("word").sha256 != original_hash
            assert first.get_hit("word").value == "first"
            assert resource_cache_info().currsize == 2
    finally:
        first.close()


def test_invalid_missing_and_incompatible_files_fail_actionably(tmp_path: Path) -> None:
    missing = tmp_path / "missing.g2lex"
    with pytest.raises(FileNotFoundError, match="does not exist"):
        open_sources("en-us", (FileLexiconSource(missing),))

    invalid = tmp_path / "invalid.g2lex"
    invalid.write_bytes(b"not a G2Lex")
    with pytest.raises(ValueError, match="Invalid G2Lex file"):
        open_sources("en-us", (FileLexiconSource(invalid),))

    wrong_language = _write_g2lex(
        tmp_path, "wrong-language", {"hello": "hɛˈloʊ"}, language="de-de"
    )
    with pytest.raises(ValueError, match="language metadata conflicts"):
        open_sources("en-us", (FileLexiconSource(wrong_language),))


def test_duplicate_files_and_unsupported_english_encoding_fail(tmp_path: Path) -> None:
    path = _write_g2lex(tmp_path, "duplicate", {"hello": "hɛˈloʊ"})
    with pytest.raises(ValueError, match="duplicate G2Lex file source"):
        open_sources("en-us", (FileLexiconSource(path), FileLexiconSource(path)))

    unsupported = _write_g2lex(
        tmp_path, "unsupported", {"hello": "hɛˈloʊ"}, encoding="x-unknown"
    )
    lexicon = Lexicon(lexicons=(), g2lex_files=(FileLexiconSource(unsupported),))
    try:
        with pytest.raises(ValueError, match="Unsupported English phoneme encoding"):
            lexicon.lookup("hello")
    finally:
        lexicon.close()
