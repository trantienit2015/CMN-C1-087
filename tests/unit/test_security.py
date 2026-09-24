"""Security tests — S-1 trust gate (framework-enforced via __call__).

PreProcessNode declares required_trust_level = INTERNAL (codebase source is store-internal).
The trust gate lives in BaseNode.__call__(), so we call node(state) (NOT node.execute). The
framework normalizes status to its string value after the gate.
"""
import os
import tempfile

from framework.schemas.trust_level import TrustLevel

from src.nodes.pre_process_node import PreProcessNode


def _state(trust, source_path):
    return {
        "user_input": "",
        "source_path": source_path,
        "correlation_id": "x",
        "session_id": "x",
        "thread_id": "x",
        "trace_id": "",
        "caller_trust_level": trust,
        "caller_id": "",
        "hitl_allowed": True,
    }


def test_trust_gate_blocks_anonymous():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = PreProcessNode()(_state(TrustLevel.ANONYMOUS.value, tmpdir))
    assert result["status"] == "error"


def test_trust_gate_blocks_verified_external():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = PreProcessNode()(_state(TrustLevel.VERIFIED_EXTERNAL.value, tmpdir))
    assert result["status"] == "error"


def test_trust_gate_allows_internal():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "app.py"), "w") as f:
            f.write("def main(): pass\n")
        result = PreProcessNode()(_state(TrustLevel.INTERNAL.value, tmpdir))
    assert result["status"] == "success"


def test_required_trust_level_is_valid_enum():
    # criterion #13 — must be one of the three valid enum values.
    assert PreProcessNode.required_trust_level in (
        TrustLevel.ANONYMOUS,
        TrustLevel.VERIFIED_EXTERNAL,
        TrustLevel.INTERNAL,
    )
