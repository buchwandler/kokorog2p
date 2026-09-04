from __future__ import annotations

from lexphon import PronunciationToken

from kokorog2p.th.g2p import ThaiG2P


class RecordingLexphon:
    def __init__(self) -> None:
        self.sources: list[str] = []

    def lookup_prefixes(self, text: str, *, position: int = 0, tag: str | None = None):
        del tag
        self.sources.append(text)
        return (
            (
                PronunciationToken(
                    text=text[position:],
                    pronunciation="a",
                    source="lexicon",
                    lexicon_id="th:lexhint",
                    matched_key=text[position:],
                    source_encoding="ipa",
                ),
            )
            if position == 0
            else ()
        )


def test_prepared_thai_input_skips_legacy_semantic_normalizer() -> None:
    lexphon = RecordingLexphon()
    g2p = ThaiG2P(latin_fallback="none")
    g2p._lexphon = lexphon  # type: ignore[assignment]
    g2p._kokorog2p_prepared_input = True

    g2p("สิบสอง นาฬิกา ศูนย์")

    assert set(lexphon.sources) == {"สิบสอง", "นาฬิกา", "ศูนย์"}
    assert lexphon.sources.count("สิบสอง") == len("สิบสอง")
    assert lexphon.sources.count("นาฬิกา") == len("นาฬิกา")
    assert lexphon.sources.count("ศูนย์") == len("ศูนย์")
