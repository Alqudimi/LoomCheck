# Decision record: why LoomCheck

## Context

The account already contains projects for Git workflows, project templates, ML tooling, document workflows, cryptography, MCP diagnostics, contract drift, policy gateways, provenance, replay, code-review impact, and release readiness. A new project that repeats those surfaces would add volume but not meaningful engineering breadth.

The selected opportunity is deterministic testing of cooperative asynchronous workflows. Python developers can run async tests, but a failing interleaving is still difficult to reproduce. The closest direct reference, Blanket, focuses on deterministic multithreaded primitives; Trio's long-running issue about scheduler-dependent heisenbugs describes the need for controlled schedule exploration and reduction. LoomCheck addresses the asyncio/cooperative side with a small, explicit instrumentation contract.

## Decision

Build LoomCheck as a standard-library Python package with a CLI. The MVP will support named tasks, explicit checkpoints, deterministic schedule prefixes, bounded exploration, greedy witness shrinking, and JSON/Markdown reports. It will not attempt transparent bytecode instrumentation, network virtualization, or a hosted dashboard.

## Alternatives considered

| Alternative | Why it was not selected |
|---|---|
| AI agent observability platform | The space is already crowded by Phoenix, LangSmith, Langfuse, Braintrust, Opik, and others, while the account already has several provenance/replay/agent-safety projects. |
| Data/API contract sentinel | Valuable, but it overlaps the existing DriftFence project. |
| Build/release evidence tool | Valuable, but it overlaps Shipwright and ReproLedger. |
| General event-workflow simulator | High learning value, but the problem statement is broader and the first user benefit is less immediate than a deterministic async test witness. |
| Thread scheduler clone | Blanket is a direct, active reference and the problem would repeat its multithreaded scope. |

## Consequences

The explicit checkpoint contract makes the tool honest and portable, but users must instrument meaningful boundaries. Bounded search is understandable and CI-safe, but it is not proof of race freedom. A standard-library core minimizes supply-chain risk and makes installation easy, while adapters and pytest integration remain future extension points.

## Status

Accepted for the 0.1.0 MVP.
