"""Prefix index for bounded atom enumeration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    words: list[str] = field(default_factory=list)


class PrefixTrie:
    def __init__(self, words=()):
        self.root = _Node()
        for word in sorted(words):
            self.add(word)

    def add(self, word: str) -> None:
        node = self.root
        for char in word:
            node = node.children.setdefault(char, _Node())
        if word not in node.words:
            node.words.append(word)

    def prefixes(self, text: str, start: int = 0) -> tuple[str, ...]:
        node = self.root
        found: list[str] = []
        for char in text[start:]:
            node = node.children.get(char)
            if node is None:
                break
            found.extend(node.words)
        return tuple(found)
