"""OnboardingDocGeneration (post_process) — render the doc + apply S-3 output safety.

Assembles the final Markdown onboarding document, then applies the S-3 content gate (relocated
from the old agent-class `_security_gate_output`): anti-suppression check, secret-leakage
redaction, and prompt-injection / credential-marker blanking. Produces `formatted_output`
(returned by the graph as `output`). Node contract: execute(self, state) -> dict; status enum.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import CMN_C1_087_State
from src.services.doc_render import render_onboarding_doc
from src.services.output_safety import apply_output_safety


class PostProcessNode(FunctionNode):
    # S-1: outer backbone node - matches the manifest trust level (config/agent.yaml).
    required_trust_level = TrustLevel.INTERNAL

    def execute(self, state: CMN_C1_087_State) -> dict[str, Any]:
        final_output = render_onboarding_doc(
            module_summaries=state.get("module_summaries", {}),
            security_module_map=state.get("security_module_map", {}),
            dependency_report=state.get("dependency_report", {}),
            skipped_files=state.get("skipped_files", []),
            source_path=state.get("source_path", ""),
        )

        # S-3 output safety (anti-suppression + secret redaction + injection check).
        safety = apply_output_safety(
            final_output,
            security_module_scan_executed=state.get("security_module_scan_executed", False),
        )
        final_output = safety["final_output"]
        redaction_triggered = safety["redaction_triggered"]

        if safety.get("error"):
            emit_trace_event(
                "s3_violation",
                {"reason": safety["error"], "redaction_triggered": redaction_triggered},
                state,
            )
            return {
                "final_output": final_output,
                "redaction_triggered": redaction_triggered,
                "formatted_output": {"report": final_output, "redaction_triggered": redaction_triggered},
                "status": AgentStatus.ERROR.value,
                "error_log": [safety["error"]],
            }

        emit_trace_event(
            "onboarding_doc_generated",
            {"output_length": len(final_output), "redaction_triggered": redaction_triggered},
            state,
        )
        return {
            "final_output": final_output,
            "redaction_triggered": redaction_triggered,
            "formatted_output": {"report": final_output, "redaction_triggered": redaction_triggered},
            "status": AgentStatus.SUCCESS.value,
        }
