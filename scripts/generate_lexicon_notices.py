#!/usr/bin/env python3
"""Generate the packaged third-party lexicon notice from the manifest."""

from __future__ import annotations

from pathlib import Path

from build_g2lex_assets import ROOT, load_manifest


def _license_name(expression: str) -> str:
    return {
        "CC-BY-SA-4.0": (
            "Creative Commons Attribution-ShareAlike 4.0 International "
            + "(CC BY-SA 4.0)"
        ),
        "CC-BY-SA-3.0": "Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)",
        "MIT": "MIT",
    }.get(expression, expression)


def render() -> str:
    lines = [
        "# Third-party data notices",
        "",
        (
            "Runtime lexicon lookup is offline and does not download "
            "or parse canonical source files."
        ),
        "",
    ]
    for record in load_manifest():
        if not record.get("provider"):
            continue
        identifier = str(record["id"])
        asset = Path(str(record["asset"])).name
        source = Path(str(record["source"])).relative_to("lexicons/sources")
        lines.extend(
            [
                f"## `{asset}` ({identifier})",
                "",
                f"- **Provider:** {record['provider']}",
                f"- **Pinned revision:** `{record['revision']}`",
                f"- **Source file:** `{source}`",
                f"- **Source URL:** {record['source_url']}",
                f"- **Attribution:** {record['attribution']}",
                f"- **License:** {_license_name(str(record['license_expression']))}",
                f"- **License URL:** {record['license_url']}",
                "",
                (
                    f"`{asset}` is a generated, lossless G2Lex asset built "
                    + "from the pinned source."
                ),
                "The canonical source is not included in the wheel or sdist.",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    destination = ROOT / "kokorog2p" / "lexicons" / "data" / "THIRD_PARTY_NOTICES.md"
    destination.write_text(render(), encoding="utf-8")
    print(destination)
