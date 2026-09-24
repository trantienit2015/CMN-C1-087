"""CMN-C1-087 graph — AgentBaseGraph (L1 direct). The graph class IS the agent.

Cat 1 (single capability: produce a codebase onboarding document). Fixed 5-node backbone
initialize → pre_process → main → post_process → finalize. No separate agent class, no
double-graph, no _invoke_impl, no .run(). Public entry: Graph(config).compile() then
.invoke(user_input, ctx=...). The 5-layer security model is framework-enforced — there are no
developer `_security_gate_*` methods (S-2 path guard lives in pre_process, S-3 output safety in
post_process as ordinary node logic).
"""

from __future__ import annotations

from typing import Any
from framework.graph.agent_base_graph import AgentBaseGraph

from src.nodes.main_node import MainNode
from src.nodes.post_process_node import PostProcessNode
from src.nodes.pre_process_node import PreProcessNode
from src.schemas.state import CMN_C1_087_State


class CodebaseOnboardingSummaryAgent(AgentBaseGraph):
    """CMN-C1-087 — Codebase & Technical Documentation Onboarding Summary Agent (Cat 1)."""

    @property
    def name(self) -> str:
        return "cmn-c1-087"

    @property
    def state_schema(self) -> Any:
        return CMN_C1_087_State

    def register_nodes(self) -> None:
        super().register_nodes()  # preserve default initialize + finalize backbone
        cfg = self.config if hasattr(self, "config") else {}
        llm = cfg.get("llm")
        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = MainNode(llm=llm)
        self._nodes["post_process"] = PostProcessNode()


# Alias for the AgentRegistry entry point (config/agent.yaml module: "src.graph").
Graph = CodebaseOnboardingSummaryAgent


def build_agent(config: dict[str, Any] | None = None) -> CodebaseOnboardingSummaryAgent:
    """Factory for AgentRegistry entry point."""
    return CodebaseOnboardingSummaryAgent(config=config or {})
