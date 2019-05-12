# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| latest release on `main` | yes |
| older tags | best effort |

## Reporting a vulnerability

EvalLeak processes manifests supplied by the user and writes reports to
stdout or a file. It performs no network I/O and executes no downloaded
code, so the attack surface is narrow - malformed manifests are the main
concern (path traversal in output paths, extreme allocations from
pathological inputs).

Email security concerns to the maintainer rather than opening a public
issue. Please include a minimal crashing manifest and the version tag.
Fixes are released in the next patch release and credited in CHANGELOG.md.