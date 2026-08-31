"""Shell command risk classification.

Pattern-based triage into ``LOW`` / ``MEDIUM`` / ``HIGH``. Classification is
conservative: destructive patterns are checked first and win, so an ambiguous
command errs toward the higher risk level.
"""

from __future__ import annotations

import re
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Destructive / dangerous commands. Order matters within ``classify`` only in
# that HIGH is checked before anything else.
_HIGH_PATTERNS: tuple[str, ...] = (
    r"\brm\s+(-\w*r\w*f\w*|-\w*f\w*r\w*)",  # rm -rf / rm -fr
    r"curl\b[^\n|]*\|\s*(ba)?sh\b",  # curl ... | sh
    r"wget\b[^\n|]*\|\s*(ba)?sh\b",  # wget ... | sh
    r"\bsudo\b",  # privilege escalation
    r"\bmkfs\b",  # format filesystem
    r"\bdd\s+if=",  # raw disk write
    r">\s*/dev/",  # write to a device node
    r"\bshutdown\b|\breboot\b|\bhalt\b",  # system power control
    r":\(\)\s*\{",  # fork bomb
)

# Read-only inspection commands (anchored to the start of the command).
_LOW_PATTERNS: tuple[str, ...] = (
    r"^\s*ls(\s|$)",
    r"^\s*cat\b",
    r"^\s*head\b",
    r"^\s*tail\b",
    r"^\s*wc\b",
    r"^\s*pwd\b",
    r"^\s*echo\b",
    r"^\s*git\s+status\b",
    r"^\s*git\s+diff\b",
    r"^\s*git\s+log\b",
)


def classify(command: str) -> RiskLevel:
    """Classify a shell command into a risk level.

    HIGH destructive patterns win over LOW read-only patterns; anything that
    matches neither is MEDIUM.
    """
    for pattern in _HIGH_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.HIGH
    for pattern in _LOW_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.LOW
    return RiskLevel.MEDIUM
