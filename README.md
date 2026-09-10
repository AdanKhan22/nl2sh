# nl2sh: Natural Language to Shell Commands CLI

`nl2sh` is a safe, auditable command-line interface that converts natural language descriptions into executable shell commands using Google's Gemini API, backed by a strict multi-layer safety gate.

---

## Key Features

- **Multi-OS & Shell Awareness**: Automatically detects whether you are on Windows, macOS, or Linux and tailors commands for PowerShell, CMD, Bash, or Zsh.
- **Strict Safety Engine**: Evaluates every generated command against heuristic denylist rules (detecting recursive deletes, disk wipes, fork bombs, remote script piping, system file tampering, etc.).
- **Proportional Confirmation**:
  - **Low Risk**: Standard `[y/N]` prompt (defaults to No).
  - **High Risk**: Requires typing `YES` in full.
- **In-Place Command Editing**: Review and tweak the generated command in your terminal before running it.
- **Dry-Run Mode (`--dry-run` / `-d`)**: Generate, inspect, and evaluate commands without executing them.
- **Audit Logging**: Every command (whether executed, dry-run, or rejected) is recorded in `~/.nl2sh/history.jsonl`.
- **Contextual Follow-ups**: Remembers recent requests to enable multi-turn context (e.g. *"now sort those by size"*).
- **Secure Encrypted Storage**: API keys are securely encrypted using Windows DPAPI.

---

## Quick Start

### 1. Standalone Executable (Windows)
Download `nl2sh.exe` from the latest GitHub Release and double-click to run! On first launch, it will interactively prompt for your free Gemini API key and securely encrypt it.

### 2. Running from Source
Using `uv`:
```bash
# Run interactive session
uv run nl2sh

# Run a one-shot query
uv run nl2sh "find all files ending with .py in current folder"

# Run a dry-run query (no execution)
uv run nl2sh "recursively find large files" --dry-run
```

### 3. Install as a System CLI
```bash
pip install -e .
# or
uv tool install .
```

---

## Configuration

You can provide your API key via:
1. First-time interactive prompt (stored encrypted in `~/.nl2sh/config.json`)
2. Environment variable: `export GEMINI_API_KEY="your-key"` or `$env:GEMINI_API_KEY="your-key"`
3. Local `.env` file (see `.env.example`)

---

## Running Tests

```bash
uv run pytest
```

---

## License

MIT License
