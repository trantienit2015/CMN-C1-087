# docs/02_design.md — CMN-C1-087 Design Specification

**Template ID:** CMN-C1-087
**L1 Base:** `AgentBaseGraph` (L1 direct — the graph class IS the agent)
**Category:** Cat 1 (single capability: codebase onboarding document generation)
**Pattern:** Fixed 3-slot backbone (pre_process / main / post_process)

---

## 1. Architecture

The graph class `CodebaseOnboardingSummaryAgent(AgentBaseGraph)` IS the agent — no separate
agent class, no double-graph, no `_invoke_impl`, no `.run()`. The framework owns the fixed
backbone `initialize → pre_process → main → post_process → finalize` and the 5-layer security
model. Public entry: `Graph(config).compile()` then `.invoke(user_input, ctx=...)`.

The five business steps map onto the three author slots:

```
pre_process : CodebaseIngestion (+ S-2 path guard)
main        : SecurityModuleClassify (non-suppressible) → DependencyAnalysis → ModuleSummary
post_process: OnboardingDocGeneration → S-3 output safety (redaction / injection / anti-suppression)
```

Deterministic logic lives in `src/services/` (auditable, independently testable); an optional
LLM (injected via config, secret bound at the entry point) only narrates module summaries.

---

## 2. State Schema (`src/schemas/state.py`)

`class CMN_C1_087_State(AgentState)` — flat TypedDict extending `AgentState`. Agent-specific
fields: `source_path`, `output_doc_path`, `max_file_size_kb`, `file_manifest`, `skipped_files`,
`security_module_map`, `security_module_scan_executed`, `dependency_report`, `module_summaries`,
`final_output`, `redaction_triggered`. Output is surfaced via `formatted_output`. No Pydantic,
no dataclass, no credentials, no `InvocationContext` in state.

---

## 3. Node / service responsibilities

### 3-1. pre_process — `PreProcessNode` (CodebaseIngestion + S-2)
- S-1: `required_trust_level = INTERNAL` (codebase source is store-internal).
- S-2 path guard (inline): `os.path.realpath`, reject forbidden prefixes (`/etc`,`/proc`,`/sys`,`/root`),
  bound `max_file_size_kb` (1–10000). Returns `status=ERROR` on violation.
- Traverses top-level + one level deep; rejects archives; skips oversized + COBOL files
  (`skipped_files` with reason); builds `file_manifest` (known languages + entry points + docs).

### 3-2. main — `MainNode`
- `src/services/security_scan.py::classify_security_modules` — NON-SUPPRESSIBLE keyword scan
  (auth/login/password/payment/credit_card/pii/encrypt/decrypt/crypto/session/jwt/token/oauth).
  `security_module_scan_executed=True` is always set (anti-suppression invariant).
- `src/services/dependency.py::analyze_dependencies` — parse requirements.txt / pom.xml /
  package.json / Gemfile / go.mod; flag known-deprecated packages.
- `src/services/summary.py::summarize_modules` — per-file isolated summary (optional LLM,
  deterministic fallback "mock summary output"); COBOL + already-skipped files excluded.
- Guards a pre_process failure (no manifest) → `status=ERROR` (the backbone always routes
  pre_process → main).

### 3-3. post_process — `PostProcessNode` (OnboardingDocGeneration + S-3)
- `src/services/doc_render.py::render_onboarding_doc` — assemble Markdown: non-suppressible AI
  disclaimer, Module Structure, Data Flow & Dependencies, Security Modules (always), How to
  Contribute, Skipped Files.
- `src/services/output_safety.py::apply_output_safety` — S-3 content gate (ordinary node logic,
  NOT a developer `_security_gate_*` method): anti-suppression assertion
  (`security_module_scan_executed` must be True), secret-leakage redaction
  (`[REDACTED - potential secret]`), prompt-injection / credential-marker blanking. Sets
  `redaction_triggered`; returns `status=ERROR` + `error_log` on a hard violation.

---

## 4. Security (framework-enforced 5-layer)

| Layer | Handling |
|---|---|
| S-1 Trust gate | `PreProcessNode.required_trust_level = INTERNAL`; agent-level `required_trust_level: INTERNAL` in `config/agent.yaml`. Enforced in `BaseNode.__call__()`. |
| S-2 Path guard | Inline in `pre_process` (realpath + forbidden prefixes + size bound). |
| S-3 Output safety | `src/services/output_safety.py`, called by `post_process` (no `_security_gate_*` method). |
| S-4 Audit | `emit_trace_event(event_type, payload, state)` in each side-effecting node. |
| S-5 Credential scan | Import-time framework scan; no credentials in source/state. |

There are no developer `__pre_invoke__` / `_security_gate_input` / `_security_gate_output`
methods and no separate agent class — those were retired with the old regime.

---

## 5. Config (`config/agent.yaml`)

Single manifest: `agent.{id: CMN-C1-087, name: CodebaseOnboardingSummaryAgent, version, category:
"Cat 1", industry: CMN, base_type: DocGenerationAgent, module: "src.graph", class:
CodebaseOnboardingSummaryAgent, config.{max_retry: 2, timeout_seconds: 30}, required_trust_level:
INTERNAL}`. Domain knobs (`max_file_size_kb`) default in the nodes/services. No separate config.yaml.

---

## 6. COBOL handling (v1)

`.cob` / `.cbl` files are added to `skipped_files` (reason `"COBOL:v1-skip"`) at ingestion and
excluded from summarization; noted under "Skipped Files" in the final document.
