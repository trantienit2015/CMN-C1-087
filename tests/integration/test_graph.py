"""Integration test — full graph compile() + invoke() (Cat 1 backbone).

Drives the whole pipeline (initialize → pre_process → main → post_process → finalize) with
INTERNAL trust (pre_process requires it). Deterministic core — no live LLM. The source path is
passed as the agent's user_input (pre_process reads source_path or falls back to user_input).
"""
import os
import tempfile

import pytest

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from framework.secrets.context import bound_secrets
from shared.secrets.inmemory_provider import InMemoryProvider

from src.graph.graph import CodebaseOnboardingSummaryAgent


def _internal_ctx():
    return InvocationContext(
        correlation_id="it-corr",
        session_id="it-session",
        thread_id="it-thread",
        parent_trace_id="",
        caller_id="dev-ops",
        caller_trust_level=TrustLevel.INTERNAL,
        secrets=InMemoryProvider({}),
        hitl_allowed=True,
    )


@pytest.fixture
def agent():
    a = CodebaseOnboardingSummaryAgent(config={"max_retry": 1})
    a.compile()
    return a


def test_full_pipeline_success(agent):
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname, content in [
            ("app.py", "from flask import Flask\n"),
            ("auth.py", "def login(password):\n    pass\n"),
            ("requirements.txt", "pyyaml==3.13\n"),
        ]:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(content)
        with bound_secrets(InMemoryProvider({})):
            result = agent.invoke(tmpdir, ctx=_internal_ctx())
    assert result["status"] == "success"
    assert result["output"] is not None
    assert "## Security Modules" in result["output"]["report"]
    assert "MainNode" in result["node_history"]


def test_full_pipeline_error_on_missing_source(agent):
    with bound_secrets(InMemoryProvider({})):
        result = agent.invoke("", ctx=_internal_ctx())
    assert result["status"] in ("error", "cancelled")
