import json
import logging
from typing import Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CommandSuggestion(BaseModel):
    command: str = Field(
        description="A single executable shell command. No multi-step scripts, no code fences."
    )
    explanation: str = Field(
        description="Plain-English explanation of what the command does and what each flag means."
    )
    risk_level: str = Field(
        description="Assessed risk level: 'low', 'medium', or 'high'."
    )
    clarification_needed: bool = Field(
        description="Set to true if the request is ambiguous or vague, false otherwise."
    )
    clarification_message: Optional[str] = Field(
        default=None,
        description="Optional clarification question or note if clarification_needed is true.",
    )


SYSTEM_INSTRUCTION = """
You are a precision shell command generator (nl2sh).
Your job is to convert natural language instructions into a SINGLE valid shell command for the user's specific OS and shell.

Guidelines:
1. Target the specified OS and Shell syntax accurately.
2. Produce a single command. Avoid chaining commands (&&, ;, |) unless the task specifically calls for it.
3. Do not wrap commands in markdown code blocks. Provide raw command text only.
4. Do NOT generate destructive operations (e.g. recursive delete, disk formatting, wiping partitions, piping remote curl to shell) unless the user's request explicitly, unambiguously requests it.
5. If the user's prompt is too vague or could have destructive unintended side effects, set clarification_needed to true and explain why in clarification_message.
"""


def generate_command(
    query: str,
    target_os: str,
    target_shell: str,
    api_key: str,
    model_name: str = "gemini-3.5-flash-lite",
    recent_context: Optional[str] = None,
) -> CommandSuggestion:
    """
    Calls Gemini API using google-genai SDK to generate a structured CommandSuggestion.
    """
    client = genai.Client(api_key=api_key)

    prompt = f"""
Target OS: {target_os}
Target Shell: {target_shell}
"""
    if recent_context:
        prompt += f"""
Recent Command Context / History:
{recent_context}
"""

    prompt += f"""
User Instruction: "{query}"

Generate the command according to the specified JSON schema.
"""

    # Explicitly disable automatic function calling since we only need structured JSON output
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=CommandSuggestion,
        temperature=0.1,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )

    if not response.text:
        raise RuntimeError("Empty response received from Gemini API.")

    data = json.loads(response.text)
    return CommandSuggestion(**data)
