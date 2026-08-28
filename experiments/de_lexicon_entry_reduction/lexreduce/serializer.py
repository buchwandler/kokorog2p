"""Auditable, source-independent runtime asset format."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from experiments.de_lexicon_compression.lexlab.model import SourceInfo

from ..model import ImplicitLexicon, LiteralLexicon
from .affixes import AffixTable
from .composer import ImplicitComposer
from .linkers import LinkerTable
from .membership import MembershipIndex
from .prefix_index import LiteralPrefixIndex
from .rules import RuleSet
from .segmentation import SegmentationScorer

ASSET_SCHEMA = 1


def _source_dict(source: SourceInfo) -> dict[str, Any]:
    value = asdict(source)
    value["path"] = Path(source.path).name if source.path else None
    return value


def manifest_dict(asset: ImplicitLexicon) -> dict[str, Any]:
    metrics = asset.metrics()
    return {
        "schema": ASSET_SCHEMA,
        "kind": "implicit-entry-reduction",
        "source": _source_dict(asset.source),
        "source_id": asset.source.source_id,
        "source_sha256": asset.source.sha256,
        "baseline_word_count": metrics.baseline_word_count,
        "literal_word_count": metrics.literal_word_count,
        "generated_word_count": metrics.generated_word_count,
        "per_generated_word_recipe_count": asset.per_generated_word_recipe_count,
        "target_literal_word_count": int(
            asset.metadata.get("target_literal_word_count", 400_000)
        ),
        "target_met": metrics.literal_word_count
        <= int(asset.metadata.get("target_literal_word_count", 400_000)),
        "composer_version": asset.metadata.get("composer_version", "1"),
        "membership_version": asset.metadata.get("membership_version", 1),
        "rule_version": asset.metadata.get("rule_version", "1"),
    }


def asset_dict(asset: ImplicitLexicon) -> dict[str, Any]:
    """Return the single logical representation, with no derived table."""

    return {
        "manifest": manifest_dict(asset),
        "metadata": dict(asset.metadata),
        "literals": {word: list(asset.literals[word]) for word in asset.literals},
        "literal_index": asset.literal_index.as_dict(),
        "membership": asset.membership.as_dict(),
        "rules": asset.composer.rules.as_dict(),
        "composer": {
            "max_components": asset.composer.max_components,
            "max_states": asset.composer.max_states,
            "two_part_fast_path": asset.composer.two_part_fast_path,
            "linkers": asset.composer.linkers.as_dict()
            if asset.composer.linkers
            else None,
            "recursive_components": asset.composer.recursive_components,
            "max_recursive_depth": asset.composer.max_recursive_depth,
            "segmentation_scorer": asset.composer.segmentation_scorer.as_dict()
            if asset.composer.segmentation_scorer
            else None,
            "affixes": asset.composer.affixes.as_dict()
            if asset.composer.affixes
            else None,
        },
    }


def serialize(asset: ImplicitLexicon) -> bytes:
    return (
        json.dumps(
            asset_dict(asset), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        + "\n"
    ).encode()


def save_asset(directory: Path, asset: ImplicitLexicon) -> dict[str, Any]:
    """Write separate auditable files and return the manifest."""

    directory.mkdir(parents=True, exist_ok=True)
    manifest = manifest_dict(asset)
    _write_json(directory / "manifest.json", manifest)
    _write_json(
        directory / "literals.json",
        {word: list(asset.literals[word]) for word in asset.literals},
    )
    _write_json(directory / "literal-index.json", asset.literal_index.as_dict())
    (directory / "membership.dafsa").write_bytes(asset.membership.serialize())
    _write_json(directory / "rules.json", asset.composer.rules.as_dict())
    _write_json(
        directory / "composer.json",
        {
            "max_components": asset.composer.max_components,
            "max_states": asset.composer.max_states,
            "two_part_fast_path": asset.composer.two_part_fast_path,
            "linkers": asset.composer.linkers.as_dict()
            if asset.composer.linkers
            else None,
            "recursive_components": asset.composer.recursive_components,
            "max_recursive_depth": asset.composer.max_recursive_depth,
            "segmentation_scorer": asset.composer.segmentation_scorer.as_dict()
            if asset.composer.segmentation_scorer
            else None,
            "affixes": asset.composer.affixes.as_dict()
            if asset.composer.affixes
            else None,
            "metadata": asset.metadata,
        },
    )
    return manifest


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def load_asset(directory: Path) -> ImplicitLexicon:
    """Load only runtime files. The canonical source is never opened."""

    manifest = _read_json(directory / "manifest.json")
    if (
        manifest.get("schema") != ASSET_SCHEMA
        or manifest.get("kind") != "implicit-entry-reduction"
    ):
        raise ValueError("unsupported implicit-entry-reduction asset")
    source = SourceInfo(**manifest["source"])
    literals = LiteralLexicon(_read_json(directory / "literals.json"))
    index = LiteralPrefixIndex.from_dict(_read_json(directory / "literal-index.json"))
    membership = MembershipIndex.deserialize(
        (directory / "membership.dafsa").read_bytes()
    )
    rules = RuleSet.from_dict(_read_json(directory / "rules.json"))
    composer_config = _read_json(directory / "composer.json")
    composer = ImplicitComposer(
        int(composer_config.get("max_components", 4)),
        int(composer_config.get("max_states", 100_000)),
        rules,
        bool(composer_config.get("two_part_fast_path", True)),
        LinkerTable.from_dict(composer_config["linkers"])
        if composer_config.get("linkers")
        else None,
        bool(composer_config.get("recursive_components", False)),
        int(composer_config.get("max_recursive_depth", 4)),
        SegmentationScorer.from_dict(composer_config["segmentation_scorer"])
        if composer_config.get("segmentation_scorer")
        else None,
        AffixTable.from_dict(composer_config["affixes"])
        if composer_config.get("affixes")
        else None,
    )
    metadata = dict(composer_config.get("metadata", {}))
    metadata.setdefault("baseline_word_count", int(manifest["baseline_word_count"]))
    metadata.setdefault("per_generated_word_recipe_count", 0)
    return ImplicitLexicon(source, literals, index, membership, composer, metadata)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_asset_bytes(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.iterdir() if path.is_file())
