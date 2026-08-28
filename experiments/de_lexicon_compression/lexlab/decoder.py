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

    def verify_report(
        self, source: ParsedLexicon, *, sample_limit: int = 100
    ) -> dict[str, object]:
        """Compare complete lookup semantics and classify every mismatch."""
        source_words = set(source.words)
        asset_words = set(self.words)
        missing = sorted(source_words - asset_words)
        extra = sorted(asset_words - source_words)
        pronunciation_mismatches = 0
        variant_count_mismatches = 0
        variant_order_mismatches = 0
        failures: list[dict[str, object]] = []
        for word in sorted(source_words & asset_words):
            expected = source.lookup_all(word)
            actual = self.lookup_all(word)
            if actual == expected:
                continue
            pronunciation_mismatches += 1
            if len(actual) != len(expected):
                variant_count_mismatches += 1
            elif set(actual) == set(expected) and actual != expected:
                variant_order_mismatches += 1
            if len(failures) < sample_limit:
                failures.append({"word": word, "expected": expected, "actual": actual})
        failures.extend(
            {"word": word, "expected": source.lookup_all(word), "actual": ()}
            for word in missing[: max(0, sample_limit - len(failures))]
        )
        failures.extend(
            {"word": word, "expected": (), "actual": self.lookup_all(word)}
            for word in extra[: max(0, sample_limit - len(failures))]
        )
        return {
            "missing_words": missing,
            "extra_words": extra,
            "pronunciation_mismatches": pronunciation_mismatches,
            "variant_count_mismatches": variant_count_mismatches,
            "variant_order_mismatches": variant_order_mismatches,
            "failures": len(missing) + len(extra) + pronunciation_mismatches,
            "failure_rows": failures,
            "lossless": not (missing or extra or pronunciation_mismatches),
        }

    def verify_against(self, source: ParsedLexicon) -> tuple[str, ...]:
        failures = []
        for word in source.words:
            actual = self.lookup_all(word)
            expected = source.lookup_all(word)
            if actual != expected:
                failures.append(word)
        return tuple(failures)
