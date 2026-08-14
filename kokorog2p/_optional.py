"""Helpers for loading optional runtime dependencies without side effects."""

from typing import Any

_TRANSFORMER_COMPONENTS = {"tok2vec", "transformer"}
_TAGGING_COMPONENTS = {"tagger", "morphologizer"}


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
        # Load first and inspect the actual pipeline. Transformer models use a
        # ``transformer`` component rather than the ``tok2vec`` name used by
        # classic pipelines, so a fixed enable list is not portable.
        nlp = spacy.load(name)
        if enable is None:
            return nlp

        pipe_names = tuple(getattr(nlp, "pipe_names", ()))
        available = set(pipe_names)
        requested = set(enable)
        missing = requested - available
        if missing & _TRANSFORMER_COMPONENTS and available & _TRANSFORMER_COMPONENTS:
            missing -= _TRANSFORMER_COMPONENTS
        if "tagger" in missing and available & _TAGGING_COMPONENTS:
            missing -= {"tagger"}
        if missing:
            names = ", ".join(sorted(missing))
            components = ", ".join(pipe_names) or "none"
            raise ImportError(
                f"spaCy model {name!r} does not provide required component(s): "
                f"{names}. "
                f"Available components: {components}."
            )

        # Preserve requested components and whichever representation component
        # the selected model actually exposes; disable only unrelated pipes.
        required = requested & available
        if "tagger" in requested:
            required |= available & _TAGGING_COMPONENTS
        if requested & _TRANSFORMER_COMPONENTS:
            required |= available & _TRANSFORMER_COMPONENTS
        unrelated = [pipe for pipe in pipe_names if pipe not in required]
        if unrelated and hasattr(nlp, "disable_pipes"):
            nlp.disable_pipes(*unrelated)
        return nlp
    except (OSError, ImportError) as exc:
        if isinstance(exc, ImportError) and str(exc).startswith("spaCy model"):
            raise
        raise ImportError(
            f"Unable to load installed spaCy model {name!r}. "
            f"Reinstall it explicitly with: python -m spacy download {name}"
        ) from exc
