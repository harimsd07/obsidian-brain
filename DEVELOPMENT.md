# Development Guide

Guide for setting up development environment and contributing to Obsidian Brain.

---

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Git
- Virtual environment tool (venv, virtualenv, or conda)
- Text editor or IDE (VSCode, PyCharm, Neovim, etc.)

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/obsidian-brain.git
cd obsidian-brain

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 4. Install in development mode
pip install -e ".[dev]"

# 5. Verify installation
pytest tests/
# Should show: 149 passed
```

---

## Project Structure

```
obsidian-brain/
├── brain/                      # Main package
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── config.py               # Configuration management
│   ├── db.py                   # Database layer (ChromaDB)
│   ├── llm.py                  # LLM provider integration
│   ├── retriever.py            # Search/retrieval logic
│   ├── web_ui.py               # FastAPI web server (687 lines)
│   ├── api_docs.py             # OpenAPI documentation (154 lines)
│   ├── middleware.py           # Rate limiting, caching, metrics (NEW)
│   ├── mcp_server.py           # MCP protocol handler
│   ├── telegram_bot.py         # Telegram bot integration
│   ├── commands/               # CLI command modules
│   │   ├── __init__.py
│   │   ├── init.py             # Setup wizard
│   │   ├── ask.py              # Ask questions
│   │   ├── chat.py             # Interactive chat
│   │   ├── search.py           # Text search
│   │   ├── ingest.py           # Index vault
│   │   └── watch.py            # Auto-index
│   └── types.py                # Type definitions
├── tests/                      # Test suite (149 tests)
│   ├── __init__.py
│   ├── test_retriever.py       # Retriever tests
│   ├── test_search.py          # Search tests
│   ├── test_llm.py             # LLM integration tests
│   ├── test_web_ui.py          # API endpoint tests
│   ├── test_config.py          # Configuration tests
│   ├── conftest.py             # Pytest fixtures
│   └── fixtures/               # Test data
├── data/                       # Runtime data
│   └── chroma/                 # Vector database
├── docs/                       # Documentation
│   ├── README.md               # Project overview
│   ├── ARCHITECTURE.md         # System design
│   ├── INSTALLATION.md         # Setup guide
│   ├── COMMANDS.md             # CLI reference
│   ├── WORKFLOW.md             # Usage examples
│   ├── API.md                  # API reference
│   └── DEVELOPMENT.md          # This file
├── pyproject.toml              # Project configuration
├── pytest.ini                  # Pytest configuration
├── .env.example                # Example environment file
├── Dockerfile                  # Docker configuration
└── README.md                   # Quick start guide
```

---

## Code Style & Standards

### Python Style Guide

Follow PEP 8 with these conventions:

```python
# Type hints required
def search(query: str, n: int = 5) -> List[Result]:
    """Search with detailed docstring."""
    pass

# Docstring format
def function(param: str) -> str:
    """
    Brief description.
    
    Longer description if needed.
    
    Args:
        param: Parameter description
    
    Returns:
        Return value description
    
    Raises:
        ValueError: When validation fails
    """
    pass

# Error handling
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### Imports Organization

```python
# 1. Standard library
import os
from pathlib import Path
from typing import List, Optional

# 2. Third-party packages
import typer
from pydantic import BaseModel
import requests

# 3. Local imports
from brain.config import Config
from brain.retriever import retrieve
```

### Formatting

```bash
# Format code with black
black brain/ tests/

# Check style with flake8
flake8 brain/ tests/

# Sort imports with isort
isort brain/ tests/
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_retriever.py

# Run specific test
pytest tests/test_retriever.py::test_retrieve_basic

# Run with coverage
pytest --cov=brain --cov-report=html

# Run tests matching pattern
pytest -k "search"
```

### Writing Tests

```python
import pytest
from brain.retriever import retrieve
from tests.fixtures import sample_vault

def test_retrieve_basic(sample_vault):
    """Test basic retrieval functionality."""
    # Arrange
    query = "python"
    expected_min_results = 1
    
    # Act
    results = retrieve(query, n=5)
    
    # Assert
    assert len(results) >= expected_min_results
    assert all(hasattr(r, 'doc_id') for r in results)

def test_retrieve_validation():
    """Test input validation."""
    # Test empty query
    result = retrieve("")
    assert result == []
    
    # Test whitespace query
    result = retrieve("   ")
    assert result == []
    
    # Test invalid n
    result = retrieve("test", n=-1)
    assert len(result) > 0  # Uses default

def test_retrieve_hybrid_vs_semantic():
    """Test hybrid vs semantic search."""
    query = "machine learning"
    
    hybrid_results = retrieve(query, hybrid=True)
    semantic_results = retrieve(query, hybrid=False)
    
    # Hybrid should generally have different order
    assert len(hybrid_results) > 0
    assert len(semantic_results) > 0
```

