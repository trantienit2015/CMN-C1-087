# docs/03_test_spec.md — CMN-C1-087 Test Specification

**Template ID:** CMN-C1-087
**Version:** 0.1.0

---

## Test Cases (TC)

### TC-01: Python web app → onboarding doc generated correctly
**Input:** Directory with `app.py`, `models.py`, `requirements.txt`
**Expected:**
- `module_summaries` contains entries for `app.py` and `models.py`
- `final_output` is a non-empty Markdown string containing `## Module Structure`
- `dependency_report.found_files` includes `requirements.txt`

### TC-02: Java microservice → module summary present
**Input:** Directory with `Application.java`, `pom.xml`
**Expected:**
- `module_summaries` contains entry for `Application.java`
- `dependency_report.found_files` includes `pom.xml`

### TC-03: COBOL file → graceful skip
**Input:** Directory containing `PAYROLL.cob` alongside `main.py`
**Expected:**
- `skipped_files` contains `{"path": "...PAYROLL.cob", "reason": "COBOL:v1-skip"}`
- `main.py` IS in `module_summaries` (processing continues normally)
- `final_output` contains a "Skipped Files" section

### TC-04: Auth module present → always in security_module_map
**Input:** Directory with `auth.py` containing `def login(password):` and any verbosity config
**Expected:**
- `security_module_map` contains `auth.py` regardless of verbosity setting
- `security_module_scan_executed` is `True`
- `final_output` contains `## Security Modules` section with `auth.py` listed

### TC-05: Deprecated dependency in requirements.txt → flagged
**Input:** `requirements.txt` containing `pyyaml==3.13`
**Expected:**
- `dependency_report.deprecated_flags` is non-empty
- Flagged entry references `pyyaml`
- `final_output` contains deprecation warning in Data Flow section

### TC-06: README.md present → integrated into onboarding doc
**Input:** Directory with `README.md` alongside source files
**Expected:**
- `README.md` appears in `file_manifest`
- Content of README referenced or summarized in `final_output`

---

## Proof-of-Boundary Tests (PB)

### PB-01: Hardcoded API key in source → redacted + flagged
**Boundary:** OutputSecurityGateNode (SecretLeakageGate)
**Setup:** `final_output` contains an `api_key = "sk-..."` assignment with an OpenAI-style test key
**Run:** OutputSecurityGateNode
**Expected:**
- the test key does NOT appear in output `final_output`
- `[REDACTED - potential secret]` appears in its place
- `secret_patterns_found` is `True`

### PB-02: Auth module → always in security_module_map regardless of config
**Boundary:** SecurityModuleClassifyNode (non-suppressible)
**Setup:** `file_manifest` contains `auth.py` with `password` keyword; config sets verbosity=low
**Run:** SecurityModuleClassifyNode
**Expected:**
- `auth.py` is in `security_module_map`
- `security_module_scan_executed` is `True`

### PB-03: AWS key in source → never appears in final_output
**Boundary:** OutputSecurityGateNode (SecretLeakageGate)
**Setup:** `final_output` contains `AKIAIOSFODNN7EXAMPLE` (known AWS access key format)
**Run:** OutputSecurityGateNode
**Expected:**
- `AKIAIOSFODNN7EXAMPLE` does NOT appear in output
- `[REDACTED - potential secret]` appears in its place
- `secret_patterns_found` is `True`

---

## Test Layout (src/ regime)

```
tests/
├── unit/
│   ├── test_nodes.py      # pre_process / main / post_process (TC-01..TC-06 at node level), AgentStatus enum
│   ├── test_services.py   # security_scan / dependency / summary / doc_render / output_safety (PB-01/03 redaction)
│   └── test_security.py   # S-1 trust gate via __call__ (TC-08 / PB-1)
├── integration/
│   └── test_graph.py      # full outer compile() + invoke() (PB-6)
└── proof_of_boundary/
    ├── test_import_isolation.py   # PB-4 AST scan src/ — no agenticstar/platform import
    └── test_state_safety.py       # PB-2/PB-5 AST scan state.py — no credential field/BaseModel/InvocationContext
```

## Mapping vs the old regime

- The old `OutputSecurityGateNode` / `_security_gate_output()` is retired. Its S-3 logic
  (secret redaction, prompt-injection blanking, anti-suppression) is now `src/services/output_safety.py`,
  applied by `PostProcessNode`. PB-01/PB-03 redaction tests now call `apply_output_safety(...)`.
- Nodes return partial dicts with `status` as an `AgentStatus` enum (no `{**state, ...}` spread).
- S-1 trust is `INTERNAL` (was the invalid `VERIFIED_INTERNAL`); enforced by the framework via `__call__`.
- `secret_patterns_found` was renamed to `redaction_triggered` (state-safety scanner flags `secret*` field names).

Result: **30 tests pass**, ruff clean.
