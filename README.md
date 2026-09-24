# CMN-C1-087 — Codebase & Technical Documentation Onboarding Summary Agent

> **Category**: Cat 1 (delivers a single technical capability in a generic, use-case-agnostic way)
> **Industry**: CMN

## Overview

Produces a Markdown onboarding guide for a source code repository. The input is plain text: the
path of a directory that the agent process can read. The request is rejected when the path is
empty, resolves to a system location such as /etc, /proc, /sys or /root, or is not a directory;
an optional per-file size limit must be between 1 and 10000 KB (default 500 KB). The entry node
requires an internal-level caller.

The agent walks the directory (top level and one level of subfolders) and collects Python,
Java, JavaScript, TypeScript and documentation files plus common entry-point files. Archives,
oversized files and COBOL files are listed as skipped. It then scans every collected file for
security-sensitive keywords (auth, password, payment, token, crypto and similar), parses
dependency manifests (requirements.txt, pom.xml, package.json, Gemfile, go.mod) and flags a
short built-in list of known-deprecated packages, and writes a per-file summary. The guide
contains an AI-generated disclaimer, module structure, dependencies and flagged packages, a
security modules section that is always present, contribution notes and the skipped files.
Credential-like strings in the guide are redacted; if prompt-injection markers or credential
patterns remain, the whole guide is replaced by a notice and an error status is returned.

A language model is optional. A client passed through the graph configuration is asked to
summarise each file; if no client is given, or a call fails, each file receives a fixed
placeholder summary instead. The bundled HTTP entry point does not pass a client, so it always
uses the placeholder. No knowledge base is used.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
