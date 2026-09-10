import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


def execute_shell_command(command: str, target_shell: str) -> ExecutionResult:
    """
    Executes a shell command directly under the specified shell environment.
    Captures stdout, stderr, and the return code.
    """
    shell_lower = target_shell.lower()
    
    if "powershell" in shell_lower or "pwsh" in shell_lower:
        cmd_args = ["powershell", "-NoProfile", "-Command", command]
    elif "cmd" in shell_lower:
        cmd_args = ["cmd.exe", "/c", command]
    elif "bash" in shell_lower:
        cmd_args = ["bash", "-c", command]
    elif "zsh" in shell_lower:
        cmd_args = ["zsh", "-c", command]
    else:
        # Generic fallback
        cmd_args = command

    is_string_shell = isinstance(cmd_args, str)

    proc = subprocess.run(
        cmd_args,
        shell=is_string_shell,
        text=True,
        capture_output=True,
    )

    return ExecutionResult(
        exit_code=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
