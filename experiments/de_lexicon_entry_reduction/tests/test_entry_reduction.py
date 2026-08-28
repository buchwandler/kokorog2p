from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo
from experiments.de_lexicon_entry_reduction.lexreduce import (
    ImplicitComposer,
    LiteralLexicon,
    LiteralPrefixIndex,
    MembershipIndex,
    audit_runtime_representation,
    best_segmentation,
    build_implicit_lexicon,
    default_rules,
    german_affix_table,
    german_linker_table,
    optimize_basis,
)
from experiments.de_lexicon_entry_reduction.lexreduce.boundary_rules import (
    BoundaryStressClassRule,
    FinalComponentStressDemotionRule,
)
from experiments.de_lexicon_entry_reduction.lexreduce.composer import SearchLimitError
from experiments.de_lexicon_entry_reduction.lexreduce.reports import summary_dict
from experiments.de_lexicon_entry_reduction.lexreduce.selector import (
    Candidate,
    RuleSelector,
    SelectorPredicate,
    extract_features,
    train_selector,
)
from experiments.de_lexicon_entry_reduction.lexreduce.serializer import (
    asset_dict,
    load_asset,
    save_asset,
    serialize,
)
from experiments.de_lexicon_entry_reduction.verify import (
    adversarial_misses,
    verify_candidate,
)


def make_source(*pairs: tuple[str, str]) -> ParsedLexicon:
    return ParsedLexicon.from_pairs(SourceInfo("toy"), pairs)


def test_motivating_sum_rule_and_unknown_recombination() -> None:
    source = make_source(("1", "a"), ("2", "b"), ("12", "ab"))
    result = build_implicit_lexicon(source)
    candidate = result.asset

    assert result.metrics.baseline_word_count == 3
    assert result.metrics.literal_word_count == 2
    assert result.metrics.generated_word_count == 1
    assert candidate.per_generated_word_recipe_count == 0
    assert candidate.lookup_all("12") == ("ab",)
    assert candidate.is_known("12")
    assert candidate.lookup_all("21") == ()
    assert not candidate.is_known("21")
    assert "12" not in candidate.literals
    assert not hasattr(candidate, "derived")


def test_runtime_composer_has_no_oracle_and_keeps_ambiguous_word_literal() -> None:
    source = make_source(
        ("A", "a"),
        ("C", "c"),
        ("AB", "x"),
        ("BC", "bc"),
        ("ABC", "abc"),
    )
    result = build_implicit_lexicon(source)
    assert "ABC" in result.asset.literals
    assert result.asset.lookup_all("ABC") == ("abc",)
    assert result.asset.composer.derive(
        "ABC",
        literals=result.asset.literals,
        prefix_index=result.asset.literal_index,
    ) == ("xc",)


def test_variant_order_is_exact() -> None:
    source = make_source(
        ("A", "a1"), ("A", "a2"), ("B", "b1"), ("B", "b2"), ("AB", "a1b1")
    )
    result = build_implicit_lexicon(source)
    assert result.asset.lookup_all("AB") == ("a1b1",)
    assert "AB" in result.asset.literals

    literals = LiteralLexicon({"A": ("a1", "a2"), "B": ("b1", "b2")})
    composer = ImplicitComposer()
    assert composer.derive(
        "AB", literals=literals, prefix_index=LiteralPrefixIndex.from_literals(literals)
    ) == (
        "a1b1",
        "a1b2",
        "a2b1",
        "a2b2",
    )


def test_stress_rule_is_shared_and_oracle_free() -> None:
    source = make_source(
        ("Haus", "hˈaʊs"),
        ("tür", "tˈyːɐ"),
        ("Haustür", "hˈaʊstˌyːɐ"),
    )
    concat = build_implicit_lexicon(source, rules=default_rules())
    compound = build_implicit_lexicon(source, rules=default_rules(True))
    assert "Haustür" in concat.asset.literals
    assert "Haustür" not in compound.asset.literals
    assert compound.asset.lookup_all("Haustür") == ("hˈaʊstˌyːɐ",)
    assert compound.asset.composer.rules.rules[0].rule_id == "C1"


def test_deterministic_segmentation_and_state_limit() -> None:
    literals = LiteralLexicon({"a": ("a",), "ab": ("ab",), "bc": ("bc",), "c": ("c",)})
    index = LiteralPrefixIndex.from_literals(literals)
    assert best_segmentation("abc", index, literals, max_components=3) == ("ab", "c")
    with pytest.raises(SearchLimitError):
        best_segmentation("abc", index, literals, max_components=4, max_states=1)


def test_membership_exact_and_deterministic() -> None:
    words = ("Haus", "Haustür", "Tür")
    membership = MembershipIndex.from_words(words)
    assert membership.iter_words() == tuple(sorted(words))
    assert all(membership.contains(word) for word in words)
    assert not any(membership.contains(word) for word in adversarial_misses(words))
    assert membership.serialize() == MembershipIndex.from_words(words).serialize()


def test_serialization_round_trip_has_no_derived_table(tmp_path: Path) -> None:
    source = make_source(("1", "a"), ("2", "b"), ("12", "ab"))
    result = build_implicit_lexicon(source)
    assert "derived" not in asset_dict(result.asset)
    save_asset(tmp_path, result.asset)
    reloaded = load_asset(tmp_path)
    assert reloaded.lookup_all("12") == ("ab",)
    assert reloaded.is_known("12")
    assert not reloaded.is_known("21")
    assert "derived" not in json.loads((tmp_path / "manifest.json").read_text())
    assert not (tmp_path / "derived.json").exists()
    assert serialize(result.asset)


