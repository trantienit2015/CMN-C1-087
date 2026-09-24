"""CodebaseIngestion (pre_process) — validate source_path + S-2 path guard + build manifest.

AgentCore node contract: override execute(self, state) -> dict; return a partial update; set
status (AgentStatus enum); never override __call__; no _invoke_impl. Codebase source data is
operational/internal (S-1): require INTERNAL trust. The S-2 path-traversal guard (resolve
symlinks, reject forbidden system prefixes, bound max_file_size_kb) runs inline before os.walk().
"""

from __future__ import annotations

from typing import Any
import os

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

from src.schemas.state import CMN_C1_087_State

ENTRY_POINTS = {
    "main.py",
    "app.py",
    "wsgi.py",
    "asgi.py",
    "server.py",
    "index.js",
    "index.ts",
    "app.js",
    "server.js",
    "App.java",
    "Main.java",
    "Application.java",
    "__init__.py",
}

LANGUAGE_MAP = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".cob": "cobol",
    ".cbl": "cobol",
}

DOC_EXTENSIONS = {".md", ".rst", ".txt"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar"}
_FORBIDDEN_PATH_PREFIXES = ("/etc", "/proc", "/sys", "/root")
_DEFAULT_MAX_FILE_SIZE_KB = 500


class PreProcessNode(FunctionNode):
    """Validate + ingest the codebase: S-2 path guard, then build file_manifest + skipped_files."""

    # S-1: codebase source is store-internal operational data.
    required_trust_level = TrustLevel.INTERNAL

    def execute(self, state: CMN_C1_087_State) -> dict[str, Any]:
        source_path = state.get("source_path") or state.get("user_input", "")
        max_kb = state.get("max_file_size_kb", _DEFAULT_MAX_FILE_SIZE_KB)

        # S-2: source_path required.
        if not source_path:
            return {"status": AgentStatus.ERROR.value, "error_log": ["S-2 violation: source_path required"]}

        # S-2: bound max_file_size_kb.
        if not isinstance(max_kb, int) or max_kb <= 0 or max_kb > 10_000:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["S-2 violation: max_file_size_kb out of range (must be 1-10000)"],
            }

        # S-2: resolve symlinks and reject forbidden system prefixes before os.walk().
        abs_path = os.path.realpath(source_path)
        for prefix in _FORBIDDEN_PATH_PREFIXES:
            if abs_path.startswith(prefix):
                return {
                    "status": AgentStatus.ERROR.value,
                    "error_log": [f"S-2 violation: forbidden path: {abs_path}"],
                }

        if not os.path.isdir(abs_path):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"source_path not found or not a directory: {abs_path}"],
            }

        max_bytes = max_kb * 1024
        file_manifest: list[str] = []
        skipped_files: list[dict[str, Any]] = list[Any](state.get("skipped_files", []))

        for root, _dirs, files in os.walk(abs_path):
            # v1 scope: top-level and one level deep only.
            depth = root[len(abs_path) :].count(os.sep)
            if depth > 1:
                continue
            for fname in files:
                fpath = os.path.join(root, fname)
                _, ext = os.path.splitext(fname)
                ext = ext.lower()

                if ext in ARCHIVE_EXTENSIONS:
                    skipped_files.append({"path": fpath, "reason": "S1:archive-rejected"})
                    continue
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    skipped_files.append({"path": fpath, "reason": "unreadable"})
                    continue
                if size > max_bytes:
                    skipped_files.append({"path": fpath, "reason": f"oversized:>{max_kb}kb"})
                    continue
                if ext in (".cob", ".cbl"):
                    skipped_files.append({"path": fpath, "reason": "COBOL:v1-skip"})
                    continue
                if ext in LANGUAGE_MAP or fname in ENTRY_POINTS or ext in DOC_EXTENSIONS:
                    file_manifest.append(fpath)

        emit_trace_event(
            "codebase_ingested",
            {"files_ingested": len(file_manifest), "files_skipped": len(skipped_files)},
            state,
        )
        return {
            "source_path": abs_path,
            "max_file_size_kb": max_kb,
            "file_manifest": file_manifest,
            "skipped_files": skipped_files,
            "status": AgentStatus.SUCCESS.value,
        }
