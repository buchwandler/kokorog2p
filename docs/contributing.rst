Contributing
============

We welcome contributions to kokorog2p! This guide will help you get started.

Development Setup
-----------------

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/holgern/kokorog2p.git
      cd kokorog2p

2. **Create a virtual environment**:

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install development dependencies**:

   .. code-block:: bash

      pip install -e ".[dev]"

4. **Install pre-commit hooks**:

   .. code-block:: bash

      pre-commit install

Running Tests
-------------

Run all tests:

.. code-block:: bash

   pytest tests/

Run specific test file:

.. code-block:: bash

   pytest tests/test_en_g2p.py

Run with coverage:

.. code-block:: bash

   pytest tests/ --cov=kokorog2p --cov-report=html

Code Quality
------------

Format code:

.. code-block:: bash

   ruff format kokorog2p/ tests/

Lint code:

.. code-block:: bash

   ruff check kokorog2p/ tests/

Type checking:

.. code-block:: bash

   mypy kokorog2p/

Building Documentation
----------------------

Build HTML documentation:

.. code-block:: bash

   cd docs/
   python make.py html

View documentation:

.. code-block:: bash

   open _build/html/index.html  # On macOS
   xdg-open _build/html/index.html  # On Linux

Adding a New Language
---------------------

To add support for a new language:

1. **Create language module**:

   .. code-block:: text

      kokorog2p/
      └── xx/  # Two-letter language code
          ├── __init__.py
          ├── g2p.py
          ├── lexicon.py (if dictionary-based)
          ├── numbers.py (for number handling)
          └── data/
              └── __init__.py

2. **Implement G2P class**:

   .. code-block:: python

      from kokorog2p.base import G2PBase
      from kokorog2p.token import GToken

      class NewLanguageG2P(G2PBase):
          def __init__(self, language="xx", **kwargs):
              super().__init__(language=language, **kwargs)

          def __call__(self, text: str) -> list[GToken]:
              # Implement phonemization
              pass

3. **Add to get_g2p()**:

   Edit ``kokorog2p/__init__.py`` to add language support:

   .. code-block:: python

      elif lang in ("xx", "xx-xx", "xxx", "language_name"):
          from kokorog2p.xx import NewLanguageG2P
          g2p = NewLanguageG2P(language=language, **kwargs)

4. **Add tests**:

   Create ``tests/test_xx_g2p.py`` with comprehensive tests.

5. **Add benchmark**:

   Create ``benchmarks/benchmark_xx_g2p.py`` for performance testing.

6. **Update documentation**:

   - Add to ``docs/languages.rst``
   - Create ``docs/api/newlanguage.rst``

Submitting Changes
------------------

1. **Create a branch**:

   .. code-block:: bash

      git checkout -b feature/my-new-feature

2. **Make changes and commit**:

   .. code-block:: bash

      git add .
      git commit -m "Add new feature"

3. **Push to GitHub**:

   .. code-block:: bash

      git push origin feature/my-new-feature

4. **Create Pull Request**:

   Go to GitHub and create a pull request from your branch.

Code Style Guidelines
---------------------

* Follow PEP 8
* Use type hints for all functions
* Write docstrings for all public functions and classes
* Keep functions focused and small
* Add tests for new features
* Update documentation for API changes

Commit Message Guidelines
--------------------------

* Use present tense ("Add feature" not "Added feature")
* Use imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit first line to 72 characters
* Reference issues and pull requests when relevant

Getting Help
------------

* Open an issue on GitHub
* Join our Discord server
* Email the maintainers

Thank you for contributing!
