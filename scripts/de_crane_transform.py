#!/usr/bin/env python3
"""Derive the German Crane runtime lexicon from its immutable TSV source."""

from __future__ import annotations

import argparse
import json
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

TRANSFORM_VERSION = "de-crane-lowercase-lexhint-v1"

SELECTOR_ORDER = (
    "DEFAULT",
    "DET",
    "PRON",
    "NOUN",
    "PROPN",
    "VERB",
    "AUX",
    "ADJ",
    "ADV",
    "ADP",
    "NUM",
    "CCONJ",
    "SCONJ",
    "PART",
    "INTJ",
    "X",
)

_LEXHINT_TO_G2LEX_POS = {
    "determiner": "DET",
    "det": "DET",
    "pronoun": "PRON",
    "pron": "PRON",
    "noun": "NOUN",
    "proper noun": "PROPN",
    "proper_noun": "PROPN",
    "propn": "PROPN",
    "verb": "VERB",
    "auxiliary": "AUX",
    "aux": "AUX",
    "adjective": "ADJ",
    "adj": "ADJ",
    "adverb": "ADV",
    "adv": "ADV",
    "adposition": "ADP",
    "preposition": "ADP",
    "postposition": "ADP",
    "numeral": "NUM",
    "num": "NUM",
    "particle": "PART",
    "interjection": "INTJ",
}

REVIEWED_COLLISION_POLICIES: Mapping[str, Mapping[str, object]] = {
    "die": {
        "default": "diː",
        "allowed_pos": ("DET", "PRON"),
        "drop_pos": ("NOUN",),
        "reason": (
            "Sentence-initial German article/pronoun must not resolve "
            "to technical noun Die /daɪ/."
        ),
    },
}


@dataclass(frozen=True, slots=True)
class CraneRow:
    source_spelling: str
    pronunciation: str
    source_index: int


@dataclass(slots=True)
class LowercaseGroup:
    key: str
    rows: list[CraneRow] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ResolvedCraneEntry:
    key: str
    value: object
    report: dict[str, object]


@dataclass(frozen=True, slots=True)
class CraneTransformResult:
    entries: dict[str, object]
    report: dict[str, object]


def normalize_key(word: str) -> str:
    """Normalize a Crane runtime key without aggressive case folding."""
    return unicodedata.normalize("NFC", word).lower()


def comparable_ipa(value: str) -> str:
    """Strip only common IPA delimiters for evidence matching."""
    value = unicodedata.normalize("NFC", value).strip()
    if len(value) >= 2 and value[0] == "/" and value[-1] == "/":
        value = value[1:-1]
    if len(value) >= 2 and value[0] == "[" and value[-1] == "]":
        value = value[1:-1]
    return value


def parse_crane_rows(path: Path) -> list[CraneRow]:
    """Read and normalize the canonical two-column Crane TSV once."""
    rows: list[CraneRow] = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        for source_index, line in enumerate(stream):
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 2:
                raise ValueError(
                    f"{path}:{source_index + 1}: expected spelling and pronunciation"
                )
            spelling = unicodedata.normalize("NFC", fields[0])
            pronunciation = unicodedata.normalize("NFC", fields[1].strip())
            if not spelling:
                raise ValueError(f"{path}:{source_index + 1}: empty spelling")
            if not pronunciation:
                raise ValueError(f"{path}:{source_index + 1}: empty pronunciation")
            rows.append(CraneRow(spelling, pronunciation, source_index))
    return rows


def group_lowercase(rows: Iterable[CraneRow]) -> dict[str, LowercaseGroup]:
    """Group rows by NFC-lowercase key while retaining source order."""
    groups: dict[str, LowercaseGroup] = {}
    for row in rows:
        key = normalize_key(row.source_spelling)
        group = groups.setdefault(key, LowercaseGroup(key))
        pair = (row.source_spelling, row.pronunciation)
        if not any(
            (old.source_spelling, old.pronunciation) == pair for old in group.rows
        ):
            group.rows.append(row)
    return groups


def normalize_pos(value: str) -> str:
    """Map LexHint's universal POS labels to G2Lex selectors."""
    normalized = unicodedata.normalize("NFC", value).strip().lower().replace("-", " ")
    return _LEXHINT_TO_G2LEX_POS.get(normalized, normalized.upper())


