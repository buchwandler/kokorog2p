"""Offline discovery and selection of optional spaCy language models.

The resolver deliberately has no installation or download path. It uses
installed distribution/module metadata for discovery and only asks spaCy to
load a candidate when automatic selection needs to verify that candidate is
usable.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from importlib import metadata
from importlib.util import find_spec
from typing import Any


class SpacyModelSize(str, Enum):
    """Supported spaCy model quality tiers, ordered from best to smallest."""

    TRF = "trf"
    LG = "lg"
    MD = "md"
    SM = "sm"


_MODEL_SIZES: tuple[SpacyModelSize, ...] = (
    SpacyModelSize.TRF,
    SpacyModelSize.LG,
    SpacyModelSize.MD,
    SpacyModelSize.SM,
)
_MODEL_PREFIXES: Mapping[str, str] = {
    "en": "en_core_web",
    "fr": "fr_core_news",
    "de": "de_core_news",
    "es": "es_core_news",
    "it": "it_core_news",
    "pt": "pt_core_news",
}
_LANGUAGE_ALIASES: Mapping[str, str] = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "en-us": "en",
    "en-gb": "en",
    "en-uk": "en",
    "fr": "fr",
    "fra": "fr",
    "french": "fr",
    "fr-fr": "fr",
    "de": "de",
    "deu": "de",
    "german": "de",
    "de-de": "de",
    "de-at": "de",
    "de-ch": "de",
    "es": "es",
    "spa": "es",
    "spanish": "es",
    "es-es": "es",
    "it": "it",
    "ita": "it",
    "italian": "it",
    "it-it": "it",
    "pt": "pt",
    "por": "pt",
    "portuguese": "pt",
    "pt-br": "pt",
    "pt-pt": "pt",
}


def normalize_spacy_language(language: str) -> str:
    """Normalize a supported language code to its spaCy model family."""

    normalized = language.lower().replace("_", "-")
    try:
        return _LANGUAGE_ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(_MODEL_PREFIXES))
        raise ValueError(
            f"Unsupported spaCy model language {language!r}. "
            f"Supported families: {supported}."
        ) from exc


def _coerce_size(value: SpacyModelSize | str) -> SpacyModelSize:
    try:
        return (
            value
            if isinstance(value, SpacyModelSize)
            else SpacyModelSize(value.lower())
        )
    except (AttributeError, ValueError) as exc:
        supported = ", ".join(size.value for size in _MODEL_SIZES)
        raise ValueError(
            f"Unsupported spaCy model size {value!r}; use one of {supported}."
        ) from exc


def _model_name(language: str, size: SpacyModelSize) -> str:
    return f"{_MODEL_PREFIXES[language]}_{size.value}"


def candidate_spacy_models(language: str) -> tuple[str, ...]:
    """Return compatible candidate package names in quality order."""

    normalized = normalize_spacy_language(language)
    return tuple(_model_name(normalized, size) for size in _MODEL_SIZES)


def _installed_packages() -> set[str]:
    """Find installed importable model packages without importing spaCy."""

    installed: set[str] = set()
    try:
        package_map = metadata.packages_distributions()
    except Exception:  # pragma: no cover - broken metadata should not crash discovery
        package_map = {}
    known = {
        _model_name(language, size)
        for language in _MODEL_PREFIXES
        for size in _MODEL_SIZES
    }
    installed.update(name for name in package_map if name in known)
    for language in _MODEL_PREFIXES:
        for size in _MODEL_SIZES:
            package_name = _model_name(language, size)
            try:
                if find_spec(package_name) is not None:
                    installed.add(package_name)
            except (ImportError, ModuleNotFoundError, ValueError):
                pass
    return installed


def is_spacy_model_installed(package_name: str) -> bool:
    """Return whether a concrete model package appears to be installed."""

    return package_name in _installed_packages()


@dataclass(frozen=True)
class SpacyModelResolution:
    """Structured result of a concrete spaCy model selection."""

    language: str
    package: str
    size: SpacyModelSize
    automatic: bool
    candidates: tuple[str, ...]
    checked: tuple[str, ...]
    errors: tuple[tuple[str, str], ...]
    spacy_available: bool

    @property
    def model(self) -> str:
        """Alias for callers that refer to the selected package as ``model``."""

        return self.package

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Return JSON-friendly resolution diagnostics."""

        return {
            "language": self.language,
            "package": self.package,
            "size": self.size.value,
            "automatic": self.automatic,
            "candidates": list(self.candidates),
            "checked": list(self.checked),
            "errors": dict(self.errors),
            "spacy_available": self.spacy_available,
        }


class SpacyModelResolutionError(ImportError):
    """Raised when a requested or automatically selected model cannot be used."""

    def __init__(
        self,
        message: str,
        *,
        language: str,
        automatic: bool,
        candidates: tuple[str, ...],
        errors: tuple[tuple[str, str], ...],
        spacy_available: bool,
    ) -> None:
        super().__init__(message)
        self.language = language
        self.automatic = automatic
        self.candidates = candidates
        self.errors = errors
        self.spacy_available = spacy_available


