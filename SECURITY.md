# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| Earlier | No |

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository
(**Security** tab → **Report a vulnerability**). Do not open a public issue for
a security problem and do not include API keys, session logs, or `.env`
contents in any report.

Include, when possible:

- The affected version and Python version.
- A minimal reproduction or the relevant tool/policy call.
- Whether the issue crosses the workspace boundary, executes commands, leaks a
  secret, or bypasses the approval flow.
- Any known mitigations.

You can expect an initial acknowledgement on a best-effort basis, followed by a
coordinated fix and disclosure. Please give the maintainers reasonable time to
release a fix before publishing details.

## Scope

Argus is an agent harness, not an operating system sandbox. The safety policy
reduces accidental damage from model-generated commands; it is not designed to
contain hostile code or a compromised model. For untrusted tasks, run Argus in a
container or virtual machine with only the required workspace mounted.

Reports are especially valuable when they demonstrate:

- A path escape from the workspace through `read_file`, `write_file`,
  `edit_file`, `list_files`, or `grep`.
- A shell command that reads or modifies `.env`, `.git`, `.argus`, or files
  outside the workspace despite the deny patterns.
- A way to bypass the `safe`/`read-only` policy or obtain approval silently in
  headless mode.
- Secret exposure in tool output, subprocess environments, session files, or
  provider requests. Note that the Ollama adapter intentionally does not read
  `ARGUS_API_KEY`.
- Prompt injection in project memory or skills that causes tool misuse.

## Secret handling

- `.env` and `.env.*` are ignored by Git (except `.env.example`) and protected
  from workspace tools.
- Tool output is redacted for common credential formats and for values of
  secret-named environment variables.
- Shell tools receive a sanitized environment with secret-named variables
  removed.
- Redaction is best-effort defense in depth, not a guarantee. Never place
  secrets in prompts, issues, screenshots, or generated files.
