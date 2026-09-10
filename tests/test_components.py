import json
import pytest
from unittest.mock import patch, MagicMock
from nl2sh.llm import generate_command, CommandSuggestion
from nl2sh.detector import detect_environment
from nl2sh.history import HistoryManager, HistoryRecord


def test_detector():
    os_name, shell_name = detect_environment()
    assert os_name in ["Linux", "macOS", "Windows"]
    assert len(shell_name) > 0


def test_history_logging(tmp_path):
    history_file = tmp_path / "test_history.jsonl"
    mgr = HistoryManager(history_file)

    rec1 = HistoryRecord(
        instruction="list files",
        target_os="Windows",
        target_shell="powershell",
        generated_command="dir",
        explanation="List directory content",
        risk_level="low",
        executed=True,
        exit_code=0,
    )
    mgr.log(rec1)

    rec2 = HistoryRecord(
        instruction="find python files",
        target_os="Windows",
        target_shell="powershell",
        generated_command="Get-ChildItem -Filter *.py",
        explanation="Find python files",
        risk_level="low",
        executed=False,
    )
    mgr.log(rec2)

    recent = mgr.get_recent(limit=2)
    assert len(recent) == 2
    assert recent[0].instruction == "list files"
    assert recent[1].instruction == "find python files"

    context = mgr.format_recent_context(limit=2)
    assert "list files" in context
    assert "Executed successfully" in context
    assert "Suggested but not executed" in context


@patch("nl2sh.llm.genai.Client")
def test_generate_command_mock(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "command": "find . -name '*.log'",
        "explanation": "Finds all log files in the current folder.",
        "risk_level": "low",
        "clarification_needed": False,
        "clarification_message": None,
    })
    mock_client.models.generate_content.return_value = mock_response

    suggestion = generate_command(
        query="find log files",
        target_os="Linux",
        target_shell="bash",
        api_key="fake-key",
    )

    assert isinstance(suggestion, CommandSuggestion)
    assert suggestion.command == "find . -name '*.log'"
    assert suggestion.risk_level == "low"
    assert not suggestion.clarification_needed