### Test Fixtures

```python
# conftest.py
import pytest
from pathlib import Path
from brain.db import add_documents

@pytest.fixture
def sample_vault(tmp_path):
    """Create a temporary vault with sample documents."""
    documents = [
        "Python is a programming language",
        "Machine learning uses algorithms",
        "Deep learning uses neural networks"
    ]
    
    metadatas = [
        {"source": "python.md", "line": 1},
        {"source": "ml.md", "line": 10},
        {"source": "dl.md", "line": 20}
    ]
    
    add_documents(documents, metadatas)
    yield
    # Cleanup after test

@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM for testing without API calls."""
    def mock_generate(prompt):
        return "Mock answer based on: " + prompt[:50]
    
    monkeypatch.setattr("brain.llm.generate_answer", mock_generate)
```

### Coverage Requirements

- Minimum coverage: 80%
- Critical path: 95%
- New features: 90%+

Check coverage:

```bash
pytest --cov=brain --cov-report=term-missing
```

---

## Adding New Features

### Adding a New Command

```python
# brain/commands/new_command.py
import typer
from brain.retriever import retrieve
from brain.llm import generate_answer

app = typer.Typer()

@app.command()
def new_command(
    arg1: str = typer.Argument(..., help="First argument"),
    option1: str = typer.Option("default", help="Optional"),
) -> None:
    """Command description."""
    try:
        # Implementation
        results = retrieve(arg1, n=5)
        answer = generate_answer("prompt")
        
        # Output
        typer.echo(answer)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
```

Register in CLI:

```python
# brain/cli.py
from brain.commands import new_command

@app.command()
def new_command(
    arg1: str = typer.Argument(...),
    option1: str = typer.Option("default")
):
    """Command description."""
    from brain.commands.new_command import app as cmd_app
    cmd_app(arg1, option1)
```

### Adding a New LLM Provider

```python
# 1. Add provider to config.py
class LLMConfig(BaseModel):
    provider: Literal["ollama", "groq", "google", "nvidia-nim", "new-provider"]

# 2. Implement in llm.py
def _generate_new_provider(prompt: str, model: str) -> str:
    """Generate using new provider."""
    api_key = os.getenv("NEW_PROVIDER_API_KEY")
    # Implementation
    return response

def _embed_new_provider(text: str) -> List[float]:
    """Generate embeddings using new provider."""
    api_key = os.getenv("NEW_PROVIDER_API_KEY")
    # Implementation
    return embeddings

# 3. Add to provider router
def generate_answer(prompt: str) -> str:
    if config.llm_config.provider == "new-provider":
        return _generate_new_provider(prompt, config.llm_config.model)
    # ... other providers

# 4. Add to init.py wizard
# 5. Add tests

# 6. Update documentation
```

### Adding a New API Endpoint

```python
# brain/web_ui.py
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/api/new-endpoint")
async def new_endpoint(request: NewRequest) -> NewResponse:
    """
    New endpoint description.
    
    Returns:
        NewResponse: Response data
    """
    try:
        # Input validation done by Pydantic
        # Process request
        result = process(request.param)
        
        # Log
        logger.info(f"New endpoint called with: {request.param}")
        
        return NewResponse(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Define request/response models
class NewRequest(BaseModel):
    param: str = Field(..., min_length=1, max_length=1000)
    
class NewResponse(BaseModel):
    success: bool
    data: dict
```

---

## Debugging

### Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In your code
logger.debug(f"Variable value: {variable}")
logger.info(f"Operation: {operation}")
logger.warning(f"Potential issue: {issue}")
logger.error(f"Error occurred: {error}")
```

### Using Debugger

```python
# With pdb
import pdb; pdb.set_trace()

# With breakpoint() (Python 3.7+)
breakpoint()

# Debug in pytest
pytest -v --pdb tests/test_file.py::test_name
```

### Performance Profiling

```python
import cProfile
import pstats

# Profile function
cProfile.run('my_function()', 'output.prof')

