"""DependencyAnalysis service — detect dependency manifests and flag deprecated packages.

Parses requirements.txt / pom.xml / package.json / Gemfile / go.mod under source_path and flags
known-deprecated packages. Pure functions, no external API calls, no state.
"""

from __future__ import annotations

from typing import Any
import json
import os
import re

KNOWN_DEPRECATED = {
    # Python
    "django<2.0",
    "flask<1.0",
    "requests<2.20",
    "pyyaml<5.1",
    # Node
    "request",
    "node-uuid",
    "jade",
    # Java (groupId:artifactId)
    "commons-collections:3",
    "log4j:1",
}

DEPENDENCY_FILES = {
    "requirements.txt": "_parse_requirements",
    "pom.xml": "_parse_pom",
    "package.json": "_parse_package_json",
    "Gemfile": "_parse_gemfile",
    "go.mod": "_parse_gomod",
}

# Strip version operators and numbers from a dep key (e.g. "pyyaml<5.1" → "pyyaml").
_VERSION_STRIP_RE = re.compile(r"[<>=!~\s].*$")


def _dep_name(dep: str) -> str:
    """Extract the bare package name from a KNOWN_DEPRECATED entry.

    Java groupId:artifactId style → take the segment before ":"; version-pinned style
    (pyyaml<5.1) → strip operators and version.
    """
    base = dep.split(":")[0]
    return _VERSION_STRIP_RE.sub("", base).lower()


def analyze_dependencies(source_path: str) -> dict[str, Any]:
    """Return {found_files, packages, deprecated_flags} for the dependency manifests found."""
    abs_path = os.path.realpath(source_path)
    found_files: list[str] = []
    packages: list[str] = []
    deprecated_flags: list[dict[str, Any]] = []

    for root, _, files in os.walk(abs_path):
        depth = root[len(abs_path) :].count(os.sep)
        if depth > 2:
            continue
        for fname in files:
            if fname in DEPENDENCY_FILES:
                fpath = os.path.join(root, fname)
                found_files.append(fpath)
                parser = _PARSERS.get(DEPENDENCY_FILES[fname])
                if parser:
                    pkgs = parser(fpath)
                    packages.extend(pkgs)
                    for pkg in pkgs:
                        pkg_lower = pkg.lower()
                        for dep in KNOWN_DEPRECATED:
                            if _dep_name(dep) in pkg_lower:
                                deprecated_flags.append({"package": pkg, "reason": f"known-deprecated:{dep}"})

    return {
        "found_files": found_files,
        "packages": packages,
        "deprecated_flags": deprecated_flags,
    }


def _parse_requirements(fpath: str) -> list[str]:
    pkgs: list[str] = []
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pkgs.append(line.split("==")[0].split(">=")[0].split("<=")[0].strip())
    except OSError:
        pass
    return pkgs


def _parse_pom(fpath: str) -> list[str]:
    pkgs: list[str] = []
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        pkgs = [a.strip() for a in re.findall(r"<artifactId>([^<]+)</artifactId>", content)]
    except OSError:
        pass
    return pkgs


def _parse_package_json(fpath: str) -> list[str]:
    pkgs: list[str] = []
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        for section in ("dependencies", "devDependencies"):
            pkgs.extend(data.get(section, {}).keys())
    except (OSError, json.JSONDecodeError):
        pass
    return pkgs


def _parse_gemfile(fpath: str) -> list[str]:
    pkgs: list[str] = []
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'\s*gem\s+[\'"]([^\'"]+)[\'"]', line)
                if m:
                    pkgs.append(m.group(1))
    except OSError:
        pass
    return pkgs


def _parse_gomod(fpath: str) -> list[str]:
    pkgs: list[str] = []
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"\s*require\s+(\S+)", line)
                if m:
                    pkgs.append(m.group(1))
    except OSError:
        pass
    return pkgs


_PARSERS = {
    "_parse_requirements": _parse_requirements,
    "_parse_pom": _parse_pom,
    "_parse_package_json": _parse_package_json,
    "_parse_gemfile": _parse_gemfile,
    "_parse_gomod": _parse_gomod,
}
