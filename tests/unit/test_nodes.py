"""Unit tests for the three pipeline nodes (pre_process / main / post_process).

Each node is tested in isolation via node.execute(state) and asserts the AgentStatus enum.
The core is deterministic (no live LLM). Preserves the original TC-01..TC-06 behavior at the
node level (ingest manifest, dependency report, security map, COBOL skip, README integration).
"""
import os
import tempfile

from framework.schemas.agent_status import AgentStatus

from src.nodes.main_node import MainNode
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode


def _base_state(**over):
    state = {
        "user_input": "",
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "",
        "caller_trust_level": "internal",
        "caller_id": "",
        "hitl_allowed": True,
    }
    state.update(over)
    return state


def _write(tmpdir, files):
    for fname, content in files:
        with open(os.path.join(tmpdir, fname), "w") as f:
            f.write(content)


def _run_pipeline(tmpdir, extra=None):
    """Run pre_process → main → post_process node.execute chain (deterministic, no LLM)."""
    state = _base_state(source_path=tmpdir)
    if extra:
        state.update(extra)
    pre = PreProcessNode().execute(state)
    main = MainNode().execute(_base_state(**{**state, **pre}))
    post = PostProcessNode().execute(_base_state(**{**state, **pre, **main}))
    return {**pre, **main, **post}


# --- PreProcessNode (CodebaseIngestion + S-2) ---

def test_pre_process_success_builds_manifest():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("app.py", "from flask import Flask\n"), ("README.md", "# proj\n")])
        result = PreProcessNode().execute(_base_state(source_path=tmpdir))
    assert result["status"] == AgentStatus.SUCCESS
    names = [os.path.basename(f) for f in result["file_manifest"]]
    assert "app.py" in names and "README.md" in names


def test_pre_process_empty_source_path_error():
    result = PreProcessNode().execute(_base_state(source_path=""))
    assert result["status"] == AgentStatus.ERROR
    assert result["error_log"]


def test_pre_process_s2_forbidden_path():
    # On Linux CI /etc resolves to a forbidden prefix (S-2); on other platforms it is rejected
    # as not-a-directory. Either way ingestion must error rather than walk a system path.
    result = PreProcessNode().execute(_base_state(source_path="/etc"))
    assert result["status"] == AgentStatus.ERROR
    assert result["error_log"]


def test_pre_process_max_kb_out_of_range():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = PreProcessNode().execute(_base_state(source_path=tmpdir, max_file_size_kb=0))
    assert result["status"] == AgentStatus.ERROR


def test_pre_process_cobol_skipped():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("PAYROLL.cob", "IDENTIFICATION DIVISION.\n"), ("main.py", "def m(): pass\n")])
        result = PreProcessNode().execute(_base_state(source_path=tmpdir))
    reasons = {os.path.basename(s["path"]): s["reason"] for s in result["skipped_files"]}
    assert reasons.get("PAYROLL.cob") == "COBOL:v1-skip"


# --- MainNode (security scan + dependency + summary) ---

def test_main_security_map_and_dependency():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("auth.py", "def login(password):\n    pass\n"),
                        ("requirements.txt", "pyyaml==3.13\nrequests==2.31.0\n")])
        out = _run_pipeline(tmpdir)
    auth_path = os.path.join(tmpdir, "auth.py")
    assert auth_path in out["security_module_map"]
    assert out["security_module_scan_executed"] is True
    assert len(out["dependency_report"]["deprecated_flags"]) > 0  # pyyaml 3.13


def test_main_module_summaries_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("app.py", "from flask import Flask\n"), ("models.py", "class User: pass\n")])
        out = _run_pipeline(tmpdir)
    assert os.path.join(tmpdir, "app.py") in out["module_summaries"]
    assert os.path.join(tmpdir, "models.py") in out["module_summaries"]
    assert out["status"] == AgentStatus.SUCCESS


def test_main_security_scan_not_suppressed_by_verbosity():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("auth.py", "def login(password):\n    pass\n")])
        out = _run_pipeline(tmpdir, extra={"verbosity": "low"})
    assert os.path.join(tmpdir, "auth.py") in out["security_module_map"]


# --- PostProcessNode (doc render + S-3 output safety) ---

def test_post_process_renders_doc_sections():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("auth.py", "def login(password):\n    pass\n"),
                        ("PAYROLL.cob", "IDENTIFICATION DIVISION.\n")])
        out = _run_pipeline(tmpdir)
    fo = out["final_output"]
    assert out["status"] == AgentStatus.SUCCESS
    assert "## Module Structure" in fo
    assert "## Security Modules" in fo and "auth.py" in fo
    assert "## Skipped Files" in fo


def test_post_process_readme_integrated():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write(tmpdir, [("README.md", "# My Project\n"), ("app.py", "def main(): pass\n")])
        out = _run_pipeline(tmpdir)
    assert os.path.join(tmpdir, "README.md") in out["module_summaries"]
    assert "README.md" in out["final_output"]