def collect_lexhint_candidates(lexicon: Any, word: str) -> tuple[Any, ...]:
    """Query all LexHint case variants for one ambiguous lowercase spelling."""
    return tuple(lexicon.entries(word, all_case_variants=True))


def _entry_pronunciations(entry: Any) -> tuple[str, ...]:
    return tuple(
        unicodedata.normalize("NFC", pronunciation.ipa).strip()
        for pronunciation in getattr(entry, "pronunciations", ())
        if getattr(pronunciation, "ipa", "").strip()
    )


def _lexhint_report(entries: Iterable[Any]) -> list[dict[str, object]]:
    return [
        {
            "word": unicodedata.normalize("NFC", str(entry.word)),
            "pos": str(entry.pos),
            "pronunciations": list(_entry_pronunciations(entry)),
        }
        for entry in entries
    ]


def _ordered_selectors(selectors: Mapping[str, object]) -> dict[str, object]:
    order = {selector: index for index, selector in enumerate(SELECTOR_ORDER)}
    return dict(
        sorted(
            selectors.items(),
            key=lambda item: (order.get(item[0], len(order)), item[0]),
        )
    )


def _plain_value(pronunciations: list[str]) -> str | tuple[str, ...]:
    if len(pronunciations) == 1:
        return pronunciations[0]
    return tuple(pronunciations)


def resolve_group(
    group: LowercaseGroup,
    *,
    lexhint_entries: tuple[Any, ...] = (),
) -> ResolvedCraneEntry:
    """Resolve one lowercase group using Crane pronunciations and LexHint evidence."""
    pronunciations = []
    for row in group.rows:
        if row.pronunciation not in pronunciations:
            pronunciations.append(row.pronunciation)
    exact_lowercase = [
        row.pronunciation for row in group.rows if row.source_spelling == group.key
    ]
    default = exact_lowercase[0] if exact_lowercase else pronunciations[0]
    report: dict[str, object] = {
        "key": group.key,
        "lexhint": _lexhint_report(lexhint_entries),
    }
    # The source report above is deduplicated without changing first-seen order.
    source_report: list[dict[str, object]] = []
    seen_spellings: set[str] = set()
    for row in group.rows:
        if row.source_spelling in seen_spellings:
            continue
        seen_spellings.add(row.source_spelling)
        source_report.append(
            {
                "spelling": row.source_spelling,
                "pronunciations": [
                    item.pronunciation
                    for item in group.rows
                    if item.source_spelling == row.source_spelling
                ],
            }
        )
    report["source"] = source_report

    policy = REVIEWED_COLLISION_POLICIES.get(group.key)
    is_interesting = (
        len(source_report) > 1 or len(pronunciations) > 1 or policy is not None
    )
    if not is_interesting:
        report.update(
            {
                "output": default
                if len(pronunciations) == 1
                else tuple(pronunciations),
                "policy": None,
            }
        )
        return ResolvedCraneEntry(group.key, _plain_value(pronunciations), report)

    selectors: dict[str, object] = {"DEFAULT": default}
    matched: dict[str, str] = {}
    for entry in lexhint_entries:
        selector = normalize_pos(str(entry.pos))
        if selector in matched:
            continue
        for candidate in _entry_pronunciations(entry):
            comparable = comparable_ipa(candidate)
            for crane_pronunciation in pronunciations:
                if comparable == comparable_ipa(crane_pronunciation):
                    matched[selector] = crane_pronunciation
                    break
            if selector in matched:
                break

    for selector, pronunciation in matched.items():
        selectors[selector] = pronunciation

    dropped: list[dict[str, str]] = []
    if policy is not None:
        policy_default = str(policy["default"])
        if policy_default not in pronunciations:
            raise ValueError(
                f"reviewed policy default is absent from Crane group {group.key!r}"
            )
        selectors = {"DEFAULT": policy_default}
        allowed = set(policy["allowed_pos"])
        for selector, pronunciation in matched.items():
            if selector in allowed:
                selectors[selector] = pronunciation
            elif selector in set(policy["drop_pos"]):
                dropped.append({"selector": selector, "pronunciation": pronunciation})
        report["policy"] = "reviewed"
        report["policy_reason"] = str(policy["reason"])
        report["dropped"] = dropped
    else:
        report["policy"] = "lexhint" if matched else "unresolved"

    value = (
        _ordered_selectors(selectors)
        if len(selectors) > 1
        else _plain_value(pronunciations)
    )
    report["output"] = value
    report["matched"] = dict(sorted(matched.items()))
    return ResolvedCraneEntry(group.key, value, report)


