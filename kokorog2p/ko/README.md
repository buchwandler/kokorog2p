# Korean G2P provenance

The Korean pronunciation engine is a local, packaged adaptation of the `g2pkc`
variant used by 5Hyeons/StyleTTS2. Its rule lineage originates in
[Kyubyong/g2pK](https://github.com/Kyubyong/g2pK).

## Frozen sources

- Compatibility source: [5Hyeons/StyleTTS2](https://github.com/5Hyeons/StyleTTS2)
- Branch: `vocos`
- Source revision: `a895e5bff1d7a22dff2f2d32dafb7c4c4e0ee4b7`
- Data path: `g2pK/g2pkc/table.csv`
- `table.csv` SHA-256: `61aca8535fd75f16ca71df59bc5eeab625073edfd50732fda3f12b30ccade31f`
- Default Kokoro model tokenizer:
  <https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/blob/main/tokenizer.json>
- Tokenizer SHA-256: `77a02c8e164413299b4b4c403b14f8e0e1c1b727db4d46a09d6327b861060a34`

The local adaptation converts upstream data modules to Python modules, keeps
`link3` out of the executed link pipeline for Kokoro compatibility, avoids
runtime downloads, and supports operation without optional morphology or CMUdict
resources when the input does not require them.

The copied rule data retains its upstream Apache-2.0 provenance. This document
records source identity and local changes; the repository's license and notice
files apply to distribution.
