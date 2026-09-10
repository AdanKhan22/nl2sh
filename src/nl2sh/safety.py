import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SafetyAssessment:
    risk_level: RiskLevel
    reasons: List[str] = field(default_factory=list)
    requires_strong_confirmation: bool = False


# Dangerous regex patterns indicating HIGH risk
HIGH_RISK_PATTERNS = [
    # Recursive deletes targeting root, home, or wildcards
    (r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+([/~*]|\$HOME|\.\s*/)", "Recursive force deletion of root, home, or broad directory"),
    (r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r?\s+([/~*]|\$HOME|\.\s*/)", "Recursive force deletion of root, home, or broad directory"),
    (r"\brmdir\s+/[a-zA-Z0-9_/]*", "Direct directory removal on system paths"),
    
    # Windows dangerous deletes
    (r"\bRemove-Item\s+.*-Recurse(\s+.*-Force)?\s+([A-Za-z]:\\|\\|\*)", "Recursive removal of root drive or wildcard in PowerShell"),
    (r"\brd\s+(/[a-zA-Z]\s*)+\s*([A-Za-z]:\\|\\|\*)", "Quiet recursive directory wipe in CMD"),
    (r"\bdel\s+(/[a-zA-Z]\s*)+\s*([A-Za-z]:\\|\\|\*)", "Quiet root/drive or broad wipe in CMD"),

    # Disk & filesystem modifications
    (r"\bdd\s+.*if=.*of=", "Direct disk writing/wiping using dd"),
    (r"\bmkfs(\.[a-z0-9]+)?\b", "Filesystem creation/formatting"),
    (r"\b(fdisk|parted|gdisk)\b", "Partition table manipulation"),
    (r"\bFormat-Volume\b", "PowerShell volume formatting"),
    (r"\bformat\s+[a-zA-Z]:", "Windows drive format command"),

    # Broad permission alterations
    (r"\bchmod\s+-[a-zA-Z]*R[a-zA-Z]*\s+777\s+/", "Recursive chmod 777 on system paths"),
    (r"\bchown\s+-[a-zA-Z]*R[a-zA-Z]*\s+.*[:/]", "Recursive owner modification on system paths"),

    # Fork bombs / resource starvation
    (r":\(\)\s*\{\s*:\|:&\s*\};:", "Classic bash fork bomb"),
    (r"\b(cat\s+/dev/urandom|cat\s+/dev/zero)\s*>\s*/dev/sd", "Writing raw streams to storage block device"),

    # Remote pipe to shell execution
    (r"(curl|wget|fetch)\s+[^\n|;&]+\|\s*(ba|z|k|t?c)?sh\b", "Piping remote network payload directly to a shell"),
    (r"irm\s+[^\n|;&]+\|\s*iex\b", "PowerShell Invoke-RestMethod piped into Invoke-Expression"),
    (r"Invoke-Expression\s*\(?.*(Invoke-WebRequest|irm|iwr)", "PowerShell dynamic execution of remote payload"),

    # Overwriting critical configuration / boot files
    (r">\s*/etc/(passwd|shadow|hosts|fstab|sudoers)", "Direct overwrite of critical Linux system configuration file"),
    (r">\s*/boot/", "Direct overwrite of bootloader files"),
    (r">\s*C:\\Windows\\System32\\", "Overwriting Windows system files"),

    # Sudo usage
    (r"\bsudo\b", "Superuser privilege escalation (sudo)"),

    # Arbitrary script/payload generation to disk
    (r"(Set-Content|Out-File|Add-Content)\s+.*-Path\s+['\"].*\.(ps1|vbs|bat|cmd|sh|exe)['\"]", "Writing executable script payload to disk"),
    (r">\s*['\"]?.*\.(ps1|vbs|bat|cmd|sh|exe)\b", "Redirecting output into an executable script or binary file"),
    (r"\b(Disable-ADAccount|Move-ADObject|Remove-ADUser|Set-ADUser)\b", "Active Directory user/domain modification"),
]

# Medium risk patterns (operations that alter state or terminate processes, but aren't necessarily catastrophic)
MEDIUM_RISK_PATTERNS = [
    (r"\brm\s+", "File deletion"),
    (r"\bRemove-Item\b", "PowerShell item deletion"),
    (r"\bdel\b|\berase\b", "CMD file deletion"),
    (r"\bkill\s+-9\b|\bkillall\b|\bpkill\b", "Force terminating processes"),
    (r"\bStop-Process\b", "PowerShell terminating processes"),
    (r"\btaskkill\s+/f\b", "Windows force killing process"),
    (r"\bchmod\b|\bchown\b", "File permission modification"),
    (r"\bSet-Acl\b", "PowerShell ACL modification"),
    (r"\b(reboot|shutdown|poweroff|init\s+0)\b", "System reboot or shutdown"),
    (r"\bStop-Computer\b|\bRestart-Computer\b", "PowerShell computer restart/shutdown"),
    (r"\bgit\s+(reset\s+--hard|clean\s+-fdx?|push\s+.*--force)", "Destructive git operation that can erase uncommitted work"),
    (r">\s*[^>\s]", "File overwrite redirection (>)"),
]


def assess_command_safety(command: str, llm_suggested_risk: str = "low") -> SafetyAssessment:
    """
    Evaluates command safety by checking against heuristic denylist rules
    and reconciling with the LLM's suggested risk level.
    """
    cmd_clean = command.strip()
    reasons: List[str] = []
    
    # 1. Check HIGH risk patterns
    for pattern, reason in HIGH_RISK_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            reasons.append(f"HIGH RISK: {reason}")

    if reasons:
        return SafetyAssessment(
            risk_level=RiskLevel.HIGH,
            reasons=reasons,
            requires_strong_confirmation=True,
        )

    # 2. Check MEDIUM risk patterns
    for pattern, reason in MEDIUM_RISK_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            reasons.append(f"MEDIUM RISK: {reason}")

    # Check if LLM flagged it higher
    llm_risk_clean = llm_suggested_risk.lower().strip()
    if llm_risk_clean == "high":
        reasons.append("Flagged as HIGH risk by model analysis.")
        return SafetyAssessment(
            risk_level=RiskLevel.HIGH,
            reasons=reasons,
            requires_strong_confirmation=True,
        )
    elif llm_risk_clean == "medium" and not reasons:
        reasons.append("Flagged as MEDIUM risk by model analysis.")
        return SafetyAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=reasons,
            requires_strong_confirmation=False,
        )

    if reasons:
        return SafetyAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=reasons,
            requires_strong_confirmation=False,
        )

    # Default to LOW risk
    return SafetyAssessment(
        risk_level=RiskLevel.LOW,
        reasons=["Standard read-only or non-destructive command."],
        requires_strong_confirmation=False,
    )
