# Development

How to set up a development environment for Moogo Smart Mosquito Misting Device.

## Prerequisites

- Python 3.13+ and [`uv`](https://docs.astral.sh/uv/).
- A running Home Assistant instance (Docker Compose setup available at the repo root).

## Setup

```bash
git clone https://github.com/joyfulhouse/moogo.git
cd moogo
uv sync
```

The `custom_components/moogo/` directory can be symlinked or mapped via Docker Compose
into your Home Assistant `config/custom_components/` directory for live testing.

## Quality Checks

```bash
uv run pytest          # tests
uv run ruff check      # lint
uv run ruff format     # format
uv run mypy            # type check
```

Run all of these before opening a pull request. See
[CONTRIBUTING](https://github.com/joyfulhouse/.github/blob/main/CONTRIBUTING.md)
for the contribution workflow.

## Library Dependency

The integration delegates all API communication to the
[pymoogo](https://github.com/joyfulhouse/pymoogo) library. To develop against a
local build of pymoogo, update `pyproject.toml` to point to a local path:

```toml
dependencies = [
    "pymoogo @ ../pymoogo",
]
```

## Releasing

1. Update `custom_components/moogo/manifest.json` `version`.
2. Update `pyproject.toml` `version`.
3. Update `CHANGELOG.md` — move items from `[Unreleased]` to a new version section.
4. Commit, tag (`v<version>`), and push. GitHub Actions will run validation.
