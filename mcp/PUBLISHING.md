# Publishing `agent-mail-mcp` to PyPI

Once published, users can install the MCP server with a single command:

```bash
pipx install agent-mail-mcp     # or: uv tool install agent-mail-mcp
```

and reference `agent-mail-mcp` as the `command` in their MCP client config.

## Release steps (maintainers)

1. Bump `version` in `pyproject.toml`.
2. Build the distributions:
   ```bash
   cd mcp
   python -m pip install --upgrade build twine
   python -m build            # creates dist/*.whl and dist/*.tar.gz
   ```
3. (Recommended) Upload to TestPyPI first and verify install:
   ```bash
   python -m twine upload --repository testpypi dist/*
   pipx install --pip-args="--index-url https://test.pypi.org/simple/" agent-mail-mcp
   ```
4. Upload to PyPI:
   ```bash
   python -m twine upload dist/*
   ```

Prefer a [PyPI Trusted Publisher](https://docs.pypi.org/trusted-publishers/) (OIDC from
GitHub Actions) over a long-lived API token so no secret needs to live in the repo.

## Versioning

Pre-1.0; follow semver once the API stabilizes. Keep the version in step with notable
backend API changes that affect the tools.
