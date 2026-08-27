"""Thai semantic preparation kept local until spokenform owns Thai."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Iterator

from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.types import TextReplacement

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_DIGITS = ("ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า")
_SMALL_UNITS = ("", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน")
_WORD_RE = re.compile(r"\S+")
_DECIMAL_RE = re.compile(r"(?<!\w)(\d+)\.(\d+)(?!\w)")
_RANGE_RE = re.compile(r"(?<!\w)(\d+)\s*(?:-|–|—|ถึง)\s*(\d+)(?!\w)")
_CURRENCY_RE = re.compile(r"(?:฿|บาท\s*)(\d+(?:\.\d+)?)|(?<!\w)(\d+(?:\.\d+)?)\s*บาท")
_TIME_RE = re.compile(r"(?<!\w)(\d{1,2}):(\d{2})(?!\w)")
_IDENTIFIER_RE = re.compile(r"(?<!\w)(\d[\d\-/]{2,})(?!\w)")

_OPERATOR_WORDS = {
    "%": "เปอร์เซ็นต์",
    "+": "บวก",
    "=": "เท่ากับ",
    "<": "น้อยกว่า",
    ">": "มากกว่า",
    "≤": "น้อยกว่าหรือเท่ากับ",
    "≥": "มากกว่าหรือเท่ากับ",
}
_PUNCTUATION_TRANSLATION = str.maketrans(
    {"、": ",", "。": ".", "！": "!", "？": "?", "，": ",", "：": ":", "；": ";"}
)


class ThaiNormalizer:
    """Normalize common Thai text forms without loading Thai NLP packages."""

    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.diagnostics: list[dict[str, str]] = []

    def _cardinal_under_million(self, value: int) -> str:
        if value == 0:
            return _DIGITS[0]
        digits = str(value)
        parts: list[str] = []
        for position, digit_text in enumerate(digits):
            digit = int(digit_text)
            unit_position = len(digits) - position - 1
            if not digit:
                continue
            if unit_position == 1 and digit == 2:
                parts.append("ยี่สิบ")
            elif unit_position == 1 and digit == 1:
                parts.append("สิบ")
            elif unit_position == 0 and digit == 1 and value >= 20:
                parts.append("เอ็ด")
            else:
                parts.append(_DIGITS[digit] + _SMALL_UNITS[unit_position])
        return "".join(parts)

    def cardinal(self, value: int) -> str:
        if value < 0:
            return "ลบ" + self.cardinal(-value)
        if value >= 1_000_000:
            millions, remainder = divmod(value, 1_000_000)
            result = self.cardinal(millions) + "ล้าน"
            return result + (
                self._cardinal_under_million(remainder) if remainder else ""
            )
        return self._cardinal_under_million(value)

    @staticmethod
    def _digits(value: str) -> str:
        return " ".join(_DIGITS[int(char)] for char in value)

    def _number_or_digits(self, value: str, *, identifier: bool = False) -> str:
        if identifier:
            return self._digits(value)
        return self.cardinal(int(value))

    def _replace_time(self, match: re.Match[str]) -> str:
        hour, minute = match.groups()
        return f"{self.cardinal(int(hour))} นาฬิกา {self._digits(minute)} นาที"

    def _replace_decimal(self, match: re.Match[str]) -> str:
        integer, fraction = match.groups()
        return f"{self.cardinal(int(integer))} จุด {self._digits(fraction)}"

    def _replace_currency(self, match: re.Match[str]) -> str:
        value = match.group(1) or match.group(2)
        if "." in value:
            integer, fraction = value.split(".", 1)
            return f"{self.cardinal(int(integer))} บาท {self._digits(fraction)} สตางค์"
        return f"{self.cardinal(int(value))} บาท"

    @staticmethod
    def _replace_identifier_value(value: str) -> str:
        if "/" in value or "-" in value:
            return " ".join(
                ThaiNormalizer._digits(part) if part.isdigit() else "ขีด"
                for part in re.split(r"([/-])", value)
                if part
            )
        return ThaiNormalizer._digits(value)

    def _expand_repetition(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            word = match.group(1)
            return f"{word} {word}"

        return re.sub(r"(\S+)\s*ๆ", replace, text)

    def _collapse_elongation(self, text: str) -> str:
        # Two copies can be meaningful Thai spelling. Three or more are chat elongation.
        return re.sub(r"([ก-ฮะ-์])\1{2,}", r"\1\1", text)

    def _fold_latin_accents(self, text: str) -> str:
        output: list[str] = []
        for char in text:
            if char.isascii() and char.isalpha():
                output.append(char)
                continue
            if char.isalpha() and "LATIN" in unicodedata.name(char, ""):
                output.extend(
                    part
                    for part in unicodedata.normalize("NFKD", char)
                    if not unicodedata.combining(part)
                )
            else:
                output.append(char)
        return "".join(output)

    def _drop_unsupported(self, text: str) -> str:
        kept: list[str] = []
        dropped: list[str] = []
        for char in text:
            category = unicodedata.category(char)
            if (
                category.startswith("C")
                and char not in "\n\t\r"
                or category == "So"
                and not ("THAI" in unicodedata.name(char, ""))
            ):
                dropped.append(char)
            else:
                kept.append(char)
        if dropped:
            unique = "".join(dict.fromkeys(dropped))
            self.warnings.append(f"TH_UNSUPPORTED_SOURCE_SYMBOL: dropped {unique!r}")
            self.diagnostics.append(
                {"kind": "TH_UNSUPPORTED_SOURCE_SYMBOL", "symbols": unique}
            )
        return "".join(kept)

    def normalize(self, text: str) -> str:
        self.warnings = []
        self.diagnostics = []
        result = text.translate(_THAI_DIGITS)
        result = self._fold_latin_accents(result)
        result = self._collapse_elongation(result)
        result = re.sub(r"(?<!\w)(\d{1,2}):(\d{2})(?!\w)", self._replace_time, result)
        result = _CURRENCY_RE.sub(self._replace_currency, result)
        result = _DECIMAL_RE.sub(self._replace_decimal, result)
        result = _RANGE_RE.sub(
            lambda m: (
                f"{self.cardinal(int(m.group(1)))} ถึง {self.cardinal(int(m.group(2)))}"
            ),
            result,
        )
        result = re.sub(
            r"((?:เลขที่|รหัส|โทร|เบอร์|บัญชี)\s+)([\d\-/]{3,})",
            lambda m: m.group(1) + self._replace_identifier_value(m.group(2)),
            result,
        )
        result = re.sub(
            r"(?<!\w)(\d[\d\-/]*[/-]\d[\d\-/]*)(?!\w)",
            lambda m: self._replace_identifier_value(m.group(1)),
            result,
        )

        def replace_integer(match: re.Match[str]) -> str:
            value = match.group(0)
            before = result[max(0, match.start() - 8) : match.start()]
            if value == "555" and not re.search(
                r"[บาทคนครั้งกิโลเมตร]", result[match.end() : match.end() + 4]
            ):
                return "ฮ่า ฮ่า ฮ่า"
            identifier = bool(re.search(r"(?:เลขที่|รหัส|โทร|เบอร์|บัญชี)\s*$", before))
            return self._number_or_digits(value, identifier=identifier)

        result = re.sub(r"(?<![\w.])\d+(?![\w.])", replace_integer, result)
        result = self._expand_repetition(result)
        for symbol, spoken in _OPERATOR_WORDS.items():
            result = result.replace(symbol, f" {spoken} ")
        result = result.translate(_PUNCTUATION_TRANSLATION)
        result = normalize_punctuation(result)
        result = self._drop_unsupported(result)
        return re.sub(r"[ \t\r\n]+", " ", result).strip()

    def __call__(self, text: str) -> str:
        return self.normalize(text)

    def normalize_token(self, text: str, **_: object) -> str:
        return self.normalize(text)

    def iter_structured_replacements(
        self, text: str, *, protected_spans: Iterable[tuple[int, int]] = ()
    ) -> Iterator[TextReplacement]:
        del protected_spans
        normalized = self.normalize(text)
        if normalized != text:
            yield TextReplacement(
                start=0,
                end=len(text),
                text=normalized,
                kind="THAI_NORMALIZATION",
                priority=10,
                language="th-th",
            )

    def normalize_for_g2p(self, text: str) -> str:
        return self.normalize(text)


__all__ = ["ThaiNormalizer"]
