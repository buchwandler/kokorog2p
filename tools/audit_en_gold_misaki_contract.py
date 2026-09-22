#!/usr/bin/env python3
"""Audit a consolidated English gold asset against the frontend contract."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from kokorog2p.vocab import get_vocab

_REQUIRED_BACKING_ENTRIES = ("am", "to", "used", "versus")
_LETTERS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _finding(stage: str, key: str, message: str) -> dict[str, str]:
    return {"stage": stage, "key": key, "message": message}

def _valid_pronunciation(value: str) -> bool:
    vocabulary = get_vocab()
    return bool(value) and all(char in vocabulary for char in value)

def _selector_items(
    value: object,
) -> tuple[tuple[object, object], ...] | None:
    if isinstance(value, Mapping):
        return tuple(value.items())
    items = getattr(value, "items", None)
    if items is None or callable(items):
        return None
    return tuple(items)



def _audit_value(
    key: str,
    value: object,
    selector: str = "DEFAULT",
) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, str):
        return [_finding("shape", key, f"{selector} value is not a string")]
    if not _valid_pronunciation(value):
        invalid = "".join(sorted({char for char in value if char not in get_vocab()}))
        return [_finding("encoding", key, f"unsupported symbols: {invalid}")]
    return []



def audit_entries(entries: Mapping[str, object]) -> tuple[dict[str, str], ...]:
    """Return stage-aware findings for one consolidated gold mapping."""
    findings: list[dict[str, str]] = []
    for key, value in entries.items():
        if not isinstance(key, str) or not key:
            findings.append(
                _finding(
                    "shape",
                    str(key),
                    "lexical key must be non-empty text",
                )
            )
            continue
        selector_items = _selector_items(value)
        if selector_items is not None:
            selectors = tuple(selector for selector, _ in selector_items)
            if any(not isinstance(selector, str) for selector in selectors):
                findings.append(
                    _finding(
                        "selector",
                        key,
                        "selector names must be strings",
                    )
                )
            if "DEFAULT" not in selectors and len(key) != 1:
                findings.append(
                    _finding(
                        "selector",
                        key,
                        "tagged entry has no usable DEFAULT",
                    )
                )
            for selector, selected in selector_items:
                findings.extend(_audit_value(key, selected, str(selector)))
        elif isinstance(value, tuple):
            if len(value) != 1:
                findings.append(
                    _finding(
                        "shape",
                        key,
                        "tuple pronunciation must contain one value",
                    )
                )
            else:
                findings.extend(_audit_value(key, value[0]))
        else:
            findings.extend(_audit_value(key, value))

    for key in _REQUIRED_BACKING_ENTRIES:
        if key not in entries:
            findings.append(
                _finding(
                    "special_case",
                    key,
                    "required special-case backing entry is missing",
                )
            )
    for key in _LETTERS:
        if key not in entries:
            findings.append(_finding("spelling", key, "letter-name entry is missing"))
    return tuple(findings)


def _load_fixture(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload) if isinstance(payload, Mapping) else None
    if not isinstance(entries, Mapping):
        raise TypeError(
            "fixture must contain an object mapping lexical keys to values"
        )
    return entries


def _load_external(language: str) -> Mapping[str, object]:
    from kokorog2p.en.lexicon import Lexicon

    lexicon = Lexicon(british=language == "en-gb", lexicons=("gold",))
    try:
        entries = lexicon._selected.layer("gold")
        if entries is None:
            raise ValueError("selected gold layer is unavailable")
        return dict(entries)
    finally:
        lexicon.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("en-us", "en-gb"), default="en-us")
    parser.add_argument(
        "--fixture",
        type=Path,
        help="JSON fixture containing an entries mapping",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        entries = (
            _load_fixture(args.fixture)
            if args.fixture
            else _load_external(args.language)
        )
        findings = audit_entries(entries)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"gold contract audit error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"language": args.language, "findings": findings},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
