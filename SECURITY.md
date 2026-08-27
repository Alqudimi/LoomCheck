# Security Policy

## Supported versions

Only the latest commit on `main` is currently supported because LoomCheck is in alpha. Once tagged releases exist, the latest minor release will receive security fixes.

## Scope and security boundary

LoomCheck is a local developer tool with no network behavior, service listener, or telemetry. The CLI intentionally imports and executes the target specified by the user; it is not a sandbox and must not be used to run untrusted scenarios. Reports can contain exception messages, labels, and schedules, which may be sensitive.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability. Use GitHub's private security advisory workflow for `Alqudimi/LoomCheck`, or contact the maintainer through the private channel listed on the GitHub profile. Include a minimal reproduction, affected version/commit, impact, and a suggested mitigation when available.

We will acknowledge a report when practical, validate the reproduction, coordinate a fix and disclosure timeline, and credit the reporter if they consent. Never include real credentials, tokens, or private production traces in a report.

## Secure development

The repository uses dependency review in CI, pinned action major versions, secret scanning where available, static checks, and regression tests for input validation and failure handling. JSON schedules are parsed as data; the project does not deserialize executable objects or execute shell commands.
