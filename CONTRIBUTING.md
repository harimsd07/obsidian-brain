# Contributing to Obsidian Brain

Thanks for your interest in contributing. Here's how to get started.

---

## Setup

```bash
git clone https://github.com/harimsd07/obsidian-brain
cd obsidian-brain
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest                        # run all tests
pytest tests/test_chunker.py  # run specific file
pytest -v --tb=short          # verbose output
```

Tests are fully mocked — no Ollama or API keys needed to run them.

## Project structure

- `brain/` — all source code
- `brain/commands/` — CLI subcommands (one file per command)
- `tests/` — pytest tests mirroring source structure

## Adding a new command

1. Create `brain/commands/your_command.py` with a `run_your_command()` function
2. Add a new `@app.command()` in `brain/cli.py` that calls it
3. Wrap with `try/except BrainError` for error handling
4. Add tests in `tests/test_your_command.py`

## Error handling

Always raise from `brain/exceptions.py` — never let raw tracebacks reach the user.

```python
from brain.exceptions import VaultNotFound
raise VaultNotFound(str(vault_path))
```

## Pull request checklist

- [ ] Tests pass (`pytest`)
- [ ] New code has corresponding tests
- [ ] No API keys or secrets in code
- [ ] `.env` is in `.gitignore`
- [ ] Error messages are human-readable
