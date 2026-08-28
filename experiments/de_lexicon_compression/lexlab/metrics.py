"""Compression, quality, and representation metrics for experiment runs."""

from __future__ import annotations

import gzip
import lzma
import zlib
from collections.abc import Sequence


def levenshtein(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        current = [i]
        for j, other in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (char != other),
                )
            )
        previous = current
    return previous[-1]


def cer(expected: Sequence[str], actual: Sequence[str]) -> float:
    reference = sum(len(value) for value in expected)
    distance = sum(
        levenshtein(left, right) for left, right in zip(expected, actual, strict=False)
    )
    distance += sum(len(value) for value in expected[len(actual) :])
    distance += sum(len(value) for value in actual[len(expected) :])
    return distance / reference if reference else (0.0 if distance == 0 else 1.0)


def compression_layers(data: bytes) -> dict[str, int]:
    """Return deterministic sizes used by installed and wheel comparisons."""
    raw_deflate = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
    deflated = raw_deflate.compress(data) + raw_deflate.flush()
    return {
        "plain_bytes": len(data),
        "gzip_bytes": len(gzip.compress(data, mtime=0)),
        "xz_bytes": len(
            lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64)
        ),
        "wheel_equivalent_deflate_bytes": len(deflated),
    }


def compare_compression_layers(baseline: bytes, asset: bytes) -> dict[str, int | float]:
    """Compare equivalent encodings and expose net savings in each layer."""
    baseline_sizes = compression_layers(baseline)
    asset_sizes = compression_layers(asset)
    result: dict[str, int | float] = {}
    for key, value in baseline_sizes.items():
        result[f"baseline_{key}"] = value
    for key, value in asset_sizes.items():
        result[f"asset_{key}"] = value
        result[f"net_{key.replace('_bytes', '')}_saved"] = value * -1
    for layer in ("plain", "gzip", "xz", "wheel_equivalent_deflate"):
        base = baseline_sizes[f"{layer}_bytes"]
        compressed = asset_sizes[f"{layer}_bytes"]
        result[f"net_{layer}_bytes_saved"] = base - compressed
        result[f"reduction_vs_{layer}_pct"] = (
            (1 - compressed / base) * 100 if base else 0.0
        )
    return result
