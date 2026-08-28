"""Shared data model for the entry-reduction experiment."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from experiments.de_lexicon_compression.lexlab.model import SourceInfo

PronunciationTuple = tuple[str, ...]


class LiteralLexicon(Mapping[str, PronunciationTuple]):
    """Read-only resident pronunciation table for literal words."""

    def __init__(self, values: Mapping[str, Iterable[str]] = ()) -> None:
        self._values = {
            word: tuple(pronunciations)
            for word, pronunciations in sorted(dict(values).items())
        }

    def __getitem__(self, word: str) -> PronunciationTuple:
        return self._values[word]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def get(self, word: str, default: Any = None) -> PronunciationTuple | Any:
        return self._values.get(word, default)

    @property
    def words(self) -> tuple[str, ...]:
        return tuple(self._values)


@dataclass(frozen=True, slots=True)
class CandidateMetrics:
    baseline_word_count: int
    literal_word_count: int
    generated_word_count: int
    per_generated_word_recipe_count: int = 0

    @property
    def entry_reduction_count(self) -> int:
        return self.generated_word_count

    @property
    def entry_reduction_rate(self) -> float:
        return (
            self.generated_word_count / self.baseline_word_count
            if self.baseline_word_count
            else 0.0
        )


@dataclass(slots=True)
class ImplicitLexicon:
    """Reloadable runtime candidate with no generated-word table."""

    source: SourceInfo
    literals: LiteralLexicon
    literal_index: Any
    membership: Any
    composer: Any
    metadata: dict[str, object] = field(default_factory=dict)

    def lookup_all(self, word: str) -> PronunciationTuple:
        literal = self.literals.get(word)
        if literal is not None:
            return literal
        if not self.membership.contains(word):
            return ()
        resolver = None
        context = None
        if self.composer.recursive_components:
            from .lexreduce.resolver import ComponentResolver, ResolveContext

            context = ResolveContext()
            resolver = ComponentResolver(
                self.membership,
                self.composer,
                self.literals,
                self.literal_index,
                max_depth=self.composer.max_recursive_depth,
                max_states=self.composer.max_states,
            )
        generated = self.composer.derive(
            word,
            literals=self.literals,
            prefix_index=self.literal_index,
            resolver=resolver,
            context=context,
        )
        if generated is None:
            raise RuntimeError(
                f"known non-literal word could not be regenerated: {word!r}"
            )
        return generated

    def lookup(self, word: str) -> str | None:
        values = self.lookup_all(word)
        return values[0] if values else None

    def is_known(self, word: str) -> bool:
        return self.membership.contains(word)

    @property
    def per_generated_word_recipe_count(self) -> int:
        return int(self.metadata.get("per_generated_word_recipe_count", 0))

    @property
    def literal_word_count(self) -> int:
        return len(self.literals)

    def metrics(self) -> CandidateMetrics:
        baseline_count = int(self.metadata["baseline_word_count"])
        return CandidateMetrics(
            baseline_count,
            len(self.literals),
            baseline_count - len(self.literals),
            self.per_generated_word_recipe_count,
        )
