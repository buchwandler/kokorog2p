"""Small Korean semantic-preparation fallback for older Spokenform releases."""

import re

from kokorog2p.types import TextReplacement

_PATTERNS = (
    (
        re.compile(r"(?P<number>\d[\d,]*)\s*°\s*[Cc]"),
        "섭씨 {number}도",
        "temperature-celsius",
    ),
    (
        re.compile(r"(?P<number>\d[\d,]*)\s*km/h", re.IGNORECASE),
        "시속 {number}킬로미터",
        "speed-kilometer-per-hour",
    ),
    (
        re.compile(r"(?P<number>\d[\d,]*)\s*L/100km", re.IGNORECASE),
        "100킬로미터당 {number}리터",
        "fuel-consumption-liter-per-100-kilometer",
    ),
    (re.compile(r"₩(?P<number>\d[\d,]*)"), "{number}원", "currency-krw"),
    (
        re.compile(r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"),
        "{year}년 {month}월 {day}일",
        "date-iso",
    ),
)


def replacements(
    text: str,
    *,
    source_offset: int = 0,
    protected_spans: tuple[tuple[int, int], ...] = (),
) -> list[TextReplacement]:
    """Return source-aligned structured Korean semantic replacements."""
    found: list[TextReplacement] = []
    occupied: list[tuple[int, int]] = []
    for pattern, template, rule in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(
                start < protected_end and end > protected_start
                for protected_start, protected_end in protected_spans
            ):
                continue
            if any(
                start < other_end and end > other_start
                for other_start, other_end in occupied
            ):
                continue
            found.append(
                TextReplacement(
                    start=source_offset + start,
                    end=source_offset + end,
                    text=template.format(**match.groupdict()),
                    kind="structured",
                    rule=f"structured:ko:{rule}",
                    language="ko",
                    stages=("structured",),
                )
            )
            occupied.append((start, end))
    return sorted(found, key=lambda item: item.start)
