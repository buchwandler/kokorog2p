"""Dependency-light adapters for foreign offset-based text pipelines.

The helpers in this module intentionally use structural protocols instead of
importing phrasplit or SSMD.  Applications can therefore use kokorog2p by
itself while passing compatible objects from either package when installed.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Literal, Protocol

from kokorog2p.types import OverrideSpan, PhonemizeResult


class SegmentLike(Protocol):
    """Structural interface for an offset-preserving text segment."""

    text: str
    char_start: int
    char_end: int


def _validated_offset(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


def _span_values(span: object) -> tuple[int, int, Mapping[str, object]]:
    try:
        start = _validated_offset(span.char_start, "char_start")
        end = _validated_offset(span.char_end, "char_end")
        attrs = span.attrs
    except AttributeError as exc:
        raise TypeError(
            "override spans must provide char_start, char_end, and attrs"
        ) from exc
    if end < start:
        raise ValueError(f"char_end ({end}) must be >= char_start ({start})")
    if not isinstance(attrs, Mapping):
        raise TypeError(f"attrs must be a mapping, got {type(attrs).__name__}")
    return start, end, attrs


def coerce_override_spans(spans: Iterable[object]) -> list[OverrideSpan]:
    """Copy and validate structurally compatible override spans.

    The returned dataclasses own their attribute dictionaries, so adapting
    foreign spans never mutates caller-owned mappings.
    """

    normalized: list[OverrideSpan] = []
    for index, span in enumerate(spans):
        try:
            start, end, attrs = _span_values(span)
            copied_attrs: dict[str, str] = {}
            for key, value in attrs.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise TypeError("attrs keys and values must be strings")
                copied_attrs[key] = value
            normalized.append(OverrideSpan(start, end, copied_attrs))
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"invalid override span at index {index}: {exc}") from exc
    return normalized


def overrides_from_ssmd(
    spans: Iterable[object],
    *,
    xsampa: Literal["reject", "convert"] = "reject",
    text_length: int | None = None,
) -> list[OverrideSpan]:
    """Normalize SSMD-style annotation spans into kokorog2p overrides.

    ``ph`` and IPA-valued ``ipa`` attributes become ``ph``.  ``lang`` and
    ``language`` become ``lang``.  X-SAMPA is rejected unless a converter is
    explicitly supplied by a future implementation; it is never silently
    interpreted as IPA.
    """

    if xsampa not in ("reject", "convert"):
        raise ValueError("xsampa must be 'reject' or 'convert'")
    if text_length is not None:
        _validated_offset(text_length, "text_length")

    normalized: list[OverrideSpan] = []
    for index, span in enumerate(spans):
        start, end, raw_attrs = _span_values(span)
        if text_length is not None and end > text_length:
            raise ValueError(
                f"invalid SSMD span at index {index}: end {end} exceeds text length "
                f"{text_length}"
            )
        attrs: dict[str, str] = {}
        for key, value in raw_attrs.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TypeError(
                    f"invalid SSMD span at index {index}: attrs keys and values must "
                    "be strings"
                )
            normalized_key = key.lower()
            if normalized_key in {"tag", "node", "node_id", "kind"}:
                continue
            if normalized_key in {"sampa", "x-sampa", "xsampa"} or (
                normalized_key == "alphabet"
                and value.lower() in {"sampa", "x-sampa", "xsampa"}
            ):
                if xsampa == "convert":
                    raise ValueError(
                        "X-SAMPA conversion is not available; provide IPA or use "
                        "xsampa='reject'"
                    )
                raise ValueError(
                    "X-SAMPA phoneme attributes are rejected explicitly; provide "
                    "IPA instead"
                )
            if normalized_key == "ph":
                attrs["ph"] = value
            elif normalized_key == "ipa":
                attrs["ph"] = value
            elif normalized_key in {"lang", "language"}:
                attrs["lang"] = value
            elif normalized_key != "alphabet":
                attrs[key] = value
        normalized.append(OverrideSpan(start, end, attrs))
    return normalized


def overrides_for_segment(
    segment_start: int,
    segment_end: int,
    overrides: Iterable[object],
) -> list[OverrideSpan]:
    """Intersect document spans and rebase them to segment-local offsets."""

    start = _validated_offset(segment_start, "segment_start")
    end = _validated_offset(segment_end, "segment_end")
    if end < start:
        raise ValueError(f"segment_end ({end}) must be >= segment_start ({start})")

    rebased: list[OverrideSpan] = []
    for span in coerce_override_spans(overrides):
        local_start = max(span.char_start, start)
        local_end = min(span.char_end, end)
        if local_start < local_end:
            rebased.append(
                OverrideSpan(
                    local_start - start,
                    local_end - start,
                    dict(span.attrs),
                )
            )
    return rebased


def _validate_segment(segment: object, clean_text: str) -> tuple[str, int, int]:
    try:
        text = segment.text
        start = _validated_offset(segment.char_start, "char_start")
        end = _validated_offset(segment.char_end, "char_end")
    except AttributeError as exc:
        raise TypeError("segments must provide text, char_start, and char_end") from exc
    if not isinstance(text, str):
        raise TypeError("segment text must be a string")
    if end < start or end > len(clean_text):
        raise ValueError(f"invalid segment offsets [{start}:{end}] for clean text")
    if clean_text[start:end] != text:
        raise ValueError(
            f"segment text does not match clean_text[{start}:{end}]: {text!r}"
        )
    return text, start, end


def phonemize_segments(
    clean_text: str,
    segments: Sequence[object],
    overrides: Sequence[object] = (),
    *,
    phonemize: Callable[..., PhonemizeResult],
    **kwargs: Any,
) -> list[PhonemizeResult]:
    """Phonemize offset-preserving segments with document-level overrides."""

    results: list[PhonemizeResult] = []
    for segment in segments:
        text, start, end = _validate_segment(segment, clean_text)
        local_overrides = overrides_for_segment(start, end, overrides)
        results.append(phonemize(text, overrides=local_overrides, **kwargs))
    return results


__all__ = [
    "SegmentLike",
    "coerce_override_spans",
    "overrides_for_segment",
    "overrides_from_ssmd",
    "phonemize_segments",
]