def _spacy_available() -> bool:
    try:
        return find_spec("spacy") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _default_probe(package_name: str) -> None:
    import spacy

    nlp = spacy.load(package_name)
    pipe_names = set(getattr(nlp, "pipe_names", ()))
    tagging_components = {"tagger", "morphologizer"}
    if not pipe_names & tagging_components:
        available = ", ".join(sorted(pipe_names)) or "none"
        raise ImportError(
            f"spaCy model {package_name!r} does not provide the required tagger or "
            f"morphologizer "
            f"component. Available components: {available}."
        )
    if not pipe_names & {"tok2vec", "transformer"}:
        available = ", ".join(sorted(pipe_names)) or "none"
        raise ImportError(
            f"spaCy model {package_name!r} does not provide a required "
            f"'tok2vec' or 'transformer' component. Available components: {available}."
        )


def _explicit_error(
    package_name: str, language: str, reason: str, *, spacy_available: bool
) -> SpacyModelResolutionError:
    return SpacyModelResolutionError(
        f"Unable to use requested spaCy model {package_name!r} for language "
        f"{language!r}: "
        f"{reason} Install it explicitly with: python -m spacy download {package_name}",
        language=language,
        automatic=False,
        candidates=(package_name,),
        errors=((package_name, reason),),
        spacy_available=spacy_available,
    )


def resolve_spacy_model(
    language: str,
    *,
    spacy_model: str | None = None,
    spacy_model_size: SpacyModelSize | str | None = None,
    probe_loadability: bool = True,
    package_checker: Callable[[str], bool] | None = None,
    loader: Callable[[str], Any] | None = None,
) -> SpacyModelResolution:
    """Resolve a concrete installed spaCy model without downloading anything.

    A concrete ``spacy_model`` wins over ``spacy_model_size``. ``None`` and
    ``"auto"`` select the highest installed candidate that spaCy can load;
    exact size requests are strict and never fall back to another tier.
    """

    normalized = normalize_spacy_language(language)
    candidates = candidate_spacy_models(normalized)
    automatic = spacy_model is None or spacy_model.lower() == "auto"
    spacy_available = _spacy_available()
    checker = package_checker or is_spacy_model_installed

    if not automatic:
        requested = spacy_model
        expected_prefix = f"{_MODEL_PREFIXES[normalized]}_"
        if not requested.startswith(expected_prefix) or requested.rsplit("_", 1)[
            -1
        ] not in {size.value for size in _MODEL_SIZES}:
            raise _explicit_error(
                requested,
                normalized,
                f"it is not a compatible model package for language {normalized!r}",
                spacy_available=spacy_available,
            )
        if not checker(requested):
            raise _explicit_error(
                requested,
                normalized,
                "it is not installed",
                spacy_available=spacy_available,
            )
        size = SpacyModelSize(requested.rsplit("_", 1)[-1])
        return SpacyModelResolution(
            normalized,
            requested,
            size,
            False,
            (requested,),
            (requested,),
            (),
            spacy_available,
        )

    if spacy_model_size is not None:
        size = _coerce_size(spacy_model_size)
        requested = _model_name(normalized, size)
        if not checker(requested):
            raise _explicit_error(
                requested,
                normalized,
                "it is not installed",
                spacy_available=spacy_available,
            )
        return SpacyModelResolution(
            normalized,
            requested,
            size,
            False,
            (requested,),
            (requested,),
            (),
            spacy_available,
        )

    checked: list[str] = []
    errors: list[tuple[str, str]] = []
    probe = loader or _default_probe
    selected: str | None = None
    for package_name in candidates:
        if not checker(package_name):
            errors.append((package_name, "not installed"))
            continue
        checked.append(package_name)
        if probe_loadability:
            try:
                probe(package_name)
            except (
                Exception
            ) as exc:  # spaCy exposes several version-specific exceptions
                errors.append((package_name, f"{type(exc).__name__}: {exc}"))
                continue
        selected = package_name
        break
    if selected is None:
        install_examples = ", ".join(
            f"python -m spacy download {name}" for name in candidates
        )
        detail = "; ".join(f"{name}: {reason}" for name, reason in errors)
        spaCy_note = "spaCy itself is not installed. " if not spacy_available else ""
        raise SpacyModelResolutionError(
            f"No loadable spaCy model found for language {normalized!r}. "
            f"Checked candidate tiers/packages: {', '.join(candidates)}. "
            f"{spaCy_note}Candidate diagnostics: {detail or 'none'}. "
            f"Install an appropriate model explicitly, for example: {install_examples}",
            language=normalized,
            automatic=True,
            candidates=candidates,
            errors=tuple(errors),
            spacy_available=spacy_available,
        )
    selected_size = SpacyModelSize(selected.rsplit("_", 1)[-1])
    return SpacyModelResolution(
        normalized,
        selected,
        selected_size,
        True,
        candidates,
        tuple(checked),
        tuple(errors),
        spacy_available,
    )


__all__ = [
    "SpacyModelResolution",
    "SpacyModelResolutionError",
    "SpacyModelSize",
    "candidate_spacy_models",
    "is_spacy_model_installed",
    "normalize_spacy_language",
    "resolve_spacy_model",
]
