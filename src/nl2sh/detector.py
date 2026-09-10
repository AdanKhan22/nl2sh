import os
import platform
import shutil
from typing import Tuple


def detect_environment() -> Tuple[str, str]:
    """
    Detect the current operating system and active/default shell.
    Returns:
        (os_name, shell_name)
        e.g. ("Linux", "bash"), ("macOS", "zsh"), ("Windows", "powershell")
    """
    # Detect OS
    system = platform.system()
    if system == "Darwin":
        os_name = "macOS"
    elif system == "Linux":
        os_name = "Linux"
    elif system == "Windows":
        os_name = "Windows"
    else:
        os_name = system

    # Detect Shell
    shell_name = "unknown"

    # Check environment variables
    # Unix shells usually set SHELL=/bin/bash or /bin/zsh
    shell_env = os.environ.get("SHELL", "")
    if shell_env:
        shell_name = os.path.basename(shell_env).lower()
    elif os_name == "Windows":
        # Check if running under PowerShell, CMD, Git Bash, etc.
        # Often PSModulePath is set in PowerShell
        if os.environ.get("PSModulePath"):
            shell_name = "powershell"
        elif os.environ.get("COMSPEC"):
            comspec = os.environ.get("COMSPEC", "").lower()
            if "powershell" in comspec:
                shell_name = "powershell"
            elif "cmd.exe" in comspec or "cmd" in comspec:
                shell_name = "cmd"
            else:
                shell_name = "cmd"
        else:
            shell_name = "powershell"
    else:
        # Fallback Unix check
        if shutil.which("bash"):
            shell_name = "bash"
        elif shutil.which("sh"):
            shell_name = "sh"

    return os_name, shell_name
