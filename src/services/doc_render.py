"""OnboardingDocGeneration service — assemble the final Markdown onboarding document.

Renders module summaries, dependency report, the NON-SUPPRESSIBLE security module map, a
how-to-contribute section, and skipped files. The AI disclaimer and security module map are
always included. Pure function, no state, no LLM.
"""

from __future__ import annotations

from typing import Any
import os

AI_DISCLAIMER = (
    "⚠️ **AI-Generated Document** — " "This document was generated automatically. Validate with a developer before use."
)


def _section(title: str, content: str) -> str:
    return f"## {title}\n\n{content}\n"


def render_onboarding_doc(
    module_summaries: dict[str, Any],
    security_module_map: dict[str, Any],
    dependency_report: dict[str, Any],
    skipped_files: list[Any],
    source_path: str,
) -> str:
    sections: list[str] = []

    # Non-suppressible disclaimer
    sections.append(f"> {AI_DISCLAIMER}\n")

    # Module Structure
    if module_summaries:
        mod_content = ""
        for fpath, summary in module_summaries.items():
            rel = os.path.relpath(fpath, source_path) if source_path else fpath
            mod_content += f"### `{rel}`\n\n{summary}\n\n"
        sections.append(_section("Module Structure", mod_content))
    else:
        sections.append(_section("Module Structure", "_No modules processed._"))

    # Data Flow & Dependencies
    dep = dependency_report or {}
    dep_content = ""
    if dep.get("found_files"):
        dep_content += "**Dependency files found:**\n"
        for f in dep["found_files"]:
            dep_content += f"- `{os.path.basename(f)}`\n"
        dep_content += "\n"
    if dep.get("packages"):
        dep_content += f"**Packages detected:** {len(dep['packages'])}\n\n"
    if dep.get("deprecated_flags"):
        dep_content += "**⚠️ Deprecated / flagged packages:**\n"
        for d in dep["deprecated_flags"]:
            dep_content += f"- `{d['package']}` — {d['reason']}\n"
        dep_content += "\n"
    if not dep_content:
        dep_content = "_No dependency files found._"
    sections.append(_section("Data Flow & Dependencies", dep_content))

    # Security Modules (NON-SUPPRESSIBLE — always included)
    sec_content = (
        "⚠️ The following modules contain security-sensitive patterns. " "Review carefully before modification.\n\n"
    )
    if security_module_map:
        for fpath, patterns in security_module_map.items():
            rel = os.path.relpath(fpath, source_path) if source_path else fpath
            sec_content += f"- `{rel}`: {', '.join(patterns)}\n"
    else:
        sec_content += "_No security-sensitive modules detected._"
    sections.append(_section("Security Modules", sec_content))

    # How to Contribute
    contribute = (
        "1. Understand the module structure above before making changes.\n"
        "2. Run the full test suite before submitting a merge request.\n"
        "3. Security modules (listed above) require additional review — "
        "involve a senior engineer.\n"
        "4. Follow the existing code style and naming conventions.\n"
        "5. Update this onboarding document if you add new modules.\n"
    )
    sections.append(_section("How to Contribute", contribute))

    # Skipped Files
    if skipped_files:
        skip_content = ""
        for entry in skipped_files:
            rel = os.path.relpath(entry["path"], source_path) if source_path else entry["path"]
            skip_content += f"- `{rel}` — {entry['reason']}\n"
        sections.append(_section("Skipped Files", skip_content))

    return "# Codebase Onboarding Guide\n\n" + "\n".join(sections)
