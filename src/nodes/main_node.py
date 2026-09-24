"""Main node — SecurityModuleClassify + DependencyAnalysis + ModuleSummary.

AgentBaseGraph runs a fixed pipeline (initialize → pre_process → main → post_process → finalize),
so the three middle business steps are orchestrated here via deterministic services in src/services/.
The security-module scan is NON-SUPPRESSIBLE: security_module_scan_executed is always set True.

Node contract: execute(self, state) -> dict; status is an AgentStatus enum; no __call__/_invoke_impl.
An optional LLM (injected via config, secret bound at the entry point) narrates module summaries.
"""

from __future__ import annotations

from typing import Any
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import CMN_C1_087_State
from src.services.dependency import analyze_dependencies
from src.services.security_scan import classify_security_modules
from src.services.summary import summarize_modules

_DEFAULT_MAX_FILE_SIZE_KB = 500


class MainNode(FunctionNode):
    # S-1: outer backbone node - matches the manifest trust level (config/agent.yaml).
    required_trust_level = TrustLevel.INTERNAL

    def __init__(self, llm: Any = None) -> None:
        # Immutable injected dep only (no mutable per-invocation state on self).
        self._llm = llm

    def execute(self, state: CMN_C1_087_State) -> dict[str, Any]:
        # Propagate a pre_process failure: AgentBaseGraph always routes pre_process → main,
        # so guard here (no manifest means ingestion failed / nothing to analyze).
        if not state.get("file_manifest") and not state.get("skipped_files"):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["main: no ingested files (source_path invalid or empty)"],
            }

        file_manifest = state.get("file_manifest", [])
        skipped_files = state.get("skipped_files", [])
        source_path = state.get("source_path", "")
        max_kb = state.get("max_file_size_kb", _DEFAULT_MAX_FILE_SIZE_KB)
        correlation_id = state.get("correlation_id")

        # SecurityModuleClassify — NON-SUPPRESSIBLE (always records the scan flag).
        security_module_map = classify_security_modules(file_manifest)

        # DependencyAnalysis (deterministic).
        dependency_report = (
            analyze_dependencies(source_path)
            if source_path
            else {
                "found_files": [],
                "packages": [],
                "deprecated_flags": [],
            }
        )

        # ModuleSummary (per-file; optional LLM narration, deterministic fallback).
        module_summaries = summarize_modules(
            file_manifest, skipped_files, max_kb, llm=self._llm, correlation_id=correlation_id
        )

        emit_trace_event(
            "modules_analyzed",
            {
                "security_modules_found": len(security_module_map),
                "dep_files_found": len(dependency_report.get("found_files", [])),
                "deprecated_flags": len(dependency_report.get("deprecated_flags", [])),
                "modules_summarized": len(module_summaries),
            },
            state,
        )

        return {
            "security_module_map": security_module_map,
            "security_module_scan_executed": True,  # anti-suppression invariant
            "dependency_report": dependency_report,
            "module_summaries": module_summaries,
            "status": AgentStatus.SUCCESS.value,
        }
