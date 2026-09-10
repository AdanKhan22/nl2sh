import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# 1. Load from environment variables / existing .env files if present
load_dotenv()

if getattr(sys, "frozen", False):
    exe_dir_env = Path(sys.executable).parent / ".env"
    if exe_dir_env.exists():
        load_dotenv(dotenv_path=exe_dir_env)

home_env = Path.home() / ".nl2sh" / ".env"
if home_env.exists():
    load_dotenv(dotenv_path=home_env)


CONFIG_DIR = Path.home() / ".nl2sh"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    gemini_api_key: str | None
    model_name: str
    history_file: Path


def load_user_config() -> dict:
    """Reads JSON config from ~/.nl2sh/config.json if it exists."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_user_api_key(api_key: str) -> None:
    """Encrypts and saves the user's Gemini API key to ~/.nl2sh/config.json."""
    from nl2sh.crypto import dpapi_encrypt

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current_data = load_user_config()
    current_data["gemini_api_key"] = dpapi_encrypt(api_key.strip())
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current_data, f, indent=2)


def get_config() -> Config:
    # Priority: 1) System environment variable / .env, 2) ~/.nl2sh/config.json
    api_key = os.environ.get("GEMINI_API_KEY")
    user_data = load_user_config()
    
    if not api_key:
        stored_key = user_data.get("gemini_api_key")
        if stored_key:
            from nl2sh.crypto import dpapi_decrypt
            try:
                api_key = dpapi_decrypt(stored_key)
            except Exception:
                api_key = stored_key

    model_name = os.environ.get(
        "NL2SH_MODEL", user_data.get("model_name", "gemini-3.5-flash-lite")
    )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    history_file = CONFIG_DIR / "history.jsonl"

    return Config(
        gemini_api_key=api_key,
        model_name=model_name,
        history_file=history_file,
    )
