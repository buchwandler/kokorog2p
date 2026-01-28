from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.voice import Voice
from kokorog2p.backends.espeak.wrapper import find_espeak_data


class EspeakCliError(RuntimeError):
    pass


class CliPhonemizer(EspeakPhonemizerBase):
    def __init__(
        self,
        language: str = "en-us",
        executable: str | None = None,
        data_path: str | Path | None = None,
        sep: str = "_",
        tie_char: str = "^",
    ) -> None:
        super().__init__()  # <-- shared state init

        self.language = language
        self.executable = executable
        self.sep = sep
        self.tie_char = tie_char
        self._voice_name: str | None = None

        if data_path is None:
            data_path = find_espeak_data()
        self._data_path: Path | None = (
            Path(data_path) if data_path is not None else None
        )
        self.set_voice(language)

    def _exe(self) -> str:
        if self.executable:
            return self.executable
        return (
            os.environ.get("KOKOROG2P_ESPEAK_EXECUTABLE")
            or shutil.which("espeak-ng")
            or shutil.which("espeak")
            or "espeak-ng"
        )

    @classmethod
    def is_available(cls) -> bool:
        env = os.environ.get("KOKOROG2P_ESPEAK_EXECUTABLE")
        return bool(env or shutil.which("espeak-ng") or shutil.which("espeak"))

    @property
    def version(self) -> tuple[int, ...]:
        if self._version is None:
            exe = self._exe()
            try:
                p = subprocess.run([exe, "--version"], text=True, capture_output=True)
            except FileNotFoundError as e:
                raise EspeakCliError(
                    "espeak-ng CLI executable not found. Install espeak-ng (or espeak) "
                    "or set KOKOROG2P_ESPEAK_EXECUTABLE to the full path of the binary."
                ) from e
            s = (p.stdout or "") + "\n" + (p.stderr or "")
            ver, data = self._parse_version_output(s)
            self._version = ver
            if self._data_path is None and data is not None:
                self._data_path = data
        return self._version

    @property
    def voice_language(self) -> str | None:
        return self.language

    @property
    def data_path(self) -> Path | None:
        return self._data_path

    def set_voice(self, language: str) -> None:
        identifier, voice = self._resolve_voice(language)
        self.language = language
        self._voice_name = identifier
        self._current_voice = voice  # enables base.voice_language, pickling, etc.

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        exe = self._exe()
        if filter_name:
            cmd = [exe, f"--voices={filter_name}"]
        else:
            cmd = [exe, "--voices"]
        if self.data_path:
            cmd.append(f"--path={self.data_path}")

        try:
            p = subprocess.run(cmd, text=True, encoding="utf-8", capture_output=True)
        except FileNotFoundError as e:
            raise EspeakCliError(
                "espeak-ng CLI executable not found. Install espeak-ng (or espeak) "
                "or set KOKOROG2P_ESPEAK_EXECUTABLE to the full path of the binary."
            ) from e
        if p.returncode != 0:
            raise EspeakCliError(
                f"espeak-ng failed (rc={p.returncode}): {p.stderr.strip()}"
            )

        voices: list[Voice] = []
        for line in (p.stdout or "").splitlines():
            line = line.strip()
            if not line or line.startswith("Pty"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            language = parts[1]
            name = parts[3].replace("_", " ")
            identifier = parts[4]
            voices.append(Voice(name=name, language=language, identifier=identifier))

        return voices

    def phonemize(self, text: str, use_tie: bool = False) -> str:
        if not text or not text.strip():
            return ""

        if use_tie and self.version < (1, 49):
            raise RuntimeError("Tie option requires espeak >= 1.49")

        exe = self._exe()
        voice = self._voice_name or self.language
        cmd = [
            exe,
            "-q",
            "-x",
            "--ipa",
            f"-v{voice}",
        ]
        if use_tie:
            cmd.append(f"--tie={self.tie_char}")
        else:
            cmd.append(f"--sep={self.sep}")
        if self.data_path:
            cmd.append(f"--path={self.data_path}")

        try:
            p = subprocess.run(
                cmd,
                input=text,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )
        except FileNotFoundError as e:
            raise EspeakCliError(
                "espeak-ng CLI executable not found. Install espeak-ng (or espeak) "
                "or set KOKOROG2P_ESPEAK_EXECUTABLE to the full path of the binary."
            ) from e
        if p.returncode != 0:
            raise EspeakCliError(
                f"espeak-ng failed (rc={p.returncode}): {p.stderr.strip()}"
            )

        out = re.sub(r"\s+", " ", (p.stdout or "").strip())
        if not use_tie:
            out = out.replace(self.tie_char, "")
        return out
