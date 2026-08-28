#!/usr/bin/env python3
"""Run the bounded V1 matrix or the staged V2 experiment matrix."""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

try:
    from .run import run
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.de_lexicon_entry_reduction.run import run


def _run_v2_stages(args: argparse.Namespace) -> list[dict[str, object]]:
    stages = (
        ("V1-R", {"selector": "v1", "boundary_rules": "v1", "linkers": "v1"}),
        ("S1", {"selector": "v2", "boundary_rules": "v1", "linkers": "v1"}),
        ("B1", {"selector": "v2", "boundary_rules": "v2", "linkers": "v1"}),
        ("L1", {"selector": "v2", "boundary_rules": "v2", "linkers": "german"}),
        (
            "R1",
            {
                "selector": "v2",
                "boundary_rules": "v2",
                "linkers": "german",
                "recursive_components": True,
            },
        ),
        (
            "O1",
            {
                "selector": "v2",
                "boundary_rules": "v2",
                "linkers": "german",
                "recursive_components": True,
            },
        ),
        (
            "G1",
            {
                "selector": "v2",
                "boundary_rules": "v2",
                "linkers": "german",
                "segmentation_scorer": "v2",
            },
        ),
        (
            "A1",
            {
                "selector": "v2",
                "boundary_rules": "v2",
                "linkers": "german",
                "affixes": "german",
            },
        ),
    )
    rows = []
    for name, options in stages:
        destination = args.output / name
        row = run(
            args.source,
            "implicit-compound",
            destination,
            data_root=args.data_root,
            path=args.path,
            max_components=args.max_components,
            max_states=args.max_states,
            optimizer="utility" if name == "O1" else "greedy",
            **options,
        )
        row["stage"] = name
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="builtin")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--components", default="2,3,4")
    parser.add_argument("--rules", default="concat,compound")
    parser.add_argument("--optimizer", default="greedy,utility")
    parser.add_argument(
        "--v2-stages",
        action="store_true",
        help="run V1-R through the staged V2 configurations",
    )
    parser.add_argument("--max-components", type=int, default=4)
    parser.add_argument("--max-states", type=int, default=100_000)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--path", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.v2_stages:
        rows = _run_v2_stages(args)
    else:
        rows = []
        for components, rule, optimizer in product(
            (int(value) for value in args.components.split(",")),
            args.rules.split(","),
            args.optimizer.split(","),
        ):
            mode = "implicit-compound" if rule == "compound" else "implicit-concat"
            destination = args.output / f"{mode}-c{components}-{optimizer}"
            rows.append(
                run(
                    args.source,
                    mode,
                    destination,
                    data_root=args.data_root,
                    path=args.path,
                    max_components=components,
                    optimizer=optimizer,
                )
            )
    (args.output / "matrix.json").write_text(
        json.dumps(rows, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
