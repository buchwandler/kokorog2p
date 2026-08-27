# Thai clean-room benchmark dataset

These cases are independently authored synthetic contract fixtures. They are not copied
from the Wayu evaluation or training corpora.

| Fixture                      | Origin                                | License                              | Retrieval date | Expected pronunciation           | Redistribution               |
| ---------------------------- | ------------------------------------- | ------------------------------------ | -------------- | -------------------------------- | ---------------------------- |
| `thai_cleanroom_cases.jsonl` | Independently authored by the project | CC0-compatible project-authored text | 2026-08-27     | TLTK or human review when frozen | Allowed with this repository |

The differential benchmark accepts an operator-provided checkout of the pinned Wayu
reference. The checkout must provide a development-only `benchmark_adapter.py` that
reads the JSONL cases from stdin and emits one JSON object per case with `id`, and
optionally `normalized`, `phonemes`, and `drops`. The reference checkout is not
vendored, downloaded, imported at runtime, or used by normal CI.