def test_deterministic_build_and_runtime_audit() -> None:
    source = make_source(("1", "a"), ("2", "b"), ("12", "ab"))
    first = build_implicit_lexicon(source)
    second = build_implicit_lexicon(source)
    assert first.metrics == second.metrics
    assert tuple(first.asset.literals) == tuple(second.asset.literals)
    assert serialize(first.asset) == serialize(second.asset)
    audit = audit_runtime_representation(first.asset)
    assert audit["per_generated_word_recipe_count"] == 0


def test_optimizer_and_verification_metrics() -> None:
    source = make_source(("1", "a"), ("2", "b"), ("12", "ab"))
    optimized = optimize_basis(source, max_passes=2)
    verification = verify_candidate(optimized.build.asset, source, miss_words=("21",))
    summary = summary_dict(optimized.build, verification=verification)
    assert optimized.build.metrics.literal_word_count == 2
    assert summary["entry_reduction_count"] == 1
    assert verification["words_checked"] == 3
    assert verification["lossless"]


def test_selector_chooses_candidates_without_expected_ipa() -> None:
    variants = (("hˈaʊs",), ("tˈyːɐ",))
    features = extract_features("Haustür", ("Haus", "tür"), variants)
    selector = RuleSelector(
        (SelectorPredicate("component_count", "2", "C0", 100),), "C1"
    )
    selected = selector.select(
        features,
        (Candidate("C1", ("hˈaʊstˌyːɐ",)), Candidate("C0", ("hˈaʊstˈyːɐ",))),
    )
    assert selected is not None and selected.rule_id == "C0"
    assert "expected" not in selector.as_dict()
    assert selector.serialized_bytes <= selector.max_serialized_bytes


def test_selector_round_trip_and_training_are_deterministic() -> None:
    variants = (("aˈ",), ("bˈ",))
    features = extract_features("ab", ("a", "b"), variants)
    rows = ({"features": features, "target_rule": "C0"} for _ in range(100))
    first = train_selector(rows, min_support=10)
    second = train_selector(
        ({"features": features, "target_rule": "C0"} for _ in range(100)),
        min_support=10,
    )
    assert first.as_dict() == second.as_dict()
    assert RuleSelector.from_dict(first.as_dict()) == first
    assert all("ab" not in str(value) for value in first.as_dict().values())


def test_boundary_rules_are_shared_and_deterministic() -> None:
    variants = (("hˈaʊs",), ("tˈyːɐ",))
    final = FinalComponentStressDemotionRule()
    assert final.applies("Haustür", ("Haus", "tür"), variants)
    assert final.compose("Haustür", ("Haus", "tür"), variants) == ("hˈaʊstˌyːɐ",)
    class_rule = BoundaryStressClassRule()
    assert class_rule.applies("Haustür", ("Haus", "tür"), variants)


def test_linker_is_shared_and_membership_still_gates(tmp_path: Path) -> None:
    source = make_source(("Arbeit", "a"), ("zeit", "z"), ("Arbeitszeit", "az"))
    result = build_implicit_lexicon(source, linkers=german_linker_table())
    assert result.metrics.generated_word_count == 1
    assert result.asset.lookup_all("Arbeitszeit") == ("az",)
    assert not result.asset.is_known("Arbeitszeitx")
    assert result.asset.composer.linkers is not None
    save_asset(tmp_path, result.asset)
    assert load_asset(tmp_path).lookup_all("Arbeitszeit") == ("az",)
    assert not hasattr(result.asset, "derived")


def test_recursive_generated_constituents_are_ephemeral(tmp_path: Path) -> None:
    source = make_source(
        ("A", "a"), ("B", "b"), ("C", "c"), ("AB", "ab"), ("ABC", "abc")
    )
    result = build_implicit_lexicon(source, recursive_components=True, max_components=2)
    assert result.metrics.literal_word_count == 3
    assert result.metrics.generated_word_count == 2
    assert result.asset.lookup_all("AB") == ("ab",)
    assert result.asset.lookup_all("ABC") == ("abc",)
    save_asset(tmp_path, result.asset)
    assert load_asset(tmp_path).lookup_all("ABC") == ("abc",)
    assert not hasattr(result.asset, "derived")
    assert result.asset.per_generated_word_recipe_count == 0


def test_shared_affix_grammar_is_bounded() -> None:
    source = make_source(("glück", "g"), ("unglück", "g"))
    result = build_implicit_lexicon(source, affixes=german_affix_table())
    assert result.asset.lookup_all("unglück") == ("g",)
    assert result.metrics.generated_word_count == 1
    assert not hasattr(result.asset, "derived")


@pytest.mark.slow
def test_full_builtin_opt_in() -> None:
    data_path = Path("lexicons/sources/de/de_gold.json")
    if not data_path.is_file():
        pytest.skip("documented built-in data asset is unavailable")
    from experiments.de_lexicon_entry_reduction.source import load_canonical_source

    source = load_canonical_source("builtin")
    result = build_implicit_lexicon(source, max_components=2)
    assert result.metrics.baseline_word_count == 738_427
    assert result.metrics.per_generated_word_recipe_count == 0
