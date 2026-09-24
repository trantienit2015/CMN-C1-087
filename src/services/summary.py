"""ModuleSummary service — per-file summarization with isolated context.

Each file is summarized independently (no shared LLM context across files). An optional LLM is
injected by the caller (MainNode, secret bound at the entry point); when no LLM is injected a
deterministic placeholder is returned so the pipeline is fully testable without a live model.
COBOL files are skipped; files already in skipped_files are not reprocessed. Pure functions.
"""

from __future__ import annotations

from typing import Any
import logging
import os

logger = logging.getLogger(__name__)

COBOL_EXTENSIONS = {".cob", ".cbl"}
SAMPLE_LINES = 200
SAMPLE_MID_START = 0.4
SAMPLE_MID_END = 0.6

# Deterministic fallback when no LLM is injected (mirrors the prior CI stub output).
_DEFAULT_SUMMARY = "mock summary output"


def _read_representative_content(fpath: str, max_kb: int) -> str:
    """Read up to max_kb worth of content; for large files sample first + middle."""
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return ""

    max_bytes = max_kb * 1024
    try:
        total_size = os.path.getsize(fpath)
    except OSError:
        return ""

    if total_size <= max_bytes:
        return "".join(lines)

    first = lines[:SAMPLE_LINES]
    mid_start = int(len(lines) * SAMPLE_MID_START)
    mid_end = int(len(lines) * SAMPLE_MID_END)
    middle = lines[mid_start:mid_end]
    return "".join(first) + "\n...[truncated]...\n" + "".join(middle)


def _build_prompt(fpath: str, content: str) -> str:
    return (
        "You are a senior software engineer reviewing a codebase for a new team member.\n"
        "Summarize the following file in 3-5 sentences. Include:\n"
        "- Purpose of the module\n"
        "- Key classes or functions\n"
        "- Inputs and outputs\n"
        "Do NOT reproduce any credentials, secrets, or sensitive values.\n\n"
        f"File: {os.path.basename(fpath)}\n\n"
        f"```\n{content[:4000]}\n```"
    )


def summarize_modules(
    file_manifest: list[str],
    skipped_files: list[dict[str, Any]],
    max_kb: int,
    llm: Any = None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Return {filepath -> summary} for each non-skipped, non-COBOL file in the manifest.

    When an LLM is injected, it narrates the summary (a failed call is logged with
    correlation_id and falls back to deterministic text — never silent). Without an LLM, a
    deterministic placeholder is used.
    """
    skipped_paths = {s["path"] for s in skipped_files}
    module_summaries: dict[str, str] = {}

    for fpath in file_manifest:
        if fpath in skipped_paths:
            continue
        _, ext = os.path.splitext(fpath)
        if ext.lower() in COBOL_EXTENSIONS:
            continue

        content = _read_representative_content(fpath, max_kb)
        if not content.strip():
            module_summaries[fpath] = "(empty file)"
            continue

        summary = _DEFAULT_SUMMARY
        if llm is not None:
            try:
                summary = llm.summarize(_build_prompt(fpath, content)) or _DEFAULT_SUMMARY
            except Exception as exc:  # narration is best-effort; fall back deterministically
                logger.warning(
                    "ModuleSummary LLM call failed (correlation_id=%s, file=%s): %s — "
                    "falling back to deterministic summary",
                    correlation_id,
                    os.path.basename(fpath),
                    exc,
                )
                summary = _DEFAULT_SUMMARY
        module_summaries[fpath] = summary

    return module_summaries
