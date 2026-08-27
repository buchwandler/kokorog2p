"""Runtime decoder sharing the compressor's deterministic composition contract."""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import ParsedLexicon, SourceInfo


@dataclass(slots=True)
class CompressedLexicon:
    source: SourceInfo
    atoms: dict[str, tuple[str, ...]]
    exceptions: dict[str, tuple[str, ...]]
    derived: dict[str, tuple[str, ...]]
    metadata: dict[str, object] = field(default_factory=dict)

    def lookup_all(self, word: str) -> tuple[str, ...]:
        if word in self.exceptions:
            return self.exceptions[word]
        if word in self.atoms:
            return self.atoms[word]
        components = self.derived.get(word)
        if components is None:
            return ()
        values = [self.atoms[component] for component in components]
        result = [""]
        for variants in values:
            result = [prefix + value for prefix in result for value in variants]
        return tuple(result)

    def lookup(self, word: str) -> str | None:
        values = self.lookup_all(word)
        return values[0] if values else None

    def is_known(self, word: str) -> bool:
        return word in self.atoms or word in self.exceptions or word in self.derived

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(sorted((*self.atoms, *self.exceptions, *self.derived)))

    def verify_against(self, source: ParsedLexicon) -> tuple[str, ...]:
        failures = []
        for word in source.words:
            actual = self.lookup_all(word)
            expected = source.lookup_all(word)
            if actual != expected:
                failures.append(word)
        return tuple(failures)
