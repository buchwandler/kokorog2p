"""Canonical source-semantic data model."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SourceInfo:
    source_id: str
    revision: str | None = None
    sha256: str = ""
    license: str = ""
    provenance_status: str = ""
    parser_version: str = "1"
    view_version: str = "1"
    format: str = ""
    path: str | None = None
    size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class PronunciationRecord:
    ipa: str
    line_number: int | None = None


@dataclass(slots=True)
class ParsedLexicon:
    """A parsed source, preserving ordered and duplicate pronunciation records."""

    source: SourceInfo
    entries: dict[str, tuple[PronunciationRecord, ...]]
    physical_rows: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.entries = dict(self.entries)
        self.physical_rows = (
            sum(len(records) for records in self.entries.values())
            if self.physical_rows is None
            else self.physical_rows
        )

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(self.entries)

    def lookup_all(self, word: str) -> tuple[str, ...]:
        return tuple(record.ipa for record in self.entries.get(word, ()))

    def lookup_records(self, word: str) -> tuple[PronunciationRecord, ...]:
        return self.entries.get(word, ())

    def lookup(self, word: str) -> str | None:
        values = self.lookup_all(word)
        return values[0] if values else None

    def is_known(self, word: str) -> bool:
        return word in self.entries

    def iter_records(self) -> Iterator[tuple[str, PronunciationRecord]]:
        for word, records in self.entries.items():
            for record in records:
                yield word, record

    def runtime_unique(self) -> ParsedLexicon:
        unique_entries: dict[str, tuple[PronunciationRecord, ...]] = {}
        for word, records in self.entries.items():
            seen: set[str] = set()
            unique_entries[word] = tuple(
                record
                for record in records
                if not (record.ipa in seen or seen.add(record.ipa))
            )
        return ParsedLexicon(
            self.source,
            unique_entries,
            sum(len(values) for values in unique_entries.values()),
            {**self.metadata, "view": "runtime_unique"},
        )

    def with_source(self, source: SourceInfo) -> ParsedLexicon:
        return ParsedLexicon(
            source, self.entries, self.physical_rows, dict(self.metadata)
        )

    @classmethod
    def from_pairs(
        cls,
        source: SourceInfo,
        pairs: Iterable[tuple[str, str]],
        *,
        line_numbers: bool = True,
    ) -> ParsedLexicon:
        entries: dict[str, list[PronunciationRecord]] = {}
        count = 0
        for count, (word, ipa) in enumerate(pairs, 1):
            entries.setdefault(word, []).append(
                PronunciationRecord(ipa, count if line_numbers else None)
            )
        return cls(
            source, {word: tuple(records) for word, records in entries.items()}, count
        )
