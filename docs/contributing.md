# Contributing

We welcome contributions to kokorog2p! This guide will help you get started.

## Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/buchwandler/kokorog2p.git
   cd kokorog2p
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:

   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

## Running Tests

Run the safe core selection with plain pytest:

```bash
python -m pytest -q
```

Bare pytest excludes tests marked `integration`, `spacy`, `slow`, or `resource_heavy`.
Use the canonical runner for deterministic sequential batches and broader profiles:

```bash
python tools/run_test_suite.py --profile core --batch-size 8 --max-rss-mb auto
python tools/run_test_suite.py --profile full --batch-size 4 --max-rss-mb auto
python tools/run_test_suite.py --profile full --include-integration --max-rss-mb auto
```

Inspect or filter the plan without running tests:

```bash
python tools/run_test_suite.py --profile full --list-plan
python tools/run_test_suite.py --profile full --match "en|normalization" --list-plan
python tools/run_test_suite.py --profile full --start-at tests/test_en_g2p.py --list-plan
```

Pass pytest arguments with `--pytest-arg=-vv` or after the runner options. The runner
executes one child at a time, applies automatic or explicit RSS ceilings, splits a
resource-limited batch, and reports all failed groups. Do not use xdist or parallel
workers as a memory workaround.

Coverage is aggregated across the sequential subprocesses:

```bash
python tools/run_test_suite.py --profile core --coverage --junit-dir junit
```

The separate wrapper is useful for focused RSS diagnostics:

```bash
python tools/run_pytest_with_memory.py --max-rss-mb auto -q tests/test_en_g2p.py
```

Optional spaCy, native backend, multilingual, and cross-package checks remain marked and
are run by their corresponding full or specialized workflow jobs. Provision external
Lexphon data explicitly for released-data integration tests.

## Code Quality

Format code:

```bash
ruff format kokorog2p/ tests/
```

Lint code:

```bash
ruff check kokorog2p/ tests/
```

Type checking:

```bash
mypy kokorog2p/
```

## Building Documentation

Build HTML documentation:

```bash
cd docs/
python make.py html
```

View documentation:

```bash
open _build/html/index.html  # On macOS
xdg-open _build/html/index.html  # On Linux
```

## Adding a New Language

To add support for a new language:

1. **Create language module**:

   ```text
   kokorog2p/
   └── xx/  # Two-letter language code
       ├── __init__.py
       ├── g2p.py
       ├── lexicon.py (if dictionary-based)
   ├── normalizer.py (for intrinsic typography/phonology)
       └── data/
           └── __init__.py
   ```

2. **Implement G2P class**:

   ```python
   from kokorog2p.base import G2PBase
   from kokorog2p.token import GToken

   class NewLanguageG2P(G2PBase):
       def __init__(self, language="xx", **kwargs):
           super().__init__(language=language, **kwargs)

       def __call__(self, text: str) -> list[GToken]:
           # Implement phonemization
           pass
   ```

3. **Add to get_g2p()**:

   Edit `kokorog2p/__init__.py` to add language support:

   ```python
   elif lang in ("xx", "xx-xx", "xxx", "language_name"):
       from kokorog2p.xx import NewLanguageG2P
       g2p = NewLanguageG2P(language=language, **kwargs)
   ```

4. **Add tests**:

   Create `tests/test_xx_g2p.py` with comprehensive tests.

5. **Add benchmark**:

   Create `benchmarks/benchmark_xx_g2p.py` for performance testing.

6. **Update documentation**:

   - Add to `docs/languages.md`
   - Create `docs/api/newlanguage.md`

## Submitting Changes

1. **Create a branch**:

   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make changes and commit**:

   ```bash
   git add .
   git commit -m "Add new feature"
   ```

3. **Push to GitHub**:

   ```bash
   git push origin feature/my-new-feature
   ```

4. **Create Pull Request**:

   Go to GitHub and create a pull request from your branch.

## Code Style Guidelines

- Follow PEP 8
- Use type hints for all functions
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Add tests for new features
- Update documentation for API changes

## Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests when relevant

## Getting Help

- Open an issue on GitHub
- Join our Discord server
- Email the maintainers

Thank you for contributing!
