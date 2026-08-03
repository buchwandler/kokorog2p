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

Run all tests:

```bash
pytest tests/
```

Run specific test file:

```bash
pytest tests/test_en_g2p.py
```

Run with coverage:

```bash
pytest tests/ --cov=kokorog2p --cov-report=html
```

### Running on memory-constrained machines

The English and German dictionaries are large, and optional spaCy models add substantial
native memory. Prefer sequential pytest processes for independent language groups
instead of `pytest-xdist`; each xdist worker loads another interpreter and may load
another dictionary or model.

```bash
python -m pytest -q tests/test_attr_parser.py tests/test_base.py tests/test_pipeline_api.py
python -m pytest -q tests/test_en_*.py tests/test_quote_*.py
python -m pytest -q tests/test_de_g2p.py
```

Peak RSS can be observed with `python tools/run_pytest_with_memory.py -q`. For a clean
collection comparison, set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. A bare `Killed` message
or exit status 137 can indicate an operating-system OOM kill; on Linux, inspect `dmesg`
or `journalctl -k` after the run and check any container or cgroup memory limit.

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
       ├── numbers.py (for number handling)
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
