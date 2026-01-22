"""Base classes for text normalization in the G2P pipeline.

Normalization is the process of converting various text forms to a canonical
representation that the rest of the pipeline can work with consistently.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from kokorog2p.pipeline.models import NormalizationStep


@dataclass
class NormalizationRule:
    """A single normalization rule that can be applied to text.

    Rules can be simple replacements or regex-based transformations.
    """

    name: str  # Rule identifier (e.g., "apostrophe", "quote")
    pattern: str | re.Pattern  # What to match (string or regex)
    replacement: str | Callable[[re.Match], str]  # What to replace with
    description: str = ""  # Human-readable description

    def __post_init__(self):
        """Compile regex patterns if needed."""
        if isinstance(self.pattern, str) and not hasattr(self, "_is_simple"):
            # Check if simple string replacement or regex
            # Heuristic: if pattern has regex metacharacters, compile it
            if (
                any(c in self.pattern for c in r"^$.*+?[]{}()\|")
                or "\\" in self.pattern
            ):
                self.pattern = re.compile(self.pattern)
                self._is_simple = False
            else:
                self._is_simple = True
        else:
            self._is_simple = isinstance(self.pattern, str)

    def apply(
        self, text: str, track_changes: bool = True
    ) -> tuple[str, list[NormalizationStep]]:
        """Apply this rule to text and optionally track changes.

        Args:
            text: Text to normalize
            track_changes: Whether to track individual changes

        Returns:
            Tuple of (normalized_text, list of NormalizationStep)
        """
        if not text:
            return text, []

        steps: list[NormalizationStep] = []

        if self._is_simple:
            # Simple string replacement
            pattern_str = str(self.pattern)
            if track_changes and pattern_str in text:
                # Track each occurrence
                pos = 0
                result_parts: list[str] = []
                for part in text.split(pattern_str):
                    if result_parts:  # Not the first part
                        repl_str = (
                            str(self.replacement)
                            if not callable(self.replacement)
                            else ""
                        )
                        steps.append(
                            NormalizationStep(
                                rule_name=self.name,
                                position=pos,
                                original=pattern_str,
                                normalized=repl_str,
                                context=self.description,
                            )
                        )
                        result_parts.append(repl_str)
                        pos += len(repl_str)
                    result_parts.append(part)
                    pos += len(part)
                result = "".join(result_parts)
            else:
                result = text.replace(pattern_str, str(self.replacement))
        else:
            # Regex replacement
            pattern = (
                self.pattern
                if isinstance(self.pattern, re.Pattern)
                else re.compile(self.pattern)
            )

            if track_changes:
                # Track each match
                matches = list(pattern.finditer(text))
                if matches:
                    result_parts = []
                    last_end = 0

                    for match in matches:
                        # Add text before match
                        result_parts.append(text[last_end : match.start()])

                        # Apply replacement
                        if callable(self.replacement):
                            repl = self.replacement(match)
                        else:
                            repl = match.expand(self.replacement)

                        result_parts.append(repl)

                        # Track the change
                        steps.append(
                            NormalizationStep(
                                rule_name=self.name,
                                position=match.start(),
                                original=match.group(),
                                normalized=repl,
                                context=self.description,
                            )
                        )

                        last_end = match.end()

                    # Add remaining text
                    result_parts.append(text[last_end:])
                    result = "".join(result_parts)
                else:
                    result = text
            else:
                # Just do the replacement
                if callable(self.replacement):
                    repl_fn = self.replacement
                    result = pattern.sub(lambda m: repl_fn(m), text)
                else:
                    result = pattern.sub(self.replacement, text)

        return result, steps


class TextNormalizer(ABC):
    """Abstract base class for text normalization.

    Subclasses should define rules and implement the normalize method.
    Language-specific normalizers can override or extend the rule set.
    """

    def __init__(self, track_changes: bool = False):
        """Initialize the normalizer.

        Args:
            track_changes: Whether to track normalization changes for debugging
        """
        self.track_changes = track_changes
        self._rules: list[NormalizationRule] = []
        self._initialize_rules()

    @abstractmethod
    def _initialize_rules(self) -> None:
        """Initialize the normalization rules.

        Subclasses should populate self._rules in the order they should be applied.
        Order matters! For example, apostrophe normalization should happen before
        quote normalization to handle edge cases correctly.
        """
        pass

    def add_rule(self, rule: NormalizationRule) -> None:
        """Add a normalization rule to the pipeline.

        Args:
            rule: Rule to add
        """
        self._rules.append(rule)

    def normalize(self, text: str) -> tuple[str, list[NormalizationStep]]:
        """Normalize text by applying all rules in order.

        Args:
            text: Text to normalize

        Returns:
            Tuple of (normalized_text, list of all normalization steps)
        """
        if not text:
            return text, []

        all_steps: list[NormalizationStep] = []
        result = text

        for rule in self._rules:
            result, steps = rule.apply(result, track_changes=self.track_changes)
            all_steps.extend(steps)

        return result, all_steps

    def _apply_rules(
        self, text: str, rules: list[NormalizationRule] | None = None
    ) -> str:
        """Apply normalization rules without tracking steps.

        Args:
            text: Text to normalize.
            rules: Optional list of rules to apply (defaults to all rules).

        Returns:
            Normalized text.
        """
        if not text:
            return text

        result = text
        for rule in rules or self._rules:
            result, _ = rule.apply(result, track_changes=False)
        return result

    def __call__(self, text: str) -> str:
        """Normalize text (convenience method that discards step tracking).

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        result, _ = self.normalize(text)
        return result
