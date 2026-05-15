# Project Instructions

- Follow Conventional Commits for all commits.
- Keep the Home Assistant integration aligned with current HA custom integration best practices.
- Use `uv` for Python dependency management and command execution.
- Before committing code changes, run `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest -q`.
- Add or update tests for every integration behavior change.
- Keep the integration domain `smd_d_keys`; do not rename it to older PoC names.
- Use the local Docker Compose Home Assistant setup for manual verification when useful, and do not commit `.local/`.
- Keep product/API contracts in `docs/superpowers/specs/` or `docs/research/`, not in this file.
- Do not commit credentials, captured tokens, APK artifacts, or other sensitive reverse-engineering material.
- Remove temporary sensitive debug logging before committing.
