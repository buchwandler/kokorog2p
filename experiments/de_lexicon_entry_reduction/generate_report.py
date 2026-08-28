#!/usr/bin/env python3
"""Render a Markdown report from a run summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .lexreduce.reports import report_markdown
except ImportError:  # direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.de_lexicon_entry_reduction.lexreduce.reports import report_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    output = args.output or args.summary.with_name("report.md")
    output.write_text(report_markdown(summary), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
