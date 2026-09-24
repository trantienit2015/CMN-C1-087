"""SecurityModuleClassify service — NON-SUPPRESSIBLE security-pattern scan.

Scans every file in the manifest for security-sensitive patterns. Pure functions, no state,
no side effects. The caller (MainNode) always records security_module_scan_executed=True so the
scan can never be suppressed/configured away (anti-suppression invariant).
"""

from __future__ import annotations

import re

SECURITY_PATTERNS = [
    (r"(?i)\bauth\b", "auth"),
    (r"(?i)\blogin\b", "login"),
    (r"(?i)\bpassword\b", "password"),
    (r"(?i)\bpayment\b", "payment"),
    (r"(?i)\bcredit.?card\b", "credit_card"),
    (r"(?i)\bpii\b", "pii"),
    (r"(?i)\bencrypt\b", "encrypt"),
    (r"(?i)\bdecrypt\b", "decrypt"),
    (r"(?i)\bcrypto\b", "crypto"),
    (r"(?i)\bsession\b", "session"),
    (r"(?i)\bjwt\b", "jwt"),
    (r"(?i)\btoken\b", "token"),
    (r"(?i)\boauth\b", "oauth"),
]


def classify_security_modules(file_manifest: list[str]) -> dict[str, list[str]]:
    """Return {filepath -> [matched security pattern labels]} for files that match any pattern."""
    security_module_map: dict[str, list[str]] = {}
    for fpath in file_manifest:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            continue
        matched = [label for pattern, label in SECURITY_PATTERNS if re.search(pattern, content)]
        if matched:
            security_module_map[fpath] = list(set(matched))
    return security_module_map
