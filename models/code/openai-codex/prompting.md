# OpenAI Codex Prompting Guide

*Last updated: 2025-08-16*

## Tips & Techniques

- The codex CLI agent supports other providers and does not require OpenAI account settings, tokens, or registration cookie calls
- Use codex CLI with an OpenAI Plus/Pro subscription to access command-line GPT-5 without per-token billing.
- The clickable "Suggested task → Start task" buttons appear when you’re in a Codex Ask conversation that (a) is connected to a repository sandbox, and (b) ...
- Use the codex CLI agent with the --config option to set the model name and local Ollama port, e.g., codex --config model=ollama-model port=11434
- clickable 'Suggested task → Start task' buttons appear when you're in a Codex Ask conversation that is connected to a repository sandbox

## Recommended Settings

- model=your-kobold-model
- provider=kobold
- providers.kobold.name=Kobold
- providers.kobold.baseURL=http://localhost:5001/v1
- providers.kobold.envKey=KOBOLD_API_KEY
- config_path=~/.codex/config.json
- provider=ollama
- model=deepseek-r1:1.5b
- command=codex -p ollama -m deepseek-r1:1.5b

## Sources

- Reddit community discussions
- User-reported experiences
