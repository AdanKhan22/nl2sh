from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from nl2sh.safety import RiskLevel, SafetyAssessment

console = Console()


def display_command_card(
    command: str,
    explanation: str,
    assessment: SafetyAssessment,
    os_name: str,
    shell_name: str,
) -> None:
    """Renders a formatted command card with color-coded risk assessment."""
    if assessment.risk_level == RiskLevel.HIGH:
        risk_badge = "[bold white on red] HIGH RISK [/bold white on red]"
        border_style = "red"
    elif assessment.risk_level == RiskLevel.MEDIUM:
        risk_badge = "[bold black on yellow] MEDIUM RISK [/bold black on yellow]"
        border_style = "yellow"
    else:
        risk_badge = "[bold white on green] LOW RISK [/bold white on green]"
        border_style = "green"

    content = Text()
    content.append("Generated Command:\n", style="bold cyan")
    content.append(f"  {command}\n\n", style="bold yellow")
    
    content.append("Explanation:\n", style="bold cyan")
    content.append(f"  {explanation}\n\n", style="italic")
    
    content.append(f"Target Environment: ", style="bold")
    content.append(f"{os_name} ({shell_name})\n")

    if assessment.reasons:
        content.append("\nSafety Notes:\n", style="bold")
        for reason in assessment.reasons:
            content.append(f"  - {reason}\n", style="dim" if assessment.risk_level == RiskLevel.LOW else "bold red")

    console.print()
    console.print(
        Panel(
            content,
            title=f"nl2sh {risk_badge}",
            border_style=border_style,
            expand=False,
        )
    )
    console.print()


def display_error(message: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")


def display_warning(message: str) -> None:
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def display_info(message: str) -> None:
    console.print(f"[bold blue]nl2sh:[/bold blue] {message}")
