# IonForge

Open-source charged particle optics toolkit.

## Installation

```bash
uv add ionforge
```

For STL mesh support:

```bash
uv add "ionforge[stl]"
```

## Development

```bash
uv sync --extra dev --extra stl
uv run pytest
uv run ruff check .
uv run pyright
```
