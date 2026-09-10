import sys
import warnings
from typing import Optional

warnings.filterwarnings("ignore", category=UserWarning, module="google.genai")
import typer
from rich.prompt import Prompt, Confirm

from nl2sh.config import get_config
from nl2sh.detector import detect_environment
from nl2sh.safety import assess_command_safety, RiskLevel
from nl2sh.llm import generate_command
from nl2sh.history import HistoryManager, HistoryRecord
from nl2sh.executor import execute_shell_command
from nl2sh import ui

app = typer.Typer(
    name="nl2sh",
    help="Convert natural language instructions into safe, executable shell commands.",
    add_completion=False,
)


def process_instruction(
    query: str,
    dry_run: bool,
    target_os: str,
    target_shell: str,
    no_context: bool,
    config,
    history_mgr: HistoryManager,
) -> None:
    """Processes a single natural language instruction."""
    recent_context = None if no_context else history_mgr.format_recent_context(limit=3)

    ui.display_info(f"Generating command for [bold cyan]{target_os}[/bold cyan] ({target_shell})...")

    try:
        suggestion = generate_command(
            query=query,
            target_os=target_os,
            target_shell=target_shell,
            api_key=config.gemini_api_key,
            model_name=config.model_name,
            recent_context=recent_context,
        )
    except Exception as e:
        ui.display_error(f"Failed to communicate with LLM backend: {e}")
        return

    if suggestion.clarification_needed:
        ui.display_warning("The model indicated that your instruction is ambiguous or needs clarification:")
        if suggestion.clarification_message:
            ui.console.print(f"  [italic]{suggestion.clarification_message}[/italic]")
        ui.console.print(f"\nProposed alternative/preliminary command: [yellow]{suggestion.command}[/yellow]")
        ui.console.print(f"Explanation: {suggestion.explanation}\n")
        history_mgr.log(
            HistoryRecord(
                instruction=query,
                target_os=target_os,
                target_shell=target_shell,
                generated_command=suggestion.command,
                explanation=suggestion.explanation,
                risk_level=suggestion.risk_level,
                executed=False,
            )
        )
        return

    # Safety Assessment Layer (Denylist & Heuristics)
    assessment = assess_command_safety(
        command=suggestion.command,
        llm_suggested_risk=suggestion.risk_level,
    )

    # Display Command Card
    ui.display_command_card(
        command=suggestion.command,
        explanation=suggestion.explanation,
        assessment=assessment,
        os_name=target_os,
        shell_name=target_shell,
    )

    # Dry-run handling
    if dry_run:
        ui.display_info("Dry-run mode enabled. Command will not be executed.")
        history_mgr.log(
            HistoryRecord(
                instruction=query,
                target_os=target_os,
                target_shell=target_shell,
                generated_command=suggestion.command,
                explanation=suggestion.explanation,
                risk_level=assessment.risk_level.value,
                executed=False,
            )
        )
        return

    # Option to edit command before execution
    final_command = suggestion.command
    allow_edit = Confirm.ask("Would you like to edit this command before running?", default=False)
    if allow_edit:
        final_command = Prompt.ask("Edit command", default=suggestion.command)
        if final_command != suggestion.command:
            assessment = assess_command_safety(final_command, llm_suggested_risk="medium")
            ui.console.print(f"\n[bold]Updated command:[/bold] [yellow]{final_command}[/yellow]")

    # Confirmation Gate
    confirmed = False
    if assessment.requires_strong_confirmation:
        ui.console.print(
            "\n[bold red]ATTENTION:[/bold red] This command is classified as [bold red]HIGH RISK[/bold red].\n"
            "To execute this command, you must type '[bold white on red]YES[/bold white on red]' in full."
        )
        user_input = Prompt.ask("Confirmation", default="NO")
        confirmed = (user_input.strip() == "YES")
    else:
        confirmed = Confirm.ask("Run this command?", default=False)

    if not confirmed:
        ui.display_info("Execution cancelled by user.")
        history_mgr.log(
            HistoryRecord(
                instruction=query,
                target_os=target_os,
                target_shell=target_shell,
                generated_command=final_command,
                explanation=suggestion.explanation,
                risk_level=assessment.risk_level.value,
                executed=False,
            )
        )
        return

    # Subprocess execution
    ui.display_info(f"Executing: [bold]{final_command}[/bold]\n")
    exec_result = execute_shell_command(final_command, target_shell)

    if exec_result.stdout:
        ui.console.print(exec_result.stdout.rstrip())
    if exec_result.stderr:
        ui.console.print(f"[bold red]{exec_result.stderr.rstrip()}[/bold red]")

    ui.console.print(f"\n[dim]Process exited with code {exec_result.exit_code}[/dim]")

    # Record to audit log
    history_mgr.log(
        HistoryRecord(
            instruction=query,
            target_os=target_os,
            target_shell=target_shell,
            generated_command=final_command,
            explanation=suggestion.explanation,
            risk_level=assessment.risk_level.value,
            executed=True,
            exit_code=exec_result.exit_code,
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
        )
    )


