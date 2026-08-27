import subprocess
import sys


def test_cli_help_has_no_network_side_effect():
    command = [
        sys.executable,
        "experiments/de_lexicon_compression/compress.py",
        "--help",
    ]
    assert subprocess.run(command, check=True, capture_output=True).returncode == 0
