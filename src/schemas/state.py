"""State schema for CMN-C1-087 — CodebaseOnboardingSummaryAgent.

Flat TypedDict extending the framework AgentState. Only agent-specific fields are declared
here; AgentState already provides the shared fields (user_input, status, node_history,
error_log, correlation_id, caller_trust_level, formatted_output, etc.). All fields are
flat / JSON-serializable — no Pydantic, dataclasses, credentials, or InvocationContext.
"""

from __future__ import annotations

from typing import Any
from framework.schemas.agent_state import AgentState


class CMN_C1_087_State(AgentState):
    # --- Input config (provided on user_input / input_context or defaults) ---
    source_path: str
    output_doc_path: str
    max_file_size_kb: int

    # --- CodebaseIngestion (pre_process) output ---
    file_manifest: list[str]
    skipped_files: list[dict[str, Any]]  # [{"path": str, "reason": str}]

    # --- SecurityModuleClassify (main) output — non-suppressible ---
    security_module_map: dict[str, list[str]]  # filepath -> [matched_patterns]
    security_module_scan_executed: bool  # anti-suppression: always True after the scan

    # --- DependencyAnalysis (main) output ---
    dependency_report: dict[str, Any]  # {found_files, packages, deprecated_flags}

    # --- ModuleSummary (main) output ---
    module_summaries: dict[str, str]  # filepath -> summary

    # --- OnboardingDocGeneration + S-3 output safety (post_process) output ---
    final_output: str
    redaction_triggered: bool  # True if the secret-leakage redaction triggered
