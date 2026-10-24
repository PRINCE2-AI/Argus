# Argus — Portfolio Notes

Use this document to present Argus on a resume, in a portfolio, and in
interviews. The emphasis is on decisions and evidence, not feature lists.

## Links

- Live site: <https://argus-harness-oa3gk1gz2f0.qoder.website>
- Documentation: <https://argus-harness-oa3gk1gz2f0.qoder.website/docs.html>
- Source: <https://github.com/PRINCE2-AI/Argus>

## One-line pitch

Built a zero-dependency Python AI agent harness that unifies six model providers
behind durable sessions and a layered safety policy, with offline tests, CI, and
container and PyPI release pipelines.

## Resume bullets

Pick three or four based on the role.

- **Designed a provider-neutral agent harness** in Python with adapters for
  Gemini, Anthropic, OpenAI, OpenRouter, Groq, and local Ollama; handled
  provider-specific tool-call IDs, Gemini thought signatures, Anthropic content
  blocks, and reasoning-model parameter differences behind one tested contract.
- **Built crash-tolerant JSONL session storage** that tolerates torn writes,
  repairs tool calls interrupted by a restart, restores compaction summaries,
  and prevents duplicate message persistence — backed by a fully offline test
  suite of 102 tests.
- **Hardened model-generated tool execution** with a path jail, deterministic
  shell deny list, explicit approval modes, output redaction, sanitized
  subprocess environments, and fail-closed semantic review; added regression
  tests for parent-directory escapes and protected-file access.
- **Shipped a production-style open-source workflow**: Python 3.10–3.13 CI
  matrix, linting, wheel/sdist validation and install smoke tests, PyPI trusted
  publishing, GHCR container release, security and contribution policies, and
  documentation translated into Spanish, Hindi, and French.
- **Internationalized the product** with English, Spanish, Hindi, and French CLI
  strings, locale detection, translated READMEs, and key-parity tests across all
  language dictionaries.

## At a glance

| Metric | Value |
| --- | --- |
| Language | Python 3.10+ |
| Runtime dependencies | 0 |
| Model providers | 6 |
| Interface languages | 4 |
| Offline tests | 102 |
| CI versions | 3.10, 3.11, 3.12, 3.13 |
| Session format | Append-only JSONL with repair on load |
| Safety modes | `read-only`, `safe` (default), `yolo` |
| Packaging | `argus-harness` wheel/sdist, `argus` console script |
| Delivery | GitHub Actions, PyPI trusted publishing, GHCR image |

## What makes the project technically interesting

### Provider abstraction without leaking vendor details

The loop, tools, sessions, and policy operate on one neutral message format. The
hard parts are not the HTTP calls; they are the invariants between vendors:

- OpenAI requires `tool_call_id` on tool results and JSON-encoded arguments.
- Anthropic expects `tool_use` and `tool_result` content blocks, and consecutive
  results must be merged into one user turn.
- Gemini names tool results `functionResponse`, uses model-specific roles, and
  Gemini 3 requires thought signatures to round-trip.
- Reasoning models reject `temperature` and use `max_completion_tokens`.

Each adapter owns those details and normalizes usage into the same dictionary.
The test suite verifies translation and parsing with fake transports, so no
credentials or network are needed.

### Session durability

The storage layer is intentionally boring: one JSON object per line, appended
as work happens. The interesting engineering is in recovery:

- A partially written final line is ignored.
- Adjacent duplicate tool rows from an older persistence bug are removed.
- Loading slices history at the latest compaction marker.
- Orphaned tool results are dropped.
- Unanswered tool calls from a crashed process are filled with an explicit error
  result, paired by call ID or position.

This turns a crash from “the session is corrupted” into “resume and continue.”

### Safety as layered, testable code

The policy is not a prompt instruction; it is a code path every tool call goes
through. The layers are:

1. Mode policy and interactive approval.
2. Deterministic deny patterns that apply even in `yolo`.
3. Realpath-based workspace confinement and protected paths.
4. Headless denial by default, with explicit `--yes` opt-in.
5. Optional semantic review that fails closed.
6. Secret redaction and sanitized subprocess environments.

