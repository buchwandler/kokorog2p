"""Deprecated Spokenform-backed Korean numeral compatibility helpers."""

from __future__ import annotations

import re

from spokenform import prepare_for_kokorog2p
from spokenform.locales.ko import process_num as _spokenform_process_num

BOUND_NOUNS = (
    "군데 권 개 그루 닢 두 마리 모 모금 뭇 발 발짝 방 번 벌 보루"
    " 살 수 술 시 쌈 움큼 정 짝 채 척 첩 축 켤레 톨 통 가지 배 시간 살 명 줄 곳"
)
_BOUND_NOUN_PATTERN = re.compile(
    r"(?P<number>[\d][\d,]*)(?P<noun> ?(?:"
    + "|".join(
        sorted(
            (re.escape(noun) for noun in set(BOUND_NOUNS.split())),
            key=len,
            reverse=True,
        )
    )
    + r"))(?:/B)?"
)


def process_num(num: str, sino: bool = True) -> str:
    """Return a Korean numeral using Spokenform's compatibility implementation."""
    return _spokenform_process_num(num, sino=sino)


def convert_num(string: str) -> str:
    """Prepare annotated Korean text through Spokenform.

    This historical helper is retained for direct g2pk callers. The semantic
    number and counter rules are owned by Spokenform rather than this package.
    """

    def replace_counter(match: re.Match[str]) -> str:
        source = match.group(0)
        marker = "/B" if source.endswith("/B") else ""
        return (
            prepare_for_kokorog2p(
                source.removesuffix(marker), language="ko"
            ).spoken_text
            + marker
        )

    prepared = _BOUND_NOUN_PATTERN.sub(replace_counter, string)
    return prepare_for_kokorog2p(prepared, language="ko").spoken_text


if __name__ == "__main__":
    print(process_num("123,456,789"))
    print(process_num("123,456,789", sino=False))
    print(convert_num("우리 3시/B 10분/B에 만나자."))
