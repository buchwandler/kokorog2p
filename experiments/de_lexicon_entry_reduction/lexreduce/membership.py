"""Minimal deterministic acyclic finite-state membership automaton."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _BuildNode:
    terminal: bool = False
    edges: dict[str, _BuildNode] | None = None

    def __post_init__(self) -> None:
        if self.edges is None:
            self.edges = {}


@dataclass(frozen=True, slots=True)
class MembershipIndex:
    """Compact immutable membership automaton using tuple arrays."""

    terminal_states: tuple[bool, ...]
    edges: tuple[tuple[tuple[str, int], ...], ...]
    root: int = 0

    @classmethod
    def from_words(cls, words: list[str] | tuple[str, ...]) -> MembershipIndex:
        root = _BuildNode()
        for word in sorted(words):
            node = root
            for character in word:
                node = node.edges.setdefault(character, _BuildNode())
            node.terminal = True

        interned: dict[tuple[bool, tuple[tuple[str, int], ...]], int] = {}
        terminals: list[bool] = []
        edges: list[tuple[tuple[str, int], ...]] = []

        def intern(node: _BuildNode) -> int:
            children = tuple(
                (character, intern(child))
                for character, child in sorted(node.edges.items())
            )
            signature = (node.terminal, children)
            existing = interned.get(signature)
            if existing is not None:
                return existing
            index = len(terminals)
            interned[signature] = index
            terminals.append(node.terminal)
            edges.append(children)
            return index

        root_id = intern(root)
        if root_id != 0:
            order = _reachable_order(root_id, edges)
            remap = {old: new for new, old in enumerate(order)}
            terminals = [terminals[index] for index in order]
            edges = [
                tuple((character, remap[target]) for character, target in edges[index])
                for index in order
            ]
            root_id = remap[root_id]
        return cls(tuple(terminals), tuple(edges), root_id)

    @property
    def state_count(self) -> int:
        return len(self.terminal_states)

    @property
    def edge_count(self) -> int:
        return sum(len(values) for values in self.edges)

    def contains(self, word: str) -> bool:
        state = self.root
        for character in word:
            next_state = None
            for edge_character, target in self.edges[state]:
                if edge_character == character:
                    next_state = target
                    break
            if next_state is None:
                return False
            state = next_state
        return self.terminal_states[state]

    def iter_words(self) -> tuple[str, ...]:
        """Offline audit helper. Runtime lookup does not need enumeration."""

        words: list[str] = []

        def visit(state: int, prefix: str) -> None:
            if self.terminal_states[state]:
                words.append(prefix)
            for character, target in self.edges[state]:
                visit(target, prefix + character)

        visit(self.root, "")
        return tuple(words)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "root": self.root,
            "terminal_states": list(self.terminal_states),
            "edges": [
                [[character, target] for character, target in state_edges]
                for state_edges in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> MembershipIndex:
        if int(value.get("version", 1)) != 1:
            raise ValueError(
                f"unsupported membership version: {value.get('version')!r}"
            )
        edges = tuple(
            tuple((str(character), int(target)) for character, target in state_edges)
            for state_edges in value["edges"]
        )
        terminals = tuple(bool(item) for item in value["terminal_states"])
        if len(edges) != len(terminals):
            raise ValueError("membership state arrays have different lengths")
        return cls(terminals, edges, int(value.get("root", 0)))

    def serialize(self) -> bytes:
        return (
            json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> MembershipIndex:
        return cls.from_dict(json.loads(data.decode("utf-8")))

    @property
    def serialized_bytes(self) -> int:
        return len(self.serialize())


def _reachable_order(root: int, edges: list[tuple[tuple[str, int], ...]]) -> list[int]:
    order: list[int] = []
    seen: set[int] = set()

    def visit(state: int) -> None:
        if state in seen:
            return
        seen.add(state)
        order.append(state)
        for _, target in edges[state]:
            visit(target)

    visit(root)
    return order
