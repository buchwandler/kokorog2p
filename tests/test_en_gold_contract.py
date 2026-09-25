from kokorog2p.en.phoneme_codec import select_source_value
from tools.audit_en_gold_misaki_contract import audit_entries


class TaggedValueLike:
    def __init__(self, *items: tuple[str, object]) -> None:
        self.items = items


def _valid_fixture() -> dict[str, object]:
    entries: dict[str, object] = {
        letter: "ˈA" for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    }
    entries.update(
        {
            "am": "əm",
            "to": "tu",
            "used": {"DEFAULT": "juːzd", "VBD": "juːzd"},
            "versus": "vɜɹsəs",
            "read": {"VERB": "ɹid", "DEFAULT": "ɹɛd"},
        }
    )
    return entries


def test_gold_contract_accepts_g2lex_tagged_values() -> None:
    tagged = TaggedValueLike(("DEFAULT", "jˈuzd"), ("VBD", None))
    assert select_source_value(tagged, "VBD") == ("jˈuzd", "DEFAULT")
    assert audit_entries({**_valid_fixture(), "used": tagged}) == ()


def test_gold_contract_fixture_passes() -> None:
    assert audit_entries(_valid_fixture()) == ()


def test_gold_contract_reports_stage_aware_findings() -> None:
    entries = _valid_fixture()
    del entries["A"]
    entries["read"] = {"VERB": "ɹid"}
    entries["broken"] = "hɛ§lo"
    findings = audit_entries(entries)
    assert {finding["stage"] for finding in findings} == {
        "encoding",
        "selector",
        "spelling",
    }
    assert any(finding["key"] == "read" for finding in findings)
    assert any(finding["key"] == "broken" for finding in findings)
    assert any(finding["key"] == "A" for finding in findings)
