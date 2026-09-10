"""Named candidate and pinned reference profile registries."""

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


def revisions_path() -> Path:
    return Path(__file__).with_name("revisions.json")


def load_revisions() -> dict[str, object]:
    return json.loads(revisions_path().read_text(encoding="utf-8"))