def transform_crane(
    source: Path,
    *,
    lexhint_lexicon: Any,
    source_metadata: Mapping[str, object] | None = None,
) -> CraneTransformResult:
    """Transform Crane and query LexHint only for ambiguous groups."""
    rows = parse_crane_rows(source)
    groups = group_lowercase(rows)
    entries: dict[str, object] = {}
    reports: list[dict[str, object]] = []
    collision_count = 0
    multi_pronunciation_count = 0
    lexhint_resolved_count = 0
    reviewed_count = 0
    unresolved_count = 0

    for key, group in groups.items():
        source_spellings = {row.source_spelling for row in group.rows}
        pronunciations = {row.pronunciation for row in group.rows}
        policy = REVIEWED_COLLISION_POLICIES.get(key)
        interesting = (
            len(source_spellings) > 1 or len(pronunciations) > 1 or policy is not None
        )
        candidates = (
            collect_lexhint_candidates(lexhint_lexicon, key) if interesting else ()
        )
        resolved = resolve_group(group, lexhint_entries=candidates)
        entries[key] = resolved.value
        if interesting:
            collision_count += int(len(source_spellings) > 1 or len(pronunciations) > 1)
            multi_pronunciation_count += int(len(pronunciations) > 1)
            lexhint_resolved_count += int(bool(resolved.report.get("matched")))
            reviewed_count += int(resolved.report.get("policy") == "reviewed")
            unresolved_count += int(resolved.report.get("policy") == "unresolved")
            reports.append(resolved.report)

    expected_die = {"DEFAULT": "diː", "DET": "diː", "PRON": "diː"}
    if entries.get("die") != expected_die:
        raise ValueError(f"die transformation contract failed: {entries.get('die')!r}")
    report: dict[str, object] = {
        "transform": TRANSFORM_VERSION,
        "source_rows": len(rows),
        "source_unique_spellings": len({row.source_spelling for row in rows}),
        "runtime_unique_keys": len(entries),
        "collision_group_count": collision_count,
        "multi_pronunciation_collision_count": multi_pronunciation_count,
        "lexhint_resolved_count": lexhint_resolved_count,
        "reviewed_override_count": reviewed_count,
        "unresolved_count": unresolved_count,
        "source_sha256": sha256(source.read_bytes()).hexdigest(),
        "source_metadata": dict(source_metadata or {}),
        "groups": sorted(reports, key=lambda item: str(item["key"])),
    }
    return CraneTransformResult(entries, report)


def _serialize_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _serialize_value(value[key]) for key in _ordered_selectors(value)}
    if isinstance(value, tuple):
        return list(value)
    return value


def serialize_entries(entries: Mapping[str, object]) -> str:
    """Serialize rich Kokoro JSON deterministically."""
    ordered = {key: _serialize_value(entries[key]) for key in sorted(entries)}
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":")) + "\n"


def write_report(report: Mapping[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--word")
    parser.add_argument("--show-collisions", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    from lexhint import Lexicon

    lexicon = Lexicon("de")
    result = transform_crane(args.source, lexhint_lexicon=lexicon)
    if args.report:
        write_report(result.report, args.report)
    if args.word:
        print(
            json.dumps(
                {args.word: result.entries.get(normalize_key(args.word))},
                ensure_ascii=False,
            )
        )
    if args.show_collisions:
        print(
            json.dumps(
                result.report["groups"], ensure_ascii=False, indent=2, sort_keys=True
            )
        )
    if args.strict and int(result.report["unresolved_count"]) > 0:
        raise SystemExit(
            f"unresolved lowercase collisions: {result.report['unresolved_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