# View results
p = pstats.Stats('output.prof')
p.sort_stats('cumulative').print_stats(10)
```

---

## Git Workflow

### Creating a Feature Branch

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/new-feature

# Make changes
git add .
git commit -m "Add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Commit Message Format

```
feat: Add new feature description
fix: Fix bug description
docs: Update documentation
test: Add tests
refactor: Refactor code
perf: Performance improvement
chore: Maintenance tasks

Example:
feat: Add NVIDIA NIM support to LLM providers

- Implement embedding generation with NVIDIA NIM
- Add to provider selection in init wizard
- Update tests and documentation
```

### Pull Request Process

1. Create feature branch
2. Make changes and commit
3. Write/update tests
4. Update documentation
5. Push and create PR
6. Request review
7. Address feedback
8. Merge after approval

---

## Documentation

### Code Documentation

```python
def complex_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief one-line description.
    
    Longer description explaining the function's purpose,
    behavior, and any important notes.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Dictionary with keys:
        - 'result': The main result
        - 'metadata': Additional information
    
    Raises:
        ValueError: If param1 is empty
        TypeError: If param2 is not an integer
    
    Example:
        >>> result = complex_function("test", 5)
        >>> print(result['result'])
        'test_result'
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    if not isinstance(param2, int):
        raise TypeError("param2 must be an integer")
    
    # Implementation
    return {"result": "value", "metadata": {}}
```

### Updating User Documentation

When adding features, update relevant docs:

- **README.md**: Quick overview
- **ARCHITECTURE.md**: Design decisions
- **COMMANDS.md**: CLI usage
- **API.md**: Endpoint documentation
- **WORKFLOW.md**: Usage examples
- **INSTALLATION.md**: Setup instructions

---

## Performance Optimization

### Profiling

```bash
# Profile retriever
python -m cProfile -s cumulative -m pytest tests/test_retriever.py

# Memory profiling
pip install memory_profiler
python -m memory_profiler brain/retriever.py
```

### Optimization Checklist

- [ ] Use appropriate data structures (dict for lookup, list for iteration)
- [ ] Cache expensive operations (embeddings, LLM calls)
- [ ] Batch database operations
- [ ] Use async/await for I/O
- [ ] Profile before optimizing
- [ ] Add benchmarks for critical paths

---

## Troubleshooting Development

### Issue: Import errors

```bash
# Reinstall in development mode
pip install -e ".[dev]"

# Clear cache
find . -type d -name __pycache__ -exec rm -r {} +
rm -rf .pytest_cache/
```

### Issue: Tests failing

```bash
# Run with verbose output
pytest -v -s

# Run specific test
pytest tests/test_file.py::test_name -v

# Clear database
rm -rf data/chroma/
```

### Issue: Configuration not loading

```bash
# Check .env file
cat .env

# Verify paths
python -c "from brain.config import config; print(config)"

# Test with explicit path
BRAIN_VAULT_PATH=/path/to/vault pytest
```

---

## Deployment Checklist

Before release:

- [ ] All tests passing (149/149)
- [ ] Code coverage 80%+
- [ ] No linting errors
- [ ] Documentation updated
- [ ] Type hints complete
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Release notes written

---

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest --cov=brain
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Resources

### Documentation
- [PEP 8](https://pep8.org/) - Python style guide
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework docs
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Pytest](https://docs.pytest.org/) - Testing framework

### Tools
- [Black](https://black.readthedocs.io/) - Code formatter
- [Flake8](https://flake8.pycqa.org/) - Linter
- [isort](https://pycqa.github.io/isort/) - Import sorter
- [mypy](http://mypy-lang.org/) - Type checker

### Learning
- [Real Python](https://realpython.com/) - Python tutorials
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) - FastAPI guide
- [Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html) - Pytest guide

---

## Getting Help

- **Issues**: GitHub Issues for bugs and features
- **Discussions**: GitHub Discussions for questions
- **Documentation**: See docs/ folder
- **Examples**: See WORKFLOW.md

---

## Code Review Guidelines

When reviewing code:

1. **Functionality**: Does it work as intended?
2. **Style**: Follows PEP 8 and project conventions?
3. **Tests**: Adequate test coverage?
4. **Documentation**: Clear and complete?
5. **Performance**: No obvious performance issues?
6. **Security**: No security vulnerabilities?

---

See Also:

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [COMMANDS.md](./COMMANDS.md) - CLI reference
- [API.md](./API.md) - API reference