@app.command()
def main(
    query: Optional[str] = typer.Argument(
        None,
        help="Natural language instruction (optional; omit for interactive mode).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Generate and inspect the command and safety risk without prompting to execute.",
    ),
    target_os_opt: Optional[str] = typer.Option(
        None,
        "--os",
        help="Override OS detection (e.g. Linux, macOS, Windows).",
    ),
    target_shell_opt: Optional[str] = typer.Option(
        None,
        "--shell",
        help="Override Shell detection (e.g. bash, zsh, powershell).",
    ),
    no_context: bool = typer.Option(
        False,
        "--no-context",
        help="Ignore recent command history context.",
    ),
):
    """
    Main entry point for nl2sh. If no instruction is passed, runs interactively.
    """
    config = get_config()
    if not config.gemini_api_key:
        ui.console.print(
            "\n[bold yellow]No Gemini API key detected.[/bold yellow]\n"
            "To use nl2sh, you need a Google Gemini API key (free at https://aistudio.google.com/).\n"
        )
        entered_key = Prompt.ask(
            "[bold cyan]Paste your Gemini API key here[/bold cyan]"
        ).strip()

        if not entered_key:
            ui.display_error("No API key provided. Exiting.")
            input("\nPress Enter to exit...")
            raise typer.Exit(code=1)

        from nl2sh.config import save_user_api_key
        save_user_api_key(entered_key)
        ui.console.print("[bold green]✓ API key saved to your private user profile! (~/.nl2sh/config.json)[/bold green]\n")
        config = get_config()

    detected_os, detected_shell = detect_environment()
    target_os = target_os_opt or detected_os
    target_shell = target_shell_opt or detected_shell
    history_mgr = HistoryManager(config.history_file)

    # 1. Direct one-shot mode if user provided query on CLI
    if query:
        process_instruction(
            query=query,
            dry_run=dry_run,
            target_os=target_os,
            target_shell=target_shell,
            no_context=no_context,
            config=config,
            history_mgr=history_mgr,
        )
        return

    # 2. Interactive Loop mode (ideal for double-clicking or ongoing sessions)
    ui.console.print(
        "\n[bold cyan]╔══════════════════════════════════════════════════════════════╗\n"
        "║                     Welcome to nl2sh                         ║\n"
        "║       Natural Language to Shell Commands Assistant          ║\n"
        "╚══════════════════════════════════════════════════════════════╝[/bold cyan]\n"
    )
    ui.console.print(f"Detected environment: [bold green]{target_os} ({target_shell})[/bold green]")
    ui.console.print("[dim]Type your command in plain English. Type 'exit' or 'q' to quit.[/dim]\n")

    try:
        while True:
            user_input = Prompt.ask("\n[bold cyan]nl2sh >[/bold cyan]")
            user_input = user_input.strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                ui.console.print("[dim]Goodbye![/dim]")
                break

            process_instruction(
                query=user_input,
                dry_run=dry_run,
                target_os=target_os,
                target_shell=target_shell,
                no_context=no_context,
                config=config,
                history_mgr=history_mgr,
            )
    except (KeyboardInterrupt, EOFError):
        ui.console.print("\n[dim]Session closed.[/dim]")


if __name__ == "__main__":
    app()
