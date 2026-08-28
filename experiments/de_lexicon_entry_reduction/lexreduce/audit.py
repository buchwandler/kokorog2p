"""Anti-cheating checks for the runtime representation."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

from ..model import ImplicitLexicon

_FORBIDDEN_NAMES = {
    "derived",
    "generated",
    "generated_words",
    "recipes",
    "recipe_by_word",
    "word_ids",
    "rule_by_word",
    "split_by_word",
    "components_by_word",
    "selector_by_word",
    "repair_by_word",
    "linker_by_word",
    "generated_ids",
}


def _audit_mapping(value: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = str(key).lower()
            if key_name in _FORBIDDEN_NAMES:
                findings.append(f"{path}.{key}")
            findings.extend(_audit_mapping(child, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            findings.extend(_audit_mapping(child, f"{path}[{index}]"))
    return findings


def audit_runtime_representation(candidate: ImplicitLexicon) -> dict[str, Any]:
    """Reject obvious per-generated-word structures and return audit counts."""

    field_names = {field.name for field in fields(candidate)}
    forbidden_fields = sorted(field_names & _FORBIDDEN_NAMES)
    if forbidden_fields:
        raise AssertionError(f"forbidden runtime fields: {forbidden_fields}")
    metadata_names = set(candidate.metadata)
    forbidden_metadata = sorted(metadata_names & _FORBIDDEN_NAMES)
    if forbidden_metadata:
        raise AssertionError(f"forbidden runtime metadata: {forbidden_metadata}")
    serialized_findings = _audit_mapping(candidate.composer.rules.as_dict(), "rules")
    if serialized_findings:
        raise AssertionError(
            f"forbidden serialized runtime structures: {serialized_findings}"
        )
    selector = candidate.composer.rules.selector
    if (
        selector is not None
        and selector.serialized_bytes > selector.max_serialized_bytes
    ):
        raise AssertionError("selector exceeds declared serialized byte limit")
    if candidate.per_generated_word_recipe_count != 0:
        raise AssertionError("generated words have runtime recipes")
    return {
        "forbidden_fields": [],
        "forbidden_metadata": [],
        "literal_word_count": candidate.literal_word_count,
        "per_generated_word_recipe_count": candidate.per_generated_word_recipe_count,
        "checked": True,
    }
