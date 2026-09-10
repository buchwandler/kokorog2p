"""Named candidate, reference, golden, and suite registries."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .candidate import CANDIDATE_PROFILES
from .providers import HexgradEnglishMisakiProvider, SemidarkGermanMisakiProvider
from .types import CandidateProfile, ReferenceMetadata, ReferenceProvider

REFERENCE_PROFILES: dict[str, ReferenceMetadata] = {
    "hexgrad-en-us-v1": HexgradEnglishMisakiProvider().metadata,
    "hexgrad-en-gb-v1": HexgradEnglishMisakiProvider(british=True).metadata,
    "semidark-de-v1": SemidarkGermanMisakiProvider().metadata,
}

REFERENCE_GOLDENS: dict[str, str] = {
    "hexgrad-en-us-v1": "hexgrad_en_us_v1.json",
    "hexgrad-en-gb-v1": "hexgrad_en_gb_v1.json",
    "semidark-de-v1": "semidark_de_v1.json",
}

REFERENCE_SUITES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "core": (
        ("hexgrad-en-us-v1", "en-us-default", "en-us"),
        ("hexgrad-en-gb-v1", "en-gb-default", "en-gb"),
        ("semidark-de-v1", "de-default", "de"),
    )
}

CANDIDATE_REGISTRY: dict[str, CandidateProfile] = CANDIDATE_PROFILES

_PROVIDER_FACTORIES: dict[str, Callable[[], ReferenceProvider]] = {
    "hexgrad-en-us-v1": HexgradEnglishMisakiProvider,
    "hexgrad-en-gb-v1": lambda: HexgradEnglishMisakiProvider(british=True),
    "semidark-de-v1": SemidarkGermanMisakiProvider,
}


def get_candidate_profile(profile_id: str) -> CandidateProfile:
    try:
        return CANDIDATE_REGISTRY[profile_id]
    except KeyError as exc:
        raise KeyError(f"unknown candidate profile: {profile_id}") from exc


def get_reference_metadata(profile_id: str) -> ReferenceMetadata:
    try:
        return REFERENCE_PROFILES[profile_id]
    except KeyError as exc:
        raise KeyError(f"unknown reference profile: {profile_id}") from exc


def get_reference_provider(profile_id: str) -> ReferenceProvider:
    try:
        return _PROVIDER_FACTORIES[profile_id]()
    except KeyError as exc:
        raise KeyError(f"unknown reference profile: {profile_id}") from exc


def golden_dir() -> Path:
    return Path(__file__).with_name("goldens")


def get_reference_golden_path(profile_id: str) -> Path:
    try:
        filename = REFERENCE_GOLDENS[profile_id]
    except KeyError as exc:
        raise KeyError(f"unknown reference golden: {profile_id}") from exc
    return golden_dir() / filename


def get_reference_suite(suite_id: str) -> tuple[tuple[str, str, str], ...]:
    try:
        return REFERENCE_SUITES[suite_id]
    except KeyError as exc:
        raise KeyError(f"unknown reference suite: {suite_id}") from exc


def revisions_path() -> Path:
    return Path(__file__).with_name("revisions.json")


def load_revisions() -> dict[str, object]:
    return json.loads(revisions_path().read_text(encoding="utf-8"))