The project documents that this is not an OS sandbox. That honesty matters:
safety claims should match the actual boundary.

### Open-source delivery as an engineering signal

The repository is set up the way a maintained project should be:

- CI on four Python versions, plus lint and package jobs.
- A wheel installed outside the source tree and smoke-tested in CI.
- PyPI trusted publishing with no long-lived token.
- Container publishing to GHCR on release.
- `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT`, `CHANGELOG`, `.env.example`.
- Tests that are deterministic, offline, and credential-free.

## Two debugging stories to tell

### 1. The duplicate tool rows

Real session files contained the same tool result twice. The original writer
recorded the tool message on `tool_end`, then a generic recorder wrote it again
because its cursor had not advanced. The fix moved the append into the loop
before the event and made the harness advance a single cursor for every recorded
message.

The important part is how it was found: inspect real artifacts, not just unit
behavior. Regression tests now assert exactly one tool row is persisted.

### 2. The shell escape and the localhost key

Two boundary bugs surfaced during review:

- `cd .. && rm -rf neighbor` did not match the original destructive-removal
  pattern. The fix added explicit parent/absolute `cd` and `pushd` denial, plus
  `rm` traversal and `.git`/`.argus` protections.
- The Ollama adapter inherited `ARGUS_API_KEY` from the generic fallback and
  would send a cloud credential to `localhost`. The fix removed that fallback
  for Ollama and added a test asserting the key is not used.

Both are good examples of treating the model as untrusted input, not as a
well-behaved caller.

## 90-second demo script

```bash
# 1. Show the shape of the project
ls argus argus/providers tests

# 2. Run the offline suite
python -m unittest discover -s tests -v

# 3. Start interactively in read-only mode
argus --mode read-only

# 4. Inspect safety and sessions
/mode safe
/session
/tokens
/exit

# 5. Show CI, release, and packaging
cat .github/workflows/ci.yml
cat pyproject.toml
```

Then open a saved session JSONL and point out the compact, append-only format.
Finish with the architecture diagram in `docs/ARCHITECTURE.md`.

## Interview talking points

**Why no framework?**
The goal was to understand and control every boundary: message format, tool
execution, approval, persistence, and recovery. A framework would hide exactly
the parts this project is meant to demonstrate.

**Why JSONL instead of SQLite?**
Sessions are append-heavy, human-inspectable, and workspace-local. JSONL makes
every step visible and recovery simple; SQLite would add schema and connection
handling without solving a current problem. Compaction is a file-level concern.

**Why is compaction character-based?**
It is provider-agnostic and cheap. The tradeoff is accuracy; a provider-specific
tokenizer is on the roadmap. The important property is that summaries are
persisted and marked so restore semantics are correct.

**What is the biggest remaining risk?**
Shell semantics. Pattern matching cannot perfectly model a shell, so the policy
reduces accidents but does not contain hostile code. The documented answer is a
container or VM for untrusted work, which is also how the Docker image is
intended to be used.

**How do you test an agent without calling a model?**
Inject a provider. The loop and harness depend on a small contract; a scripted
provider returns deterministic replies and records requests, so tests assert
tool execution, persistence, compaction, and repair without network access.

## Skills demonstrated

Python · API design · adapter pattern · concurrency · filesystem safety ·
subprocess isolation · JSONL persistence and recovery · prompt-injection
posture · i18n · testing · GitHub Actions · packaging · Docker · technical
writing.

## Where to put it on a resume

- **Projects:** two bullets focused on architecture and one measurable outcome
  (e.g. six providers, 102 offline tests, four Python versions in CI).
- **Experience:** a bullet about designing a safety boundary for
  model-generated tool execution and backing it with regression tests.
- **Skills:** Python, LLM tool calling, agent architecture, GitHub Actions,
  Docker, PyPI packaging, i18n.

Avoid claiming production users or scale that the project does not have. The
strength here is depth, correctness, and delivery discipline.
