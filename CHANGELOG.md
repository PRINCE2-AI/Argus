# Changelog

All notable changes to Argus are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-25

The first public, package-ready release. Argus remains a small harness, but its
boundaries are now tested and explicit.

### Added

- Provider abstraction with Gemini, OpenAI-compatible, OpenRouter, Groq,
  Ollama, and Anthropic adapters behind one neutral message format.
- Provider registry with aliases, model-based inference, and environment-based
  configuration.
- Offline test suite with a scripted provider covering tools, policy, sessions,
  compaction, the harness, providers, i18n, memory, skills, and fleets.
- CLI internationalization for English, Spanish, Hindi, and French, with
  `--lang`, `ARGUS_LANG`, and locale detection.
- Translated READMEs and architecture and portfolio documentation.
- `pyproject.toml`, console script `argus`, `argus-harness` distribution
  metadata, and standard-library typing throughout.
- GitHub Actions CI across Python 3.10–3.13 with lint and distribution checks.
- Release workflow with PyPI trusted publishing, GHCR container publishing, and
  release artifact attachment.
- Dockerfile and `.dockerignore`.
- `--list-sessions`, `--session`, `--provider`, `--base-url`, `--lang`,
  `--max-turns`, `--budget-tokens`, `--workers`, and `--version` CLI options.
- Interactive `/mode`, `/session`, `/tokens`, and `/lang` commands.
- Usage accounting on the harness and `/tokens`.
- Typed tool schemas via dictionary parameters in `@tool`.
- Session compaction markers so resumed sessions reload compacted history.
- CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, CHANGELOG, and `.env.example`.

### Changed

- The default safety mode is `safe` for both the CLI and `Harness`.
- Headless safe mode denies mutating tools unless `--yes` is passed.
- `Harness` accepts an injected `Provider` instance and records one copy of
  each message.
- Compaction summaries are persisted and marked; history is sliced on load.
- `list_files` defaults to `**` and includes root-level files.
- `write_file` and `edit_file` use atomic replacement.
- Subprocesses run with secret-named environment variables removed.
- README rewritten with provider matrix, architecture diagram, CLI reference,
  safety model, and deployment instructions.

### Fixed

- Duplicate tool-result rows in persisted sessions.
- Session repair pairing tool results with call IDs after a crash.
- Parent-directory shell escapes such as `cd .. && rm -rf neighbor`.
- Reads of `.env` and writes/removal targeting `.git` or `.argus`.
- Over-broad `.env` deny pattern that blocked `cp .env.example .env`.
- `edit_file` leaving a partially written file on failure.
- Ollama inheriting and sending the global cloud `ARGUS_API_KEY` to localhost.
- Normalization of malformed OpenAI tool arguments.
- Gemini safety blocks and Anthropic error payloads now raise clear provider
  errors.

### Security

- Expanded deterministic deny patterns for destructive shell operations,
  privilege escalation, reverse shells, metadata access, and forced Git
  operations.
- Path jail checks on every filesystem tool, including protected names and
  prefixes.
- Output redaction for common key formats and environment secret values.
- Optional Jev semantic review fails closed when unavailable or uncertain.
- Memory and skill content is wrapped and explicitly treated as untrusted
  reference data.

## [0.1.0] - 2026-09-26

Internal day-by-day implementation: provider boundary, tool loop, workspace
tools, safety policy, compaction, memory, skills, sessions, sub-agents, CLI, and
parallel fleets. Not published as a package.
