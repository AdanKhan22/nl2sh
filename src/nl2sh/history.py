import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HistoryRecord(BaseModel):
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    instruction: str
    target_os: str
    target_shell: str
    generated_command: str
    explanation: str
    risk_level: str
    executed: bool
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class HistoryManager:
    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: HistoryRecord) -> None:
        """Append an audit record in JSONL format."""
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

    def get_recent(self, limit: int = 3) -> List[HistoryRecord]:
        """Fetch the most recent N history records for context injection."""
        if not self.history_file.exists():
            return []

        records: List[HistoryRecord] = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    records.append(HistoryRecord(**data))
                except Exception:
                    continue

        return records[-limit:]

    def format_recent_context(self, limit: int = 3) -> Optional[str]:
        records = self.get_recent(limit)
        if not records:
            return None

        lines = []
        for r in records:
            status = "Executed successfully" if r.executed and r.exit_code == 0 else (
                "Executed with error" if r.executed else "Suggested but not executed"
            )
            lines.append(
                f"- User asked: '{r.instruction}' -> Generated: `{r.generated_command}` ({status})"
            )
        return "\n".join(lines)
