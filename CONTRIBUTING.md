# Contributing to Argus

Thanks for improving Argus. The project favors small, readable changes with
tests over broad rewrites.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the checks before opening a pull request:

```bash
python -m unittest discover -s tests -v
ruff check argus tests
python -m compileall -q argus
```

## Safety invariants

These are not optional:

- Tests must be deterministic and offline. Never use a real API key or call a
  live model in the test suite.
- New shell deny patterns need a blocked case, a near-miss allowed case, and a
  test for both.
- Filesystem tools must stay inside the workspace. Do not add a tool that can
  read or write `.env`, `.git`, or `.argus`.
- Headless runs must not auto-approve mutating tools. `--yes` and
  `--mode yolo` are explicit opt-ins.
- Do not print, log, commit, or include environment secrets in fixtures.
  `.env` is ignored and must remain so.
- Jev or any future classifier must fail closed: unavailable, malformed, or
  low-confidence decisions must not authorize an action.

If a security issue is involved, report it privately per
[SECURITY.md](SECURITY.md) instead of opening a public pull request.

## Code conventions

- Python 3.10+ standard library only at runtime. Do not add a dependency
  without a strong reason and prior discussion.
- Keep modules small and boundaries explicit. Prefer a direct function over a
  new abstraction.
- Use type hints where they clarify a contract. No comments that restate the
  code; explain constraints and non-obvious reasons only.
- All provider-specific wire formats belong in `argus/providers/`.
- New CLI strings must be added to every language in `argus/i18n.py`.
- Preserve the neutral message format and the `Provider.complete` contract.

## Adding a provider

1. Subclass `Provider` in `argus/providers/`.
2. Set `name`, `default_model`, environment variable groups, and whether a key
   is required.
3. Implement `to_wire` and `parse` as static methods where practical.
4. Normalize usage into `usage_dict`.
5. Handle provider-specific safety blocks and malformed responses with
   `ProviderError`.
6. Register the class and any aliases in `argus/providers/__init__.py`.
7. Add adapter tests with a fake transport. Do not use network access.

## Pull requests

- Keep the change focused; separate refactors from behavior changes.
- Describe the problem, the approach, and how it was verified.
- Include tests for behavior changes and update user-facing docs when
  commands, flags, or configuration change.
- CI must pass on Python 3.10, 3.11, 3.12, and 3.13.

## Releasing

Maintainers release from `main`:

1. Update `__version__` in `argus/__init__.py`.
2. Move the changelog entries in `CHANGELOG.md` from `Unreleased` to the new
   version with the release date.
3. Run tests, lint, and `python -m build` locally.
4. Tag the commit (`vX.Y.Z`) and publish a GitHub Release.
5. The release workflow builds the sdist/wheel, attaches them to the release,
   and publishes the container image to GHCR.

PyPI publishing is not configured yet. If it is added later, configure
`argus-harness` as a trusted publisher on PyPI for this repository, workflow
`release.yml`, and environment `pypi`. No long-lived PyPI token belongs in
repository secrets.
