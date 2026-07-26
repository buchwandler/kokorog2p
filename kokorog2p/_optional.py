"""Helpers for loading optional runtime dependencies without side effects."""

from typing import Any


def load_spacy_model(name: str, *, enable: list[str] | None = None) -> Any:
    """Load an installed spaCy model without attempting a network download.

    Raises an actionable ``ImportError`` when either spaCy or the requested
    model is unavailable. Model installation is intentionally an explicit
    operator action so inference remains safe in offline environments.
    """
    try:
        import spacy
    except ImportError as exc:
        raise ImportError(
            "spaCy is required for this tokenizer path. "
            "Install it explicitly with: python -m pip install spacy"
        ) from exc

    if not spacy.util.is_package(name):
        raise ImportError(
            f"spaCy model {name!r} is not installed. "
            f"Install it explicitly with: python -m spacy download {name}"
        )

    try:
        if enable is None:
            return spacy.load(name)
        return spacy.load(name, enable=enable)
    except (OSError, ImportError) as exc:
        raise ImportError(
            f"Unable to load installed spaCy model {name!r}. "
            f"Reinstall it explicitly with: python -m spacy download {name}"
        ) from exc
